#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SYSTEM_INFORMER_ROOT = REPO_ROOT / "SystemInformer"


# symbol | id | English | zh-CN
NEW_RESOURCE_DATA = r"""
IDS_PH_GROUP_PROCESSES|2464|Processes|进程
IDS_PH_GROUP_THREADS|2465|Threads|线程
IDS_PH_GROUP_ENVIRONMENT|2466|Environment|环境
IDS_PH_GROUP_WMI|2467|WMI|WMI
IDS_PH_GROUP_TOKEN|2468|Token|令牌
IDS_PH_GROUP_MEMORY|2469|Memory|内存
IDS_PH_GROUP_MODULES|2470|Modules|模块
IDS_PH_GROUP_SERVICES|2471|Services|服务
IDS_PH_GROUP_IO|2472|I/O|I/O
IDS_PH_GROUP_USER|2473|User|用户
IDS_PH_GROUP_SYSTEM|2474|System|系统
IDS_PH_GROUP_BASIC_INFORMATION|2475|Basic information|基本信息
IDS_PH_GROUP_SECURITY_INFORMATION|2476|Security information|安全信息
IDS_PH_GROUP_REFERENCES|2477|References|引用数
IDS_PH_GROUP_QUOTA_CHARGES|2478|Quota charges|配额占用
IDS_PH_GROUP_ALPC_PORT|2479|ALPC Port|ALPC 端口
IDS_PH_GROUP_EVENT_TRACE_INFORMATION|2480|Event trace information|事件跟踪信息
IDS_PH_GROUP_FILE_INFORMATION|2481|File information|文件信息
IDS_PH_GROUP_SECTION_INFORMATION|2482|Section information|节对象信息
IDS_PH_GROUP_MUTANT_INFORMATION|2483|Mutant information|互斥体信息
IDS_PH_GROUP_PROCESS_INFORMATION|2484|Process information|进程信息
IDS_PH_GROUP_THREAD_INFORMATION|2485|Thread information|线程信息
IDS_PH_GROUP_SYMBOLIC_LINK_INFORMATION|2486|Symbolic Link information|符号链接信息
IDS_PH_GROUP_AUDITING_INFORMATION|2487|Auditing information|审核信息
IDS_PH_GROUP_SHARED_WINSOCK_CONTEXT|2488|Shared Winsock context|共享 Winsock 上下文
IDS_PH_GROUP_ADDRESSES|2489|Addresses|地址
IDS_PH_GROUP_AFD_INFO_CLASSES|2490|AFD info classes|AFD 信息类
IDS_PH_GROUP_TDI_DEVICES|2491|TDI devices|TDI 设备
IDS_PH_GROUP_SOCKET_LEVEL_OPTIONS|2492|Socket-level options|套接字级选项
IDS_PH_GROUP_IP_LEVEL_OPTIONS|2493|IP-level options|IP 级选项
IDS_PH_GROUP_TCP_LEVEL_OPTIONS|2494|TCP-level options|TCP 级选项
IDS_PH_GROUP_TCP_INFORMATION|2495|TCP information|TCP 信息
IDS_PH_GROUP_UDP_LEVEL_OPTIONS|2496|UDP-level options|UDP 级选项
IDS_PH_GROUP_HYPERV_LEVEL_OPTIONS|2497|Hyper-V-level options|Hyper-V 级选项
IDS_PH_GROUP_FLAGS|2498|Flags|标志
IDS_PH_GROUP_PRIVILEGES|2499|Privileges|特权
IDS_PH_GROUP_RESTRICTING_SIDS|2500|Restricting SIDs|限制 SID
IDS_PH_GROUPS|2501|Groups|组
IDS_PH_GROUPS_LOGON_SID|2502|Groups (Logon SID)|组（登录 SID）
IDS_PH_GROUPS_MANDATORY_LABEL|2503|Groups (Mandatory label)|组（强制标签）
IDS_PH_GROUP_GENERAL|2504|General|常规
IDS_PH_GROUP_LUIDS|2505|LUIDs|LUID
IDS_PH_GROUP_TRUST_LEVEL|2506|TrustLevel|信任级别
IDS_PH_GROUP_PROFILE|2507|Profile|配置文件
IDS_PH_GROUP_SYSTEM_ID|2508|System ID|系统 ID
IDS_PH_GROUP_PARENT|2509|Parent|父级
IDS_PH_GROUP_PACKAGE|2510|Package|程序包
""".strip()


