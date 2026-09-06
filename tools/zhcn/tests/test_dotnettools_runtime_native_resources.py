#!/usr/bin/env python3
"""Regression coverage for DotNetTools runtime UI native resources."""

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "DotNetTools"
CATEGORIES = {"c_emenu", "c_listview_col", "c_search", "c_treenew_col"}


RESOURCE_DATA = (
    ("IDS_DN_MENU_INSPECT", 2089, "&Inspect", "检查(&I)"),
    ("IDS_DN_MENU_INSPECT_NATIVE_IMAGE", 2090, "Inspect native image", "检查本机映像"),
    ("IDS_DN_MENU_OPEN_FILE_LOCATION", 2091, "Open &file location", "打开文件位置(&F)"),
    ("IDS_DN_MENU_OPEN_NATIVE_FILE_LOCATION", 2092, "Open native file location", "打开本机映像文件位置"),
    ("IDS_DN_MENU_COPY", 2093, "&Copy", "复制(&C)"),
    ("IDS_DN_COLUMN_STRUCTURE", 2094, "Structure", "结构"),
    ("IDS_DN_COLUMN_ADDRESS", 2095, "Address", "地址"),
    ("IDS_DN_COLUMN_FLAGS", 2096, "Flags", "标志"),
    ("IDS_DN_COLUMN_FILE_NAME", 2097, "File name", "文件名"),
    ("IDS_DN_COLUMN_NATIVE_IMAGE_PATH", 2098, "Native image path", "本机映像路径"),
    ("IDS_DN_COLUMN_BASE_ADDRESS", 2099, "Base address", "基址"),
    ("IDS_DN_COLUMN_MVID", 2100, "MVID", "MVID"),
    ("IDS_DN_SEARCH_ASSEMBLIES", 2101, "Search Assemblies (Ctrl+K)", "搜索程序集 (Ctrl+K)"),
    ("IDS_DN_MENU_HIDE_DYNAMIC", 2102, "Hide dynamic", "隐藏动态模块"),
    ("IDS_DN_MENU_HIDE_NATIVE", 2103, "Hide native", "隐藏本机映像"),
    ("IDS_DN_MENU_HIGHLIGHT_DYNAMIC", 2104, "Highlight dynamic", "高亮动态程序集"),
    ("IDS_DN_MENU_HIGHLIGHT_NATIVE", 2105, "Highlight native", "高亮本机映像"),
    ("IDS_DN_COLUMN_COUNTER", 2106, "Counter", "计数器"),
    ("IDS_DN_COLUMN_VALUE", 2107, "Value", "值"),
)


ASM_CONTEXT_MENU = (
    ("ID_CLR_INSPECT", "IDS_DN_MENU_INSPECT"),
    ("ID_CLR_INSPECTNATIVE", "IDS_DN_MENU_INSPECT_NATIVE_IMAGE"),
    ("ID_CLR_OPENFILELOCATION", "IDS_DN_MENU_OPEN_FILE_LOCATION"),
    ("ID_CLR_OPENNATIVELOCATION", "IDS_DN_MENU_OPEN_NATIVE_FILE_LOCATION"),
    ("ID_CLR_COPY", "IDS_DN_MENU_COPY"),
)


