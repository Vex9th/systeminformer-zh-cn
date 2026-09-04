#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import struct
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET


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


def wide_string(value: str) -> bytes:
    return value.encode("utf-16-le") + b"\0\0"


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
                fonts = FONT_RE.findall(localized)

                self.assertGreater(len(source_ids), 0)
                self.assertEqual(localized_ids, source_ids)
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

    def test_english_manifest_ignores_generated_localized_resources(self) -> None:
        audit = (REPO_ROOT / "tools" / "zhcn" / "audit.py").read_text(encoding="utf-8")

        self.assertIn('base.endswith(".zh-cn.rc")', audit)


if __name__ == "__main__":
    unittest.main()
