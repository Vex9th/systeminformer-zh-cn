#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "WindowExplorer"
SOURCE_PATH = PLUGIN_ROOT / "wndprp.c"


RESOURCES = (
    ("IDS_WE_NOT_AVAILABLE", 12096, "N/A", "不适用", "strings"),
    ("IDS_WE_UNKNOWN", 12097, "Unknown", "未知", "strings"),
    ("IDS_WE_YES", 12098, "Yes", "是", "native_strings"),
    ("IDS_WE_NO", 12099, "No", "否", "native_strings"),
    ("IDS_WE_DPI_UNAWARE", 12100, "Unaware", "不感知", "native_strings"),
    ("IDS_WE_DPI_SYSTEM_AWARE", 12101, "System aware", "系统感知", "native_strings"),
    ("IDS_WE_DPI_PER_MONITOR_AWARE", 12102, "Per-monitor aware", "每监视器感知", "native_strings"),
    ("IDS_WE_DPI_PER_MONITOR_V2", 12103, "Per-monitor V2", "每监视器 V2", "native_strings"),
    ("IDS_WE_DPI_UNAWARE_GDI_SCALED", 12104, "Unaware (GDI scaled)", "不感知（GDI 缩放）", "native_strings"),
    ("IDS_WE_TRUE", 12105, "true", "是", "native_strings"),
    ("IDS_WE_FALSE", 12106, "false", "否", "native_strings"),
    ("IDS_WE_FAILED_TO_QUERY", 12107, "Failed to query", "查询失败", "native_strings"),
    ("IDS_WE_NO_AUTOMATION_ELEMENT", 12108, "Error: No automation element", "错误：没有自动化元素", "native_strings"),
    ("IDS_WE_UIA_COM_CREATION_FAILED", 12109, "Error: UIA COM creation failed", "错误：UIA COM 创建失败", "native_strings"),
)

RESOURCE_BY_ENGLISH = {english: symbol for symbol, _id, english, _zh, _owner in RESOURCES}