REUSED_RESOURCE_DATA = r"""
IDS_PH_LOGON_NETWORK|2250|Network|网络
IDS_PH_STAT_HANDLES|2394|Handles|句柄
IDS_PH_STAT_CPU|2340|CPU|CPU
IDS_PH_STAT_OTHER|2386|Other|其他
IDS_PH_PLUGIN_PROPERTIES|2242|Properties|属性
""".strip()


def parse_resource_data(value):
    return [
        (symbol, int(resource_id), english, chinese)
        for symbol, resource_id, english, chinese in (
            line.split("|") for line in value.splitlines()
        )
    ]


NEW_RESOURCES = parse_resource_data(NEW_RESOURCE_DATA)
REUSED_RESOURCES = parse_resource_data(REUSED_RESOURCE_DATA)
ALL_RESOURCES = NEW_RESOURCES + REUSED_RESOURCES
RESOURCE_BY_ENGLISH = {
    english: symbol for symbol, _resource_id, english, _chinese in ALL_RESOURCES
}
EXPECTED_SYMBOLS = {symbol for symbol, *_ in ALL_RESOURCES}


# file | API | list-view/context expression | group expression | symbol
ROUTE_DATA = r"""
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_PROCESSES_AND_THREADS|IDS_PH_GROUP_PROCESSES
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_THREADS|IDS_PH_GROUP_THREADS
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_NETWORK|IDS_PH_LOGON_NETWORK
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_ENVIRONMENT|IDS_PH_GROUP_ENVIRONMENT
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_WMI|IDS_PH_GROUP_WMI
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_TOKEN|IDS_PH_GROUP_TOKEN
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_MEMORY|IDS_PH_GROUP_MEMORY
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_MODULES|IDS_PH_GROUP_MODULES
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_HANDLES|IDS_PH_STAT_HANDLES
options.c|PhAddListViewGroup|HighlightingListViewHandle|PH_OPTIONS_HIGHLIGHTING_GROUP_SERVICES|IDS_PH_GROUP_SERVICES
prpgstat.c|PhListView_AddGroup|Context->ListViewContext|PH_PROCESS_STATISTICS_CATEGORY_CPU|IDS_PH_STAT_CPU
prpgstat.c|PhListView_AddGroup|Context->ListViewContext|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|IDS_PH_GROUP_MEMORY
prpgstat.c|PhListView_AddGroup|Context->ListViewContext|PH_PROCESS_STATISTICS_CATEGORY_IO|IDS_PH_GROUP_IO
prpgstat.c|PhListView_AddGroup|Context->ListViewContext|PH_PROCESS_STATISTICS_CATEGORY_OTHER|IDS_PH_STAT_OTHER
envdlg.c|PhAddListViewGroup|context->ListViewHandle|ENV_GROUP_USER|IDS_PH_GROUP_USER
envdlg.c|PhAddListViewGroup|context->ListViewHandle|ENV_GROUP_SYSTEM|IDS_PH_GROUP_SYSTEM
sessprp.c|PhAddListViewGroup|context->ListViewHandle|0|IDS_PH_GROUP_USER
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_BASICINFO|IDS_PH_GROUP_BASIC_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_SECURITY|IDS_PH_GROUP_SECURITY_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_REFERENCES|IDS_PH_GROUP_REFERENCES
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_QUOTA|IDS_PH_GROUP_QUOTA_CHARGES
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_ALPC|IDS_PH_GROUP_ALPC_PORT
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_ETW|IDS_PH_GROUP_EVENT_TRACE_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_FILE|IDS_PH_GROUP_FILE_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_SECTION|IDS_PH_GROUP_SECTION_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_MUTANT|IDS_PH_GROUP_MUTANT_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD|IDS_PH_GROUP_PROCESS_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD|IDS_PH_GROUP_THREAD_INFORMATION
hndlprp.c|PhListView_AddGroup|Context->ListViewClass|PH_HANDLE_GENERAL_CATEGORY_SYMBOLICLINK|IDS_PH_GROUP_SYMBOLIC_LINK_INFORMATION
hndlprp.c|PhAddListViewGroup|Context->ListViewHeader|PH_HANDLE_GENERAL_CATEGORY_SECURITY|IDS_PH_GROUP_SECURITY_INFORMATION
hndlprp.c|PhAddListViewGroup|Context->ListViewHeader|PH_HANDLE_GENERAL_CATEGORY_SECURITY|IDS_PH_GROUP_AUDITING_INFORMATION
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_SHARED|IDS_PH_GROUP_SHARED_WINSOCK_CONTEXT
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_ADDRESSES|IDS_PH_GROUP_ADDRESSES
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_INFOCLASS|IDS_PH_GROUP_AFD_INFO_CLASSES
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_TDI|IDS_PH_GROUP_TDI_DEVICES
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_SO|IDS_PH_GROUP_SOCKET_LEVEL_OPTIONS
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_IP|IDS_PH_GROUP_IP_LEVEL_OPTIONS
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_TCP|IDS_PH_GROUP_TCP_LEVEL_OPTIONS
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_TCP_INFO|IDS_PH_GROUP_TCP_INFORMATION
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_UDP|IDS_PH_GROUP_UDP_LEVEL_OPTIONS
ntobjprp.c|PhListView_AddGroup|context->ListViewContext|PH_AFD_SOCKET_GROUP_HVSOCKET|IDS_PH_GROUP_HYPERV_LEVEL_OPTIONS
tokprp.c|PhAddListViewGroup|tokenPageContext->ListViewHandle|PH_PROCESS_TOKEN_CATEGORY_FLAGS|IDS_PH_GROUP_FLAGS
tokprp.c|PhAddListViewGroup|tokenPageContext->ListViewHandle|PH_PROCESS_TOKEN_CATEGORY_PRIVILEGES|IDS_PH_GROUP_PRIVILEGES
tokprp.c|PhAddListViewGroup|tokenPageContext->ListViewHandle|PH_PROCESS_TOKEN_CATEGORY_RESTRICTED|IDS_PH_GROUP_RESTRICTING_SIDS
tokprp.c|PhAddListViewGroup|tokenPageContext->ListViewHandle|PH_PROCESS_TOKEN_CATEGORY_GROUPS|IDS_PH_GROUPS
tokprp.c|PhAddListViewGroup|tokenPageContext->ListViewHandle|PH_PROCESS_TOKEN_CATEGORY_LOGON|IDS_PH_GROUPS_LOGON_SID
tokprp.c|PhAddListViewGroup|tokenPageContext->ListViewHandle|PH_PROCESS_TOKEN_CATEGORY_INTEGRITY|IDS_PH_GROUPS_MANDATORY_LABEL
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_GROUP_GENERAL
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_GROUP_LUIDS
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_GROUP_MEMORY
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_PLUGIN_PROPERTIES
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_GROUP_TRUST_LEVEL
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_GROUP_PROFILE
tokprp.c|PhAddListViewGroup|context->ListViewHandle|listViewGroupIndex++|IDS_PH_GROUP_SYSTEM_ID
tokprp.c|PhAddListViewGroup|context->ListViewHandle|0|IDS_PH_GROUP_GENERAL
tokprp.c|PhAddListViewGroup|context->ListViewHandle|1|IDS_PH_PLUGIN_PROPERTIES
tokprp.c|PhAddListViewGroup|context->ListViewHandle|2|IDS_PH_GROUP_PARENT
tokprp.c|PhAddListViewGroup|context->ListViewHandle|3|IDS_PH_GROUP_PACKAGE
tokprp.c|PhAddListViewGroup|context->ListViewHandle|4|IDS_PH_GROUP_PROFILE
""".strip()


