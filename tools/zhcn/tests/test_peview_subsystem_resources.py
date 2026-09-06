#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


# case | symbol | id | English | zh-CN
RESOURCE_DATA = r"""
IMAGE_SUBSYSTEM_NATIVE|IDS_PV_SUBSYSTEM_NATIVE|3258|Native|本机
IMAGE_SUBSYSTEM_WINDOWS_GUI|IDS_PV_SUBSYSTEM_WINDOWS_GUI|3259|Windows GUI|Windows 图形界面
IMAGE_SUBSYSTEM_WINDOWS_CUI|IDS_PV_SUBSYSTEM_WINDOWS_CUI|3260|Windows CUI|Windows 控制台
IMAGE_SUBSYSTEM_OS2_CUI|IDS_PV_SUBSYSTEM_OS2_CUI|3261|OS/2 CUI|OS/2 控制台
IMAGE_SUBSYSTEM_POSIX_CUI|IDS_PV_SUBSYSTEM_POSIX_CUI|3262|POSIX CUI|POSIX 控制台
IMAGE_SUBSYSTEM_WINDOWS_CE_GUI|IDS_PV_SUBSYSTEM_WINDOWS_CE_GUI|3263|Windows CE GUI|Windows CE 图形界面
IMAGE_SUBSYSTEM_EFI_APPLICATION|IDS_PV_SUBSYSTEM_EFI_APPLICATION|3264|EFI Application|EFI 应用程序
IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER|IDS_PV_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER|3265|EFI Boot Service Driver|EFI 启动服务驱动程序
IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER|IDS_PV_SUBSYSTEM_EFI_RUNTIME_DRIVER|3266|EFI Runtime Driver|EFI 运行时驱动程序
IMAGE_SUBSYSTEM_EFI_ROM|IDS_PV_SUBSYSTEM_EFI_ROM|3267|EFI ROM|EFI ROM
IMAGE_SUBSYSTEM_XBOX|IDS_PV_SUBSYSTEM_XBOX|3268|Xbox|Xbox
IMAGE_SUBSYSTEM_WINDOWS_BOOT_APPLICATION|IDS_PV_SUBSYSTEM_WINDOWS_BOOT_APPLICATION|3269|Windows Boot Application|Windows 启动应用程序
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (case_name, symbol, int(resource_id), english, chinese)
    for case_name, symbol, resource_id, english, chinese in RESOURCES
]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_subsystem", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def masked_source(path):
    audit = load_audit_module()
    return audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))


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


class PeViewSubsystemResourcesTests(unittest.TestCase):
    def test_switch_routes_every_subsystem_to_the_exact_resource_in_order(self):
        source = masked_source(PEVIEW_ROOT / "peprp.c")
        body = function_body(source, "PvpSetPeImageSubsystem")
        route_pattern = re.compile(
            r"\bcase\s+(IMAGE_SUBSYSTEM_[A-Z0-9_]+)\s*:\s*"
            r"type\s*=\s*PvpLoadUiString\(\s*(IDS_PV_SUBSYSTEM_[A-Z0-9_]+)\s*\)\s*;\s*"
            r"break\s*;",
            re.S,
        )
        actual = route_pattern.findall(body)
        expected = [(case_name, symbol) for case_name, symbol, *_rest in RESOURCES]

        self.assertEqual(actual, expected)
        self.assertRegex(body, r"\bPCWSTR\s+type\s*;")
        self.assertNotRegex(body, r"\bPWSTR\s+type\s*;")
        self.assertRegex(
            body,
            r"\bdefault\s*:\s*type\s*=\s*"
            r"PvpLoadUiString\(\s*IDS_PV_MAPPING_UNKNOWN\s*\)\s*;\s*break\s*;",
        )
        self.assertNotIn('L"Windows CE CUI"', body)
        self.assertNotRegex(body, r"\bcase\s+IMAGE_SUBSYSTEM_[A-Z0-9_]+\s*:\s*type\s*=\s*L\"")

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for _case_name, symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[2] for row in RESOURCES], list(range(3258, 3270)))
        self.assertEqual(sorted(defines.values()), list(range(3000, 3298)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 298)
        self.assertEqual(len(chinese), 298)
        self.assertRegex(
            header,
            r"(?m)^#define IDS_PV_LAST\s+IDS_PV_CERTIFICATE_SIZE_FORMAT$",
        )
        self.assertRegex(
            header,
            r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3298$",
        )

    def test_all_subsystem_labels_are_native_only(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        strings = data["strings"]
        native_strings = data["native_strings"]

        self.assertFalse(strings.keys() & native_strings.keys())
        for _case_name, _symbol, _id, english, chinese in RESOURCES:
            with self.subTest(english=english):
                self.assertEqual(native_strings.get(english), chinese)
                self.assertNotIn(english, strings)

    def test_ci_and_fresh_audit_boundaries_are_exact(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("peview.exe=298"), 2)
        self.assertNotIn("peview.exe=258", workflow)

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
