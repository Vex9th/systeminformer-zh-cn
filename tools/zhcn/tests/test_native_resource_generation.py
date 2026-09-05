#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / "tools" / "zhcn" / "generate_native_resources.py"
SOURCE_RC = REPO_ROOT / "SystemInformer" / "SystemInformer.rc"
ZH_CN_RC = REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc"
PLUGIN_MODULES = (
    "DotNetTools",
    "ExtendedNotifications",
    "ExtendedServices",
    "ExtendedTools",
    "HardwareDevices",
    "NetworkTools",
    "OnlineChecks",
    "ToolStatus",
    "Updater",
    "UserNotes",
    "WindowExplorer",
)
TOOL_MODULES = (
    (
        "peview",
        REPO_ROOT / "tools" / "peview" / "peview.rc",
        REPO_ROOT / "tools" / "peview" / "peview.zh-cn.rc",
        REPO_ROOT / "tools" / "peview" / "peview.vcxproj",
        REPO_ROOT / "tools" / "peview" / "peview.vcxproj.filters",
    ),
    (
        "CustomSetupTool",
        REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc",
        REPO_ROOT / "tools" / "CustomSetupTool" / "resource.zh-cn.rc",
        REPO_ROOT / "tools" / "CustomSetupTool" / "CustomSetupTool.vcxproj",
        REPO_ROOT / "tools" / "CustomSetupTool" / "CustomSetupTool.vcxproj.filters",
    ),
)
DIALOG_RE = re.compile(r"(?m)^([A-Z][A-Z0-9_]*|\d+)\s+DIALOG(?:EX)?\b")
FONT_RE = re.compile(r'(?m)^\s*FONT\s+(\d+)\s*,\s*"([^"]+)"')
STRING_ENTRY_RE = re.compile(r'(?m)^\s*([A-Z][A-Z0-9_]*|\d+)\s+"')