ASM_COLUMNS = (
    ("DNATNC_STRUCTURE", "IDS_DN_COLUMN_STRUCTURE"),
    ("DNATNC_ADDRESS", "IDS_DN_COLUMN_ADDRESS"),
    ("DNATNC_FLAGS", "IDS_DN_COLUMN_FLAGS"),
    ("DNATNC_PATH", "IDS_DN_COLUMN_FILE_NAME"),
    ("DNATNC_NATIVEPATH", "IDS_DN_COLUMN_NATIVE_IMAGE_PATH"),
    ("DNATNC_BASEADDRESS", "IDS_DN_COLUMN_BASE_ADDRESS"),
    ("DNATNC_MVID", "IDS_DN_COLUMN_MVID"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("dotnettools_runtime_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.S)
    if match is None:
        raise AssertionError(f"function not found: {name}")
    opening = source.find("{", match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated function: {name}")


def parse_stringtable(path: pathlib.Path):
    return {
        symbol: value.replace('""', '"').replace(r"\n", "\n")
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_DN_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


def auto_getter(resource: str) -> str:
    return (
        r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
        rf"PluginInstance->DllBase\s*,\s*{resource}\s*,\s*NULL\s*\)\)\)"
    )


class DotNetToolsRuntimeNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit_module()
        cls.sources = {
            path.name: cls.audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in PLUGIN_ROOT.glob("*.c")
        }

    def test_resources_are_exact_contiguous_and_preserve_shortcuts(self):
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_DN_[A-Z0-9_]+)\s+(\d+)$",
                header,
            )
        }
        english = parse_stringtable(PLUGIN_ROOT / "DotNetTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "DotNetTools.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCE_DATA], list(range(2089, 2108)))
        self.assertEqual(sorted(defines.values()), list(range(2000, 2113)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 113)
        self.assertEqual(len(chinese), 113)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2113$")
        self.assertEqual(english["IDS_DN_MENU_INSPECT"].count("&"), 1)
        self.assertEqual(english["IDS_DN_MENU_OPEN_FILE_LOCATION"].count("&"), 1)
        self.assertEqual(english["IDS_DN_MENU_COPY"].count("&"), 1)
        self.assertIn("Ctrl+K", english["IDS_DN_SEARCH_ASSEMBLIES"])
        self.assertIn("Ctrl+K", chinese["IDS_DN_SEARCH_ASSEMBLIES"])

    def test_assembly_page_uses_persistent_cache_and_exact_routes(self):
        source = self.sources["asmpage.c"]
        helper = function_body(source, "DotNetAsmGetUiString")
        self.assertRegex(source, r"static\s+PH_INITONCE\s+DotNetAsmUiStringsInitOnce\s*=\s*PH_INITONCE_INIT\s*;")
        self.assertRegex(
            source,
            r"static\s+PPH_STRING\s+DotNetAsmUiStrings\s*\[\s*"
            r"IDS_DN_MENU_HIGHLIGHT_NATIVE\s*-\s*IDS_DN_MENU_INSPECT\s*\+\s*1\s*\]\s*;",
        )
        self.assertRegex(helper, r"ResourceId\s*<\s*IDS_DN_MENU_INSPECT\s*\|\|\s*ResourceId\s*>\s*IDS_DN_MENU_HIGHLIGHT_NATIVE")
        self.assertRegex(helper, r"PhBeginInitOnce\(&DotNetAsmUiStringsInitOnce\)")
        self.assertRegex(helper, r"for\s*\(ULONG resourceId\s*=\s*IDS_DN_MENU_INSPECT\s*;\s*resourceId\s*<=\s*IDS_DN_MENU_HIGHLIGHT_NATIVE\s*;\s*resourceId\+\+\)")
        self.assertRegex(helper, r"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*resourceId\s*,\s*NULL\s*\)")
        self.assertRegex(helper, r"PhEndInitOnce\(&DotNetAsmUiStringsInitOnce\)")
        self.assertRegex(helper, r"return\s+PhGetStringOrEmpty\(DotNetAsmUiStrings\[ResourceId\s*-\s*IDS_DN_MENU_INSPECT\]\)\s*;")

        menu = function_body(source, "DotNetAsmShowContextMenu")
        actual_menu = tuple(re.findall(
            r"PhCreateEMenuItem\(\s*0\s*,\s*([A-Z0-9_]+)\s*,\s*"
            r"DotNetAsmGetUiString\((IDS_DN_[A-Z0-9_]+)\)",
            menu,
            re.S,
        ))
        self.assertEqual(actual_menu, ASM_CONTEXT_MENU)

        tree = function_body(source, "DotNetAsmInitializeTreeList")
        actual_columns = tuple(re.findall(
            r"PhAddTreeNewColumn\(\s*Context->TreeNewHandle\s*,\s*([A-Z0-9_]+)\s*,[^,]+,\s*"
            r"DotNetAsmGetUiString\((IDS_DN_[A-Z0-9_]+)\)",
            tree,
            re.S,
        ))
        self.assertEqual(actual_columns, ASM_COLUMNS)

        page = function_body(source, "DotNetAsmPageDlgProc")
        self.assertRegex(page, r"PhCreateSearchControl\([^;]*DotNetAsmGetUiString\(IDS_DN_SEARCH_ASSEMBLIES\)", re.S)
        option_routes = tuple(re.findall(
            r"PhCreateEMenuItem\(\s*0\s*,\s*(DN_ASM_MENU_[A-Z0-9_]+)\s*,\s*"
            r"DotNetAsmGetUiString\((IDS_DN_[A-Z0-9_]+)\)",
            page,
            re.S,
        ))
        self.assertEqual(option_routes, (
            ("DN_ASM_MENU_HIDE_DYNAMIC_OPTION", "IDS_DN_MENU_HIDE_DYNAMIC"),
            ("DN_ASM_MENU_HIDE_NATIVE_OPTION", "IDS_DN_MENU_HIDE_NATIVE"),
            ("DN_ASM_MENU_HIGHLIGHT_DYNAMIC_OPTION", "IDS_DN_MENU_HIGHLIGHT_DYNAMIC"),
            ("DN_ASM_MENU_HIGHLIGHT_NATIVE_OPTION", "IDS_DN_MENU_HIGHLIGHT_NATIVE"),
        ))

    def test_performance_page_uses_exact_resource_routes(self):
        source = self.sources["perfpage.c"]
        page = function_body(source, "DotNetPerfPageDlgProc")
        self.assertRegex(page, r"PhAddListViewColumn\([^;]*" + auto_getter("IDS_DN_COLUMN_COUNTER") + r"\s*\)\s*;", re.S)
        self.assertRegex(page, r"PhAddListViewColumn\([^;]*" + auto_getter("IDS_DN_COLUMN_VALUE") + r"\s*\)\s*;", re.S)
        self.assertRegex(
            page,
            r"PhCreateEMenuItem\(\s*0\s*,\s*ID_CLR_COPY\s*,\s*"
            + auto_getter("IDS_DN_MENU_COPY")
            + r"\s*,\s*NULL\s*,\s*NULL\s*\)",
        )

    def test_target_literals_leave_all_four_fresh_categories(self):
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)
        remaining = Counter(
            (entry["category"], entry["english"], entry["file"])
            for entry in entries
            if entry["category"] in CATEGORIES
        )
        self.assertEqual(remaining, Counter())

        source = "\n".join(self.sources.values())
        for _symbol, _resource_id, english, _chinese in RESOURCE_DATA:
            with self.subTest(english=english):
                self.assertNotIn(f'L"{english}"', source)


if __name__ == "__main__":
    unittest.main()
