#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


# symbol | id | English | zh-CN
RESOURCE_DATA = r"""
IDS_PV_MACHINE_I386|3270|i386|i386
IDS_PV_MACHINE_I386_CHPE|3271|i386 (CHPE)|i386 (CHPE)
IDS_PV_MACHINE_AMD64|3272|AMD64|AMD64
IDS_PV_MACHINE_AMD64_ARM64X|3273|AMD64 (ARM64X)|AMD64 (ARM64X)
IDS_PV_MACHINE_IA64|3274|IA64|IA64
IDS_PV_MACHINE_ARM_THUMB2|3275|ARM Thumb-2|ARM Thumb-2
IDS_PV_MACHINE_ARM64|3276|ARM64|ARM64
IDS_PV_MACHINE_ARM64_ARM64X|3277|ARM64 (ARM64X)|ARM64 (ARM64X)
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in RESOURCES
]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_machine", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def masked_source(filename):
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PEVIEW_ROOT / filename).read_text(encoding="utf-8-sig")
    )


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
                return text[start + 1:offset]
    raise AssertionError(f"unterminated function: {function_name}")


def normalize(expression):
    return re.sub(r"\s+", "", expression)


def parse_case_assignments(body):
    pattern = re.compile(
        r"(?:\bcase\s+([A-Za-z0-9_]+)\s*:|\b(default)\s*:)\s*"
        r"type\s*=\s*(.+?)\s*;\s*break\s*;",
        re.S,
    )
    return tuple(
        (match.group(1) or match.group(2), normalize(match.group(3)))
        for match in pattern.finditer(body)
    )


def parse_defines():
    header = (PEVIEW_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    defines = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PV_[A-Z0-9_]+)\s+(\d+)$",
            header,
        )
    }
    return defines, header


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PV_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class PeViewMachineResourcesTests(unittest.TestCase):
    def test_wsl_switch_keeps_exact_cases_order_and_resources(self):
        body = function_body(masked_source("exlfprp.c"), "PvpSetWslImageMachineType")
        self.assertEqual(
            parse_case_assignments(body),
            (
                ("EM_386", "PvpLoadUiString(IDS_PV_MACHINE_I386)"),
                ("EM_X86_64", "PvpLoadUiString(IDS_PV_MACHINE_AMD64)"),
                ("default", "PvpLoadUiString(IDS_PV_ERROR)"),
            ),
        )
        self.assertRegex(body, r"\bPCWSTR\s+type\s*=\s*PvpLoadUiString\(IDS_PV_NOT_AVAILABLE\)\s*;")
        self.assertNotRegex(body, r"\bPWSTR\s+type\b|\bPPH_STRING\s+type\b")
        self.assertRegex(body, r"PhSetDialogItemText\(\s*hwndDlg\s*,\s*IDC_TARGETMACHINE\s*,\s*type\s*\)")

    def test_pe_switch_and_three_ternaries_are_exact(self):
        body = function_body(masked_source("peprp.c"), "PvpSetPeImageMachineType")
        self.assertEqual(
            parse_case_assignments(body),
            (
                (
                    "IMAGE_FILE_MACHINE_I386",
                    "PhGetMappedImageCHPEVersion(&PvMappedImage)?"
                    "PvpLoadUiString(IDS_PV_MACHINE_I386_CHPE):"
                    "PvpLoadUiString(IDS_PV_MACHINE_I386)",
                ),
                (
                    "IMAGE_FILE_MACHINE_AMD64",
                    "PhGetMappedImageCHPEVersion(&PvMappedImage)?"
                    "PvpLoadUiString(IDS_PV_MACHINE_AMD64_ARM64X):"
                    "PvpLoadUiString(IDS_PV_MACHINE_AMD64)",
                ),
                ("IMAGE_FILE_MACHINE_IA64", "PvpLoadUiString(IDS_PV_MACHINE_IA64)"),
                ("IMAGE_FILE_MACHINE_ARMNT", "PvpLoadUiString(IDS_PV_MACHINE_ARM_THUMB2)"),
                (
                    "IMAGE_FILE_MACHINE_ARM64",
                    "PhGetMappedImageCHPEVersion(&PvMappedImage)?"
                    "PvpLoadUiString(IDS_PV_MACHINE_ARM64_ARM64X):"
                    "PvpLoadUiString(IDS_PV_MACHINE_ARM64)",
                ),
                ("default", "PvpLoadUiString(IDS_PV_MAPPING_UNKNOWN)"),
            ),
        )
        self.assertRegex(body, r"\bPCWSTR\s+type\s*;")
        self.assertNotRegex(body, r"\bPWSTR\s+type\b|\bPPH_STRING\s+type\b")
        self.assertEqual(body.count("PhGetMappedImageCHPEVersion(&PvMappedImage)"), 3)
        self.assertRegex(
            body,
            r"PhSetListViewSubItem\(\s*ListViewHandle\s*,\s*"
            r"PVP_IMAGE_GENERAL_INDEX_NAME\s*,\s*1\s*,\s*type\s*\)",
        )

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCES], list(range(3270, 3278)))
        self.assertEqual(sorted(defines.values()), list(range(3000, 3278)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 278)
        self.assertEqual(len(chinese), 278)
        self.assertRegex(header, r"(?m)^#define IDS_PV_LAST\s+IDS_PV_MACHINE_ARM64_ARM64X$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3278$")

    def test_all_machine_labels_are_native_only(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        strings = data["strings"]
        native_strings = data["native_strings"]

        self.assertFalse(strings.keys() & native_strings.keys())
        for _symbol, _resource_id, english, chinese in RESOURCES:
            with self.subTest(english=english):
                self.assertEqual(native_strings.get(english), chinese)
                self.assertNotIn(english, strings)

    def test_ci_and_fresh_audit_boundaries_are_exact(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("peview.exe=278"), 2)
        self.assertNotIn("peview.exe=270", workflow)

        audit = load_audit_module()
        entries = []
        for path in sorted(PEVIEW_ROOT.rglob("*.c")):
            audit.scan_c_file(str(path), entries)
        remaining = [
            entry
            for entry in entries
            if entry["category"] == "c_window_text"
            and entry["file"].startswith("tools/peview/")
        ]
        self.assertEqual(len({entry["english"] for entry in remaining}), 9)
        self.assertEqual(len(remaining), 9)


if __name__ == "__main__":
    unittest.main()
