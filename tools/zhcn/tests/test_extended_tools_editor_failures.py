#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


def source_text(filename):
    return (PLUGIN_ROOT / filename).read_text(encoding="utf-8-sig")


def function_body(text, function_name):
    match = re.search(rf"\b{re.escape(function_name)}\s*\([^;]*?\)\s*\{{", text, re.S)
    if not match:
        raise AssertionError(f"function not found: {function_name}")

    start = match.end() - 1
    depth = 0
    for offset in range(start, len(text)):
        if text[offset] == "{":
            depth += 1
        elif text[offset] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : offset]
    raise AssertionError(f"unterminated function: {function_name}")


class ExtendedToolsEditorFailureTests(unittest.TestCase):
    def test_firmware_and_tpm_runtime_identifiers_use_raw_list_items(self):
        firmware = function_body(source_text("firmware.c"), "EtEnumerateFirmwareEntries")
        tpm = function_body(source_text("tpm.c"), "EtEnumerateTpmEntries")

        self.assertRegex(
            firmware,
            r"PhAddListViewItemRaw\(\s*Context->ListViewHandle\s*,\s*MAXINT\s*,\s*"
            r"PhGetStringOrEmpty\(entry->Name\)\s*,\s*entry\s*\)",
        )
        self.assertNotIn("PhAddListViewItem(", firmware)

        self.assertRegex(
            tpm,
            r"PhAddListViewItemRaw\(\s*Context->ListViewHandle\s*,\s*MAXINT\s*,\s*"
            r"string->Buffer\s*,\s*ULongToPtr\(indices\[i\]\.Value\)\s*\)",
        )
        self.assertNotIn("PhAddListViewItem(", tpm)

    def test_tpm_reserved_type_and_ulong_formats_are_correct(self):
        tpm = source_text("tpm.c")
        editor = source_text("tpm_editor.c")

        self.assertRegex(
            tpm,
            r"TPMA_NV_RESERVED_TYPE_3[^\r\n]+L\"Reserved type 3\"",
        )
        self.assertNotRegex(
            tpm,
            r"TPMA_NV_RESERVED_TYPE_3[^\r\n]+L\"Reserved type 4\"",
        )
        self.assertNotIn("%08x", editor)
        self.assertEqual(editor.count("%08lx"), 2)

    def test_editor_context_cleanup_covers_dialog_and_thread_failures(self):
        cases = (
            (
                "firmware_editor.c",
                "EtFirmwareEditorContextDestroy",
                "EtFirmwareEditorDialogThreadStart",
                "EtShowFirmwareEditDialog",
                ("Title", "Name", "GuidString"),
                "VariableValue",
            ),
            (
                "tpm_editor.c",
                "EtTpmEditorContextDestroy",
                "EtTpmEditorDialogThreadStart",
                "EtShowTpmEditDialog",
                (),
                "Data",
            ),
        )

        for filename, destroy_name, thread_name, show_name, refs, allocation in cases:
            with self.subTest(filename=filename):
                source = source_text(filename)
                destroy = function_body(source, destroy_name)
                thread = function_body(source, thread_name)
                show = function_body(source, show_name)
                dialog = function_body(
                    source,
                    "EtFirmwareEditorDlgProc"
                    if filename == "firmware_editor.c"
                    else "EtTpmEditorDlgProc",
                )

                for ref in refs:
                    self.assertIn(f"PhClearReference(&Context->{ref});", destroy)
                self.assertRegex(
                    destroy,
                    rf"if\s*\(Context->{allocation}\)\s*PhFree\(Context->{allocation}\)\s*;",
                )
                self.assertIn("PhFree(Context);", destroy)

                self.assertRegex(
                    thread,
                    r"if\s*\(!windowHandle\)\s*\{\s*"
                    r"PhDeleteAutoPool\(&autoPool\);\s*"
                    rf"{destroy_name}\(context\);\s*"
                    r"return\s+STATUS_UNSUCCESSFUL\s*;\s*\}",
                )
                self.assertRegex(
                    thread,
                    r"if\s*\(IsWindow\(windowHandle\)\)\s*DestroyWindow\(windowHandle\);\s*"
                    rf"PhDeleteAutoPool\(&autoPool\);\s*{destroy_name}\(context\);\s*"
                    r"return\s+STATUS_SUCCESS\s*;",
                )
                self.assertEqual(thread.count(f"{destroy_name}(context);"), 2)
                self.assertRegex(
                    show,
                    rf"if\s*\(!NT_SUCCESS\(PhCreateThread2\({thread_name},\s*context\)\)\)\s*"
                    rf"{destroy_name}\(context\)\s*;",
                )
                self.assertNotIn(destroy_name, dialog)


if __name__ == "__main__":
    unittest.main()
