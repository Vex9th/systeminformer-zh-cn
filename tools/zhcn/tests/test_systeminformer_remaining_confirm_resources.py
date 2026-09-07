#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_CONFIRM_SELECTED_HANDLE", 2957, "the selected handle", "所选句柄"),
    ("IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING", 2958, "Closing handles may cause system instability and data corruption.", "关闭句柄可能导致系统不稳定和数据损坏。"),
    ("IDS_PH_CONFIRM_CRITICAL_PROCESS_HANDLES", 2959, "critical process handle(s)", "关键进程的句柄"),
    ("IDS_PH_CONFIRM_CRITICAL_HANDLES", 2960, "critical handle(s)", "关键句柄"),
    ("IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING", 2961, "You are about to close one or more handles for a critical process with strict handle checks enabled. This will shut down the operating system immediately.\r\n\r\n", "你即将关闭一个或多个关键进程的句柄，而该进程已启用严格句柄检查。这将导致操作系统立即关机。\r\n\r\n"),
    ("IDS_PH_CONFIRM_SELECTED_PRIVILEGES", 2962, "the selected privilege(s)", "所选特权"),
    ("IDS_PH_CONFIRM_UIACCESS_FLAG", 2963, "the UIAccess flag", "UIAccess 标志"),
    ("IDS_PH_CONFIRM_INTEGRITY_LEVEL", 2964, "the integrity level", "完整性级别"),
    ("IDS_PH_CONFIRM_LOWER_INTEGRITY_WARNING", 2965, "Once lowered, the integrity level of the token cannot be raised again.", "令牌的完整性级别一旦降低，便无法再次提升。"),
    ("IDS_PH_ACTION_LOAD", 2966, "load", "加载"),
    ("IDS_PH_CONFIRM_MODULE_OBJECT", 2967, "a module", "模块"),
    ("IDS_PH_CONFIRM_LOAD_MODULE_WARNING", 2968, "Some programs may restrict access or ban your account when loading modules into the process.", "向进程加载模块时，某些程序可能会限制访问或封禁你的账户。"),
    ("IDS_PH_ACTION_UPDATE", 2969, "update", "更新"),
    ("IDS_PH_CONFIRM_INTEGRITY_LABEL", 2970, "the integrity label", "完整性标签"),
    ("IDS_PH_CONFIRM_INTEGRITY_LABEL_WARNING", 2971, "Altering the integrity label for a process may produce undesirable results, instability or data corruption.", "更改进程的完整性标签可能产生不良后果，导致系统不稳定或数据损坏。"),
    ("IDS_PH_CONFIRM_TERMINATE_PROCESS_TREE_WARNING", 2972, "Terminating a process tree will cause the process and its descendants to be terminated.", "终止进程树将使该进程及其子进程一并终止。"),
    ("IDS_PH_CONFIRM_SUSPEND_PROCESS_TREE_WARNING", 2973, "Suspending a process tree will cause the process and its descendants to be suspended.", "挂起进程树将使该进程及其子进程一并挂起。"),
    ("IDS_PH_CONFIRM_RESUME_PROCESS_TREE_WARNING", 2974, "Resuming a process tree will cause the process and its descendants to be resumed.", "恢复进程树将使该进程及其子进程一并恢复。"),
    ("IDS_PH_CONFIRM_FREEZE_PROCESS_WARNING", 2975, "Freezing does not persist after exiting System Informer.", "冻结状态在退出 sys_info 后不会保留。"),
    ("IDS_PH_CONFIRM_MEMORY_REGION", 2976, "the memory region", "该内存区域"),
    ("IDS_PH_CONFIRM_PROCESS_VIRTUALIZATION", 2977, "virtualization for the process", "该进程的虚拟化"),
    ("IDS_PH_CONFIRM_PROCESS_CRITICAL_STATUS", 2978, "critical status on the process", "该进程的关键状态"),
    ("IDS_PH_CONFIRM_THREAD_CRITICAL_STATUS", 2979, "critical status on the thread", "该线程的关键状态"),
    ("IDS_PH_CONFIRM_CRITICAL_STATUS_WARNING", 2980, "If the process ends, the operating system will shut down immediately.", "该进程一旦结束，操作系统将立即关机。"),
    ("IDS_PH_CONFIRM_PROCESS_ECO_MODE", 2981, "Eco mode for this process", "此进程的生态模式"),
    ("IDS_PH_CONFIRM_ECO_MODE_WARNING", 2982, "Eco mode will lower process priority and improve power efficiency but may cause instability in some processes.", "生态模式会降低进程优先级并提高能效，但可能导致某些进程不稳定。"),
    ("IDS_PH_CONFIRM_EXECUTION_REQUIRED_WARNING", 2983, "The process continues to run instead of being suspended or terminated by process lifetime management (PLM).", "该进程将继续运行，而不会被进程生命周期管理 (PLM) 挂起或终止。"),
)

