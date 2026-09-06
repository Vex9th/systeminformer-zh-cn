#!/usr/bin/env python3
"""Regression coverage for UserNotes priority TaskDialog resources."""

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "UserNotes"
SOURCE_PATH = PLUGIN_ROOT / "main.c"


RESOURCE_DATA = (
    ("IDS_UN_BUTTON_SAVE", 2020, "Save", "保存"),
    ("IDS_UN_BUTTON_CANCEL", 2021, "Cancel", "取消"),
    ("IDS_UN_PRIORITY_REALTIME", 2022, "Realtime", "实时"),
    ("IDS_UN_PRIORITY_HIGH", 2023, "High", "高"),
    ("IDS_UN_PRIORITY_ABOVE_NORMAL", 2024, "Above normal", "高于正常"),
    ("IDS_UN_PRIORITY_NORMAL", 2025, "Normal", "正常"),
    ("IDS_UN_PRIORITY_BELOW_NORMAL", 2026, "Below normal", "低于正常"),
    ("IDS_UN_PRIORITY_IDLE", 2027, "Idle", "空闲"),
    ("IDS_UN_PRIORITY_LOW", 2028, "Low", "低"),
    ("IDS_UN_PRIORITY_VERY_LOW", 2029, "Very low", "极低"),
    ("IDS_UN_PRIORITY_MEDIUM", 2030, "Medium", "中"),
    (
        "IDS_UN_PROCESS_PRIORITY_INSTRUCTION",
        2031,
        "Select the default process priority.",
        "选择默认进程优先级。",
    ),
    (
        "IDS_UN_PROCESS_PRIORITY_CONTENT",
        2032,
        "The process priority will be applied by Windows even when System Informer isn't currently running. Note: Realtime priority requires the User has the SeIncreaseBasePriorityPrivilege or the process running as Administrator.",
        "即使 sys_info 当前未运行，Windows 也会应用该进程优先级。注意：实时优先级要求用户拥有 SeIncreaseBasePriorityPrivilege 特权，或者进程以管理员身份运行。",
    ),
    (
        "IDS_UN_IO_PRIORITY_INSTRUCTION",
        2033,
        "Select the default process IO priority.",
        "选择默认进程 I/O 优先级。",
    ),
    (
        "IDS_UN_IO_PRIORITY_CONTENT",
        2034,
        "The IO priority will be applied by Windows even when System Informer isn't currently running. Note: High IO priority requires the User has the SeIncreaseBasePriorityPrivilege or the process running as Administrator.",
        "即使 sys_info 当前未运行，Windows 也会应用该 I/O 优先级。注意：高 I/O 优先级要求用户拥有 SeIncreaseBasePriorityPrivilege 特权，或者进程以管理员身份运行。",
    ),
    (
        "IDS_UN_PAGE_PRIORITY_INSTRUCTION",
        2035,
        "Select the default process page priority.",
        "选择默认进程页面优先级。",
    ),
    (
        "IDS_UN_PAGE_PRIORITY_CONTENT",
        2036,
        "The page priority will be applied by Windows even when System Informer isn't currently running.",
        "即使 sys_info 当前未运行，Windows 也会应用该页面优先级。",
    ),
    (
        "IDS_UN_D3DKMT_PRIORITY_TITLE",
        2037,
        "D3DKMT scheduling priority",
        "D3DKMT 调度优先级",
    ),
    (
        "IDS_UN_GRAPHICS_PRIORITY_INSTRUCTION",
        2038,
        "Select the graphics scheduling priority.",
        "选择图形调度优先级。",
    ),
    (
        "IDS_UN_REALTIME_PRIORITY_NOTE",
        2039,
        "Note: Realtime priority requires the User has the SeIncreaseBasePriorityPrivilege or the process running as Administrator.",
        "注意：实时优先级要求用户拥有 SeIncreaseBasePriorityPrivilege 特权，或者进程以管理员身份运行。",
    ),
)


