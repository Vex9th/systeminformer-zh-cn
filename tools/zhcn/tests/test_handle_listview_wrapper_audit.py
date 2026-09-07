#!/usr/bin/env python3

import importlib.util
import pathlib
import unittest
from collections import Counter

try:
    from tools.zhcn.tests.temp_source import scan_temporary_source
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    from temp_source import scan_temporary_source


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
AUDIT_PATH = REPO_ROOT / "tools" / "zhcn" / "audit.py"
HANDLE_SOURCE = REPO_ROOT / "SystemInformer" / "hndlprp.c"


def load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "handle_listview_wrapper_audit", AUDIT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HandleListViewWrapperAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def scan_source(self, source: str):
        return scan_temporary_source(self.audit.scan_c_file, source)

    def test_wrapper_names_argument_indexes_and_categories_are_exact(self) -> None:
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhAddHandleListViewItem"),
            {3: "c_listview_group_item"},
        )
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhSetHandleListViewItem"),
            {3: "c_window_text"},
        )
        self.assertNotIn("PhAddHandleListViewItemRenamed", self.audit.CALL_SPECS)
        self.assertNotIn("PhSetHandleListViewItemRenamed", self.audit.CALL_SPECS)

    def test_scanner_finds_direct_and_single_hop_wrapper_text_only(self) -> None:
        entries = self.scan_source(
            r'''
            void show_handle_text(BOOLEAN directory)
            {
                PCWSTR groupText = L"One-hop group";
                PCWSTR valueText;
                PCWSTR unknownText = LookupSetting(L"Hidden setting key");
                PCWSTR translatedText = PhTranslateString(L"Already translated local");

                valueText = L"One-hop value";

                PhAddHandleListViewItem(context, 1, 2, L"Direct group");
                PhAddHandleListViewItem(context, 1, 2, groupText);
                PhSetHandleListViewItem(context, 2, 1, L"Direct value");
                PhSetHandleListViewItem(
                    context,
                    2,
                    1,
                    directory ? L"Directory value" : L"File value"
                    );
                PhSetHandleListViewItem(context, 2, 1, valueText);

                PhAddHandleListViewItem(context, 1, 2, unknownText);
                PhSetHandleListViewItem(context, 2, 1, translatedText);
                PhSetHandleListViewItem(
                    context,
                    2,
                    1,
                    PhLoadUiString(instance, IDS_VALUE, L"Resource fallback")
                    );
                PhSetHandleListViewItem(
                    context,
                    2,
                    1,
                    PhTranslateString(L"Already translated direct")
                    );
                PhSetHandleListViewItem(
                    context,
                    2,
                    1,
                    LookupSetting(L"Hidden direct setting key")
                    );

                PhAddHandleListViewItemRenamed(context, 1, 2, L"Renamed group");
                PhSetHandleListViewItemRenamed(context, 2, 1, L"Renamed value");
                PhAddHandleListViewItem(context, 1, L"Wrong add argument", dynamicText);
                PhSetHandleListViewItem(context, 2, L"Wrong set argument", dynamicText);
            }
            '''
        )

        self.assertEqual(
            Counter(
                (entry["category"], entry["english"])
                for entry in entries
            ),
            Counter(
                {
                    ("c_listview_group_item", "Direct group"): 1,
                    ("c_listview_group_item", "One-hop group"): 1,
                    ("c_window_text", "Direct value"): 1,
                    ("c_window_text", "Directory value"): 1,
                    ("c_window_text", "File value"): 1,
                    ("c_window_text", "One-hop value"): 1,
                }
            ),
        )

    def test_scanner_does_not_guess_across_reassignments_or_scopes(self) -> None:
        entries = self.scan_source(
            r'''
            void show_handle_text(BOOLEAN condition)
            {
                PCWSTR reassigned = L"Stale value";
                PCWSTR outer = L"Outer value";

                if (condition)
                    reassigned = L"Conditional value";
                PhSetHandleListViewItem(context, 2, 1, reassigned);

                {
                    PCWSTR outer = LookupSetting(L"Inner hidden key");
                    PhSetHandleListViewItem(context, 2, 1, outer);
                }

                PhSetHandleListViewItem(context, 2, 1, outer);
            }
            '''
        )

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [("c_window_text", "Outer value")],
        )

    def test_strict_single_hop_is_invalidated_by_all_local_mutations(self) -> None:
        entries = self.scan_source(
            r'''
            void show_mutated_handle_text(BOOLEAN condition, ULONG count)
            {
                PCWSTR postfixText = L"Postfix stale";
                PCWSTR compoundText = L"Compound stale";
                PCWSTR prefixText = L"Prefix stale";
                WCHAR indexedText[] = L"Indexed stale";
                WCHAR nestedIndexText[] = L"Nested index stale";
                WCHAR multidimensionalText[] = L"Multidimensional stale";
                PCWSTR whileText;
                PCWSTR forText;
                PCWSTR doText;
                ULONG index;

                postfixText++;
                compoundText += 1;
                ++prefixText;
                indexedText[0] = L'X';
                nestedIndexText[indexes[0]] = L'X';
                multidimensionalText[0][1] = L'X';
                while (condition)
                    whileText = L"Conditional while value";
                for (index = 0; index < count; index++)
                    forText = L"Conditional for value";
                do
                    doText = L"Conditional do value";
                while (condition);

                PhSetHandleListViewItem(context, 1, 1, postfixText);
                PhSetHandleListViewItem(context, 2, 1, compoundText);
                PhSetHandleListViewItem(context, 3, 1, prefixText);
                PhSetHandleListViewItem(context, 4, 1, indexedText);
                PhSetHandleListViewItem(context, 5, 1, nestedIndexText);
                PhSetHandleListViewItem(context, 6, 1, multidimensionalText);
                PhSetHandleListViewItem(context, 7, 1, whileText);
                PhSetHandleListViewItem(context, 8, 1, forText);
                PhSetHandleListViewItem(context, 9, 1, doText);
            }
            '''
        )

        self.assertEqual(entries, [])

    def test_array_comparison_does_not_invalidate_single_hop_text(self) -> None:
        entries = self.scan_source(
            r'''
            void show_compared_handle_text(void)
            {
                WCHAR comparedText[] = L"Compared value";

                if (comparedText[0] == L'C')
                    NOTHING;
                PhSetHandleListViewItem(context, 1, 1, comparedText);
            }
            '''
        )

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [("c_window_text", "Compared value")],
        )

    def test_string_fallbacks_are_visible_but_resource_getters_are_not(self) -> None:
        entries = self.scan_source(
            r'''
            void show_fallback_handle_text(void)
            {
                PCWSTR localFallback = PhGetStringOrDefault(
                    dynamicText,
                    L"Local visible fallback"
                    );
                PCWSTR localResource = PhLoadUiString(
                    instance,
                    IDS_VALUE,
                    L"Local resource fallback"
                    );

                PhSetHandleListViewItem(
                    context,
                    1,
                    1,
                    PhGetStringOrDefault(dynamicText, L"Direct visible fallback")
                    );
                PhSetHandleListViewItem(context, 2, 1, localFallback);
                PhSetHandleListViewItem(
                    context,
                    3,
                    1,
                    PhLoadUiString(instance, IDS_VALUE, L"Direct resource fallback")
                    );
                PhSetHandleListViewItem(context, 4, 1, localResource);
            }
            '''
        )

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [
                ("c_window_text", "Direct visible fallback"),
                ("c_window_text", "Local visible fallback"),
            ],
        )

    def test_unconditional_multiple_definitions_fail_closed(self) -> None:
        entries = self.scan_source(
            r'''
            void show_reassigned_handle_text(void)
            {
                PCWSTR text;

                text = L"First definition";
                text = L"Second definition";
                PhSetHandleListViewItem(context, 1, 1, text);
            }
            '''
        )

        self.assertEqual(entries, [])

    def test_current_handle_source_counts_are_locked(self) -> None:
        entries = []
        self.audit.scan_c_file(str(HANDLE_SOURCE), entries)

        group_text = [
            entry["english"]
            for entry in entries
            if entry["category"] == "c_listview_group_item"
        ]
        window_text = [
            entry["english"]
            for entry in entries
            if entry["category"] == "c_window_text"
        ]

        self.assertEqual((len(group_text), len(set(group_text))), (0, 0))
        self.assertEqual((len(window_text), len(set(window_text))), (0, 0))


if __name__ == "__main__":
    unittest.main()
