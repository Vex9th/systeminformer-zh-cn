#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def read_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")


def function_body(source: str, function_name: str) -> str:
    match = re.search(rf"\b{re.escape(function_name)}\s*\([^;]*?\)\s*\{{", source, re.S)
    if not match:
        raise AssertionError(f"function not found: {function_name}")

    start = match.end() - 1
    depth = 0

    for offset in range(start, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : offset]

    raise AssertionError(f"unterminated function: {function_name}")


def compact(source: str) -> str:
    return re.sub(r"\s+", " ", source).strip()


class ProcessPropertiesTabFontContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = read_source("SystemInformer/procprp.c")

    def test_tab_font_uses_tree_font_setting_and_rebinds_before_delete(self) -> None:
        body = compact(function_body(self.source, "PhpUpdateProcessPropTabFont"))

        self.assertIn("PhPropSheetNewGetTabControl(HostHandle)", body)
        self.assertIn("newFont = PhCreateTreeWindowFont(WindowDpi)", body)
        self.assertIn("if (!newFont) return;", body)

        publish = body.index("PropSheetContext->PropSheetWindowFont = newFont")
        rebind = body.index("SetWindowFont(tabControlHandle, newFont, TRUE)")
        delete = body.index("DeleteFont(oldFont)")
        self.assertLess(publish, rebind)
        self.assertLess(rebind, delete)

    def test_initialization_dpi_refresh_and_cleanup_are_wired(self) -> None:
        initialized = compact(
            function_body(self.source, "PhpProcessPropertiesNewInitialized")
        )
        host = compact(
            function_body(self.source, "PhpProcessPropertiesNewHostWndProc")
        )

        self.assertIn(
            "PhpUpdateProcessPropTabFont(propSheetContext, HostHandle, PhGetWindowDpi(HostHandle));",
            initialized,
        )
        self.assertRegex(
            host,
            r"case WM_DPICHANGED:.*CallWindowProc\(oldWndProc.*"
            r"PhpUpdateProcessPropTabFont\(propSheetContext, WindowHandle, LOWORD\(wParam\)\)",
        )
        self.assertRegex(
            host,
            r"case WM_NCDESTROY:.*DeleteFont\(propSheetContext->PropSheetWindowFont\)",
        )


if __name__ == "__main__":
    unittest.main()