DIALOG_ROUTES = {
    "ShowProcessPriorityDialog": (
        (
            ("PHAPP_ID_PRIORITY_REALTIME", "IDS_UN_PRIORITY_REALTIME"),
            ("PHAPP_ID_PRIORITY_HIGH", "IDS_UN_PRIORITY_HIGH"),
            ("PHAPP_ID_PRIORITY_ABOVENORMAL", "IDS_UN_PRIORITY_ABOVE_NORMAL"),
            ("PHAPP_ID_PRIORITY_NORMAL", "IDS_UN_PRIORITY_NORMAL"),
            ("PHAPP_ID_PRIORITY_BELOWNORMAL", "IDS_UN_PRIORITY_BELOW_NORMAL"),
            ("PHAPP_ID_PRIORITY_IDLE", "IDS_UN_PRIORITY_IDLE"),
        ),
        "IDS_UN_PROCESS_PRIORITY_INSTRUCTION",
        "IDS_UN_PROCESS_PRIORITY_CONTENT",
    ),
    "ShowProcessIoPriorityDialog": (
        (
            ("PHAPP_ID_IOPRIORITY_HIGH", "IDS_UN_PRIORITY_HIGH"),
            ("PHAPP_ID_IOPRIORITY_NORMAL", "IDS_UN_PRIORITY_NORMAL"),
            ("PHAPP_ID_IOPRIORITY_LOW", "IDS_UN_PRIORITY_LOW"),
            ("PHAPP_ID_IOPRIORITY_VERYLOW", "IDS_UN_PRIORITY_VERY_LOW"),
        ),
        "IDS_UN_IO_PRIORITY_INSTRUCTION",
        "IDS_UN_IO_PRIORITY_CONTENT",
    ),
    "ShowProcessPagePriorityDialog": (
        (
            ("PHAPP_ID_PAGEPRIORITY_NORMAL", "IDS_UN_PRIORITY_NORMAL"),
            ("PHAPP_ID_PAGEPRIORITY_BELOWNORMAL", "IDS_UN_PRIORITY_BELOW_NORMAL"),
            ("PHAPP_ID_PAGEPRIORITY_MEDIUM", "IDS_UN_PRIORITY_MEDIUM"),
            ("PHAPP_ID_PAGEPRIORITY_LOW", "IDS_UN_PRIORITY_LOW"),
            ("PHAPP_ID_PAGEPRIORITY_VERYLOW", "IDS_UN_PRIORITY_VERY_LOW"),
        ),
        "IDS_UN_PAGE_PRIORITY_INSTRUCTION",
        "IDS_UN_PAGE_PRIORITY_CONTENT",
    ),
    "ShowProcessD3DKMTPriorityDialog": (
        (
            ("D3DKMT_SCHEDULINGPRIORITYCLASS_REALTIME", "IDS_UN_PRIORITY_REALTIME"),
            ("D3DKMT_SCHEDULINGPRIORITYCLASS_HIGH", "IDS_UN_PRIORITY_HIGH"),
            ("D3DKMT_SCHEDULINGPRIORITYCLASS_ABOVE_NORMAL", "IDS_UN_PRIORITY_ABOVE_NORMAL"),
            ("D3DKMT_SCHEDULINGPRIORITYCLASS_NORMAL", "IDS_UN_PRIORITY_NORMAL"),
            ("D3DKMT_SCHEDULINGPRIORITYCLASS_BELOW_NORMAL", "IDS_UN_PRIORITY_BELOW_NORMAL"),
            ("D3DKMT_SCHEDULINGPRIORITYCLASS_IDLE", "IDS_UN_PRIORITY_IDLE"),
        ),
        "IDS_UN_GRAPHICS_PRIORITY_INSTRUCTION",
        "IDS_UN_REALTIME_PRIORITY_NOTE",
    ),
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("usernotes_taskdialog_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.S)
    if match is None:
        raise AssertionError(f"function not found: {name}")
    opening = source.find("{", match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated function: {name}")


def parse_stringtable(path: pathlib.Path):
    return {
        symbol: value.replace('""', '"').replace(r"\n", "\n")
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_UN_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


def resource_getter(resource: str) -> str:
    return (
        r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
        rf"PluginInstance->DllBase\s*,\s*{resource}\s*,\s*NULL\s*\)\)\)"
    )


class UserNotesTaskDialogNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            SOURCE_PATH.read_text(encoding="utf-8-sig")
        )

    def test_resources_are_exact_contiguous_and_bilingual(self):
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_UN_[A-Z0-9_]+)\s+(\d+)$",
                header,
            )
        }
        english = parse_stringtable(PLUGIN_ROOT / "UserNotes.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "UserNotes.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCE_DATA], list(range(2020, 2040)))
        self.assertEqual(sorted(defines.values()), list(range(2000, 2052)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 52)
        self.assertEqual(len(chinese), 52)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2052$")

    def test_four_dialogs_use_exact_local_resource_backed_arrays_and_prompts(self):
        for function_name, (radio_routes, instruction, content) in DIALOG_ROUTES.items():
            with self.subTest(function=function_name):
                body = function_body(self.source, function_name)
                self.assertNotRegex(body, r"static\s+TASKDIALOG_BUTTON")
                radio_block = re.search(
                    r"TASKDIALOG_BUTTON\s+TaskDialogRadioButtonArray\[\]\s*=\s*\{(.*?)\}\s*;",
                    body,
                    re.S,
                )
                self.assertIsNotNone(radio_block)
                expected = tuple(
                    re.findall(
                        r"\{\s*([A-Z0-9_]+)\s*,\s*"
                        r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
                        r"PluginInstance->DllBase\s*,\s*(IDS_UN_[A-Z0-9_]+)\s*,\s*"
                        r"NULL\s*\)\)\)\s*\}",
                        radio_block.group(1),
                        re.S,
                    )
                )
                self.assertEqual(expected, radio_routes)

                self.assertRegex(
                    body,
                    r"TASKDIALOG_BUTTON\s+TaskDialogButtonArray\[\]\s*=\s*\{\s*"
                    r"\{\s*IDYES\s*,\s*" + resource_getter("IDS_UN_BUTTON_SAVE") + r"\s*\}\s*,\s*"
                    r"\{\s*IDCANCEL\s*,\s*" + resource_getter("IDS_UN_BUTTON_CANCEL") + r"\s*\}\s*,?\s*"
                    r"\}\s*;",
                )
                self.assertRegex(
                    body,
                    r"config\.pszMainInstruction\s*=\s*" + resource_getter(instruction) + r"\s*;",
                )
                self.assertRegex(
                    body,
                    r"config\.pszContent\s*=\s*" + resource_getter(content) + r"\s*;",
                )
                show_index = body.index("PhShowTaskDialog(&config")
                self.assertLess(body.index("TaskDialogRadioButtonArray"), show_index)
                self.assertLess(body.index("TaskDialogButtonArray"), show_index)

        d3d = function_body(self.source, "ShowProcessD3DKMTPriorityDialog")
        self.assertRegex(
            d3d,
            r"config\.pszWindowTitle\s*=\s*" + resource_getter("IDS_UN_D3DKMT_PRIORITY_TITLE") + r"\s*;",
        )

    def test_error_pages_reuse_existing_ifeo_priority_resource(self):
        callback = function_body(self.source, "TaskDialogBootstrapCallback")
        self.assertEqual(callback.count("IDS_UN_UNABLE_UPDATE_IFEO_PRIORITY"), 3)
        self.assertEqual(callback.count("PhTaskDialogNavigatePage(WindowHandle, &config);"), 3)
        self.assertNotIn("Unable to update the IFEO key for priority.", callback)

    def test_target_literals_leave_fresh_taskdialog_scan(self):
        entries = []
        self.audit.scan_c_file(str(SOURCE_PATH), entries)
        remaining = Counter(
            (entry["category"], entry["english"])
            for entry in entries
            if entry["category"] in {"c_taskdialog", "c_taskdialog_raw"}
        )
        self.assertEqual(remaining, Counter())

        source_routes = Counter(re.findall(r"\b(IDS_UN_[A-Z0-9_]+)\b", self.source))
        expected_routes = Counter({
            "IDS_UN_BUTTON_SAVE": 4,
            "IDS_UN_BUTTON_CANCEL": 4,
            "IDS_UN_PRIORITY_REALTIME": 2,
            "IDS_UN_PRIORITY_HIGH": 3,
            "IDS_UN_PRIORITY_ABOVE_NORMAL": 2,
            "IDS_UN_PRIORITY_NORMAL": 4,
            "IDS_UN_PRIORITY_BELOW_NORMAL": 3,
            "IDS_UN_PRIORITY_IDLE": 2,
            "IDS_UN_PRIORITY_LOW": 2,
            "IDS_UN_PRIORITY_VERY_LOW": 2,
            "IDS_UN_PRIORITY_MEDIUM": 1,
            **{row[0]: 1 for row in RESOURCE_DATA[11:]},
        })
        self.assertEqual(
            Counter({key: source_routes[key] for key in expected_routes}),
            expected_routes,
        )


if __name__ == "__main__":
    unittest.main()
