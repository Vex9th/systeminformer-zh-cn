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
IDS_PV_IAT_ENTRY|3278|IATEntry|IAT 条目
IDS_PV_LONG_JUMP|3279|LongJump|长跳转
IDS_PV_RELOC_ABS|3280|ABS|ABS
IDS_PV_RELOC_HIGH|3281|HIGH|HIGH
IDS_PV_RELOC_LOW|3282|LOW|LOW
IDS_PV_RELOC_HIGHLOW|3283|HIGHLOW|HIGHLOW
IDS_PV_RELOC_DIR64|3284|DIR64|DIR64
IDS_PV_RELOC_MOV32|3285|MOV32|MOV32
IDS_PV_RELOC_MOV32_T|3286|MOV32(T)|MOV32(T)
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in RESOURCES
]


CFG_ROUTES = (
    ("ControlFlowGuardFunction", "IDS_PV_TYPE_FUNCTION"),
    ("ControlFlowGuardTakenIatEntry", "IDS_PV_IAT_ENTRY"),
    ("ControlFlowGuardLongJump", "IDS_PV_LONG_JUMP"),
)


RELOCATION_ROUTES = (
    ("IMAGE_REL_BASED_ABSOLUTE", "IDS_PV_RELOC_ABS"),
    ("IMAGE_REL_BASED_HIGH", "IDS_PV_RELOC_HIGH"),
    ("IMAGE_REL_BASED_LOW", "IDS_PV_RELOC_LOW"),
    ("IMAGE_REL_BASED_HIGHLOW", "IDS_PV_RELOC_HIGHLOW"),
    ("IMAGE_REL_BASED_DIR64", "IDS_PV_RELOC_DIR64"),
    ("IMAGE_REL_BASED_ARM_MOV32", "IDS_PV_RELOC_MOV32"),
    ("IMAGE_REL_BASED_THUMB_MOV32", "IDS_PV_RELOC_MOV32_T"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_technical", path)
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


def switch_body(text, expression):
    match = re.search(rf"\bswitch\s*\(\s*{re.escape(expression)}\s*\)\s*\{{", text)
    if not match:
        raise AssertionError(f"switch not found: {expression}")

    start = match.end() - 1
    depth = 0
    for offset in range(start, len(text)):
        if text[offset] == "{":
            depth += 1
        elif text[offset] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:offset]
    raise AssertionError(f"unterminated switch: {expression}")


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


class PeViewTechnicalValueResourcesTests(unittest.TestCase):
    def test_cfg_switch_keeps_exact_cases_resources_and_target_column(self):
        body = function_body(masked_source("cfgprp.c"), "PvPeAddListViewCfgFunctionEntry")
        switch = switch_body(body, "Type")
        pattern = re.compile(
            r"\bcase\s+([A-Za-z0-9_]+)\s*:\s*"
            r"PhSetListViewSubItem\(\s*ListViewHandle\s*,\s*lvItemIndex\s*,\s*2\s*,\s*"
            r"PvpLoadUiString\(\s*(IDS_PV_[A-Z0-9_]+)\s*\)\s*\)\s*;\s*break\s*;",
            re.S,
        )

        self.assertEqual(tuple(pattern.findall(switch)), CFG_ROUTES)
        self.assertNotRegex(switch, r"\bdefault\s*:")
        self.assertNotIn("IDS_PV_COLUMN_IAT_SLOT", switch)

    def test_relocation_switch_keeps_all_seven_routes_and_null_default_semantics(self):
        body = function_body(masked_source("perelocprp.c"), "PvEnumerateRelocationEntries")
        switch = switch_body(body, "entry->Record.Type")
        pattern = re.compile(
            r"\bcase\s+([A-Za-z0-9_]+)\s*:\s*"
            r"type\s*=\s*PvpLoadUiString\(\s*(IDS_PV_RELOC_[A-Z0-9_]+)\s*\)\s*;\s*"
            r"break\s*;",
            re.S,
        )

        self.assertEqual(tuple(pattern.findall(switch)), RELOCATION_ROUTES)
        self.assertNotRegex(switch, r"\bdefault\s*:")
        self.assertRegex(body, r"\bPCWSTR\s+type\s*=\s*NULL\s*;")
        self.assertNotRegex(body, r"\bPWSTR\s+type\b|\bPPH_STRING\s+type\b")
        self.assertRegex(
            body,
            r"\}\s*if\s*\(\s*type\s*\)\s*"
            r"PhSetListViewSubItem\(\s*ListViewHandle\s*,\s*lvItemIndex\s*,\s*2\s*,\s*type\s*\)\s*;\s*"
            r"if\s*\(\s*entry->BlockRva\s*\)",
        )
        self.assertNotIn("PhDereferenceObject(type)", body)

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCES], list(range(3278, 3287)))
        self.assertEqual(sorted(defines.values()), list(range(3000, 3287)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 287)
        self.assertEqual(len(chinese), 287)
        self.assertRegex(header, r"(?m)^#define IDS_PV_LAST\s+IDS_PV_RELOC_MOV32_T$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3287$")

    def test_all_technical_values_are_native_only(self):
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
        self.assertEqual(workflow.count("peview.exe=287"), 2)
        self.assertNotIn("peview.exe=278", workflow)

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
        self.assertEqual(len({entry["english"] for entry in remaining}), 0)
        self.assertEqual(len(remaining), 0)


if __name__ == "__main__":
    unittest.main()
