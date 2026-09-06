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


class FontHandleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = read_source("phlib/guisup.c")
        cls.header = read_source("phlib/include/guisup.h")
        cls.main_window = read_source("SystemInformer/mainwnd.c")
        cls.tab_new = read_source("phlib/tabnew.c")
        cls.exports = read_source("SystemInformer/SystemInformer.def")
        cls.production_sources = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for root in ("phlib", "SystemInformer", "plugins")
            for extension in ("*.c", "*.cpp")
            for path in (REPO_ROOT / root).rglob(extension)
        )

    def test_dynamic_ui_fonts_use_the_dpi_aware_system_message_font(self) -> None:
        normal = compact(function_body(self.source, "PhInitializeFont"))
        common = compact(function_body(self.source, "PhCreateCommonFont"))
        message = compact(function_body(self.source, "PhCreateMessageFont"))
        tree = compact(function_body(self.source, "PhCreateTreeWindowFont"))

        self.assertEqual(
            normal,
            "HFONT fontHandle; if (fontHandle = PhCreateMessageFont(WindowDpi)) return fontHandle; return GetStockFont(DEFAULT_GUI_FONT);",
        )
        self.assertNotIn("Microsoft Sans Serif", normal)
        self.assertNotIn("Tahoma", normal)
        self.assertNotIn("ANSI_CHARSET", common)
        self.assertIn(
            "PhGetSystemParametersInfo(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, WindowDpi)",
            common,
        )
        self.assertIn(
            "metrics.lfMessageFont.lfHeight = -PhMultiplyDivideSigned(Size, WindowDpi, 72);",
            common,
        )
        self.assertIn("metrics.lfMessageFont.lfWeight = Weight;", common)
        self.assertIn("CreateFontIndirect(&metrics.lfMessageFont)", common)
        self.assertNotIn("lfFaceName", common)
        self.assertNotIn("lfCharSet", common)
        self.assertNotIn("lfQuality", common)
        self.assertIn(
            "PhGetSystemParametersInfo(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, WindowDpi)",
            message,
        )
        self.assertNotIn("lfFaceName", message)
        self.assertNotIn("lfCharSet", message)
        self.assertNotIn("lfQuality", message)
        self.assertEqual(
            tree,
            'return PhpCreateFontFromSetting(L"Font", WindowDpi, PhCreateMessageFont);',
        )

    def test_explicit_tree_font_setting_and_dpi_refresh_semantics_are_preserved(
        self,
    ) -> None:
        from_setting = compact(function_body(self.source, "PhpCreateFontFromSetting"))
        main_dpi = compact(function_body(self.main_window, "PhMwpOnDpiChanged"))
        application_refresh = compact(
            function_body(self.main_window, "PhMwpOnSettingChange")
        )
        tree_refresh = compact(
            function_body(self.main_window, "PhMwpInvokeUpdateWindowFont")
        )
        tab_window_proc = compact(function_body(self.tab_new, "PhTabNewWndProc"))
        tab_font_refresh = compact(function_body(self.tab_new, "PhTabNewUpdateFont"))

        self.assertLess(
            from_setting.index("CreateFontIndirect(&font)"),
            from_setting.index("Fallback(WindowDpi)"),
        )
        self.assertIn("font.lfQuality = (UCHAR)PhFontQuality;", from_setting)
        self.assertLess(
            main_dpi.index("PhMwpInitializeMetrics(WindowHandle, WindowDpi);"),
            main_dpi.index("PhMwpOnSettingChange(WindowHandle, 0, NULL);"),
        )
        self.assertIn("PhMwpOnSettingChange(WindowHandle, 0, NULL);", main_dpi)
        self.assertIn("PhMwpInvokeUpdateWindowFont(NULL);", main_dpi)
        self.assertIn(
            "PhApplicationFont = PhCreateApplicationFont(LayoutWindowDpi);",
            application_refresh,
        )
        self.assertIn("if (oldFont) DeleteFont(oldFont);", application_refresh)
        self.assertIn("PhCreateTreeWindowFont(LayoutWindowDpi)", tree_refresh)
        self.assertIn("if (oldFont) DeleteFont(oldFont);", tree_refresh)
        self.assertIn(
            "case WM_DPICHANGED_AFTERPARENT: { context->WindowDpi = PhGetWindowDpi(WindowHandle); PhTabNewUpdateFont(context);",
            tab_window_proc,
        )
        self.assertIn(
            "if (Context->Font && Context->OwnFont) DeleteFont(Context->Font);",
            tab_font_refresh,
        )

    def test_monospace_initializer_keeps_real_gdi_handle_fallbacks(self) -> None:
        monospace = compact(function_body(self.source, "PhInitializeMonospaceFont"))

        self.assertIn(
            'if (fontHandle = PhCreateFontHandle(L"Lucida Console", 9, FW_DONTCARE, FF_MODERN, WindowDpi)) return fontHandle; '
            'if (fontHandle = PhCreateFontHandle(L"Courier New", 9, FW_DONTCARE, FF_MODERN, WindowDpi)) return fontHandle; '
            "if (fontHandle = PhCreateFontHandle(NULL, 9, FW_DONTCARE, FF_MODERN, WindowDpi)) return fontHandle;",
            monospace,
        )
        self.assertNotIn("PhCreateFont(", monospace)

    def test_real_handle_helper_keeps_the_createfont_contract(self) -> None:
        body = compact(function_body(self.source, "PhCreateFontHandle"))

        self.assertEqual(
            body,
            "return CreateFont( PhMultiplyDivideSigned(-Size, Dpi, 72), 0, 0, 0, Weight, FALSE, FALSE, FALSE, ANSI_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, PhFontQuality, PitchAndFamily, Name );",
        )

    def test_opaque_font_abi_remains_declared_and_implemented(self) -> None:
        for symbol in (
            "PH_FONT_OBJECT",
            "PhFontObjectHeaderToObject",
            "PhFontObjectToObjectHeader",
            "PhCreateFont",
            "PhReferenceFont",
            "PhDereferenceFont",
        ):
            self.assertIn(symbol, self.header)
            self.assertIn(symbol, self.source)

        create = function_body(self.source, "PhCreateFont")
        reference = function_body(self.source, "PhReferenceFont")
        dereference = function_body(self.source, "PhDereferenceFont")
        self.assertIn("PhCreateFontHandle", create)
        self.assertIn("_InterlockedIncrement", reference)
        self.assertIn("_InterlockedDecrement", dereference)
        self.assertIn("DeleteFont(fontHandle)", dereference)

    def test_opaque_wrapper_has_no_internal_production_callers(self) -> None:
        self.assertEqual(
            len(re.findall(r"\bPhCreateFont\s*\(", self.production_sources)), 1
        )
        self.assertEqual(
            len(re.findall(r"\bPhReferenceFont\s*\(", self.production_sources)), 1
        )
        self.assertEqual(
            len(re.findall(r"\bPhDereferenceFont\s*\(", self.production_sources)), 1
        )

    def test_opaque_exports_keep_their_existing_neighbors(self) -> None:
        self.assertRegex(
            self.exports,
            r"(?m)^\s+PhReferenceDeviceTreeEx\s*$\n^\s+PhReferenceFont\s*$\n^\s+PhReferenceNetworkItem\s*$",
        )
        self.assertRegex(
            self.exports,
            r"(?m)^\s+PhDeleteLayoutManager\s*$\n^\s+PhDereferenceFont\s*$\n^\s+PhDialogBox\s*$",
        )
        for symbol in (
            "PhCreateFont",
            "PhCreateFontHandle",
            "PhReferenceFont",
            "PhDereferenceFont",
        ):
            self.assertEqual(
                len(re.findall(rf"(?m)^\s+{symbol}\s*$", self.exports)), 1
            )

    def test_existing_internal_font_replacement_keeps_gdi_delete_semantics(self) -> None:
        swap = compact(function_body(self.header, "PhSwapReferenceFont"))

        self.assertIn("oldFont = *FontHandle;", swap)
        self.assertIn("*FontHandle = NewFont;", swap)
        self.assertIn("if (oldFont) DeleteFont(oldFont);", swap)


if __name__ == "__main__":
    unittest.main()
