#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

MEMORY_PROTECTION_VALUES = (
    "Possible values:\r\n\r\n"
    "0x01 - PAGE_NOACCESS\r\n"
    "0x02 - PAGE_READONLY\r\n"
    "0x04 - PAGE_READWRITE\r\n"
    "0x08 - PAGE_WRITECOPY\r\n"
    "0x10 - PAGE_EXECUTE\r\n"
    "0x20 - PAGE_EXECUTE_READ\r\n"
    "0x40 - PAGE_EXECUTE_READWRITE\r\n"
    "0x80 - PAGE_EXECUTE_WRITECOPY\r\n"
    "Modifiers:\r\n"
    "0x100 - PAGE_GUARD\r\n"
    "0x200 - PAGE_NOCACHE\r\n"
    "0x400 - PAGE_WRITECOMBINE\r\n"
)
MEMORY_PROTECTION_VALUES_ZH = MEMORY_PROTECTION_VALUES.replace(
    "Possible values:", "可用值："
).replace("Modifiers:", "修饰符：")

ABOUT_CREDITS = (
    "Thanks to:\n"
    "    <a href=\"https://github.com/wj32\">wj32</a> - Wen Jia Liu\n"
    "    <a href=\"https://github.com/dmex\">dmex</a> - Steven G\n"
    "    <a href=\"https://github.com/jxy-s\">jxy-s</a> - Johnny Shaw\n"
    "    <a href=\"https://github.com/ionescu007\">ionescu007</a> - Alex Ionescu\n"
    "    <a href=\"https://github.com/yardenshafir\">yardenshafir</a> - Yarden Shafir\n"
    "    <a href=\"https://github.com/winsiderss/systeminformer/graphs/contributors\">Contributors</a> - thank you for your additions!\n"
    "    Donors - thank you for your support!\n\n"
    "System Informer uses the following components:\n"
    "    <a href=\"https://github.com/GameTechDev/PresentMon\">PresentMon</a> by Intel Corporation\n"
    "    <a href=\"https://github.com/michaelrsweet/mxml\">Mini-XML</a> by Michael Sweet\n"
    "    <a href=\"https://github.com/PCRE2Project/pcre2\">PCRE2</a> by Philip Hazel\n"
    "    <a href=\"https://github.com/json-c/json-c\">json-c</a> by Michael Clark\n"
    "    MD5 code by Jouni Malinen\n"
    "    SHA1 code by Filip Navara, based on code by Steve Reid\n"
)
ABOUT_CREDITS_ZH = (
    "特别感谢：\n"
    "    <a href=\"https://github.com/wj32\">wj32</a> - Wen Jia Liu\n"
    "    <a href=\"https://github.com/dmex\">dmex</a> - Steven G\n"
    "    <a href=\"https://github.com/jxy-s\">jxy-s</a> - Johnny Shaw\n"
    "    <a href=\"https://github.com/ionescu007\">ionescu007</a> - Alex Ionescu\n"
    "    <a href=\"https://github.com/yardenshafir\">yardenshafir</a> - Yarden Shafir\n"
    "    <a href=\"https://github.com/winsiderss/systeminformer/graphs/contributors\">贡献者</a> - 感谢你们的贡献！\n"
    "    捐助者 - 感谢你们的支持！\n\n"
    "sys_info 使用以下组件：\n"
    "    <a href=\"https://github.com/GameTechDev/PresentMon\">PresentMon</a>，由 Intel Corporation 开发\n"
    "    <a href=\"https://github.com/michaelrsweet/mxml\">Mini-XML</a>，由 Michael Sweet 开发\n"
    "    <a href=\"https://github.com/PCRE2Project/pcre2\">PCRE2</a>，由 Philip Hazel 开发\n"
    "    <a href=\"https://github.com/json-c/json-c\">json-c</a>，由 Michael Clark 开发\n"
    "    MD5 代码由 Jouni Malinen 编写\n"
    "    SHA1 代码由 Filip Navara 基于 Steve Reid 的代码编写\n"
)

