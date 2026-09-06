#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


# symbol | id | English | zh-CN | translation owner
RESOURCE_DATA = r"""
IDS_PV_IMPORT_OBJECT_CODE|3247|Code|代码|native_strings
IDS_PV_IMPORT_OBJECT_CONST|3248|Const|常量|native_strings
IDS_PV_IMPORT_NAME_NO_PREFIX|3249|Name, no prefix|名称（无前缀）|native_strings
IDS_PV_IMPORT_NAME_UNDECORATE|3250|Name, undecorate|名称（去修饰）|native_strings
IDS_PV_ELF_TYPE_RELOCATABLE|3251|Relocatable|可重定位文件|native_strings
IDS_PV_ELF_TYPE_DYNAMIC|3252|Dynamic|动态|strings
IDS_PV_ELF_TYPE_EXECUTABLE|3253|Executable|可执行文件|native_strings
IDS_PV_ARM64_UNWIND_FULL|3254|Full|完整|native_strings
IDS_PV_TYPE_FUNCTION|3255|Function|函数|native_strings
IDS_PV_ARM64_UNWIND_FRAGMENT|3256|Fragment|片段|native_strings
IDS_PV_ARM64_UNWIND_RESERVED|3257|Reserved|已保留|strings
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in RESOURCES
]


# Existing resources reused by these enum labels.
REUSED_RESOURCES = (
    ("IDS_PV_COLUMN_DATA", 3035, "Data", "数据", "strings"),
    ("IDS_PV_MAPPING_UNKNOWN", 3097, "Unknown", "未知", "strings"),
    ("IDS_PV_COLUMN_ORDINAL", 3054, "Ordinal", "序号", "strings"),
    ("IDS_PV_COLUMN_NAME", 3051, "Name", "名称", "strings"),
)


SWITCH_ROUTES = {
    ("libprp.c", "PvpLibExportsDlgProc", "importEntry.Type"): (
        ("IMPORT_OBJECT_CODE", "IDS_PV_IMPORT_OBJECT_CODE"),
        ("IMPORT_OBJECT_DATA", "IDS_PV_COLUMN_DATA"),
        ("IMPORT_OBJECT_CONST", "IDS_PV_IMPORT_OBJECT_CONST"),
        ("default", "IDS_PV_MAPPING_UNKNOWN"),
    ),
    ("libprp.c", "PvpLibExportsDlgProc", "importEntry.NameType"): (
        ("IMPORT_OBJECT_ORDINAL", "IDS_PV_COLUMN_ORDINAL"),
        ("IMPORT_OBJECT_NAME", "IDS_PV_COLUMN_NAME"),
        ("IMPORT_OBJECT_NAME_NO_PREFIX", "IDS_PV_IMPORT_NAME_NO_PREFIX"),
        ("IMPORT_OBJECT_NAME_UNDECORATE", "IDS_PV_IMPORT_NAME_UNDECORATE"),
        ("default", "IDS_PV_MAPPING_UNKNOWN"),
    ),
    ("exlfprp.c", "PvpSetWslImageType", "PvMappedImage.Header->e_type"): (
        ("ET_REL", "IDS_PV_ELF_TYPE_RELOCATABLE"),
        ("ET_DYN", "IDS_PV_ELF_TYPE_DYNAMIC"),
        ("ET_EXEC", "IDS_PV_ELF_TYPE_EXECUTABLE"),
        ("default", "IDS_PV_ERROR"),
    ),
    ("peprp.c", "PvpSetPeImageMachineType", "machine"): (
        ("IMAGE_FILE_MACHINE_IA64", "IDS_PV_MACHINE_IA64"),
        ("IMAGE_FILE_MACHINE_ARMNT", "IDS_PV_MACHINE_ARM_THUMB2"),
        ("default", "IDS_PV_MAPPING_UNKNOWN"),
    ),
    ("peprp.c", "PvpSetPeImageSubsystem", "subsystem"): (
        ("IMAGE_SUBSYSTEM_NATIVE", "IDS_PV_SUBSYSTEM_NATIVE"),
        ("IMAGE_SUBSYSTEM_WINDOWS_GUI", "IDS_PV_SUBSYSTEM_WINDOWS_GUI"),
        ("IMAGE_SUBSYSTEM_WINDOWS_CUI", "IDS_PV_SUBSYSTEM_WINDOWS_CUI"),
        ("IMAGE_SUBSYSTEM_OS2_CUI", "IDS_PV_SUBSYSTEM_OS2_CUI"),
        ("IMAGE_SUBSYSTEM_POSIX_CUI", "IDS_PV_SUBSYSTEM_POSIX_CUI"),
        ("IMAGE_SUBSYSTEM_WINDOWS_CE_GUI", "IDS_PV_SUBSYSTEM_WINDOWS_CE_GUI"),
        ("IMAGE_SUBSYSTEM_EFI_APPLICATION", "IDS_PV_SUBSYSTEM_EFI_APPLICATION"),
        ("IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER", "IDS_PV_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER"),
        ("IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER", "IDS_PV_SUBSYSTEM_EFI_RUNTIME_DRIVER"),
        ("IMAGE_SUBSYSTEM_EFI_ROM", "IDS_PV_SUBSYSTEM_EFI_ROM"),
        ("IMAGE_SUBSYSTEM_XBOX", "IDS_PV_SUBSYSTEM_XBOX"),
        ("IMAGE_SUBSYSTEM_WINDOWS_BOOT_APPLICATION", "IDS_PV_SUBSYSTEM_WINDOWS_BOOT_APPLICATION"),
        ("default", "IDS_PV_MAPPING_UNKNOWN"),
    ),
}


# file | API | arguments before text | symbol | enclosing case
DIRECT_ROUTES = (
    ("cfgprp.c", "PhSetListViewSubItem", "ListViewHandle,lvItemIndex,2", "IDS_PV_TYPE_FUNCTION", "ControlFlowGuardFunction"),
    ("peexceptprp.c", "PhSetListViewSubItem", "Context->ListViewHandle,lvItemIndex,1", "IDS_PV_ARM64_UNWIND_FULL", "PdataRefToFullXdata"),
    ("peexceptprp.c", "PhSetListViewSubItem", "Context->ListViewHandle,lvItemIndex,1", "IDS_PV_TYPE_FUNCTION", "PdataPackedUnwindFunction"),
    ("peexceptprp.c", "PhSetListViewSubItem", "Context->ListViewHandle,lvItemIndex,1", "IDS_PV_ARM64_UNWIND_FRAGMENT", "PdataPackedUnwindFragment"),
    ("peexceptprp.c", "PhSetListViewSubItem", "Context->ListViewHandle,lvItemIndex,1", "IDS_PV_ARM64_UNWIND_RESERVED", "3"),
    ("propstore.c", "PhSetListViewSubItem", "ListViewHandle,lvItemIndex,1", "IDS_PV_MAPPING_UNKNOWN", ""),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_enums", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_text(source_name):
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PEVIEW_ROOT / source_name).read_text(encoding="utf-8-sig")
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


def parse_switch_routes(source_name, function_name, expression):
    body = switch_body(function_body(source_text(source_name), function_name), expression)
    routes = []
    pattern = re.compile(
        r"(?:\bcase\s+([A-Za-z0-9_]+)\s*:|\b(default)\s*:)"
        r"(?:(?!\bcase\b|\bdefault\b).)*?"
        r"\btype\s*=\s*PvpLoadUiString\(\s*(IDS_PV_[A-Z0-9_]+)\s*\)\s*;",
        re.S,
    )
    for match in pattern.finditer(body):
        routes.append((match.group(1) or match.group(2), match.group(3)))
    return tuple(routes)


def normalize(expression):
    return re.sub(r"\s+", "", expression)


def parse_direct_routes(source_name):
    audit = load_audit_module()
    source = source_text(source_name)
    routes = []

    for api, args, _spans, call_start in audit.find_calls(
        source, {"PhSetListViewSubItem"}
    ):
        if len(args) != 4:
            continue
        match = re.fullmatch(
            r"\s*PvpLoadUiString\(\s*(IDS_PV_[A-Z0-9_]+)\s*\)\s*",
            args[3],
            re.S,
        )
        if not match:
            continue

        prefix = source[max(0, call_start - 900):call_start]
        case_matches = list(re.finditer(r"\bcase\s+([A-Za-z0-9_]+)\s*:", prefix))
        case_name = case_matches[-1].group(1) if case_matches else ""
        routes.append(
            (
                source_name,
                api,
                ",".join(normalize(arg) for arg in args[:3]),
                match.group(1),
                case_name,
            )
        )
    return routes


def parse_defines():
    text = (PEVIEW_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    return {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PV_[A-Z0-9_]+)\s+(\d+)$",
            text,
        )
    }, text


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PV_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class PeViewEnumWindowTextResourcesTests(unittest.TestCase):
    def test_all_28_switch_routes_keep_exact_case_order_and_resources(self):
        actual = {
            key: parse_switch_routes(*key)
            for key in SWITCH_ROUTES
        }
        self.assertEqual(actual, SWITCH_ROUTES)
        self.assertEqual(
            sum(
                symbol != "IDS_PV_ERROR"
                for routes in actual.values()
                for _case_name, symbol in routes
            ),
            28,
        )

        lib_source = function_body(source_text("libprp.c"), "PvpLibExportsDlgProc")
        self.assertRegex(lib_source, r"\bPCWSTR\s+type\s*;")
        self.assertNotRegex(lib_source, r"\bPWSTR\s+type\s*;")
        for function_name in ("PvpSetPeImageMachineType", "PvpSetPeImageSubsystem"):
            body = function_body(source_text("peprp.c"), function_name)
            self.assertRegex(body, r"\bPCWSTR\s+type\s*;")
            self.assertNotRegex(body, r"\bPWSTR\s+type\s*;")
        self.assertRegex(
            function_body(source_text("exlfprp.c"), "PvpSetWslImageType"),
            r"\bPCWSTR\s+type\s*=",
        )

    def test_six_direct_routes_keep_exact_api_arguments_and_case(self):
        expected_symbols = {
            symbol for symbol, _id, _en, _zh, _owner in RESOURCES
        } | {"IDS_PV_MAPPING_UNKNOWN"}
        actual = [
            route
            for source_name in ("cfgprp.c", "peexceptprp.c", "propstore.c")
            for route in parse_direct_routes(source_name)
            if route[3] in expected_symbols
        ]
        expected = [
            (source, api, normalize(arguments), symbol, case_name)
            for source, api, arguments, symbol, case_name in DIRECT_ROUTES
        ]
        self.assertEqual(Counter(actual), Counter(expected))

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for symbol, resource_id, en, zh, _owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(sorted(defines.values()), list(range(3000, 3287)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 287)
        self.assertEqual(len(chinese), 287)
        self.assertRegex(
            header,
            r"(?m)^#define IDS_PV_LAST\s+IDS_PV_RELOC_MOV32_T$",
        )
        self.assertRegex(
            header,
            r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3287$",
        )

    def test_json_uses_exact_existing_owners_without_layer_overlap(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        strings = data["strings"]
        native_strings = data["native_strings"]

        self.assertFalse(strings.keys() & native_strings.keys())
        for _symbol, _id, english, chinese, owner in RESOURCES + list(REUSED_RESOURCES):
            with self.subTest(english=english):
                table = data[owner]
                other = strings if owner == "native_strings" else native_strings
                self.assertEqual(table.get(english), chinese)
                self.assertNotIn(english, other)

    def test_ci_and_fresh_audit_boundaries_are_exact(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("peview.exe=287"), 2)
        self.assertNotIn("peview.exe=258", workflow)
        self.assertNotIn("peview.exe=247", workflow)

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
