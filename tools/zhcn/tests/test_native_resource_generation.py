#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / "tools" / "zhcn" / "generate_native_resources.py"
SOURCE_RC = REPO_ROOT / "SystemInformer" / "SystemInformer.rc"
ZH_CN_RC = REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc"
PLUGIN_MODULES = (
    "DotNetTools",
    "ExtendedNotifications",
    "ExtendedServices",
    "ExtendedTools",
    "HardwareDevices",
    "NetworkTools",
    "OnlineChecks",
    "ToolStatus",
    "Updater",
    "UserNotes",
    "WindowExplorer",
)
TOOL_MODULES = (
    (
        "peview",
        REPO_ROOT / "tools" / "peview" / "peview.rc",
        REPO_ROOT / "tools" / "peview" / "peview.zh-cn.rc",
        REPO_ROOT / "tools" / "peview" / "peview.vcxproj",
        REPO_ROOT / "tools" / "peview" / "peview.vcxproj.filters",
    ),
    (
        "CustomSetupTool",
        REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc",
        REPO_ROOT / "tools" / "CustomSetupTool" / "resource.zh-cn.rc",
        REPO_ROOT / "tools" / "CustomSetupTool" / "CustomSetupTool.vcxproj",
        REPO_ROOT / "tools" / "CustomSetupTool" / "CustomSetupTool.vcxproj.filters",
    ),
)
DIALOG_RE = re.compile(r"(?m)^([A-Z][A-Z0-9_]*|\d+)\s+DIALOG(?:EX)?\b")
FONT_RE = re.compile(r'(?m)^\s*FONT\s+(\d+)\s*,\s*"([^"]+)"')
STRING_ENTRY_RE = re.compile(r'(?m)^\s*([A-Z][A-Z0-9_]*|\d+)\s+"')


