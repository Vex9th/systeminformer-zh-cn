#!/usr/bin/env python3
"""Regression coverage for TaskDialog button data-flow auditing."""

import importlib.util
import os
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = REPO_ROOT / "tools" / "zhcn" / "audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("zhcn_audit_taskdialog_buttons", AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TaskDialogButtonAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def scan_source(self, source: str):
        entries = []
        self.audit.scan_taskdialog_buttons(
            source,
            self.audit.mask_c_comments(source),
            "fixture.c",
            entries,
        )
        return entries

    def test_decodes_c_universal_character_names_for_runtime_keys(self) -> None:
        self.assertEqual("🪟", self.audit.literal_text(r'L"\U0001FA9F"'))
        self.assertEqual("⚙", self.audit.literal_text(r'L"\u2699"'))

    def test_distinguishes_show_translation_from_raw_navigation_sinks(self) -> None:
        entries = self.scan_source(
            r'''
            TASKDIALOG_BUTTON showButtons[] =
            {
                { 1, L"Show " L"button" },
            };
            TASKDIALOG_BUTTON showRadioButtons[] =
            {
                { 2, L"Show radio" },
            };
            TASKDIALOG_BUTTON navigateButtons[] =
            {
                { 3, L"Navigate raw" },
                { 4, PhTranslateString(L"Already translated") },
                { 5, PluginGetUiString(IDS_BUTTON) },
            };
            TASKDIALOG_BUTTON indirectButtons[] =
            {
                { 6, L"Indirect raw" },
            };

            void Show(void)
            {
                TASKDIALOGCONFIG config;
                config.pButtons = showButtons;
                config.cButtons = RTL_NUMBER_OF(showButtons);
                config.pRadioButtons = showRadioButtons;
                config.cRadioButtons = RTL_NUMBER_OF(showRadioButtons);
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }

            void Navigate(void)
            {
                TASKDIALOGCONFIG config;
                config.pButtons = navigateButtons;
                config.cButtons = RTL_NUMBER_OF(navigateButtons);
                PhTaskDialogNavigatePage(NULL, &config);
            }

            void Indirect(void)
            {
                TASKDIALOGCONFIG config;
                config.pButtons = indirectButtons;
                config.cButtons = 1;
                TaskDialogIndirect(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertCountEqual(
            ["Show button", "Show radio"],
            [entry["english"] for entry in entries if entry["category"] == "c_taskdialog"],
        )
        self.assertCountEqual(
            ["Navigate raw", "Indirect raw"],
            [entry["english"] for entry in entries if entry["category"] == "c_taskdialog_raw"],
        )
        self.assertNotIn(
            "Already translated",
            [entry["english"] for entry in entries],
        )

    def test_reusing_one_config_across_known_sinks_preserves_each_sink_route(self) -> None:
        entries = self.scan_source(
            r'''
            void ShowThenNavigate(void)
            {
                TASKDIALOG_BUTTON buttons[] = { { 1, L"Shared button" } };
                TASKDIALOGCONFIG config;

                config.pButtons = buttons;
                config.cButtons = 1;
                PhShowTaskDialog(&config, NULL, NULL, NULL);
                PhTaskDialogNavigatePage(NULL, &config);
            }
            '''
        )
        self.assertCountEqual(
            [("c_taskdialog", "Shared button"), ("c_taskdialog_raw", "Shared button")],
            [(entry["category"], entry["english"]) for entry in entries],
        )

    def test_all_supported_c_integer_zero_forms_disable_button_arrays(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOG_BUTTON first[] = { { 1, L"Zero U" } };
                TASKDIALOG_BUTTON second[] = { { 2, L"Zero UL" } };
                TASKDIALOG_BUTTON third[] = { { 3, L"False" } };
                TASKDIALOG_BUTTON fourth[] = { { 4, L"Cast zero" } };
                TASKDIALOG_BUTTON radio[] = { { 5, L"Radio zero" } };
                TASKDIALOGCONFIG one;
                TASKDIALOGCONFIG two;
                TASKDIALOGCONFIG three;
                TASKDIALOGCONFIG four;
                TASKDIALOGCONFIG five;

                one.pButtons = first;
                one.cButtons = 0U;
                PhShowTaskDialog(&one, NULL, NULL, NULL);

                two.pButtons = second;
                two.cButtons = 0UL;
                PhShowTaskDialog(&two, NULL, NULL, NULL);

                three.pButtons = third;
                three.cButtons = FALSE;
                PhShowTaskDialog(&three, NULL, NULL, NULL);

                four.pButtons = fourth;
                four.cButtons = (ULONG)0;
                PhShowTaskDialog(&four, NULL, NULL, NULL);

                five.pRadioButtons = radio;
                five.cRadioButtons = 0L;
                PhShowTaskDialog(&five, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual([], entries)

    def test_tracks_compound_member_branch_and_one_hop_composer_sources(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(BOOLEAN Choice, PCWSTR Name)
            {
                TASKDIALOG_BUTTON buttons[2];
                TASKDIALOGCONFIG config;
                PPH_STRING label = PhaFormatString(L"Open %s", Name);

                if (Choice)
                    buttons[0] = (TASKDIALOG_BUTTON){ 1, L"First branch" };
                else
                    buttons[0] = (TASKDIALOG_BUTTON){ 1, L"Second branch" };
                buttons[1].pszButtonText = label->Buffer;

                config.pButtons = buttons;
                config.cButtons = 2;
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertCountEqual(
            ["First branch", "Second branch"],
            [entry["english"] for entry in entries if entry["category"] == "c_taskdialog"],
        )
        self.assertEqual(
            ["Open %s"],
            [entry["english"] for entry in entries if entry["category"] == "c_runtime_composed"],
        )

    def test_reads_designated_button_and_config_initializers(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOG_BUTTON buttons[] =
                {
                    { .nButtonID = 1, .pszButtonText = L"Designated button" },
                };
                TASKDIALOGCONFIG config =
                {
                    .pButtons = buttons,
                    .cButtons = RTL_NUMBER_OF(buttons),
                };
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual(["Designated button"], [entry["english"] for entry in entries])

    def test_fails_closed_for_unused_zero_count_shadowed_and_mutated_arrays(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOG_BUTTON unused[] = { { 1, L"Unused" } };
                TASKDIALOG_BUTTON zeroed[] = { { 2, L"Zero count" } };
                TASKDIALOG_BUTTON mutated[] = { { 3, L"Stale before mutation" } };
                TASKDIALOG_BUTTON shadowed[] = { { 4, L"Outer shadowed" } };
                TASKDIALOGCONFIG first;
                TASKDIALOGCONFIG second;
                TASKDIALOGCONFIG third;

                first.pButtons = zeroed;
                first.cButtons = 0;
                PhShowTaskDialog(&first, NULL, NULL, NULL);

                ResetButtons(mutated);
                second.pButtons = mutated;
                second.cButtons = RTL_NUMBER_OF(mutated);
                PhShowTaskDialog(&second, NULL, NULL, NULL);

                {
                    OTHER_BUTTON shadowed[] = { { 5, L"Wrong type shadow" } };
                    third.pButtons = shadowed;
                    third.cButtons = 1;
                    PhShowTaskDialog(&third, NULL, NULL, NULL);
                }
            }
            '''
        )
        self.assertEqual([], entries)

    def test_local_wrong_type_array_shadows_global_typed_array(self) -> None:
        entries = self.scan_source(
            r'''
            TASKDIALOG_BUTTON buttons[] = { { 1, L"Hidden global" } };

            void Show(void)
            {
                OTHER_BUTTON buttons[] = { { 2, L"Wrong local type" } };
                TASKDIALOGCONFIG config;
                config.pButtons = buttons;
                config.cButtons = 1;
                PhShowTaskDialog(&config, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual([], entries)

    def test_invalidates_overwritten_or_address_mutated_slots_only(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(void)
            {
                TASKDIALOG_BUTTON overwritten[] = { { 1, L"Overwritten stale" } };
                TASKDIALOG_BUTTON addressMutated[] = { { 2, L"Address stale" } };
                TASKDIALOG_BUTTON languageOperator[] = { { 3, L"Still visible" } };
                TASKDIALOGCONFIG first;
                TASKDIALOGCONFIG second;
                TASKDIALOGCONFIG third;

                overwritten[0] = MakeButton();
                first.pButtons = overwritten;
                first.cButtons = 1;
                PhShowTaskDialog(&first, NULL, NULL, NULL);

                ResetButton(&addressMutated[0]);
                second.pButtons = addressMutated;
                second.cButtons = 1;
                PhShowTaskDialog(&second, NULL, NULL, NULL);

                (void)sizeof(languageOperator);
                third.pButtons = languageOperator;
                third.cButtons = 1;
                PhShowTaskDialog(&third, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual(["Still visible"], [entry["english"] for entry in entries])

    def test_whole_config_reset_and_conditional_reset_use_may_reach_semantics(self) -> None:
        entries = self.scan_source(
            r'''
            void Show(BOOLEAN Choice)
            {
                TASKDIALOG_BUTTON stale[] = { { 1, L"Cleared binding" } };
                TASKDIALOG_BUTTON maybe[] = { { 2, L"May reach" } };
                TASKDIALOGCONFIG reset;
                TASKDIALOGCONFIG conditional;

                reset.pButtons = stale;
                reset.cButtons = 1;
                ResetConfig(&reset);
                PhShowTaskDialog(&reset, NULL, NULL, NULL);

                conditional.pButtons = maybe;
                conditional.cButtons = 1;
                if (Choice)
                    ResetConfig(&conditional);
                PhShowTaskDialog(&conditional, NULL, NULL, NULL);
            }
            '''
        )
        self.assertEqual(["May reach"], [entry["english"] for entry in entries])

    def test_contract_marks_raw_taskdialog_buttons_as_callsite_migration(self) -> None:
        self.assertIn("c_taskdialog_raw", self.audit.ALL_CATEGORIES)
        self.assertIn("c_taskdialog_raw", self.audit.CALLSITE_MIGRATION_CATEGORIES)

    def test_real_tree_button_delta_is_exact(self) -> None:
        entries = []
        for path in self.audit.iter_source_files():
            if not path.endswith((".c", ".cpp")):
                continue
            source = Path(path).read_text(encoding="utf-8", errors="replace")
            relative_path = os.path.relpath(path, self.audit.REPO_ROOT).replace("\\", "/")
            self.audit.scan_taskdialog_buttons(
                source,
                self.audit.mask_c_comments(source),
                relative_path,
                entries,
            )

        self.assertEqual([], entries)
        self.assertEqual(0, len(self.audit.build_manifest(entries)["unique_strings"]))


if __name__ == "__main__":
    unittest.main()