ROUTES = [tuple(line.split("|")) for line in ROUTE_DATA.splitlines()]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_si_groups", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(expression):
    return re.sub(r"\s+", "", expression)


def parse_active_routes():
    audit = load_audit_module()
    routes = []

    for source_name in (
        "options.c",
        "prpgstat.c",
        "envdlg.c",
        "sessprp.c",
        "hndlprp.c",
        "ntobjprp.c",
        "tokprp.c",
    ):
        source = (SYSTEM_INFORMER_ROOT / source_name).read_text(encoding="utf-8-sig")
        masked = audit.mask_c_comments(source)

        for name, args, _spans, _start in audit.find_calls(
            masked, {"PhAddListViewGroup", "PhListView_AddGroup"}
        ):
            if len(args) != 3:
                continue

            literal_match = re.fullmatch(r'\s*L"([^"]+)"\s*', args[2], re.S)
            getter_match = re.fullmatch(
                r"\s*PhGetApplicationUiString\s*\(\s*(IDS_PH_[A-Z0-9_]+)\s*\)\s*",
                args[2],
                re.S,
            )
            symbol = None
            if literal_match:
                symbol = RESOURCE_BY_ENGLISH.get(literal_match.group(1))
            elif getter_match and getter_match.group(1) in EXPECTED_SYMBOLS:
                symbol = getter_match.group(1)

            if symbol:
                routes.append(
                    (
                        source_name,
                        name,
                        normalize(args[0]),
                        normalize(args[1]),
                        symbol if getter_match else None,
                    )
                )

    return routes