RESOURCES = (
    ("IDS_PH_PERMISSION_ALLOW", 2562, "Allow", "允许"),
    ("IDS_PH_APP_CONTAINER_CHILD", 2563, "Child", "子级"),
    ("IDS_PH_LOCK_TYPE_CRITICAL_SECTION", 2564, "Critical section", "临界区"),
    ("IDS_PH_LINKED_TOKEN_TITLE", 2565, "Linked Token", "链接的令牌"),
    ("IDS_PH_EVENT_TYPE_NOTIFICATION", 2566, "Notification", "通知"),
    ("IDS_PH_HEAP_TYPE_NT", 2567, "NT Heap", "NT 堆"),
    ("IDS_PH_HEAP_TYPE_NT_LFH", 2568, "NT Heap (LFH)", "NT 堆（LFH）"),
    ("IDS_PH_HEAP_TYPE_NT_LOOKASIDE", 2569, "NT Heap (Lookaside)", "NT 堆（Lookaside）"),
    ("IDS_PH_LOCK_TYPE_RESOURCE", 2570, "Resource", "资源锁"),
    ("IDS_PH_HEAP_TYPE_SEGMENT", 2571, "Segment Heap", "段堆"),
    ("IDS_PH_HEAP_TYPE_SEGMENT_LFH", 2572, "Segment Heap (LFH)", "段堆（LFH）"),
    ("IDS_PH_HEAP_TYPE_SEGMENT_LOOKASIDE", 2573, "Segment Heap (Lookaside)", "段堆（Lookaside）"),
    ("IDS_PH_EVENT_TYPE_SYNCHRONIZATION", 2574, "Synchronization", "同步"),
    ("IDS_PH_MEMORY_PROTECTION_VALUES", 2575, MEMORY_PROTECTION_VALUES, MEMORY_PROTECTION_VALUES_ZH),
    ("IDS_PH_DEFAULT_TASK_MANAGER_STATUS", 2576, "System Informer is the default Task Manager:", "sys_info 是默认任务管理器："),
    ("IDS_PH_NOT_DEFAULT_TASK_MANAGER_STATUS", 2577, "System Informer is not the default Task Manager:", "sys_info 不是默认任务管理器："),
    ("IDS_PH_ABOUT_CREDITS", 2578, ABOUT_CREDITS, ABOUT_CREDITS_ZH),
    ("IDS_PH_THREAD_COUNT_VALUE_TITLE", 2579, "Value (0 = auto / unlimited)", "值（0 = 自动 / 无限制）"),
    ("IDS_PH_DEVICE_UNCLASSIFIED", 2580, "Unclassified", "未分类"),
    ("IDS_PH_DEVICE_UNNAMED", 2581, "Unnamed", "未命名"),
    ("IDS_PH_DEVICE_ARRIVED_TITLE_FORMAT", 2582, "%s Device Arrived", "%s 设备已接入"),
    ("IDS_PH_DEVICE_REMOVED_TITLE_FORMAT", 2583, "%s Device Removed", "%s 设备已移除"),
    ("IDS_PH_NATIVE_RESTART_WARNING", 2584, "This option performs a hard restart in a disorderly manner and may cause file corruption or system instability.", "此选项将执行硬重启，不会正常关闭系统，可能导致文件损坏或系统不稳定。"),
    ("IDS_PH_CRITICAL_RESTART_WARNING", 2585, "This option forces a critical restart in a disorderly manner and may cause file corruption or system instability.", "此选项将强制重启，不会正常关闭系统，可能导致文件损坏或系统不稳定。"),
    ("IDS_PH_NATIVE_SHUTDOWN_WARNING", 2586, "This option performs a hard shutdown in a disorderly manner and may cause file corruption or system instability.", "此选项将执行硬关机，不会正常关闭系统，可能导致文件损坏或系统不稳定。"),
    ("IDS_PH_CRITICAL_SHUTDOWN_WARNING", 2587, "This option forces a critical shutdown in a disorderly manner and may cause file corruption or system instability.", "此选项将强制关机，不会正常关闭系统，可能导致文件损坏或系统不稳定。"),
    ("IDS_PH_SYSTEM_PROCESS_ACTION_WARNING_FORMAT", 2588, "You are about to %s one or more system processes.", "你即将%s一个或多个系统进程。"),
    ("IDS_PH_CRITICAL_PROCESS_ACTION_WARNING_FORMAT", 2589, "You are about to %s one or more critical processes.", "你即将%s一个或多个关键进程。"),
    ("IDS_PH_CRITICAL_PROCESS_TERMINATE_WARNING_FORMAT", 2590, "You are about to %s one or more critical processes. This will shut down the operating system immediately.", "你即将%s一个或多个关键进程。这将导致操作系统立即关机。"),
    ("IDS_PH_UNKNOWN_OBJECT_TYPE_FORMAT", 2591, "(unknown: %lu)", "（未知：%lu）"),
    ("IDS_PH_ACTION_START", 2592, "start", "启动"),
    ("IDS_PH_ACTION_CONTINUE", 2593, "continue", "继续"),
    ("IDS_PH_ACTION_PAUSE", 2594, "pause", "暂停"),
    ("IDS_PH_ACTION_STOP", 2595, "stop", "停止"),
    ("IDS_PH_ACTION_DELETE", 2596, "delete", "删除"),
    ("IDS_PH_UNABLE_SERVICE_ACTION_FORMAT", 2597, 'Unable to %s service "%s".', "无法%s服务“%s”。"),
)