def load_validator_module():
    path = REPO_ROOT / "tools" / "zhcn" / "validate_templates.py"
    spec = importlib.util.spec_from_file_location("validate_templates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_native_resources", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_runtime_translation_generator_module():
    path = REPO_ROOT / "tools" / "zhcn" / "generate_translation.py"
    spec = importlib.util.spec_from_file_location("generate_translation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_auto_translation_module():
    path = REPO_ROOT / "tools" / "zhcn" / "auto_translate.py"
    spec = importlib.util.spec_from_file_location("auto_translate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_translation_checker_module():
    path = REPO_ROOT / "tools" / "zhcn" / "check_translation.py"
    spec = importlib.util.spec_from_file_location("check_translation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stringtable_ids(source: str) -> list[str]:
    generator = load_generator_module()
    return [
        resource_id
        for block in generator.extract_stringtable_blocks(source)
        for resource_id in STRING_ENTRY_RE.findall("\n".join(block))
    ]


def wide_string(value: str) -> bytes:
    return value.encode("utf-16-le") + b"\0\0"


def make_stringtable_block(values: dict[int, str]) -> bytes:
    data = bytearray()

    for index in range(16):
        value = values.get(index, "")
        encoded = value.encode("utf-16-le")
        data += struct.pack("<H", len(encoded) // 2)
        data += encoded

    return bytes(data)


def make_dialog_template(
    caption: str,
    label: str,
    point_size: int,
    typeface: str,
    *,
    item_text_ordinal=None,
    weight: int = 400,
    pad_end: bool = True,
    tail_label: str = "Tail",
    set_font: bool = True,
) -> bytes:
    style = 0x80000000 | 0x00C00000 | (0x0040 if set_font else 0x0008)
    data = bytearray(struct.pack(
        "<HHIIIHhhhh", 1, 0xFFFF, 0, 0, style, 2, 0, 0, 120, 40
    ))
    data += b"\0\0"  # menu
    data += b"\0\0"  # window class
    data += wide_string(caption)
    if set_font:
        data += struct.pack("<HHBB", point_size, weight, 0, 1)
        data += wide_string(typeface)
    data += b"\0" * (-len(data) % 4)
    data += struct.pack("<IIIhhhhI", 0, 0, 0x50000000, 6, 8, 100, 12, 202)
    data += struct.pack("<HH", 0xFFFF, 0x0082)  # static control class
    if item_text_ordinal is None:
        data += wide_string(label)
    else:
        data += struct.pack("<HH", 0xFFFF, item_text_ordinal)
    data += struct.pack("<HH", 4, 0x1234)  # size includes the size WORD
    data += b"\0" * (-len(data) % 4)
    data += struct.pack("<IIIhhhhI", 0, 0, 0x50000000, 6, 22, 100, 12, 203)
    data += struct.pack("<HH", 0xFFFF, 0x0082)
    data += wide_string(tail_label)
    data += b"\0\0"
    if pad_end:
        data += b"\0" * (-len(data) % 4)
    return bytes(data)


class NativeResourceGenerationTests(unittest.TestCase):
    def test_audit_preserves_urls_and_doubled_quotes_in_rc_strings(self):
        audit = load_audit_module()
        source = (
            'CONTROL "<a href=""https://example.invalid/path"">Label</a>",'
            'IDC_LINK\n// CONTROL "Ignored",IDC_STATIC\n'
        )
        masked = audit.mask_rc_comments(source)
        match = audit.RC_QUOTED_RE.search(masked)

        self.assertIsNotNone(match)
        self.assertEqual(
            audit.rc_unescape(match.group(1)),
            '<a href="https://example.invalid/path">Label</a>',
        )
        self.assertNotIn("Ignored", masked)

    def test_audit_keeps_visible_sentences_that_start_with_placeholder(self) -> None:
        audit = load_audit_module()

        self.assertTrue(audit.is_noise("%s"))
        self.assertTrue(audit.is_noise("%lu"))
        self.assertTrue(audit.is_noise("%lu|"))
        self.assertFalse(audit.is_noise("%s complete."))
        self.assertFalse(
            audit.is_noise("%s is not recommended when running this program.")
        )
        self.assertEqual(audit.CALL_SPECS["PhShowStatus"], {1: "c_msgbox"})
        self.assertEqual(
            audit.CALL_SPECS["PhShowContinueStatus"], {1: "c_msgbox"}
        )

    def test_audit_scans_message_macro_title_and_format_arguments(self) -> None:
        audit = load_audit_module()
        source = """
            PhShowError(hwnd, L"Real visible message.");
            PhShowError(hwnd, L"Adjacent " L"format message.");
            PhShowError(hwnd, L"%s", L"Visible vararg message.");
            PhShowWarning(hwnd, L"Visible warning: %s", detail);
            PhShowInformation2(hwnd, L"Visible title", L"Visible content");
            PhShowError2(
                hwnd,
                L"Visible vararg title",
                L"%s",
                L"Visible vararg content"
            );
            PhShowWarning2(
                hwnd,
                L"Adjacent title",
                L"%s",
                L"Adjacent "
                L"content"
            );
            PhShowWarning(
                hwnd,
                L"Visible format without placeholders.",
                L"Unused vararg literal."
            );
            // PhShowError(hwnd, L"Commented-out message.");
            /* PhShowError(hwnd, L"Block-commented message."); */
            PhShowMessageOneTime2(
                hwnd,
                TD_CLOSE_BUTTON,
                TD_INFORMATION_ICON,
                L"One-time title",
                &checked,
                L"One-time content"
            );
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            {entry["english"] for entry in entries},
            {
                "Real visible message.",
                "Adjacent format message.",
                "Visible vararg message.",
                "Visible warning: %s",
                "Visible title",
                "Visible content",
                "Visible vararg title",
                "Visible vararg content",
                "Adjacent title",
                "Adjacent content",
                "Visible format without placeholders.",
                "One-time title",
                "One-time content",
            },
        )
        categories = {
            entry["english"]: entry["category"]
            for entry in entries
        }
        self.assertEqual(
            categories["Visible vararg message."],
            "c_msgbox_vararg",
        )
        self.assertEqual(
            categories["Visible vararg content"],
            "c_msgbox",
        )
        self.assertNotIn("Commented-out message.", categories)
        self.assertNotIn("Block-commented message.", categories)
        self.assertNotIn("Unused vararg literal.", categories)

    def test_audit_scans_common_ui_text_setters(self) -> None:
        audit = load_audit_module()
        source = """
            typedef struct _CHOICE_ENTRY {
                ULONG Value;
                PCWSTR Name;
            } CHOICE_ENTRY;
            static CHOICE_ENTRY structChoices[] = {
                { 1, L"First struct choice" },
                { 2, L"Second struct choice" }
            };
            PCWSTR sharedChoices[] = { L"Global shared choice" };
            void sample(void) {
                PhSetDialogItemText(hwnd, IDC_STATUS, L"Dialog item text");
                PhSetWindowText(hwnd, L"Window title");
                SetWindowText(hwnd, L"Native window title");
                SetWindowTextW(hwnd, L"Wide window title");
                PhSetListViewSubItem(list, 4, 1, L"List-view value");
                PPH_SYSINFO_DRAW_PANEL drawPanel = panel;
                PhMoveReference(&drawPanel->Title, PhCreateString(L"Panel title"));
                drawPanel->Title = PhCreateString(L"Panel fallback title");
                static PH_STRINGREF sectionText = PH_STRINGREF_INIT(L"Section title");
                PH_SYSINFO_SECTION section;
                section.Name = sectionText;
                {
                    OTHER* drawPanel;
                    OTHER section;
                    drawPanel->Title = L"Shadowed panel field";
                    section.Name = L"Shadowed section field";
                }
                PhAddListViewGroup(list, 1, L"Group heading");
                PhAddListViewGroupItem(list, 1, MAXINT, L"Grouped item", NULL);
                PhAddIListViewGroupItem(list, 1, MAXINT, L"Interface grouped item", NULL);
                PhListView_AddGroup(list, 2, L"Wrapped group heading");
                PhListView_AddGroupItem(list, 2, MAXINT, L"Wrapped grouped item", NULL);
                ComboBox_AddString(combo, L"Choice label");
                PCWSTR choices[] = { L"First array choice", L"Second array choice" };
                PhAddComboBoxStrings(combo, choices, RTL_NUMBER_OF(choices));
                PWSTR formattedChoices[2];
                formattedChoices[i] = PhaFormatString(L"%u units", i)->Buffer;
                PhAddComboBoxStrings(combo, formattedChoices, RTL_NUMBER_OF(formattedChoices));
                PCWSTR mixedChoices[2] = { L"Initial mixed choice" };
                mixedChoices[1] = L"Assigned mixed choice";
                PhAddComboBoxStrings(combo, mixedChoices, RTL_NUMBER_OF(mixedChoices));
                PCWSTR nativeChoices[] = {
                    ToolStatusGetUiString(IDS_TEST_CHOICE, L"Native fallback")
                };
                PhAddComboBoxStrings(combo, nativeChoices, RTL_NUMBER_OF(nativeChoices));
                for (ULONG i = 0; i < RTL_NUMBER_OF(structChoices); i++) {
                    ComboBox_AddString(combo, structChoices[i].Name);
                }
            }
            void first(void) {
                PCWSTR sharedChoices[] = { L"Unrelated local choice" };
            }
            void second(void) {
                PhAddComboBoxStrings(combo, sharedChoices, RTL_NUMBER_OF(sharedChoices));
            }
            void third(void) {
                PWSTR assignedChoices[1];
                {
                    PWSTR assignedChoices[1];
                    assignedChoices[0] = L"Unrelated shadow assignment";
                }
                assignedChoices[0] = L"Visible scoped assignment";
                PhAddComboBoxStrings(combo, assignedChoices, RTL_NUMBER_OF(assignedChoices));
            }
            void unrelated_sysinfo_names(void) {
                OTHER *drawPanel;
                OTHER section;
                drawPanel->Title = L"Unrelated panel field";
                section.Name = L"Unrelated section field";
            }
            // PhSetWindowText(hwnd, L"Commented title");
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            {(entry["category"], entry["english"]) for entry in entries},
            {
                ("c_window_text", "Dialog item text"),
                ("c_window_text", "Window title"),
                ("c_window_text", "Native window title"),
                ("c_window_text", "Wide window title"),
                ("c_window_text", "List-view value"),
                ("c_window_text", "Panel title"),
                ("c_window_text", "Panel fallback title"),
                ("c_window_text", "Section title"),
                ("c_listview_group", "Group heading"),
                ("c_listview_group", "Wrapped group heading"),
                ("c_listview_group_item", "Grouped item"),
                ("c_listview_group_item", "Interface grouped item"),
                ("c_listview_group_item", "Wrapped grouped item"),
                ("c_combobox", "Choice label"),
                ("c_combobox", "First array choice"),
                ("c_combobox", "Second array choice"),
                ("c_combobox", "%u units"),
                ("c_combobox", "Initial mixed choice"),
                ("c_combobox", "Assigned mixed choice"),
                ("c_combobox", "Global shared choice"),
                ("c_combobox", "Visible scoped assignment"),
                ("c_combobox", "First struct choice"),
                ("c_combobox", "Second struct choice"),
            },
        )
        scanned_text = {entry["english"] for entry in entries}
        self.assertNotIn("Native fallback", scanned_text)
        self.assertNotIn("Unrelated local choice", scanned_text)
        self.assertNotIn("Unrelated shadow assignment", scanned_text)

    def test_audit_scans_all_visible_literals_in_target_argument(self) -> None:
        audit = load_audit_module()
        source = """
            void update_status(BOOLEAN configured) {
                PhSetDialogItemText(
                    hwnd,
                    IDC_STATUS,
                    configured ? L"Configured status" : L"Optional status"
                );
                PhSetDialogItemText(
                    hwnd,
                    IDC_ADJACENT,
                    L"Adjacent " L"status"
                );
                PhSetDialogItemText(
                    hwnd,
                    IDC_NATIVE,
                    configured
                        ? PhGetString(PH_AUTO(PhLoadUiString(
                            module, IDS_NATIVE, L"Native load fallback")))
                        : ToolStatusGetUiString(
                            IDS_PLUGIN_NATIVE, L"Plugin getter fallback")
                );
                PhSetDialogItemText(
                    L"Non-target window",
                    configured ? L"Non-target control" : L"Other control",
                    dynamic_text
                );
                PhShowError(hwnd, L"%s", L"Visible vararg exactly once.");
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [
                (entry["category"], entry["english"])
                for entry in entries
            ],
            [
                ("c_window_text", "Configured status"),
                ("c_window_text", "Optional status"),
                ("c_window_text", "Adjacent status"),
                ("c_msgbox_vararg", "Visible vararg exactly once."),
            ],
        )

    def test_audit_ignores_setting_keys_but_keeps_visible_surrounding_text(self) -> None:
        audit = load_audit_module()
        source = """
            void update_setting_text(BOOLEAN configured) {
                PhSetDialogItemText(
                    hwnd,
                    IDC_PATH,
                    PhaGetStringSetting(L"DbgHelpSearchPath")->Buffer
                );
                PhSetWindowText(
                    hwnd,
                    configured
                        ? PhGetStringSetting(L"ConfiguredPath")->Buffer
                        : L"Visible fallback"
                );
                PhSetWindowText(
                    hwnd,
                    PhaFormatString(
                        L"Configured path: %s",
                        PhGetStringSetting(L"FormattedPath")->Buffer
                    )->Buffer
                );
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [
                ("c_window_text", "Visible fallback"),
                ("c_runtime_composed", "Configured path: %s"),
            ],
        )

    def test_audit_tracks_direct_and_one_hop_runtime_composition(self) -> None:
        audit = load_audit_module()
        source = """
            void show_actions(BOOLEAN critical, ULONG count) {
                PPH_STRING message;
                PPH_STRING allocatedMessage;
                WCHAR countText[64];
                WCHAR percentText[64];
                PCWSTR plainLabel;

                PhShowConfirmMessage(
                    hwnd,
                    L"delete",
                    L"the item",
                    PhaConcatStrings(
                        3,
                        L"You are about to ",
                        L"delete",
                        L" the selected item."
                    )->Buffer,
                    TRUE
                );

                PhShowConfirmMessage(
                    hwnd,
                    L"delete",
                    L"the item",
                    critical
                        ? L"Direct conditional message"
                        : PhaFormatString(L"Composed conditional %s", itemName)->Buffer,
                    TRUE
                );

                allocatedMessage = PhConcatStrings2(L"Allocated prefix ", itemName);
                PhShowConfirmMessage(
                    hwnd,
                    L"delete",
                    L"the item",
                    allocatedMessage->Buffer,
                    TRUE
                );

                message = PhaFormatString(
                    L"Delete %s now?",
                    itemName
                );
                PhShowConfirmMessage(
                    hwnd,
                    L"delete",
                    L"the item",
                    message->Buffer,
                    TRUE
                );

                if (count == 0)
                    swprintf_s(countText, RTL_NUMBER_OF(countText), L"Thread count... (auto)");
                else
                    swprintf_s(countText, RTL_NUMBER_OF(countText), L"Thread count... (%lu)", count);
                PhCreateEMenuItem(0, 1, countText, NULL, NULL);

                swprintf_s(percentText, RTL_NUMBER_OF(percentText), L"Progress 100%% done");
                PhCreateEMenuItem(0, 3, percentText, NULL, NULL);

                plainLabel = critical ? L"Critical action" : L"Normal action";
                PhCreateEMenuItem(0, 2, plainLabel, NULL, NULL);

                PhShowMessage(hwnd, MB_OK, L"Direct API format: %s", itemName);
                PhShowMessage2(hwnd, TD_OK_BUTTON, TD_INFORMATION_ICON,
                    L"Direct title", L"Direct API content: %s", itemName);
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [
                ("c_confirm", "delete"),
                ("c_confirm", "the item"),
                ("c_runtime_composed", "You are about to "),
                ("c_runtime_composed", "delete"),
                ("c_runtime_composed", " the selected item."),
                ("c_confirm", "delete"),
                ("c_confirm", "the item"),
                ("c_confirm", "Direct conditional message"),
                ("c_runtime_composed", "Composed conditional %s"),
                ("c_confirm", "delete"),
                ("c_confirm", "the item"),
                ("c_runtime_composed", "Allocated prefix "),
                ("c_confirm", "delete"),
                ("c_confirm", "the item"),
                ("c_runtime_composed", "Delete %s now?"),
                ("c_emenu", "Thread count... (auto)"),
                ("c_runtime_composed", "Thread count... (%lu)"),
                ("c_runtime_composed", "Progress 100%% done"),
                ("c_emenu", "Critical action"),
                ("c_emenu", "Normal action"),
                ("c_msgbox", "Direct API format: %s"),
                ("c_msgbox", "Direct title"),
                ("c_msgbox", "Direct API content: %s"),
            ],
        )

    def test_audit_preserves_same_line_one_hop_source_occurrences(self) -> None:
        audit = load_audit_module()
        source = """
            void show_labels(void) {
                PCWSTR first = L"Repeated"; PCWSTR second = L"Repeated";
                PhSetWindowText(firstWindow, first);
                PhSetWindowText(secondWindow, second);
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [entry["english"] for entry in entries],
            ["Repeated", "Repeated"],
        )

    def test_audit_invalidates_hidden_or_overwritten_one_hop_sources(self) -> None:
        audit = load_audit_module()
        long_condition = " && ".join(["flag"] * 100)
        source = """
            PCWSTR globalText = L"Global text";

            void show_labels(PCWSTR parameterText) {
                PCWSTR text = L"Never displayed";
                WCHAR buffer[64];
                PCWSTR shadowed = L"Outer shadow";
                PCWSTR addressWritten = L"Address source";
                PCWSTR blockWritten = L"Block old source";
                PCWSTR lookupText = LookupSetting(L"Not visible setting key");
                PCWSTR mixedText = useValue ? FormatValue(value) : L"Visible fallback";
                PCWSTR comparedText = L"Initial comparison text";
                PCWSTR conditionalAssignment = L"Conditional assignment fallback";
                PCWSTR conditionalMutation = L"Conditional mutation fallback";
                PCWSTR semicolonInitializer = L"Ready; continue";
                PCWSTR semicolonAssignment;
                PCWSTR loggedText = L"Logged initial";
                PCWSTR callLoggedText = L"Call log initial";
                PCWSTR longConditional = L"Long conditional fallback";

                text = runtimeText;
                PhSetWindowText(hwnd, text);

                swprintf_s(buffer, RTL_NUMBER_OF(buffer), L"Formatted %lu", value);
                GetWindowText(otherWindow, buffer, RTL_NUMBER_OF(buffer));
                PhCreateEMenuItem(0, 1, buffer, NULL, NULL);

                UpdateText(&addressWritten);
                PhSetWindowText(hwnd, addressWritten);

                {
                    blockWritten = L"Block visible";
                }
                PhSetWindowText(hwnd, blockWritten);

                {
                    PCWSTR shadowed = L"Inner visible";
                    PhSetWindowText(hwnd, shadowed);
                }

                PhSetWindowText(hwnd, shadowed);
                PhSetWindowText(hwnd, lookupText);
                PhSetWindowText(hwnd, mixedText);
                comparedText == L"Comparison operand";
                PhSetWindowText(hwnd, comparedText);
                if (flag)
                    conditionalAssignment = runtimeText;
                PhSetWindowText(hwnd, conditionalAssignment);
                if (flag)
                    UpdateText(&conditionalMutation);
                PhSetWindowText(hwnd, conditionalMutation);
                semicolonAssignment = L"Assigned; ready";
                PhSetWindowText(hwnd, semicolonInitializer);
                PhSetWindowText(hwnd, semicolonAssignment);
                Log(L"loggedText = not code;");
                PhSetWindowText(hwnd, loggedText);
                Log(L"UpdateText(&callLoggedText)");
                PhSetWindowText(hwnd, callLoggedText);
                if (__LONG_CONDITION__)
                    longConditional = runtimeText;
                PhSetWindowText(hwnd, longConditional);
                PhSetWindowText(hwnd, parameterText);
                PhSetWindowText(hwnd, globalText);
            }
        """.replace("__LONG_CONDITION__", long_condition)
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [
                ("c_window_text", "Block visible"),
                ("c_window_text", "Inner visible"),
                ("c_window_text", "Outer shadow"),
                ("c_window_text", "Visible fallback"),
                ("c_window_text", "Initial comparison text"),
                ("c_window_text", "Conditional assignment fallback"),
                ("c_window_text", "Conditional mutation fallback"),
                ("c_window_text", "Ready; continue"),
                ("c_window_text", "Assigned; ready"),
                ("c_window_text", "Logged initial"),
                ("c_window_text", "Call log initial"),
                ("c_window_text", "Long conditional fallback"),
            ],
        )

    def test_audit_finds_known_repository_one_hop_composed_sources(self) -> None:
        audit = load_audit_module()
        cases = {
            REPO_ROOT / "SystemInformer" / "memsrcht.c": {
                ("c_emenu", "Thread count... (auto)"),
                ("c_runtime_composed", "Thread count... (%lu)"),
            },
            REPO_ROOT / "plugins" / "ExtendedTools" / "tpm.c": {
                ("c_runtime_composed", "0x%08lx"),
            },
            REPO_ROOT / "tools" / "peview" / "misc.c": {
                ("c_runtime_composed", 'Copy "%s"'),
            },
        }

        for source_path, expected in cases.items():
            with self.subTest(source_path=source_path):
                entries = []
                audit.scan_c_file(str(source_path), entries)
                actual = {
                    (entry["category"], entry["english"])
                    for entry in entries
                }
                self.assertTrue(expected <= actual)

    def test_peview_search_path_setting_is_not_a_window_text(self) -> None:
        audit = load_audit_module()
        source_path = REPO_ROOT / "tools" / "peview" / "options.c"
        source = source_path.read_text(encoding="utf-8-sig")
        entries = []

        audit.scan_c_file(str(source_path), entries)

        self.assertIn(
            'PhaGetStringSetting(L"DbgHelpSearchPath")',
            source,
        )
        self.assertIn(
            'PhSetStringSetting2(L"DbgHelpSearchPath"',
            source,
        )
        self.assertFalse(
            any(
                entry["category"] == "c_window_text"
                and entry["english"] == "DbgHelpSearchPath"
                for entry in entries
            )
        )

    def test_audit_merges_conditional_literal_sequences_and_tracks_lines(self) -> None:
        audit = load_audit_module()
        source = """
            void update_status(BOOLEAN flag) {
                PhSetDialogItemText(
                    hwnd,
                    IDC_STATUS,
                    flag
                        ? L"First " L"branch"
                        : L"Other branch"
                );
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [
                (entry["category"], entry["english"], entry["line"])
                for entry in entries
            ],
            [
                (
                    "c_window_text",
                    "First branch",
                    source.count("\n", 0, source.index('L"First "')) + 1,
                ),
                (
                    "c_window_text",
                    "Other branch",
                    source.count("\n", 0, source.index('L"Other branch"')) + 1,
                ),
            ],
        )

    def test_audit_scans_conditional_formats_without_getter_fallbacks(self) -> None:
        audit = load_audit_module()
        source = """
            void show_messages(BOOLEAN flag) {
                PhShowError(
                    hwnd,
                    L"%s",
                    ToolStatusGetUiString(IDS_NATIVE, L"Getter fallback")
                );
                PhShowError(
                    hwnd,
                    flag ? L"Done" : L"%s",
                    L"Details"
                );
                PhShowError(
                    hwnd,
                    flag ? L"%s" : L"Result: %s",
                    L"Shared details"
                );
                PhShowError2(
                    hwnd,
                    L"Conditional title",
                    flag ? L"%s" : L"Prefix: %s",
                    L"Conditional details"
                );
                PhShowError2(
                    hwnd,
                    L"Dynamic format title",
                    flag ? L"%s" : dynamicFormat,
                    L"Dynamic format details"
                );
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [
                ("c_msgbox", "Done"),
                ("c_msgbox_vararg", "Details"),
                ("c_msgbox", "Result: %s"),
                ("c_msgbox_vararg", "Shared details"),
                ("c_msgbox", "Conditional title"),
                ("c_msgbox", "Prefix: %s"),
                ("c_msgbox_vararg", "Conditional details"),
                ("c_msgbox", "Dynamic format title"),
                ("c_msgbox_vararg", "Dynamic format details"),
            ],
        )

    def test_audit_does_not_count_migrated_online_checks_key_status_branches(self) -> None:
        audit = load_audit_module()
        source_path = REPO_ROOT / "plugins" / "OnlineChecks" / "options.c"
        entries = []

        audit.scan_c_file(str(source_path), entries)

        status_entries = Counter(
            entry["english"]
            for entry in entries
            if entry["file"] == "plugins/OnlineChecks/options.c"
            and entry["category"] == "c_window_text"
            and entry["english"] in {
                "Set - using your key",
                "Unset - optional",
            }
        )
        self.assertEqual(status_entries, Counter())

    def test_audit_scans_qualified_macro_struct_combobox_arrays(self) -> None:
        audit = load_audit_module()
        source = """
            static CONST PH_KEY_VALUE_PAIR serviceActionPairs[] = {
                SIP(L"Take no action", 0),
                SIP(L"Restart the service", 1)
            };
            void add_actions(HWND combo) {
                for (ULONG i = 0; i < RTL_NUMBER_OF(serviceActionPairs); i++) {
                    ComboBox_AddString(combo, (PWSTR)serviceActionPairs[i].Key);
                }
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        combo_text = {
            entry["english"]
            for entry in entries
            if entry["category"] == "c_combobox"
        }
        self.assertEqual(combo_text, {"Take no action", "Restart the service"})

    def test_audit_scans_struct_member_group_item_calls(self) -> None:
        audit = load_audit_module()
        source = """
            typedef struct _GROUP_ITEM_ENTRY {
                ULONG Value;
                PCWSTR Name;
                PCWSTR Description;
            } GROUP_ITEM_ENTRY;
            static CONST GROUP_ITEM_ENTRY groupItems[] = {
                { 1, L"First group item", L"First description" },
                {
                    2,
                    PhGetString(PH_AUTO(PhLoadUiString(
                        module, IDS_NATIVE_ITEM, L"Native fallback"))),
                    L"Second description"
                },
                { 3, L"Third group item", L"Third description" }
                // { 4, L"Commented group item", L"Commented description" }
            };
            void add_group_items(void) {
                PhAddListViewGroupItem(
                    list, groupItems[i].Value, i, groupItems[i].Name, NULL);
                PhAddIListViewGroupItem(
                    list, groupItems[i].Value, i, groupItems[i].Name, NULL);
                PhListView_AddGroupItem(
                    list, groupItems[i].Value, i, groupItems[i].Name, NULL);
            }
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        group_item_text = Counter(
            entry["english"]
            for entry in entries
            if entry["category"] == "c_listview_group_item"
        )
        self.assertEqual(
            group_item_text,
            Counter({"First group item": 3, "Third group item": 3}),
        )
        self.assertNotIn("First description", group_item_text)
        self.assertNotIn("Second description", group_item_text)
        self.assertNotIn("Third description", group_item_text)
        self.assertNotIn("Native fallback", group_item_text)
        self.assertNotIn("Commented group item", group_item_text)

    def test_audit_does_not_count_migrated_window_explorer_uia_property_names(self) -> None:
        audit = load_audit_module()
        source_path = REPO_ROOT / "plugins" / "WindowExplorer" / "wndprp.c"
        source = source_path.read_text(encoding="utf-8")
        array_start = source.index("static WND_UIA_PROPERTY WndUiaProperties[]")
        array_end = source.index("\n};", array_start)
        first_line = source.count("\n", 0, array_start) + 1
        last_line = source.count("\n", 0, array_end) + 1
        entries = []

        audit.scan_c_file(str(source_path), entries)

        uia_entries = [
            entry
            for entry in entries
            if entry["category"] == "c_listview_group_item"
            and first_line <= entry["line"] <= last_line
        ]
        self.assertEqual(uia_entries, [])

    def test_main_tray_notification_items_use_native_resources(self) -> None:
        audit = load_audit_module()
        source_path = REPO_ROOT / "SystemInformer" / "options.c"
        source = source_path.read_text(encoding="utf-8")
        masked_source = audit.mask_c_comments(source)
        resource_header = (
            REPO_ROOT / "SystemInformer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = SOURCE_RC.read_text(encoding="utf-8-sig")
        chinese_resource = ZH_CN_RC.read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "IDS_PH_TRAY_NOTIFY_NEW_PROCESSES": (2303, "New processes", "新进程"),
            "IDS_PH_TRAY_NOTIFY_TERMINATED_PROCESSES": (2304, "Terminated processes", "已终止的进程"),
            "IDS_PH_TRAY_NOTIFY_NEW_SERVICES": (2305, "New services", "新服务"),
            "IDS_PH_TRAY_NOTIFY_STARTED_SERVICES": (2306, "Started services", "已启动的服务"),
            "IDS_PH_TRAY_NOTIFY_STOPPED_SERVICES": (2307, "Stopped services", "已停止的服务"),
            "IDS_PH_TRAY_NOTIFY_DELETED_SERVICES": (2308, "Deleted services", "已删除的服务"),
            "IDS_PH_TRAY_NOTIFY_MODIFIED_SERVICES": (2309, "Modified services", "已修改的服务"),
            "IDS_PH_TRAY_NOTIFY_ARRIVED_DEVICES": (2310, "Arrived devices", "新到设备"),
            "IDS_PH_TRAY_NOTIFY_REMOVED_DEVICES": (2311, "Removed devices", "已移除的设备"),
        }
        expected_routes = [
            ("PH_NOTIFY_PROCESS_CREATE", "IDS_PH_TRAY_NOTIFY_NEW_PROCESSES"),
            ("PH_NOTIFY_PROCESS_DELETE", "IDS_PH_TRAY_NOTIFY_TERMINATED_PROCESSES"),
            ("PH_NOTIFY_SERVICE_CREATE", "IDS_PH_TRAY_NOTIFY_NEW_SERVICES"),
            ("PH_NOTIFY_SERVICE_START", "IDS_PH_TRAY_NOTIFY_STARTED_SERVICES"),
            ("PH_NOTIFY_SERVICE_STOP", "IDS_PH_TRAY_NOTIFY_STOPPED_SERVICES"),
            ("PH_NOTIFY_SERVICE_DELETE", "IDS_PH_TRAY_NOTIFY_DELETED_SERVICES"),
            ("PH_NOTIFY_SERVICE_MODIFIED", "IDS_PH_TRAY_NOTIFY_MODIFIED_SERVICES"),
            ("PH_NOTIFY_DEVICE_ARRIVED", "IDS_PH_TRAY_NOTIFY_ARRIVED_DEVICES"),
            ("PH_NOTIFY_DEVICE_REMOVED", "IDS_PH_TRAY_NOTIFY_REMOVED_DEVICES"),
        ]
        array_start = source.index("static PH_TRAYICON_NOTIFY_ITEM TrayIconNotifyItems[]")
        array_end = source.index("\n};", array_start)
        first_line = source.count("\n", 0, array_start) + 1
        last_line = source.count("\n", 0, array_end) + 1
        entries = []

        audit.scan_c_file(str(source_path), entries)

        tray_entries = [
            entry
            for entry in entries
            if entry["category"] == "c_listview_group_item"
            and first_line <= entry["line"] <= last_line
        ]
        actual_routes = re.findall(
            r"\{\s*(PH_NOTIFY_[A-Z_]+),\s*(IDS_PH_TRAY_NOTIFY_[A-Z_]+)\s*\}",
            masked_source[array_start:array_end],
        )

        self.assertEqual(tray_entries, [])
        self.assertEqual(actual_routes, expected_routes)
        self.assertRegex(
            masked_source,
            r"typedef\s+struct\s+_PH_TRAYICON_NOTIFY_ITEM\s*\{\s*"
            r"ULONG\s+Bit;\s*ULONG\s+NameResourceId;\s*\}",
        )
        self.assertRegex(
            masked_source,
            r"PhAddListViewGroupItem\(\s*IconListViewHandle,\s*"
            r"PH_OPTIONS_TRAY_ICON_GROUP_NOTIFICATIONS,\s*MAXINT,\s*"
            r"PhGetApplicationUiString\(TrayIconNotifyItems\[i\]\.NameResourceId\),\s*"
            r"&TrayIconNotifyItems\[i\]\s*\);",
        )

        for resource_id, (numeric_id, english_text, chinese_text) in expected_resources.items():
            with self.subTest(tray_notification_resource=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                self.assertEqual(
                    translation_data["native_strings"].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data["strings"])

        tray_array = masked_source[array_start:array_end]
        self.assertNotIn('L"', tray_array)
        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_STAT_PAGEPRIORITY$",
        )
        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2378$",
        )

    def test_audit_scans_tool_resources_and_stringtables(self) -> None:
        audit = load_audit_module()
        source_files = {
            pathlib.Path(path).resolve().relative_to(REPO_ROOT).as_posix()
            for path in audit.iter_source_files()
        }
        entries = []

        audit.scan_rc_file(
            str(REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc"),
            entries,
        )

        self.assertIn("tools/peview/peview.rc", source_files)
        self.assertIn("tools/CustomSetupTool/resource.rc", source_files)
        self.assertTrue(
            any(
                entry["category"] == "rc_stringtable"
                and entry["english"] == "Downloading update..."
                for entry in entries
            )
        )

    def test_generator_parses_rc_doubled_quotes_as_one_string(self):
        generator = load_generator_module()
        line = (
            '    CONTROL "<a href=""https://example.invalid"">English label</a>",'
            'IDC_LINK'
        )
        translations = {
            '<a href="https://example.invalid">English label</a>':
                '<a href="https://example.invalid">中文标签</a>',
        }

        localized = generator.replace_first_string(line, translations)

        self.assertIn(
            '"<a href=""https://example.invalid"">中文标签</a>"',
            localized,
        )
        self.assertNotIn("English label", localized)

    def test_generator_rejects_unreviewed_dialog_text(self) -> None:
        generator = load_generator_module()

        with self.assertRaisesRegex(ValueError, "missing translation decision"):
            generator.replace_first_string('CAPTION "New upstream dialog"', {})

    def test_generator_rejects_nested_resource_script_includes(self) -> None:
        generator = load_generator_module()

        with self.assertRaisesRegex(ValueError, "nested resource script"):
            generator.source_includes(
                '#include "resource.h"\n#include "upstream-resources.rc2"'
            )

    def test_generator_localizes_stringtable_entries(self) -> None:
        generator = load_generator_module()
        block = [
            "STRINGTABLE",
            "BEGIN",
            '    IDS_SETUP_NEXT "&Next >"',
            "END",
        ]

        localized = generator.localize_stringtable_block(
            block,
            {"&Next >": "下一步(&N) >"},
        )

        self.assertEqual(localized[2], '    IDS_SETUP_NEXT "下一步(&N) >"')

    def test_native_translation_decisions_are_separate_from_runtime_dictionary(self) -> None:
        generator = load_generator_module()
        runtime_generator = load_runtime_translation_generator_module()
        auto_translator = load_auto_translation_module()
        checker = load_translation_checker_module()
        table = {
            "strings": {"Runtime text": "运行时文字"},
            "native_strings": {"Native text": "原生文字"},
        }

        self.assertEqual(
            generator.translation_decisions(table),
            {
                "Runtime text": "运行时文字",
                "Native text": "原生文字",
            },
        )
        self.assertEqual(
            checker.translation_decisions(table),
            {
                "Runtime text": "运行时文字",
                "Native text": "原生文字",
            },
        )
        conflicting_table = {
            "strings": {"Same key": "运行时"},
            "native_strings": {"Same key": "原生"},
        }
        with self.assertRaisesRegex(ValueError, "both strings and native_strings"):
            generator.translation_decisions(conflicting_table)
        with self.assertRaisesRegex(ValueError, "both strings and native_strings"):
            checker.translation_decisions(conflicting_table)
        self.assertTrue(
            checker.is_reviewed_native_identity(
                {"native_strings": {"R: ": "R: "}},
                "rc_stringtable",
                "R: ",
            )
        )
        self.assertFalse(
            checker.is_reviewed_native_identity(
                table,
                "rc_stringtable",
                "Native text",
            )
        )
        self.assertFalse(
            checker.is_reviewed_native_identity(
                {"native_strings": {"R: ": "R: "}},
                "c_listview_group",
                "R: ",
            )
        )
        self.assertFalse(
            auto_translator.needs_automatic_translation(
                {"native_strings": {"R: ": "R: "}},
                "R: ",
            )
        )
        self.assertTrue(
            auto_translator.needs_automatic_translation(
                {"strings": {"Pending": "Pending"}},
                "Pending",
            )
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8"
        ) as translation_file:
            json.dump(table, translation_file, ensure_ascii=False)
            translation_file.flush()
            content, count = runtime_generator.build(translation_file.name)

        self.assertEqual(count, 1)
        self.assertIn('L"Runtime text", L"运行时文字"', content)
        self.assertNotIn("Native text", content)

    def test_generator_preserves_stringtable_line_break_escapes(self) -> None:
        generator = load_generator_module()
        line = r'    IDS_SETUP_MESSAGE "First\r\nSecond"'

        localized = generator.replace_first_string(
            line,
            {"First\r\nSecond": "第一行\r\n第二行"},
            decode_escapes=True,
        )

        self.assertEqual(localized, r'    IDS_SETUP_MESSAGE "第一行\r\n第二行"')

    def test_compiled_dialog_parser_separates_structure_text_and_font(self) -> None:
        validator = load_validator_module()
        english = validator.parse_dialog_template(
            make_dialog_template("General", "Options", 8, "MS Shell Dlg")
        )
        chinese = validator.parse_dialog_template(
            make_dialog_template("常规", "设置", 9, "Microsoft YaHei UI")
        )

        self.assertEqual(english["structure"], chinese["structure"])
        self.assertEqual(chinese["font"][0], 9)
        self.assertEqual(chinese["font"][-1], "Microsoft YaHei UI")
        self.assertEqual(chinese["strings"], ["常规", "设置", "Tail"])

    def test_compiled_stringtable_parser_preserves_slots(self) -> None:
        validator = load_validator_module()
        strings = validator.parse_stringtable_block(
            make_stringtable_block({0: "Back", 3: "完成", 8: "😀", 15: "Retry"})
        )

        self.assertEqual(strings[0], "Back")
        self.assertEqual(strings[3], "完成")
        self.assertEqual(strings[8], "😀")
        self.assertEqual(strings[15], "Retry")
        self.assertEqual(len(strings), 16)
        self.assertEqual(
            validator.format_specifiers("Error %lu: %s"),
            validator.format_specifiers("错误 %lu：%s"),
        )
        self.assertNotEqual(
            validator.format_specifiers("Error %s: %lu"),
            validator.format_specifiers("错误 %lu：%s"),
        )
        self.assertEqual(
            validator.format_specifiers("%.*s / %-08I64u"),
            ["%.*s", "%-08I64u"],
        )
        self.assertEqual(
            validator.format_specifiers(
                "Append /fail=%1% to pass the fail count to the program."
            ),
            [],
        )
        self.assertTrue(validator.required_string_resources_missing(set(), True))
        self.assertFalse(validator.required_string_resources_missing(set(), False))
        self.assertFalse(validator.required_string_resources_missing({2000}, True))
        self.assertTrue(validator.string_resource_count_mismatch({2000}, 41))
        self.assertFalse(validator.string_resource_count_mismatch(set(range(41)), 41))
        self.assertFalse(validator.string_resource_count_mismatch({2000}, None))

    def test_source_translation_placeholder_check_preserves_order_and_flags(self) -> None:
        checker = load_translation_checker_module()

        self.assertIsNone(
            checker.check_placeholders("Error %lu: %s", "错误 %lu：%s")
        )
        self.assertIsNotNone(
            checker.check_placeholders("Error %s: %lu", "错误 %lu：%s")
        )
        self.assertEqual(
            checker.format_specs("%.*s / %-08I64u"),
            ["%.*s", "%-08I64u"],
        )
        self.assertEqual(
            checker.format_specs(
                "Append /fail=%1% to pass the fail count to the program."
            ),
            [],
        )
        self.assertTrue(checker.translation_is_effective("c_msgbox", "已翻译"))
        self.assertFalse(
            checker.translation_is_effective("c_msgbox_vararg", "已翻译")
        )
        self.assertTrue(
            checker.translation_is_effective("c_listview_group", "已翻译")
        )
        for category in (
            "c_window_text",
            "c_combobox",
            "c_listview_group_item",
        ):
            with self.subTest(callsite_migration_category=category):
                self.assertFalse(
                    checker.translation_is_effective(category, "已翻译")
                )

    def test_checker_native_only_decisions_apply_only_to_native_resources(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 4,
            "unique_strings": [
                {
                    "english": "Connected",
                    "category": "rc_stringtable",
                    "locations": [{"file": "plugins/Test/Test.rc", "line": 1}],
                },
                {
                    "english": "Connected",
                    "category": "c_listview_group",
                    "locations": [{"file": "plugins/Test/test.c", "line": 2}],
                },
                {
                    "english": "R: ",
                    "category": "rc_stringtable",
                    "locations": [{"file": "plugins/Test/Test.rc", "line": 3}],
                },
                {
                    "english": "R: ",
                    "category": "c_listview_group",
                    "locations": [{"file": "plugins/Test/test.c", "line": 4}],
                },
            ]
        }
        translations = {
            "strings": {},
            "native_strings": {
                "Connected": "已连接",
                "R: ": "R: ",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            manifest_path = temp_path / "manifest.json"
            translation_path = temp_path / "zh-CN.json"
            report_path = temp_path / "coverage-report.md"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            translation_path.write_text(
                json.dumps(translations, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "zhcn" / "check_translation.py"),
                    "--manifest",
                    str(manifest_path),
                    "--translation",
                    str(translation_path),
                    "--report",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(
                "translation audit: translated 1/3, untranslated 2",
                result.stdout,
            )
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("| rc_stringtable | 1 | 1 | 0 |", report)
            self.assertIn("| c_listview_group | 0 | 2 | 2 |", report)
            self.assertIn("- `R: ` (plugins/Test/test.c:4)", report)
            self.assertIn("- `R: ` (rc_stringtable)", report)

    def test_checker_callsite_migration_categories_ignore_all_dictionaries(self) -> None:
        categories = (
            "c_combobox",
            "c_listview_group_item",
            "c_msgbox_vararg",
            "c_window_text",
            "c_balloon",
        )
        manifest = {
            "schema_version": 2,
            "total_occurrences": len(categories),
            "unique_strings": [
                {
                    "module": "plugins/Test",
                    "english": f"Callsite text {index}",
                    "category": category,
                    "locations": [{"file": "plugins/Test/test.c", "line": index}],
                }
                for index, category in enumerate(categories, start=1)
            ]
        }
        translations = {
            "strings": {
                "Callsite text 1": "调用点文字 1",
                "Callsite text 2": "调用点文字 2",
            },
            "native_strings": {
                "Callsite text 3": "调用点文字 3",
                "Callsite text 4": "调用点文字 4",
                "Callsite text 5": "调用点文字 5",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            manifest_path = temp_path / "manifest.json"
            translation_path = temp_path / "zh-CN.json"
            report_path = temp_path / "coverage-report.md"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            translation_path.write_text(
                json.dumps(translations, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "zhcn" / "check_translation.py"),
                    "--manifest",
                    str(manifest_path),
                    "--translation",
                    str(translation_path),
                    "--report",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(
                "translation audit: translated 0/5, untranslated 5",
                result.stdout,
            )

    def test_checker_uses_the_translation_source_for_each_category(self) -> None:
        checker = load_translation_checker_module()
        table = {
            "strings": {"Runtime text": "运行时文字"},
            "native_strings": {"Native text": "原生文字"},
        }

        for category in checker.NATIVE_RESOURCE_CATEGORIES:
            with self.subTest(native_resource_category=category):
                self.assertEqual(
                    checker.translation_for_category(
                        table, category, "Runtime text"
                    ),
                    "运行时文字",
                )
                self.assertEqual(
                    checker.translation_for_category(
                        table, category, "Native text"
                    ),
                    "原生文字",
                )

        for category in checker.RUNTIME_DICTIONARY_CATEGORIES:
            with self.subTest(runtime_dictionary_category=category):
                self.assertEqual(
                    checker.translation_for_category(
                        table, category, "Runtime text"
                    ),
                    "运行时文字",
                )
                self.assertIsNone(
                    checker.translation_for_category(
                        table, category, "Native text"
                    )
                )

        for category in checker.CALLSITE_MIGRATION_CATEGORIES:
            with self.subTest(callsite_migration_category=category):
                self.assertIsNone(
                    checker.translation_for_category(
                        table, category, "Runtime text"
                    )
                )
                self.assertIsNone(
                    checker.translation_for_category(
                        table, category, "Native text"
                    )
                )

    def test_checker_classifies_every_category_emitted_by_the_audit(self) -> None:
        checker = load_translation_checker_module()
        audit_source = (
            REPO_ROOT / "tools" / "zhcn" / "audit.py"
        ).read_text(encoding="utf-8")
        audit_categories = set(
            re.findall(r'"((?:rc|c|phlib)_[a-z_]+)"', audit_source)
        )
        category_sets = (
            checker.NATIVE_RESOURCE_CATEGORIES,
            checker.RUNTIME_DICTIONARY_CATEGORIES,
            checker.CALLSITE_MIGRATION_CATEGORIES,
        )

        self.assertEqual(set().union(*category_sets), audit_categories)
        for index, left in enumerate(category_sets):
            for right in category_sets[index + 1:]:
                self.assertTrue(left.isdisjoint(right))

    def test_compiled_dialog_parser_keeps_control_ordinals_in_structure(self) -> None:
        validator = load_validator_module()
        english = validator.parse_dialog_template(
            make_dialog_template(
                "About", "", 8, "MS Shell Dlg", item_text_ordinal=100
            )
        )
        chinese = validator.parse_dialog_template(
            make_dialog_template(
                "关于", "", 9, "Microsoft YaHei UI", item_text_ordinal=101
            )
        )

        self.assertNotEqual(english["structure"], chinese["structure"])

    def test_compiled_dialog_parser_accepts_unpadded_final_item(self) -> None:
        validator = load_validator_module()
        template = make_dialog_template(
            "General", "Options", 8, "MS Shell Dlg", pad_end=False,
            tail_label="Final",
        )

        self.assertEqual(len(template) % 4, 2)
        parsed = validator.parse_dialog_template(template)

        self.assertEqual(parsed["strings"], ["General", "Options", "Final"])

    def test_compiled_dialog_parser_does_not_treat_fixedsys_as_font(self) -> None:
        validator = load_validator_module()
        template = make_dialog_template(
            "General", "Options", 8, "unused", set_font=False
        )

        parsed = validator.parse_dialog_template(template)

        self.assertIsNone(parsed["font"])

    def test_compiled_dialog_font_attributes_exclude_only_size_and_face(self) -> None:
        validator = load_validator_module()
        baseline = validator.parse_dialog_template(
            make_dialog_template("General", "Options", 8, "MS Shell Dlg")
        )
        changed_weight = validator.parse_dialog_template(
            make_dialog_template(
                "常规", "设置", 9, "Microsoft YaHei UI", weight=700
            )
        )

        self.assertNotEqual(
            validator.dialog_font_attributes(baseline["font"]),
            validator.dialog_font_attributes(changed_weight["font"]),
        )

    def test_all_generated_resources_are_current(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("14 modules", result.stdout)
        self.assertIn("270 dialogs", result.stdout)
        self.assertIn("1270 strings", result.stdout)

    def test_generated_utf8_resource_does_not_redeclare_code_page(self) -> None:
        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")

        self.assertTrue(ZH_CN_RC.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("#pragma code_page", localized)

    def test_main_dialog_resource_ids_match_english_source(self) -> None:
        source = SOURCE_RC.read_text(encoding="utf-8-sig")
        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        source_ids = DIALOG_RE.findall(source)
        localized_ids = DIALOG_RE.findall(localized)

        self.assertGreater(len(source_ids), 50)
        self.assertEqual(localized_ids, source_ids)

    def test_localized_dialogs_preserve_source_font_metrics(self) -> None:
        source = SOURCE_RC.read_text(encoding="utf-8-sig")
        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        source_fonts = FONT_RE.findall(source)
        fonts = FONT_RE.findall(localized)

        self.assertIn("LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED", localized)
        self.assertGreater(len(fonts), 50)
        self.assertEqual(fonts, source_fonts)

    def test_native_resource_is_compiled_and_checked_by_ci(self) -> None:
        project = (REPO_ROOT / "SystemInformer" / "SystemInformer.vcxproj").read_text(
            encoding="utf-8-sig"
        )
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn('<ResourceCompile Include="SystemInformer.zh-cn.rc" />', project)
        self.assertIn("generate_native_resources.py --check", workflow)

    def test_plugin_native_resources_are_compiled_by_their_projects(self) -> None:
        for module_name in PLUGIN_MODULES:
            with self.subTest(module=module_name):
                module_dir = REPO_ROOT / "plugins" / module_name
                localized_name = f"{module_name}.zh-cn.rc"
                localized = module_dir / localized_name
                project_root = ET.parse(
                    module_dir / f"{module_name}.vcxproj"
                ).getroot()
                filters_root = ET.parse(
                    module_dir / f"{module_name}.vcxproj.filters"
                ).getroot()
                project_resources = [
                    element.attrib.get("Include")
                    for element in project_root.iter()
                    if element.tag.endswith("ResourceCompile")
                ]
                filter_resources = [
                    element
                    for element in filters_root.iter()
                    if element.tag.endswith("ResourceCompile")
                    and element.attrib.get("Include") == localized_name
                ]

                self.assertTrue(localized.is_file())
                self.assertTrue(localized.read_bytes().startswith(b"\xef\xbb\xbf"))
                self.assertEqual(project_resources.count(localized_name), 1)
                self.assertEqual(len(filter_resources), 1)
                filter_names = [
                    child.text
                    for child in filter_resources[0]
                    if child.tag.endswith("Filter")
                ]
                self.assertEqual(filter_names, ["Resource Files"])

    def test_plugin_dialog_resource_ids_and_fonts_match_english_sources(self) -> None:
        for module_name in PLUGIN_MODULES:
            with self.subTest(module=module_name):
                module_dir = REPO_ROOT / "plugins" / module_name
                source = (module_dir / f"{module_name}.rc").read_text(
                    encoding="utf-8-sig"
                )
                localized = (module_dir / f"{module_name}.zh-cn.rc").read_text(
                    encoding="utf-8-sig"
                )
                source_ids = DIALOG_RE.findall(source)
                localized_ids = DIALOG_RE.findall(localized)
                source_string_ids = stringtable_ids(source)
                localized_string_ids = stringtable_ids(localized)
                source_fonts = FONT_RE.findall(source)
                fonts = FONT_RE.findall(localized)

                self.assertGreater(len(source_ids), 0)
                self.assertEqual(localized_ids, source_ids)
                self.assertEqual(localized_string_ids, source_string_ids)
                self.assertEqual(len(fonts), len(source_ids))
                self.assertIn(
                    "LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED",
                    localized,
                )
                self.assertEqual(fonts, source_fonts)

    def test_tool_native_resources_match_sources_and_projects(self) -> None:
        for module_name, source_path, localized_path, project_path, filters_path in TOOL_MODULES:
            with self.subTest(module=module_name):
                source = source_path.read_text(encoding="utf-8-sig")
                localized = localized_path.read_text(encoding="utf-8-sig")
                source_ids = DIALOG_RE.findall(source)
                localized_ids = DIALOG_RE.findall(localized)
                source_string_ids = stringtable_ids(source)
                localized_string_ids = stringtable_ids(localized)
                source_fonts = FONT_RE.findall(source)
                fonts = FONT_RE.findall(localized)
                localized_name = localized_path.name
                project_root = ET.parse(project_path).getroot()
                filters_root = ET.parse(filters_path).getroot()
                project_resources = [
                    element.attrib.get("Include")
                    for element in project_root.iter()
                    if element.tag.endswith("ResourceCompile")
                ]
                filter_resources = [
                    element
                    for element in filters_root.iter()
                    if element.tag.endswith("ResourceCompile")
                    and element.attrib.get("Include") == localized_name
                ]

                self.assertGreater(len(source_ids), 0)
                self.assertEqual(localized_ids, source_ids)
                self.assertEqual(localized_string_ids, source_string_ids)
                self.assertEqual(len(fonts), len(source_ids))
                self.assertTrue(localized_path.read_bytes().startswith(b"\xef\xbb\xbf"))
                self.assertIn(
                    "LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED",
                    localized,
                )
                self.assertEqual(fonts, source_fonts)
                self.assertEqual(project_resources.count(localized_name), 1)
                self.assertEqual(len(filter_resources), 1)
                self.assertEqual(
                    [
                        child.text
                        for child in filter_resources[0]
                        if child.tag.endswith("Filter")
                    ],
                    ["Resource Files"],
                )

    def test_custom_sign_tool_has_no_localizable_ui_resources(self) -> None:
        source = (
            REPO_ROOT / "tools" / "CustomSignTool" / "resource.rc"
        ).read_text(encoding="utf-8-sig")

        self.assertIsNone(DIALOG_RE.search(source))
        self.assertIsNone(
            re.search(
                r"(?m)^\s*(?:(?:[A-Z][A-Z0-9_]*|\d+)\s+)?"
                r"(?:MENU(?:EX)?|STRINGTABLE)\b",
                source,
            )
        )

    def test_localized_tools_select_zh_cn_ui_language(self) -> None:
        for relative_path in (
            "tools/peview/main.c",
            "tools/CustomSetupTool/main.c",
        ):
            with self.subTest(source=relative_path):
                source = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")

                self.assertRegex(
                    source,
                    r"PhSetApplicationUiLanguage\(\s*"
                    r"MAKELANGID\(LANG_CHINESE,\s*SUBLANG_CHINESE_SIMPLIFIED\)",
                )
                self.assertIn("PhTranslationEnabled = TRUE;", source)

    def test_tool_property_pages_use_language_aware_resource_loader(self) -> None:
        peview = (REPO_ROOT / "tools" / "peview" / "prpsh.c").read_text(
            encoding="utf-8-sig"
        )
        setup = (
            REPO_ROOT / "tools" / "CustomSetupTool" / "wizard.c"
        ).read_text(encoding="utf-8-sig")

        self.assertNotRegex(peview, r"(?<!Ph)CreatePropertySheetPage\s*\(")
        self.assertRegex(
            peview,
            r"if \(!propSheetPageHandle\)\s*\{\s*"
            r"PhDereferenceObject\(PropPageContext\);\s*return FALSE;",
        )
        self.assertRegex(
            peview,
            r"return PvCreatePropPageContextEx\(\s*"
            r"PhInstanceHandle,\s*Template,\s*DlgProc,\s*Context\s*\);",
        )
        self.assertIn("PhCreatePropertySheetPage(&pageDefinitions[pageIndex])", setup)
        self.assertIn("header.phpage = pages;", setup)
        self.assertNotIn("PSH_PROPSHEETPAGE", setup)
        self.assertNotIn("header.ppsp = pages;", setup)

    def test_peview_uses_dpi_aware_system_message_font(self) -> None:
        peview = (REPO_ROOT / "tools" / "peview" / "prpsh.c").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("newFont = PhCreateMessageFont(dpiValue);", peview)
        self.assertIn("PhApplicationFont = newFont;", peview)
        self.assertIn(
            "SetWindowFont(PropSheet_GetTabControl(hwnd), newFont, TRUE);",
            peview,
        )
        self.assertNotIn("DeleteFont(PhApplicationFont);", peview)
        self.assertNotIn('PvpCreateFont(L"Microsoft Sans Serif"', peview)
        self.assertNotIn('PvpCreateFont(L"Tahoma"', peview)

    def test_peview_context_menus_use_native_string_resources(self) -> None:
        peview_header = (
            REPO_ROOT / "tools" / "peview" / "include" / "peview.h"
        ).read_text(encoding="utf-8-sig")
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "peview").glob("*.c")
        )
        resource_header = (
            REPO_ROOT / "tools" / "peview" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "tools" / "peview" / "peview.rc"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("PvpLoadUiString", peview_header)
        self.assertIn("IDS_PV_MENU_DISPLAY_RESOURCE", resource_header)
        self.assertIn("IDS_PV_MENU_SAVE_CERTIFICATE", resource_header)
        self.assertEqual(len(stringtable_ids(resource_script)), 218)

        migrated_labels = (
            "ANSI",
            "UTF-8",
            "UTF-16",
            "Extended character set",
            "Skip .text section",
            "Skip high entropy sections",
            "Skip strings with numbers",
            "Skip strings with symbols",
            "Minimum length...",
            "Refresh",
            "Hide writable",
            "Hide executable",
            "Hide code",
            "Hide readable",
            "Hide parameters",
            "Filter non-writable",
            "Highlight writable",
            "Highlight executable",
            "Highlight code",
            "Highlight readable",
            "Display resource...",
            "Save resource...",
            "Copy",
            "View certificate...",
            "Save certificate...",
            "&Copy",
            "Delete",
            "Size column to fit",
            "Size all columns to fit",
            "Hide column",
            "Choose columns...",
            "Reset sort",
        )
        for label in migrated_labels:
            self.assertNotRegex(
                source,
                rf"PhCreateEMenuItem\([^\n]*L\"{re.escape(label)}\"",
            )

    def test_peview_column_labels_use_native_string_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "peview").glob("*.c")
        )

        for function_name in ("PhAddListViewColumn", "PhAddTreeNewColumn"):
            calls = re.findall(
                rf"{function_name}\((.*?)\);",
                source,
                re.DOTALL,
            )
            self.assertTrue(calls)
            for call in calls:
                self.assertLessEqual(
                    set(re.findall(r'L"([^"\r\n]+)"', call)),
                    {"#"},
                )

    def test_peview_hash_groups_use_native_string_resources(self) -> None:
        source = (REPO_ROOT / "tools" / "peview" / "hashprp.c").read_text(
            encoding="utf-8-sig"
        )
        resource_header = (
            REPO_ROOT / "tools" / "peview" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_rc = (
            REPO_ROOT / "tools" / "peview" / "peview.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_rc = (
            REPO_ROOT / "tools" / "peview" / "peview.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_groups = (
            (
                "IDS_PV_GROUP_FILE_HASHES",
                3128,
                "PV_HASHLIST_CATEGORY_FILEHASH",
                "File hashes",
                "文件哈希",
            ),
            (
                "IDS_PV_GROUP_IMPORT_HASHES",
                3129,
                "PV_HASHLIST_CATEGORY_IMPORTHASH",
                "Import hashes",
                "导入哈希",
            ),
            (
                "IDS_PV_GROUP_FUZZY_HASHES",
                3130,
                "PV_HASHLIST_CATEGORY_FUZZYHASH",
                "Fuzzy hashes",
                "模糊哈希",
            ),
            (
                "IDS_PV_GROUP_AUTHENTICODE_HASHES",
                3131,
                "PV_HASHLIST_CATEGORY_AUTHENTIHASH",
                "Authenticode hashes",
                "Authenticode 哈希",
            ),
            (
                "IDS_PV_GROUP_WDAC_PAGE_HASHES",
                3132,
                "PV_HASHLIST_CATEGORY_WDACPAGEHASH",
                "Page hashes (WDAC)",
                "页哈希（WDAC）",
            ),
            (
                "IDS_PV_GROUP_AUTHENTICODE_PAGE_HASHES",
                3133,
                "PV_HASHLIST_CATEGORY_PAGEHASH",
                "Page hashes (Authenticode)",
                "页哈希（Authenticode）",
            ),
        )

        for resource_id, numeric_id, group_id, english_text, chinese_text in expected_groups:
            with self.subTest(hash_group=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_rc,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_rc,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                self.assertEqual(
                    translation_data["native_strings"].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data["strings"])
                self.assertNotIn(f'L"{english_text}"', source)
                self.assertRegex(
                    source,
                    rf"PhAddListViewGroup\(\s*context->ListViewHandle,\s*"
                    rf"{group_id},\s*PvpLoadUiString\({resource_id}\)\s*\);",
                )

        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+IDS_PV_LAST\s+IDS_PV_FIELD_FILE_LAST_USN$",
        )
        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3218$",
        )
        self.assertEqual(len(stringtable_ids(english_rc)), 218)
        self.assertEqual(len(stringtable_ids(chinese_rc)), 218)

    def test_peview_options_and_error_messages_use_native_string_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "peview").glob("*.c")
        )
        migrated_labels = (
            "Enable theme support",
            "Enable legacy properties window",
            "Enable view borders",
            "Remember last selected window",
            "Do you want to reset all settings and restart PE Viewer?",
            "Do you want to restart PE Viewer now?",
            "One or more options you have changed requires a restart of PE Viewer.",
            "PE View's settings file is corrupt. Do you want to reset it?",
            "PE Viewer does not support this image type.",
            "PE Viewer has crashed :(",
            "Unable to create the CLR table preview window.",
            "Unable to enumerate the image resources.",
            "Unable to locate the resource data.",
            "Unable to preview CLR table rows because CLR metadata is unavailable.",
            "You are attempting to run the 32-bit version of PE Viewer on 64-bit Windows.",
        )

        for label in migrated_labels:
            self.assertNotIn(f'L"{label}', source)

        for function_name in (
            "PhShowError",
            "PhShowError2",
            "PhShowMessage",
            "PhShowMessage2",
            "PhShowStatus",
            "PhShowWarning2",
        ):
            calls = re.findall(
                rf"{function_name}\s*\((.*?)\);",
                source,
                re.DOTALL,
            )
            for call in calls:
                with self.subTest(function=function_name, call=call):
                    self.assertLessEqual(
                        set(re.findall(r'L"(?:[^"\\]|\\.)*"', call)),
                        {'L""', 'L"%s"'},
                    )

    def test_main_options_messages_use_native_string_resources(self) -> None:
        options = (REPO_ROOT / "SystemInformer" / "options.c").read_text(
            encoding="utf-8-sig"
        )
        main = (REPO_ROOT / "SystemInformer" / "main.c").read_text(
            encoding="utf-8-sig"
        )
        resource_script = SOURCE_RC.read_text(encoding="utf-8-sig")

        self.assertEqual(len(stringtable_ids(resource_script)), 378)
        self.assertIn(
            "static PPH_STRING PhApplicationUiStrings[IDS_PH_LAST - IDS_PH_FIRST + 1]",
            main,
        )
        self.assertIn("if (!PhpInitializeApplicationUiStrings())", main)

        resource_ids = set(stringtable_ids(resource_script))
        application_source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (
                *(REPO_ROOT / "SystemInformer").glob("*.c"),
                REPO_ROOT / "phlib" / "guisup.c",
                REPO_ROOT / "phlib" / "mapldr.c",
                REPO_ROOT / "phlib" / "util.c",
            )
        )
        used_ids = set(
            re.findall(
                r"\b(IDS_PH_[A-Z0-9_]+)\b",
                application_source,
            )
        ) - {"IDS_PH_FIRST", "IDS_PH_LAST"}
        self.assertEqual(used_ids, resource_ids)

        resource_header = (
            REPO_ROOT / "SystemInformer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        resource_header += (
            REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
        ).read_text(encoding="utf-8-sig")
        numeric_ids = [
            int(value)
            for _, value in re.findall(
                r"^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)$",
                resource_header,
                re.MULTILINE,
            )
        ]
        self.assertEqual(sorted(numeric_ids), list(range(2000, 2378)))
        self.assertNotRegex(options, r"\bmessage\s*=\s*L\"")
        self.assertNotRegex(
            options,
            r"PhShowOptionsDefaultInstallLocation\([^;]*L\"",
        )

        for function_name in (
            "PhShowError",
            "PhShowError2",
            "PhShowInformation2",
            "PhShowMessage",
            "PhShowMessage2",
            "PhShowStatus",
            "PhShowWarning2",
        ):
            calls = re.findall(
                rf"{function_name}\s*\((.*?)\);",
                options,
                re.DOTALL,
            )
            for call in calls:
                with self.subTest(function=function_name, call=call):
                    self.assertLessEqual(
                        set(re.findall(r'L"(?:[^"\\]|\\.)*"', call)),
                        {'L""', 'L"%s"'},
                    )

    def test_plugin_manager_metadata_uses_native_string_resources(self) -> None:
        plugman = (REPO_ROOT / "SystemInformer" / "plugman.c").read_text(
            encoding="utf-8-sig"
        )
        resource_script = SOURCE_RC.read_text(encoding="utf-8-sig")
        resource_texts = dict(re.findall(
            r'^\s*(IDS_PH_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        plugin_modules = (
            "UserNotes",
            "ExtendedTools",
            "ExtendedNotifications",
            "DotNetTools",
            "OnlineChecks",
            "Updater",
            "NetworkTools",
            "HardwareDevices",
            "WindowExplorer",
            "ToolStatus",
            "ExtendedServices",
        )
        expected_plugins = []
        for module_name in plugin_modules:
            plugin_directory = REPO_ROOT / "plugins" / module_name
            plugin_headers = "\n".join(
                path.read_text(encoding="utf-8-sig")
                for path in plugin_directory.glob("*.h")
            )
            plugin_main = (plugin_directory / "main.c").read_text(
                encoding="utf-8-sig"
            )
            internal_name = re.search(
                r'^#define\s+PLUGIN_NAME\s+L"([^"]+)"',
                plugin_headers,
                re.MULTILINE,
            ).group(1)
            display_name = re.search(
                r'info->DisplayName\s*=\s*L"([^"]+)"',
                plugin_main,
            ).group(1)
            description_assignment = re.search(
                r'info->Description\s*=\s*((?:L"[^"]*"\s*)+);',
                plugin_main,
                re.DOTALL,
            ).group(1)
            description = "".join(re.findall(r'L"([^"]*)"', description_assignment))
            expected_plugins.append((internal_name, display_name, description))
        routed_plugins = re.findall(
            r'\{\s*L"([^"]+)",\s*(IDS_PH_PLUGIN_[A-Z0-9_]+_NAME),\s*'
            r'(IDS_PH_PLUGIN_[A-Z0-9_]+_DESCRIPTION)\s*\}',
            plugman,
        )

        self.assertEqual(len(routed_plugins), len(expected_plugins))
        for (internal_name, display_name, description), route in zip(
            expected_plugins,
            routed_plugins,
        ):
            with self.subTest(plugin_internal_name=internal_name):
                self.assertEqual(route[0], internal_name)
                self.assertEqual(resource_texts[route[1]], display_name)
                self.assertEqual(resource_texts[route[2]], description)

        add_node = plugman[
            plugman.index("PPH_PLUGIN_TREE_ROOT_NODE AddPluginsNode("):
            plugman.index("PPH_PLUGIN_TREE_ROOT_NODE FindPluginsNode(")
        ]
        refresh_details = plugman[
            plugman.rindex("VOID PhpRefreshPluginDetails("):
            plugman.rindex("INT_PTR CALLBACK PhpPluginPropertiesDlgProc(")
        ]
        self.assertIn("PhpGetPluginLocalizedInformation", add_node)
        self.assertIn("PhpGetPluginLocalizedInformation", refresh_details)
        self.assertIn("IDS_PH_PLUGIN_UNNAMED", refresh_details)
        self.assertIn("IDS_PH_PLUGIN_VERSION_UNKNOWN", refresh_details)

        manager_labels = {
            "IDS_PH_PLUGIN_COLUMN": "Plugin",
            "IDS_PH_PLUGIN_DISABLED_COUNT": "Disabled Plugins (%lu)",
            "IDS_PH_PLUGIN_DISABLE": "Disable",
            "IDS_PH_PLUGIN_PROPERTIES": "Properties",
            "IDS_PH_PLUGIN_PROPERTY_COLUMN": "Property",
        }
        for resource_id, english_text in manager_labels.items():
            with self.subTest(plugin_manager_resource_id=resource_id):
                self.assertEqual(resource_texts[resource_id], english_text)
                self.assertNotIn(f'L"{english_text}"', plugman)

        self.assertEqual(
            len(re.findall(
                r"PhaFormatString\(\s*"
                r"PhGetApplicationUiString\(IDS_PH_PLUGIN_DISABLED_COUNT\),\s*"
                r"PhpDisabledPluginsCount\(\)\s*\)",
                plugman,
            )),
            3,
        )
        manager_routes = {
            "IDS_PH_PLUGIN_COLUMN": r"PhAddTreeNewColumnEx2\([^;]*IDS_PH_PLUGIN_COLUMN[^;]*\);",
            "IDS_PH_PLUGIN_DISABLE": r"PhCreateEMenuItem\([^;]*IDS_PH_PLUGIN_DISABLE[^;]*\)",
            "IDS_PH_PLUGIN_PROPERTIES": r"PhCreateEMenuItem\([^;]*IDS_PH_PLUGIN_PROPERTIES[^;]*\)",
            "IDS_PH_PLUGIN_PROPERTY_COLUMN": r"PhAddListViewColumn\([^;]*IDS_PH_PLUGIN_PROPERTY_COLUMN[^;]*\);",
        }
        for resource_id, route_pattern in manager_routes.items():
            with self.subTest(plugin_manager_route=resource_id):
                self.assertRegex(plugman, route_pattern)

    def test_main_combo_and_service_labels_use_native_resources(self) -> None:
        source_paths = (
            "options.c",
            "runas.c",
            "hidnproc.c",
            "sessmsg.c",
            "findobj.c",
            "affinity.c",
            "memedit.c",
            "srvctl.c",
        )
        source = "\n".join(
            (REPO_ROOT / "SystemInformer" / path).read_text(encoding="utf-8-sig")
            for path in source_paths
        )
        resource_script = SOURCE_RC.read_text(encoding="utf-8-sig")
        resource_texts = dict(re.findall(
            r'^\s*(IDS_PH_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        expected_routes = {
            "IDS_PH_THEME_AUTOMATIC": ("Automatic", 1),
            "IDS_PH_THEME_LIGHT": ("Light", 1),
            "IDS_PH_THEME_DARK": ("Dark", 1),
            "IDS_PH_THEME_CUSTOM": ("Custom", 1),
            "IDS_PH_LOGON_BATCH": ("Batch", 1),
            "IDS_PH_LOGON_INTERACTIVE": ("Interactive", 1),
            "IDS_PH_LOGON_NETWORK": ("Network", 1),
            "IDS_PH_LOGON_NEW_CREDENTIALS": ("New credentials", 1),
            "IDS_PH_LOGON_SERVICE": ("Service", 1),
            "IDS_PH_HIDDEN_PROCESS_BRUTE_FORCE": ("Brute force", 1),
            "IDS_PH_HIDDEN_PROCESS_CSR_HANDLES": ("CSR handles", 1),
            "IDS_PH_HIDDEN_PROCESS_ETW_HANDLES": ("ETW handles", 1),
            "IDS_PH_HIDDEN_PROCESS_PROCESS_HANDLES": ("Process handles", 1),
            "IDS_PH_HIDDEN_PROCESS_REGISTRY_HANDLES": ("Registry handles", 1),
            "IDS_PH_HIDDEN_PROCESS_NTDLL_HANDLES": ("Ntdll handles", 1),
            "IDS_PH_FIND_EVERYTHING": ("Everything", 1),
            "IDS_PH_PROCESSOR_GROUP_FORMAT": ("Group %hu", 1),
            "IDS_PH_MESSAGE_ICON_NONE": ("None", 1),
            "IDS_PH_MESSAGE_ICON_INFORMATION": ("Information", 1),
            "IDS_PH_MESSAGE_ICON_WARNING": ("Warning", 1),
            "IDS_PH_MESSAGE_ICON_ERROR": ("Error", 1),
            "IDS_PH_MESSAGE_ICON_QUESTION": ("Question", 1),
            "IDS_PH_BYTES_PER_ROW_FORMAT": ("%u bytes per row", 2),
            "IDS_PH_SERVICE_STOP": ("S&top", 2),
            "IDS_PH_SERVICE_PAUSE": ("&Pause", 4),
            "IDS_PH_SERVICE_CONTINUE": ("C&ontinue", 1),
            "IDS_PH_SERVICE_START": ("&Start", 3),
        }
        item_data_resource_ids = {
            resource_id
            for resource_id in expected_routes
            if resource_id.startswith((
                "IDS_PH_LOGON_",
                "IDS_PH_HIDDEN_PROCESS_",
                "IDS_PH_MESSAGE_ICON_",
            ))
        }

        for resource_id, (english_text, expected_count) in expected_routes.items():
            with self.subTest(main_native_label=resource_id):
                self.assertEqual(resource_texts.get(resource_id), english_text)
                if resource_id in item_data_resource_ids:
                    self.assertEqual(source.count(resource_id), 1)
                else:
                    self.assertEqual(
                        source.count(
                            f"PhGetApplicationUiString({resource_id})"
                        ),
                        expected_count,
                    )

        for english_text, _ in expected_routes.values():
            with self.subTest(unrouted_main_native_label=english_text):
                self.assertNotRegex(
                    source,
                    rf'(?:ComboBox_AddString|PhSetWindowText|PhaFormatString)'
                    rf'\s*\([^;]*L"{re.escape(english_text)}"',
                )

        hidnproc = (REPO_ROOT / "SystemInformer" / "hidnproc.c").read_text(
            encoding="utf-8-sig"
        )
        runas = (REPO_ROOT / "SystemInformer" / "runas.c").read_text(
            encoding="utf-8-sig"
        )
        sessmsg = (REPO_ROOT / "SystemInformer" / "sessmsg.c").read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn("PhSelectComboBoxString(methodHandle", hidnproc)
        self.assertNotIn("PhEqualString2(method", hidnproc)
        self.assertNotIn("PhGetWindowText(GetDlgItem(hwndDlg, IDC_METHOD))", hidnproc)
        self.assertRegex(hidnproc, r"ComboBox_SetItemData\(\s*methodHandle")
        self.assertRegex(hidnproc, r"ComboBox_GetItemData\(\s*methodHandle")
        self.assertRegex(
            hidnproc,
            r"PhGetApplicationUiString\(PhpZombieProcessMethods\[i\]\.ResourceId\)",
        )
        self.assertEqual(
            re.findall(
                r"\{ (IDS_PH_HIDDEN_PROCESS_[A-Z0-9_]+), ([A-Za-z0-9_]+) \}",
                hidnproc,
            ),
            [
                ("IDS_PH_HIDDEN_PROCESS_BRUTE_FORCE", "BruteForceScanMethod"),
                ("IDS_PH_HIDDEN_PROCESS_CSR_HANDLES", "CsrHandlesScanMethod"),
                ("IDS_PH_HIDDEN_PROCESS_ETW_HANDLES", "EtwGuidScanMethod"),
                ("IDS_PH_HIDDEN_PROCESS_PROCESS_HANDLES", "ProcessHandleScanMethod"),
                ("IDS_PH_HIDDEN_PROCESS_REGISTRY_HANDLES", "RegistryScanMethod"),
                ("IDS_PH_HIDDEN_PROCESS_NTDLL_HANDLES", "NtdllScanMethod"),
            ],
        )
        self.assertIn("ComboBox_DeleteString(methodHandle", hidnproc)
        self.assertRegex(
            hidnproc,
            r"selectedIndex = ComboBox_GetCurSel\(methodHandle\);\s*"
            r"if \(selectedIndex == CB_ERR\)\s*break;\s*"
            r"selectedMethod = ComboBox_GetItemData\(methodHandle, selectedIndex\);\s*"
            r"if \(selectedMethod == CB_ERR\)\s*break;",
        )

        self.assertNotIn("PhpLogonTypePairs", runas)
        self.assertNotIn(
            "PhGetWindowText(Context->TypeComboBoxWindowHandle)",
            runas,
        )
        self.assertRegex(
            runas,
            r"ComboBox_SetItemData\(\s*context->TypeComboBoxWindowHandle",
        )
        self.assertRegex(
            runas,
            r"ComboBox_GetItemData\(Context->TypeComboBoxWindowHandle",
        )
        self.assertRegex(
            runas,
            r"PhGetApplicationUiString\(PhpLogonTypes\[i\]\.ResourceId\)",
        )
        self.assertEqual(
            re.findall(
                r"\{ (IDS_PH_LOGON_[A-Z0-9_]+), (LOGON32_LOGON_[A-Z0-9_]+) \}",
                runas,
            ),
            [
                ("IDS_PH_LOGON_BATCH", "LOGON32_LOGON_BATCH"),
                ("IDS_PH_LOGON_INTERACTIVE", "LOGON32_LOGON_INTERACTIVE"),
                ("IDS_PH_LOGON_NETWORK", "LOGON32_LOGON_NETWORK"),
                (
                    "IDS_PH_LOGON_NEW_CREDENTIALS",
                    "LOGON32_LOGON_NEW_CREDENTIALS",
                ),
                ("IDS_PH_LOGON_SERVICE", "LOGON32_LOGON_SERVICE"),
            ],
        )
        self.assertIn(
            "ComboBox_DeleteString(context->TypeComboBoxWindowHandle",
            runas,
        )

        self.assertNotIn("PhpMessageBoxIconPairs", sessmsg)
        self.assertNotIn("PhaGetDlgItemText(hwndDlg, IDC_TYPE)", sessmsg)
        self.assertRegex(sessmsg, r"ComboBox_SetItemData\(\s*iconComboBox")
        self.assertRegex(sessmsg, r"ComboBox_GetItemData\(iconComboBox")
        self.assertRegex(
            sessmsg,
            r"PhGetApplicationUiString\(PhpMessageIcons\[i\]\.ResourceId\)",
        )
        self.assertEqual(
            re.findall(
                r"\{ (IDS_PH_MESSAGE_ICON_[A-Z0-9_]+), (MB_[A-Z0-9_]+) \}",
                sessmsg,
            ),
            [
                ("IDS_PH_MESSAGE_ICON_NONE", "MB_OK"),
                ("IDS_PH_MESSAGE_ICON_INFORMATION", "MB_ICONINFORMATION"),
                ("IDS_PH_MESSAGE_ICON_WARNING", "MB_ICONWARNING"),
                ("IDS_PH_MESSAGE_ICON_ERROR", "MB_ICONERROR"),
                ("IDS_PH_MESSAGE_ICON_QUESTION", "MB_ICONQUESTION"),
            ],
        )
        self.assertIn("ComboBox_DeleteString(iconComboBox", sessmsg)
        self.assertRegex(
            sessmsg,
            r"selectedIndex = ComboBox_GetCurSel\(iconComboBox\);\s*"
            r"if \(selectedIndex == CB_ERR\)\s*break;\s*"
            r"selectedIcon = ComboBox_GetItemData\(iconComboBox, selectedIndex\);\s*"
            r"if \(selectedIcon == CB_ERR\)\s*break;",
        )

    def test_main_window_creation_errors_share_native_resource(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        self.assertNotIn('L"Unable to create the window."', source)
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_UNABLE_CREATE_WINDOW)"
            ),
            10,
        )

    def test_main_untranslated_list_view_groups_use_native_resources(self) -> None:
        sources = {
            name: (REPO_ROOT / "SystemInformer" / name).read_text(
                encoding="utf-8-sig"
            )
            for name in ("options.c", "prpgstat.c")
        }
        resource_script = SOURCE_RC.read_text(encoding="utf-8-sig")
        resource_texts = dict(re.findall(
            r'^\s*(IDS_PH_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        expected_resources = {
            "IDS_PH_GROUP_ENERGY": ("Energy", "prpgstat.c"),
            "IDS_PH_GROUP_IMAGES_AND_DLLS": ("Images and DLLs", "options.c"),
            "IDS_PH_GROUP_NOTIFICATIONS": ("Notifications", "options.c"),
            "IDS_PH_GROUP_TRAY_ICONS": ("Tray icons", "options.c"),
        }
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )

        for resource_id, (english_text, source_name) in expected_resources.items():
            with self.subTest(main_list_view_group=resource_id):
                self.assertEqual(resource_texts.get(resource_id), english_text)
                self.assertEqual(
                    sources[source_name].count(
                        f"PhGetApplicationUiString({resource_id})"
                    ),
                    1,
                )
                self.assertNotIn(f'L"{english_text}"', sources[source_name])
                self.assertIn(english_text, translation_data["native_strings"])
                self.assertNotIn(english_text, translation_data["strings"])

        self.assertRegex(
            sources["prpgstat.c"],
            r"PhListView_AddGroup\([^;]*?PH_PROCESS_STATISTICS_CATEGORY_ENERGY,[^;]*?"
            r"PhGetApplicationUiString\(IDS_PH_GROUP_ENERGY\)[^;]*?\);",
        )
        options_routes = {
            "PH_OPTIONS_HIGHLIGHTING_GROUP_IMAGES": "IDS_PH_GROUP_IMAGES_AND_DLLS",
            "PH_OPTIONS_TRAY_ICON_GROUP_NOTIFICATIONS": "IDS_PH_GROUP_NOTIFICATIONS",
            "PH_OPTIONS_TRAY_ICON_GROUP_TRAY_ICONS": "IDS_PH_GROUP_TRAY_ICONS",
        }
        for group_id, resource_id in options_routes.items():
            with self.subTest(main_list_view_group_route=group_id):
                self.assertRegex(
                    sources["options.c"],
                    rf"PhAddListViewGroup\([^;]*?{group_id},[^;]*?"
                    rf"PhGetApplicationUiString\({resource_id}\)[^;]*?\);",
                )

    def test_session_and_handle_group_items_use_native_resources(self) -> None:
        audit = load_audit_module()
        sources = {
            name: audit.mask_c_comments(
                (REPO_ROOT / "SystemInformer" / name).read_text(
                    encoding="utf-8-sig"
                )
            )
            for name in ("sessprp.c", "hndlprp.c")
        }
        resource_header = (
            REPO_ROOT / "SystemInformer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = SOURCE_RC.read_text(encoding="utf-8-sig")
        chinese_resource = ZH_CN_RC.read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "IDS_PH_SESSION_USER_NAME": (2290, "User name", "用户名"),
            "IDS_PH_SESSION_ID": (2291, "Session ID", "会话 ID"),
            "IDS_PH_SESSION_STATE": (2292, "State", "状态"),
            "IDS_PH_SESSION_LOGON_TIME": (2293, "Logon time", "登录时间"),
            "IDS_PH_SESSION_CONNECT_TIME": (2294, "Connect time", "连接时间"),
            "IDS_PH_SESSION_DISCONNECT_TIME": (2295, "Disconnect time", "断开连接时间"),
            "IDS_PH_SESSION_LAST_INPUT_TIME": (2296, "Last input time", "上次输入时间"),
            "IDS_PH_SESSION_CLIENT_NAME": (2297, "Client name", "客户端名称"),
            "IDS_PH_SESSION_CLIENT_ADDRESS": (2298, "Client address", "客户端地址"),
            "IDS_PH_SESSION_CLIENT_DISPLAY": (2299, "Client display", "客户端显示"),
            "IDS_PH_HANDLE_SECURITY_OWNER": (2300, "Owner", "所有者"),
            "IDS_PH_HANDLE_SECURITY_GROUP": (2301, "Group", "组"),
            "IDS_PH_HANDLE_SECURITY_INTEGRITY": (2302, "Integrity", "完整性"),
        }
        runtime_owned = {
            "User name",
            "Session ID",
            "State",
            "Logon time",
            "Owner",
            "Group",
            "Integrity",
        }

        for resource_id, (numeric_id, english_text, chinese_text) in expected_resources.items():
            with self.subTest(main_group_item_resource=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                table_name = "strings" if english_text in runtime_owned else "native_strings"
                other_table = "native_strings" if table_name == "strings" else "strings"
                self.assertEqual(
                    translation_data[table_name].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data[other_table])

        session_routes = tuple(expected_resources)[:10]
        for index, resource_id in enumerate(session_routes):
            with self.subTest(session_group_item_index=index):
                self.assertRegex(
                    sources["sessprp.c"],
                    rf"PhAddListViewGroupItem\(\s*context->ListViewHandle,\s*0,\s*{index},\s*"
                    rf"PhGetApplicationUiString\({resource_id}\),\s*NULL\s*\);",
                )

        handle_routes = tuple(expected_resources)[10:]
        for index, resource_id in enumerate(handle_routes):
            with self.subTest(handle_security_group_item_index=index):
                call_pattern = (
                    rf"PhAddListViewGroupItem\(\s*Context->ListViewHeader,\s*"
                    rf"PH_HANDLE_GENERAL_CATEGORY_SECURITY,\s*{index},\s*"
                    rf"PhGetApplicationUiString\({resource_id}\),\s*NULL\s*\);"
                )
                self.assertEqual(len(re.findall(call_pattern, sources["hndlprp.c"])), 2)

        for _, english_text, _ in expected_resources.values():
            with self.subTest(removed_group_item_literal=english_text):
                self.assertNotRegex(
                    sources["sessprp.c"] + sources["hndlprp.c"],
                    rf"PhAddListViewGroupItem\([^;]*L\"{re.escape(english_text)}\"[^;]*\);",
                )

        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_STAT_PAGEPRIORITY$",
        )
        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2378$",
        )

    def test_early_crash_prompt_does_not_depend_on_ui_string_cache(self) -> None:
        main = (REPO_ROOT / "SystemInformer" / "main.c").read_text(
            encoding="utf-8-sig"
        )
        crash_prompt = (
            'L"System Informer has crashed :(\\r\\n\\r\\n'
            'Do you want to create a minidump on the Desktop?"'
        )

        self.assertIn(crash_prompt, main)
        self.assertNotIn("IDS_PH_CREATE_CRASH_MINIDUMP", main)

    def test_main_missing_process_errors_share_native_resource(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        self.assertNotIn('L"The process does not exist."', source)
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_PROCESS_DOES_NOT_EXIST)"
            ),
            15,
        )

    def test_main_common_service_and_file_errors_share_native_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        self.assertNotIn('L"The service does not exist."', source)
        self.assertNotIn('L"Unable to locate the file."', source)
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_SERVICE_DOES_NOT_EXIST)"
            ),
            6,
        )
        self.assertGreaterEqual(
            source.count("PhGetApplicationUiString(IDS_PH_UNABLE_LOCATE_FILE)"),
            8,
        )

    def test_main_common_operation_errors_share_native_resources(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )

        for literal in (
            'L"Unable to create the file"',
            'L"Unable to decommit the memory region"',
            'L"Unable to free the memory region"',
            'L"Unable to perform the operation."',
            'L"Unable to unmap the section view"',
        ):
            self.assertNotIn(literal, source)
        self.assertNotRegex(source, r'L"Unable to open the process\.?"')
        self.assertGreaterEqual(
            source.count("PhGetApplicationUiString(IDS_PH_UNABLE_CREATE_FILE)"),
            10,
        )
        self.assertGreaterEqual(
            source.count("PhGetApplicationUiString(IDS_PH_UNABLE_OPEN_PROCESS)"),
            14,
        )
        self.assertGreaterEqual(
            source.count(
                "PhGetApplicationUiString(IDS_PH_UNABLE_PERFORM_OPERATION)"
            ),
            9,
        )
        for resource_id in (
            "IDS_PH_UNABLE_DECOMMIT_MEMORY_REGION",
            "IDS_PH_UNABLE_FREE_MEMORY_REGION",
            "IDS_PH_UNABLE_UNMAP_SECTION_VIEW",
        ):
            self.assertEqual(source.count(resource_id), 1)

    def test_main_memory_and_enumeration_errors_use_native_resources(self) -> None:
        sources = {
            path.name: path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        }
        literals = (
            "Unable to enumerate processes",
            "Unable to close the TCP connection",
            "Unable to edit memory",
            "Unable to edit the memory region.",
            "Unable to determine whether the thread is waiting.",
            "Unable to empty the memory list.",
            "Unable to empty the region working set.",
            "Unable to enumerate process handles",
            "Unable to duplicate the token.",
            "Unable to change memory protection",
            "Unable to close the window.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                pattern = re.compile(
                    rf'L"{re.escape(literal.removesuffix("."))}\.?' + '"'
                )
                remaining_files = [
                    name
                    for name, source in sources.items()
                    if pattern.search(source)
                ]
                self.assertEqual(
                    remaining_files,
                    [],
                    f"raw UI literal remains: {literal}",
                )

    def test_main_runtime_operation_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )
        literals = (
            "Unable to query heap information.",
            "Unable to query 32bit heap information.",
            "Unable to query lock information.",
            "Unable to search for strings.",
            "Unable to create the search thread",
            "Unable to analyze the thread.",
            "Unable to show the process properties.",
            "Unable to change service configuration.",
            "Unable to create the service.",
            "Unable to shutdown WSL instances.",
            "Unable to save application settings.",
            "Unable to find the memory region for the selected address.",
            "Unable to open the file location.",
            "Unable to open the file properties.",
            "Unable to open key.",
            "Unable to open the thread.",
            "Unable to map a view of the section.",
            "Unable to query the section.",
            "Unable to load the stack.",
            "Unable to refresh the stack.",
            "Unable to query pagefile information.",
            "The minimum length must be at least 4.",
            "At least one memory type (Private, Image, or Mapped) must be selected.",
            "The thread does not appear to be waiting.",
            "The process has already terminated; only the process record is available.",
            "The binary path is empty.",
            "The object is unnamed.",
            "The 32-bit version of System Informer could not be located.",
            "The section size is greater than 32 MB. Only the first 32 MB will be available.",
            "A 64-bit dump will be created instead. Do you want to continue?",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                stem = re.escape(literal.removesuffix("."))
                self.assertNotRegex(source, rf'L"{stem}\.?[ \t]*"')

    def test_main_power_and_session_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )
        literals = (
            "Unable to hibernate the computer.",
            "Unable to restart the computer.",
            "Unable to shut down the computer.",
            "Unable to sleep the computer.",
            "Unable to lock the computer.",
            "Unable to log off the computer.",
            "Unable to connect to the session",
            "Unable to disconnect the session",
            "Unable to logoff the session",
            "Unable to remote control the session",
            "Unable to shadow session.",
            "Unable to send the message",
            "Unable to detach the debugger.",
            "Unable to configure the advanced boot options.",
            "Unable to configure the boot application.",
            "You cannot remote control the current session.",
            "The process is not being debugged.",
            "Unable to restart to firmware options.",
            "Make sure System Informer is running with administrative privileges.",
            "This machine does not have UEFI support.",
            "Unable to create kernel minidump.",
            "Kernel minidump of processes require administrative privileges.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                stem = re.escape(literal.removesuffix("."))
                self.assertNotRegex(source, rf'L"{stem}\.?[ \t]*"')

    def test_main_process_environment_and_dump_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (REPO_ROOT / "SystemInformer").glob("*.c")
        )
        literals = (
            "Unable to access the dump file",
            "Unable to create the minidump",
            "Unable to change affinity settings.",
            "Unable to create live kernel dump.",
            "Unable to perform the scan",
            "Unable to set the environment variable.",
            "Unable to delete the environment variable.",
            "Unable to disable UIAccess flag.",
            "Unable to set the integrity level",
            "Unable to read memory",
            "Unable to write memory",
            "Unable to set the integrity label",
            "Unable to terminate the process",
            "Unable to create a process structure for the selected process.",
            "Unable to terminate the job",
            "Unable to add the process to the job",
            "Unable to terminate the task.",
            "Unable to clone the process",
            "Unable to update the length.",
            "Unable to query the process.",
            "Unable to start the program.",
            "You must select at least one CPU.",
            "The minimum length is invalid.",
            "Unable to start the execution alias with a process token.",
            "Unable to save the live kernel dump.",
            "Unable to query the current affinity.",
            "Unable to open the token",
            "Unable to execute the command.",
            "Invalid value.",
            "Enter a value between 0 and 64.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                stem = re.escape(literal.removesuffix("."))
                self.assertNotRegex(source, rf'L"{stem}\.?[ \t]*"')

    def test_main_affinity_and_token_dynamic_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in (
                REPO_ROOT / "SystemInformer" / "affinity.c",
                REPO_ROOT / "SystemInformer" / "plugin.c",
                REPO_ROOT / "SystemInformer" / "tokprp.c",
            )
        )
        literals = (
            "Unable to change affinity of process %lu",
            "Unable to change affinity of thread %lu",
            "Unable to update affinity for thread(s)",
            "Unable to update affinity for thread(s):\\r\\n%s",
            "Unable to %s %s.",
            "An unknown error occurred.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', source)

        token_properties = (
            REPO_ROOT / "SystemInformer" / "tokprp.c"
        ).read_text(encoding="utf-8-sig")
        self.assertNotRegex(
            token_properties,
            r'action\s*=\s*L"(?:set|enable|disable|reset|remove)"',
        )
        self.assertNotIn('L"privilege"', token_properties)
        self.assertNotIn('L"group"', token_properties)

        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        self.assertIn(
            'IDS_PH_TOKEN_PRIVILEGE                             "特权"',
            localized,
        )

        service_actions = (
            REPO_ROOT / "SystemInformer" / "actions.c"
        ).read_text(encoding="utf-8-sig")
        self.assertNotIn(
            "PhGetApplicationUiString(IDS_PH_UNABLE_APPLY_TOKEN_ACTION)",
            service_actions,
        )

    def test_main_thread_and_program_errors_use_native_resources(self) -> None:
        sources = {
            name: (REPO_ROOT / "SystemInformer" / name).read_text(encoding="utf-8-sig")
            for name in ("actions.c", "appsup.c", "prpgthrd.c")
        }
        combined = "\n".join(sources.values())

        self.assertNotIn('L"Unable to execute the program."', combined)
        self.assertNotRegex(combined, r'L"Unable to [^"]*thread %lu"')
        self.assertIn("_In_ ULONG MessageId", sources["actions.c"])
        self.assertIn(
            "PhGetApplicationUiString(MessageId)",
            sources["actions.c"],
        )

        expected_ids = {
            "IDS_PH_UNABLE_TERMINATE_THREAD": 3,
            "IDS_PH_UNABLE_SUSPEND_THREAD": 3,
            "IDS_PH_UNABLE_RESUME_THREAD": 3,
            "IDS_PH_UNABLE_FREEZE_THREAD": 1,
            "IDS_PH_UNABLE_THAW_THREAD": 1,
            "IDS_PH_UNABLE_CHANGE_THREAD_BOOST_PRIORITY": 1,
            "IDS_PH_UNABLE_SET_THREAD_BOOST_PRIORITY": 2,
            "IDS_PH_UNABLE_CHANGE_THREAD_PRIORITY": 1,
            "IDS_PH_UNABLE_SET_THREAD_PRIORITY": 1,
            "IDS_PH_UNABLE_SET_THREAD_IO_PRIORITY": 3,
            "IDS_PH_UNABLE_SET_THREAD_PAGE_PRIORITY": 1,
            "IDS_PH_UNABLE_EXECUTE_PROGRAM": 3,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", combined)),
                    expected_count,
                )

        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        self.assertIn(
            'IDS_PH_UNABLE_SUSPEND_THREAD                       "无法挂起线程 %lu"',
            localized,
        )
        self.assertNotIn('"无法暂停线程 %lu"', localized)

    def test_main_object_and_module_errors_use_native_resources(self) -> None:
        sources = {
            name: (REPO_ROOT / "SystemInformer" / name).read_text(encoding="utf-8-sig")
            for name in (
                "actions.c",
                "appsup.c",
                "findobj.c",
                "informerwnd.c",
                "memrslt.c",
                "ntobjprp.c",
                "usrlist.c",
            )
        }
        combined = "\n".join(sources.values())
        literals = (
            "Failed to get process start key.",
            "Setting handle attributes requires a connection to the kernel driver.",
            'Unable to close \\"%s\\"',
            "Unable to compile the regular expression.",
            '\\"%s\\" at position %zu.',
            "Unable to locate routines.",
            "Unable to locate the application directory.",
            "Unable to open the event",
            "Unable to open the event pair",
            "Unable to open the semaphore",
            "Unable to open the timer",
            "Unable to search for handles because the total number of handles on the system is too large.",
            "Please check if there are any processes with an extremely large number of handles open.",
            "Unidentified third party object.",
            "Unable to unload the module",
            "Unable to unload ",
            "Unable to unmap the section view at 0x%p",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', combined)

        expected_ids = {
            "IDS_PH_UNABLE_GET_PROCESS_START_KEY": 1,
            "IDS_PH_HANDLE_ATTRIBUTES_REQUIRE_DRIVER": 1,
            "IDS_PH_UNABLE_CLOSE_NAMED_OBJECT": 1,
            "IDS_PH_UNABLE_COMPILE_REGULAR_EXPRESSION": 1,
            "IDS_PH_REGULAR_EXPRESSION_ERROR_POSITION": 1,
            "IDS_PH_UNABLE_LOCATE_ROUTINES": 1,
            "IDS_PH_UNABLE_LOCATE_APPLICATION_DIRECTORY": 1,
            "IDS_PH_UNABLE_OPEN_EVENT": 1,
            "IDS_PH_UNABLE_OPEN_EVENT_PAIR": 1,
            "IDS_PH_UNABLE_OPEN_SEMAPHORE": 1,
            "IDS_PH_UNABLE_OPEN_TIMER": 1,
            "IDS_PH_TOO_MANY_HANDLES": 1,
            "IDS_PH_TOO_MANY_HANDLES_HINT": 1,
            "IDS_PH_UNIDENTIFIED_THIRD_PARTY_OBJECT": 1,
            "IDS_PH_UNABLE_UNLOAD_MODULE": 1,
            "IDS_PH_UNABLE_UNLOAD_NAMED_MODULE": 3,
            "IDS_PH_UNABLE_UNLOAD_NAMED_MODULE_ADMIN": 1,
            "IDS_PH_UNABLE_UNMAP_SECTION_AT_ADDRESS": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", combined)),
                    expected_count,
                )

    def test_main_confirmation_warnings_use_native_resources(self) -> None:
        source = "\n".join(
            (REPO_ROOT / "SystemInformer" / name).read_text(encoding="utf-8-sig")
            for name in ("actions.c", "hidnproc.c", "mwpgproc.c", "tokprp.c")
        )
        literals = (
            "Deleting a service can prevent the system from starting or functioning properly.",
            "Enabling or disabling virtualization for a process may alter its functionality and produce undesirable effects.",
            "Removing privileges may reduce the functionality of the process, and is permanent for the lifetime of the process.",
            "Removing this flag may reduce the functionality of the process provided it is an accessibility application.",
            "Terminating a Zombie process may cause the system to become unstable or crash.",
            "The process will be restarted with the same command line, working directory and privileges.",
            "This filter cannot function because digital signature checking is not enabled.\\r\\n%s",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', source)

        resource_ids = (
            "IDS_PH_SERVICE_DELETION_WARNING",
            "IDS_PH_PROCESS_VIRTUALIZATION_WARNING",
            "IDS_PH_REMOVE_PRIVILEGES_WARNING",
            "IDS_PH_REMOVE_UIACCESS_WARNING",
            "IDS_PH_ZOMBIE_TERMINATION_WARNING",
            "IDS_PH_PROCESS_RESTART_NOTICE",
            "IDS_PH_SIGNATURE_FILTER_REQUIRES_CHECKING",
        )

        for resource_id in resource_ids:
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    1,
                )

        localized = ZH_CN_RC.read_text(encoding="utf-8-sig")
        self.assertIn(
            'IDS_PH_REMOVE_PRIVILEGES_WARNING                   "移除特权可能会削弱进程功能，并且在进程存续期间无法恢复。"',
            localized,
        )
        self.assertIn(
            'IDS_PH_PROCESS_RESTART_NOTICE                      "该进程将使用相同的命令行、工作目录和特权重新启动。"',
            localized,
        )

    def test_extended_services_errors_use_native_resources(self) -> None:
        source = "\n".join(
            (REPO_ROOT / "plugins" / "ExtendedServices" / name).read_text(
                encoding="utf-8-sig"
            )
            for name in (
                "other.c",
                "recovery.c",
                "svcpnp.c",
                "trigger.c",
                "triggpg.c",
            )
        )
        literals = (
            "Failed to change the device state.",
            "Failed to restart the device.",
            "Failed to uninstall the device.",
            "Unable to find the ETW publisher GUID.",
            "The custom subtype is invalid.",
            "If you continue, they will be removed.",
            "Unable to query service information.",
            "Unable to open LSA policy",
            "Unable to change service information.",
            "Unable to query service recovery information.",
            "The service has %lu failure actions configured",
            "Unable to change service recovery information.",
            "Unable to query service trigger information.",
            "Unable to change service trigger information.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_ES_FAILED_CHANGE_DEVICE_STATE": 2,
            "IDS_ES_FAILED_RESTART_DEVICE": 3,
            "IDS_ES_FAILED_UNINSTALL_DEVICE": 2,
            "IDS_ES_UNABLE_FIND_ETW_PUBLISHER_GUID": 1,
            "IDS_ES_CUSTOM_SUBTYPE_INVALID": 1,
            "IDS_ES_TRIGGER_DATA_REMOVAL_WARNING": 1,
            "IDS_ES_UNABLE_QUERY_SERVICE_INFORMATION": 1,
            "IDS_ES_UNABLE_OPEN_LSA_POLICY": 1,
            "IDS_ES_UNABLE_CHANGE_SERVICE_INFORMATION": 1,
            "IDS_ES_UNABLE_QUERY_SERVICE_RECOVERY_INFORMATION": 2,
            "IDS_ES_SERVICE_FAILURE_ACTIONS_TRUNCATED": 1,
            "IDS_ES_UNABLE_CHANGE_SERVICE_RECOVERY_INFORMATION": 1,
            "IDS_ES_UNABLE_QUERY_SERVICE_TRIGGER_INFORMATION": 1,
            "IDS_ES_UNABLE_CHANGE_SERVICE_TRIGGER_INFORMATION": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

    def test_extended_tools_errors_use_native_resources(self) -> None:
        source = "\n".join(
            (REPO_ROOT / "plugins" / "ExtendedTools" / name).read_text(
                encoding="utf-8-sig"
            )
            for name in (
                "disktab.c",
                "firmware.c",
                "firmware_editor.c",
                "modsrv.c",
                "objmgr.c",
                "reparse.c",
                "thrdact.c",
                "tpm.c",
                "tpm_editor.c",
                "unldll.c",
                "wbcl.c",
                "wswatch.c",
            )
        )
        literals = (
            "Boot log entry",
            "Failed to read TPM",
            "There is no synchronous I/O to cancel.",
            "Unable to cancel synchronous I/O",
            "Unable to create the symbol provider.",
            "Unable to delete firmware variable.",
            "Unable to enable environment privilege.",
            "Unable to enable WS watch.",
            "Unable to enumerate the objects.",
            "Unable to locate files with the SecurityId.",
            "Unable to locate the target.",
            "Unable to query directory object.",
            "Unable to query firmware table.",
            "Unable to query module references.",
            "Unable to query the EFI variable.",
            "Unable to query the TPM",
            "Unable to read the log file",
            "Unable to read the measured boot log",
            "Unable to read TPM",
            "Unable to remove the object identifier.",
            "Unable to remove the reparse point.",
            "Unable to retrieve unload event trace information.",
            "Unable to select the process.",
            "Unable to update the EFI variable.",
            "Unable to write to the TPM",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_ET_BOOT_LOG_ENTRY": 1,
            "IDS_ET_FAILED_READ_TPM": 1,
            "IDS_ET_NO_SYNCHRONOUS_IO": 1,
            "IDS_ET_UNABLE_CANCEL_SYNCHRONOUS_IO": 1,
            "IDS_ET_UNABLE_CREATE_SYMBOL_PROVIDER": 1,
            "IDS_ET_UNABLE_DELETE_FIRMWARE_VARIABLE": 1,
            "IDS_ET_UNABLE_ENABLE_ENVIRONMENT_PRIVILEGE": 1,
            "IDS_ET_UNABLE_ENABLE_WS_WATCH": 1,
            "IDS_ET_UNABLE_ENUMERATE_OBJECTS": 1,
            "IDS_ET_UNABLE_LOCATE_SECURITY_ID_FILES": 1,
            "IDS_ET_UNABLE_LOCATE_TARGET": 2,
            "IDS_ET_UNABLE_QUERY_DIRECTORY_OBJECT": 1,
            "IDS_ET_UNABLE_QUERY_FIRMWARE_TABLE": 1,
            "IDS_ET_UNABLE_QUERY_MODULE_REFERENCES": 2,
            "IDS_ET_UNABLE_QUERY_EFI_VARIABLE": 2,
            "IDS_ET_UNABLE_QUERY_TPM": 1,
            "IDS_ET_UNABLE_READ_LOG_FILE": 1,
            "IDS_ET_UNABLE_READ_MEASURED_BOOT_LOG": 1,
            "IDS_ET_UNABLE_READ_TPM": 1,
            "IDS_ET_UNABLE_REMOVE_OBJECT_IDENTIFIER": 1,
            "IDS_ET_UNABLE_REMOVE_REPARSE_POINT": 1,
            "IDS_ET_UNABLE_RETRIEVE_UNLOAD_TRACE": 1,
            "IDS_ET_UNABLE_SELECT_PROCESS": 1,
            "IDS_ET_UNABLE_UPDATE_EFI_VARIABLE": 2,
            "IDS_ET_UNABLE_WRITE_TPM": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

    def test_extended_tools_adapter_details_share_native_resources(self) -> None:
        sources = {
            adapter: (
                REPO_ROOT / "plugins" / "ExtendedTools" / f"{adapter}details.c"
            ).read_text(encoding="utf-8-sig")
            for adapter in ("gpu", "npu")
        }
        resource_header = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_rc = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "ExtendedTools.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_rc = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "ExtendedTools.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "IDS_ET_ADAPTER_DETAILS_PHYSICAL_LOCATION": (
                61026,
                "PHYSICALLOCTION",
                "Physical Location",
                "物理位置",
            ),
            "IDS_ET_ADAPTER_DETAILS_DRIVER_DATE": (
                61027,
                "DRIVERDATE",
                "Driver Date",
                "驱动程序日期",
            ),
            "IDS_ET_ADAPTER_DETAILS_DRIVER_VERSION": (
                61028,
                "DRIVERVERSION",
                "Driver Version",
                "驱动程序版本",
            ),
            "IDS_ET_ADAPTER_DETAILS_WDDM_VERSION": (
                61029,
                "WDDMVERSION",
                "WDDM Version",
                "WDDM 版本",
            ),
            "IDS_ET_ADAPTER_DETAILS_VENDOR_ID": (
                61030,
                "VENDORID",
                "Vendor ID",
                "供应商 ID",
            ),
            "IDS_ET_ADAPTER_DETAILS_DEVICE_ID": (
                61031,
                "DEVICEID",
                "Device ID",
                "设备 ID",
            ),
            "IDS_ET_ADAPTER_DETAILS_TOTAL_MEMORY": (
                61032,
                "TOTALMEMORY",
                "Total Memory",
                "总内存",
            ),
            "IDS_ET_ADAPTER_DETAILS_RESERVED_MEMORY": (
                61033,
                "RESERVEDMEMORY",
                "Reserved Memory",
                "预留内存",
            ),
            "IDS_ET_ADAPTER_DETAILS_MEMORY_FREQUENCY": (
                61034,
                "MEMORYFREQUENCY",
                "Memory Frequency",
                "内存频率",
            ),
            "IDS_ET_ADAPTER_DETAILS_MEMORY_BANDWIDTH": (
                61035,
                "MEMORYBANDWIDTH",
                "Memory Bandwidth",
                "内存带宽",
            ),
            "IDS_ET_ADAPTER_DETAILS_PCIE_BANDWIDTH": (
                61036,
                "PCIEBANDWIDTH",
                "PCIE Bandwidth",
                "PCIe 带宽",
            ),
            "IDS_ET_ADAPTER_DETAILS_FAN_RPM": (
                61037,
                "FANRPM",
                "Fan RPM",
                "风扇转速（RPM）",
            ),
            "IDS_ET_ADAPTER_DETAILS_POWER_USAGE": (
                61038,
                "POWERUSAGE",
                "Power Usage",
                "功率使用率",
            ),
            "IDS_ET_ADAPTER_DETAILS_TEMPERATURE": (
                61039,
                "TEMPERATURE",
                "Temperature",
                "温度",
            ),
        }

        for resource_id, (
            numeric_id,
            index_suffix,
            english_text,
            chinese_text,
        ) in expected_resources.items():
            with self.subTest(adapter_detail=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_rc,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_rc,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                self.assertEqual(
                    translation_data["strings"].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data["native_strings"])

                for adapter, source in sources.items():
                    adapter_upper = adapter.upper()
                    self.assertNotIn(f'L"{english_text}"', source)
                    self.assertRegex(
                        source,
                        rf"PhAddListViewGroupItem\(\s*"
                        rf"ListViewHandle,\s*{adapter.title()}GroupId,\s*"
                        rf"{adapter_upper}ADAPTER_DETAILS_INDEX_{index_suffix},\s*"
                        rf"PhGetString\(PH_AUTO\(PhLoadUiString\(\s*"
                        rf"PluginInstance->DllBase,\s*{resource_id},\s*NULL\s*"
                        rf"\)\)\),\s*NULL\s*\);",
                    )

        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61104$",
        )

    def test_module_services_thread_does_not_use_auto_pool_before_initialization(
        self,
    ) -> None:
        source = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "modsrv.c"
        ).read_text(encoding="utf-8-sig")
        thread_body = source.split(
            "NTSTATUS EtpModuleServicesDialogThreadStart", 1
        )[1].split("VOID EtShowModuleServicesDialog", 1)[0]
        before_initialization = thread_body.split("PhInitializeAutoPool", 1)[0]

        self.assertNotIn("PH_AUTO(", before_initialization)
        self.assertEqual(
            before_initialization.count("PhDereferenceObject(resourceTitle);"),
            2,
        )

    def test_user_notes_errors_use_native_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "UserNotes" / "main.c"
        ).read_text(encoding="utf-8-sig")
        literals = (
            "Successfully deleted the IFEO key.",
            "This process has multi-group affinity, %s",
            "Unable to configure IFEO priority for this image.",
            "Unable to query graphics scheduling priority",
            "Unable to query IO priority.",
            "Unable to query page priority.",
            "Unable to query priority.",
            "Unable to query process affinity.",
            "Unable to query process boost.",
            "Unable to query process efficiency mode.",
            "Unable to update graphics scheduling priority",
            "Unable to update the IFEO for IO priority.",
            "Unable to update the IFEO for page priority.",
            "Unable to update the IFEO for priority.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_UN_IFEO_KEY_DELETED": 3,
            "IDS_UN_MULTI_GROUP_AFFINITY": 2,
            "IDS_UN_UNABLE_CONFIGURE_IFEO_PRIORITY": 1,
            "IDS_UN_UNABLE_QUERY_GRAPHICS_PRIORITY": 1,
            "IDS_UN_UNABLE_QUERY_IO_PRIORITY": 2,
            "IDS_UN_UNABLE_QUERY_PAGE_PRIORITY": 2,
            "IDS_UN_UNABLE_QUERY_PRIORITY": 2,
            "IDS_UN_UNABLE_QUERY_PROCESS_AFFINITY": 2,
            "IDS_UN_UNABLE_QUERY_PROCESS_BOOST": 3,
            "IDS_UN_UNABLE_QUERY_PROCESS_EFFICIENCY": 3,
            "IDS_UN_UNABLE_UPDATE_GRAPHICS_PRIORITY": 1,
            "IDS_UN_UNABLE_UPDATE_IFEO_IO_PRIORITY": 2,
            "IDS_UN_UNABLE_UPDATE_IFEO_PAGE_PRIORITY": 2,
            "IDS_UN_UNABLE_UPDATE_IFEO_PRIORITY": 2,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

    def test_remaining_plugin_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        files = {
            "HardwareDevices": ("gpunodes.c",),
            "NetworkTools": ("update.c", "whois.c"),
            "OnlineChecks": ("exclude.c", "upload.c"),
            "ToolStatus": ("find.c", "main.c"),
            "Updater": ("utils.c",),
            "WindowExplorer": ("wnddlg.c", "wndprp.c"),
        }
        source = "\n".join(
            audit.mask_c_comments(
                (REPO_ROOT / "plugins" / plugin / name).read_text(
                    encoding="utf-8-sig"
                )
            )
            for plugin, names in files.items()
            for name in names
        )
        literals = (
            "There are no graphics nodes to display.",
            "The GeoLite updater doesn't support legacy versions of Windows.",
            "Unable to display the whois window.",
            "The regular expression could not be compiled.",
            "Unable to query the service.",
            "The process (PID %lu) does not exist.",
            "Unable to display Find dialog.",
            "Unable to execute the setup.",
            "Unable to add window property.",
            "Unable to create the window property.",
            "Unable to destroy the window.",
            "Unable to display window properties.",
            "Unable to remove the window property.",
            "Unable to update the window property.",
            "The window does not exist.",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}', source)

        expected_ids = {
            "IDS_HD_NO_GRAPHICS_NODES": 1,
            "IDS_NT_GEOLITE_LEGACY_WINDOWS": 1,
            "IDS_NT_UNABLE_DISPLAY_WHOIS": 1,
            "IDS_OC_REGEX_COMPILE_FAILED": 1,
            "IDS_OC_UNABLE_QUERY_SERVICE": 1,
            "IDS_TS_PROCESS_NOT_FOUND": 2,
            "IDS_TS_UNABLE_DISPLAY_FIND": 1,
            "IDS_UP_UNABLE_EXECUTE_SETUP": 1,
            "IDS_WE_UNABLE_ADD_WINDOW_PROPERTY": 1,
            "IDS_WE_UNABLE_CREATE_WINDOW_PROPERTY": 1,
            "IDS_WE_UNABLE_DESTROY_WINDOW": 2,
            "IDS_WE_UNABLE_DISPLAY_WINDOW_PROPERTIES": 2,
            "IDS_WE_UNABLE_REMOVE_WINDOW_PROPERTY": 1,
            "IDS_WE_UNABLE_UPDATE_WINDOW_PROPERTY": 1,
            "IDS_WE_WINDOW_NOT_FOUND": 2,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

        resource_ids_by_plugin = {
            "HardwareDevices": ("IDS_HD_NO_GRAPHICS_NODES",),
            "NetworkTools": (
                "IDS_NT_GEOLITE_LEGACY_WINDOWS",
                "IDS_NT_UNABLE_DISPLAY_WHOIS",
            ),
            "OnlineChecks": (
                "IDS_OC_REGEX_COMPILE_FAILED",
                "IDS_OC_UNABLE_QUERY_SERVICE",
            ),
            "ToolStatus": (
                "IDS_TS_PROCESS_NOT_FOUND",
                "IDS_TS_UNABLE_DISPLAY_FIND",
            ),
            "Updater": ("IDS_UP_UNABLE_EXECUTE_SETUP",),
            "WindowExplorer": (
                "IDS_WE_UNABLE_ADD_WINDOW_PROPERTY",
                "IDS_WE_UNABLE_CREATE_WINDOW_PROPERTY",
                "IDS_WE_UNABLE_DESTROY_WINDOW",
                "IDS_WE_UNABLE_DISPLAY_WINDOW_PROPERTIES",
                "IDS_WE_UNABLE_REMOVE_WINDOW_PROPERTY",
                "IDS_WE_UNABLE_UPDATE_WINDOW_PROPERTY",
                "IDS_WE_WINDOW_NOT_FOUND",
            ),
        }

        for plugin, resource_ids in resource_ids_by_plugin.items():
            header = (
                REPO_ROOT / "plugins" / plugin / "resource.h"
            ).read_text(encoding="utf-8-sig")
            compiled_definitions = header.split("#ifdef APSTUDIO_INVOKED", 1)[0]

            for resource_id in resource_ids:
                with self.subTest(plugin=plugin, resource_id=resource_id):
                    self.assertRegex(
                        compiled_definitions,
                        rf"(?m)^#define\s+{re.escape(resource_id)}\s+\d+$",
                    )

    def test_small_plugin_window_texts_use_native_resources(self) -> None:
        audit = load_audit_module()
        source_paths = {
            "WindowExplorer": (
                REPO_ROOT / "plugins" / "WindowExplorer" / "wnddlg.c",
                REPO_ROOT / "plugins" / "WindowExplorer" / "wndprp.c",
            ),
            "OnlineChecks": (
                REPO_ROOT / "plugins" / "OnlineChecks" / "options.c",
            ),
            "Updater": (
                REPO_ROOT / "plugins" / "Updater" / "options.c",
            ),
        }
        sources = {
            plugin: "\n".join(
                audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
                for path in paths
            )
            for plugin, paths in source_paths.items()
        }
        headers = {
            plugin: (
                REPO_ROOT / "plugins" / plugin / "resource.h"
            ).read_text(encoding="utf-8-sig")
            for plugin in source_paths
        }
        english_resources = {
            plugin: (
                REPO_ROOT / "plugins" / plugin / f"{plugin}.rc"
            ).read_text(encoding="utf-8-sig")
            for plugin in source_paths
        }
        chinese_resources = {
            plugin: (
                REPO_ROOT / "plugins" / plugin / f"{plugin}.zh-cn.rc"
            ).read_text(encoding="utf-8-sig")
            for plugin in source_paths
        }
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "WindowExplorer": {
                "IDS_WE_PAUSE": (12090, "Pause", "暂停", "strings"),
                "IDS_WE_RESUME": (12091, "Resume", "恢复", "native_strings"),
                "IDS_WE_PROPERTY_EDITOR": (12092, "Property Editor", "属性编辑器", "native_strings"),
            },
            "OnlineChecks": {
                "IDS_OC_KEY_STATUS_SET": (12002, "Set - using your key", "已设置 - 使用你的密钥", "native_strings"),
                "IDS_OC_KEY_STATUS_UNSET": (12003, "Unset - optional", "未设置 - 可选", "native_strings"),
                "IDS_OC_PASTE_LICENSE_KEY_HERE": (12004, "Paste the license key here:", "在此粘贴许可证密钥：", "native_strings"),
            },
            "Updater": {
                "IDS_UP_LAST_UPDATE_CHECK_FORMAT": (12004, "Last update check: %s (%s ago)", "上次检查更新：%s（%s 前）", "native_strings"),
                "IDS_UP_NEXT_UPDATE_CHECK_RELATIVE_FORMAT": (12005, "Next update check: %s (%s)", "下次检查更新：%s（%s）", "native_strings"),
                "IDS_UP_NEXT_UPDATE_CHECK_FORMAT": (12006, "Next update check: %s", "下次检查更新：%s", "native_strings"),
            },
        }
        expected_aps = {
            "WindowExplorer": 12093,
            "OnlineChecks": 12005,
            "Updater": 12007,
        }

        for plugin, resources in expected_resources.items():
            for resource_id, (numeric_id, english_text, chinese_text, table_name) in resources.items():
                with self.subTest(plugin=plugin, window_text_resource=resource_id):
                    self.assertRegex(
                        headers[plugin],
                        rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                    )
                    self.assertRegex(
                        english_resources[plugin],
                        rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                    )
                    self.assertRegex(
                        chinese_resources[plugin],
                        rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                    )
                    other_table = "strings" if table_name == "native_strings" else "native_strings"
                    self.assertEqual(
                        translation_data[table_name].get(english_text),
                        chinese_text,
                    )
                    self.assertNotIn(english_text, translation_data[other_table])

            self.assertRegex(
                headers[plugin],
                rf"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+{expected_aps[plugin]}$",
            )

        window_source = sources["WindowExplorer"]
        pause_branches = re.search(
            r"if\s*\(\s*Context->ProviderPaused\s*\)\s*"
            r"\{(?P<paused>.*?)\}\s*else\s*\{(?P<running>.*?)\}",
            window_source,
            re.DOTALL,
        )
        self.assertIsNotNone(pause_branches)
        self.assertIn("IDS_WE_RESUME", pause_branches.group("paused"))
        self.assertNotIn("IDS_WE_PAUSE", pause_branches.group("paused"))
        self.assertIn("IDS_WE_PAUSE", pause_branches.group("running"))
        self.assertNotIn("IDS_WE_RESUME", pause_branches.group("running"))
        self.assertRegex(
            window_source,
            r"PhSetWindowText\([^;]*?PhGetString\(PH_AUTO\(PhLoadUiString\(\s*"
            r"PluginInstance->DllBase,\s*IDS_WE_PROPERTY_EDITOR,\s*NULL\s*\)\)\)"
            r"[^;]*?\);",
        )

        online_source = sources["OnlineChecks"]
        self.assertRegex(
            online_source,
            r"\*Configured\s*\?\s*PhGetString\(PH_AUTO\(PhLoadUiString\(\s*"
            r"PluginInstance->DllBase,\s*IDS_OC_KEY_STATUS_SET,\s*NULL\s*\)\)\)\s*"
            r":\s*PhGetString\(PH_AUTO\(PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
            r"IDS_OC_KEY_STATUS_UNSET,\s*NULL\s*\)\)\)",
        )
        paste_route = (
            r"PhSetDialogItemText\(\s*WindowHandle,\s*IDC_KEYTEXT_L,\s*"
            r"PhGetString\(PH_AUTO\(PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
            r"IDS_OC_PASTE_LICENSE_KEY_HERE,\s*NULL\s*\)\)\)\s*\);"
        )
        self.assertEqual(len(re.findall(paste_route, online_source)), 1)

        updater_routes = []
        for name, args, _, _ in audit.find_calls(
            sources["Updater"], {"PhaFormatString"}
        ):
            resource_match = re.search(
                r"PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
                r"(IDS_UP_[A-Z0-9_]+),\s*NULL\s*\)",
                args[0],
            )
            if resource_match:
                updater_routes.append((
                    resource_match.group(1),
                    tuple(re.sub(r"\s+", "", arg) for arg in args[1:]),
                ))
        self.assertEqual(
            updater_routes,
            [
                (
                    "IDS_UP_LAST_UPDATE_CHECK_FORMAT",
                    (
                        "PhGetStringOrEmpty(timeString)",
                        "PhGetStringOrEmpty(timeRelativeString)",
                    ),
                ),
                (
                    "IDS_UP_NEXT_UPDATE_CHECK_RELATIVE_FORMAT",
                    (
                        "PhGetStringOrEmpty(timeString)",
                        "PhGetStringOrEmpty(timeRelativeString)",
                    ),
                ),
                (
                    "IDS_UP_NEXT_UPDATE_CHECK_FORMAT",
                    ("PhGetStringOrEmpty(timeString)",),
                ),
            ],
        )

        migrated_texts = {
            english_text
            for resources in expected_resources.values()
            for _, english_text, _, _ in resources.values()
        }
        entries = []
        for paths in source_paths.values():
            for path in paths:
                audit.scan_c_file(str(path), entries)
        self.assertEqual(
            [
                entry
                for entry in entries
                if entry["english"] in migrated_texts
            ],
            [],
        )

    def test_extended_tools_and_updater_combo_labels_use_native_resources(self) -> None:
        firmware_editor = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "firmware_editor.c"
        ).read_text(encoding="utf-8-sig")
        tpm_editor = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "tpm_editor.c"
        ).read_text(encoding="utf-8-sig")
        updater_options = (
            REPO_ROOT / "plugins" / "Updater" / "options.c"
        ).read_text(encoding="utf-8-sig")
        extended_tools_rc = (
            REPO_ROOT / "plugins" / "ExtendedTools" / "ExtendedTools.rc"
        ).read_text(encoding="utf-8-sig")
        updater_rc = (
            REPO_ROOT / "plugins" / "Updater" / "Updater.rc"
        ).read_text(encoding="utf-8-sig")
        expected_resources = {
            "IDS_ET_BYTES_PER_ROW_FORMAT": (
                "%u bytes per row",
                firmware_editor,
                extended_tools_rc,
            ),
            "IDS_UP_INTERVAL_ONE_DAY": ("1 day", updater_options, updater_rc),
            "IDS_UP_INTERVAL_ONE_WEEK": ("1 week", updater_options, updater_rc),
            "IDS_UP_INTERVAL_ONE_MONTH": ("1 month", updater_options, updater_rc),
        }

        for resource_id, (english_text, source, resource_script) in expected_resources.items():
            with self.subTest(plugin_combo_resource=resource_id):
                self.assertRegex(
                    resource_script,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"',
                )
                self.assertEqual(source.count(resource_id), 1)
                self.assertNotIn(f'L"{english_text}"', source)

        for editor_name, editor in (
            ("firmware", firmware_editor),
            ("tpm", tpm_editor),
        ):
            with self.subTest(extended_tools_bytes_per_row_editor=editor_name):
                self.assertRegex(
                    editor,
                    r"PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
                    r"IDS_ET_BYTES_PER_ROW_FORMAT,\s*NULL\s*\)",
                )
                self.assertEqual(editor.count("IDS_ET_BYTES_PER_ROW_FORMAT"), 1)
                self.assertNotIn('L"%u bytes per row"', editor)
                self.assertIn("1u << (2 + i)", editor)

        self.assertEqual(
            re.findall(
                r"\{ (IDS_UP_INTERVAL_[A-Z0-9_]+), (\d+) \}",
                updater_options,
            ),
            [
                ("IDS_UP_INTERVAL_ONE_DAY", "1"),
                ("IDS_UP_INTERVAL_ONE_WEEK", "7"),
                ("IDS_UP_INTERVAL_ONE_MONTH", "30"),
            ],
        )
        self.assertIn("ComboBox_DeleteString(comboBoxHandle", updater_options)
        self.assertIn("ComboBox_GetItemData(comboBoxHandle", updater_options)
        self.assertNotIn("switch (ComboBox_GetCurSel", updater_options)
        initialization = updater_options[
            updater_options.index("case WM_INITDIALOG:"):
            updater_options.index("case WM_COMMAND:")
        ]
        self.assertLess(
            initialization.index("ARRAYSIZE(PhpUpdateIntervals)"),
            initialization.index(
                "PhGetIntegerSetting(SETTING_NAME_AUTO_CHECK)"
            ),
        )

    def test_extended_services_service_options_use_item_data_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "other.c"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "ExtendedServices.rc"
        ).read_text(encoding="utf-8-sig")
        expected_entries = [
            ("IDS_ES_SERVICE_OPTION_NONE", "SERVICE_SID_TYPE_NONE"),
            ("IDS_ES_SERVICE_SID_RESTRICTED", "SERVICE_SID_TYPE_RESTRICTED"),
            ("IDS_ES_SERVICE_SID_UNRESTRICTED", "SERVICE_SID_TYPE_UNRESTRICTED"),
            ("IDS_ES_SERVICE_OPTION_NONE", "SERVICE_LAUNCH_PROTECTED_NONE"),
            ("IDS_ES_SERVICE_PROTECTION_FULL_WINDOWS", "SERVICE_LAUNCH_PROTECTED_WINDOWS"),
            ("IDS_ES_SERVICE_PROTECTION_LIGHT_WINDOWS", "SERVICE_LAUNCH_PROTECTED_WINDOWS_LIGHT"),
            (
                "IDS_ES_SERVICE_PROTECTION_LIGHT_ANTIMALWARE",
                "SERVICE_LAUNCH_PROTECTED_ANTIMALWARE_LIGHT",
            ),
        ]
        resource_texts = {
            "IDS_ES_SERVICE_OPTION_NONE": "None",
            "IDS_ES_SERVICE_SID_RESTRICTED": "Restricted",
            "IDS_ES_SERVICE_SID_UNRESTRICTED": "Unrestricted",
            "IDS_ES_SERVICE_PROTECTION_FULL_WINDOWS": "Full (Windows)",
            "IDS_ES_SERVICE_PROTECTION_LIGHT_WINDOWS": "Light (Windows)",
            "IDS_ES_SERVICE_PROTECTION_LIGHT_ANTIMALWARE": "Light (Antimalware)",
        }

        self.assertEqual(
            re.findall(
                r"\{ (IDS_ES_SERVICE_[A-Z0-9_]+), (SERVICE_[A-Z0-9_]+) \}",
                source,
            ),
            expected_entries,
        )
        for resource_id, english_text in resource_texts.items():
            with self.subTest(extended_services_option=resource_id):
                self.assertRegex(
                    resource_script,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"',
                )

        self.assertNotIn("EspServiceSidTypePairs", source)
        self.assertNotIn("EspServiceLaunchProtectedPairs", source)
        self.assertNotIn("EspServiceSidTypeStrings", source)
        self.assertNotIn("EspServiceLaunchProtectedStrings", source)
        self.assertNotRegex(
            source,
            r"PhGetWindowText\(GetDlgItem\(WindowHandle, IDC_(?:SIDTYPE|PROTECTION)\)\)",
        )
        self.assertNotRegex(
            source,
            r"PhSelectComboBoxString\(GetDlgItem\(WindowHandle, IDC_(?:SIDTYPE|PROTECTION)\)",
        )
        self.assertIn("ComboBox_SetItemData", source)
        self.assertIn("ComboBox_DeleteString", source)
        self.assertIn("ComboBox_GetItemData", source)
        self.assertRegex(
            source,
            r"Context->SidTypeValid\s*=\s*EspSelectServiceOption\(\s*"
            r"GetDlgItem\(WindowHandle, IDC_SIDTYPE\),\s*"
            r"sidInfo\.dwServiceSidType\s*\);",
        )
        self.assertRegex(
            source,
            r"Context->LaunchProtectedValid\s*=\s*EspSelectServiceOption\(\s*"
            r"GetDlgItem\(WindowHandle, IDC_PROTECTION\),\s*"
            r"launchProtectedInfo\.dwLaunchProtected\s*\);",
        )

    def test_extended_services_trigger_choices_use_item_data_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "trigger.c"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "ExtendedServices.rc"
        ).read_text(encoding="utf-8-sig")
        expected_type_entries = [
            ("IDS_ES_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL", "SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL"),
            ("IDS_ES_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY", "SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY"),
            ("IDS_ES_TRIGGER_TYPE_DOMAIN_JOIN", "SERVICE_TRIGGER_TYPE_DOMAIN_JOIN"),
            ("IDS_ES_TRIGGER_TYPE_FIREWALL_PORT_EVENT", "SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT"),
            ("IDS_ES_TRIGGER_TYPE_GROUP_POLICY", "SERVICE_TRIGGER_TYPE_GROUP_POLICY"),
            ("IDS_ES_TRIGGER_TYPE_NETWORK_ENDPOINT", "SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT"),
            ("IDS_ES_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE", "SERVICE_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE"),
            ("IDS_ES_TRIGGER_CUSTOM", "SERVICE_TRIGGER_TYPE_CUSTOM"),
        ]
        expected_subtype_entries = [
            ("IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS", "SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY", "NULL"),
            ("IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS_FIRST_ARRIVAL", "SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY", "&NetworkManagerFirstIpAddressArrivalGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS_LAST_REMOVAL", "SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY", "&NetworkManagerLastIpAddressRemovalGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS_UNKNOWN", "SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY", "&SubTypeUnknownGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_DOMAIN", "SERVICE_TRIGGER_TYPE_DOMAIN_JOIN", "NULL"),
            ("IDS_ES_TRIGGER_SUBTYPE_DOMAIN_JOIN", "SERVICE_TRIGGER_TYPE_DOMAIN_JOIN", "&DomainJoinGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_DOMAIN_LEAVE", "SERVICE_TRIGGER_TYPE_DOMAIN_JOIN", "&DomainLeaveGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_DOMAIN_UNKNOWN", "SERVICE_TRIGGER_TYPE_DOMAIN_JOIN", "&SubTypeUnknownGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT", "SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT", "NULL"),
            ("IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT_OPEN", "SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT", "&FirewallPortOpenGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT_CLOSE", "SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT", "&FirewallPortCloseGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT_UNKNOWN", "SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT", "&SubTypeUnknownGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_CHANGE", "SERVICE_TRIGGER_TYPE_GROUP_POLICY", "NULL"),
            ("IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_MACHINE", "SERVICE_TRIGGER_TYPE_GROUP_POLICY", "&MachinePolicyPresentGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_USER", "SERVICE_TRIGGER_TYPE_GROUP_POLICY", "&UserPolicyPresentGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_UNKNOWN", "SERVICE_TRIGGER_TYPE_GROUP_POLICY", "&SubTypeUnknownGuid"),
            ("IDS_ES_TRIGGER_TYPE_NETWORK_ENDPOINT", "SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT", "NULL"),
            ("IDS_ES_TRIGGER_SUBTYPE_NETWORK_ENDPOINT_RPC", "SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT", "&RpcInterfaceEventGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_NETWORK_ENDPOINT_NAMED_PIPE", "SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT", "&NamedPipeEventGuid"),
            ("IDS_ES_TRIGGER_SUBTYPE_NETWORK_ENDPOINT_UNKNOWN", "SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT", "&SubTypeUnknownGuid"),
        ]
        expected_action_entries = [
            ("IDS_ES_TRIGGER_ACTION_START_SERVICE", "SERVICE_TRIGGER_ACTION_SERVICE_START"),
            ("IDS_ES_TRIGGER_ACTION_STOP_SERVICE", "SERVICE_TRIGGER_ACTION_SERVICE_STOP"),
        ]
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            re.findall(r"\{ (IDS_ES_TRIGGER_[A-Z0-9_]+), (SERVICE_TRIGGER_TYPE_[A-Z0-9_]+) \}", source),
            expected_type_entries,
        )
        self.assertEqual(
            re.findall(
                r"\{ (IDS_ES_TRIGGER_[A-Z0-9_]+), (SERVICE_TRIGGER_TYPE_[A-Z0-9_]+), ([^ }]+) \}",
                source,
            ),
            expected_subtype_entries,
        )
        self.assertEqual(
            re.findall(r"\{ (IDS_ES_TRIGGER_ACTION_[A-Z0-9_]+), (SERVICE_TRIGGER_ACTION_[A-Z0-9_]+) \}", source),
            expected_action_entries,
        )
        for action_text in ("Start service", "Stop service"):
            self.assertIn(action_text, translation_data["native_strings"])
            self.assertNotIn(action_text, translation_data["strings"])

        for resource_id in {
            *(entry[0] for entry in expected_type_entries),
            *(entry[0] for entry in expected_subtype_entries),
            *(entry[0] for entry in expected_action_entries),
            "IDS_ES_TRIGGER_UNKNOWN",
        }:
            with self.subTest(trigger_resource=resource_id):
                self.assertRegex(resource_script, rf"(?m)^\s*{resource_id}\s+\"")

        self.assertNotIn("EspTriggerTypeStringToInteger", source)
        self.assertNotRegex(source, r"PhaGetDlgItemText\(WindowHandle, IDC_(?:TYPE|ACTION)\)")
        self.assertNotRegex(source, r"PhGetWindowText\([^\n]*IDC_TYPE")
        self.assertNotRegex(source, r"PhEqualString2\([^\n]*L\"(?:Custom|Start|Stop)\"")
        self.assertNotRegex(source, r"ComboBox_AddString\([^\n]*L\"(?:Custom|Start|Stop)\"")
        self.assertNotRegex(source, r"\b(?:TypeEntries|SubTypeEntries)\[i\]\.Name\b")
        self.assertIn("ComboBox_SetItemData", source)
        self.assertIn("ComboBox_DeleteString", source)
        self.assertIn("ComboBox_GetItemData", source)
        self.assertIn("EspGetSelectedTriggerComboBoxItemData", source)
        self.assertIn("&EspCustomSubTypeEntry", source)

        save_body = source.split("case IDOK:", 1)[1].split("DoNotClose:", 1)[0]
        first_mutation = save_body.index("context->EditingInfo->Type = type")
        self.assertLess(save_body.index("EspGetSelectedTriggerComboBoxItemData"), first_mutation)
        self.assertLess(save_body.index("PhStringToGuid"), first_mutation)
        self.assertLess(save_body.index("SERVICE_TRIGGER_ACTION_SERVICE_START"), first_mutation)

    def test_extended_services_recovery_actions_use_item_data_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "recovery.c"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "ExtendedServices.rc"
        ).read_text(encoding="utf-8-sig")
        expected_entries = [
            ("IDS_ES_RECOVERY_ACTION_NONE", "SC_ACTION_NONE"),
            ("IDS_ES_RECOVERY_ACTION_RESTART_SERVICE", "SC_ACTION_RESTART"),
            ("IDS_ES_RECOVERY_ACTION_RESTART_COMPUTER", "SC_ACTION_REBOOT"),
            ("IDS_ES_RECOVERY_ACTION_RUN_PROGRAM", "SC_ACTION_RUN_COMMAND"),
            ("IDS_ES_RECOVERY_ACTION_OWN_RESTART", "SC_ACTION_OWN_RESTART"),
        ]
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            re.findall(
                r"\{ (IDS_ES_RECOVERY_ACTION_[A-Z0-9_]+), (SC_ACTION_[A-Z0-9_]+) \}",
                source,
            ),
            expected_entries,
        )
        for resource_id, _ in expected_entries:
            self.assertRegex(resource_script, rf"(?m)^\s*{resource_id}\s+\"")
        for action_text in (
            "Take no action",
            "Restart the service",
            "Restart the computer",
            "Run a program",
            "Own restart",
        ):
            self.assertIn(action_text, translation_data["native_strings"])
            self.assertNotIn(action_text, translation_data["strings"])

        self.assertNotIn("ServiceActionPairs", source)
        self.assertNotIn("EspStringToServiceAction", source)
        self.assertNotIn("EspServiceActionToString", source)
        self.assertNotIn("PhGetComboBoxString", source)
        self.assertIn("ComboBox_SetItemData", source)
        self.assertIn("ComboBox_GetItemData", source)
        self.assertIn("ComboBox_DeleteString", source)
        self.assertRegex(
            source,
            r"BOOLEAN ComboBoxToServiceAction\([\s\S]*?_Out_ SC_ACTION_TYPE \*ActionType",
        )
        selection_body = source.split("ServiceActionToComboBox(", 1)[1].split(
            "VOID EspFixControls", 1
        )[0]
        self.assertNotIn("noneIndex", selection_body)
        self.assertIn("ComboBox_SetCurSel(ComboBoxHandle, -1)", selection_body)
        self.assertRegex(source, r"BOOLEAN ServiceActionToComboBox\(")
        apply_body = source.split("case PSN_APPLY:", 1)[1].split(
            "// Try to save the changes.", 1
        )[0]
        self.assertEqual(apply_body.count("ComboBoxToServiceAction("), 4)
        self.assertIn("PSNRET_INVALID_NOCHANGEPAGE", apply_body)
        self.assertLess(
            apply_body.index("actions[i].Delay = 0;"),
            apply_body.index("switch (actions[i].Type)"),
        )

    def test_extended_services_dynamic_status_text_uses_native_resources(self) -> None:
        sources = {
            name: (
                REPO_ROOT / "plugins" / "ExtendedServices" / name
            ).read_text(encoding="utf-8-sig")
            for name in ("depend.c", "srvprgrs.c", "svcpnp.c")
        }
        source = "\n".join(sources.values())
        resource_script = (
            REPO_ROOT / "plugins" / "ExtendedServices" / "ExtendedServices.rc"
        ).read_text(encoding="utf-8-sig")
        resource_texts = dict(re.findall(
            r'^\s*(IDS_ES_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        expected_resources = {
            "IDS_ES_PNP_GROUP_CONNECTED": ("Connected", "svcpnp.c"),
            "IDS_ES_PNP_GROUP_DISCONNECTED": ("Disconnected", "svcpnp.c"),
            "IDS_ES_RESTART_ATTEMPTING_STOP": ("Attempting to stop %s...", "srvprgrs.c"),
            "IDS_ES_RESTART_ATTEMPTING_START": ("Attempting to start %s...", "srvprgrs.c"),
            "IDS_ES_DEPENDENCIES_MESSAGE": ("This service depends on the following services:", "depend.c"),
            "IDS_ES_UNABLE_ENUMERATE_DEPENDENCIES": ("Unable to enumerate dependencies: %s", "depend.c"),
            "IDS_ES_DEPENDENTS_MESSAGE": ("The following services depend on this service:", "depend.c"),
            "IDS_ES_UNABLE_ENUMERATE_DEPENDENTS": ("Unable to enumerate dependents: %s", "depend.c"),
            "IDS_ES_PNP_DEVICES_MESSAGE": ("This service has registered the following PnP devices:", "svcpnp.c"),
            "IDS_ES_PNP_UNSUPPORTED_MESSAGE": ("This service type doesn't support PnP devices.", "svcpnp.c"),
        }

        for resource_id, (english_text, source_name) in expected_resources.items():
            with self.subTest(extended_services_dynamic_text=resource_id):
                self.assertEqual(resource_texts.get(resource_id), english_text)
                self.assertEqual(sources[source_name].count(resource_id), 1)
                self.assertNotIn(f'L"{english_text}"', source)

        for source_name in sources:
            with self.subTest(extended_services_source=source_name):
                self.assertIn("PhLoadUiString(", sources[source_name])

        self.assertEqual(sources["depend.c"].count("IDS_ES_UNKNOWN_ERROR"), 2)
        self.assertNotIn('L"Unknown error."', sources["depend.c"])
        self.assertNotIn("PhaConcatStrings2(", sources["depend.c"])

        restart_initialization, restart_timer = sources["srvprgrs.c"].split(
            "case WM_TIMER:", 1
        )
        self.assertIn("IDS_ES_RESTART_ATTEMPTING_STOP", restart_initialization)
        self.assertNotIn("IDS_ES_RESTART_ATTEMPTING_START", restart_initialization)
        self.assertIn("IDS_ES_RESTART_ATTEMPTING_START", restart_timer)
        self.assertNotIn("IDS_ES_RESTART_ATTEMPTING_STOP", restart_timer)

        dependencies, dependents = sources["depend.c"].split(
            "INT_PTR CALLBACK EspServiceDependentsDlgProc", 1
        )
        self.assertIn("IDS_ES_DEPENDENCIES_MESSAGE", dependencies)
        self.assertIn("IDS_ES_UNABLE_ENUMERATE_DEPENDENCIES", dependencies)
        self.assertNotIn("IDS_ES_DEPENDENTS_MESSAGE", dependencies)
        self.assertNotIn("IDS_ES_UNABLE_ENUMERATE_DEPENDENTS", dependencies)
        self.assertRegex(
            dependencies,
            r"PhSetDialogItemText\(\s*WindowHandle,\s*IDC_MESSAGE,\s*"
            r"PhGetString\(PH_AUTO\(PhLoadUiString\([^;]*?"
            r"IDS_ES_DEPENDENCIES_MESSAGE",
        )
        self.assertRegex(
            dependencies,
            r"PhaFormatString\(\s*PhGetString\(PH_AUTO\(PhLoadUiString\([^;]*?"
            r"IDS_ES_UNABLE_ENUMERATE_DEPENDENCIES",
        )
        self.assertIn("IDS_ES_DEPENDENTS_MESSAGE", dependents)
        self.assertIn("IDS_ES_UNABLE_ENUMERATE_DEPENDENTS", dependents)
        self.assertNotIn("IDS_ES_DEPENDENCIES_MESSAGE", dependents)
        self.assertNotIn("IDS_ES_UNABLE_ENUMERATE_DEPENDENCIES", dependents)
        self.assertRegex(
            dependents,
            r"PhSetDialogItemText\(\s*WindowHandle,\s*IDC_MESSAGE,\s*"
            r"PhGetString\(PH_AUTO\(PhLoadUiString\([^;]*?"
            r"IDS_ES_DEPENDENTS_MESSAGE",
        )
        self.assertRegex(
            dependents,
            r"PhaFormatString\(\s*PhGetString\(PH_AUTO\(PhLoadUiString\([^;]*?"
            r"IDS_ES_UNABLE_ENUMERATE_DEPENDENTS",
        )

        self.assertRegex(
            sources["svcpnp.c"],
            r"PhAddListViewGroup\([^;]*?0,[^;]*?IDS_ES_PNP_GROUP_CONNECTED[^;]*?\);",
        )
        self.assertRegex(
            sources["svcpnp.c"],
            r"PhAddListViewGroup\([^;]*?1,[^;]*?IDS_ES_PNP_GROUP_DISCONNECTED[^;]*?\);",
        )
        pnp_driver, pnp_non_driver = sources["svcpnp.c"].split(
            "if (context->ServiceItem->Type & SERVICE_DRIVER)", 1
        )[1].split("            else\n", 1)
        self.assertIn("IDS_ES_PNP_DEVICES_MESSAGE", pnp_driver)
        self.assertNotIn("IDS_ES_PNP_UNSUPPORTED_MESSAGE", pnp_driver)
        self.assertIn("IDS_ES_PNP_UNSUPPORTED_MESSAGE", pnp_non_driver)
        self.assertNotIn("IDS_ES_PNP_DEVICES_MESSAGE", pnp_non_driver)

    def test_session_shadow_hotkeys_use_item_data_resources(self) -> None:
        source = (
            REPO_ROOT / "SystemInformer" / "sessshad.c"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "SystemInformer" / "SystemInformer.rc"
        ).read_text(encoding="utf-8-sig")
        expected_entries = [
            ("IDS_PH_SESSION_KEY_BACKSPACE", "VK_BACK"),
            ("IDS_PH_SESSION_KEY_DELETE", "VK_DELETE"),
            ("IDS_PH_SESSION_KEY_DOWN", "VK_DOWN"),
            ("IDS_PH_SESSION_KEY_END", "VK_END"),
            ("IDS_PH_SESSION_KEY_ENTER", "VK_RETURN"),
            ("IDS_PH_SESSION_KEY_HOME", "VK_HOME"),
            ("IDS_PH_SESSION_KEY_INSERT", "VK_INSERT"),
            ("IDS_PH_SESSION_KEY_LEFT", "VK_LEFT"),
            ("IDS_PH_SESSION_KEY_PAGE_DOWN", "VK_NEXT"),
            ("IDS_PH_SESSION_KEY_PAGE_UP", "VK_PRIOR"),
            ("IDS_PH_SESSION_KEY_PRINT_SCREEN", "VK_SNAPSHOT"),
            ("IDS_PH_SESSION_KEY_RIGHT", "VK_RIGHT"),
            ("IDS_PH_SESSION_KEY_SPACE", "VK_SPACE"),
            ("IDS_PH_SESSION_KEY_TAB", "VK_TAB"),
            ("IDS_PH_SESSION_KEY_UP", "VK_UP"),
        ]
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            re.findall(
                r"\{ (IDS_PH_SESSION_KEY_[A-Z0-9_]+), (VK_[A-Z0-9_]+) \}",
                source,
            ),
            expected_entries,
        )
        for resource_id, _ in expected_entries:
            self.assertRegex(resource_script, rf"(?m)^\s*{resource_id}\s+\"")
        for key_text in (
            "{Backspace}",
            "{Delete}",
            "{Down}",
            "{End}",
            "{Enter}",
            "{Home}",
            "{Insert}",
            "{Left}",
            "{Page Down}",
            "{Page Up}",
            "{Print Screen}",
            "{Right}",
            "{Space}",
            "{Tab}",
            "{Up}",
        ):
            self.assertIn(key_text, translation_data["native_strings"])
            self.assertNotIn(key_text, translation_data["strings"])

        self.assertNotIn("VirtualKeyPairs", source)
        self.assertNotIn("PhFindIntegerSiKeyValuePairs", source)
        self.assertNotRegex(source, r"PhaGetDlgItemText\(hwndDlg, IDC_VIRTUALKEY\)")
        self.assertNotRegex(source, r"PhSelectComboBoxString\(virtualKeyComboBox")
        self.assertIn("ComboBox_SetItemData", source)
        self.assertIn("ComboBox_GetItemData", source)
        self.assertIn("ComboBox_DeleteString", source)
        self.assertIn("PhpAddSessionShadowHotKey", source)
        self.assertIn("PhpGetSessionShadowHotKey", source)
        self.assertRegex(source, r"for \(WCHAR key = L'0'; key <= L'9'; key\+\+\)")
        self.assertRegex(source, r"for \(WCHAR key = L'A'; key <= L'Z'; key\+\+\)")
        self.assertIn("{ 0, VK_F2 }", source)
        self.assertIn("{ 0, VK_F12 }", source)
        self.assertIn('PhFormatString(L"{F%lu}"', source)
        save_body = source.split("case IDOK:", 1)[1].split("modifiers = 0;", 1)[0]
        self.assertIn("if (!PhpGetSessionShadowHotKey", save_body)

    def test_window_explorer_uia_groups_use_native_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "wndprp.c"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "WindowExplorer.rc"
        ).read_text(encoding="utf-8-sig")
        resource_texts = dict(re.findall(
            r'^\s*(IDS_WE_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "IDS_WE_UIA_GROUP_IDENTIFICATION": ("Identification", "WND_UIA_GROUP_IDENTIFICATION"),
            "IDS_WE_UIA_GROUP_ACCESSIBILITY": ("Accessibility", "WND_UIA_GROUP_ACCESSIBILITY"),
            "IDS_WE_UIA_GROUP_PATTERNS": ("Patterns", "WND_UIA_GROUP_PATTERNS"),
        }

        for resource_id, (english_text, group_id) in expected_resources.items():
            with self.subTest(window_explorer_uia_group=resource_id):
                self.assertEqual(resource_texts.get(resource_id), english_text)
                self.assertNotIn(f'L"{english_text}"', source)
                self.assertRegex(
                    source,
                    rf"PhAddListViewGroup\([^;]*?{group_id},[^;]*?"
                    rf"PhLoadUiString\([^;]*?{resource_id}[^;]*?\)[^;]*?\);",
                )

        self.assertRegex(
            source,
            r'PhAddListViewGroup\(ListViewHandle, WND_UIA_GROUP_STATE, L"State"\);',
        )
        self.assertEqual(translation_data["strings"].get("State"), "状态")
        self.assertNotIn("State", translation_data["native_strings"])

    def test_window_explorer_window_property_items_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "wndprp.c"
        ).read_text(encoding="utf-8-sig")
        source = audit.mask_c_comments(source)
        resource_header = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "WindowExplorer.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_resource = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "WindowExplorer.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "IDS_WE_WINDOW_PROPERTY_APP_ID": (12010, "AppId", "应用 ID"),
            "IDS_WE_WINDOW_PROPERTY_THREAD": (12011, "Thread", "线程"),
            "IDS_WE_WINDOW_PROPERTY_RECTANGLE": (12012, "Rectangle", "矩形"),
            "IDS_WE_WINDOW_PROPERTY_NORMAL_RECTANGLE": (12013, "Normal rectangle", "正常位置矩形"),
            "IDS_WE_WINDOW_PROPERTY_CLIENT_RECTANGLE": (12014, "Client rectangle", "客户区矩形"),
            "IDS_WE_WINDOW_PROPERTY_INSTANCE_HANDLE": (12015, "Instance handle", "实例句柄"),
            "IDS_WE_WINDOW_PROPERTY_MENU_HANDLE": (12016, "Menu handle", "菜单句柄"),
            "IDS_WE_WINDOW_PROPERTY_USER_DATA": (12017, "User data", "用户数据"),
            "IDS_WE_WINDOW_PROPERTY_UNICODE": (12018, "Unicode", "Unicode"),
            "IDS_WE_WINDOW_PROPERTY_WINDOW_TEXT": (12019, "Window text", "窗口文本"),
            "IDS_WE_WINDOW_PROPERTY_WINDOW_HANDLE": (12020, "Window handle", "窗口句柄"),
            "IDS_WE_WINDOW_PROPERTY_WINDOW_UNIQUE_ID": (12021, "Window unique id", "窗口唯一 ID"),
            "IDS_WE_WINDOW_PROPERTY_MESSAGE_ONLY": (12022, "Window message-only", "仅消息窗口"),
            "IDS_WE_WINDOW_PROPERTY_EXTRA_BYTES": (12023, "Window extra bytes", "窗口附加字节"),
            "IDS_WE_WINDOW_PROPERTY_PROCEDURE": (12024, "Window procedure", "窗口过程"),
            "IDS_WE_WINDOW_PROPERTY_DIALOG_PROCEDURE": (12025, "Dialog procedure", "对话框过程"),
            "IDS_WE_WINDOW_PROPERTY_DIALOG_CONTROL_ID": (12026, "Dialog control ID", "对话框控件 ID"),
            "IDS_WE_WINDOW_PROPERTY_FONT": (12027, "Font", "字体"),
            "IDS_WE_WINDOW_PROPERTY_STYLES": (12028, "Styles", "样式"),
            "IDS_WE_WINDOW_PROPERTY_EXTENDED_STYLES": (12029, "Extended styles", "扩展样式"),
            "IDS_WE_WINDOW_PROPERTY_AUTOMATION_SERVER": (12030, "Automation server", "自动化服务器"),
            "IDS_WE_WINDOW_PROPERTY_DPI_CONTEXT": (12031, "DPI Context", "DPI 上下文"),
            "IDS_WE_WINDOW_PROPERTY_MONITOR": (12032, "Monitor", "监视器"),
            "IDS_WE_WINDOW_PROPERTY_TOP_LEVEL": (12033, "Top level", "顶层窗口"),
            "IDS_WE_WINDOW_PROPERTY_CLOAKED": (12034, "Cloaked", "隐匿状态"),
            "IDS_WE_WINDOW_PROPERTY_BAND": (12035, "Band", "窗口带"),
            "IDS_WE_WINDOW_PROPERTY_IME_WINDOW": (12036, "IME Window", "IME 窗口"),
            "IDS_WE_WINDOW_PROPERTY_EXCLUSIVE_OWNERSHIP": (12037, "Exclusive ownership", "独占所有权"),
            "IDS_WE_WINDOW_PROPERTY_NAME": (12038, "Name", "名称"),
            "IDS_WE_WINDOW_PROPERTY_BASE_NAME": (12039, "Base name", "基类名"),
            "IDS_WE_WINDOW_PROPERTY_ATOM": (12040, "Atom", "原子"),
            "IDS_WE_WINDOW_PROPERTY_LARGE_ICON_HANDLE": (12041, "Large icon handle", "大图标句柄"),
            "IDS_WE_WINDOW_PROPERTY_SMALL_ICON_HANDLE": (12042, "Small icon handle", "小图标句柄"),
            "IDS_WE_WINDOW_PROPERTY_CURSOR_HANDLE": (12043, "Cursor handle", "光标句柄"),
            "IDS_WE_WINDOW_PROPERTY_BACKGROUND_BRUSH": (12044, "Background brush", "背景画刷"),
            "IDS_WE_WINDOW_PROPERTY_MENU_NAME": (12045, "Menu name", "菜单名称"),
            "IDS_WE_WINDOW_PROPERTY_DROP_SHADOW": (12046, "Drop shadow", "阴影"),
            "IDS_WE_WINDOW_PROPERTY_SAVE_BITS": (12047, "Save bits", "保存位图"),
        }
        expected_routes = [
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_APPID", "IDS_WE_WINDOW_PROPERTY_APP_ID"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_THREAD", "IDS_WE_WINDOW_PROPERTY_THREAD"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_RECT", "IDS_WE_WINDOW_PROPERTY_RECTANGLE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_NORMALRECT", "IDS_WE_WINDOW_PROPERTY_NORMAL_RECTANGLE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_CLIENTRECT", "IDS_WE_WINDOW_PROPERTY_CLIENT_RECTANGLE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_INSTANCE", "IDS_WE_WINDOW_PROPERTY_INSTANCE_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_MENUHANDLE", "IDS_WE_WINDOW_PROPERTY_MENU_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_USERDATA", "IDS_WE_WINDOW_PROPERTY_USER_DATA"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_UNICODE", "IDS_WE_WINDOW_PROPERTY_UNICODE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_WNDTEXT", "IDS_WE_WINDOW_PROPERTY_WINDOW_TEXT"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_WNDHANDLE", "IDS_WE_WINDOW_PROPERTY_WINDOW_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_WNDUNIQID", "IDS_WE_WINDOW_PROPERTY_WINDOW_UNIQUE_ID"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_WNDMSGONLY", "IDS_WE_WINDOW_PROPERTY_MESSAGE_ONLY"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_WNDEXTRA", "IDS_WE_WINDOW_PROPERTY_EXTRA_BYTES"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_WNDPROC", "IDS_WE_WINDOW_PROPERTY_PROCEDURE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_DLGPROC", "IDS_WE_WINDOW_PROPERTY_DIALOG_PROCEDURE"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_DLGCTLID", "IDS_WE_WINDOW_PROPERTY_DIALOG_CONTROL_ID"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_FONTNAME", "IDS_WE_WINDOW_PROPERTY_FONT"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_STYLES", "IDS_WE_WINDOW_PROPERTY_STYLES"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_EXSTYLES", "IDS_WE_WINDOW_PROPERTY_EXTENDED_STYLES"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_AUTOMATION", "IDS_WE_WINDOW_PROPERTY_AUTOMATION_SERVER"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_DPICONTEXT", "IDS_WE_WINDOW_PROPERTY_DPI_CONTEXT"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_MONITOR", "IDS_WE_WINDOW_PROPERTY_MONITOR"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_TOPLEVEL", "IDS_WE_WINDOW_PROPERTY_TOP_LEVEL"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_CLOAKED", "IDS_WE_WINDOW_PROPERTY_CLOAKED"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_IAMID", "IDS_WE_WINDOW_PROPERTY_BAND"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_IMEWND", "IDS_WE_WINDOW_PROPERTY_IME_WINDOW"),
            ("WINDOW_PROPERTIES_CATEGORY_GENERAL", "WINDOW_PROPERTIES_INDEX_D3DKMT_EXCLUSIVE", "IDS_WE_WINDOW_PROPERTY_EXCLUSIVE_OWNERSHIP"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_NAME", "IDS_WE_WINDOW_PROPERTY_NAME"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_BASENAME", "IDS_WE_WINDOW_PROPERTY_BASE_NAME"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_ATOM", "IDS_WE_WINDOW_PROPERTY_ATOM"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_STYLES", "IDS_WE_WINDOW_PROPERTY_STYLES"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_INSTANCE", "IDS_WE_WINDOW_PROPERTY_INSTANCE_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_LARGEICON", "IDS_WE_WINDOW_PROPERTY_LARGE_ICON_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_SMALLICON", "IDS_WE_WINDOW_PROPERTY_SMALL_ICON_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_CURSOR", "IDS_WE_WINDOW_PROPERTY_CURSOR_HANDLE"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_BACKBRUSH", "IDS_WE_WINDOW_PROPERTY_BACKGROUND_BRUSH"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_MENUNAME", "IDS_WE_WINDOW_PROPERTY_MENU_NAME"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_WNDEXTRA", "IDS_WE_WINDOW_PROPERTY_EXTRA_BYTES"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_WNDPROC", "IDS_WE_WINDOW_PROPERTY_PROCEDURE"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_DROPSHADOW", "IDS_WE_WINDOW_PROPERTY_DROP_SHADOW"),
            ("WINDOW_PROPERTIES_CATEGORY_CLASS", "WINDOW_PROPERTIES_INDEX_CLASS_SAVEBITS", "IDS_WE_WINDOW_PROPERTY_SAVE_BITS"),
        ]
        runtime_owned = {"Thread", "Unicode", "Monitor", "Name"}
        actual_routes = Counter(re.findall(
            r"PhAddListViewGroupItem\(\s*ListViewHandle,\s*"
            r"(WINDOW_PROPERTIES_CATEGORY_(?:GENERAL|CLASS)),\s*"
            r"(WINDOW_PROPERTIES_INDEX_[A-Z0-9_]+),\s*"
            r"PhGetString\(PH_AUTO\(PhLoadUiString\(\s*"
            r"PluginInstance->DllBase,\s*(IDS_WE_WINDOW_PROPERTY_[A-Z0-9_]+),\s*"
            r"NULL\s*\)\)\),\s*NULL\s*\);",
            source,
        ))

        for resource_id, (numeric_id, english_text, chinese_text) in expected_resources.items():
            with self.subTest(window_property_resource=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                table_name = "strings" if english_text in runtime_owned else "native_strings"
                other_table = "native_strings" if table_name == "strings" else "strings"
                self.assertEqual(translation_data[table_name].get(english_text), chinese_text)
                self.assertNotIn(english_text, translation_data[other_table])

        self.assertEqual(actual_routes, Counter(expected_routes))

        for _, english_text, _ in expected_resources.values():
            with self.subTest(removed_window_property_literal=english_text):
                self.assertNotRegex(
                    source,
                    rf"PhAddListViewGroupItem\([^;]*L\"{re.escape(english_text)}\"[^;]*\);",
                )

    def test_window_explorer_uia_property_items_use_native_resources(self) -> None:
        audit = load_audit_module()
        source = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "wndprp.c"
        ).read_text(encoding="utf-8-sig")
        source = audit.mask_c_comments(source)
        resource_header = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "WindowExplorer.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_resource = (
            REPO_ROOT / "plugins" / "WindowExplorer" / "WindowExplorer.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "IDS_WE_UIA_PROPERTY_RUNTIME_ID": (12048, "Runtime ID", "运行时 ID"),
            "IDS_WE_UIA_PROPERTY_AUTOMATION_ID": (12049, "Automation ID", "自动化 ID"),
            "IDS_WE_UIA_PROPERTY_CLASS_NAME": (12050, "Class Name", "类名"),
            "IDS_WE_UIA_PROPERTY_CONTROL_TYPE": (12051, "Control Type", "控件类型"),
            "IDS_WE_UIA_PROPERTY_LOCALIZED_CONTROL_TYPE": (12052, "Localized Control Type", "本地化控件类型"),
            "IDS_WE_UIA_PROPERTY_FRAMEWORK_ID": (12053, "Framework ID", "框架 ID"),
            "IDS_WE_UIA_PROPERTY_PROCESS_ID": (12054, "Process ID", "进程 ID"),
            "IDS_WE_UIA_PROPERTY_NATIVE_WINDOW_HANDLE": (12055, "Native Window Handle", "原生窗口句柄"),
            "IDS_WE_UIA_PROPERTY_IS_ENABLED": (12056, "Is Enabled", "已启用"),
            "IDS_WE_UIA_PROPERTY_IS_KEYBOARD_FOCUSABLE": (12057, "Is Keyboard Focusable", "可获得键盘焦点"),
            "IDS_WE_UIA_PROPERTY_HAS_KEYBOARD_FOCUS": (12058, "Has Keyboard Focus", "拥有键盘焦点"),
            "IDS_WE_UIA_PROPERTY_IS_OFFSCREEN": (12059, "Is Offscreen", "位于屏幕外"),
            "IDS_WE_UIA_PROPERTY_IS_PASSWORD": (12060, "Is Password", "密码控件"),
            "IDS_WE_UIA_PROPERTY_IS_REQUIRED_FOR_FORM": (12061, "Is Required For Form", "表单必填项"),
            "IDS_WE_UIA_PROPERTY_ORIENTATION": (12062, "Orientation", "方向"),
            "IDS_WE_UIA_PROPERTY_ITEM_STATUS": (12063, "Item Status", "项目状态"),
            "IDS_WE_UIA_PROPERTY_ACCELERATOR_KEY": (12064, "Accelerator Key", "加速键"),
            "IDS_WE_UIA_PROPERTY_ACCESS_KEY": (12065, "Access Key", "访问键"),
            "IDS_WE_UIA_PROPERTY_HELP_TEXT": (12066, "Help Text", "帮助文本"),
            "IDS_WE_UIA_PROPERTY_LABELED_BY": (12067, "Labeled By", "标签来源"),
            "IDS_WE_UIA_PROPERTY_BOUNDING_RECTANGLE": (12068, "Bounding Rectangle", "边界矩形"),
            "IDS_WE_UIA_PROPERTY_CLICKABLE_POINT": (12069, "Clickable Point", "可点击点"),
            "IDS_WE_UIA_PROPERTY_ITEM_TYPE": (12070, "Item Type", "项目类型"),
            "IDS_WE_UIA_PROPERTY_FULL_DESCRIPTION": (12071, "Full Description", "完整描述"),
            "IDS_WE_UIA_PROPERTY_DOCK_PATTERN": (12072, "Is Dock Pattern Available", "停靠模式可用"),
            "IDS_WE_UIA_PROPERTY_EXPAND_COLLAPSE_PATTERN": (12073, "Is Expand/Collapse Pattern Available", "展开/折叠模式可用"),
            "IDS_WE_UIA_PROPERTY_GRID_ITEM_PATTERN": (12074, "Is Grid Item Pattern Available", "网格项模式可用"),
            "IDS_WE_UIA_PROPERTY_GRID_PATTERN": (12075, "Is Grid Pattern Available", "网格模式可用"),
            "IDS_WE_UIA_PROPERTY_INVOKE_PATTERN": (12076, "Is Invoke Pattern Available", "调用模式可用"),
            "IDS_WE_UIA_PROPERTY_MULTIPLE_VIEW_PATTERN": (12077, "Is Multiple View Pattern Available", "多视图模式可用"),
            "IDS_WE_UIA_PROPERTY_RANGE_VALUE_PATTERN": (12078, "Is Range Value Pattern Available", "范围值模式可用"),
            "IDS_WE_UIA_PROPERTY_SELECTION_ITEM_PATTERN": (12079, "Is Selection Item Pattern Available", "选择项模式可用"),
            "IDS_WE_UIA_PROPERTY_SELECTION_PATTERN": (12080, "Is Selection Pattern Available", "选择模式可用"),
            "IDS_WE_UIA_PROPERTY_SCROLL_PATTERN": (12081, "Is Scroll Pattern Available", "滚动模式可用"),
            "IDS_WE_UIA_PROPERTY_SCROLL_ITEM_PATTERN": (12082, "Is Scroll Item Pattern Available", "滚动项模式可用"),
            "IDS_WE_UIA_PROPERTY_TABLE_PATTERN": (12083, "Is Table Pattern Available", "表格模式可用"),
            "IDS_WE_UIA_PROPERTY_TABLE_ITEM_PATTERN": (12084, "Is Table Item Pattern Available", "表格项模式可用"),
            "IDS_WE_UIA_PROPERTY_TEXT_PATTERN": (12085, "Is Text Pattern Available", "文本模式可用"),
            "IDS_WE_UIA_PROPERTY_TOGGLE_PATTERN": (12086, "Is Toggle Pattern Available", "切换模式可用"),
            "IDS_WE_UIA_PROPERTY_TRANSFORM_PATTERN": (12087, "Is Transform Pattern Available", "变换模式可用"),
            "IDS_WE_UIA_PROPERTY_VALUE_PATTERN": (12088, "Is Value Pattern Available", "值模式可用"),
            "IDS_WE_UIA_PROPERTY_WINDOW_PATTERN": (12089, "Is Window Pattern Available", "窗口模式可用"),
        }
        expected_routes = [
            ("UIA_RuntimeIdPropertyId", "IDS_WE_UIA_PROPERTY_RUNTIME_ID", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_NamePropertyId", "IDS_WE_WINDOW_PROPERTY_NAME", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_AutomationIdPropertyId", "IDS_WE_UIA_PROPERTY_AUTOMATION_ID", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_ClassNamePropertyId", "IDS_WE_UIA_PROPERTY_CLASS_NAME", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_ControlTypePropertyId", "IDS_WE_UIA_PROPERTY_CONTROL_TYPE", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_LocalizedControlTypePropertyId", "IDS_WE_UIA_PROPERTY_LOCALIZED_CONTROL_TYPE", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_FrameworkIdPropertyId", "IDS_WE_UIA_PROPERTY_FRAMEWORK_ID", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_ProcessIdPropertyId", "IDS_WE_UIA_PROPERTY_PROCESS_ID", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_NativeWindowHandlePropertyId", "IDS_WE_UIA_PROPERTY_NATIVE_WINDOW_HANDLE", "WND_UIA_GROUP_IDENTIFICATION"),
            ("UIA_IsEnabledPropertyId", "IDS_WE_UIA_PROPERTY_IS_ENABLED", "WND_UIA_GROUP_STATE"),
            ("UIA_IsKeyboardFocusablePropertyId", "IDS_WE_UIA_PROPERTY_IS_KEYBOARD_FOCUSABLE", "WND_UIA_GROUP_STATE"),
            ("UIA_HasKeyboardFocusPropertyId", "IDS_WE_UIA_PROPERTY_HAS_KEYBOARD_FOCUS", "WND_UIA_GROUP_STATE"),
            ("UIA_IsOffscreenPropertyId", "IDS_WE_UIA_PROPERTY_IS_OFFSCREEN", "WND_UIA_GROUP_STATE"),
            ("UIA_IsPasswordPropertyId", "IDS_WE_UIA_PROPERTY_IS_PASSWORD", "WND_UIA_GROUP_STATE"),
            ("UIA_IsRequiredForFormPropertyId", "IDS_WE_UIA_PROPERTY_IS_REQUIRED_FOR_FORM", "WND_UIA_GROUP_STATE"),
            ("UIA_OrientationPropertyId", "IDS_WE_UIA_PROPERTY_ORIENTATION", "WND_UIA_GROUP_STATE"),
            ("UIA_ItemStatusPropertyId", "IDS_WE_UIA_PROPERTY_ITEM_STATUS", "WND_UIA_GROUP_STATE"),
            ("UIA_AcceleratorKeyPropertyId", "IDS_WE_UIA_PROPERTY_ACCELERATOR_KEY", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_AccessKeyPropertyId", "IDS_WE_UIA_PROPERTY_ACCESS_KEY", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_HelpTextPropertyId", "IDS_WE_UIA_PROPERTY_HELP_TEXT", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_LabeledByPropertyId", "IDS_WE_UIA_PROPERTY_LABELED_BY", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_BoundingRectanglePropertyId", "IDS_WE_UIA_PROPERTY_BOUNDING_RECTANGLE", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_ClickablePointPropertyId", "IDS_WE_UIA_PROPERTY_CLICKABLE_POINT", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_ItemTypePropertyId", "IDS_WE_UIA_PROPERTY_ITEM_TYPE", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_FullDescriptionPropertyId", "IDS_WE_UIA_PROPERTY_FULL_DESCRIPTION", "WND_UIA_GROUP_ACCESSIBILITY"),
            ("UIA_IsDockPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_DOCK_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsExpandCollapsePatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_EXPAND_COLLAPSE_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsGridItemPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_GRID_ITEM_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsGridPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_GRID_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsInvokePatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_INVOKE_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsMultipleViewPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_MULTIPLE_VIEW_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsRangeValuePatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_RANGE_VALUE_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsSelectionItemPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_SELECTION_ITEM_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsSelectionPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_SELECTION_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsScrollPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_SCROLL_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsScrollItemPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_SCROLL_ITEM_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsTablePatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_TABLE_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsTableItemPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_TABLE_ITEM_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsTextPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_TEXT_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsTogglePatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_TOGGLE_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsTransformPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_TRANSFORM_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsValuePatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_VALUE_PATTERN", "WND_UIA_GROUP_PATTERNS"),
            ("UIA_IsWindowPatternAvailablePropertyId", "IDS_WE_UIA_PROPERTY_WINDOW_PATTERN", "WND_UIA_GROUP_PATTERNS"),
        ]

        for resource_id, (numeric_id, english_text, chinese_text) in expected_resources.items():
            with self.subTest(uia_property_resource=resource_id):
                self.assertRegex(resource_header, rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$")
                self.assertRegex(english_resource, rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$')
                self.assertRegex(chinese_resource, rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$')
                table_name = "strings" if english_text == "Process ID" else "native_strings"
                other_table = "native_strings" if table_name == "strings" else "strings"
                self.assertEqual(translation_data[table_name].get(english_text), chinese_text)
                self.assertNotIn(english_text, translation_data[other_table])

        actual_routes = re.findall(
            r"\{\s*&(UIA_[A-Za-z0-9]+PropertyId),\s*(IDS_WE_[A-Z0-9_]+),\s*"
            r"(WND_UIA_GROUP_[A-Z]+)\s*\}",
            source,
        )
        self.assertEqual(actual_routes, expected_routes)
        self.assertRegex(
            source,
            r"PhAddListViewGroupItem\(\s*ListViewHandle,\s*"
            r"WndUiaProperties\[i\]\.GroupId,\s*i,\s*"
            r"PhGetString\(PH_AUTO\(PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
            r"WndUiaProperties\[i\]\.NameResourceId,\s*NULL\s*\)\)\),\s*NULL\s*\);",
        )
        uia_array = source.split(
            "static WND_UIA_PROPERTY WndUiaProperties[] = {", 1
        )[1].split("\n};", 1)[0]
        self.assertNotIn('L"', uia_array)

    def test_dotnet_performance_groups_use_native_resources(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "DotNetTools" / "perfpage.c"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "plugins" / "DotNetTools" / "DotNetTools.rc"
        ).read_text(encoding="utf-8-sig")
        resource_texts = dict(re.findall(
            r'^\s*(IDS_DN_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_resources = {
            "DOTNET_CATEGORY_MEMORY": (
                "IDS_DN_PERF_GROUP_MEMORY",
                ".NET CLR Memory",
            ),
            "DOTNET_CATEGORY_EXCEPTIONS": (
                "IDS_DN_PERF_GROUP_EXCEPTIONS",
                ".NET CLR Exceptions",
            ),
            "DOTNET_CATEGORY_INTEROP": (
                "IDS_DN_PERF_GROUP_INTEROP",
                ".NET CLR Interop",
            ),
            "DOTNET_CATEGORY_JIT": (
                "IDS_DN_PERF_GROUP_JIT",
                ".NET CLR Jit",
            ),
            "DOTNET_CATEGORY_LOADING": (
                "IDS_DN_PERF_GROUP_LOADING",
                ".NET CLR Loading",
            ),
            "DOTNET_CATEGORY_LOCKSANDTHREADS": (
                "IDS_DN_PERF_GROUP_LOCKS_AND_THREADS",
                ".NET CLR LocksAndThreads",
            ),
            "DOTNET_CATEGORY_REMOTING": (
                "IDS_DN_PERF_GROUP_REMOTING",
                ".NET CLR Remoting",
            ),
            "DOTNET_CATEGORY_SECURITY": (
                "IDS_DN_PERF_GROUP_SECURITY",
                ".NET CLR Security",
            ),
        }
        category_strings_match = re.search(
            r"CONST\s+PCWSTR\s+DotNetCategoryStrings\s*\[\s*\]\s*=\s*"
            r"\{(?P<items>.*?)\};",
            source,
            re.DOTALL,
        )

        self.assertIsNotNone(category_strings_match)
        self.assertEqual(
            re.findall(
                r'L"((?:[^"\\]|\\.)*)"',
                category_strings_match.group("items"),
            ),
            [
                ".NET CLR Exceptions",
                ".NET CLR Interop",
                ".NET CLR Jit",
                ".NET CLR Loading",
                ".NET CLR LocksAndThreads",
                ".NET CLR Memory",
                ".NET CLR Remoting",
                ".NET CLR Security",
            ],
        )

        for group_id, (resource_id, english_text) in expected_resources.items():
            with self.subTest(dotnet_performance_group=group_id):
                self.assertEqual(resource_texts.get(resource_id), english_text)
                self.assertRegex(
                    source,
                    rf"PhAddListViewGroup\([^;]*?{group_id},[^;]*?"
                    rf"PhLoadUiString\([^;]*?{resource_id}[^;]*?\)[^;]*?\);",
                )
                self.assertEqual(source.count(f'L"{english_text}"'), 1)
                self.assertIn(english_text, translation_data["native_strings"])
                self.assertNotIn(english_text, translation_data["strings"])

    def test_dotnet_performance_batch_a_items_use_native_resources(self) -> None:
        audit = load_audit_module()
        source_path = REPO_ROOT / "plugins" / "DotNetTools" / "perfpage.c"
        source = audit.mask_c_comments(source_path.read_text(encoding="utf-8-sig"))
        resource_header = (
            REPO_ROOT / "plugins" / "DotNetTools" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = (
            REPO_ROOT / "plugins" / "DotNetTools" / "DotNetTools.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_resource = (
            REPO_ROOT / "plugins" / "DotNetTools" / "DotNetTools.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        expected_resources = {
            "IDS_DN_PERF_ITEM_MEMORY_GENZEROCOLLECTIONS": (
                2008,
                "# Gen 0 Collections",
                "第 0 代 GC 次数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GENZEROCOLLECTIONS",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GENONECOLLECTIONS": (
                2009,
                "# Gen 1 Collections",
                "第 1 代 GC 次数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GENONECOLLECTIONS",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GENTWOCOLLECTIONS": (
                2010,
                "# Gen 2 Collections",
                "第 2 代 GC 次数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GENTWOCOLLECTIONS",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_PROMOTEDFROMGENZERO": (
                2011,
                "Promoted Memory from Gen 0",
                "从第 0 代提升的内存",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_PROMOTEDFROMGENZERO",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_PROMOTEDFROMGENONE": (
                2012,
                "Promoted Memory from Gen 1",
                "从第 1 代提升的内存",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_PROMOTEDFROMGENONE",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_PROMOTEDFINALFROMGENZERO": (
                2013,
                "Promoted Finalization-Memory from Gen 0",
                "因等待终结而从第 0 代提升的内存",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_PROMOTEDFINALFROMGENZERO",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_PROCESSID": (
                2014,
                "Process ID",
                "进程 ID",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_PROCESSID",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GENZEROHEAPSIZE": (
                2015,
                "Gen 0 Heap Size",
                "第 0 代堆大小",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GENZEROHEAPSIZE",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GENONEHEAPSIZE": (
                2016,
                "Gen 1 Heap Size",
                "第 1 代堆大小",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GENONEHEAPSIZE",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GENTWOHEAPSIZE": (
                2017,
                "Gen 2 Heap Size",
                "第 2 代堆大小",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GENTWOHEAPSIZE",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_LOHSIZE": (
                2018,
                "Large Object Heap Size",
                "大型对象堆大小",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_LOHSIZE",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_FINALSURVIVORS": (
                2019,
                "Finalization Survivors",
                "待终结存活对象数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_FINALSURVIVORS",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GCHANDLES": (
                2020,
                "# GC Handles",
                "GC 句柄数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GCHANDLES",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_INDUCEDGC": (
                2021,
                "# Induced GC",
                "强制 GC 次数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_INDUCEDGC",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TIMEINGC": (
                2022,
                "% Time in GC",
                "GC 耗时 (%)",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TIMEINGC",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_BYTESINALLHEAPS": (
                2023,
                "# Bytes in all Heaps",
                "所有堆中的字节数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_BYTESINALLHEAPS",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TOTALCOMMITTED": (
                2024,
                "# Total Committed Bytes",
                "已提交字节总数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TOTALCOMMITTED",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TOTALRESERVED": (
                2025,
                "# Total Reserved Bytes",
                "已保留字节总数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TOTALRESERVED",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TOTALPINNED": (
                2026,
                "# of Pinned Objects",
                "固定对象数目",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TOTALPINNED",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TOTALSINKS": (
                2027,
                "# of Sink Blocks in use",
                "正在使用的同步块数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TOTALSINKS",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TOTALBYTESSINCESTART": (
                2028,
                "Total Bytes Allocated (since start)",
                "自启动以来分配的总字节数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TOTALBYTESSINCESTART",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_TOTALLOHBYTESSINCESTART": (
                2029,
                "Total Bytes Allocated for Large Objects (since start)",
                "自启动以来为大型对象分配的总字节数",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_TOTALLOHBYTESSINCESTART",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GC0PROMOTEDBYTESPERSEC": (
                2030,
                "Gen 0 Promoted Bytes / sec",
                "第 0 代提升的字节数/秒",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GC0PROMOTEDBYTESPERSEC",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_GC1PROMOTEDBYTESPERSEC": (
                2031,
                "Gen 1 Promoted Bytes / sec",
                "第 1 代提升的字节数/秒",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_GC1PROMOTEDBYTESPERSEC",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_FINALPROMOTEDBYTESPERSEC": (
                2032,
                "Promoted Finalization-Memory / sec",
                "因等待终结而提升的字节数/秒",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_FINALPROMOTEDBYTESPERSEC",
            ),
            "IDS_DN_PERF_ITEM_MEMORY_ALLOCATEDBYTESPERSEC": (
                2033,
                "Allocated Bytes / sec",
                "分配的字节数/秒",
                "DOTNET_CATEGORY_MEMORY",
                "DOTNET_INDEX_MEMORY_ALLOCATEDBYTESPERSEC",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_THROWNCOUNT": (
                2034,
                "# of Exceptions Thrown",
                "引发的异常数",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_THROWNCOUNT",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_FILTERSCOUNT": (
                2035,
                "# of Filters Executed",
                "执行的筛选器数",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_FILTERSCOUNT",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_FINALLYCOUNT": (
                2036,
                "# of Finallys Executed",
                "finally 块执行次数",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_FINALLYCOUNT",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_THROWNPERSEC": (
                2037,
                "# of Exceps Thrown / sec",
                "引发的异常数/秒",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_THROWNPERSEC",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_FILTERSPERSEC": (
                2038,
                "# of Filters Executed / sec",
                "筛选次数/秒",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_FILTERSPERSEC",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_FINALLYPERSEC": (
                2039,
                "# of Finallys Executed / sec",
                "finally 块执行次数/秒",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_FINALLYPERSEC",
            ),
            "IDS_DN_PERF_ITEM_EXCEPTIONS_THROWTOCATCHDEPTHPERSEC": (
                2040,
                "Throw To Catch Depth / sec",
                "引发到捕获的堆栈帧数/秒",
                "DOTNET_CATEGORY_EXCEPTIONS",
                "DOTNET_INDEX_EXCEPTIONS_THROWTOCATCHDEPTHPERSEC",
            ),
            "IDS_DN_PERF_ITEM_INTEROP_CCWCOUNT": (
                2041,
                "# of CCWs",
                "CCW 数目",
                "DOTNET_CATEGORY_INTEROP",
                "DOTNET_INDEX_INTEROP_CCWCOUNT",
            ),
            "IDS_DN_PERF_ITEM_INTEROP_STUBCOUNT": (
                2042,
                "# of Stubs",
                "存根数",
                "DOTNET_CATEGORY_INTEROP",
                "DOTNET_INDEX_INTEROP_STUBCOUNT",
            ),
            "IDS_DN_PERF_ITEM_INTEROP_MARSHALCOUNT": (
                2043,
                "# of Marshalling",
                "封送次数",
                "DOTNET_CATEGORY_INTEROP",
                "DOTNET_INDEX_INTEROP_MARSHALCOUNT",
            ),
            "IDS_DN_PERF_ITEM_INTEROP_TLBIMPORTPERSEC": (
                2044,
                "# of TLB imports / sec",
                "TLB 导入次数/秒",
                "DOTNET_CATEGORY_INTEROP",
                "DOTNET_INDEX_INTEROP_TLBIMPORTPERSEC",
            ),
            "IDS_DN_PERF_ITEM_INTEROP_TLBEXPORTPERSEC": (
                2045,
                "# of TLB exports / sec",
                "TLB 导出次数/秒",
                "DOTNET_CATEGORY_INTEROP",
                "DOTNET_INDEX_INTEROP_TLBEXPORTPERSEC",
            ),
        }
        expected_routes = [
            (group_id, index_id, resource_id)
            for resource_id, (_, _, _, group_id, index_id) in expected_resources.items()
        ]
        entries = []

        audit.scan_c_file(str(source_path), entries)

        active_items = {
            entry["english"]
            for entry in entries
            if entry["category"] == "c_listview_group_item"
        }
        actual_routes = re.findall(
            r"DotNetPerfAddListViewGroupItem\(\s*ListViewHandle,\s*"
            r"(DOTNET_CATEGORY_[A-Z0-9_]+),\s*"
            r"(DOTNET_INDEX_[A-Z0-9_]+),\s*"
            r"(IDS_DN_PERF_ITEM_[A-Z0-9_]+)\s*\);",
            source,
        )
        actual_routes = [
            route for route in actual_routes if route[2] in expected_resources
        ]

        self.assertEqual(actual_routes, expected_routes)
        self.assertRegex(
            source,
            r"static\s+VOID\s+DotNetPerfAddListViewGroupItem\(\s*"
            r"_In_\s+HWND\s+ListViewHandle,\s*"
            r"_In_\s+DOTNET_CATEGORY\s+GroupId,\s*"
            r"_In_\s+DOTNET_INDEX\s+Index,\s*"
            r"_In_\s+ULONG\s+NameResourceId\s*\)\s*"
            r"\{\s*PhAddListViewGroupItem\(\s*ListViewHandle,\s*GroupId,\s*Index,\s*"
            r"PhGetString\(PH_AUTO\(PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
            r"NameResourceId,\s*NULL\s*\)\)\),\s*UlongToPtr\(Index\)\s*\);\s*\}",
        )

        for resource_id, (
            numeric_id,
            english_text,
            chinese_text,
            _,
            _,
        ) in expected_resources.items():
            with self.subTest(dotnet_performance_item=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                table_name = "strings" if english_text == "Process ID" else "native_strings"
                other_table = "native_strings" if table_name == "strings" else "strings"
                self.assertEqual(translation_data[table_name].get(english_text), chinese_text)
                self.assertNotIn(english_text, translation_data[other_table])
                self.assertNotIn(english_text, active_items)

        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2089$",
        )
        self.assertEqual(
            workflow.count(
                "--expect-string-count-in 'bin\\Release64\\plugins\\DotNetTools.dll=89'"
            ),
            2,
        )

    def test_dotnet_performance_batch_b_items_use_native_resources(self) -> None:
        audit = load_audit_module()
        source_path = REPO_ROOT / "plugins" / "DotNetTools" / "perfpage.c"
        source = audit.mask_c_comments(source_path.read_text(encoding="utf-8-sig"))
        resource_header = (
            REPO_ROOT / "plugins" / "DotNetTools" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = (
            REPO_ROOT / "plugins" / "DotNetTools" / "DotNetTools.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_resource = (
            REPO_ROOT / "plugins" / "DotNetTools" / "DotNetTools.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        expected_items = [
            ("DOTNET_CATEGORY_JIT", "DOTNET_INDEX_JIT_ILMETHODSJITTED", "IDS_DN_PERF_ITEM_JIT_METHODSJITTED", 2046, "# of Methods Jitted", "JIT 编译方法数"),
            ("DOTNET_CATEGORY_JIT", "DOTNET_INDEX_JIT_ILBYTESJITTED", "IDS_DN_PERF_ITEM_JIT_ILBYTESJITTED", 2047, "# of IL Bytes Jitted", "JIT 编译的 IL 字节数"),
            ("DOTNET_CATEGORY_JIT", "DOTNET_INDEX_JIT_ILTOTALBYTESJITTED", "IDS_DN_PERF_ITEM_JIT_TOTALILBYTESJITTED", 2048, "Total # of IL Bytes Jitted", "JIT 编译的 IL 字节总数"),
            ("DOTNET_CATEGORY_JIT", "DOTNET_INDEX_JIT_FAILURES", "IDS_DN_PERF_ITEM_JIT_FAILURES", 2049, "Jit Failures", "JIT 编译失败数"),
            ("DOTNET_CATEGORY_JIT", "DOTNET_INDEX_JIT_TIME", "IDS_DN_PERF_ITEM_JIT_TIME", 2050, "% Time in Jit", "JIT 编译耗时 (%)"),
            ("DOTNET_CATEGORY_JIT", "DOTNET_INDEX_JIT_ILBYTESJITTEDPERSEC", "IDS_DN_PERF_ITEM_JIT_ILBYTESJITTEDPERSEC", 2051, "IL Bytes Jitted / sec", "JIT 编译的 IL 字节数/秒"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_CURRENTLOADED", "IDS_DN_PERF_ITEM_LOADING_CURRENTCLASSESLOADED", 2052, "Current Classes Loaded", "当前已加载类数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_TOTALLOADED", "IDS_DN_PERF_ITEM_LOADING_TOTALCLASSESLOADED", 2053, "Total Classes Loaded", "已加载类总数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_CURRENTAPPDOMAINS", "IDS_DN_PERF_ITEM_LOADING_CURRENTAPPDOMAINS", 2054, "Current Appdomains", "当前 AppDomain 数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_TOTALAPPDOMAINS", "IDS_DN_PERF_ITEM_LOADING_TOTALAPPDOMAINS", 2055, "Total Appdomains", "AppDomain 总数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_CURRENTASSEMBLIES", "IDS_DN_PERF_ITEM_LOADING_CURRENTASSEMBLIES", 2056, "Current Assemblies", "当前程序集数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_TOTALASSEMBLIES", "IDS_DN_PERF_ITEM_LOADING_TOTALASSEMBLIES", 2057, "Total Assemblies", "程序集总数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_ASSEMBLYSEARCHLENGTH", "IDS_DN_PERF_ITEM_LOADING_ASSEMBLYSEARCHLENGTH", 2058, "Assembly Search Length", "程序集搜索长度"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_TOTALLOADFAILURES", "IDS_DN_PERF_ITEM_LOADING_TOTALLOADFAILURES", 2059, "Total # of Load Failures", "类加载失败总数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_BYTESINLOADERHEAP", "IDS_DN_PERF_ITEM_LOADING_BYTESINLOADERHEAP", 2060, "Bytes in Loader Heap", "加载器堆字节数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_TOTALAPPDOMAINSUNLOADED", "IDS_DN_PERF_ITEM_LOADING_TOTALAPPDOMAINSUNLOADED", 2061, "Total Appdomains Unloaded", "已卸载 AppDomain 总数"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_CLASSESLOADEDRATE", "IDS_DN_PERF_ITEM_LOADING_CLASSESLOADEDPERSEC", 2062, "Rate of Classes Loaded", "类加载数/秒"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_APPDOMAINSRATE", "IDS_DN_PERF_ITEM_LOADING_APPDOMAINSLOADEDPERSEC", 2063, "Rate of Appdomains", "AppDomain 加载数/秒"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_ASSEMBLIESRATE", "IDS_DN_PERF_ITEM_LOADING_ASSEMBLIESLOADEDPERSEC", 2064, "Rate of Assemblies", "程序集加载数/秒"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_LOADFAILURESRATE", "IDS_DN_PERF_ITEM_LOADING_LOADFAILURESPERSEC", 2065, "Rate of Load Failures", "类加载失败数/秒"),
            ("DOTNET_CATEGORY_LOADING", "DOTNET_INDEX_LOADING_APPDOMAINSUNLOADEDRATE", "IDS_DN_PERF_ITEM_LOADING_APPDOMAINSUNLOADEDPERSEC", 2066, "Rate of Appdomains Unloaded", "AppDomain 卸载数/秒"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_TOTALLOCKS", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_TOTALCONTENTIONS", 2067, "Total # of Contentions", "锁争用总次数"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_TOTALQUEUELENGTH", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_CURRENTQUEUELENGTH", 2068, "Current Queue Length", "当前锁等待线程数"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_QUEUELENGTHPEAK", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_QUEUELENGTHPEAK", 2069, "Queue Length Peak", "队列长度峰值"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_CURRENTLOGICAL", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_CURRENTLOGICALTHREADS", 2070, "# of Current Logical Threads", "当前逻辑线程数"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_CURRENTPHYSICAL", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_CURRENTPHYSICALTHREADS", 2071, "# of Current Physical Threads", "当前物理线程数"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_CURRENTRECOGNIZED", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_CURRENTRECOGNIZEDTHREADS", 2072, "# of Current Recognized Threads", "当前已识别线程数"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_TOTALRECOGNIZED", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_TOTALRECOGNIZEDTHREADS", 2073, "# of Total Recognized Threads", "已识别线程总数"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_CONTENTIONRATE", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_CONTENTIONSPERSEC", 2074, "Contention Rate / sec", "锁争用次数/秒"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_QUEUELENGTHRATE", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_QUEUELENGTHPERSEC", 2075, "Queue Length / sec", "锁等待线程数/秒"),
            ("DOTNET_CATEGORY_LOCKSANDTHREADS", "DOTNET_INDEX_LOCKSANDTHREADS_RECOGNIZEDTHREADSRATE", "IDS_DN_PERF_ITEM_LOCKSANDTHREADS_RECOGNIZEDTHREADSPERSEC", 2076, "Rate of Recognized Threads / sec", "已识别线程数/秒"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_TOTALREMOTECALLS", "IDS_DN_PERF_ITEM_REMOTING_TOTALREMOTECALLS", 2077, "Total Remote Calls", "远程调用总数"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_CHANNELS", "IDS_DN_PERF_ITEM_REMOTING_CHANNELS", 2078, "Channels", "通道数"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_CONTEXTPROXIES", "IDS_DN_PERF_ITEM_REMOTING_CONTEXTPROXIES", 2079, "Context Proxies", "上下文代理数"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_CONTEXTCLASSESLOADED", "IDS_DN_PERF_ITEM_REMOTING_CONTEXTBOUNDCLASSESLOADED", 2080, "Context-Bound Classes Loaded", "已加载的上下文绑定类数"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_CONTEXTS", "IDS_DN_PERF_ITEM_REMOTING_CONTEXTS", 2081, "Contexts", "上下文数"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_CONTEXTSALLOCATED", "IDS_DN_PERF_ITEM_REMOTING_CONTEXTBOUNDOBJECTSALLOCATED", 2082, "# of context bound objects allocated", "已分配的上下文绑定对象数"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_REMOTECALLSRATE", "IDS_DN_PERF_ITEM_REMOTING_REMOTECALLSPERSEC", 2083, "Remote Calls / sec", "远程调用数/秒"),
            ("DOTNET_CATEGORY_REMOTING", "DOTNET_INDEX_REMOTING_OBJALLOCATIONRATE", "IDS_DN_PERF_ITEM_REMOTING_CONTEXTBOUNDOBJECTSALLOCATIONSPERSEC", 2084, "Context-Bound Objects Alloc / sec", "上下文绑定对象分配数/秒"),
            ("DOTNET_CATEGORY_SECURITY", "DOTNET_INDEX_SECURITY_TOTALRUNTIMECHECKS", "IDS_DN_PERF_ITEM_SECURITY_TOTALRUNTIMECHECKS", 2085, "Total Runtime Checks", "运行时安全检查总数"),
            ("DOTNET_CATEGORY_SECURITY", "DOTNET_INDEX_SECURITY_LINKTIMECHECKS", "IDS_DN_PERF_ITEM_SECURITY_LINKTIMECHECKS", 2086, "# Link Time Checks", "链接时安全检查数"),
            ("DOTNET_CATEGORY_SECURITY", "DOTNET_INDEX_SECURITY_TIMEINRTCHECKS", "IDS_DN_PERF_ITEM_SECURITY_TIMEINRUNTIMECHECKS", 2087, "% Time in RT checks", "运行时安全检查耗时 (%)"),
            ("DOTNET_CATEGORY_SECURITY", "DOTNET_INDEX_SECURITY_STACKWALKDEPTH", "IDS_DN_PERF_ITEM_SECURITY_STACKWALKDEPTH", 2088, "Stack Walk Depth", "堆栈遍历深度"),
        ]
        entries = []

        audit.scan_c_file(str(source_path), entries)

        active_items = {
            entry["english"]
            for entry in entries
            if entry["category"] == "c_listview_group_item"
        }
        expected_routes = [
            (group_id, index_id, resource_id)
            for group_id, index_id, resource_id, _, _, _ in expected_items
        ]
        resource_ids = {item[2] for item in expected_items}
        actual_routes = [
            route
            for route in re.findall(
                r"DotNetPerfAddListViewGroupItem\(\s*ListViewHandle,\s*"
                r"(DOTNET_CATEGORY_[A-Z0-9_]+),\s*"
                r"(DOTNET_INDEX_[A-Z0-9_]+),\s*"
                r"(IDS_DN_PERF_ITEM_[A-Z0-9_]+)\s*\);",
                source,
            )
            if route[2] in resource_ids
        ]

        self.assertEqual(len(expected_items), 43)
        self.assertEqual(
            [numeric_id for _, _, _, numeric_id, _, _ in expected_items],
            list(range(2046, 2089)),
        )
        self.assertEqual(actual_routes, expected_routes)

        for (
            group_id,
            index_id,
            resource_id,
            numeric_id,
            english_text,
            chinese_text,
        ) in expected_items:
            with self.subTest(dotnet_performance_item=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese_text)}"$',
                )
                self.assertEqual(
                    translation_data["native_strings"].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data["strings"])
                self.assertNotIn(english_text, active_items)

        self.assertRegex(
            resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2089$",
        )
        self.assertNotRegex(
            resource_header,
            r"(?m)^#define\s+IDS_DN_PERF_ITEM_LOCKSANDTHREADS_TOTALQUEUELENGTH\s+",
        )
        self.assertNotRegex(
            resource_header,
            r"(?m)^#define\s+IDS_DN_PERF_ITEM_REMOTING_CONTEXTSALLOCATED\s+",
        )
        self.assertEqual(
            workflow.count(
                "--expect-string-count-in 'bin\\Release64\\plugins\\DotNetTools.dll=89'"
            ),
            2,
        )

    def test_network_tools_window_text_uses_native_resources(self) -> None:
        audit = load_audit_module()
        source_paths = {
            name: REPO_ROOT / "plugins" / "NetworkTools" / name
            for name in ("options.c", "ping.c", "tracert.c", "whois.c")
        }
        sources = {
            name: audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for name, path in source_paths.items()
        }
        resource_header = (
            REPO_ROOT / "plugins" / "NetworkTools" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = (
            REPO_ROOT / "plugins" / "NetworkTools" / "NetworkTools.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_resource = (
            REPO_ROOT / "plugins" / "NetworkTools" / "NetworkTools.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8-sig")
        expected_resources = {
            "IDS_NT_PASTE_LICENSE_KEY_HERE": (12002, "Paste the license key here:", "在此粘贴许可证密钥："),
            "IDS_NT_PASTE_ACCOUNT_ID_HERE": (12003, "Paste the account id here:", "在此粘贴账户 ID："),
            "IDS_NT_PING_TITLE_FORMAT": (12004, "Ping %s", "Ping %s"),
            "IDS_NT_PING_STATUS_FORMAT": (12005, "Pinging %s with %lu bytes of data...", "正在 Ping %s，使用 %lu 字节数据..."),
            "IDS_NT_PING_AVERAGE_FORMAT": (12006, "Average: %.2f ms", "平均值：%.2f ms"),
            "IDS_NT_PING_MINIMUM_FORMAT": (12007, "Minimum: %.2f ms", "最小值：%.2f ms"),
            "IDS_NT_PING_MAXIMUM_FORMAT": (12008, "Maximum: %.2f ms", "最大值：%.2f ms"),
            "IDS_NT_PINGS_SENT_FORMAT": (12009, "Pings sent: %lu", "已发送 Ping：%lu"),
            "IDS_NT_PINGS_LOST_FORMAT": (12010, "Pings lost: %lu (%.0f%%)", "已丢失 Ping：%lu (%.0f%%)"),
            "IDS_NT_PING_DEVIATION_FORMAT": (12011, "Deviation: %.2f ms", "偏差：%.2f ms"),
            "IDS_NT_BAD_REPLIES_FORMAT": (12012, "Bad replies: %lu", "错误回复：%lu"),
            "IDS_NT_ANON_REPLIES_FORMAT": (12013, "Anon replies: %lu", "匿名回复：%lu"),
            "IDS_NT_TRACERT_TITLE_FORMAT": (12014, "Tracing %s...", "正在跟踪 %s..."),
            "IDS_NT_TRACERT_ROUTE_FORMAT": (12015, "Tracing route to %s with %lu bytes of data...", "正在跟踪到 %s 的路由，使用 %lu 字节数据..."),
            "IDS_NT_TRACERT_TITLE_RESULT_FORMAT": (12016, "Tracing %s... %s", "正在跟踪 %s... %s"),
            "IDS_NT_TRACERT_ROUTE_RESULT_FORMAT": (12017, "Tracing route to %s with %lu bytes of data... %s.", "正在跟踪到 %s 的路由，使用 %lu 字节数据... %s。"),
            "IDS_NT_TRACERT_RESULT_ERROR": (12018, "error", "错误"),
            "IDS_NT_TRACERT_RESULT_CONTINUOUS": (12019, "continuous ping active", "连续 Ping 已启用"),
            "IDS_NT_TRACERT_RESULT_COMPLETE": (12020, "complete", "完成"),
            "IDS_NT_WHOIS_TITLE_FORMAT": (12021, "Whois %s...", "WHOIS %s..."),
        }
        expected_calls = {
            "IDS_NT_PASTE_LICENSE_KEY_HERE": ("options.c", 1),
            "IDS_NT_PASTE_ACCOUNT_ID_HERE": ("options.c", 1),
            "IDS_NT_PING_TITLE_FORMAT": ("ping.c", 1),
            "IDS_NT_PING_STATUS_FORMAT": ("ping.c", 1),
            "IDS_NT_PING_AVERAGE_FORMAT": ("ping.c", 1),
            "IDS_NT_PING_MINIMUM_FORMAT": ("ping.c", 1),
            "IDS_NT_PING_MAXIMUM_FORMAT": ("ping.c", 1),
            "IDS_NT_PINGS_SENT_FORMAT": ("ping.c", 1),
            "IDS_NT_PINGS_LOST_FORMAT": ("ping.c", 1),
            "IDS_NT_PING_DEVIATION_FORMAT": ("ping.c", 1),
            "IDS_NT_BAD_REPLIES_FORMAT": ("ping.c", 1),
            "IDS_NT_ANON_REPLIES_FORMAT": ("ping.c", 1),
            "IDS_NT_TRACERT_TITLE_FORMAT": ("tracert.c", 2),
            "IDS_NT_TRACERT_ROUTE_FORMAT": ("tracert.c", 2),
            "IDS_NT_TRACERT_TITLE_RESULT_FORMAT": ("tracert.c", 1),
            "IDS_NT_TRACERT_ROUTE_RESULT_FORMAT": ("tracert.c", 1),
            "IDS_NT_TRACERT_RESULT_ERROR": ("tracert.c", 1),
            "IDS_NT_TRACERT_RESULT_CONTINUOUS": ("tracert.c", 1),
            "IDS_NT_TRACERT_RESULT_COMPLETE": ("tracert.c", 1),
            "IDS_NT_WHOIS_TITLE_FORMAT": ("whois.c", 1),
        }
        all_source = "\n".join(sources.values())
        ui_string_expression = (
            r"PhGetString\(PH_AUTO\(PhLoadUiString\("
            r"PluginInstance->DllBase,\s*{resource_id},\s*NULL\)\)\)"
        )
        for resource_id, (numeric_id, english_text, chinese_text) in expected_resources.items():
            with self.subTest(network_tools_window_text=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{re.escape(resource_id)}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{re.escape(resource_id)}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{re.escape(resource_id)}\s+"{re.escape(chinese_text)}"$',
                )
                self.assertEqual(
                    translation_data["native_strings"].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data["strings"])
                self.assertNotIn(f'L"{english_text}"', all_source)
                source_name, expected_call_count = expected_calls[resource_id]
                self.assertEqual(
                    len(
                        re.findall(
                            rf"PhLoadUiString\(PluginInstance->DllBase,\s*{re.escape(resource_id)},",
                            sources[source_name],
                        )
                    ),
                    expected_call_count,
                )
                self.assertEqual(
                    re.findall(r"%(?:\.\d+)?(?:l)?[suf%]", english_text),
                    re.findall(r"%(?:\.\d+)?(?:l)?[suf%]", chinese_text),
                )

        options_branches = re.search(
            r"if\s*\(id\s*==\s*IDC_KEYTEXT\)\s*\{(?P<license>.*?)\}"
            r"\s*else\s*\{(?P<account>.*?)\}",
            sources["options.c"],
            re.DOTALL,
        )
        self.assertIsNotNone(options_branches)
        for branch_name, resource_id in (
            ("license", "IDS_NT_PASTE_LICENSE_KEY_HERE"),
            ("account", "IDS_NT_PASTE_ACCOUNT_ID_HERE"),
        ):
            with self.subTest(network_tools_option_branch=branch_name):
                self.assertRegex(
                    options_branches.group(branch_name),
                    r"PhSetDialogItemText\(\s*WindowHandle,\s*IDC_KEYTEXT_L,\s*"
                    + ui_string_expression.format(resource_id=resource_id)
                    + r"\s*\);",
                )

        ping_targets = {
            "hwndDlg": "IDS_NT_PING_TITLE_FORMAT",
            "context->StatusHandle": "IDS_NT_PING_STATUS_FORMAT",
            "IDC_ICMP_AVG": "IDS_NT_PING_AVERAGE_FORMAT",
            "IDC_ICMP_MIN": "IDS_NT_PING_MINIMUM_FORMAT",
            "IDC_ICMP_MAX": "IDS_NT_PING_MAXIMUM_FORMAT",
            "IDC_PINGS_SENT": "IDS_NT_PINGS_SENT_FORMAT",
            "IDC_PINGS_LOST": "IDS_NT_PINGS_LOST_FORMAT",
            "IDC_ICMP_STDEV": "IDS_NT_PING_DEVIATION_FORMAT",
            "IDC_BAD_HASH": "IDS_NT_BAD_REPLIES_FORMAT",
            "IDC_ANON_ADDR": "IDS_NT_ANON_REPLIES_FORMAT",
        }
        for target, resource_id in ping_targets.items():
            with self.subTest(network_tools_ping_target=target):
                if target.startswith("IDC_"):
                    call_prefix = (
                        rf"PhSetDialogItemText\(\s*hwndDlg,\s*{target},\s*"
                        r"PhaFormatString\(\s*"
                    )
                else:
                    call_prefix = (
                        rf"PhSetWindowText\(\s*{re.escape(target)},\s*"
                        r"PhaFormatString\(\s*"
                    )
                self.assertRegex(
                    sources["ping.c"],
                    call_prefix
                    + ui_string_expression.format(resource_id=resource_id)
                    + r"\s*,",
                )

        ping_unsigned_counters = {
            "IDC_PINGS_SENT": ("IDS_NT_PINGS_SENT_FORMAT", "PingSentCount"),
            "IDC_PINGS_LOST": ("IDS_NT_PINGS_LOST_FORMAT", "PingLossCount"),
            "IDC_BAD_HASH": ("IDS_NT_BAD_REPLIES_FORMAT", "HashFailCount"),
            "IDC_ANON_ADDR": ("IDS_NT_ANON_REPLIES_FORMAT", "UnknownAddrCount"),
        }
        for target, (resource_id, field_name) in ping_unsigned_counters.items():
            with self.subTest(network_tools_ping_unsigned_counter=target):
                self.assertRegex(
                    sources["ping.c"],
                    rf"PhSetDialogItemText\(\s*hwndDlg,\s*{target},\s*"
                    r"PhaFormatString\(\s*"
                    + ui_string_expression.format(resource_id=resource_id)
                    + rf"\s*,\s*\(ULONG\)context->{field_name}\b",
                )

        tracing_result_selection = re.search(
            r"if\s*\(failed\)\s*\{\s*"
            r"tracingResult\s*=\s*PhLoadUiString\(PluginInstance->DllBase,\s*"
            r"IDS_NT_TRACERT_RESULT_ERROR,\s*NULL\);\s*\}\s*"
            r"else if\s*\(context->PingContinuous\)\s*\{\s*"
            r"tracingResult\s*=\s*PhLoadUiString\(PluginInstance->DllBase,\s*"
            r"IDS_NT_TRACERT_RESULT_CONTINUOUS,\s*NULL\);\s*\}\s*"
            r"else\s*\{\s*"
            r"tracingResult\s*=\s*PhLoadUiString\(PluginInstance->DllBase,\s*"
            r"IDS_NT_TRACERT_RESULT_COMPLETE,\s*NULL\);\s*\}",
            sources["tracert.c"],
            re.DOTALL,
        )
        self.assertIsNotNone(tracing_result_selection)

        tracert_formatted_targets = (
            (r"hwndDlg", "IDS_NT_TRACERT_TITLE_FORMAT", 1),
            (r"context->WindowHandle", "IDS_NT_TRACERT_TITLE_FORMAT", 1),
            (r"context->WindowHandle", "IDS_NT_TRACERT_TITLE_RESULT_FORMAT", 1),
            (r"GetDlgItem\(hwndDlg,\s*IDC_STATUS\)", "IDS_NT_TRACERT_ROUTE_FORMAT", 2),
            (r"GetDlgItem\(hwndDlg,\s*IDC_STATUS\)", "IDS_NT_TRACERT_ROUTE_RESULT_FORMAT", 1),
        )
        for target_pattern, resource_id, expected_count in tracert_formatted_targets:
            with self.subTest(network_tools_tracert_target=resource_id):
                self.assertEqual(
                    len(
                        re.findall(
                            rf"PhSetWindowText\(\s*{target_pattern},\s*"
                            r"PhaFormatString\(\s*"
                            + ui_string_expression.format(resource_id=resource_id)
                            + r"\s*,",
                            sources["tracert.c"],
                        )
                    ),
                    expected_count,
                )

        tracing_finish_body = sources["tracert.c"].split(
            "case NTM_RECEIVEDFINISH:", 1
        )[1].split("case WM_TRACERT_HOSTNAME:", 1)[0]
        title_update = tracing_finish_body.index(
            "PhSetWindowText(context->WindowHandle"
        )
        status_update = tracing_finish_body.index(
            "PhSetWindowText(GetDlgItem(hwndDlg, IDC_STATUS)"
        )
        result_release = tracing_finish_body.index(
            "PhDereferenceObject(tracingResult)"
        )
        tree_update = tracing_finish_body.index(
            "TreeNew_NodesStructured(context->TreeNewHandle)"
        )
        self.assertEqual(tracing_finish_body.count("PhGetString(tracingResult)"), 2)
        self.assertEqual(tracing_finish_body.count("PhDereferenceObject(tracingResult)"), 1)
        self.assertLess(title_update, status_update)
        self.assertLess(status_update, result_release)
        self.assertLess(result_release, tree_update)

        self.assertRegex(resource_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12022$")
        migrated_resource_ids = "|".join(
            re.escape(resource_id) for resource_id in expected_resources
        )
        self.assertEqual(
            len(
                re.findall(
                    rf"PhLoadUiString\(PluginInstance->DllBase,\s*(?:{migrated_resource_ids}),",
                    all_source,
                )
            ),
            22,
        )
        self.assertEqual(
            len(re.findall(r"IDS_NT_TRACERT_RESULT_(?:ERROR|CONTINUOUS|COMPLETE)", sources["tracert.c"])),
            3,
        )
        self.assertEqual(
            len(
                re.findall(
                    r"--expect-string-count-in\s+'bin\\Release64\\plugins\\NetworkTools\.dll=22'",
                    workflow,
                )
            ),
            2,
        )

    def test_hardware_device_connection_text_uses_native_resources(self) -> None:
        audit = load_audit_module()
        source_names = (
            "diskoptions.c",
            "gpuoptions.c",
            "netoptions.c",
            "poweroptions.c",
            "netdetails.c",
            "netgraph.c",
        )
        sources = {
            name: audit.mask_c_comments(
                (REPO_ROOT / "plugins" / "HardwareDevices" / name).read_text(
                    encoding="utf-8-sig"
                )
            )
            for name in source_names
        }
        resource_header = (
            REPO_ROOT / "plugins" / "HardwareDevices" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        english_resource = (
            REPO_ROOT / "plugins" / "HardwareDevices" / "HardwareDevices.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_resource = (
            REPO_ROOT / "plugins" / "HardwareDevices" / "HardwareDevices.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translation_data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8-sig")
        expected_resources = {
            "IDS_HD_CONNECTED": (12001, "Connected", "已连接"),
            "IDS_HD_DISCONNECTED": (12002, "Disconnected", "已断开连接"),
            "IDS_HD_ADAPTER": (12003, "Adapter", "适配器"),
            "IDS_HD_UNICAST": (12004, "Unicast", "单播"),
            "IDS_HD_BROADCAST": (12005, "Broadcast", "广播"),
            "IDS_HD_MULTICAST": (12006, "Multicast", "多播"),
            "IDS_HD_ERRORS": (12007, "Errors", "错误"),
            "IDS_HD_UNKNOWN_NETWORK_ADAPTER": (
                12008,
                "Unknown network adapter",
                "未知网络适配器",
            ),
        }
        native_owned = {
            "Connected",
            "Disconnected",
            "Unicast",
            "Broadcast",
            "Multicast",
            "Errors",
            "Unknown network adapter",
        }

        for resource_id, (numeric_id, english_text, chinese_text) in expected_resources.items():
            with self.subTest(hardware_device_resource=resource_id):
                self.assertRegex(
                    resource_header,
                    rf"(?m)^#define\s+{re.escape(resource_id)}\s+{numeric_id}$",
                )
                self.assertRegex(
                    english_resource,
                    rf'(?m)^\s*{re.escape(resource_id)}\s+"{re.escape(english_text)}"$',
                )
                self.assertRegex(
                    chinese_resource,
                    rf'(?m)^\s*{re.escape(resource_id)}\s+"{re.escape(chinese_text)}"$',
                )
                table_name = "native_strings" if english_text in native_owned else "strings"
                other_table = "strings" if table_name == "native_strings" else "native_strings"
                self.assertEqual(
                    translation_data[table_name].get(english_text),
                    chinese_text,
                )
                self.assertNotIn(english_text, translation_data[other_table])

        ui_string_expression = (
            r"PhGetString\(PH_AUTO\(PhLoadUiString\("
            r"PluginInstance->DllBase,\s*{resource_id},\s*NULL\)\)\)"
        )
        cached_ui_string_expression = (
            r"HardwareDevicesGetUiString\({resource_id}\)"
        )
        for source_name in (
            "diskoptions.c",
            "gpuoptions.c",
            "netoptions.c",
            "poweroptions.c",
        ):
            with self.subTest(hardware_device_groups=source_name):
                self.assertRegex(
                    sources[source_name],
                    r"PhAddListViewGroup\(\s*[^,]+,\s*0,\s*"
                    + ui_string_expression.format(resource_id="IDS_HD_CONNECTED")
                    + r"\s*\);",
                )
                self.assertRegex(
                    sources[source_name],
                    r"PhAddListViewGroup\(\s*[^,]+,\s*1,\s*"
                    + ui_string_expression.format(resource_id="IDS_HD_DISCONNECTED")
                    + r"\s*\);",
                )
                self.assertNotIn('L"Connected"', sources[source_name])
                self.assertNotIn('L"Disconnected"', sources[source_name])

        netdetails_groups = {
            "NETADAPTER_DETAILS_CATEGORY_ADAPTER": "IDS_HD_ADAPTER",
            "NETADAPTER_DETAILS_CATEGORY_UNICAST": "IDS_HD_UNICAST",
            "NETADAPTER_DETAILS_CATEGORY_BROADCAST": "IDS_HD_BROADCAST",
            "NETADAPTER_DETAILS_CATEGORY_MULTICAST": "IDS_HD_MULTICAST",
            "NETADAPTER_DETAILS_CATEGORY_ERRORS": "IDS_HD_ERRORS",
        }
        for category, resource_id in netdetails_groups.items():
            with self.subTest(hardware_device_details_group=category):
                self.assertRegex(
                    sources["netdetails.c"],
                    rf"PhAddListViewGroup\(\s*ListViewHandle,\s*{category},\s*"
                    + ui_string_expression.format(resource_id=resource_id)
                    + r"\s*\);",
                )

        for literal in (
            "Connected",
            "Disconnected",
            "Adapter",
            "Unicast",
            "Broadcast",
            "Multicast",
            "Errors",
        ):
            with self.subTest(hardware_device_removed_literal=literal):
                self.assertNotIn(f'L"{literal}"', "\n".join(sources.values()))

        self.assertRegex(
            sources["netdetails.c"],
            r"PhSetListViewSubItem\(\s*Context->ListViewHandle,\s*"
            r"NETADAPTER_DETAILS_INDEX_STATE,\s*1,\s*"
            r"mediaState\s*==\s*MediaConnectStateConnected\s*\?\s*"
            + cached_ui_string_expression.format(resource_id="IDS_HD_CONNECTED")
            + r"\s*:\s*"
            + cached_ui_string_expression.format(resource_id="IDS_HD_DISCONNECTED")
            + r"\s*\);",
        )
        self.assertRegex(
            sources["netdetails.c"],
            r"PhSetWindowText\(\s*WindowHandle,\s*PhGetStringOrDefault\(\s*"
            r"context->AdapterName,\s*"
            + ui_string_expression.format(resource_id="IDS_HD_UNKNOWN_NETWORK_ADAPTER")
            + r"\s*\)\s*\);",
        )
        self.assertNotIn('L"Unknown network adapter"', sources["netdetails.c"])
        self.assertEqual(sources["netoptions.c"].count('L"Unknown network adapter"'), 1)

        network_panel = sources["netgraph.c"].split(
            "VOID NetworkDeviceUpdatePanel(", 1
        )[1].split("INT_PTR CALLBACK NetworkDevicePanelDialogProc(", 1)[0]
        state_condition = network_panel.index(
            "if (mediaState == MediaConnectStateConnected)"
        )
        disconnected_speed = network_panel.index(
            "PhSetWindowText(Context->NetAdapterPanelSpeedLabel, "
            "HardwareDevicesGetUiString(IDS_HD_NOT_AVAILABLE))",
            state_condition,
        )
        outer_else = network_panel.rindex(
            "\n     else\n     {", state_condition, disconnected_speed
        )
        next_panel_section = network_panel.index(
            "PhInitFormatSize(&format[0], "
            "Context->AdapterEntry->CurrentNetworkReceive",
            disconnected_speed,
        )
        connected_branch = network_panel[state_condition:outer_else]
        disconnected_branch = network_panel[outer_else:next_panel_section]
        panel_state_call = (
            r"PhSetWindowText\(\s*Context->NetAdapterPanelStateLabel,\s*"
            + cached_ui_string_expression.format(resource_id="{resource_id}")
            + r"\s*\);"
        )
        self.assertRegex(
            connected_branch,
            panel_state_call.format(resource_id="IDS_HD_CONNECTED"),
        )
        self.assertNotRegex(
            connected_branch,
            panel_state_call.format(resource_id="IDS_HD_DISCONNECTED"),
        )
        self.assertRegex(
            disconnected_branch,
            panel_state_call.format(resource_id="IDS_HD_DISCONNECTED"),
        )
        self.assertNotRegex(
            disconnected_branch,
            panel_state_call.format(resource_id="IDS_HD_CONNECTED"),
        )
        self.assertNotIn('L"Connected"', sources["netgraph.c"])
        self.assertNotIn('L"Disconnected"', sources["netgraph.c"])

        expected_load_counts = {
            "IDS_HD_CONNECTED": 4,
            "IDS_HD_DISCONNECTED": 4,
            "IDS_HD_ADAPTER": 1,
            "IDS_HD_UNICAST": 1,
            "IDS_HD_BROADCAST": 1,
            "IDS_HD_MULTICAST": 1,
            "IDS_HD_ERRORS": 1,
            "IDS_HD_UNKNOWN_NETWORK_ADAPTER": 1,
        }
        all_source = "\n".join(sources.values())
        for resource_id, expected_count in expected_load_counts.items():
            with self.subTest(hardware_device_load_count=resource_id):
                self.assertEqual(
                    len(
                        re.findall(
                            rf"PhLoadUiString\(PluginInstance->DllBase,\s*{resource_id},",
                            all_source,
                        )
                    ),
                    expected_count,
                )

        self.assertRegex(resource_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12096$")
        self.assertEqual(len(stringtable_ids(english_resource)), 96)
        self.assertEqual(len(stringtable_ids(chinese_resource)), 96)
        self.assertEqual(
            len(
                re.findall(
                    r"--expect-string-count-in\s+'bin\\Release64\\plugins\\HardwareDevices\.dll=96'",
                    workflow,
                )
            ),
            2,
        )

    def test_updater_launch_installer_owns_an_auto_pool(self) -> None:
        source = (
            REPO_ROOT / "plugins" / "Updater" / "toastmain.c"
        ).read_text(encoding="utf-8-sig")
        launch_body = source.split("VOID UpdaterLaunchInstaller", 1)[1].split(
            "NTSTATUS NTAPI UpdaterToastInstallThread", 1
        )[0]

        initialize = launch_body.index("PhInitializeAutoPool")
        execute = launch_body.index("UpdateShellExecute")
        cleanup = launch_body.index("PhDeleteAutoPool")

        self.assertLess(initialize, execute)
        self.assertLess(execute, cleanup)

    def test_final_main_and_phlib_errors_use_native_resources(self) -> None:
        audit = load_audit_module()
        paths = (
            REPO_ROOT / "SystemInformer" / "actions.c",
            REPO_ROOT / "SystemInformer" / "appsup.c",
            REPO_ROOT / "SystemInformer" / "main.c",
            REPO_ROOT / "phlib" / "guisup.c",
            REPO_ROOT / "phlib" / "mapldr.c",
            REPO_ROOT / "phlib" / "util.c",
        )
        source = "\n".join(
            audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in paths
        )
        literals = (
            "Unable to %s %s (PID %lu)",
            "Unable to %s %s",
            'Unable to %s handle \\"%s\\" (%s)%s',
            "Unable to %s handle %s%s",
        )

        for literal in literals:
            with self.subTest(literal=literal):
                self.assertNotIn(f'L"{literal}"', source)

        expected_ids = {
            "IDS_PH_ERROR_WITH_DETAILS": 1,
            "IDS_PH_COMMAND_LINE_OPTIONS": 1,
            "IDS_PH_COMMAND_LINE_OPTIONS_CONTENT": 1,
            "IDS_PH_UNABLE_INITIALIZE_DESKTOP_POLICY": 1,
            "IDS_PH_UNABLE_LOAD_SETTINGS": 1,
            "IDS_PH_UNABLE_APPLY_PROCESS_ACTION_PID": 1,
            "IDS_PH_UNABLE_APPLY_PROCESS_ACTION": 1,
            "IDS_PH_UNABLE_APPLY_NAMED_HANDLE_ACTION": 1,
            "IDS_PH_UNABLE_APPLY_HANDLE_ACTION": 1,
            "IDS_PH_UNABLE_LOAD_PLUGIN": 1,
            "IDS_PH_PLUGIN_IMPORT_BY_ORDINAL": 1,
            "IDS_PH_PLUGIN_IMPORT_BY_NAME": 1,
            "IDS_PH_LOCATION_NOT_FOUND": 1,
            "IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT": 1,
            "IDS_PH_ACTION_TERMINATE": 3,
            "IDS_PH_ACTION_SUSPEND": 3,
            "IDS_PH_ACTION_RESUME": 3,
            "IDS_PH_ACTION_FREEZE": 1,
            "IDS_PH_ACTION_THAW": 1,
            "IDS_PH_ACTION_RESTART": 1,
            "IDS_PH_ACTION_DEBUG": 1,
            "IDS_PH_ACTION_REDUCE_WORKING_SET": 1,
            "IDS_PH_ACTION_EMPTY_WORKING_SET": 1,
            "IDS_PH_ACTION_SET_BACKGROUND_ACTIVITY_MODERATION": 1,
            "IDS_PH_ACTION_SET_VIRTUALIZATION": 1,
            "IDS_PH_ACTION_SET_CRITICAL_STATUS": 1,
            "IDS_PH_ACTION_SET_ECO_MODE": 1,
            "IDS_PH_ACTION_CREATE_EXECUTION_REQUIRED": 1,
            "IDS_PH_ACTION_DETACH_DEBUGGER": 1,
            "IDS_PH_ACTION_LOAD_DLL": 1,
            "IDS_PH_ACTION_SET_IO_PRIORITY": 2,
            "IDS_PH_ACTION_SET_PAGE_PRIORITY": 1,
            "IDS_PH_ACTION_SET_PRIORITY_CLASS": 2,
            "IDS_PH_ACTION_CHANGE_BOOST_PRIORITY": 1,
            "IDS_PH_ACTION_SET_BOOST_PRIORITY": 1,
            "IDS_PH_ACTION_FLUSH_PROCESS_HEAPS": 1,
            "IDS_PH_ACTION_CLOSE_HANDLE": 2,
            "IDS_PH_ACTION_SET_HANDLE_ATTRIBUTES": 1,
        }

        for resource_id, expected_count in expected_ids.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(
                    len(re.findall(rf"\b{re.escape(resource_id)}\b", source)),
                    expected_count,
                )

        shared_header = REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
        self.assertTrue(shared_header.exists())
        shared_definitions = shared_header.read_text(encoding="utf-8-sig")
        for resource_id in (
            "IDS_PH_UNABLE_LOAD_PLUGIN",
            "IDS_PH_PLUGIN_IMPORT_BY_ORDINAL",
            "IDS_PH_PLUGIN_IMPORT_BY_NAME",
            "IDS_PH_LOCATION_NOT_FOUND",
            "IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT",
        ):
            with self.subTest(shared_resource_id=resource_id):
                self.assertRegex(
                    shared_definitions,
                    rf"(?m)^#define\s+{re.escape(resource_id)}\s+\d+$",
                )

        main_header = (
            REPO_ROOT / "SystemInformer" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("#include <phappresourceid.h>", main_header)

        main_source = (
            REPO_ROOT / "SystemInformer" / "main.c"
        ).read_text(encoding="utf-8-sig")
        startup_parameters = main_source[
            main_source.index("VOID PhpProcessStartupParameters("):
            main_source.index("VOID PhpEnablePrivileges(")
        ]
        app_settings = main_source[
            main_source.index("VOID PhInitializeAppSettings("):
            main_source.index("BOOLEAN NTAPI PhpCommandLineOptionCallback(")
        ]
        win_main = main_source[
            main_source.index("INT WINAPI wWinMain("):
            main_source.index("VOID PhRegisterDialog(")
        ]
        self.assertNotIn("PhGetApplicationUiString", startup_parameters)
        self.assertNotIn("PhLoadUiString", startup_parameters)
        self.assertNotIn("PhShowInformation2", startup_parameters)
        self.assertNotIn("PhGetApplicationUiString", app_settings)
        self.assertIn("PhStartupParameters.Help = TRUE;", startup_parameters)
        self.assertRegex(
            app_settings,
            r"PhLoadUiString\s*\([^;]+\bIDS_PH_UNABLE_LOAD_SETTINGS\b[^;]+NULL\s*\)",
        )
        self.assertLess(
            app_settings.index("PhSetApplicationUiLanguage("),
            app_settings.index("IDS_PH_UNABLE_LOAD_SETTINGS"),
        )
        help_safe_error_guard = (
            "if (!PhStartupParameters.NoSettings && !PhStartupParameters.Help)"
        )
        self.assertIn(help_safe_error_guard, app_settings)
        self.assertLess(
            app_settings.index(help_safe_error_guard),
            app_settings.index("PhResetSettingsFile("),
        )
        self.assertLess(
            win_main.index("PhInitializeAppSettings();"),
            win_main.index("PhpInitializeApplicationUiStrings()"),
        )
        self.assertLess(
            win_main.index("PhpInitializeApplicationUiStrings()"),
            win_main.index("if (PhStartupParameters.Help)"),
        )
        help_branch = win_main[win_main.index("if (PhStartupParameters.Help)"):]
        self.assertIn(
            "PhGetApplicationUiString(IDS_PH_COMMAND_LINE_OPTIONS)",
            help_branch,
        )
        self.assertIn(
            "PhGetApplicationUiString(IDS_PH_COMMAND_LINE_OPTIONS_CONTENT)",
            help_branch,
        )

        phconfig = (
            REPO_ROOT / "phlib" / "include" / "phconfig.h"
        ).read_text(encoding="utf-8-sig")
        phglobal = (
            REPO_ROOT / "phlib" / "global.c"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("EXTERN_C PVOID PhApplicationUiResourceInstance;", phconfig)
        self.assertIn("PVOID PhApplicationUiResourceInstance = NULL;", phglobal)
        registration = "PhApplicationUiResourceInstance = PhInstanceHandle;"
        self.assertIn(registration, win_main)
        self.assertLess(
            win_main.index(registration),
            win_main.index("PhpProcessStartupParameters();"),
        )

        phlib_source = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (
                REPO_ROOT / "phlib" / "guisup.c",
                REPO_ROOT / "phlib" / "mapldr.c",
                REPO_ROOT / "phlib" / "util.c",
            )
        )
        self.assertNotRegex(
            phlib_source,
            r"PhLoadUiString\s*\([^;]+,\s*L\"",
        )
        self.assertNotRegex(
            phlib_source,
            r"PhLoadUiString\s*\(\s*NtCurrentImageBase\(\)",
        )
        self.assertEqual(
            len(re.findall(r"PhLoadUiString\s*\([^;]+,\s*NULL\s*\)", phlib_source)),
            5,
        )
        self.assertGreaterEqual(
            phlib_source.count("PhApplicationUiResourceInstance"),
            5,
        )
        map_loader = (REPO_ROOT / "phlib" / "mapldr.c").read_text(
            encoding="utf-8-sig"
        )
        self.assertEqual(
            map_loader.count(
                'PhGetStringOrDefault(resourceTitle, L"Unable to load plugin.")'
            ),
            2,
        )
        for resource_id, fallback in (
            ("IDS_PH_PLUGIN_IMPORT_BY_ORDINAL", "Name: %s\\r\\nOrdinal: %u\\r\\nModule: %hs"),
            ("IDS_PH_PLUGIN_IMPORT_BY_NAME", "Name: %s\\r\\nFunction: %hs\\r\\nModule: %hs"),
        ):
            with self.subTest(phlib_format_resource_id=resource_id):
                self.assertRegex(
                    map_loader,
                    rf"(?s){resource_id}(?:(?!IDS_PH_).)*PhGetStringOrDefault\(resourceFormat,\s*L\"{re.escape(fallback)}\"\)",
                )
        self.assertRegex(
            (REPO_ROOT / "phlib" / "util.c").read_text(encoding="utf-8-sig"),
            r'(?s)IDS_PH_LOCATION_NOT_FOUND(?:(?!IDS_PH_).)*PhGetStringOrDefault\(resourceTitle, L"The location could not be found\."\)',
        )
        self.assertRegex(
            (REPO_ROOT / "phlib" / "guisup.c").read_text(encoding="utf-8-sig"),
            r'(?s)IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT(?:(?!IDS_PH_).)*PhGetStringOrDefault\(resourceTitle, L"Unable to create the window context\."\)',
        )

        gui_support = (
            REPO_ROOT / "phlib" / "guisup.c"
        ).read_text(encoding="utf-8-sig")
        fls_failure = gui_support[
            gui_support.index("if (!FlsSetValue(WindowCallbackFlsIndex, hashtable))"):
            gui_support.index("RtlFailFast(FAST_FAIL_INVALID_FLS_DATA);")
        ]
        self.assertLess(
            fls_failure.index("PhGetLastError()"),
            fls_failure.index("PhLoadUiString("),
        )

    def test_toolstatus_runtime_text_uses_native_resources(self) -> None:
        statusbar = (
            REPO_ROOT / "plugins" / "ToolStatus" / "statusbar.c"
        ).read_text(encoding="utf-8-sig")
        toolbar = (
            REPO_ROOT / "plugins" / "ToolStatus" / "toolbar.c"
        ).read_text(encoding="utf-8-sig")
        graph = (
            REPO_ROOT / "plugins" / "ToolStatus" / "graph.c"
        ).read_text(encoding="utf-8-sig")
        options = (
            REPO_ROOT / "plugins" / "ToolStatus" / "options.c"
        ).read_text(encoding="utf-8-sig")
        customize_toolbar = (
            REPO_ROOT / "plugins" / "ToolStatus" / "customizetb.c"
        ).read_text(encoding="utf-8-sig")
        main = (
            REPO_ROOT / "plugins" / "ToolStatus" / "main.c"
        ).read_text(encoding="utf-8-sig")
        header = (
            REPO_ROOT / "plugins" / "ToolStatus" / "toolstatus.h"
        ).read_text(encoding="utf-8-sig")
        resource_script = (
            REPO_ROOT / "plugins" / "ToolStatus" / "ToolStatus.rc"
        ).read_text(encoding="utf-8-sig")
        source = statusbar + toolbar + main + graph + options + customize_toolbar
        statusbar_get_text = statusbar[
            statusbar.index("PWSTR StatusBarGetText("):
            statusbar.index("VOID StatusBarShowMenu(")
        ]
        customize_load_settings = customize_toolbar[
            customize_toolbar.index("VOID CustomizeLoadToolbarSettings("):
            customize_toolbar.index("VOID CustomizeResetImages(")
        ]

        self.assertNotIn("PhTranslateString", source)
        self.assertNotIn("#include <phtranslation.h>", source)
        self.assertNotRegex(statusbar_get_text, r"return\s+L\"")
        self.assertIn("ToolStatusInitializeUiStrings();", main)
        self.assertIn("PCWSTR ToolStatusGetUiString(", main)
        self.assertIn("PCWSTR ToolStatusGetUiString(", header)

        resource_ids = (
            "IDS_TS_STATUS_CPU_USAGE",
            "IDS_TS_STATUS_PERCENT",
            "IDS_TS_STATUS_COMMIT_CHARGE",
            "IDS_TS_STATUS_OPEN_PAREN",
            "IDS_TS_STATUS_CLOSE_PAREN_PERCENT",
            "IDS_TS_STATUS_PHYSICAL_MEMORY",
            "IDS_TS_STATUS_FREE_MEMORY",
            "IDS_TS_STATUS_PROCESSES",
            "IDS_TS_STATUS_THREADS",
            "IDS_TS_STATUS_HANDLES",
            "IDS_TS_STATUS_IO_READ_OTHER",
            "IDS_TS_STATUS_IO_WRITE",
            "IDS_TS_STATUS_CLOSE_PAREN_COLON",
            "IDS_TS_STATUS_COLON",
            "IDS_TS_STATUS_EMPTY",
            "IDS_TS_STATUS_VISIBLE",
            "IDS_TS_STATUS_VISIBLE_NA",
            "IDS_TS_STATUS_SELECTED",
            "IDS_TS_STATUS_SELECTED_NA",
            "IDS_TS_STATUS_INTERVAL_FAST",
            "IDS_TS_STATUS_INTERVAL_NORMAL",
            "IDS_TS_STATUS_INTERVAL_BELOW_NORMAL",
            "IDS_TS_STATUS_INTERVAL_SLOW",
            "IDS_TS_STATUS_INTERVAL_VERY_SLOW",
            "IDS_TS_STATUS_INTERVAL_NA",
            "IDS_TS_STATUS_INTERVAL_PAUSED",
            "IDS_TS_STATUS_SELECTED_WS",
            "IDS_TS_STATUS_SELECTED_WS_NA",
            "IDS_TS_STATUS_SELECTED_PRIVATE_BYTES",
            "IDS_TS_STATUS_SELECTED_PRIVATE_BYTES_NA",
            "IDS_TS_STATUS_KSI",
            "IDS_TS_STATUS_NOT_CONNECTED",
            "IDS_TS_STATUS_KSI_DOWN",
            "IDS_TS_STATUS_KSI_UP",
            "IDS_TS_STATUS_LABEL_CPU_USAGE",
            "IDS_TS_STATUS_LABEL_PHYSICAL_MEMORY",
            "IDS_TS_STATUS_LABEL_NUMBER_OF_PROCESSES",
            "IDS_TS_STATUS_LABEL_COMMIT_CHARGE",
            "IDS_TS_STATUS_LABEL_FREE_PHYSICAL_MEMORY",
            "IDS_TS_STATUS_LABEL_NUMBER_OF_THREADS",
            "IDS_TS_STATUS_LABEL_NUMBER_OF_HANDLES",
            "IDS_TS_STATUS_LABEL_NUMBER_OF_VISIBLE_ITEMS",
            "IDS_TS_STATUS_LABEL_NUMBER_OF_SELECTED_ITEMS",
            "IDS_TS_STATUS_LABEL_INTERVAL_STATUS",
            "IDS_TS_STATUS_LABEL_IO_READ_OTHER",
            "IDS_TS_STATUS_LABEL_IO_WRITE",
            "IDS_TS_STATUS_LABEL_MAX_CPU_PROCESS",
            "IDS_TS_STATUS_LABEL_MAX_IO_PROCESS",
            "IDS_TS_STATUS_LABEL_SELECTED_PROCESS_WS",
            "IDS_TS_STATUS_LABEL_SELECTED_PROCESS_PRIVATE_BYTES",
            "IDS_TS_STATUS_LABEL_KSI_STATUS",
            "IDS_TS_MENU_TOOLBAR",
            "IDS_TS_MENU_MAIN_AUTO_HIDE",
            "IDS_TS_MENU_SEARCH_BOX",
            "IDS_TS_MENU_LOCK_TOOLBAR",
            "IDS_TS_MENU_CUSTOMIZE",
            "IDS_TS_MENU_LOCK",
            "IDS_TS_MENU_LOGOFF",
            "IDS_TS_MENU_SLEEP",
            "IDS_TS_MENU_HIBERNATE",
            "IDS_TS_MENU_UPDATE_RESTART",
            "IDS_TS_MENU_UPDATE_SHUTDOWN",
            "IDS_TS_MENU_RESTART",
            "IDS_TS_MENU_RESTART_ADVANCED",
            "IDS_TS_MENU_RESTART_BOOT",
            "IDS_TS_MENU_RESTART_FIRMWARE",
            "IDS_TS_MENU_SHUTDOWN",
            "IDS_TS_MENU_HYBRID_SHUTDOWN",
            "IDS_TS_SEARCH_PROCESSES",
            "IDS_TS_SEARCH_SERVICES",
            "IDS_TS_SEARCH_NETWORK",
            "IDS_TS_SEARCH_DISABLED",
            "IDS_TS_GRAPH_CPU_HISTORY",
            "IDS_TS_GRAPH_PHYSICAL_MEMORY_HISTORY",
            "IDS_TS_GRAPH_COMMIT_CHARGE_HISTORY",
            "IDS_TS_GRAPH_IO_HISTORY",
            "IDS_TS_GRAPH_UNAVAILABLE_SUFFIX",
            "IDS_TS_GRAPH_PID_CLOSE_READ_OTHER",
            "IDS_TS_GRAPH_READ_OTHER",
            "IDS_TS_GRAPH_WRITE_SEPARATOR",
            "IDS_TS_GRAPH_READ",
            "IDS_TS_GRAPH_WRITE_LINE",
            "IDS_TS_GRAPH_OTHER_LINE",
            "IDS_TS_GRAPH_NONE",
            "IDS_TS_CUSTOMIZE_NO_TEXT_LABELS",
            "IDS_TS_CUSTOMIZE_SELECTIVE_TEXT",
            "IDS_TS_CUSTOMIZE_SHOW_TEXT_LABELS",
            "IDS_TS_CUSTOMIZE_SEARCH_ALWAYS_SHOW",
            "IDS_TS_CUSTOMIZE_SEARCH_HIDE_INACTIVE",
            "IDS_TS_CUSTOMIZE_SEPARATOR",
            "IDS_TS_TOOLBAR_REFRESH",
            "IDS_TS_TOOLBAR_OPTIONS",
            "IDS_TS_TOOLBAR_FIND_HANDLES_OR_DLLS",
            "IDS_TS_TOOLBAR_SYSTEM_INFORMATION",
            "IDS_TS_TOOLBAR_FIND_WINDOW",
            "IDS_TS_TOOLBAR_FIND_WINDOW_THREAD",
            "IDS_TS_TOOLBAR_FIND_WINDOW_KILL",
            "IDS_TS_TOOLBAR_ALWAYS_ON_TOP",
            "IDS_TS_TOOLBAR_COMPUTER",
            "IDS_TS_TOOLBAR_SHOW_DETAILS_ALL_PROCESSES",
            "IDS_TS_ERROR",
        )
        resource_texts = dict(re.findall(
            r'^\s*(IDS_TS_[A-Z0-9_]+)\s+"([^"]*)"',
            resource_script,
            re.MULTILINE,
        ))
        routed_fallbacks = {}
        for resource_id, fallback in re.findall(
            r'ToolStatusGetUiString\(\s*(IDS_TS_[A-Z0-9_]+),\s*L"([^"]*)"\s*\)',
            source,
        ):
            routed_fallbacks.setdefault(resource_id, set()).add(fallback)
        option_routes = re.findall(
            r'\{\s*TASKBAR_ICON_[A-Z0-9_]+,\s*(IDS_TS_[A-Z0-9_]+),\s*L"([^"]*)"\s*\}',
            options,
        )
        for resource_id, fallback in option_routes:
            routed_fallbacks.setdefault(resource_id, set()).add(fallback)

        for resource_id in resource_ids:
            with self.subTest(toolstatus_resource_id=resource_id):
                self.assertEqual(
                    routed_fallbacks.get(resource_id),
                    {resource_texts[resource_id]},
                )

        newly_routed_texts = {
            resource_texts[resource_id]
            for resource_id in resource_ids
            if resource_id.startswith((
                "IDS_TS_MENU_",
                "IDS_TS_SEARCH_",
                "IDS_TS_GRAPH_",
                "IDS_TS_CUSTOMIZE_",
            ))
        }
        for fallback in newly_routed_texts:
            with self.subTest(toolstatus_native_fallback=fallback):
                literal = f'L"{fallback}"'
                routed = re.findall(
                    rf'ToolStatusGetUiString\(\s*IDS_TS_[A-Z0-9_]+,\s*{re.escape(literal)}\s*\)',
                    source,
                )
                table_routes = [
                    route
                    for route in option_routes
                    if route[1] == fallback
                ]
                self.assertEqual(
                    source.count(literal),
                    len(routed) + len(table_routes),
                )

        self.assertIn(
            "ToolStatusUiStrings[IDS_TS_LAST - IDS_TS_FIRST + 1]",
            main,
        )
        self.assertRegex(
            main,
            r"PhLoadUiString\s*\(\s*PluginInstance->DllBase,\s*resourceId,\s*NULL\s*\)",
        )
        self.assertIn("IDS_TS_FIRST", main)
        self.assertIn("IDS_TS_LAST", main)
        self.assertIn("ComboBox_SetItemData", options)
        self.assertIn("ComboBox_GetItemData", options)
        self.assertIn("ComboBox_DeleteString", options)
        self.assertNotIn("CustomizeTextOptionsStrings", customize_toolbar)
        self.assertNotIn("CustomizeSearchDisplayStrings", customize_toolbar)
        self.assertEqual(
            re.findall(r"IDS_TS_CUSTOMIZE_[A-Z0-9_]+", customize_load_settings),
            [
                "IDS_TS_CUSTOMIZE_NO_TEXT_LABELS",
                "IDS_TS_CUSTOMIZE_SELECTIVE_TEXT",
                "IDS_TS_CUSTOMIZE_SHOW_TEXT_LABELS",
                "IDS_TS_CUSTOMIZE_SEARCH_ALWAYS_SHOW",
                "IDS_TS_CUSTOMIZE_SEARCH_HIDE_INACTIVE",
            ],
        )
        self.assertNotIn("GraphTypePairs", options)
        self.assertNotIn("GraphTypeGetTypeInteger", options)
        self.assertNotIn("PhSelectComboBoxString", options)

    def test_statusbar_audit_counts_only_native_resource_calls(self) -> None:
        audit = load_audit_module()
        source = """
            return L"Unrouted status label";
            return ToolStatusGetUiString(
                IDS_TS_STATUS_LABEL_CPU_USAGE,
                L"Routed status label"
                );
        """
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_statusbar(source_file.name, entries)

        self.assertEqual(
            [entry["english"] for entry in entries],
            ["Routed status label"],
        )

    def test_main_status_calls_do_not_hide_unresolved_variable_messages(self) -> None:
        audit = load_audit_module()
        unresolved = []

        for path in (REPO_ROOT / "SystemInformer").glob("*.c"):
            source = path.read_text(encoding="utf-8-sig")
            for name, args, spans, call_start in audit.find_calls(
                source, {"PhShowStatus", "PhShowContinueStatus"}
            ):
                if len(args) <= 1:
                    continue
                message = args[1]
                if (
                    audit.first_literal(message) is None
                    and "PhGetApplicationUiString" not in message
                ):
                    unresolved.append(
                        f"{path.name}:{audit.line_of_offset(source, call_start)}:{name}"
                    )

        self.assertEqual(unresolved, [])

    def test_printf_vararg_literals_are_migrated_at_their_callsites(self) -> None:
        audit = load_audit_module()
        unresolved = []

        for path in audit.iter_source_files():
            if not path.endswith((".c", ".cpp")):
                continue
            entries = []
            audit.scan_c_file(path, entries)
            unresolved.extend(
                entry
                for entry in entries
                if entry["category"] == "c_msgbox_vararg"
            )

        self.assertEqual(
            [
                f"{entry['file']}:{entry['line']}:{entry['english']}"
                for entry in unresolved
            ],
            [],
        )

    def test_plugin_vararg_fallbacks_use_native_string_resources(self) -> None:
        extended_services = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "plugins" / "ExtendedServices").glob("*.c")
        )
        user_notes = (
            REPO_ROOT / "plugins" / "UserNotes" / "main.c"
        ).read_text(encoding="utf-8-sig")

        self.assertEqual(extended_services.count("IDS_ES_UNKNOWN_ERROR"), 5)
        self.assertEqual(
            user_notes.count("IDS_UN_AFFINITY_INDIVIDUAL_THREADS"),
            2,
        )

    def test_setup_progress_and_wizard_buttons_use_string_resources(self) -> None:
        setup_sources = {
            path.name: path.read_text(encoding="utf-8-sig")
            for path in (REPO_ROOT / "tools" / "CustomSetupTool").glob("*.c")
        }

        for name in ("install.c", "update.c", "uninstall.c"):
            with self.subTest(source=name):
                self.assertNotRegex(
                    setup_sources[name],
                    r"SetupSetProgressText\([^,]+,\s*L\"",
                )

        wizard = setup_sources["wizard.c"]
        main = setup_sources["main.c"]
        all_setup_source = "\n".join(setup_sources.values())
        setup_resource = (
            REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc"
        ).read_text(encoding="utf-8-sig")
        self.assertEqual(len(stringtable_ids(setup_resource)), 74)
        self.assertNotRegex(
            wizard,
            r"SetupSetWizardButtonText\([^,]+,\s*[^,]+,\s*L\"",
        )
        for literal in (
            'L"Cancel Setup?"',
            'L"Invalid Start Menu folder"',
            'L"Enter a valid Start Menu folder name."',
        ):
            self.assertNotIn(literal, wizard)
        self.assertNotRegex(wizard, r"PhShowStatus\([^,]+,\s*L\"")
        self.assertNotRegex(wizard, r"PhSetDialogItemText\([^,]+,\s*[^,]+,\s*L\"")
        self.assertNotIn('header.pszCaption = L"', wizard)
        self.assertIn("header.pszCaption = PhApplicationName;", wizard)
        self.assertIn(
            "static PPH_STRING SetupUiStrings[IDS_SETUP_LAST - IDS_SETUP_FIRST + 1]",
            main,
        )
        self.assertIn("if (!SetupInitializeUiStrings())", main)
        self.assertIn(
            "PhApplicationName = SetupGetUiString(IDS_SETUP_WINDOW_TITLE);",
            main,
        )
        resource_header = (
            REPO_ROOT / "tools" / "CustomSetupTool" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        self.assertIn(
            "#define IDS_SETUP_FIRST                                 IDS_SETUP_UNINSTALL_COMPLETE",
            resource_header,
        )
        self.assertIn(
            "#define IDS_SETUP_LAST                                  IDS_SETUP_INSTALLATION_FOLDER_FORMAT",
            resource_header,
        )
        numeric_ids = {
            name: int(value)
            for name, value in re.findall(
                r"^#define\s+(IDS_SETUP_[A-Z0-9_]+)\s+(\d+)\s*$",
                resource_header,
                re.MULTILINE,
            )
        }
        first_id = numeric_ids["IDS_SETUP_UNINSTALL_COMPLETE"]
        last_id = numeric_ids["IDS_SETUP_INSTALLATION_FOLDER_FORMAT"]
        loaded_ids = set(re.findall(r"SetupGetUiString\((IDS_SETUP_[A-Z0-9_]+)\)", all_setup_source))
        self.assertTrue(loaded_ids)
        for resource_name in loaded_ids:
            self.assertIn(resource_name, numeric_ids)
            self.assertLessEqual(first_id, numeric_ids[resource_name])
            self.assertLessEqual(numeric_ids[resource_name], last_id)
        self.assertIn("PhLoadUiString(PhInstanceHandle, ResourceId, NULL)", wizard)
        self.assertRegex(
            wizard,
            r"title->Buffer,\s*L\"%s\",\s*content->Buffer",
        )

        for literal in (
            "Hey there, before we continue...",
            "Initializing...",
            "Setup failed with an error.",
            "A free, powerful, multi-purpose tool",
            "Installation Folder:",
            "Preparing to install...",
            "System Informer has been uninstalled.",
            "A reboot is required to complete the uninstall.",
            "Uninstalling System Informer...",
            "Uninstall failed with an error.",
            "Are you sure you want to uninstall System Informer?",
            "Error updating to the latest version.",
        ):
            self.assertNotIn(f'L"{literal}', all_setup_source)

    def test_ci_validates_all_built_plugin_resources(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8-sig"
        )
        target_blocks = re.findall(
            r"\$resourceTargets = @\((.*?)\)\s+"
            r"python tools\\zhcn\\validate_templates\.py @resourceTargets",
            workflow,
            re.DOTALL,
        )

        expected_branch_targets = {
            r"bin\Release64\sys_info.exe",
            r"bin\Release64\peview.exe",
            *(rf"bin\Release64\plugins\{module_name}.dll" for module_name in PLUGIN_MODULES),
        }
        expected_release_targets = expected_branch_targets | {
            r"build\output\systeminformer-build-release-setup.exe",
            r"build\output\systeminformer-build-canary-setup.exe",
        }

        self.assertEqual(len(target_blocks), 2)
        self.assertEqual(set(re.findall(r"'([^']+)'", target_blocks[0])), expected_branch_targets)
        self.assertEqual(set(re.findall(r"'([^']+)'", target_blocks[1])), expected_release_targets)
        self.assertEqual(
            set(re.findall(r"--require-strings-in\s+'([^']+)'", workflow)),
            {
                r"build\output\systeminformer-build-release-setup.exe",
                r"build\output\systeminformer-build-canary-setup.exe",
            },
        )
        self.assertEqual(
            Counter(
                (path, int(count))
                for path, count in re.findall(
                    r"--expect-string-count-in\s+'([^'=]+)=(\d+)'",
                    workflow,
                )
            ),
            Counter(
                {
                    (r"bin\Release64\sys_info.exe", 378): 2,
                    (r"bin\Release64\plugins\DotNetTools.dll", 89): 2,
                    (r"bin\Release64\plugins\ExtendedServices.dll", 66): 2,
                    (r"bin\Release64\plugins\ExtendedTools.dll", 104): 2,
                    (r"bin\Release64\plugins\HardwareDevices.dll", 96): 2,
                    (r"bin\Release64\plugins\NetworkTools.dll", 22): 2,
                    (r"bin\Release64\plugins\WindowExplorer.dll", 93): 2,
                    (r"bin\Release64\plugins\OnlineChecks.dll", 5): 2,
                    (r"bin\Release64\plugins\ToolStatus.dll", 103): 2,
                    (r"bin\Release64\plugins\Updater.dll", 7): 2,
                    (r"bin\Release64\plugins\UserNotes.dll", 15): 2,
                    (r"bin\Release64\peview.exe", 218): 2,
                    (r"build\output\systeminformer-build-release-setup.exe", 74): 1,
                    (r"build\output\systeminformer-build-canary-setup.exe", 74): 1,
                }
            ),
        )

    def test_english_manifest_ignores_generated_localized_resources(self) -> None:
        audit = (REPO_ROOT / "tools" / "zhcn" / "audit.py").read_text(encoding="utf-8")

        self.assertIn('base.endswith(".zh-cn.rc")', audit)


if __name__ == "__main__":
    unittest.main()
