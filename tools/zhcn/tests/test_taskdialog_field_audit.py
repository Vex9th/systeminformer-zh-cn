#!/usr/bin/env python3
"""Regression coverage for TaskDialog field data-flow auditing."""

import importlib.util
import os
import re
import tempfile
import unittest
from collections import Counter
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = REPO_ROOT / "tools" / "zhcn" / "audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("zhcn_audit_taskdialog", AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TaskDialogFieldAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def scan_source(self, source: str):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8", delete=False
        ) as source_file:
            source_file.write(source)
            path = Path(source_file.name)

        try:
            entries = []
            self.audit.scan_c_file(str(path), entries)
            return [
                entry for entry in entries if entry["category"] in {
                    "c_taskdialog",
                    "c_runtime_composed",
                }
            ]
        finally:
            path.unlink(missing_ok=True)

    def texts_by_category(self, source: str):
        result = {}
        for entry in self.scan_source(source):
            result.setdefault(entry["category"], []).append(entry["english"])
        return result

    def test_requires_typed_config_and_real_taskdialog_sink(self) -> None:
        entries = self.scan_source(
            r'''
            void Shown(void)
            {
                TASKDIALOGCONFIG config;
                config.pszContent = L"Shown text";
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }

            void WrongType(void)
            {
                OTHER_CONFIG config;
                config.pszContent = L"Wrong type";
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }

            void NoSink(void)
            {
                TASKDIALOGCONFIG config;
                config.pszContent = L"No sink";
            }
            '''
        )
        self.assertEqual(["Shown text"], [entry["english"] for entry in entries])

    def test_reads_complete_adjacent_wide_literal_expression(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOGCONFIGEX config;
                config.pszExpandedInformation =
                    L"The first sentence. "
                    L"The second sentence.";
                TaskDialogIndirect(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual(
            ["The first sentence. The second sentence."],
            [entry["english"] for entry in entries],
        )

    def test_preserves_runtime_composer_category_and_one_hop_local_text(self) -> None:
        categories = self.texts_by_category(
            r'''
            void Show(PCWSTR Name)
            {
                PCWSTR detail = L"Access denied";
                TASKDIALOGCONFIG config;
                config.pszMainInstruction =
                    PhaFormatString(L"Uploading %s...", Name)->Buffer;
                config.pszContent = detail;
                PhTaskDialogNavigatePage(NULL, &config);
            }
            '''
        )
        self.assertEqual(["Access denied"], categories["c_taskdialog"])
        self.assertEqual(["Uploading %s..."], categories["c_runtime_composed"])

    def test_keeps_reaching_branch_values_and_honors_taskdialog_shadowing(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(BOOLEAN Choice)
            {
                TASKDIALOGCONFIG config;

                if (Choice)
                    config.pszContent = L"First branch";
                else
                    config.pszContent = L"Second branch";

                {
                    TASKDIALOGCONFIG config;
                    config.pszContent = L"Unsunk shadow";
                }

                PhShowTaskDialog(&config, NULL, NULL, NULL);

                {
                    OTHER_CONFIG config;
                    config.pszContent = L"Wrong-type shadow";
                    PhShowTaskDialog(&config, NULL, NULL, NULL);
                }

                {
                    custom_type config;
                    config.pszContent = L"Lowercase-type shadow";
                    PhShowTaskDialog(&config, NULL, NULL, NULL);
                }
            }
            '''
        )
        self.assertCountEqual(
            ["First branch", "Second branch"],
            [entry["english"] for entry in entries],
        )

    def test_does_not_treat_nested_member_chain_as_the_local_config(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOGCONFIG config;
                HOLDER holder;

                holder.config.pszContent = L"Nested holder text";
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual([], entries)

    def test_reads_taskdialog_designated_initializer_fields(self) -> None:
        categories = self.texts_by_category(
            r'''
            void Show(PCWSTR Name)
            {
                TASKDIALOGCONFIG config = {
                    .pszMainInstruction =
                        L"Initializer " L"instruction",
                    .pszContent =
                        PhaFormatString(L"Initializer %s", Name)->Buffer,
                };

                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual(
            ["Initializer instruction"],
            categories.get("c_taskdialog", []),
        )
        self.assertEqual(
            ["Initializer %s"],
            categories.get("c_runtime_composed", []),
        )

    def test_language_operator_with_config_address_is_not_a_mutating_call(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOGCONFIG config;
                config.pszContent = L"Survives sizeof";
                (void)sizeof(&config);
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual(
            ["Survives sizeof"],
            [entry["english"] for entry in entries],
        )

    def test_unknown_local_assignment_and_buffer_write_fail_closed(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                PCWSTR text = L"Stale pointer text";
                WCHAR buffer[64] = L"Stale buffer text";
                TASKDIALOGCONFIG first;
                TASKDIALOGCONFIG second;

                text = GetUnknownText();
                buffer[0] = L'X';
                first.pszContent = text;
                second.pszContent = buffer;
                PhShowTaskDialog(&first, NULL, NULL, NULL);
                PhShowTaskDialog(&second, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual([], entries)

    def test_whole_config_mutations_invalidate_only_unconditional_old_state(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(BOOLEAN ResetConditionally)
            {
                TASKDIALOGCONFIG resetByCall;
                TASKDIALOGCONFIG resetByMemset;
                TASKDIALOGCONFIG resetByAssignment;
                TASKDIALOGCONFIG assignedAfterReset;
                TASKDIALOGCONFIG conditionallyReset;

                resetByCall.pszContent = L"Stale before call";
                ResetConfig(&resetByCall);
                PhShowTaskDialog(&resetByCall, NULL, NULL, NULL);

                resetByMemset.pszContent = L"Stale before memset";
                memset(&resetByMemset, 0, sizeof(resetByMemset));
                PhShowTaskDialog(&resetByMemset, NULL, NULL, NULL);

                resetByAssignment.pszContent = L"Stale before assignment";
                resetByAssignment = GetUnknownConfig();
                PhShowTaskDialog(&resetByAssignment, NULL, NULL, NULL);

                ResetConfig(&assignedAfterReset);
                assignedAfterReset.pszContent = L"Fresh after reset";
                PhShowTaskDialog(&assignedAfterReset, NULL, NULL, NULL);

                conditionallyReset.pszContent = L"May reach the dialog";
                if (ResetConditionally)
                    ResetConfig(&conditionallyReset);
                PhShowTaskDialog(&conditionallyReset, NULL, NULL, NULL);
            }
            '''
        )
        # A conditional whole-config write leaves a path where the old field
        # reaches the sink, so may-reach auditing must retain that source.
        self.assertCountEqual(
            ["Fresh after reset", "May reach the dialog"],
            [entry["english"] for entry in entries],
        )

    def test_irrelevant_file_returns_before_scope_and_literal_analysis(self) -> None:
        entries = []
        with mock.patch.object(
            self.audit,
            "c_brace_scopes",
            side_effect=AssertionError("scope parser should not run"),
        ), mock.patch.object(
            self.audit,
            "mask_c_literals",
            side_effect=AssertionError("literal masker should not run"),
        ):
            self.audit.scan_taskdialog_fields(
                "void Work(void) { DoBackgroundWork(); }",
                "void Work(void) { DoBackgroundWork(); }",
                "irrelevant.c",
                entries,
            )
        self.assertEqual([], entries)

    def test_masks_native_getters_settings_and_explicit_translation_funnels(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOGCONFIG config;
                config.pszWindowTitle = PluginGetUiString(1, L"Native fallback");
                config.pszMainInstruction = PhLoadUiString(NULL, 2, L"Load fallback");
                config.pszContent = PhGetStringSetting(L"SettingName");
                config.pszFooter = PhTranslateString(L"Already translated");
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual([], entries)

    def test_filters_technical_formats_but_keeps_semantic_formats(self) -> None:
        categories = self.texts_by_category(
            r'''
            void Show(ULONG Value, PCWSTR Name)
            {
                TASKDIALOGCONFIG config;
                config.pszWindowTitle = PhaFormatString(L"0x%08Ix", Value)->Buffer;
                config.pszFooter = PhaFormatString(L"[%lu]", Value)->Buffer;
                config.pszMainInstruction = PhaFormatString(L"Uploading %s...", Name)->Buffer;
                config.pszContent = PhaFormatString(L"[%lu] Access denied", Value)->Buffer;
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertCountEqual(
            ["Uploading %s...", "[%lu] Access denied"],
            categories["c_runtime_composed"],
        )
        self.assertNotIn("c_taskdialog", categories)

    def test_nested_composer_literals_keep_their_own_source_lines_once(self) -> None:
        source = r'''
        void Show(BOOLEAN HasTime, PCWSTR Relative, PCWSTR Absolute)
        {
            TASKDIALOGCONFIG config;
            config.pszContent = PhaFormatString(
                L"Updated: %s",
                HasTime
                    ? PhaFormatString(
                        L"%s ago (%s)", Relative, Absolute)->Buffer
                    : L"N/A"
                )->Buffer;
            PhShowTaskDialog(&config, NULL, NULL, NULL);
        }
        '''
        entries = self.scan_source(source)
        self.assertEqual(
            ["Updated: %s", "%s ago (%s)", "N/A"],
            [entry["english"] for entry in entries],
        )
        expected_lines = {
            text: source[:source.index(f'L"{text}"')].count("\n") + 1
            for text in ("Updated: %s", "%s ago (%s)", "N/A")
        }
        self.assertEqual(
            expected_lines,
            {entry["english"]: entry["line"] for entry in entries},
        )

    def test_migrated_real_sources_no_longer_emit_taskdialog_literals(self) -> None:
        expected = {
            "SystemInformer/ksisup.c": {
                "Initializing System Informer kernel driver...",
                "Your kernel version is pending review on the development branch. Your kernel will be supported in the next build!",
            },
            "SystemInformer/thrdstk.c": {
                "Processing stack frames...",
                "Loading symbols for image...",
            },
            "SystemInformer/actions.c": {
                "Select a system debugger to use for this process:",
                "You will need to provide administrator permission. Click Continue to complete this operation.",
            },
            "plugins/NetworkTools/pages.c": {
                "[%lu] Access denied (invalid license key)",
            },
            "plugins/Updater/page4.c": {
                "Downloading%s channel %s...",
            },
            "plugins/OnlineChecks/page3.c": {
                "Uploading %s...",
            },
            "plugins/UserNotes/main.c": {
                "The process priority will be applied by Windows even when System Informer isn't currently running. Note: Realtime priority requires the User has the SeIncreaseBasePriorityPrivilege or the process running as Administrator.",
            },
        }

        for relative_path, expected_texts in expected.items():
            with self.subTest(path=relative_path):
                entries = []
                self.audit.scan_c_file(str(REPO_ROOT / relative_path), entries)
                actual = {
                    entry["english"]
                    for entry in entries
                    if entry["category"] in {"c_taskdialog", "c_runtime_composed"}
                }
                self.assertFalse(expected_texts & actual, expected_texts & actual)

    def test_fresh_tree_delta_matches_the_current_taskdialog_audit_baseline(self) -> None:
        legacy_field_re = re.compile(
            r'\bpsz(MainInstruction|Content|VerificationText|ButtonText|Footer|'
            r'CollapsedControlText|ExpandedControlText|WindowTitle)\s*=\s*'
            r'(L"(?:[^"\\]|\\.)*")'
        )
        legacy_entries = []
        current_entries = []
        non_taskdialog_entries = []

        for path in self.audit.iter_source_files():
            if not path.endswith((".c", ".cpp")):
                continue
            relative_path = os.path.relpath(path, self.audit.REPO_ROOT).replace(
                "\\", "/"
            )
            source = Path(path).read_text(encoding="utf-8", errors="replace")
            scan_text = self.audit.mask_c_comments(source)
            self.audit.scan_taskdialog_fields(
                source, scan_text, relative_path, current_entries
            )

            for match in legacy_field_re.finditer(scan_text):
                text = self.audit.literal_text(match.group(2))
                if not self.audit.is_noise(text):
                    legacy_entries.append({
                        "category": "c_taskdialog",
                        "file": relative_path,
                        "line": self.audit.line_of_offset(source, match.start()),
                        "english": text,
                    })

        original_scanner = self.audit.scan_taskdialog_fields
        self.audit.scan_taskdialog_fields = lambda *args: None
        try:
            for path in self.audit.iter_source_files():
                relative_path = os.path.relpath(
                    path, self.audit.REPO_ROOT
                ).replace("\\", "/")
                if path.endswith(".rc"):
                    self.audit.scan_rc_file(path, non_taskdialog_entries)
                    continue
                if relative_path == "plugins/ToolStatus/statusbar.c":
                    self.audit.scan_statusbar(path, non_taskdialog_entries)
                if relative_path in (
                    "plugins/ToolStatus/toolbar.c",
                    "plugins/ExtendedTools/fwtab.c",
                    "plugins/ExtendedTools/disktab.c",
                ):
                    self.audit.scan_translated_calls(path, non_taskdialog_entries)
                if relative_path == "plugins/ToolStatus/statusbar.c":
                    self.audit.scan_c_file(path, non_taskdialog_entries)
                    self.audit.scan_tabnew(path, non_taskdialog_entries)
                    continue
                self.audit.scan_c_file(path, non_taskdialog_entries)
                self.audit.scan_tabnew(path, non_taskdialog_entries)
                self.audit.scan_page_names(path, non_taskdialog_entries)
                self.audit.scan_extra_statics(path, non_taskdialog_entries)
        finally:
            self.audit.scan_taskdialog_fields = original_scanner

        def occurrences(entries):
            return Counter(
                (
                    entry["category"],
                    entry["english"],
                    entry["file"],
                    entry["line"],
                )
                for entry in entries
            )

        def canonical_keys(entries):
            return {
                (
                    entry["category"],
                    entry["english"],
                    entry.get("module"),
                )
                for entry in self.audit.build_manifest(entries)["unique_strings"]
            }

        legacy_occurrences = occurrences(legacy_entries)
        current_occurrences = occurrences(current_entries)
        legacy_keys = canonical_keys(non_taskdialog_entries + legacy_entries)
        current_keys = canonical_keys(non_taskdialog_entries + current_entries)
        added_keys = current_keys - legacy_keys
        removed_keys = legacy_keys - current_keys

        self.assertEqual(0, sum((current_occurrences - legacy_occurrences).values()))
        self.assertEqual(set(), added_keys)
        self.assertEqual(set(), removed_keys)


if __name__ == "__main__":
    unittest.main()