EXISTING_RESOURCES = {
    "close": "IDS_PH_ACTION_CLOSE_HANDLE",
    "remove": "IDS_PH_ACTION_REMOVE",
    "set": "IDS_PH_ACTION_SET",
    "freeze": "IDS_PH_ACTION_FREEZE",
    "delete": "IDS_PH_ACTION_DELETE",
    "enable": "IDS_PH_ACTION_ENABLE",
    "disable": "IDS_PH_ACTION_DISABLE",
}

EXPECTED_ROUTES = {
    "actions.c": {
        "IDS_PH_CONFIRM_SELECTED_HANDLE": 1,
        "IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING": 1,
        "IDS_PH_CONFIRM_CRITICAL_PROCESS_HANDLES": 1,
        "IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING": 1,
        "IDS_PH_CONFIRM_TERMINATE_PROCESS_TREE_WARNING": 1,
        "IDS_PH_CONFIRM_SUSPEND_PROCESS_TREE_WARNING": 1,
        "IDS_PH_CONFIRM_RESUME_PROCESS_TREE_WARNING": 1,
        "IDS_PH_CONFIRM_FREEZE_PROCESS_WARNING": 1,
        "IDS_PH_CONFIRM_PROCESS_VIRTUALIZATION": 1,
        "IDS_PH_CONFIRM_PROCESS_CRITICAL_STATUS": 2,
        "IDS_PH_CONFIRM_CRITICAL_STATUS_WARNING": 1,
        "IDS_PH_CONFIRM_PROCESS_ECO_MODE": 1,
        "IDS_PH_CONFIRM_ECO_MODE_WARNING": 1,
        "IDS_PH_CONFIRM_EXECUTION_REQUIRED_WARNING": 1,
        "IDS_PH_CONFIRM_MEMORY_REGION": 1,
    },
    "findobj.c": {
        "IDS_PH_CONFIRM_SELECTED_HANDLE": 1,
        "IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING": 1,
        "IDS_PH_CONFIRM_CRITICAL_HANDLES": 1,
        "IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING": 1,
    },
    "tokprp.c": {
        "IDS_PH_CONFIRM_SELECTED_PRIVILEGES": 1,
        "IDS_PH_CONFIRM_UIACCESS_FLAG": 1,
        "IDS_PH_CONFIRM_INTEGRITY_LEVEL": 1,
        "IDS_PH_CONFIRM_LOWER_INTEGRITY_WARNING": 1,
    },
    "prpgmod.c": {"IDS_PH_ACTION_LOAD": 1, "IDS_PH_CONFIRM_MODULE_OBJECT": 1, "IDS_PH_CONFIRM_LOAD_MODULE_WARNING": 1},
    "prpggen.c": {"IDS_PH_ACTION_UPDATE": 1, "IDS_PH_CONFIRM_INTEGRITY_LABEL": 1, "IDS_PH_CONFIRM_INTEGRITY_LABEL_WARNING": 1},
    "prpgthrd.c": {"IDS_PH_CONFIRM_THREAD_CRITICAL_STATUS": 2, "IDS_PH_CONFIRM_CRITICAL_STATUS_WARNING": 1},
}

