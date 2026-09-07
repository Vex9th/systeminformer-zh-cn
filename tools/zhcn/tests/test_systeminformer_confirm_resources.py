#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


RESOURCES = (
    ("IDS_PH_CONFIRM_SELECTED_SERVICE", 2511, "the selected service", "所选服务"),
    ("IDS_PH_CONFIRM_SELECTED_SERVICES", 2512, "the selected services", "所选服务"),
    ("IDS_PH_CONFIRM_SELECTED_THREAD", 2513, "the selected thread", "所选线程"),
    ("IDS_PH_CONFIRM_SELECTED_THREADS", 2514, "the selected threads", "所选线程"),
    ("IDS_PH_ACTION_FREE", 2515, "free", "释放"),
    (
        "IDS_PH_CONFIRM_FREE_MEMORY_WARNING",
        2516,
        "Freeing memory regions may cause the process to crash.\r\n\r\n"
        "Some programs may also restrict access or ban your account when freeing the memory of the process.",
        "释放内存区域可能导致进程崩溃。\r\n\r\n"
        "某些程序还可能限制访问，或因释放进程内存而封禁您的帐户。",
    ),
    ("IDS_PH_ACTION_DECOMMIT", 2517, "decommit", "取消提交"),
    (
        "IDS_PH_CONFIRM_DECOMMIT_MEMORY_WARNING",
        2518,
        "Decommitting memory regions may cause the process to crash.\r\n\r\n"
        "Some programs may also restrict access or ban your account when decommitting the memory of the process.",
        "取消提交内存区域可能导致进程崩溃。\r\n\r\n"
        "某些程序还可能限制访问，或因取消提交进程内存而封禁您的帐户。",
    ),
    ("IDS_PH_ACTION_UNMAP", 2519, "unmap", "取消映射"),
    (
        "IDS_PH_CONFIRM_UNMAP_MEMORY_WARNING",
        2520,
        "Unmapping a section view may cause the process to crash.\r\n\r\n"
        "Some programs may also restrict access or ban your account when unmapping the memory of the process.",
        "取消映射节视图可能导致进程崩溃。\r\n\r\n"
        "某些程序还可能限制访问，或因取消映射进程内存而封禁您的帐户。",
    ),
    ("IDS_PH_CONFIRM_SELECTED_HANDLES", 2521, "the selected handles", "所选句柄"),
    ("IDS_PH_ACTION_UNLOAD", 2522, "unload", "卸载"),
    (
        "IDS_PH_CONFIRM_UNLOAD_DRIVER_WARNING",
        2523,
        "Unloading a driver may cause system instability.",
        "卸载驱动程序可能导致系统不稳定。",
    ),
    (
        "IDS_PH_CONFIRM_UNLOAD_MODULE_WARNING",
        2524,
        "Unloading a module may cause the process to crash.",
        "卸载模块可能导致进程崩溃。",
    ),
    (
        "IDS_PH_CONFIRM_UNLOAD_MODULE_COMPAT_WARNING",
        2525,
        "Unloading a module may cause the process to crash. NOTE: This feature may not work correctly on your version of Windows and some programs may restrict access or ban your account.",
        "卸载模块可能导致进程崩溃。注意：此功能可能无法在您的 Windows 版本上正常工作，某些程序可能会限制访问或封禁您的帐户。",
    ),
    (
        "IDS_PH_CONFIRM_UNMAP_SECTION_WARNING",
        2526,
        "Unmapping a section view may cause the process to crash.",
        "取消映射节视图可能导致进程崩溃。",
    ),
)

