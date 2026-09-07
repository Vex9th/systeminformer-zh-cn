#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
RESOURCE_DATA = (
    ("IDS_PH_EXTLV_SIZE_COLUMN_TO_FIT", 2857, "Size column to fit", "自动调整列宽"),
    ("IDS_PH_EXTLV_SIZE_ALL_COLUMNS_TO_FIT", 2858, "Size all columns to fit", "自动调整所有列宽"),
    ("IDS_PH_EXTLV_RESET_SORT", 2859, "Reset sort", "重置排序"),
    ("IDS_PH_SEARCH_UNDO", 2860, "Undo", "撤销"),
    ("IDS_PH_SEARCH_CUT", 2861, "Cut", "剪切"),
    ("IDS_PH_SEARCH_COPY", 2862, "Copy", "复制"),
    ("IDS_PH_SEARCH_PASTE", 2863, "Paste", "粘贴"),
    ("IDS_PH_SEARCH_DELETE", 2864, "Delete", "删除"),
    ("IDS_PH_SEARCH_SELECT_ALL", 2865, "Select All", "全选"),
    ("IDS_PH_SEARCH_REGULAR_EXPRESSION", 2866, "Regular Expression", "正则表达式"),
    ("IDS_PH_SEARCH_MATCH_CASE", 2867, "Match Case", "区分大小写"),
    ("IDS_PH_SEARCH_CLEAR_SEARCH", 2868, "Clear Search", "清除搜索"),
    ("IDS_PH_DONT_SHOW_THIS_MESSAGE_AGAIN", 2869, "Don't show this message again", "不再显示此消息"),
    ("IDS_PH_CONFIRM_ACTION_FORMAT", 2870, "Do you want to %s?", "确定要%s吗？"),
    ("IDS_PH_CONFIRM_ACTION_FALLBACK_FORMAT", 2871, "Are you sure you want to %s?", "确定要%s吗？"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("phlib_native_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class PhlibRuntimeNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: cls.audit.mask_c_comments(
                (REPO_ROOT / "phlib" / name).read_text(encoding="utf-8-sig")
            )
            for name in ("extlv.c", "searchbox.c", "util.c", "mapldr.c", "guisup.c")
        }

    def test_resources_are_contiguous_bilingual_and_exported_to_phlib(self) -> None:
        root = REPO_ROOT / "SystemInformer"
        header = (root / "resource.h").read_text(encoding="utf-8-sig")
        phlib_ids = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(root / "SystemInformer.rc")
        chinese = parse_stringtable(root / "SystemInformer.zh-cn.rc")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)$",
                header,
            )
        }

        self.assertEqual([row[1] for row in RESOURCE_DATA], list(range(2857, 2872)))
        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertRegex(
                    phlib_ids,
                    rf"(?m)^#define\s+{symbol}\s+{resource_id}$",
                )

        reused = {
            "IDS_PH_UNABLE_PERFORM_OPERATION": 2027,
            "IDS_PH_UNABLE_EXECUTE_PROGRAM": 2151,
            "IDS_PH_CANCEL": 2331,
            "IDS_PH_SERVICE_PROGRESS_CONFIRM_CONTENT_FORMAT": 2617,
        }
        for symbol, resource_id in reused.items():
            with self.subTest(reused=symbol):
                self.assertRegex(
                    phlib_ids,
                    rf"(?m)^#define\s+{symbol}\s+{resource_id}$",
                )

        self.assertEqual(len(english), 1340)
        self.assertEqual(len(chinese), 1340)
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_STRINGS$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3340$")

    def test_extended_list_view_menu_uses_owned_resource_text_with_fallback(self) -> None:
        source = self.sources["extlv.c"]
        self.assertIn("#include <phappresourceid.h>", source)
        self.assertIn("PhApplicationUiResourceInstance", source)
        self.assertIn("PhLoadUiString(", source)
        self.assertIn("PhDuplicateStringZ(PhGetStringOrDefault(resourceText, FallbackText))", source)
        self.assertIn("Flags | PH_EMENU_TEXT_OWNED", source)

        routes = {
            "1": "IDS_PH_EXTLV_SIZE_COLUMN_TO_FIT",
            "2": "IDS_PH_EXTLV_SIZE_ALL_COLUMNS_TO_FIT",
            "3": "IDS_PH_EXTLV_RESET_SORT",
        }
        for command_id, resource_id in routes.items():
            with self.subTest(command_id=command_id):
                self.assertRegex(
                    source,
                    rf"PhpCreateApplicationResourceEMenuItem\(0,\s*{command_id},\s*{resource_id},",
                )

        entries = []
        self.audit.scan_c_file(str(REPO_ROOT / "phlib" / "extlv.c"), entries)
        self.assertEqual([entry for entry in entries if entry["category"] == "c_emenu"], [])

    def test_search_menu_and_tooltips_use_native_resources_without_dropping_banner_compatibility(self) -> None:
        source = self.sources["searchbox.c"]
        self.assertIn("PPH_STRING TooltipText;", source)
        self.assertRegex(source, r"PhMoveReference\(\s*&Button->TooltipText")
        self.assertIn("PhClearReference(&context->RegexButton.TooltipText)", source)
        self.assertIn("PhClearReference(&context->CaseButton.TooltipText)", source)
        self.assertIn("PhClearReference(&context->SearchButton.TooltipText)", source)

        menu_routes = {
            1: "IDS_PH_SEARCH_UNDO",
            2: "IDS_PH_SEARCH_CUT",
            3: "IDS_PH_SEARCH_COPY",
            4: "IDS_PH_SEARCH_PASTE",
            5: "IDS_PH_SEARCH_DELETE",
            6: "IDS_PH_SEARCH_SELECT_ALL",
        }
        for command_id, resource_id in menu_routes.items():
            with self.subTest(command_id=command_id):
                self.assertRegex(
                    source,
                    rf"PhpCreateSearchResourceEMenuItem\(0,\s*{command_id},\s*{resource_id},",
                )

        for resource_id in (
            "IDS_PH_SEARCH_REGULAR_EXPRESSION",
            "IDS_PH_SEARCH_MATCH_CASE",
            "IDS_PH_SEARCH_CLEAR_SEARCH",
        ):
            self.assertRegex(
                source,
                rf"PhpSearchControlCreateTooltip\([^;]*\b{resource_id}\b",
            )

        self.assertIn("PhCreateString(PhTranslateString(BannerText))", source)
        entries = []
        self.audit.scan_c_file(str(REPO_ROOT / "phlib" / "searchbox.c"), entries)
        self.assertEqual([entry for entry in entries if entry["category"] == "c_emenu"], [])

    def test_util_fixed_ui_uses_resources_while_generic_translation_contract_remains(self) -> None:
        source = self.sources["util.c"]
        for literal in (
            "Unable to perform the operation.",
            "Unable to execute the program.",
            "Don't show this message again",
            "Do you want to ",
            " Are you sure you want to continue?",
            "Are you sure you want to %s?",
        ):
            self.assertNotRegex(
                source,
                rf"PhTranslateString\(L{re.escape(chr(34) + literal + chr(34))}\)",
            )

        for resource_id in (
            "IDS_PH_UNABLE_PERFORM_OPERATION",
            "IDS_PH_UNABLE_EXECUTE_PROGRAM",
            "IDS_PH_DONT_SHOW_THIS_MESSAGE_AGAIN",
            "IDS_PH_CONFIRM_ACTION_FORMAT",
            "IDS_PH_SERVICE_PROGRESS_CONFIRM_CONTENT_FORMAT",
            "IDS_PH_CANCEL",
            "IDS_PH_CONFIRM_ACTION_FALLBACK_FORMAT",
        ):
            self.assertIn(resource_id, source)

        # Generic format/title funnels remain, but confirmation arguments are native
        # resources or already-formatted dynamic text and must not hit the dictionary.
        self.assertIn("PhFormatString_V(PhTranslateString(Format), argptr)", source)
        self.assertIn("Config->pszWindowTitle = PhTranslateString(Config->pszWindowTitle)", source)
        self.assertNotIn("PhTranslateString(Verb)", source)
        self.assertNotIn("PhTranslateString(Object)", source)
        self.assertNotIn("PhTranslateString(Message)", source)
        self.assertNotIn("TranslateObject", source)

        entries = []
        self.audit.scan_c_file(str(REPO_ROOT / "phlib" / "util.c"), entries)
        runtime = [
            entry for entry in entries
            if entry["category"] in {"c_msgbox", "c_taskdialog"}
        ]
        self.assertEqual([], runtime)
        self.assertEqual(
            [entry for entry in entries if entry["category"] == "phlib_internal"],
            [],
        )

    def test_existing_shared_library_fallbacks_remain_explicit(self) -> None:
        expected = {
            "mapldr.c": (
                "IDS_PH_UNABLE_LOAD_PLUGIN",
                'L"Unable to load plugin."',
            ),
            "guisup.c": (
                "IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT",
                'L"Unable to create the window context."',
            ),
        }
        for name, (resource_id, fallback) in expected.items():
            with self.subTest(source=name):
                source = self.sources[name]
                self.assertIn("PhApplicationUiResourceInstance", source)
                self.assertIn("PhLoadUiString(", source)
                self.assertIn(resource_id, source)
                self.assertIn(fallback, source)


if __name__ == "__main__":
    unittest.main()