def load_validator_module():
    path = REPO_ROOT / "tools" / "zhcn" / "validate_templates.py"
    spec = importlib.util.spec_from_file_location("validate_templates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_native_resources", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_translation_checker_module():
    path = REPO_ROOT / "tools" / "zhcn" / "check_translation.py"
    spec = importlib.util.spec_from_file_location("check_translation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stringtable_ids(source: str) -> list[str]:
    generator = load_generator_module()
    return [
        resource_id
        for block in generator.extract_stringtable_blocks(source)
        for resource_id in STRING_ENTRY_RE.findall("\n".join(block))
    ]


def wide_string(value: str) -> bytes:
    return value.encode("utf-16-le") + b"\0\0"


def make_stringtable_block(values: dict[int, str]) -> bytes:
    data = bytearray()

    for index in range(16):
        value = values.get(index, "")
        encoded = value.encode("utf-16-le")
        data += struct.pack("<H", len(encoded) // 2)
        data += encoded

    return bytes(data)


def make_dialog_template(
    caption: str,
    label: str,
    point_size: int,
    typeface: str,
    *,
    item_text_ordinal=None,
    weight: int = 400,
    pad_end: bool = True,
    tail_label: str = "Tail",
    set_font: bool = True,
) -> bytes:
    style = 0x80000000 | 0x00C00000 | (0x0040 if set_font else 0x0008)
    data = bytearray(struct.pack(
        "<HHIIIHhhhh", 1, 0xFFFF, 0, 0, style, 2, 0, 0, 120, 40
    ))
    data += b"\0\0"  # menu
    data += b"\0\0"  # window class
    data += wide_string(caption)
    if set_font:
        data += struct.pack("<HHBB", point_size, weight, 0, 1)
        data += wide_string(typeface)
    data += b"\0" * (-len(data) % 4)
    data += struct.pack("<IIIhhhhI", 0, 0, 0x50000000, 6, 8, 100, 12, 202)
    data += struct.pack("<HH", 0xFFFF, 0x0082)  # static control class
    if item_text_ordinal is None:
        data += wide_string(label)
    else:
        data += struct.pack("<HH", 0xFFFF, item_text_ordinal)
    data += struct.pack("<HH", 4, 0x1234)  # size includes the size WORD
    data += b"\0" * (-len(data) % 4)
    data += struct.pack("<IIIhhhhI", 0, 0, 0x50000000, 6, 22, 100, 12, 203)
    data += struct.pack("<HH", 0xFFFF, 0x0082)
    data += wide_string(tail_label)
    data += b"\0\0"
    if pad_end:
        data += b"\0" * (-len(data) % 4)
    return bytes(data)


class NativeResourceGenerationTests(unittest.TestCase):
    def test_audit_preserves_urls_and_doubled_quotes_in_rc_strings(self):
        audit = load_audit_module()
        source = (
            'CONTROL "<a href=""https://example.invalid/path"">Label</a>",'
            'IDC_LINK\n// CONTROL "Ignored",IDC_STATIC\n'
        )
        masked = audit.mask_rc_comments(source)
        match = audit.RC_QUOTED_RE.search(masked)

        self.assertIsNotNone(match)
        self.assertEqual(
            audit.rc_unescape(match.group(1)),
            '<a href="https://example.invalid/path">Label</a>',
        )
        self.assertNotIn("Ignored", masked)

    def test_audit_keeps_visible_sentences_that_start_with_placeholder(self) -> None:
        audit = load_audit_module()

        self.assertTrue(audit.is_noise("%s"))
        self.assertTrue(audit.is_noise("%lu"))
        self.assertTrue(audit.is_noise("%lu|"))
        self.assertFalse(audit.is_noise("%s complete."))
        self.assertFalse(
            audit.is_noise("%s is not recommended when running this program.")
        )
        self.assertEqual(audit.CALL_SPECS["PhShowStatus"], {1: "c_msgbox"})
        self.assertEqual(
            audit.CALL_SPECS["PhShowContinueStatus"], {1: "c_msgbox"}
        )

    def test_audit_scans_message_macro_title_and_format_arguments(self) -> None:
        audit = load_audit_module()
        source = """
            PhShowError(hwnd, L"Real visible message.");
            PhShowError(hwnd, L"Adjacent " L"format message.");
            PhShowError(hwnd, L"%s", L"Visible vararg message.");
            PhShowWarning(hwnd, L"Visible warning: %s", detail);
            PhShowInformation2(hwnd, L"Visible title", L"Visible content");
            PhShowError2(
                hwnd,
                L"Visible vararg title",
                L"%s",
                L"Visible vararg content"
            );
            PhShowWarning2(
                hwnd,
                L"Adjacent title",
                L"%s",
                L"Adjacent "
                L"content"
            );
            PhShowWarning(
                hwnd,
                L"Visible format without placeholders.",
                L"Unused vararg literal."
            );
            // PhShowError(hwnd, L"Commented-out message.");
            /* PhShowError(hwnd, L"Block-commented message."); */
            PhShowMessageOneTime2(
                hwnd,
                TD_CLOSE_BUTTON,
                TD_INFORMATION_ICON,
                L"One-time title",
                &checked,
                L"One-time content"
            );
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            {entry["english"] for entry in entries},
            {
                "Real visible message.",
                "Adjacent format message.",
                "Visible vararg message.",
                "Visible warning: %s",
                "Visible title",
                "Visible content",
                "Visible vararg title",
                "Visible vararg content",
                "Adjacent title",
                "Adjacent content",
                "Visible format without placeholders.",
                "One-time title",
                "One-time content",
            },
        )
        categories = {
            entry["english"]: entry["category"]
            for entry in entries
        }
        self.assertEqual(
            categories["Visible vararg message."],
            "c_msgbox_vararg",
        )
        self.assertEqual(
            categories["Visible vararg content"],
            "c_msgbox",
        )
        self.assertNotIn("Commented-out message.", categories)
        self.assertNotIn("Block-commented message.", categories)
        self.assertNotIn("Unused vararg literal.", categories)

    def test_audit_scans_tool_resources_and_stringtables(self) -> None:
        audit = load_audit_module()
        source_files = {
            pathlib.Path(path).resolve().relative_to(REPO_ROOT).as_posix()
            for path in audit.iter_source_files()
        }
        entries = []

        audit.scan_rc_file(
            str(REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc"),
            entries,
        )

        self.assertIn("tools/peview/peview.rc", source_files)
        self.assertIn("tools/CustomSetupTool/resource.rc", source_files)
        self.assertTrue(
            any(
                entry["category"] == "rc_stringtable"
                and entry["english"] == "Downloading update..."
                for entry in entries
            )
        )

    def test_generator_parses_rc_doubled_quotes_as_one_string(self):
        generator = load_generator_module()
        line = (
            '    CONTROL "<a href=""https://example.invalid"">English label</a>",'
            'IDC_LINK'
        )
        translations = {
            '<a href="https://example.invalid">English label</a>':
                '<a href="https://example.invalid">中文标签</a>',
        }

        localized = generator.replace_first_string(line, translations)

        self.assertIn(
            '"<a href=""https://example.invalid"">中文标签</a>"',
            localized,
        )
        self.assertNotIn("English label", localized)

    def test_generator_rejects_unreviewed_dialog_text(self) -> None:
        generator = load_generator_module()

        with self.assertRaisesRegex(ValueError, "missing translation decision"):
            generator.replace_first_string('CAPTION "New upstream dialog"', {})

    def test_generator_rejects_nested_resource_script_includes(self) -> None:
        generator = load_generator_module()

        with self.assertRaisesRegex(ValueError, "nested resource script"):
            generator.source_includes(
                '#include "resource.h"\n#include "upstream-resources.rc2"'
            )

    def test_generator_localizes_stringtable_entries(self) -> None:
        generator = load_generator_module()
        block = [
            "STRINGTABLE",
            "BEGIN",
            '    IDS_SETUP_NEXT "&Next >"',
            "END",
        ]

        localized = generator.localize_stringtable_block(
            block,
            {"&Next >": "下一步(&N) >"},
        )

        self.assertEqual(localized[2], '    IDS_SETUP_NEXT "下一步(&N) >"')

    def test_generator_preserves_stringtable_line_break_escapes(self) -> None:
        generator = load_generator_module()
        line = r'    IDS_SETUP_MESSAGE "First\r\nSecond"'

        localized = generator.replace_first_string(
            line,
            {"First\r\nSecond": "第一行\r\n第二行"},
            decode_escapes=True,
        )

        self.assertEqual(localized, r'    IDS_SETUP_MESSAGE "第一行\r\n第二行"')

    def test_compiled_dialog_parser_separates_structure_text_and_font(self) -> None:
        validator = load_validator_module()
        english = validator.parse_dialog_template(
            make_dialog_template("General", "Options", 8, "MS Shell Dlg")
        )
        chinese = validator.parse_dialog_template(
            make_dialog_template("常规", "设置", 9, "Microsoft YaHei UI")
        )

        self.assertEqual(english["structure"], chinese["structure"])
        self.assertEqual(chinese["font"][0], 9)
        self.assertEqual(chinese["font"][-1], "Microsoft YaHei UI")
        self.assertEqual(chinese["strings"], ["常规", "设置", "Tail"])

    def test_compiled_stringtable_parser_preserves_slots(self) -> None:
        validator = load_validator_module()
        strings = validator.parse_stringtable_block(
            make_stringtable_block({0: "Back", 3: "完成", 8: "😀", 15: "Retry"})
        )

        self.assertEqual(strings[0], "Back")
        self.assertEqual(strings[3], "完成")
        self.assertEqual(strings[8], "😀")
        self.assertEqual(strings[15], "Retry")
        self.assertEqual(len(strings), 16)
        self.assertEqual(
            validator.format_specifiers("Error %lu: %s"),
            validator.format_specifiers("错误 %lu：%s"),
        )
        self.assertNotEqual(
            validator.format_specifiers("Error %s: %lu"),
            validator.format_specifiers("错误 %lu：%s"),
        )
        self.assertEqual(
            validator.format_specifiers("%.*s / %-08I64u"),
            ["%.*s", "%-08I64u"],
        )
        self.assertEqual(
            validator.format_specifiers(
                "Append /fail=%1% to pass the fail count to the program."
            ),
            [],
        )
        self.assertTrue(validator.required_string_resources_missing(set(), True))
        self.assertFalse(validator.required_string_resources_missing(set(), False))
        self.assertFalse(validator.required_string_resources_missing({2000}, True))
        self.assertTrue(validator.string_resource_count_mismatch({2000}, 41))
        self.assertFalse(validator.string_resource_count_mismatch(set(range(41)), 41))
        self.assertFalse(validator.string_resource_count_mismatch({2000}, None))

    def test_source_translation_placeholder_check_preserves_order_and_flags(self) -> None:
        checker = load_translation_checker_module()

        self.assertIsNone(
            checker.check_placeholders("Error %lu: %s", "错误 %lu：%s")
        )
        self.assertIsNotNone(
            checker.check_placeholders("Error %s: %lu", "错误 %lu：%s")
        )
        self.assertEqual(
            checker.format_specs("%.*s / %-08I64u"),
            ["%.*s", "%-08I64u"],
        )
        self.assertEqual(
            checker.format_specs(
                "Append /fail=%1% to pass the fail count to the program."
            ),
            [],
        )
        self.assertTrue(checker.translation_is_effective("c_msgbox", "已翻译"))
        self.assertFalse(
            checker.translation_is_effective("c_msgbox_vararg", "已翻译")
        )

    def test_compiled_dialog_parser_keeps_control_ordinals_in_structure(self) -> None:
        validator = load_validator_module()
        english = validator.parse_dialog_template(
            make_dialog_template(
                "About", "", 8, "MS Shell Dlg", item_text_ordinal=100
            )
        )
        chinese = validator.parse_dialog_template(
            make_dialog_template(
                "关于", "", 9, "Microsoft YaHei UI", item_text_ordinal=101
            )
        )

        self.assertNotEqual(english["structure"], chinese["structure"])

    def test_compiled_dialog_parser_accepts_unpadded_final_item(self) -> None:
        validator = load_validator_module()
        template = make_dialog_template(
            "General", "Options", 8, "MS Shell Dlg", pad_end=False,
            tail_label="Final",
        )

        self.assertEqual(len(template) % 4, 2)
        parsed = validator.parse_dialog_template(template)

        self.assertEqual(parsed["strings"], ["General", "Options", "Final"])

    def test_compiled_dialog_parser_does_not_treat_fixedsys_as_font(self) -> None:
        validator = load_validator_module()
        template = make_dialog_template(
            "General", "Options", 8, "unused", set_font=False
        )

        parsed = validator.parse_dialog_template(template)

        self.assertIsNone(parsed["font"])

    def test_compiled_dialog_font_attributes_exclude_only_size_and_face(self) -> None:
        validator = load_validator_module()
        baseline = validator.parse_dialog_template(
            make_dialog_template("General", "Options", 8, "MS Shell Dlg")
        )
        changed_weight = validator.parse_dialog_template(
            make_dialog_template(
                "常规", "设置", 9, "Microsoft YaHei UI", weight=700
            )
        )

        self.assertNotEqual(
            validator.dialog_font_attributes(baseline["font"]),
            validator.dialog_font_attributes(changed_weight["font"]),
        )

    def test_all_generated_resources_are_current(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("14 modules", result.stdout)
        self.assertIn("270 dialogs", result.stdout)
        self.assertIn("487 strings", result.stdout)

    def test_generated_utf8_resource_does_not_redeclare_code_page(self) -> None:
        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")

        self.assertTrue(ZH_CN_RC.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("#pragma code_page", localized)

    def test_main_dialog_resource_ids_match_english_source(self) -> None:
        source = SOURCE_RC.read_text(encoding="utf-8-sig")
        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        source_ids = DIALOG_RE.findall(source)
        localized_ids = DIALOG_RE.findall(localized)

        self.assertGreater(len(source_ids), 50)
        self.assertEqual(localized_ids, source_ids)

    def test_localized_dialogs_use_explicit_zh_cn_font(self) -> None:
        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        fonts = FONT_RE.findall(localized)

        self.assertIn("LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED", localized)
        self.assertGreater(len(fonts), 50)
        self.assertTrue(all(int(point_size) >= 9 for point_size, _ in fonts))
        self.assertTrue(all(typeface == "Microsoft YaHei UI" for _, typeface in fonts))

    def test_native_resource_is_compiled_and_checked_by_ci(self) -> None:
        project = (REPO_ROOT / "SystemInformer" / "SystemInformer.vcxproj").read_text(
            encoding="utf-8-sig"
        )
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn('<ResourceCompile Include="SystemInformer.zh-cn.rc" />', project)
        self.assertIn("generate_native_resources.py --check", workflow)

    def test_plugin_native_resources_are_compiled_by_their_projects(self) -> None:
        for module_name in PLUGIN_MODULES:
            with self.subTest(module=module_name):
                module_dir = REPO_ROOT / "plugins" / module_name
                localized_name = f"{module_name}.zh-cn.rc"
                localized = module_dir / localized_name
                project_root = ET.parse(
                    module_dir / f"{module_name}.vcxproj"
                ).getroot()
                filters_root = ET.parse(
                    module_dir / f"{module_name}.vcxproj.filters"
                ).getroot()
                project_resources = [
                    element.attrib.get("Include")
                    for element in project_root.iter()
                    if element.tag.endswith("ResourceCompile")
                ]
                filter_resources = [
                    element
                    for element in filters_root.iter()
                    if element.tag.endswith("ResourceCompile")
                    and element.attrib.get("Include") == localized_name
                ]

                self.assertTrue(localized.is_file())
                self.assertTrue(localized.read_bytes().startswith(b"\xef\xbb\xbf"))
                self.assertEqual(project_resources.count(localized_name), 1)
                self.assertEqual(len(filter_resources), 1)
                filter_names = [
                    child.text
                    for child in filter_resources[0]
                    if child.tag.endswith("Filter")
                ]
                self.assertEqual(filter_names, ["Resource Files"])

    def test_plugin_dialog_resource_ids_and_fonts_match_english_sources(self) -> None:
        for module_name in PLUGIN_MODULES:
            with self.subTest(module=module_name):
                module_dir = REPO_ROOT / "plugins" / module_name
                source = (module_dir / f"{module_name}.rc").read_text(
                    encoding="utf-8-sig"
                )
                localized = (module_dir / f"{module_name}.zh-cn.rc").read_text(
                    encoding="utf-8-sig"
                )
                source_ids = DIALOG_RE.findall(source)
                localized_ids = DIALOG_RE.findall(localized)
                source_string_ids = stringtable_ids(source)
                localized_string_ids = stringtable_ids(localized)
                fonts = FONT_RE.findall(localized)

                self.assertGreater(len(source_ids), 0)
                self.assertEqual(localized_ids, source_ids)
                self.assertEqual(localized_string_ids, source_string_ids)
                self.assertEqual(len(fonts), len(source_ids))
                self.assertIn(
                    "LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED",
                    localized,
                )
                self.assertTrue(
                    all(int(point_size) >= 9 for point_size, _ in fonts)
                )
                self.assertTrue(
                    all(typeface == "Microsoft YaHei UI" for _, typeface in fonts)
                )

    def test_tool_native_resources_match_sources_and_projects(self) -> None:
        for module_name, source_path, localized_path, project_path, filters_path in TOOL_MODULES:
            with self.subTest(module=module_name):
                source = source_path.read_text(encoding="utf-8-sig")
                localized = localized_path.read_text(encoding="utf-8-sig")
                source_ids = DIALOG_RE.findall(source)
                localized_ids = DIALOG_RE.findall(localized)
                source_string_ids = stringtable_ids(source)
                localized_string_ids = stringtable_ids(localized)
                fonts = FONT_RE.findall(localized)
                localized_name = localized_path.name
                project_root = ET.parse(project_path).getroot()
                filters_root = ET.parse(filters_path).getroot()
                project_resources = [
                    element.attrib.get("Include")
                    for element in project_root.iter()
                    if element.tag.endswith("ResourceCompile")
                ]
                filter_resources = [
                    element
                    for element in filters_root.iter()
                    if element.tag.endswith("ResourceCompile")
                    and element.attrib.get("Include") == localized_name
                ]

                self.assertGreater(len(source_ids), 0)
                self.assertEqual(localized_ids, source_ids)
                self.assertEqual(localized_string_ids, source_string_ids)
                self.assertEqual(len(fonts), len(source_ids))
                self.assertTrue(localized_path.read_bytes().startswith(b"\xef\xbb\xbf"))
                self.assertIn(
                    "LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED",
                    localized,
                )
                self.assertTrue(
                    all(int(point_size) >= 9 for point_size, _ in fonts)
                )
                self.assertTrue(
                    all(typeface == "Microsoft YaHei UI" for _, typeface in fonts)
                )
                self.assertEqual(project_resources.count(localized_name), 1)
                self.assertEqual(len(filter_resources), 1)
                self.assertEqual(
                    [
                        child.text
                        for child in filter_resources[0]
                        if child.tag.endswith("Filter")
                    ],
                    ["Resource Files"],
                )

    def test_custom_sign_tool_has_no_localizable_ui_resources(self) -> None:
        source = (
            REPO_ROOT / "tools" / "CustomSignTool" / "resource.rc"
        ).read_text(encoding="utf-8-sig")

        self.assertIsNone(DIALOG_RE.search(source))
        self.assertIsNone(
            re.search(
                r"(?m)^\s*(?:(?:[A-Z][A-Z0-9_]*|\d+)\s+)?"
                r"(?:MENU(?:EX)?|STRINGTABLE)\b",
                source,
            )
        )

    def test_localized_tools_select_zh_cn_ui_language(self) -> None:
        for relative_path in (
            "tools/peview/main.c",
            "tools/CustomSetupTool/main.c",
        ):
            with self.subTest(source=relative_path):
                source = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")

                self.assertRegex(
                    source,
                    r"PhSetApplicationUiLanguage\(\s*"
                    r"MAKELANGID\(LANG_CHINESE,\s*SUBLANG_CHINESE_SIMPLIFIED\)",
                )
                self.assertIn("PhTranslationEnabled = TRUE;", source)

    def test_tool_property_pages_use_language_aware_resource_loader(self) -> None:
        peview = (REPO_ROOT / "tools" / "peview" / "prpsh.c").read_text(
            encoding="utf-8-sig"
        )
        setup = (
            REPO_ROOT / "tools" / "CustomSetupTool" / "wizard.c"
        ).read_text(encoding="utf-8-sig")

        self.assertNotRegex(peview, r"(?<!Ph)CreatePropertySheetPage\s*\(")
        self.assertRegex(
            peview,
            r"if \(!propSheetPageHandle\)\s*\{\s*"
            r"PhDereferenceObject\(PropPageContext\);\s*return FALSE;",
        )
        self.assertRegex(
            peview,
            r"return PvCreatePropPageContextEx\(\s*"
            r"PhInstanceHandle,\s*Template,\s*DlgProc,\s*Context\s*\);",
        )
        self.assertIn("PhCreatePropertySheetPage(&pageDefinitions[pageIndex])", setup)
        self.assertIn("header.phpage = pages;", setup)
        self.assertNotIn("PSH_PROPSHEETPAGE", setup)
        self.assertNotIn("header.ppsp = pages;", setup)

    def test_peview_uses_dpi_aware_system_message_font(self) -> None:
        peview = (REPO_ROOT / "tools" / "peview" / "prpsh.c").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("PhApplicationFont = PhCreateMessageFont(dpiValue);", peview)
        self.assertNotIn('PvpCreateFont(L"Microsoft Sans Serif"', peview)
        self.assertNotIn('PvpCreateFont(L"Tahoma"', peview)

    def test_peview_context_menus_use_native_string_resources(self) -> None:
        peview_header = (
            REPO_ROOT / "tools" / "peview" / "include" / "peview.h"
        ).read_text(encoding="utf-8-sig")
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "peview").glob("*.c")
        )
        resource_header = (
            REPO_ROOT / "tools" / "peview" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "tools" / "peview" / "peview.rc"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("PvpLoadUiString", peview_header)
        self.assertIn("IDS_PV_MENU_DISPLAY_RESOURCE", resource_header)
        self.assertIn("IDS_PV_MENU_SAVE_CERTIFICATE", resource_header)
        self.assertEqual(len(stringtable_ids(resource_script)), 128)

        migrated_labels = (
            "ANSI",
            "UTF-8",
            "UTF-16",
            "Extended character set",
            "Skip .text section",
            "Skip high entropy sections",
            "Skip strings with numbers",
            "Skip strings with symbols",
            "Minimum length...",
            "Refresh",
            "Hide writable",
            "Hide executable",
            "Hide code",
            "Hide readable",
            "Hide parameters",
            "Filter non-writable",
            "Highlight writable",
            "Highlight executable",
            "Highlight code",
            "Highlight readable",
            "Display resource...",
            "Save resource...",
            "Copy",
            "View certificate...",
            "Save certificate...",
            "&Copy",
            "Delete",
            "Size column to fit",
            "Size all columns to fit",
            "Hide column",
            "Choose columns...",
            "Reset sort",
        )
        for label in migrated_labels:
            self.assertNotRegex(
                source,
                rf"PhCreateEMenuItem\([^\n]*L\"{re.escape(label)}\"",
            )

    def test_peview_column_labels_use_native_string_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "peview").glob("*.c")
        )

        for function_name in ("PhAddListViewColumn", "PhAddTreeNewColumn"):
            calls = re.findall(
                rf"{function_name}\((.*?)\);",
                source,
                re.DOTALL,
            )
            self.assertTrue(calls)
            for call in calls:
                self.assertLessEqual(
                    set(re.findall(r'L"([^"\r\n]+)"', call)),
                    {"#"},
                )

    def test_peview_options_and_error_messages_use_native_string_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "peview").glob("*.c")
        )
        migrated_labels = (
            "Enable theme support",
            "Enable legacy properties window",
            "Enable view borders",
            "Remember last selected window",
            "Do you want to reset all settings and restart PE Viewer?",
            "Do you want to restart PE Viewer now?",
            "One or more options you have changed requires a restart of PE Viewer.",
            "PE View's settings file is corrupt. Do you want to reset it?",
            "PE Viewer does not support this image type.",
            "PE Viewer has crashed :(",
            "Unable to create the CLR table preview window.",
            "Unable to enumerate the image resources.",
            "Unable to locate the resource data.",
            "Unable to preview CLR table rows because CLR metadata is unavailable.",
            "You are attempting to run the 32-bit version of PE Viewer on 64-bit Windows.",
        )

        for label in migrated_labels:
            self.assertNotIn(f'L"{label}', source)

        for function_name in (
            "PhShowError",
            "PhShowError2",
            "PhShowMessage",
            "PhShowMessage2",
            "PhShowStatus",
            "PhShowWarning2",
        ):
            calls = re.findall(
                rf"{function_name}\s*\((.*?)\);",
                source,
                re.DOTALL,
            )
            for call in calls:
                with self.subTest(function=function_name, call=call):
                    self.assertLessEqual(
                        set(re.findall(r'L"(?:[^"\\]|\\.)*"', call)),
                        {'L""', 'L"%s"'},
                    )

    def test_main_options_messages_use_native_string_resources(self) -> None:
        options = (REPO_ROOT / "SystemInformer" / "options.c").read_text(
            encoding="utf-8-sig"
        )
        main = (REPO_ROOT / "SystemInformer" / "main.c").read_text(
            encoding="utf-8-sig"
        )
        resource_script = SOURCE_RC.read_text(encoding="utf-8-sig")

        self.assertEqual(len(stringtable_ids(resource_script)), 215)
        self.assertIn(
            "static PPH_STRING PhApplicationUiStrings[IDS_PH_LAST - IDS_PH_FIRST + 1]",
            main,
        )
        self.assertIn("if (!PhpInitializeApplicationUiStrings())", main)

        resource_ids = set(stringtable_ids(resource_script))
        application_source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (
                *(REPO_ROOT / "SystemInformer").glob("*.c"),
                REPO_ROOT / "phlib" / "guisup.c",
                REPO_ROOT / "phlib" / "mapldr.c",
                REPO_ROOT / "phlib" / "util.c",
            )
        )
        used_ids = set(
            re.findall(
                r"\b(IDS_PH_[A-Z0-9_]+)\b",
                application_source,
            )
        ) - {"IDS_PH_FIRST", "IDS_PH_LAST"}
        self.assertEqual(used_ids, resource_ids)

        resource_header = (
            REPO_ROOT / "SystemInformer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        resource_header += (
            REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
        ).read_text(encoding="utf-8-sig")
        numeric_ids = [
            int(value)
            for _, value in re.findall(
                r"^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)$",
                resource_header,
                re.MULTILINE,
            )
        ]
        self.assertEqual(sorted(numeric_ids), list(range(2000, 2215)))
        self.assertNotRegex(options, r"\bmessage\s*=\s*L\"")
        self.assertNotRegex(
            options,
            r"PhShowOptionsDefaultInstallLocation\([^;]*L\"",
        )

        for function_name in (
            "PhShowError",
            "PhShowError2",
            "PhShowInformation2",
            "PhShowMessage",
            "PhShowMessage2",
            "PhShowStatus",
            "PhShowWarning2",
        ):
            calls = re.findall(
                rf"{function_name}\s*\((.*?)\);",
                options,
                re.DOTALL,
            )
            for call in calls:
                with self.subTest(function=function_name, call=call):
                    self.assertLessEqual(
                        set(re.findall(r'L"(?:[^"\\]|\\.)*"', call)),
                        {'L""', 'L"%s"'},
                    )

    def test_main_window_creation_errors_share_native_resource(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        self.assertNotIn('L"Unable to create the window."', source)
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_UNABLE_CREATE_WINDOW)"
            ),
            10,
        )

    def test_early_crash_prompt_does_not_depend_on_ui_string_cache(self) -> None:
        main = (REPO_ROOT / "SystemInformer" / "main.c").read_text(
            encoding="utf-8-sig"
        )
        crash_prompt = (
            'L"System Informer has crashed :(\\r\\n\\r\\n'
            'Do you want to create a minidump on the Desktop?"'
        )

        self.assertIn(crash_prompt, main)
        self.assertNotIn("IDS_PH_CREATE_CRASH_MINIDUMP", main)

    def test_main_missing_process_errors_share_native_resource(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        self.assertNotIn('L"The process does not exist."', source)
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_PROCESS_DOES_NOT_EXIST)"
            ),
            15,
        )

    def test_main_common_service_and_file_errors_share_native_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        self.assertNotIn('L"The service does not exist."', source)
        self.assertNotIn('L"Unable to locate the file."', source)
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_SERVICE_DOES_NOT_EXIST)"
            ),
            6,
        )
        self.assertGreaterEqual(
            source.count("PhGetApplicationUiString(IDS_PH_UNABLE_LOCATE_FILE)"),
            8,
        )

    def test_main_common_operation_errors_share_native_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        for literal in (
            'L"Unable to create the file"',
            'L"Unable to decommit the memory region"',
            'L"Unable to free the memory region"',
            'L"Unable to perform the operation."',
            'L"Unable to unmap the section view"',
        ):
            self.assertNotIn(literal, source)
        self.assertNotRegex(source, r'L"Unable to open the process\.?"')
        self.assertGreaterEqual(
            source.count("PhGetApplicationUiString(IDS_PH_UNABLE_CREATE_FILE)"),
            10,
        )
        self.assertGreaterEqual(
            source.count("PhGetApplicationUiString(IDS_PH_UNABLE_OPEN_PROCESS)"),
            14,
        )
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_UNABLE_PERFORM_OPERATION)"
            ),
            9,
        )
        for resource_id in (
            "IDS_PH_UNABLE_DECOMMIT_MEMORY_REGION",
            "IDS_PH_UNABLE_FREE_MEMORY_REGION",
            "IDS_PH_UNABLE_UNMAP_SECTION_VIEW",
        ):
            self.assertEqual(source.count(resource_id), 1)

    def test_main_memory_and_enumeration_errors_use_native_resources(self) -> None:
        sources = {
            path.name: path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        }
        literals = (
            "Unable to enumerate processes",
            "Unable to close the TCP connection",
            "Unable to edit memory",
            "Unable to edit the memory region.",
            "Unable to determine whether the thread is waiting.",
            "Unable to empty the memory list.",
            "Unable to empty the region working set.",
            "Unable to enumerate process handles",
            "Unable to duplicate the token.",
            "Unable to change memory protection",
            "Unable to close the window.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                pattern = re.compile(
                    rf'L"{re.escape(literal.removesuffix("."))}\.?' + '"'
                )
                remaining_files = [
                    name
                    for name, source in sources.items()
                    if pattern.search(source)
                ]
                self.assertEqual(
                    remaining_files,
                    [],
                    f"raw UI literal remains: {literal}",
                )

    def test_main_runtime_operation_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )
        literals = (
            "Unable to query heap information.",
            "Unable to query 32bit heap information.",
            "Unable to query lock information.",
            "Unable to search for strings.",
            "Unable to create the search thread",
            "Unable to analyze the thread.",
            "Unable to show the process properties.",
            "Unable to change service configuration.",
            "Unable to create the service.",
            "Unable to shutdown WSL instances.",
            "Unable to save application settings.",
            "Unable to find the memory region for the selected address.",
            "Unable to open the file location.",
            "Unable to open the file properties.",
            "Unable to open key.",
            "Unable to open the thread.",
            "Unable to map a view of the section.",
            "Unable to query the section.",
            "Unable to load the stack.",
            "Unable to refresh the stack.",
            "Unable to query pagefile information.",
            "The minimum length must be at least 4.",
            "At least one memory type (Private, Image, or Mapped) must be selected.",
            "The thread does not appear to be waiting.",
            "The process has already terminated; only the process record is available.",
            "The binary path is empty.",
            "The object is unnamed.",
            "The 32-bit version of System Informer could not be located.",
            "The section size is greater than 32 MB. Only the first 32 MB will be available.",
            "A 64-bit dump will be created instead. Do you want to continue?",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                stem = re.escape(literal.removesuffix("."))
                self.assertNotRegex(source, rf'L"{stem}\.?[ \t]*"')

    def test_main_power_and_session_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )
        literals = (
            "Unable to hibernate the computer.",
            "Unable to restart the computer.",
            "Unable to shut down the computer.",
            "Unable to sleep the computer.",
            "Unable to lock the computer.",
            "Unable to log off the computer.",
            "Unable to connect to the session",
            "Unable to disconnect the session",
            "Unable to logoff the session",
            "Unable to remote control the session",
            "Unable to shadow session.",
            "Unable to send the message",
            "Unable to detach the debugger.",
            "Unable to configure the advanced boot options.",
            "Unable to configure the boot application.",
            "You cannot remote control the current session.",
            "The process is not being debugged.",
            "Unable to restart to firmware options.",
            "Make sure System Informer is running with administrative privileges.",
            "This machine does not have UEFI support.",
            "Unable to create kernel minidump.",
            "Kernel minidump of processes require administrative privileges.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                stem = re.escape(literal.removesuffix("."))
                self.assertNotRegex(source, rf'L"{stem}\.?[ \t]*"')

    def test_main_process_environment_and_dump_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )
        literals = (
            "Unable to access the dump file",
            "Unable to create the minidump",
            "Unable to change affinity settings.",
            "Unable to create live kernel dump.",
            "Unable to perform the scan",
            "Unable to set the environment variable.",
            "Unable to delete the environment variable.",
            "Unable to disable UIAccess flag.",
            "Unable to set the integrity level",
            "Unable to read memory",
            "Unable to write memory",
            "Unable to set the integrity label",
            "Unable to terminate the process",
            "Unable to create a process structure for the selected process.",
            "Unable to terminate the job",
            "Unable to add the process to the job",
            "Unable to terminate the task.",
            "Unable to clone the process",
            "Unable to update the length.",
            "Unable to query the process.",
            "Unable to start the program.",
            "You must select at least one CPU.",
            "The minimum length is invalid.",
            "Unable to start the execution alias with a process token.",
            "Unable to save the live kernel dump.",
            "Unable to query the current affinity.",
            "Unable to open the token",
            "Unable to execute the command.",
            "Invalid value.",
            "Enter a value between 0 and 64.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                stem = re.escape(literal.removesuffix("."))
                self.assertNotRegex(source, rf'L"{stem}\.?[ \t]*"')

    def test_main_affinity_and_token_dynamic_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (
                REPO_ROOT / "SystemInformer" / "affinity.c",
                REPO_ROOT / "SystemInformer" / "plugin.c",
                REPO_ROOT / "SystemInformer" / "tokprp.c",
            )
        )
        literals = (
            "Unable to change affinity of process %lu",
            "Unable to change affinity of thread %lu",
            "Unable to update affinity for thread(s)",
            "Unable to update affinity for thread(s):\\r\\n%s",
            "Unable to %s %s.",
            "An unknown error occurred.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', source)

        token_properties = (
            REPO_ROOT / "SystemInformer" / "tokprp.c"
        ).read_text(encoding="utf-8-sig")
        self.assertNotRegex(
            token_properties,
            r'action\s*=\s*L"(?:set|enable|disable|reset|remove)"',
        )
        self.assertNotIn('L"privilege"', token_properties)
        self.assertNotIn('L"group"', token_properties)

        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        self.assertIn(
            'IDS_PH_TOKEN_PRIVILEGE                             "特权"',
            localized,
        )

        service_actions = (
            REPO_ROOT / "SystemInformer" / "actions.c"
        ).read_text(encoding="utf-8-sig")
        self.assertNotIn(
            "PhGetApplicationUiString(IDS_PH_UNABLE_APPLY_TOKEN_ACTION)",
            service_actions,
        )

    def test_main_thread_and_program_errors_use_native_resources(self) -> None:
        sources = {
            name: (REPO_ROOT / "SystemInformer" / name).read_text(encoding="utf-8-sig")
            for name in ("actions.c", "appsup.c", "prpgthrd.c")
        }
        combined = "\n".join(sources.values())

        self.assertNotIn('L"Unable to execute the program."', combined)
        self.assertNotRegex(combined, r'L"Unable to [^"]*thread %lu"')
        self.assertIn("_In_ ULONG MessageId", sources["actions.c"])
        self.assertIn(
            "PhGetApplicationUiString(MessageId)",
            sources["actions.c"],
        )

        expected_ids = {
            "IDS_PH_UNABLE_TERMINATE_THREAD": 3,
            "IDS_PH_UNABLE_SUSPEND_THREAD": 3,
            "IDS_PH_UNABLE_RESUME_THREAD": 3,
            "IDS_PH_UNABLE_FREEZE_THREAD": 1,
            "IDS_PH_UNABLE_THAW_THREAD": 1,
            "IDS_PH_UNABLE_CHANGE_THREAD_BOOST_PRIORITY": 1,
            "IDS_PH_UNABLE_SET_THREAD_BOOST_PRIORITY": 2,
            "IDS_PH_UNABLE_CHANGE_THREAD_PRIORITY": 1,
            "IDS_PH_UNABLE_SET_THREAD_PRIORITY": 1,
            "IDS_PH_UNABLE_SET_THREAD_IO_PRIORITY": 3,
            "IDS_PH_UNABLE_SET_THREAD_PAGE_PRIORITY": 1,
            "IDS_PH_UNABLE_EXECUTE_PROGRAM": 3,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", combined)),
                    expected_count,
                )

        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        self.assertIn(
            'IDS_PH_UNABLE_SUSPEND_THREAD                       "无法挂起线程 %lu"',
            localized,
        )
        self.assertNotIn('"无法暂停线程 %lu"', localized)

    def test_main_object_and_module_errors_use_native_resources(self) -> None:
        sources = {
            name: (REPO_ROOT / "SystemInformer" / name).read_text(encoding="utf-8-sig")
            for name in (
                "actions.c",
                "appsup.c",
                "findobj.c",
                "informerwnd.c",
                "memrslt.c",
                "ntobjprp.c",
                "usrlist.c",
            )
        }
        combined = "\n".join(sources.values())
        literals = (
            "Failed to get process start key.",
            "Setting handle attributes requires a connection to the kernel driver.",
            'Unable to close \\"%s\\"',
            "Unable to compile the regular expression.",
            '\\"%s\\" at position %zu.',
            "Unable to locate routines.",
            "Unable to locate the application directory.",
            "Unable to open the event",
            "Unable to open the event pair",
            "Unable to open the semaphore",
            "Unable to open the timer",
            "Unable to search for handles because the total number of handles on the system is too large.",
            "Please check if there are any processes with an extremely large number of handles open.",
            "Unidentified third party object.",
            "Unable to unload the module",
            "Unable to unload ",
            "Unable to unmap the section view at 0x%p",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', combined)

        expected_ids = {
            "IDS_PH_UNABLE_GET_PROCESS_START_KEY": 1,
            "IDS_PH_HANDLE_ATTRIBUTES_REQUIRE_DRIVER": 1,
            "IDS_PH_UNABLE_CLOSE_NAMED_OBJECT": 1,
            "IDS_PH_UNABLE_COMPILE_REGULAR_EXPRESSION": 1,
            "IDS_PH_REGULAR_EXPRESSION_ERROR_POSITION": 1,
            "IDS_PH_UNABLE_LOCATE_ROUTINES": 1,
            "IDS_PH_UNABLE_LOCATE_APPLICATION_DIRECTORY": 1,
            "IDS_PH_UNABLE_OPEN_EVENT": 1,
            "IDS_PH_UNABLE_OPEN_EVENT_PAIR": 1,
            "IDS_PH_UNABLE_OPEN_SEMAPHORE": 1,
            "IDS_PH_UNABLE_OPEN_TIMER": 1,
            "IDS_PH_TOO_MANY_HANDLES": 1,
            "IDS_PH_TOO_MANY_HANDLES_HINT": 1,
            "IDS_PH_UNIDENTIFIED_THIRD_PARTY_OBJECT": 1,
            "IDS_PH_UNABLE_UNLOAD_MODULE": 1,
            "IDS_PH_UNABLE_UNLOAD_NAMED_MODULE": 3,
            "IDS_PH_UNABLE_UNLOAD_NAMED_MODULE_ADMIN": 1,
            "IDS_PH_UNABLE_UNMAP_SECTION_AT_ADDRESS": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", combined)),
                    expected_count,
                )

    def test_main_confirmation_warnings_use_native_resources(self) -> None:
        source = "\n".join(
            (REPO_ROOT / "SystemInformer" / name).read_text(encoding="utf-8-sig")
            for name in ("actions.c", "hidnproc.c", "mwpgproc.c", "tokprp.c")
        )
        literals = (
            "Deleting a service can prevent the system from starting or functioning properly.",
            "Enabling or disabling virtualization for a process may alter its functionality and produce undesirable effects.",
            "Removing privileges may reduce the functionality of the process, and is permanent for the lifetime of the process.",
            "Removing this flag may reduce the functionality of the process provided it is an accessibility application.",
            "Terminating a Zombie process may cause the system to become unstable or crash.",
            "The process will be restarted with the same command line, working directory and privileges.",
            "This filter cannot function because digital signature checking is not enabled.\\r\\n%s",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', source)

        resource_ids = (
            "IDS_PH_SERVICE_DELETION_WARNING",
            "IDS_PH_PROCESS_VIRTUALIZATION_WARNING",
            "IDS_PH_REMOVE_PRIVILEGES_WARNING",
            "IDS_PH_REMOVE_UIACCESS_WARNING",
            "IDS_PH_ZOMBIE_TERMINATION_WARNING",
            "IDS_PH_PROCESS_RESTART_NOTICE",
            "IDS_PH_SIGNATURE_FILTER_REQUIRES_CHECKING",
        )

        for resource_id in resource_ids:
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    1,
                )

        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        self.assertIn(
            'IDS_PH_REMOVE_PRIVILEGES_WARNING                   "移除特权可能会削弱进程功能，并且在进程存续期间无法恢复。"',
            localized,
        )
        self.assertIn(
            'IDS_PH_PROCESS_RESTART_NOTICE                      "该进程将使用相同的命令行、工作目录和特权重新启动。"',
            localized,
        )

    def test_extended_services_errors_use_native_resources(self) -> None:
        source = "\n".join(
            (REPO_ROOT / "plugins" / "ExtendedServices" / name).read_text(
                encoding="utf-8-sig"
            )
            for name in (
                "other.c",
                "recovery.c",
                "svcpnp.c",
                "trigger.c",
                "triggpg.c",
            )
        )
        literals = (
            "Failed to change the device state.",
            "Failed to restart the device.",
            "Failed to uninstall the device.",
            "Unable to find the ETW publisher GUID.",
            "The custom subtype is invalid.",
            "If you continue, they will be removed.",
            "Unable to query service information.",
            "Unable to open LSA policy",
            "Unable to change service information.",
            "Unable to query service recovery information.",
            "The service has %lu failure actions configured",
            "Unable to change service recovery information.",
            "Unable to query service trigger information.",
            "Unable to change service trigger information.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_ES_FAILED_CHANGE_DEVICE_STATE": 2,
            "IDS_ES_FAILED_RESTART_DEVICE": 3,
            "IDS_ES_FAILED_UNINSTALL_DEVICE": 2,
            "IDS_ES_UNABLE_FIND_ETW_PUBLISHER_GUID": 1,
            "IDS_ES_CUSTOM_SUBTYPE_INVALID": 1,
            "IDS_ES_TRIGGER_DATA_REMOVAL_WARNING": 1,
            "IDS_ES_UNABLE_QUERY_SERVICE_INFORMATION": 1,
            "IDS_ES_UNABLE_OPEN_LSA_POLICY": 1,
            "IDS_ES_UNABLE_CHANGE_SERVICE_INFORMATION": 1,
            "IDS_ES_UNABLE_QUERY_SERVICE_RECOVERY_INFORMATION": 2,
            "IDS_ES_SERVICE_FAILURE_ACTIONS_TRUNCATED": 1,
            "IDS_ES_UNABLE_CHANGE_SERVICE_RECOVERY_INFORMATION": 1,
            "IDS_ES_UNABLE_QUERY_SERVICE_TRIGGER_INFORMATION": 1,
            "IDS_ES_UNABLE_CHANGE_SERVICE_TRIGGER_INFORMATION": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

    def test_extended_tools_errors_use_native_resources(self) -> None:
        source = "\n".join(
            (REPO_ROOT / "plugins" / "ExtendedTools" / name).read_text(
                encoding="utf-8-sig"
            )
            for name in (
                "disktab.c",
                "firmware.c",
                "firmware_editor.c",
                "modsrv.c",
                "objmgr.c",
                "reparse.c",
                "thrdact.c",
                "tpm.c",
                "tpm_editor.c",
                "unldll.c",
                "wbcl.c",
                "wswatch.c",
            )
        )
        literals = (
            "Boot log entry",
            "Failed to read TPM",
            "There is no synchronous I/O to cancel.",
            "Unable to cancel synchronous I/O",
            "Unable to create the symbol provider.",
            "Unable to delete firmware variable.",
            "Unable to enable environment privilege.",
            "Unable to enable WS watch.",
            "Unable to enumerate the objects.",
            "Unable to locate files with the SecurityId.",
            "Unable to locate the target.",
            "Unable to query directory object.",
            "Unable to query firmware table.",
            "Unable to query module references.",
            "Unable to query the EFI variable.",
            "Unable to query the TPM",
            "Unable to read the log file",
            "Unable to read the measured boot log",
            "Unable to read TPM",
            "Unable to remove the object identifier.",
            "Unable to remove the reparse point.",
            "Unable to retrieve unload event trace information.",
            "Unable to select the process.",
            "Unable to update the EFI variable.",
            "Unable to write to the TPM",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_ET_BOOT_LOG_ENTRY": 1,
            "IDS_ET_FAILED_READ_TPM": 1,
            "IDS_ET_NO_SYNCHRONOUS_IO": 1,
            "IDS_ET_UNABLE_CANCEL_SYNCHRONOUS_IO": 1,
            "IDS_ET_UNABLE_CREATE_SYMBOL_PROVIDER": 1,
            "IDS_ET_UNABLE_DELETE_FIRMWARE_VARIABLE": 1,
            "IDS_ET_UNABLE_ENABLE_ENVIRONMENT_PRIVILEGE": 1,
            "IDS_ET_UNABLE_ENABLE_WS_WATCH": 1,
            "IDS_ET_UNABLE_ENUMERATE_OBJECTS": 1,
            "IDS_ET_UNABLE_LOCATE_SECURITY_ID_FILES": 1,
            "IDS_ET_UNABLE_LOCATE_TARGET": 2,
            "IDS_ET_UNABLE_QUERY_DIRECTORY_OBJECT": 1,
            "IDS_ET_UNABLE_QUERY_FIRMWARE_TABLE": 1,
            "IDS_ET_UNABLE_QUERY_MODULE_REFERENCES": 2,
            "IDS_ET_UNABLE_QUERY_EFI_VARIABLE": 2,
            "IDS_ET_UNABLE_QUERY_TPM": 1,
            "IDS_ET_UNABLE_READ_LOG_FILE": 1,
            "IDS_ET_UNABLE_READ_MEASURED_BOOT_LOG": 1,
            "IDS_ET_UNABLE_READ_TPM": 1,
            "IDS_ET_UNABLE_REMOVE_OBJECT_IDENTIFIER": 1,
            "IDS_ET_UNABLE_REMOVE_REPARSE_POINT": 1,
            "IDS_ET_UNABLE_RETRIEVE_UNLOAD_TRACE": 1,
            "IDS_ET_UNABLE_SELECT_PROCESS": 1,
            "IDS_ET_UNABLE_UPDATE_EFI_VARIABLE": 2,
            "IDS_ET_UNABLE_WRITE_TPM": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

    def test_module_services_thread_does_not_use_auto_pool_before_initialization(
        self,
    ) -> None:
        source = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "modsrv.c"
        ).read_text(encoding="utf-8-sig")
        thread_body = source.split(
            "NTSTATUS EtpModuleServicesDialogThreadStart", 1
        )[1].split("VOID EtShowModuleServicesDialog", 1)[0]
        before_initialization = thread_body.split("PhInitializeAutoPool", 1)[0]

        self.assertNotIn("PH_AUTO(", before_initialization)
        self.assertEqual(
            before_initialization.count("PhDereferenceObject(resourceTitle);"),
            2,
        )

    def test_user_notes_errors_use_native_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "UserNotes" / "main.c"
        ).read_text(encoding="utf-8-sig")
        literals = (
            "Successfully deleted the IFEO key.",
            "This process has multi-group affinity, %s",
            "Unable to configure IFEO priority for this image.",
            "Unable to query graphics scheduling priority",
            "Unable to query IO priority.",
            "Unable to query page priority.",
            "Unable to query priority.",
            "Unable to query process affinity.",
            "Unable to query process boost.",
            "Unable to query process efficiency mode.",
            "Unable to update graphics scheduling priority",
            "Unable to update the IFEO for IO priority.",
            "Unable to update the IFEO for page priority.",
            "Unable to update the IFEO for priority.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_UN_IFEO_KEY_DELETED": 3,
            "IDS_UN_MULTI_GROUP_AFFINITY": 2,
            "IDS_UN_UNABLE_CONFIGURE_IFEO_PRIORITY": 1,
            "IDS_UN_UNABLE_QUERY_GRAPHICS_PRIORITY": 1,
            "IDS_UN_UNABLE_QUERY_IO_PRIORITY": 2,
            "IDS_UN_UNABLE_QUERY_PAGE_PRIORITY": 2,
            "IDS_UN_UNABLE_QUERY_PRIORITY": 2,
            "IDS_UN_UNABLE_QUERY_PROCESS_AFFINITY": 2,
            "IDS_UN_UNABLE_QUERY_PROCESS_BOOST": 3,
            "IDS_UN_UNABLE_QUERY_PROCESS_EFFICIENCY": 3,
            "IDS_UN_UNABLE_UPDATE_GRAPHICS_PRIORITY": 1,
            "IDS_UN_UNABLE_UPDATE_IFEO_IO_PRIORITY": 2,
            "IDS_UN_UNABLE_UPDATE_IFEO_PAGE_PRIORITY": 2,
            "IDS_UN_UNABLE_UPDATE_IFEO_PRIORITY": 2,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

    def test_remaining_plugin_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        files = {
            "HardwareDevices": ("gpunodes.c",),
            "NetworkTools": ("update.c", "whois.c"),
            "OnlineChecks": ("exclude.c", "upload.c"),
            "ToolStatus": ("find.c", "main.c"),
            "Updater": ("utils.c",),
            "WindowExplorer": ("wnddlg.c", "wndprp.c"),
        }
        source = "\n".join(
            audit.mask_c_comments(
                (REPO_ROOT / "plugins" / plugin / name).read_text(
                    encoding="utf-8-sig"
                )
            )
            for plugin, names in files.items()
            for name in names
        )
        literals = (
            "There are no graphics nodes to display.",
            "The GeoLite updater doesn't support legacy versions of Windows.",
            "Unable to display the whois window.",
            "The regular expression could not be compiled.",
            "Unable to query the service.",
            "The process (PID %lu) does not exist.",
            "Unable to display Find dialog.",
            "Unable to execute the setup.",
            "Unable to add window property.",
            "Unable to create the window property.",
            "Unable to destroy the window.",
            "Unable to display window properties.",
            "Unable to remove the window property.",
            "Unable to update the window property.",
            "The window does not exist.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_HD_NO_GRAPHICS_NODES": 1,
            "IDS_NT_GEOLITE_LEGACY_WINDOWS": 1,
            "IDS_NT_UNABLE_DISPLAY_WHOIS": 1,
            "IDS_OC_REGEX_COMPILE_FAILED": 1,
            "IDS_OC_UNABLE_QUERY_SERVICE": 1,
            "IDS_TS_PROCESS_NOT_FOUND": 2,
            "IDS_TS_UNABLE_DISPLAY_FIND": 1,
            "IDS_UP_UNABLE_EXECUTE_SETUP": 1,
            "IDS_WE_UNABLE_ADD_WINDOW_PROPERTY": 1,
            "IDS_WE_UNABLE_CREATE_WINDOW_PROPERTY": 1,
            "IDS_WE_UNABLE_DESTROY_WINDOW": 2,
            "IDS_WE_UNABLE_DISPLAY_WINDOW_PROPERTIES": 2,
            "IDS_WE_UNABLE_REMOVE_WINDOW_PROPERTY": 1,
            "IDS_WE_UNABLE_UPDATE_WINDOW_PROPERTY": 1,
            "IDS_WE_WINDOW_NOT_FOUND": 2,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

        resource_ids_by_plugin = {
            "HardwareDevices": ("IDS_HD_NO_GRAPHICS_NODES",),
            "NetworkTools": (
                "IDS_NT_GEOLITE_LEGACY_WINDOWS",
                "IDS_NT_UNABLE_DISPLAY_WHOIS",
            ),
            "OnlineChecks": (
                "IDS_OC_REGEX_COMPILE_FAILED",
                "IDS_OC_UNABLE_QUERY_SERVICE",
            ),
            "ToolStatus": (
                "IDS_TS_PROCESS_NOT_FOUND",
                "IDS_TS_UNABLE_DISPLAY_FIND",
            ),
            "Updater": ("IDS_UP_UNABLE_EXECUTE_SETUP",),
            "WindowExplorer": (
                "IDS_WE_UNABLE_ADD_WINDOW_PROPERTY",
                "IDS_WE_UNABLE_CREATE_WINDOW_PROPERTY",
                "IDS_WE_UNABLE_DESTROY_WINDOW",
                "IDS_WE_UNABLE_DISPLAY_WINDOW_PROPERTIES",
                "IDS_WE_UNABLE_REMOVE_WINDOW_PROPERTY",
                "IDS_WE_UNABLE_UPDATE_WINDOW_PROPERTY",
                "IDS_WE_WINDOW_NOT_FOUND",
            ),
        }

        for plugin, resource_ids in resource_ids_by_plugin.items():
            header = (
                REPO_ROOT / "plugins" / plugin / "resource.h"
            ).read_text(encoding="utf-8-sig")
            compiled_definitions = header.split("#ifdef APSTUDIO_INVOKED", 1)[0]

            for resource_id in resource_ids:
                with self.subTest(plugin=plugin, resource_id=resource_id):
                    self.assertRegex(
                        compiled_definitions,
                        rf"(?m)^#define\s+{re.escape(resource_id)}\s+\d+$",
                    )

    def test_updater_launch_installer_owns_an_auto_pool(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "Updater" / "toastmain.c"
        ).read_text(encoding="utf-8-sig")
        launch_body = source.split("VOID UpdaterLaunchInstaller", 1)[1].split(
            "NTSTATUS NTAPI UpdaterToastInstallThread", 1
        )[0]

        initialize = launch_body.index("PhInitializeAutoPool")
        execute = launch_body.index("UpdateShellExecute")
        cleanup = launch_body.index("PhDeleteAutoPool")

        self.assertLess(initialize, execute)
        self.assertLess(execute, cleanup)

    def test_final_main_and_phlib_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        paths = (
            REPO_ROOT / "SystemInformer" / "actions.c",
            REPO_ROOT / "SystemInformer" / "appsup.c",
            REPO_ROOT / "SystemInformer" / "main.c",
            REPO_ROOT / "phlib" / "guisup.c",
            REPO_ROOT / "phlib" / "mapldr.c",
            REPO_ROOT / "phlib" / "util.c",
        )
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in paths
        )
        literals = (
            "Unable to %s %s (PID %lu)",
            "Unable to %s %s",
            'Unable to %s handle \\"%s\\" (%s)%s',
            "Unable to %s handle %s%s",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', source)

        expected_ids = {
            "IDS_PH_ERROR_WITH_DETAILS": 1,
            "IDS_PH_COMMAND_LINE_OPTIONS": 1,
            "IDS_PH_COMMAND_LINE_OPTIONS_CONTENT": 1,
            "IDS_PH_UNABLE_INITIALIZE_DESKTOP_POLICY": 1,
            "IDS_PH_UNABLE_LOAD_SETTINGS": 1,
            "IDS_PH_UNABLE_APPLY_PROCESS_ACTION_PID": 1,
            "IDS_PH_UNABLE_APPLY_PROCESS_ACTION": 1,
            "IDS_PH_UNABLE_APPLY_NAMED_HANDLE_ACTION": 1,
            "IDS_PH_UNABLE_APPLY_HANDLE_ACTION": 1,
            "IDS_PH_UNABLE_LOAD_PLUGIN": 1,
            "IDS_PH_PLUGIN_IMPORT_BY_ORDINAL": 1,
            "IDS_PH_PLUGIN_IMPORT_BY_NAME": 1,
            "IDS_PH_LOCATION_NOT_FOUND": 1,
            "IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT": 1,
            "IDS_PH_ACTION_TERMINATE": 3,
            "IDS_PH_ACTION_SUSPEND": 3,
            "IDS_PH_ACTION_RESUME": 3,
            "IDS_PH_ACTION_FREEZE": 1,
            "IDS_PH_ACTION_THAW": 1,
            "IDS_PH_ACTION_RESTART": 1,
            "IDS_PH_ACTION_DEBUG": 1,
            "IDS_PH_ACTION_REDUCE_WORKING_SET": 1,
            "IDS_PH_ACTION_EMPTY_WORKING_SET": 1,
            "IDS_PH_ACTION_SET_BACKGROUND_ACTIVITY_MODERATION": 1,
            "IDS_PH_ACTION_SET_VIRTUALIZATION": 1,
            "IDS_PH_ACTION_SET_CRITICAL_STATUS": 1,
            "IDS_PH_ACTION_SET_ECO_MODE": 1,
            "IDS_PH_ACTION_CREATE_EXECUTION_REQUIRED": 1,
            "IDS_PH_ACTION_DETACH_DEBUGGER": 1,
            "IDS_PH_ACTION_LOAD_DLL": 1,
            "IDS_PH_ACTION_SET_IO_PRIORITY": 2,
            "IDS_PH_ACTION_SET_PAGE_PRIORITY": 1,
            "IDS_PH_ACTION_SET_PRIORITY_CLASS": 2,
            "IDS_PH_ACTION_CHANGE_BOOST_PRIORITY": 1,
            "IDS_PH_ACTION_SET_BOOST_PRIORITY": 1,
            "IDS_PH_ACTION_FLUSH_PROCESS_HEAPS": 1,
            "IDS_PH_ACTION_CLOSE_HANDLE": 2,
            "IDS_PH_ACTION_SET_HANDLE_ATTRIBUTES": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

        shared_header = REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
        self.assertTrue(shared_header.exists())
        shared_definitions = shared_header.read_text(encoding="utf-8-sig")
        for resource_id in (
            "IDS_PH_UNABLE_LOAD_PLUGIN",
            "IDS_PH_PLUGIN_IMPORT_BY_ORDINAL",
            "IDS_PH_PLUGIN_IMPORT_BY_NAME",
            "IDS_PH_LOCATION_NOT_FOUND",
            "IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT",
        ):
            with self.subTest(shared_resource_id=resource_id):
                self.assertRegex(
                    shared_definitions,
                    rf"(?m)^#define\s+{re.escape(resource_id)}\s+\d+$",
                )

        main_header = (
            REPO_ROOT / "SystemInformer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("#include <phappresourceid.h>", main_header)

        main_source = (
            REPO_ROOT / "SystemInformer" / "main.c"
        ).read_text(encoding="utf-8-sig")
        startup_parameters = main_source[
            main_source.index("VOID PhpProcessStartupParameters("):
            main_source.index("VOID PhpEnablePrivileges(")
        ]
        app_settings = main_source[
            main_source.index("VOID PhInitializeAppSettings("):
            main_source.index("BOOLEAN NTAPI PhpCommandLineOptionCallback(")
        ]
        win_main = main_source[
            main_source.index("INT WINAPI wWinMain("):
            main_source.index("VOID PhRegisterDialog(")
        ]
        self.assertNotIn("PhGetApplicationUiString", startup_parameters)
        self.assertNotIn("PhLoadUiString", startup_parameters)
        self.assertNotIn("PhShowInformation2", startup_parameters)
        self.assertNotIn("PhGetApplicationUiString", app_settings)
        self.assertIn("PhStartupParameters.Help = TRUE;", startup_parameters)
        self.assertRegex(
            app_settings,
            r"PhLoadUiString\s*\([^;]+\bIDS_PH_UNABLE_LOAD_SETTINGS\b[^;]+NULL\s*\)",
        )
        self.assertLess(
            app_settings.index("PhSetApplicationUiLanguage("),
            app_settings.index("IDS_PH_UNABLE_LOAD_SETTINGS"),
        )
        help_safe_error_guard = (
            "if (!PhStartupParameters.NoSettings && !PhStartupParameters.Help)"
        )
        self.assertIn(help_safe_error_guard, app_settings)
        self.assertLess(
            app_settings.index(help_safe_error_guard),
            app_settings.index("PhResetSettingsFile("),
        )
        self.assertLess(
            win_main.index("PhInitializeAppSettings();"),
            win_main.index("PhpInitializeApplicationUiStrings()"),
        )
        self.assertLess(
            win_main.index("PhpInitializeApplicationUiStrings()"),
            win_main.index("if (PhStartupParameters.Help)"),
        )
        help_branch = win_main[win_main.index("if (PhStartupParameters.Help)"):]
        self.assertIn(
            "PhGetApplicationUiString(IDS_PH_COMMAND_LINE_OPTIONS)",
            help_branch,
        )
        self.assertIn(
            "PhGetApplicationUiString(IDS_PH_COMMAND_LINE_OPTIONS_CONTENT)",
            help_branch,
        )

        phconfig = (
            REPO_ROOT / "phlib" / "include" / "phconfig.h"
        ).read_text(encoding="utf-8-sig")
        phglobal = (
            REPO_ROOT / "phlib" / "global.c"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("EXTERN_C PVOID PhApplicationUiResourceInstance;", phconfig)
        self.assertIn("PVOID PhApplicationUiResourceInstance = NULL;", phglobal)
        registration = "PhApplicationUiResourceInstance = PhInstanceHandle;"
        self.assertIn(registration, win_main)
        self.assertLess(
            win_main.index(registration),
            win_main.index("PhpProcessStartupParameters();"),
        )

        phlib_source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (
                REPO_ROOT / "phlib" / "guisup.c",
                REPO_ROOT / "phlib" / "mapldr.c",
                REPO_ROOT / "phlib" / "util.c",
            )
        )
        self.assertNotRegex(
            phlib_source,
            r"PhLoadUiString\s*\([^;]+,\s*L\"",
        )
        self.assertNotRegex(
            phlib_source,
            r"PhLoadUiString\s*\(\s*NtCurrentImageBase\(\)",
        )
        self.assertEqual(
            len(re.findall(r"PhLoadUiString\s*\([^;]+,\s*NULL\s*\)", phlib_source)),
            5,
        )
        self.assertGreaterEqual(
            phlib_source.count("PhApplicationUiResourceInstance"),
            5,
        )
        map_loader = (REPO_ROOT / "phlib" / "mapldr.c").read_text(
            encoding="utf-8-sig"
        )
        self.assertEqual(
            map_loader.count(
                'PhGetStringOrDefault(resourceTitle, L"Unable to load plugin.")'
            ),
            2,
        )
        for resource_id, fallback in (
            ("IDS_PH_PLUGIN_IMPORT_BY_ORDINAL", "Name: %s\\r\\nOrdinal: %u\\r\\nModule: %hs"),
            ("IDS_PH_PLUGIN_IMPORT_BY_NAME", "Name: %s\\r\\nFunction: %hs\\r\\nModule: %hs"),
        ):
            with self.subTest(phlib_format_resource_id=resource_id):
                self.assertRegex(
                    map_loader,
                    rf"(?s){resource_id}(?:(?!IDS_PH_).)*PhGetStringOrDefault\(resourceFormat,\s*L\"{re.escape(fallback)}\"\)",
                )
        self.assertRegex(
            (REPO_ROOT / "phlib" / "util.c").read_text(encoding="utf-8-sig"),
            r'(?s)IDS_PH_LOCATION_NOT_FOUND(?:(?!IDS_PH_).)*PhGetStringOrDefault\(resourceTitle, L"The location could not be found\."\)',
        )
        self.assertRegex(
            (REPO_ROOT / "phlib" / "guisup.c").read_text(encoding="utf-8-sig"),
            r'(?s)IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT(?:(?!IDS_PH_).)*PhGetStringOrDefault\(resourceTitle, L"Unable to create the window context\."\)',
        )

        gui_support = (
            REPO_ROOT / "phlib" / "guisup.c"
        ).read_text(encoding="utf-8-sig")
        fls_failure = gui_support[
            gui_support.index("if (!FlsSetValue(WindowCallbackFlsIndex, hashtable))"):
            gui_support.index("RtlFailFast(FAST_FAIL_INVALID_FLS_DATA);")
        ]
        self.assertLess(
            fls_failure.index("PhGetLastError()"),
            fls_failure.index("PhLoadUiString("),
        )

    def test_main_status_calls_do_not_hide_unresolved_variable_messages(self) -> None:
        audit = load_audit_module()
        unresolved = []

        for path in (REPO_ROOT / "SystemInformer").glob("*.c"):
            source = path.read_text(encoding="utf-8-sig")
            for name, args, spans, call_start in audit.find_calls(
                source, {"PhShowStatus", "PhShowContinueStatus"}
            ):
                if len(args) <= 1:
                    continue
                message = args[1]
                if (
                    audit.first_literal(message) is None
                    and "PhGetApplicationUiString" not in message
                ):
                    unresolved.append(
                        f"{path.name}:{audit.line_of_offset(source, call_start)}:{name}"
                    )

        self.assertEqual(unresolved, [])

    def test_printf_vararg_literals_are_migrated_at_their_callsites(self) -> None:
        audit = load_audit_module()
        unresolved = []

        for path in audit.iter_source_files():
            if not path.endswith((".c", ".cpp")):
                continue
            entries = []
            audit.scan_c_file(path, entries)
            unresolved.extend(
                entry
                for entry in entries
                if entry["category"] == "c_msgbox_vararg"
            )

        self.assertEqual(
            [
                f"{entry['file']}:{entry['line']}:{entry['english']}"
                for entry in unresolved
            ],
            [],
        )

    def test_plugin_vararg_fallbacks_use_native_string_resources(self) -> None:
        extended_services = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "plugins" / "ExtendedServices").glob("*.c")
        )
        user_notes = (
            REPO_ROOT / "plugins" / "UserNotes" / "main.c"
        ).read_text(encoding="utf-8-sig")

        self.assertEqual(extended_services.count("IDS_ES_UNKNOWN_ERROR"), 3)
        self.assertEqual(
            user_notes.count("IDS_UN_AFFINITY_INDIVIDUAL_THREADS"),
            2,
        )

    def test_setup_progress_and_wizard_buttons_use_string_resources(self) -> None:
        setup_sources = {
            path.name: path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "CustomSetupTool").glob("*.c")
        }

        for name in ("install.c", "update.c", "uninstall.c"):
            with self.subTest(source=name):
                self.assertNotRegex(
                    setup_sources[name],
                    r"SetupSetProgressText\([^,]+,\s*L\"",
                )

        wizard = setup_sources["wizard.c"]
        main = setup_sources["main.c"]
        all_setup_source = "\n".join(setup_sources.values())
        setup_resource = (
            REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc"
        ).read_text(encoding="utf-8-sig")
        self.assertEqual(len(stringtable_ids(setup_resource)), 74)
        self.assertNotRegex(
            wizard,
            r"SetupSetWizardButtonText\([^,]+,\s*[^,]+,\s*L\"",
        )
        for literal in (
            'L"Cancel Setup?"',
            'L"Invalid Start Menu folder"',
            'L"Enter a valid Start Menu folder name."',
        ):
            self.assertNotIn(literal, wizard)
        self.assertNotRegex(wizard, r"PhShowStatus\([^,]+,\s*L\"")
        self.assertNotRegex(wizard, r"PhSetDialogItemText\([^,]+,\s*[^,]+,\s*L\"")
        self.assertNotIn('header.pszCaption = L"', wizard)
        self.assertIn("header.pszCaption = PhApplicationName;", wizard)
        self.assertIn(
            "static PPH_STRING SetupUiStrings[IDS_SETUP_LAST - IDS_SETUP_FIRST + 1]",
            main,
        )
        self.assertIn("if (!SetupInitializeUiStrings())", main)
        self.assertIn(
            "PhApplicationName = SetupGetUiString(IDS_SETUP_WINDOW_TITLE);",
            main,
        )
        resource_header = (
            REPO_ROOT / "tools" / "CustomSetupTool" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        self.assertIn(
            "#define IDS_SETUP_FIRST                                 IDS_SETUP_UNINSTALL_COMPLETE",
            resource_header,
        )
        self.assertIn(
            "#define IDS_SETUP_LAST                                  IDS_SETUP_INSTALLATION_FOLDER_FORMAT",
            resource_header,
        )
        numeric_ids = {
            name: int(value)
            for name, value in re.findall(
                r"^#define\s+(IDS_SETUP_[A-Z0-9_]+)\s+(\d+)\s*$",
                resource_header,
                re.MULTILINE,
            )
        }
        first_id = numeric_ids["IDS_SETUP_UNINSTALL_COMPLETE"]
        last_id = numeric_ids["IDS_SETUP_INSTALLATION_FOLDER_FORMAT"]
        loaded_ids = set(re.findall(r"SetupGetUiString\((IDS_SETUP_[A-Z0-9_]+)\)", all_setup_source))
        self.assertTrue(loaded_ids)
        for resource_name in loaded_ids:
            self.assertIn(resource_name, numeric_ids)
            self.assertLessEqual(first_id, numeric_ids[resource_name])
            self.assertLessEqual(numeric_ids[resource_name], last_id)
        self.assertIn("PhLoadUiString(PhInstanceHandle, ResourceId, NULL)", wizard)
        self.assertRegex(
            wizard,
            r"title->Buffer,\s*L\"%s\",\s*content->Buffer",
        )

        for literal in (
            "Hey there, before we continue...",
            "Initializing...",
            "Setup failed with an error.",
            "A free, powerful, multi-purpose tool",
            "Installation Folder:",
            "Preparing to install...",
            "System Informer has been uninstalled.",
            "A reboot is required to complete the uninstall.",
            "Uninstalling System Informer...",
            "Uninstall failed with an error.",
            "Are you sure you want to uninstall System Informer?",
            "Error updating to the latest version.",
        ):
            self.assertNotIn(f'L"{literal}', all_setup_source)

    def test_ci_validates_all_built_plugin_resources(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8-sig"
        )
        target_blocks = re.findall(
            r"\$resourceTargets = @\((.*?)\)\s+"
            r"python tools\\zhcn\\validate_templates\.py @resourceTargets",
            workflow,
            re.DOTALL,
        )

        expected_branch_targets = {
            r"bin\Release64\sys_info.exe",
            r"bin\Release64\peview.exe",
            *(rf"bin\Release64\plugins\{module_name}.dll" for module_name in PLUGIN_MODULES),
        }
        expected_release_targets = expected_branch_targets | {
            r"build\output\systeminformer-build-release-setup.exe",
            r"build\output\systeminformer-build-canary-setup.exe",
        }

        self.assertEqual(len(target_blocks), 2)
        self.assertEqual(set(re.findall(r"'([^']+)'", target_blocks[0])), expected_branch_targets)
        self.assertEqual(set(re.findall(r"'([^']+)'", target_blocks[1])), expected_release_targets)
        self.assertEqual(
            set(re.findall(r"--require-strings-in\s+'([^']+)'", workflow)),
            {
                r"build\output\systeminformer-build-release-setup.exe",
                r"build\output\systeminformer-build-canary-setup.exe",
            },
        )
        self.assertEqual(
            Counter(
                (path, int(count))
                for path, count in re.findall(
                    r"--expect-string-count-in\s+'([^'=]+)=(\d+)'",
                    workflow,
                )
            ),
            Counter(
                {
                    (r"bin\Release64\sys_info.exe", 215): 2,
                    (r"bin\Release64\plugins\ExtendedServices.dll", 15): 2,
                    (r"bin\Release64\plugins\ExtendedTools.dll", 25): 2,
                    (r"bin\Release64\plugins\HardwareDevices.dll", 1): 2,
                    (r"bin\Release64\plugins\NetworkTools.dll", 2): 2,
                    (r"bin\Release64\plugins\OnlineChecks.dll", 2): 2,
                    (r"bin\Release64\plugins\ToolStatus.dll", 2): 2,
                    (r"bin\Release64\plugins\Updater.dll", 1): 2,
                    (r"bin\Release64\plugins\UserNotes.dll", 15): 2,
                    (r"bin\Release64\plugins\WindowExplorer.dll", 7): 2,
                    (r"bin\Release64\peview.exe", 128): 2,
                    (r"build\output\systeminformer-build-release-setup.exe", 74): 1,
                    (r"build\output\systeminformer-build-canary-setup.exe", 74): 1,
                }
            ),
        )

    def test_english_manifest_ignores_generated_localized_resources(self) -> None:
        audit = (REPO_ROOT / "tools" / "zhcn" / "audit.py").read_text(encoding="utf-8")

        self.assertIn('base.endswith(".zh-cn.rc")', audit)


if __name__ == "__main__":
    unittest.main()