ROUTE_CONTRACTS = (
    ("actions.c", "PhUiTerminateTreeProcess", "PhShowConfirmMessageRawObject", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_TERMINATE)", "PhaFormatString(PhGetApplicationUiString(IDS_PH_PROCESS_AND_DESCENDANTS_FORMAT),Process->ProcessName->Buffer)->Buffer", "PhGetApplicationUiString(IDS_PH_CONFIRM_TERMINATE_PROCESS_TREE_WARNING)", "FALSE")),
    ("actions.c", "PhUiSuspendTreeProcess", "PhShowConfirmMessageRawObject", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_SUSPEND)", "PhaFormatString(PhGetApplicationUiString(IDS_PH_PROCESS_AND_DESCENDANTS_FORMAT),Process->ProcessName->Buffer)->Buffer", "PhGetApplicationUiString(IDS_PH_CONFIRM_SUSPEND_PROCESS_TREE_WARNING)", "FALSE")),
    ("actions.c", "PhUiResumeTreeProcess", "PhShowConfirmMessageRawObject", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_RESUME)", "PhaFormatString(PhGetApplicationUiString(IDS_PH_PROCESS_AND_DESCENDANTS_FORMAT),Process->ProcessName->Buffer)->Buffer", "PhGetApplicationUiString(IDS_PH_CONFIRM_RESUME_PROCESS_TREE_WARNING)", "FALSE")),
    ("actions.c", "PhUiFreezeTreeProcess", "PhShowConfirmMessageRawObject", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_FREEZE)", "Process->ProcessName->Buffer", "PhGetApplicationUiString(IDS_PH_CONFIRM_FREEZE_PROCESS_WARNING)", "FALSE")),
    ("actions.c", "PhUiSetVirtualizationProcess", "PhShowConfirmMessage", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_SET)", "PhGetApplicationUiString(IDS_PH_CONFIRM_PROCESS_VIRTUALIZATION)", "PhGetApplicationUiString(IDS_PH_PROCESS_VIRTUALIZATION_WARNING)", "FALSE")),
    ("actions.c", "PhUiSetCriticalProcess", "PhShowConfirmMessage", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_ENABLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_PROCESS_CRITICAL_STATUS)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_STATUS_WARNING)", "TRUE")),
    ("actions.c", "PhUiSetCriticalProcess", "PhShowConfirmMessage", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_DISABLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_PROCESS_CRITICAL_STATUS)", "NULL", "FALSE")),
    ("actions.c", "PhUiSetEcoModeProcess", "PhShowConfirmMessage", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_ENABLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_PROCESS_ECO_MODE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_ECO_MODE_WARNING)", "FALSE")),
    ("actions.c", "PhUiSetExecutionRequiredProcess", "PhShowConfirmMessageRawAction", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_CHANGE_EXECUTION_REQUIRED)", "PhaFormatString(PhGetApplicationUiString(IDS_PH_EXECUTION_REQUIRED_ACTION_FORMAT),Process->ProcessName->Buffer)->Buffer", "PhGetApplicationUiString(IDS_PH_CONFIRM_EXECUTION_REQUIRED_WARNING)", "FALSE")),
    ("actions.c", "PhUiDeleteService", "PhShowConfirmMessageRawObject", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_DELETE)", "Service->Name->Buffer", "PhGetApplicationUiString(IDS_PH_SERVICE_DELETION_WARNING)", "TRUE")),
    ("actions.c", "PhUiFreeMemory", "PhShowConfirmMessage", ("WindowHandle", "verb", "PhGetApplicationUiString(IDS_PH_CONFIRM_MEMORY_REGION)", "message", "TRUE")),
    ("actions.c", "PhUiCloseHandles", "PhShowConfirmMessage", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)", "NumberOfHandles==1?PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLE):PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLES)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING)", "FALSE")),
    ("actions.c", "PhUiCloseHandles", "PhShowConfirmMessage", ("WindowHandle", "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_PROCESS_HANDLES)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING)", "TRUE")),
    ("findobj.c", "PhFindObjectsDlgProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)", "numberOfHandleObjectNodes==1?PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLE):PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_HANDLES)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CLOSE_HANDLE_WARNING)", "FALSE")),
    ("findobj.c", "PhFindObjectsDlgProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_CLOSE_HANDLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_HANDLES)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_HANDLE_WARNING)", "TRUE")),
    ("tokprp.c", "PhpTokenPageProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_REMOVE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_PRIVILEGES)", "PhGetApplicationUiString(IDS_PH_REMOVE_PRIVILEGES_WARNING)", "FALSE")),
    ("tokprp.c", "PhpTokenPageProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_REMOVE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_UIACCESS_FLAG)", "PhGetApplicationUiString(IDS_PH_REMOVE_UIACCESS_WARNING)", "FALSE")),
    ("tokprp.c", "PhpTokenPageProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_SET)", "PhGetApplicationUiString(IDS_PH_CONFIRM_INTEGRITY_LEVEL)", "PhGetApplicationUiString(IDS_PH_CONFIRM_LOWER_INTEGRITY_WARNING)", "FALSE")),
    ("prpgmod.c", "PhpProcessModulesDlgProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_LOAD)", "PhGetApplicationUiString(IDS_PH_CONFIRM_MODULE_OBJECT)", "PhGetApplicationUiString(IDS_PH_CONFIRM_LOAD_MODULE_WARNING)", "FALSE")),
    ("prpggen.c", "PhpProcessGeneralDlgProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_UPDATE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_INTEGRITY_LABEL)", "PhGetApplicationUiString(IDS_PH_CONFIRM_INTEGRITY_LABEL_WARNING)", "FALSE")),
    ("prpgthrd.c", "PhpProcessThreadsDlgProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_ENABLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_THREAD_CRITICAL_STATUS)", "PhGetApplicationUiString(IDS_PH_CONFIRM_CRITICAL_STATUS_WARNING)", "TRUE")),
    ("prpgthrd.c", "PhpProcessThreadsDlgProc", "PhShowConfirmMessage", ("hwndDlg", "PhGetApplicationUiString(IDS_PH_ACTION_DISABLE)", "PhGetApplicationUiString(IDS_PH_CONFIRM_THREAD_CRITICAL_STATUS)", "NULL", "FALSE")),
)

