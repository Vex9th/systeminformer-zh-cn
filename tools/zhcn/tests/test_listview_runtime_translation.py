import importlib.util
import pathlib
import re
import tempfile
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "listview_runtime_translation_audit", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
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


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


class ListViewRuntimeTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def source(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")

    def calls(self, relative_path: str, function_name: str):
        source = self.audit.mask_c_comments(self.source(relative_path))
        return [
            tuple(compact(argument) for argument in arguments)
            for name, arguments, _, _ in self.audit.find_calls(
                source, {function_name}
            )
            if name == function_name
        ]

    def test_legacy_and_raw_helpers_share_one_private_insert_implementation(self) -> None:
        source = self.source("phlib/guisuplistview.cpp")
        private_body = function_body(source, "PhpAddListViewItem", self.audit)
        legacy_body = function_body(source, "PhAddListViewItem", self.audit)
        raw_body = function_body(source, "PhAddListViewItemRaw", self.audit)

        self.assertEqual(private_body.count("PhTranslateString("), 0)
        self.assertNotIn("Translate", private_body)
        private_compact = compact(private_body)
        for statement in (
            "item.mask=LVIF_TEXT|LVIF_PARAM;",
            "item.iItem=Index;",
            "item.iSubItem=0;",
            "item.pszText=const_cast<PWSTR>(Text);",
            "item.lParam=reinterpret_cast<LPARAM>(Param);",
            "returnListView_InsertItem(ListViewHandle,&item);",
        ):
            with self.subTest(private_insert_statement=statement):
                self.assertIn(statement, private_compact)
        self.assertNotIn("ListView_InsertItem", legacy_body)
        self.assertRegex(
            legacy_body,
            r"PhpAddListViewItem\s*\(\s*ListViewHandle\s*,\s*Index\s*,\s*Text\s*,\s*Param\s*\)",
        )
        self.assertNotIn("PhTranslateString", raw_body)
        self.assertNotIn("ListView_InsertItem", raw_body)
        self.assertRegex(
            raw_body,
            r"PhpAddListViewItem\s*\(\s*ListViewHandle\s*,\s*Index\s*,\s*Text\s*,\s*Param\s*\)",
        )

    def test_raw_helper_is_declared_and_appended_to_exports(self) -> None:
        header = self.audit.mask_c_comments(self.source("phlib/include/guisup.h"))
        exports = [
            line.strip()
            for line in self.source("SystemInformer/SystemInformer.def").splitlines()
            if line.strip() and not line.lstrip().startswith(";")
        ]

        self.assertRegex(
            header,
            r"PHLIBAPI\s+LONG\s+NTAPI\s+PhAddListViewItemRaw\s*\(\s*"
            r"_In_\s+HWND\s+ListViewHandle\s*,\s*"
            r"_In_\s+LONG\s+Index\s*,\s*"
            r"_In_\s+PCWSTR\s+Text\s*,\s*"
            r"_In_opt_\s+PVOID\s+Param\s*\)\s*;",
        )
        self.assertEqual(exports.count("PhAddListViewItemRaw"), 1)
        self.assertEqual(exports[-1], "PhAddListViewItemRaw")

    def test_exactly_thirteen_runtime_first_column_calls_use_raw_helper(self) -> None:
        expected = {
            "SystemInformer/colsetmgr.c": [
                (
                    "context->ListViewHandle",
                    "MAXINT",
                    "entry->Name->Buffer",
                    "entry",
                )
            ],
            "SystemInformer/srvctl.c": [
                (
                    "context->ListViewHandle",
                    "MAXINT",
                    "serviceItem->Name->Buffer",
                    "serviceItem",
                )
            ],
            "SystemInformer/pagfiles.c": [
                ("ListViewHandle", "MAXINT", "newFileName->Buffer", "NULL"),
                ("ListViewHandle", "MAXINT", "newFileName->Buffer", "NULL"),
            ],
            "SystemInformer/jobprp.c": [
                ("processesLv", "MAXINT", "PhGetString(name)", "NULL")
            ],
            "SystemInformer/envdlg.c": [
                (
                    "Context->ListViewHandle",
                    "MAXINT",
                    "text->Buffer",
                    "NULL",
                ),
                ("ListViewHandle", "target", "PhGetString(text)", "NULL"),
                (
                    "context->ListViewHandle",
                    "MAXINT",
                    "text->Buffer",
                    "NULL",
                ),
                (
                    "context->ListViewHandle",
                    "MAXINT",
                    "fileName->Buffer",
                    "NULL",
                ),
            ],
            "SystemInformer/plugman.c": [
                (
                    "Context->ListViewHandle",
                    "MAXINT",
                    "PhGetString(displayText)",
                    "displayText",
                )
            ],
            "plugins/WindowExplorer/wndprp.c": [
                ("context->ListViewHandle", "MAXINT", "handleStr", "item")
            ],
            "plugins/ExtendedTools/objmgr.c": [
                (
                    "Context->ListViewHandle",
                    "MAXINT",
                    "LPSTR_TEXTCALLBACK",
                    "entry",
                ),
                (
                    "context->ListViewHandle",
                    "MAXINT",
                    "LPSTR_TEXTCALLBACK",
                    "entry",
                ),
            ],
        }

        actual_count = 0
        for relative_path, expected_calls in expected.items():
            actual_calls = self.calls(relative_path, "PhAddListViewItemRaw")
            self.assertEqual(actual_calls, expected_calls, relative_path)
            actual_count += len(actual_calls)

        self.assertEqual(actual_count, 13)

    def test_job_limit_labels_and_other_window_properties_stay_on_legacy_helper(self) -> None:
        job_source = self.source("SystemInformer/jobprp.c")
        limit_body = function_body(job_source, "PhpAddLimit", self.audit)
        process_body = function_body(job_source, "PhpAddJobProcesses", self.audit)
        window_calls = self.calls(
            "plugins/WindowExplorer/wndprp.c", "PhAddListViewItem"
        )

        self.assertIn("PhAddListViewItem(", limit_body)
        self.assertNotIn("PhAddListViewItemRaw(", limit_body)
        self.assertIn("PhAddListViewItemRaw(", process_body)
        self.assertEqual(len(window_calls), 4)
        self.assertNotIn(
            ("context->ListViewHandle", "MAXINT", "handleStr", "item"),
            window_calls,
        )

    def test_audit_reports_raw_literals_but_not_callback_or_dynamic_data(self) -> None:
        source = r'''
            void sample(HWND listView, PCWSTR dynamicText, PVOID context)
            {
                PCWSTR oneHopText = L"One-hop raw label";

                PhAddListViewItemRaw(listView, MAXINT, L"Direct raw label", NULL);
                PhAddListViewItemRaw(listView, MAXINT, oneHopText, NULL);
                PhAddListViewItemRaw(listView, MAXINT, dynamicText, context);
                PhAddListViewItemRaw(
                    listView,
                    MAXINT,
                    LPSTR_TEXTCALLBACK,
                    context
                    );
            }
        '''
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            self.audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            Counter(
                (entry["category"], entry["english"])
                for entry in entries
            ),
            Counter(
                {
                    ("c_listview_item_raw", "Direct raw label"): 1,
                    ("c_listview_item_raw", "One-hop raw label"): 1,
                }
            ),
        )

    def test_compatibility_translation_export_is_identity_for_all_inputs(self) -> None:
        translation = self.source("phlib/phtranslation.c")
        lookup = function_body(translation, "PhTranslateString", self.audit)
        fixture = self.source("tools/tests/phlib-test/t_resource.c")

        self.assertEqual("returnEnglish;", compact(lookup))
        self.assertIn("PhTranslateString(MAKEINTRESOURCE(1))", fixture)
        self.assertIn("PhTranslateString((PCWSTR)LPSTR_TEXTCALLBACK)", fixture)
        self.assertNotIn("PhTranslationEnabled", fixture)


if __name__ == "__main__":
    unittest.main()
