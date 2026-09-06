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
        cls.exports = read_source("SystemInformer/SystemInformer.def")
        cls.production_sources = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for root in ("phlib", "SystemInformer", "plugins")
            for extension in ("*.c", "*.cpp")
            for path in (REPO_ROOT / root).rglob(extension)
        )

    def test_internal_initializers_use_real_gdi_handles_and_keep_fallbacks(self) -> None:
        normal = compact(function_body(self.source, "PhInitializeFont"))
        monospace = compact(function_body(self.source, "PhInitializeMonospaceFont"))

        self.assertIn(
            'if (fontHandle = PhCreateFontHandle(L"Microsoft Sans Serif", 8, FW_NORMAL, DEFAULT_PITCH, WindowDpi)) return fontHandle; '
            'if (fontHandle = PhCreateFontHandle(L"Tahoma", 8, FW_NORMAL, DEFAULT_PITCH, WindowDpi)) return fontHandle; '
            "if (fontHandle = PhCreateMessageFont(WindowDpi)) return fontHandle;",
            normal,
        )
        self.assertIn(
            'if (fontHandle = PhCreateFontHandle(L"Lucida Console", 9, FW_DONTCARE, FF_MODERN, WindowDpi)) return fontHandle; '
            'if (fontHandle = PhCreateFontHandle(L"Courier New", 9, FW_DONTCARE, FF_MODERN, WindowDpi)) return fontHandle; '
            "if (fontHandle = PhCreateFontHandle(NULL, 9, FW_DONTCARE, FF_MODERN, WindowDpi)) return fontHandle;",
            monospace,
        )
        self.assertNotIn("PhCreateFont(", normal)
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
