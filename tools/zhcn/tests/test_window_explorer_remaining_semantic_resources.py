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
    ("IDS_WE_EXCLUSIVE_OWNERSHIP_FORMAT", 12111, "%s (Source: %u, LUID: %08x-%08x)", "%s（源：%u，LUID：%08x-%08x）"),
    ("IDS_WE_ADDRESS_RESOLVING_FORMAT", 12112, "0x%Ix (resolving...)", "0x%Ix（正在解析...）"),
    ("IDS_WE_WINDOW_EXTRA_BYTES_FORMAT", 12113, "%lu bytes (%s) (%s)", "%lu 字节（%s）（%s）"),
    ("IDS_WE_CLASS_EXTRA_BYTES_FORMAT", 12114, "%lu bytes (%s)", "%lu 字节（%s）"),
    ("IDS_WE_UNKNOWN_DPI_CONTEXT_FORMAT", 12115, "Unknown (0x%Ix)", "未知（0x%Ix）"),
    ("IDS_WE_ATTRIBUTE_QUERY_FAILED_FORMAT", 12116, "0x%s (Failed)", "0x%s（失败）"),
    ("IDS_WE_VIDPN_OWNER_UNOWNED", 12117, "Unowned", "未占用"),
    ("IDS_WE_VIDPN_OWNER_SHARED", 12118, "Shared", "共享"),
    ("IDS_WE_VIDPN_OWNER_EXCLUSIVE", 12119, "Exclusive", "独占"),
    ("IDS_WE_VIDPN_OWNER_EXCLUSIVE_GDI", 12120, "Exclusive (GDI)", "独占（GDI）"),
    ("IDS_WE_VIDPN_OWNER_EMULATED", 12121, "Emulated", "模拟"),
)


FORMAT_ROUTES = (
    (
        "PhD3DKMTQueryVidPnExclusiveOwnership",
        "WINDOW_PROPERTIES_INDEX_D3DKMT_EXCLUSIVE",
        "1",
        "IDS_WE_EXCLUSIVE_OWNERSHIP_FORMAT",
        "%s (Source: %u, LUID: %08x-%08x)",
        (
            "ownerTypeText",
            "queryInfo.VidPnSourceId",
            "queryInfo.AdapterLuid.HighPart",
            "queryInfo.AdapterLuid.LowPart",
        ),
    ),
    (
        "WepRefreshWindowGeneralInfoSymbols",
        "WINDOW_PROPERTIES_INDEX_WNDPROC",
        "1",
        "IDS_WE_ADDRESS_RESOLVING_FORMAT",
        "0x%Ix (resolving...)",
        ("Context->WndProc",),
    ),
    (
        "WepRefreshWindowGeneralInfoSymbols",
        "WINDOW_PROPERTIES_INDEX_DLGPROC",
        "1",
        "IDS_WE_ADDRESS_RESOLVING_FORMAT",
        "0x%Ix (resolving...)",
        ("Context->DlgProc",),
    ),
    (
        "WepRefreshWindowGeneralInfo",
        "WINDOW_PROPERTIES_INDEX_WNDEXTRA",
        "1",
        "IDS_WE_WINDOW_EXTRA_BYTES_FORMAT",
        "%lu bytes (%s) (%s)",
        (
            "windowExtra",
            "PhaFormatSize(windowExtra, ULONG_MAX)->Buffer",
            "WeHashWindowExtraBytes(Context->WindowHandle)->Buffer",
        ),
    ),
    (
        "WepRefreshWindowClassInfoSymbols",
        "WINDOW_PROPERTIES_INDEX_CLASS_WNDPROC",
        "1",
        "IDS_WE_ADDRESS_RESOLVING_FORMAT",
        "0x%Ix (resolving...)",
        ("(ULONG_PTR)Context->ClassInfo.lpfnWndProc",),
    ),
    (
        "WepRefreshWindowClassInfo",
        "WINDOW_PROPERTIES_INDEX_CLASS_WNDEXTRA",
        "1",
        "IDS_WE_CLASS_EXTRA_BYTES_FORMAT",
        "%lu bytes (%s)",
        ("classExtra", "PhaFormatSize(classExtra, ULONG_MAX)->Buffer"),
    ),
    (
        "WepRefreshDpiContext",
        "WINDOW_PROPERTIES_INDEX_DPICONTEXT",
        "1",
        "IDS_WE_UNKNOWN_DPI_CONTEXT_FORMAT",
        "Unknown (0x%Ix)",
        ("(ULONG_PTR)dpiContext",),
    ),
    (
        "WepQueryWindowAttributes",
        "lvItemIndex",
        "2",
        "IDS_WE_ATTRIBUTE_QUERY_FAILED_FORMAT",
        "0x%s (Failed)",
        ("value",),
    ),
)