MIGRATED_KEYS = {
    *EXISTING_RESOURCES,
    *(english for _symbol, _resource_id, english, _chinese in NEW_RESOURCES),
}


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"').replace(r"\r", "\r").replace(r"\n", "\n")
        for symbol, value in re.findall(r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', path.read_text(encoding="utf-8-sig"))
    }


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("remaining_confirm_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


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


def call_arguments(source: str, function: str, call: str, audit):
    body = function_body(source, function, audit)
    return [
        tuple(compact(argument) for argument in arguments)
        for name, arguments, _spans, _start in audit.find_calls(body, {call})
        if name == call
    ]


class SystemInformerRemainingConfirmResourcesTests(unittest.TestCase):
    def test_resources_are_contiguous_bilingual_and_native_owned(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
        self.assertEqual(1423, len(english))
        self.assertEqual(1423, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_TERMINATE_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3423$")
        for en in MIGRATED_KEYS:
            self.assertIn(en, data["native_strings"])
            self.assertNotIn(en, data["strings"])

    def test_all_new_confirm_resources_are_routed(self) -> None:
        audit = load_audit_module()
        total = 0
        for file_name, expected in EXPECTED_ROUTES.items():
            source = audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            for symbol, count in expected.items():
                self.assertEqual(count, len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)), (file_name, symbol))
                total += count
        self.assertEqual(33, total)

    def test_confirm_call_argument_contracts_are_exact(self) -> None:
        audit = load_audit_module()
        sources = {}

        for file_name, function, call, expected in ROUTE_CONTRACTS:
            source = sources.setdefault(
                file_name,
                (APP_ROOT / file_name).read_text(encoding="utf-8-sig"),
            )
            with self.subTest(file=file_name, function=function, call=call, expected=expected):
                self.assertIn(expected, call_arguments(source, function, call, audit))

    def test_systeminformer_confirm_audit_is_empty(self) -> None:
        audit = load_audit_module()
        entries = []
        for path in sorted(APP_ROOT.glob("*.c")):
            audit.scan_c_file(str(path), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_confirm"])


if __name__ == "__main__":
    unittest.main()