ROUTES = (
    ("PhD3DKMTQueryVidPnExclusiveOwnership", "WINDOW_PROPERTIES_INDEX_D3DKMT_EXCLUSIVE", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfoSymbols", "WINDOW_PROPERTIES_INDEX_WNDPROC", "1", "IDS_WE_UNKNOWN", "Unknown"),
    ("WepRefreshWindowGeneralInfoSymbols", "WINDOW_PROPERTIES_INDEX_DLGPROC", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfoSymbols", "WINDOW_PROPERTIES_INDEX_DLGPROC", "1", "IDS_WE_UNKNOWN", "Unknown"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_RECT", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_CLIENTRECT", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_NORMALRECT", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_UNICODE", "1", "IDS_WE_YES", "Yes"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_UNICODE", "1", "IDS_WE_NO", "No"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_FONTNAME", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_FONTNAME", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_TOPLEVEL", "1", "IDS_WE_YES", "Yes"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_TOPLEVEL", "1", "IDS_WE_NO", "No"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_CLOAKED", "1", "IDS_WE_YES", "Yes"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_CLOAKED", "1", "IDS_WE_NO", "No"),
    ("WepRefreshWindowGeneralInfo", "WINDOW_PROPERTIES_INDEX_IAMID", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowStyles", "WINDOW_PROPERTIES_INDEX_STYLES", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowStyles", "WINDOW_PROPERTIES_INDEX_EXSTYLES", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshClassStyles", "WINDOW_PROPERTIES_INDEX_CLASS_DROPSHADOW", "1", "IDS_WE_YES", "Yes"),
    ("WepRefreshClassStyles", "WINDOW_PROPERTIES_INDEX_CLASS_DROPSHADOW", "1", "IDS_WE_NO", "No"),
    ("WepRefreshClassStyles", "WINDOW_PROPERTIES_INDEX_CLASS_SAVEBITS", "1", "IDS_WE_YES", "Yes"),
    ("WepRefreshClassStyles", "WINDOW_PROPERTIES_INDEX_CLASS_SAVEBITS", "1", "IDS_WE_NO", "No"),
    ("WepRefreshWindowClassInfoSymbols", "WINDOW_PROPERTIES_INDEX_CLASS_WNDPROC", "1", "IDS_WE_UNKNOWN", "Unknown"),
    ("WepRefreshAutomationProvider", "WINDOW_PROPERTIES_INDEX_AUTOMATION", "1", "IDS_WE_YES", "Yes"),
    ("WepRefreshAutomationProvider", "WINDOW_PROPERTIES_INDEX_AUTOMATION", "1", "IDS_WE_NO", "No"),
    ("WepRefreshDpiContext", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshDpiContext", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "1", "IDS_WE_DPI_UNAWARE", "Unaware"),
    ("WepRefreshDpiContext", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "1", "IDS_WE_DPI_SYSTEM_AWARE", "System aware"),
    ("WepRefreshDpiContext", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "1", "IDS_WE_DPI_PER_MONITOR_AWARE", "Per-monitor aware"),
    ("WepRefreshDpiContext", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "1", "IDS_WE_DPI_PER_MONITOR_V2", "Per-monitor V2"),
    ("WepRefreshDpiContext", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "1", "IDS_WE_DPI_UNAWARE_GDI_SCALED", "Unaware (GDI scaled)"),
    ("WepRefreshWindowPropertyStorage", "lvItemIndex", "1", "IDS_WE_UNKNOWN", "Unknown"),
    ("WepQueryWindowAttributes", "lvItemIndex", "2", "IDS_WE_TRUE", "true"),
    ("WepQueryWindowAttributes", "lvItemIndex", "2", "IDS_WE_FALSE", "false"),
    ("WepRefreshWindowUiaProperties", "i", "1", "IDS_WE_NOT_AVAILABLE", "N/A"),
    ("WepRefreshWindowUiaProperties", "i", "1", "IDS_WE_FAILED_TO_QUERY", "Failed to query"),
    ("WepRefreshWindowUiaProperties", "i", "1", "IDS_WE_NO_AUTOMATION_ELEMENT", "Error: No automation element"),
    ("WepRefreshWindowUiaProperties", "i", "1", "IDS_WE_UIA_COM_CREATION_FAILED", "Error: UIA COM creation failed"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("window_text_resource_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
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


def braced_block(source: str, opening: int) -> tuple[str, int]:
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index], index
    raise AssertionError("unterminated block")


def if_else_blocks(source: str, marker: str) -> tuple[str, str]:
    start = source.index(marker)
    opening = source.index("{", start + len(marker))
    if_body, closing = braced_block(source, opening)
    else_match = re.match(r"\s*else\s*\{", source[closing + 1:])
    if else_match is None:
        raise AssertionError(f"else block not found after: {marker}")
    else_opening = closing + 1 + else_match.end() - 1
    else_body, _closing = braced_block(source, else_opening)
    return if_body, else_body


def parse_stringtable(path: pathlib.Path):
    text = path.read_text(encoding="utf-8-sig")
    return dict(re.findall(r'(?m)^\s*(IDS_WE_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text))


class WindowExplorerWindowTextResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = SOURCE_PATH.read_text(encoding="utf-8-sig")

    def test_exact_resource_contract_layers_and_counts(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "WindowExplorer.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "WindowExplorer.zh-cn.rc")
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        self.assertEqual(len(RESOURCES), 14)
        self.assertEqual([row[1] for row in RESOURCES], list(range(12096, 12110)))
        for symbol, resource_id, en, zh, owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                other = "native_strings" if owner == "strings" else "strings"
                self.assertEqual(translations[owner].get(en), zh)
                self.assertNotIn(en, translations[other])

        self.assertFalse(translations["strings"].keys() & translations["native_strings"].keys())
        self.assertEqual(len(english), 168)
        self.assertEqual(len(chinese), 168)
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12168$")
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count(r"plugins\WindowExplorer.dll=168"), 2)
        generator_test = (REPO_ROOT / "tools" / "zhcn" / "tests" / "test_native_resource_generation.py").read_text(encoding="utf-8")
        self.assertIn('self.assertIn("2597 strings", result.stdout)', generator_test)

    def test_helper_owns_loaded_string_until_listview_copies_it(self) -> None:
        body = function_body(self.source, "WepSetListViewSubItemUiString", self.audit)
        load = body.index("text = PhLoadUiString(")
        sink = body.index("PhSetListViewSubItem(")
        release = body.index("PhClearReference(&text);")
        self.assertLess(load, sink)
        self.assertLess(sink, release)
        self.assertRegex(
            body,
            r"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*ResourceId\s*,\s*NULL\s*\)",
        )
        self.assertIn("PhGetStringOrDefault(text, Fallback)", body)

    def test_all_38_routes_keep_exact_function_item_subitem_resource_and_fallback(self) -> None:
        actual = Counter()
        functions = sorted({row[0] for row in ROUTES})
        for function in functions:
            body = function_body(self.source, function, self.audit)
            for _name, args, _spans, _start in self.audit.find_calls(
                body, {"WepSetListViewSubItemUiString"}
            ):
                self.assertEqual(len(args), 5, (function, args))
                item = " ".join(args[1].split())
                subitem = " ".join(args[2].split())
                resource_ids = re.findall(r"\bIDS_WE_[A-Z0-9_]+\b", args[3])
                fallbacks = re.findall(r'L"([^"]*)"', args[4])
                self.assertEqual(len(resource_ids), len(fallbacks), (function, args))
                for resource_id, fallback in zip(resource_ids, fallbacks):
                    actual[(function, item, subitem, resource_id, fallback)] += 1

        self.assertEqual(len(ROUTES), 38)
        self.assertEqual(actual, Counter(ROUTES))

    def test_branch_semantics_bind_boolean_dpi_and_uia_results(self) -> None:
        general = function_body(self.source, "WepRefreshWindowGeneralInfo", self.audit)
        self.assertRegex(
            general,
            r"(?s)if\s*\(IsWindowUnicode\([^)]*\)\).*?"
            r"WINDOW_PROPERTIES_INDEX_UNICODE.*?IDS_WE_YES.*?L\"Yes\".*?"
            r"else.*?WINDOW_PROPERTIES_INDEX_UNICODE.*?IDS_WE_NO.*?L\"No\"",
        )
        for predicate, index in (
            ("WeIsTopLevelWindow", "WINDOW_PROPERTIES_INDEX_TOPLEVEL"),
            ("WeIsWindowCloaked", "WINDOW_PROPERTIES_INDEX_CLOAKED"),
        ):
            self.assertRegex(
                general,
                rf"(?s)if\s*\({predicate}\([^)]*\)\).*?{index}.*?IDS_WE_YES.*?L\"Yes\".*?"
                rf"else.*?{index}.*?IDS_WE_NO.*?L\"No\"",
            )

        class_styles = function_body(self.source, "WepRefreshClassStyles", self.audit)
        for flag, index in (
            ("CS_DROPSHADOW", "WINDOW_PROPERTIES_INDEX_CLASS_DROPSHADOW"),
            ("CS_SAVEBITS", "WINDOW_PROPERTIES_INDEX_CLASS_SAVEBITS"),
        ):
            self.assertRegex(
                class_styles,
                rf"(?s){index}\s*,\s*1\s*,\s*\(Context->ClassInfo\.style\s*&\s*{flag}\)\s*"
                r"\?\s*IDS_WE_YES\s*:\s*IDS_WE_NO\s*,\s*"
                rf"\(Context->ClassInfo\.style\s*&\s*{flag}\)\s*\?\s*L\"Yes\"\s*:\s*L\"No\"",
            )

        automation = function_body(self.source, "WepRefreshAutomationProvider", self.audit)
        self.assertRegex(
            automation,
            r"(?s)if\s*\(WeWindowHasAutomationProvider\([^)]*\)\).*?IDS_WE_YES.*?L\"Yes\""
            r".*?else.*?IDS_WE_NO.*?L\"No\"",
        )

        dpi = function_body(self.source, "WepRefreshDpiContext", self.audit)
        dpi_routes = (
            ("DPI_AWARENESS_CONTEXT_UNAWARE", "IDS_WE_DPI_UNAWARE", "Unaware"),
            ("DPI_AWARENESS_CONTEXT_SYSTEM_AWARE", "IDS_WE_DPI_SYSTEM_AWARE", "System aware"),
            ("DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE", "IDS_WE_DPI_PER_MONITOR_AWARE", "Per-monitor aware"),
            ("DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2", "IDS_WE_DPI_PER_MONITOR_V2", "Per-monitor V2"),
            ("DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED", "IDS_WE_DPI_UNAWARE_GDI_SCALED", "Unaware (GDI scaled)"),
        )
        for context, resource_id, fallback in dpi_routes:
            condition = re.search(
                rf"AreDpiAwarenessContextsEqual_I\(dpiContext\s*,\s*{context}\)\s*\)\s*\{{",
                dpi,
            )
            self.assertIsNotNone(condition, context)
            body, _closing = braced_block(dpi, condition.end() - 1)
            calls = list(self.audit.find_calls(body, {"WepSetListViewSubItemUiString"}))
            self.assertEqual(len(calls), 1, (context, calls))
            self.assertEqual(
                tuple(" ".join(argument.split()) for argument in calls[0][1]),
                (
                    "ListViewHandle",
                    "WINDOW_PROPERTIES_INDEX_DPICONTEXT",
                    "1",
                    resource_id,
                    f'L"{fallback}"',
                ),
            )

        attributes = function_body(self.source, "WepQueryWindowAttributes", self.audit)
        self.assertRegex(
            attributes,
            r"(?s)\*\(PBOOL\)buffer\s*\?\s*IDS_WE_TRUE\s*:\s*IDS_WE_FALSE\s*,\s*"
            r"\*\(PBOOL\)buffer\s*\?\s*L\"true\"\s*:\s*L\"false\"",
        )

        uia = function_body(self.source, "WepRefreshWindowUiaProperties", self.audit)
        uia_branches = (
            ("if (displayString)", "IDS_WE_NOT_AVAILABLE", "N/A"),
            (
                "if (SUCCEEDED(IUIAutomationElement_GetCurrentPropertyValue",
                "IDS_WE_FAILED_TO_QUERY",
                "Failed to query",
            ),
            ("if (SUCCEEDED(hr) && element)", "IDS_WE_NO_AUTOMATION_ELEMENT", "Error: No automation element"),
            ("if (SUCCEEDED(hr) && uia)", "IDS_WE_UIA_COM_CREATION_FAILED", "Error: UIA COM creation failed"),
        )
        for marker, resource_id, fallback in uia_branches:
            if_body, else_body = if_else_blocks(uia, marker)
            calls = list(self.audit.find_calls(else_body, {"WepSetListViewSubItemUiString"}))
            self.assertEqual(len(calls), 1, (marker, calls))
            args = calls[0][1]
            self.assertEqual(" ".join(args[3].split()), resource_id)
            self.assertEqual(" ".join(args[4].split()), f'L"{fallback}"')
            self.assertNotIn(resource_id, if_body)

    def test_migrated_window_texts_leave_fresh_plugin_scan(self) -> None:
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)
        target = set(RESOURCE_BY_ENGLISH)
        remaining = [
            (entry["category"], entry["english"], entry["file"], entry["line"])
            for entry in entries
            if entry["category"] in {"c_window_text", "c_runtime_composed"}
            and entry["english"] in target
        ]
        self.assertEqual(remaining, [])
        technical_formats = {
            entry["english"]
            for entry in entries
            if entry["category"] == "c_runtime_composed"
        }
        self.assertIn("0x%Ix", technical_formats)
        self.assertIn("#%hu", technical_formats)
        self.assertIn("%s (%s)", technical_formats)
        self.assertNotIn("%s (Source: %u, LUID: %08x-%08x)", technical_formats)


if __name__ == "__main__":
    unittest.main()
