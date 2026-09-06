#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SOURCE_PATH = REPO_ROOT / "plugins" / "ExtendedTools" / "acpitable.c"


def source_text():
    return SOURCE_PATH.read_text(encoding="utf-8-sig")


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


class ExtendedToolsAcpiBoundsTests(unittest.TestCase):
    def test_common_header_reads_are_guarded_by_returned_buffer_length(self):
        source = source_text()
        signature = source[source.index("VOID EtAcpiDescriptionHeader") :]
        signature = signature[: signature.index("{")]
        body = function_body(source, "EtAcpiDescriptionHeader")

        self.assertRegex(signature, r"_In_\s+ULONG\s+Length")

        fields = (
            "Signature",
            "Length",
            "Revision",
            "Checksum",
            "OEMID",
            "OEMTableID",
            "OEMRevision",
            "CreatorID",
            "CreatorRev",
        )
        for field in fields:
            with self.subTest(field=field):
                self.assertRegex(
                    body,
                    rf"if\s*\(ET_ACPI_HAS\(Length,\s*ET_ACPI_HEADER,\s*{field}\)\)",
                )

        reads = re.findall(r"Header->([A-Za-z0-9_]+)", body)
        self.assertEqual(set(reads), set(fields))

    def test_every_description_header_call_passes_its_clamped_length(self):
        source = source_text()
        calls = re.findall(
            r"EtAcpiDescriptionHeader\(\s*Context\s*,\s*group\s*,\s*"
            r"(?:&Table->Header|Header)\s*,\s*Length\s*\)\s*;",
            source,
        )
        self.assertEqual(len(calls), 8)

        old_calls = re.findall(
            r"EtAcpiDescriptionHeader\(\s*Context\s*,\s*group\s*,\s*"
            r"(?:&Table->Header|Header)\s*\)\s*;",
            source,
        )
        self.assertEqual(old_calls, [])

    def test_dispatch_requires_length_field_and_clamps_firmware_length(self):
        body = function_body(source_text(), "EtAcpiDispatchTable")

        self.assertRegex(
            body,
            r"if\s*\(BufferLength\s*<\s*RTL_SIZEOF_THROUGH_FIELD\("
            r"ET_ACPI_HEADER,\s*Length\)\)\s*return\s*;",
        )
        self.assertRegex(body, r"length\s*=\s*header->Length\s*;")
        self.assertRegex(
            body,
            r"if\s*\(length\s*>\s*BufferLength\s*\|\|\s*length\s*==\s*0\)\s*"
            r"length\s*=\s*BufferLength\s*;",
        )


if __name__ == "__main__":
    unittest.main()
