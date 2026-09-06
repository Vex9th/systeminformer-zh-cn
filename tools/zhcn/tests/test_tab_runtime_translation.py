import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def function_body(source: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening_brace = source.find("{", match.start())
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1:index]

    raise AssertionError(f"unterminated function: {name}")


class TabRuntimeTranslationTests(unittest.TestCase):
    def source(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")

    def test_custom_tab_insert_passes_raw_text_to_immediate_copy(self) -> None:
        source = self.source("phlib/tabnew.c")
        message_handler = function_body(source, "PhTabNewOnUserMessage")
        insert_item = function_body(source, "PhTabNewInsertItem")
        insert_case_match = re.search(
            r"case\s+TCM_INSERTITEMW\s*:(.*?)case\s+TCM_ADJUSTRECT\s*:",
            message_handler,
            re.DOTALL,
        )

        self.assertIsNotNone(insert_case_match)
        insert_case = insert_case_match.group(1)
        self.assertRegex(
            insert_case,
            r"ins\.Text\s*=\s*\(tci\s*&&\s*\(tci->mask\s*&\s*TCIF_TEXT\)\)\s*"
            r"\?\s*tci->pszText\s*:\s*L\"\"\s*;",
        )
        self.assertNotIn("PhTranslateString", insert_case)
        self.assertRegex(
            insert_case,
            r"PhTabNewInsertItem\s*\(\s*Context\s*,\s*\(LONG\)WParam\s*,\s*&ins\s*\)",
        )
        self.assertRegex(
            insert_item,
            r"if\s*\(\s*InsertItem->Text\s*\)\s*"
            r"item->Text\s*=\s*PhCreateString\s*\(\s*InsertItem->Text\s*\)\s*;",
        )
        self.assertNotIn("PhTranslateString(", source)
        self.assertNotIn("#include <phtranslation.h>", source)

    def test_native_tab_helper_passes_raw_text_to_win32(self) -> None:
        source = self.source("phlib/guisup.c")
        add_tab = function_body(source, "PhAddTabControlTab")

        self.assertRegex(
            add_tab,
            r"item\.pszText\s*=\s*\(PWSTR\)Text\s*;",
        )
        self.assertNotIn("PhTranslateString", add_tab)
        self.assertRegex(
            add_tab,
            r"return\s+TabCtrl_InsertItem\s*\(\s*TabControlHandle\s*,\s*Index\s*,\s*&item\s*\)\s*;",
        )
        self.assertNotIn("PhTranslateString(", source)
        self.assertNotIn("#include <phtranslation.h>", source)

    def test_public_signature_and_export_position_are_unchanged(self) -> None:
        header = self.source("phlib/include/guisup.h")
        exports = [
            line.strip()
            for line in self.source("SystemInformer/SystemInformer.def").splitlines()
            if line.strip() and not line.lstrip().startswith(";")
        ]

        self.assertRegex(
            header,
            r"PHLIBAPI\s+LONG\s+NTAPI\s+PhAddTabControlTab\s*\(\s*"
            r"_In_\s+HWND\s+TabControlHandle\s*,\s*"
            r"_In_\s+LONG\s+Index\s*,\s*"
            r"_In_\s+PCWSTR\s+Text\s*\)\s*;",
        )
        self.assertEqual(exports.count("PhAddTabControlTab"), 1)
        self.assertEqual(exports.index("PhAddTabControlTab"), 948)
        self.assertEqual(
            exports[945:952],
            [
                "PhAddListViewGroup",
                "PhAddListViewGroupItem",
                "PhAddListViewItem",
                "PhAddTabControlTab",
                "PhBitmapSetAlpha",
                "PhCloseThemeData",
                "PhCreateApplicationFont",
            ],
        )


if __name__ == "__main__":
    unittest.main()