def parse_defines():
    header = (SYSTEM_INFORMER_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    app_header = (
        REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
    ).read_text(encoding="utf-8-sig")
    numeric = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)\s*$",
            header + "\n" + app_header,
        )
    }
    aliases = dict(
        re.findall(
            r"(?m)^#define\s+(IDS_PH_(?:FIRST|LAST))\s+(IDS_PH_[A-Z0-9_]+)\s*$",
            header,
        )
    )
    return numeric, aliases, header


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class SystemInformerListViewGroupResourceTests(unittest.TestCase):
    def test_tables_have_exact_cardinality(self):
        self.assertEqual(len(NEW_RESOURCES), 47)
        self.assertEqual(len(REUSED_RESOURCES), 5)
        self.assertEqual(len(ROUTES), 59)
        self.assertEqual(len({symbol for symbol, *_ in NEW_RESOURCES}), 47)
        self.assertEqual(
            Counter(symbol for *_, symbol in ROUTES),
            Counter(
                {
                    "IDS_PH_GROUP_MEMORY": 3,
                    "IDS_PH_GROUP_USER": 2,
                    "IDS_PH_GROUP_SECURITY_INFORMATION": 2,
                    "IDS_PH_GROUP_GENERAL": 2,
                    "IDS_PH_PLUGIN_PROPERTIES": 2,
                    "IDS_PH_GROUP_PROFILE": 2,
                    **{
                        symbol: 1
                        for symbol, *_ in ALL_RESOURCES
                        if symbol not in {
                            "IDS_PH_GROUP_MEMORY",
                            "IDS_PH_GROUP_USER",
                            "IDS_PH_GROUP_SECURITY_INFORMATION",
                            "IDS_PH_GROUP_GENERAL",
                            "IDS_PH_PLUGIN_PROPERTIES",
                            "IDS_PH_GROUP_PROFILE",
                        }
                    },
                }
            ),
        )

    def test_active_routes_match_exact_order_and_arguments(self):
        expected = [
            (source, api, normalize(list_view), normalize(group), symbol)
            for source, api, list_view, group, symbol in ROUTES
        ]
        self.assertEqual(parse_active_routes(), expected)

    def test_dynamic_token_groups_keep_return_assignments(self):
        audit = load_audit_module()
        source = (SYSTEM_INFORMER_ROOT / "tokprp.c").read_text(encoding="utf-8-sig")
        masked = audit.mask_c_comments(source)

        expected = {
            "trustLevelGroupIndex": "IDS_PH_GROUP_TRUST_LEVEL",
            "profileGroupIndex": "IDS_PH_GROUP_PROFILE",
            "systemIdGroupIndex": "IDS_PH_GROUP_SYSTEM_ID",
        }

        for variable, symbol in expected.items():
            with self.subTest(variable=variable):
                pattern = (
                    rf"\b{variable}\s*=\s*PhAddListViewGroup\(\s*"
                    rf"context->ListViewHandle\s*,\s*listViewGroupIndex\+\+\s*,\s*"
                    rf"PhGetApplicationUiString\(\s*{symbol}\s*\)\s*\)\s*;"
                )
                self.assertEqual(len(re.findall(pattern, masked, re.S)), 1)

        self.assertNotIn('L"Logon"', masked)

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        numeric, aliases, header = parse_defines()
        english = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in ALL_RESOURCES:
            self.assertEqual(numeric.get(symbol), resource_id, symbol)
            self.assertEqual(english.get(symbol), en, symbol)
            self.assertEqual(chinese.get(symbol), zh, symbol)

        self.assertEqual(aliases.get("IDS_PH_FIRST"), "IDS_PH_RESET_ALL_SETTINGS")
        self.assertEqual(
            aliases.get("IDS_PH_LAST"), "IDS_PH_HANDLE_ALPC_UNCONNECTED"
        )
        first_id = numeric[aliases["IDS_PH_FIRST"]]
        last_id = numeric[aliases["IDS_PH_LAST"]]
        expected_ids = set(range(first_id, last_id + 1))
        self.assertEqual(
            {value for value in numeric.values() if first_id <= value <= last_id},
            expected_ids,
        )
        self.assertEqual({numeric[symbol] for symbol in english}, expected_ids)
        self.assertEqual({numeric[symbol] for symbol in chinese}, expected_ids)
        self.assertEqual(len(english), 704)
        self.assertEqual(len(chinese), 704)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2704$")

    def test_json_uses_exact_existing_and_native_layers(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        strings = data["strings"]
        native_strings = data["native_strings"]
        self.assertFalse(strings.keys() & native_strings.keys())

        string_keys = {
            english for _symbol, _resource_id, english, _chinese in ALL_RESOURCES
            if english not in {
                "Basic information",
                "Security information",
                "Quota charges",
                "ALPC Port",
                "Event trace information",
                "File information",
                "Section information",
                "Mutant information",
                "Process information",
                "Thread information",
                "Symbolic Link information",
                "Auditing information",
                "Shared Winsock context",
                "Addresses",
                "AFD info classes",
                "TDI devices",
                "Socket-level options",
                "IP-level options",
                "TCP-level options",
                "TCP information",
                "UDP-level options",
                "Hyper-V-level options",
                "Privileges",
                "Restricting SIDs",
                "Groups",
                "Groups (Logon SID)",
                "Groups (Mandatory label)",
                "LUIDs",
                "TrustLevel",
                "Profile",
                "System ID",
                "Parent",
            }
        }
        self.assertEqual(len(string_keys), 20)
        self.assertEqual(len(ALL_RESOURCES) - len(string_keys), 32)

        for _symbol, _resource_id, english, chinese in ALL_RESOURCES:
            table = strings if english in string_keys else native_strings
            other = native_strings if english in string_keys else strings
            self.assertEqual(table.get(english), chinese, english)
            self.assertNotIn(english, other)

    def test_ci_requires_exact_main_resource_count_twice(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("sys_info.exe=704"), 2)
        self.assertNotIn("sys_info.exe=498", workflow)

    def test_fresh_scan_removes_all_systeminformer_groups(self):
        audit = load_audit_module()
        entries = []
        for path in sorted(SYSTEM_INFORMER_ROOT.rglob("*.c")):
            audit.scan_c_file(str(path), entries)

        remaining = [
            entry for entry in entries if entry["category"] == "c_listview_group"
        ]
        target_english = {english for _symbol, _id, english, _zh in ALL_RESOURCES}
        remaining_english = Counter(entry["english"] for entry in remaining)
        remaining_files = Counter(pathlib.Path(entry["file"]).name for entry in remaining)

        self.assertEqual(remaining, [])
        self.assertEqual(remaining_english, Counter())
        self.assertEqual(target_english & remaining_english.keys(), set())
        self.assertEqual(remaining_files, Counter())


if __name__ == "__main__":
    unittest.main()