RESOURCE_BY_ENGLISH = {english: symbol for symbol, _id, english, _zh in RESOURCES}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("confirm_resource_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
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
                return source[opening + 1 : index]

    raise AssertionError(f"unterminated function: {name}")


def parse_stringtable(path: pathlib.Path):
    text = path.read_text(encoding="utf-8-sig")
    values = {}
    for symbol, value in re.findall(
        r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
    ):
        values[symbol] = (
            value.replace('""', '"').replace(r"\r", "\r").replace(r"\n", "\n")
        )
    return values


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def call_arguments(source: str, function: str, call: str, audit):
    body = function_body(source, function, audit)
    return [
        tuple(compact(argument) for argument in arguments)
        for name, arguments, _spans, _start in audit.find_calls(body, {call})
        if name == call
    ]


class SystemInformerConfirmResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.actions = (APP_ROOT / "actions.c").read_text(encoding="utf-8-sig")
        cls.findobj = (APP_ROOT / "findobj.c").read_text(encoding="utf-8-sig")

    def test_resource_contract_is_exact_and_contiguous(self) -> None:
        self.assertEqual(len(RESOURCES), 16)
        self.assertEqual([resource_id for _symbol, resource_id, *_ in RESOURCES], list(range(2511, 2527)))

        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        app_header = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, english_text, chinese_text in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(english.get(symbol), english_text)
                self.assertEqual(chinese.get(symbol), chinese_text)

        definitions = re.findall(
            r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)\s*$",
            header + "\n" + app_header,
        )
        resource_ids = {}
        for symbol, value in definitions:
            value = int(value)
            if symbol in resource_ids:
                self.assertEqual(resource_ids[symbol], value)
            resource_ids[symbol] = value
        self.assertEqual(sorted(resource_ids.values()), list(range(2000, 3370)))
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_MENU_COLLAPSE_ALL_PLAIN$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3370$")
        self.assertEqual(len(english), 1370)
        self.assertEqual(len(chinese), 1370)

    def test_json_and_ci_have_exact_native_ownership(self) -> None:
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        self.assertFalse(translations["strings"].keys() & translations["native_strings"].keys())

        for _symbol, _resource_id, english, chinese in RESOURCES:
            with self.subTest(english=english):
                self.assertEqual(translations["native_strings"].get(english), chinese)
                self.assertNotIn(english, translations["strings"])

        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("sys_info.exe=1370"), 2)
        self.assertNotIn("sys_info.exe=511", workflow)

    def test_exact_confirm_routes_preserve_dynamic_object_boundary(self) -> None:
        actions = self.audit.mask_c_comments(self.actions)
        findobj = self.audit.mask_c_comments(self.findobj)

        service = function_body(actions, "PhpShowContinueMessageServices", self.audit)
        self.assertRegex(
            service,
            r"(?s)if\s*\(NumberOfServices\s*==\s*1\).*?"
            r"object\s*=\s*PhGetApplicationUiString\(IDS_PH_CONFIRM_SELECTED_SERVICE\).*?"
            r"else.*?object\s*=\s*PhGetApplicationUiString\(IDS_PH_CONFIRM_SELECTED_SERVICES\)",
        )
        self.assertIn("PhShowConfirmMessage(", service)
        self.assertNotIn("PhShowConfirmMessageRawObject(", service)

        threads = function_body(actions, "PhpShowContinueMessageThreads", self.audit)
        self.assertRegex(
            threads,
            r"(?s)if\s*\(NumberOfThreads\s*==\s*1\).*?"
            r"object\s*=\s*PhGetApplicationUiString\(IDS_PH_CONFIRM_SELECTED_THREAD\).*?"
            r"else.*?object\s*=\s*PhGetApplicationUiString\(IDS_PH_CONFIRM_SELECTED_THREADS\)",
        )
        self.assertIn("PhShowConfirmMessage(", threads)
        self.assertNotIn("PhShowConfirmMessageRawObject(", threads)

        memory = function_body(actions, "PhUiFreeMemory", self.audit)
        for symbol in (
            "IDS_PH_ACTION_FREE",
            "IDS_PH_CONFIRM_FREE_MEMORY_WARNING",
            "IDS_PH_ACTION_DECOMMIT",
            "IDS_PH_CONFIRM_DECOMMIT_MEMORY_WARNING",
            "IDS_PH_ACTION_UNMAP",
            "IDS_PH_CONFIRM_UNMAP_MEMORY_WARNING",
        ):
            self.assertEqual(memory.count(f"PhGetApplicationUiString({symbol})"), 1)
        self.assertRegex(memory, r"\bPCWSTR\s+verb\s*;")
        self.assertRegex(memory, r"\bPCWSTR\s+message\s*;")
        self.assertIn("PhShowConfirmMessage(", memory)

        unload = function_body(actions, "PhUiUnloadModule", self.audit)
        self.assertEqual(unload.count("PhGetApplicationUiString(IDS_PH_ACTION_UNLOAD)"), 2)
        self.assertEqual(unload.count("PhGetApplicationUiString(IDS_PH_ACTION_UNMAP)"), 1)
        for symbol in (
            "IDS_PH_CONFIRM_UNLOAD_DRIVER_WARNING",
            "IDS_PH_CONFIRM_UNLOAD_MODULE_WARNING",
            "IDS_PH_CONFIRM_UNLOAD_MODULE_COMPAT_WARNING",
            "IDS_PH_CONFIRM_UNMAP_SECTION_WARNING",
        ):
            self.assertEqual(unload.count(f"PhGetApplicationUiString({symbol})"), 1)
        self.assertRegex(unload, r"\bPCWSTR\s+verb\s*;")
        self.assertRegex(unload, r"\bPCWSTR\s+message\s*;")
        self.assertIn("PhShowConfirmMessageRawObject(", unload)

        for source, function in (
            (actions, "PhUiCloseHandles"),
            (findobj, "PhFindObjectsDlgProc"),
        ):
            body = function_body(source, function, self.audit)
            self.assertRegex(
                body,
                r"==\s*1\s*\?\s*PhGetApplicationUiString\(IDS_PH_CONFIRM_SELECTED_HANDLE\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_CONFIRM_SELECTED_HANDLES\)",
            )
            self.assertIn("PhShowConfirmMessage(", body)

        self.assertEqual(actions.count("PhGetApplicationUiString(IDS_PH_ACTION_UNMAP)"), 2)
        self.assertEqual(actions.count("PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLES)"), 1)
        self.assertEqual(findobj.count("PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLES)"), 1)

        self.assertEqual(
            call_arguments(
                actions, "PhpShowContinueMessageServices", "PhShowConfirmMessage", self.audit
            ),
            [
                (
                    "WindowHandle",
                    "PhGetApplicationUiString(VerbId)",
                    "object",
                    "PhGetApplicationUiString(MessageId)",
                    "Warning",
                )
            ],
        )
        self.assertEqual(
            call_arguments(
                actions, "PhpShowContinueMessageThreads", "PhShowConfirmMessage", self.audit
            ),
            [("WindowHandle", "Verb", "object", "Message", "Warning")],
        )
        self.assertEqual(
            call_arguments(actions, "PhUiFreeMemory", "PhShowConfirmMessage", self.audit),
            [("WindowHandle", "verb", "PhGetApplicationUiString(IDS_PH_CONFIRM_MEMORY_REGION)", "message", "TRUE")],
        )
        self.assertEqual(
            call_arguments(
                actions, "PhUiUnloadModule", "PhShowConfirmMessageRawObject", self.audit
            ),
            [("WindowHandle", "verb", "Module->Name->Buffer", "message", "TRUE")],
        )
        self.assertEqual(
            call_arguments(actions, "PhUiUnloadModule", "PhShowConfirmMessage", self.audit),
            [],
        )

        handle_object = (
            "NumberOfHandles==1?PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLE):"
            "PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLES)"
        )
        self.assertEqual(
            call_arguments(actions, "PhUiCloseHandles", "PhShowConfirmMessage", self.audit),
            [
                (
                    "WindowHandle",
                    "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)",
                    handle_object,
                    "PhGetApplicationUiString(IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING)",
                    "FALSE",
                ),
                (
                    "WindowHandle",
                    "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)",
                    "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_PROCESS_HANDLES)",
                    "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING)",
                    "TRUE",
                ),
            ],
        )
        find_object = (
            "numberOfHandleObjectNodes==1?PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLE):"
            "PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLES)"
        )
        self.assertEqual(
            call_arguments(findobj, "PhFindObjectsDlgProc", "PhShowConfirmMessage", self.audit),
            [
                (
                    "hwndDlg",
                    "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)",
                    find_object,
                    "PhGetApplicationUiString(IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING)",
                    "FALSE",
                ),
                (
                    "hwndDlg",
                    "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)",
                    "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_HANDLES)",
                    "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING)",
                    "TRUE",
                ),
            ],
        )

        expected_uses = Counter({symbol: 1 for symbol, *_ in RESOURCES})
        expected_uses.update(
            {
                "IDS_PH_CONFIRM_SELECTED_SERVICE": 1,
                "IDS_PH_CONFIRM_SELECTED_SERVICES": 1,
                "IDS_PH_ACTION_UNMAP": 1,
                "IDS_PH_ACTION_UNLOAD": 1,
                "IDS_PH_CONFIRM_SELECTED_HANDLES": 1,
            }
        )
        all_uses = Counter(
            re.findall(
                r"PhGetApplicationUiString\((IDS_PH_[A-Z0-9_]+)\)",
                actions + findobj,
            )
        )
        self.assertEqual(
            Counter({symbol: all_uses[symbol] for symbol in expected_uses}),
            expected_uses,
        )
        self.assertEqual(sum(expected_uses.values()), 21)

    def test_fresh_scan_has_no_untranslated_target_confirm_text(self) -> None:
        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "actions.c"), entries)
        self.audit.scan_c_file(str(APP_ROOT / "findobj.c"), entries)

        target = set(RESOURCE_BY_ENGLISH)
        remaining = [
            (entry["english"], entry["file"], entry["line"])
            for entry in entries
            if entry["category"] == "c_confirm" and entry["english"] in target
        ]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