SOURCE_FILES = (
    "about.c", "actions.c", "heapinfo.c", "hndlprp.c", "hndlstat.c",
    "memprot.c", "memsrcht.c", "mwpgdev.c", "ntobjprp.c", "options.c",
    "prpggen.c", "srvprp.c", "syssccpu.c", "sysscio.c", "sysscmem.c",
    "tokprp.c",
)


def load_tool(name: str):
    path = REPO_ROOT / "tools" / "zhcn" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path):
    generator = load_tool("generate_native_resources")
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: generator.decode_rc_string(value)
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"\\]|\\.|"")*)"\s*$',
            text,
        )
    }


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


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


class SystemInformerRemainingUiResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_tool("audit")
        cls.sources = {
            name: cls.audit.mask_c_comments((APP_ROOT / name).read_text(encoding="utf-8-sig"))
            for name in SOURCE_FILES
        }

    def test_new_resources_have_exact_contiguous_ids_text_counts_and_ownership(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        app_header = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        self.assertEqual([row[1] for row in RESOURCES], list(range(2562, 2598)))
        for symbol, numeric_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{numeric_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                owner = "strings" if en in {"System Informer is the default Task Manager:", "delete"} else "native_strings"
                self.assertEqual(translations[owner].get(en), zh)
                self.assertNotIn(en, translations["native_strings" if owner == "strings" else "strings"])

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
        self.assertEqual(sorted(resource_ids.values()), list(range(2000, 2918)))
        self.assertEqual(len(english), 918)
        self.assertEqual(len(chinese), 918)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_MENU_CLOSE$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2918$")
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("sys_info.exe=918"), 2)
        self.assertNotIn("sys_info.exe=597", workflow)

    def test_fixed_window_text_routes_use_borrowed_or_owned_resources_correctly(self) -> None:
        exact_counts = {
            ("prpggen.c", "IDS_PH_MESSAGE_ICON_NONE"): 1,
            ("tokprp.c", "IDS_PH_TOKEN_RESOLVING"): 2,
            ("tokprp.c", "IDS_PH_LINKED_TOKEN_TITLE"): 1,
            ("tokprp.c", "IDS_PH_APP_CONTAINER_CHILD"): 1,
            ("tokprp.c", "IDS_PH_GROUP_PARENT"): 2,
            ("hndlprp.c", "IDS_PH_PERMISSION_ALLOW"): 1,
            ("ntobjprp.c", "IDS_PH_EVENT_TYPE_NOTIFICATION"): 1,
            ("ntobjprp.c", "IDS_PH_EVENT_TYPE_SYNCHRONIZATION"): 1,
            ("memprot.c", "IDS_PH_MEMORY_PROTECTION_VALUES"): 1,
            ("options.c", "IDS_PH_DEFAULT_TASK_MANAGER_STATUS"): 1,
            ("options.c", "IDS_PH_NOT_DEFAULT_TASK_MANAGER_STATUS"): 1,
            ("about.c", "IDS_PH_ABOUT_CREDITS"): 1,
            ("memsrcht.c", "IDS_PH_THREAD_COUNT_VALUE_TITLE"): 1,
        }
        for (filename, symbol), count in exact_counts.items():
            with self.subTest(filename=filename, symbol=symbol):
                self.assertEqual(self.sources[filename].count(f"PhGetApplicationUiString({symbol})"), count)

        for filename, symbol in (
            ("syssccpu.c", "IDS_PH_STAT_CPU"),
            ("sysscio.c", "IDS_PH_GROUP_IO"),
            ("sysscmem.c", "IDS_PH_GROUP_MEMORY"),
        ):
            with self.subTest(filename=filename):
                self.assertIn(
                    f"drawPanel->Title = PhCreateString(PhGetApplicationUiString({symbol}))",
                    self.sources[filename],
                )

    def assert_options_state_route_contract(self, source: str) -> None:
        body = function_body(source, "PhpRefreshTaskManagerState")
        self.assertRegex(body, re.compile(
            r"if\s*\(PhpIsDefaultTaskManager\(\)\)\s*\{.*?"
            r"IDC_DEFSTATE.*?IDS_PH_DEFAULT_TASK_MANAGER_STATUS.*?"
            r"IDS_PH_RESTORE_DEFAULT.*?\}\s*else\s*\{.*?"
            r"IDC_DEFSTATE.*?IDS_PH_NOT_DEFAULT_TASK_MANAGER_STATUS.*?"
            r"IDS_PH_MAKE_DEFAULT",
            re.S,
        ))

    def test_task_manager_state_branches_bind_default_and_not_default_resources(self) -> None:
        self.assert_options_state_route_contract(self.sources["options.c"])

    def test_task_manager_state_contract_rejects_symmetric_status_swap(self) -> None:
        source = self.sources["options.c"]
        mutated = source.replace("IDS_PH_DEFAULT_TASK_MANAGER_STATUS", "IDS_PH_TASK_MANAGER_STATUS_SWAP", 1)
        mutated = mutated.replace("IDS_PH_NOT_DEFAULT_TASK_MANAGER_STATUS", "IDS_PH_DEFAULT_TASK_MANAGER_STATUS", 1)
        mutated = mutated.replace("IDS_PH_TASK_MANAGER_STATUS_SWAP", "IDS_PH_NOT_DEFAULT_TASK_MANAGER_STATUS", 1)
        with self.assertRaises(AssertionError):
            self.assert_options_state_route_contract(mutated)

    def assert_event_type_route_contract(self, source: str) -> None:
        body = function_body(source, "PhpRefreshEventPageInfo")
        self.assertRegex(body, re.compile(
            r"switch\s*\(basicInfo\.EventType\).*?"
            r"case\s+NotificationEvent:\s*eventType\s*=\s*"
            r"PhGetApplicationUiString\(IDS_PH_EVENT_TYPE_NOTIFICATION\);\s*break;.*?"
            r"case\s+SynchronizationEvent:\s*eventType\s*=\s*"
            r"PhGetApplicationUiString\(IDS_PH_EVENT_TYPE_SYNCHRONIZATION\);\s*break;",
            re.S,
        ))

    def test_event_type_switch_binds_notification_and_synchronization_resources(self) -> None:
        self.assert_event_type_route_contract(self.sources["ntobjprp.c"])

    def test_event_type_contract_rejects_symmetric_case_resource_swap(self) -> None:
        source = self.sources["ntobjprp.c"]
        mutated = source.replace("IDS_PH_EVENT_TYPE_NOTIFICATION", "IDS_PH_EVENT_TYPE_SWAP", 1)
        mutated = mutated.replace("IDS_PH_EVENT_TYPE_SYNCHRONIZATION", "IDS_PH_EVENT_TYPE_NOTIFICATION", 1)
        mutated = mutated.replace("IDS_PH_EVENT_TYPE_SWAP", "IDS_PH_EVENT_TYPE_SYNCHRONIZATION", 1)
        with self.assertRaises(AssertionError):
            self.assert_event_type_route_contract(mutated)

    def assert_heap_route_contract(self, source: str) -> None:
        expected = {
            "IDS_PH_HEAP_TYPE_NT": 2,
            "IDS_PH_HEAP_TYPE_NT_LFH": 2,
            "IDS_PH_HEAP_TYPE_NT_LOOKASIDE": 2,
            "IDS_PH_HEAP_TYPE_SEGMENT": 2,
            "IDS_PH_HEAP_TYPE_SEGMENT_LFH": 2,
            "IDS_PH_HEAP_TYPE_SEGMENT_LOOKASIDE": 2,
            "IDS_PH_LOCK_TYPE_CRITICAL_SECTION": 1,
            "IDS_PH_LOCK_TYPE_RESOURCE": 1,
        }
        for symbol, count in expected.items():
            self.assertEqual(source.count(f"PhGetApplicationUiString({symbol})"), count)

        self.assertEqual(source.count("case RTL_HEAP_SIGNATURE:"), 2)
        self.assertEqual(source.count("case RTL_HEAP_SEGMENT_SIGNATURE:"), 2)
        compact_heap = compact(function_body(source, "PhpEnumerateProcessHeaps"))
        self.assertEqual(compact_heap.count(compact(
            "case 1: PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, 7, "
            "PhGetApplicationUiString(IDS_PH_HEAP_TYPE_NT_LOOKASIDE)); break; "
            "case 2: PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, 7, "
            "PhGetApplicationUiString(IDS_PH_HEAP_TYPE_NT_LFH)); break; "
            "default: PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, 7, "
            "PhGetApplicationUiString(IDS_PH_HEAP_TYPE_NT)); break;"
        )), 2)
        self.assertEqual(compact_heap.count(compact(
            "case 1: PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, 7, "
            "PhGetApplicationUiString(IDS_PH_HEAP_TYPE_SEGMENT_LOOKASIDE)); break; "
            "case 2: PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, 7, "
            "PhGetApplicationUiString(IDS_PH_HEAP_TYPE_SEGMENT_LFH)); break; "
            "default: PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, 7, "
            "PhGetApplicationUiString(IDS_PH_HEAP_TYPE_SEGMENT)); break;"
        )), 2)
        self.assertRegex(source, re.compile(
            r"case\s+RTL_CRITSECT_TYPE:.*?IDS_PH_LOCK_TYPE_CRITICAL_SECTION.*?"
            r"case\s+RTL_RESOURCE_TYPE:.*?IDS_PH_LOCK_TYPE_RESOURCE",
            re.S,
        ))

    def test_heap_type_and_lock_branches_keep_their_exact_routes(self) -> None:
        self.assert_heap_route_contract(self.sources["heapinfo.c"])

    def test_heap_route_contract_rejects_lfh_lookaside_swaps(self) -> None:
        source = self.sources["heapinfo.c"]
        for first, second in (
            ("IDS_PH_HEAP_TYPE_NT_LFH", "IDS_PH_HEAP_TYPE_NT_LOOKASIDE"),
            ("IDS_PH_HEAP_TYPE_SEGMENT_LFH", "IDS_PH_HEAP_TYPE_SEGMENT_LOOKASIDE"),
        ):
            mutated = source.replace(first, "IDS_PH_HEAP_TYPE_SWAP", 2)
            mutated = mutated.replace(second, first, 2)
            mutated = mutated.replace("IDS_PH_HEAP_TYPE_SWAP", second, 2)
            with self.assertRaises(AssertionError):
                self.assert_heap_route_contract(mutated)

    def assert_device_route_contract(self, source: str) -> None:
        body = function_body(source, "PhpNotifyForDevice")
        self.assertIn("classification = PhCreateString(PhGetApplicationUiString(IDS_PH_DEVICE_UNCLASSIFIED))", body)
        self.assertIn("name = PhCreateString(PhGetApplicationUiString(IDS_PH_DEVICE_UNNAMED))", body)
        compact_body = compact(body)
        removed = compact(
            "if (Type == PH_NOTIFY_DEVICE_REMOVED) { "
            "PhLogDeviceEntry(PH_LOG_ENTRY_DEVICE_REMOVED, classification, name); "
            "title = PhFormatString(PhGetApplicationUiString(IDS_PH_DEVICE_REMOVED_TITLE_FORMAT), "
            "PhGetString(classification)); }"
        )
        arrived = compact(
            "else { PhLogDeviceEntry(PH_LOG_ENTRY_DEVICE_ARRIVED, classification, name); "
            "title = PhFormatString(PhGetApplicationUiString(IDS_PH_DEVICE_ARRIVED_TITLE_FORMAT), "
            "PhGetString(classification)); }"
        )
        self.assertIn(removed + arrived, compact_body)
        self.assertRegex(body, re.compile(
            r"PhDereferenceObject\(title\).*?PhDereferenceObject\(name\).*?PhDereferenceObject\(classification\)",
            re.S,
        ))
        notify_index = body.index("PhShowIconNotificationRaw(PhGetString(title), PhGetString(name))")
        for variable in ("title", "name", "classification"):
            release = f"PhDereferenceObject({variable})"
            self.assertEqual(body.count(release), 1)
            self.assertLess(notify_index, body.index(release))

    def test_device_notification_owns_fallbacks_and_formats_each_event_branch(self) -> None:
        self.assert_device_route_contract(self.sources["mwpgdev.c"])

    def test_device_lifetime_contract_rejects_release_before_notification(self) -> None:
        source = self.sources["mwpgdev.c"]
        notify = "    if ((PhMwpNotifyIconNotifyMask & Type))\n        PhShowIconNotificationRaw(PhGetString(title), PhGetString(name));\n\n    PhDereferenceObject(title);"
        mutated = "    PhDereferenceObject(title);\n\n    if ((PhMwpNotifyIconNotifyMask & Type))\n        PhShowIconNotificationRaw(PhGetString(title), PhGetString(name));"
        self.assertIn(notify, source)
        with self.assertRaises(AssertionError):
            self.assert_device_route_contract(source.replace(notify, mutated, 1))

    def assert_action_route_contract(self, source: str) -> None:
        restart = function_body(source, "PhUiRestartComputer")
        shutdown = function_body(source, "PhUiShutdownComputer")
        process = function_body(source, "PhpShowContinueMessageProcesses")

        self.assertRegex(restart, re.compile(
            r"case\s+PH_POWERACTION_TYPE_NATIVE:.*?messageText\s*=\s*PhGetApplicationUiString\(IDS_PH_NATIVE_RESTART_WARNING\).*?"
            r"case\s+PH_POWERACTION_TYPE_CRITICAL:.*?messageText\s*=\s*PhGetApplicationUiString\(IDS_PH_CRITICAL_RESTART_WARNING\)",
            re.S,
        ))
        self.assertRegex(shutdown, re.compile(
            r"case\s+PH_POWERACTION_TYPE_NATIVE:.*?messageText\s*=\s*PhGetApplicationUiString\(IDS_PH_NATIVE_SHUTDOWN_WARNING\).*?"
            r"case\s+PH_POWERACTION_TYPE_CRITICAL:.*?messageText\s*=\s*PhGetApplicationUiString\(IDS_PH_CRITICAL_SHUTDOWN_WARNING\)",
            re.S,
        ))
        self.assertRegex(process, r"\bPCWSTR\s+verb\s*;")
        self.assertIn("verb = PhGetApplicationUiString(VerbId)", process)
        self.assertIn("PhGetApplicationUiString(IDS_PH_SYSTEM_PROCESS_ACTION_WARNING_FORMAT),\n                verb", process)
        self.assertIn("PhGetApplicationUiString(IDS_PH_CRITICAL_PROCESS_TERMINATE_WARNING_FORMAT),\n                    verb", process)
        self.assertIn("PhGetApplicationUiString(IDS_PH_CRITICAL_PROCESS_ACTION_WARNING_FORMAT),\n                    verb", process)
        self.assertIn("VerbId == IDS_PH_ACTION_TERMINATE", process)

    def test_power_and_dangerous_process_branches_use_complete_semantic_resources(self) -> None:
        self.assert_action_route_contract(self.sources["actions.c"])

    def test_action_route_contract_rejects_real_branch_and_argument_mutations(self) -> None:
        source = self.sources["actions.c"]
        for mutated in (
            source.replace("IDS_PH_NATIVE_RESTART_WARNING", "IDS_PH_CRITICAL_RESTART_WARNING", 1),
            source.replace("verb = PhGetApplicationUiString(VerbId)", "verb = L\"terminate\"", 1),
            source.replace("VerbId == IDS_PH_ACTION_TERMINATE", "VerbId == IDS_PH_ACTION_RESUME", 1),
        ):
            with self.assertRaises(AssertionError):
                self.assert_action_route_contract(mutated)

    def assert_service_route_contract(self, source: str) -> None:
        helper = function_body(source, "PhpShowErrorService")
        signature = source[source.rfind("static BOOLEAN PhpShowErrorService", 0, source.index(helper)):source.index(helper)]
        self.assertIn("_In_ ULONG VerbId", signature)
        self.assertNotIn("PWSTR Verb", signature)
        self.assertEqual(
            compact(helper),
            compact(
                "return PhShowContinueStatus(WindowHandle, "
                "PhaFormatString(PhGetApplicationUiString(IDS_PH_UNABLE_SERVICE_ACTION_FORMAT), "
                "PhGetApplicationUiString(VerbId), Service->Name->Buffer)->Buffer, "
                "Status, Win32Result);"
            ),
        )

        calls = Counter()
        for _name, arguments, _spans, _start in self.audit.find_calls(source, {"PhpShowErrorService"}):
            self.assertEqual(len(arguments), 5)
            if compact(arguments[0]) != "WindowHandle":
                continue
            calls[compact(arguments[1])] += 1
        self.assertEqual(calls, Counter({
            "IDS_PH_ACTION_START": 4,
            "IDS_PH_ACTION_CONTINUE": 4,
            "IDS_PH_ACTION_PAUSE": 4,
            "IDS_PH_ACTION_STOP": 4,
            "IDS_PH_ACTION_DELETE": 2,
            "IDS_PH_ACTION_RESTART": 2,
        }))

        expected_functions = {
            "PhUiStartServices": "IDS_PH_ACTION_START",
            "PhUiStartService": "IDS_PH_ACTION_START",
            "PhUiContinueServices": "IDS_PH_ACTION_CONTINUE",
            "PhUiContinueService": "IDS_PH_ACTION_CONTINUE",
            "PhUiPauseServices": "IDS_PH_ACTION_PAUSE",
            "PhUiPauseService": "IDS_PH_ACTION_PAUSE",
            "PhUiStopServices": "IDS_PH_ACTION_STOP",
            "PhUiStopService": "IDS_PH_ACTION_STOP",
            "PhUiDeleteService": "IDS_PH_ACTION_DELETE",
            "PhUiRestartServices": "IDS_PH_ACTION_RESTART",
        }
        for function_name, expected_id in expected_functions.items():
            body = function_body(source, function_name)
            actual = Counter()
            for _name, arguments, _spans, _start in self.audit.find_calls(body, {"PhpShowErrorService"}):
                actual[compact(arguments[1])] += 1
            self.assertEqual(actual, Counter({expected_id: 2}), function_name)

    def test_service_error_helper_uses_stable_ids_and_all_twenty_calls_map_correctly(self) -> None:
        self.assert_service_route_contract(self.sources["actions.c"])

    def test_service_route_contract_rejects_symmetric_start_continue_swap(self) -> None:
        source = self.sources["actions.c"]
        mutated = source.replace("IDS_PH_ACTION_START", "IDS_PH_ACTION_SWAP", 4)
        mutated = mutated.replace("IDS_PH_ACTION_CONTINUE", "IDS_PH_ACTION_START", 4)
        mutated = mutated.replace("IDS_PH_ACTION_SWAP", "IDS_PH_ACTION_CONTINUE", 4)
        with self.assertRaises(AssertionError):
            self.assert_service_route_contract(mutated)

    def test_five_permission_error_fallbacks_reuse_not_available_without_changing_formats(self) -> None:
        source = self.sources["hndlprp.c"]
        bodies = {
            "PhAddStatusPermissionsTrustee": function_body(source, "PhAddStatusPermissionsTrustee"),
            "PhUpdateHandlePermissionSecurity": function_body(source, "PhUpdateHandlePermissionSecurity"),
            "PhUpdateHandleAuditingSecurity": function_body(source, "PhUpdateHandleAuditingSecurity"),
        }
        self.assertEqual(bodies["PhAddStatusPermissionsTrustee"].count("PhGetApplicationUiString(IDS_PH_NOT_AVAILABLE)"), 1)
        fallback = "PhGetStringOrDefault(string, PhGetApplicationUiString(IDS_PH_NOT_AVAILABLE))"
        self.assertEqual(bodies["PhUpdateHandlePermissionSecurity"].count(fallback), 2)
        self.assertEqual(bodies["PhUpdateHandleAuditingSecurity"].count(fallback), 2)
        for body in bodies.values():
            self.assertNotIn('PhGetStringOrDefault(string, L"N/A")', body)
            self.assertEqual(body.count('PhFormatString(L"0x%x: %s"'), body.count(fallback))

    def test_intentional_technical_literals_and_runtime_lifetimes_are_preserved(self) -> None:
        self.assertEqual(self.sources["prpggen.c"].count(r'L"\u221E"'), 1)
        self.assertEqual(self.sources["srvprp.c"].count('L"password"'), 0)
        self.assertEqual(
            self.sources["srvprp.c"].count(
                "PhGetApplicationUiString(IDS_PH_SERVICE_PASSWORD_PLACEHOLDER)"
            ),
            1,
        )
        actions = self.sources["actions.c"]
        self.assertEqual(actions.count('L"%s ago (%s)"'), 0)
        self.assertEqual(self.sources["ntobjprp.c"].count('L"%s ago (%s)"'), 1)
        for filename, literal, count in (
            ("tokprp.c", 'L" (APP_CONTAINER)"', 2),
            ("hndlprp.c", 'L"0x%x: %s"', 9),
        ):
            self.assertEqual(self.sources[filename].count(literal), count)

        self.assertNotIn("PhaFormatString(\n                L\"This option", actions)
        self.assertNotIn("PhaConcatStrings(\n                3,\n                L\"You are about to \",", actions)
        self.assertNotIn('PhFormatString(L"(unknown: %lu)"', self.sources["hndlstat.c"])

    def test_fresh_main_scan_contains_only_the_intentional_window_and_runtime_residuals(self) -> None:
        entries = []
        for path in sorted(APP_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)

        window_text = Counter(
            entry["english"] for entry in entries if entry["category"] == "c_window_text"
        )
        runtime_composed = Counter(
            entry["english"] for entry in entries if entry["category"] == "c_runtime_composed"
        )
        self.assertEqual(window_text, Counter())
        self.assertEqual(runtime_composed, Counter({
            " (APP_CONTAINER)": 1,
            "%lu: %s\\%s": 1,
            "%s (%u)": 1,
            "%s (%u) (0x%Ix - 0x%Ix)": 1,
            "%ux%u@%u": 1,
            "0x%x: %s": 6,
        }))


if __name__ == "__main__":
    unittest.main()