TECHNICAL_FORMATS = {
    "0x%Ix": 15,
    "0x%x": 1,
    "0x%Ix (%s)": 6,
    "%lu (0x%x)": 1,
    "%s (%s)": 1,
    "#%hu": 1,
}


OWNER_ROUTES = (
    ("D3DKMT_VIDPNSOURCEOWNER_UNOWNED", "IDS_WE_VIDPN_OWNER_UNOWNED", "Unowned"),
    ("D3DKMT_VIDPNSOURCEOWNER_SHARED", "IDS_WE_VIDPN_OWNER_SHARED", "Shared"),
    ("D3DKMT_VIDPNSOURCEOWNER_EXCLUSIVE", "IDS_WE_VIDPN_OWNER_EXCLUSIVE", "Exclusive"),
    ("D3DKMT_VIDPNSOURCEOWNER_EXCLUSIVEGDI", "IDS_WE_VIDPN_OWNER_EXCLUSIVE_GDI", "Exclusive (GDI)"),
    ("D3DKMT_VIDPNSOURCEOWNER_EMULATED", "IDS_WE_VIDPN_OWNER_EMULATED", "Emulated"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("window_explorer_semantic_audit", path)
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


def parse_stringtable(path: pathlib.Path):
    text = path.read_text(encoding="utf-8-sig")
    return dict(re.findall(r'(?m)^\s*(IDS_WE_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text))


def normalize(value: str) -> str:
    return " ".join(value.split())


class WindowExplorerRemainingSemanticResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = SOURCE_PATH.read_text(encoding="utf-8-sig")

    def test_exact_resources_ownership_ids_counts_and_aps(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "WindowExplorer.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "WindowExplorer.zh-cn.rc")
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        self.assertEqual([row[1] for row in RESOURCES], list(range(12111, 12122)))
        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(translations["native_strings"].get(en), zh)
                self.assertNotIn(en, translations["strings"])

        self.assertEqual(len(english), 169)
        self.assertEqual(len(chinese), 169)
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12169$")
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count(r"plugins\WindowExplorer.dll=169"), 2)
        self.assertNotIn(r"plugins\WindowExplorer.dll=111", workflow)

    def test_format_helper_has_null_safe_explicit_lifetime(self) -> None:
        body = function_body(self.source, "WepSetListViewSubItemUiFormat", self.audit)
        load = body.index("resourceFormat = PhLoadUiString(")
        fallback = body.index("PhGetStringOrDefault(resourceFormat, Fallback)")
        formatted = body.index("formattedText = PhFormatString_V(")
        sink = body.index("PhSetListViewSubItem(")
        clear_text = body.index("PhClearReference(&formattedText);")
        clear_format = body.index("PhClearReference(&resourceFormat);")

        self.assertLess(load, formatted)
        self.assertLess(formatted, fallback)
        va_start = body.index("va_start(argptr, Fallback);")
        va_end = body.index("va_end(argptr);")
        self.assertLess(va_start, formatted)
        self.assertLess(formatted, va_end)
        self.assertLess(va_end, sink)
        self.assertLess(fallback, sink)
        self.assertLess(sink, clear_text)
        self.assertLess(clear_text, clear_format)
        self.assertEqual(body.count("PhClearReference(&formattedText);"), 1)
        self.assertEqual(body.count("PhClearReference(&resourceFormat);"), 1)
        self.assertIn("PhGetStringOrEmpty(formattedText)", body)
        self.assertIn("va_start(argptr, Fallback);", body)
        self.assertIn("va_end(argptr);", body)
        self.assertNotIn("resourceFormat->Buffer", body)

    def test_all_eight_format_routes_keep_exact_sink_fallback_and_arguments(self) -> None:
        actual = Counter()
        for function in sorted({row[0] for row in FORMAT_ROUTES}):
            body = function_body(self.source, function, self.audit)
            for _name, args, _spans, _start in self.audit.find_calls(
                body, {"WepSetListViewSubItemUiFormat"}
            ):
                self.assertGreaterEqual(len(args), 6, (function, args))
                fallback = re.fullmatch(r'\s*L"([^"]*)"\s*', args[4])
                self.assertIsNotNone(fallback, (function, args))
                actual[
                    (
                        function,
                        normalize(args[1]),
                        normalize(args[2]),
                        normalize(args[3]),
                        fallback.group(1),
                        tuple(normalize(arg) for arg in args[5:]),
                    )
                ] += 1

        self.assertEqual(actual, Counter(FORMAT_ROUTES))

    def test_vidpn_owner_enum_uses_unknown_reuse_and_safe_owned_resource(self) -> None:
        body = function_body(self.source, "PhD3DKMTQueryVidPnExclusiveOwnership", self.audit)
        self.assertRegex(body, r"ownerTypeResourceId\s*=\s*IDS_WE_UNKNOWN\s*;")
        self.assertRegex(body, r'ownerTypeFallback\s*=\s*L"Unknown"\s*;')
        for enum_value, resource_id, fallback in OWNER_ROUTES:
            with self.subTest(enum_value=enum_value):
                self.assertRegex(
                    body,
                    rf"(?s)case\s+{enum_value}\s*:.*?ownerTypeResourceId\s*=\s*{resource_id}\s*;"
                    rf'.*?ownerTypeFallback\s*=\s*L"{re.escape(fallback)}"\s*;.*?break\s*;',
                )

        load = body.index("ownerType = PhLoadUiString(")
        safe = body.index("ownerTypeText = PhGetStringOrDefault(ownerType, ownerTypeFallback);")
        sink = body.index("WepSetListViewSubItemUiFormat(")
        release = body.index("PhClearReference(&ownerType);")
        self.assertLess(load, safe)
        self.assertLess(safe, sink)
        self.assertLess(sink, release)
        self.assertEqual(body.count("ownerType = PhLoadUiString("), 1)
        self.assertEqual(body.count("PhClearReference(&ownerType);"), 1)
        self.assertNotIn("ownerType->Buffer", body)

    def test_pure_technical_formats_remain_at_callsites_and_outside_resources(self) -> None:
        source = self.audit.mask_c_comments(self.source)
        english_values = set(parse_stringtable(PLUGIN_ROOT / "WindowExplorer.rc").values())
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        for value, expected_count in TECHNICAL_FORMATS.items():
            with self.subTest(value=value):
                self.assertEqual(len(re.findall(rf'L"{re.escape(value)}"', source)), expected_count)
                self.assertNotIn(value, english_values)
                self.assertNotIn(value, translations["native_strings"])
                self.assertNotIn(value, translations["strings"])

    def test_fresh_scan_leaves_only_reviewed_technical_formats(self) -> None:
        entries = []
        self.audit.scan_c_file(str(SOURCE_PATH), entries)
        remaining = {
            entry["english"]
            for entry in entries
            if entry["category"] == "c_runtime_composed"
        }
        self.assertEqual(remaining, set(TECHNICAL_FORMATS))

    def test_native_generator_total_is_synchronized(self) -> None:
        generator_test = (REPO_ROOT / "tools" / "zhcn" / "tests" / "test_native_resource_generation.py").read_text(encoding="utf-8")
        self.assertIn('self.assertIn("3235 strings", result.stdout)', generator_test)
        self.assertNotIn('self.assertIn("1726 strings", result.stdout)', generator_test)


if __name__ == "__main__":
    unittest.main()
