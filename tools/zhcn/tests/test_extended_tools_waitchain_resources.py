#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


RESOURCE_DATA = r"""
IDS_ET_WCT_COLUMN_TYPE|61132|Type|类型|strings
IDS_ET_WCT_COLUMN_THREAD_ID|61133|ThreadId|线程 ID|strings
IDS_ET_WCT_COLUMN_PROCESS_ID|61134|ProcessId|进程 ID|strings
IDS_ET_WCT_COLUMN_STATUS|61135|Status|状态|strings
IDS_ET_WCT_COLUMN_CONTEXT_SWITCHES|61136|Context Switches|上下文切换|strings
IDS_ET_WCT_COLUMN_WAIT_TIME|61137|WaitTime|等待时间|strings
IDS_ET_WCT_COLUMN_TIMEOUT|61138|Timeout|超时|strings
IDS_ET_WCT_COLUMN_ALERTABLE|61139|Alertable|可警报|strings
IDS_ET_WCT_COLUMN_NAME|61140|Name|名称|strings
IDS_ET_WCT_GO_TO_PROCESS|61141|Go to Process...|转到进程...|strings
IDS_ET_WCT_GO_TO_THREAD|61142|Go to Thread...|转到线程...|strings
IDS_ET_WCT_PROCESS_NOT_FOUND|61143|The process does not exist.|该进程不存在。|strings
IDS_ET_WCT_TRUE|61144|true|是|native_strings
IDS_ET_WCT_NO_THREADS|61145|There are no threads to display.|没有可显示的线程。|native_strings
IDS_ET_WCT_QUERYING|61146|Querying thread wait chain sessions...|正在查询线程等待链会话...|native_strings
IDS_ET_WCT_TYPE_CRITICAL_SECTION|61147|CriticalSection|临界区|native_strings
IDS_ET_WCT_TYPE_SEND_MESSAGE|61148|SendMessage|发送消息|native_strings
IDS_ET_WCT_TYPE_MUTEX|61149|Mutex|互斥体|native_strings
IDS_ET_WCT_TYPE_ALPC|61150|ALPC|ALPC|native_strings
IDS_ET_WCT_TYPE_COM|61151|COM|COM|native_strings
IDS_ET_WCT_TYPE_THREAD_WAIT|61152|ThreadWait|线程等待|native_strings
IDS_ET_WCT_TYPE_PROCESS_WAIT|61153|ProcessWait|进程等待|native_strings
IDS_ET_WCT_TYPE_THREAD|61154|Thread|线程|strings
IDS_ET_WCT_TYPE_COM_ACTIVATION|61155|COM Activation|COM 激活|native_strings
IDS_ET_WCT_UNKNOWN|61156|Unknown|未知|strings
IDS_ET_WCT_TYPE_SOCKET_IO|61157|Socket I/O|套接字 I/O|native_strings
IDS_ET_WCT_TYPE_SMB_IO|61158|SMB I/O|SMB I/O|native_strings
IDS_ET_WCT_STATUS_NO_ACCESS|61159|No Access|无访问权限|native_strings
IDS_ET_WCT_STATUS_RUNNING|61160|Running|正在运行|native_strings
IDS_ET_WCT_STATUS_BLOCKED|61161|Blocked|已阻塞|native_strings
IDS_ET_WCT_STATUS_PID_ONLY|61162|Pid Only|仅 PID|native_strings
IDS_ET_WCT_STATUS_PID_ONLY_RPCSS|61163|Pid Only (RPCSS)|仅 PID（RPCSS）|native_strings
IDS_ET_WCT_STATUS_OWNED|61164|Owned|已持有|native_strings
IDS_ET_WCT_STATUS_NOT_OWNED|61165|Not Owned|未持有|native_strings
IDS_ET_WCT_STATUS_ABANDONED|61166|Abandoned|已放弃|native_strings
IDS_ET_WCT_STATUS_ERROR|61167|Error|错误|native_strings
IDS_ET_WCT_DATE_TIME_FORMAT|61168|%s %s|%s %s|native_strings
""".strip()


RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in (
        line.split("|") for line in RESOURCE_DATA.splitlines()
    )
]


TYPE_ROUTES = (
    ("WctCriticalSectionType", "IDS_ET_WCT_TYPE_CRITICAL_SECTION", "CriticalSection"),
    ("WctSendMessageType", "IDS_ET_WCT_TYPE_SEND_MESSAGE", "SendMessage"),
    ("WctMutexType", "IDS_ET_WCT_TYPE_MUTEX", "Mutex"),
    ("WctAlpcType", "IDS_ET_WCT_TYPE_ALPC", "ALPC"),
    ("WctComType", "IDS_ET_WCT_TYPE_COM", "COM"),
    ("WctThreadWaitType", "IDS_ET_WCT_TYPE_THREAD_WAIT", "ThreadWait"),
    ("WctProcessWaitType", "IDS_ET_WCT_TYPE_PROCESS_WAIT", "ProcessWait"),
    ("WctThreadType", "IDS_ET_WCT_TYPE_THREAD", "Thread"),
    ("WctComActivationType", "IDS_ET_WCT_TYPE_COM_ACTIVATION", "COM Activation"),
    ("WctUnknownType", "IDS_ET_WCT_UNKNOWN", "Unknown"),
    ("WctSocketIoType", "IDS_ET_WCT_TYPE_SOCKET_IO", "Socket I/O"),
    ("WctSmbIoType", "IDS_ET_WCT_TYPE_SMB_IO", "SMB I/O"),
)


STATUS_ROUTES = (
    ("WctStatusNoAccess", "IDS_ET_WCT_STATUS_NO_ACCESS", "No Access"),
    ("WctStatusRunning", "IDS_ET_WCT_STATUS_RUNNING", "Running"),
    ("WctStatusBlocked", "IDS_ET_WCT_STATUS_BLOCKED", "Blocked"),
    ("WctStatusPidOnly", "IDS_ET_WCT_STATUS_PID_ONLY", "Pid Only"),
    ("WctStatusPidOnlyRpcss", "IDS_ET_WCT_STATUS_PID_ONLY_RPCSS", "Pid Only (RPCSS)"),
    ("WctStatusOwned", "IDS_ET_WCT_STATUS_OWNED", "Owned"),
    ("WctStatusNotOwned", "IDS_ET_WCT_STATUS_NOT_OWNED", "Not Owned"),
    ("WctStatusAbandoned", "IDS_ET_WCT_STATUS_ABANDONED", "Abandoned"),
    ("WctStatusUnknown", "IDS_ET_WCT_UNKNOWN", "Unknown"),
    ("WctStatusError", "IDS_ET_WCT_STATUS_ERROR", "Error"),
)


COLUMN_ROUTES = (
    ("TREE_COLUMN_ITEM_TYPE", "IDS_ET_WCT_COLUMN_TYPE", "Type"),
    ("TREE_COLUMN_ITEM_THREADID", "IDS_ET_WCT_COLUMN_THREAD_ID", "ThreadId"),
    ("TREE_COLUMN_ITEM_PROCESSID", "IDS_ET_WCT_COLUMN_PROCESS_ID", "ProcessId"),
    ("TREE_COLUMN_ITEM_STATUS", "IDS_ET_WCT_COLUMN_STATUS", "Status"),
    ("TREE_COLUMN_ITEM_CONTEXTSWITCH", "IDS_ET_WCT_COLUMN_CONTEXT_SWITCHES", "Context Switches"),
    ("TREE_COLUMN_ITEM_WAITTIME", "IDS_ET_WCT_COLUMN_WAIT_TIME", "WaitTime"),
    ("TREE_COLUMN_ITEM_TIMEOUT", "IDS_ET_WCT_COLUMN_TIMEOUT", "Timeout"),
    ("TREE_COLUMN_ITEM_ALERTABLE", "IDS_ET_WCT_COLUMN_ALERTABLE", "Alertable"),
    ("TREE_COLUMN_ITEM_NAME", "IDS_ET_WCT_COLUMN_NAME", "Name"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_waitchain", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def masked_source():
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PLUGIN_ROOT / "waitchain.c").read_text(encoding="utf-8-sig")
    )


def function_body(text, function_name):
    match = re.search(
        rf"\b{re.escape(function_name)}\s*\([^;]*?\)\s*\{{", text, re.S
    )
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


def initializer_body(text, array_name):
    match = re.search(
        rf"\b{re.escape(array_name)}\s*\[\s*\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        text,
        re.S,
    )
    if not match:
        raise AssertionError(f"initializer not found: {array_name}")
    return match.group("body")


def parse_calls(text, function_name):
    calls = []
    pattern = re.compile(rf"\b{re.escape(function_name)}\s*\(")

    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        in_string = False
        escaped = False

        for offset in range(start, len(text)):
            character = text[offset]

            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
            elif character == '"':
                in_string = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    calls.append(split_arguments(text[start:offset]))
                    break

    return calls


def split_arguments(arguments):
    result = []
    start = 0
    depth = 0
    in_string = False
    escaped = False

    for offset, character in enumerate(arguments):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "({[":
            depth += 1
        elif character in ")}]":
            depth -= 1
        elif character == "," and depth == 0:
            result.append(arguments[start:offset].strip())
            start = offset + 1

    result.append(arguments[start:].strip())
    return tuple(result)


def parse_defines():
    header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    defines = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)$", header
        )
    }
    return defines, header


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


class ExtendedToolsWaitChainResourceTests(unittest.TestCase):
    def test_type_and_status_tables_have_exact_resource_routes(self):
        source = masked_source()
        pattern = re.compile(
            r"\{\s*(Wct[A-Za-z0-9_]+)\s*,\s*"
            r"(IDS_ET_WCT_[A-Z0-9_]+)\s*,\s*L\"([^\"]+)\"\s*\}"
        )

        self.assertEqual(
            tuple(pattern.findall(initializer_body(source, "WaitChainObjectTypeEntries"))),
            TYPE_ROUTES,
        )
        self.assertEqual(
            tuple(pattern.findall(initializer_body(source, "WaitChainObjectStatusEntries"))),
            STATUS_ROUTES,
        )
        self.assertNotIn("APLC", source)

        lookup_body = function_body(source, "WaitChainTextEntryToString")
        self.assertRegex(
            lookup_body,
            r"return\s+EtGetUiString\(\s*entry->ResourceId\s*,\s*entry->Fallback\s*\)\s*;",
        )
        self.assertRegex(
            lookup_body,
            r"return\s+EtGetUiString\(\s*IDS_ET_WCT_UNKNOWN\s*,\s*L\"Unknown\"\s*\)\s*;",
        )

        for function_name, array_name in (
            ("WaitChainObjectTypeToString", "WaitChainObjectTypeEntries"),
            ("WaitChainObjectStatusToString", "WaitChainObjectStatusEntries"),
        ):
            body = function_body(source, function_name)
            self.assertRegex(
                body,
                rf"return\s+WaitChainTextEntryToString\(\s*{array_name}\s*,\s*"
                rf"RTL_NUMBER_OF\({array_name}\)\s*,",
            )

    def test_columns_menu_prompt_boolean_and_status_routes_are_exact(self):
        source = masked_source()
        initialize_body = function_body(source, "WtcInitializeWaitTree")
        column_pattern = re.compile(
            r'^EtGetUiString\(\s*(IDS_ET_WCT_[A-Z0-9_]+)\s*,\s*L"([^"]+)"\s*\)$'
        )
        column_routes = []

        for arguments in parse_calls(initialize_body, "PhAddTreeNewColumn"):
            match = column_pattern.match(arguments[3])
            self.assertIsNotNone(match)
            column_routes.append((arguments[1], *match.groups()))

        self.assertEqual(tuple(column_routes), COLUMN_ROUTES)

        dialog_body = function_body(source, "WaitChainDlgProc")
        self.assertRegex(
            dialog_body,
            r"PhCreateEMenuItem\([^;]*ID_WCT_MENU_GOTOPROCESS\s*,\s*"
            r"EtGetUiString\(\s*IDS_ET_WCT_GO_TO_PROCESS\s*,\s*L\"Go to Process\.\.\.\"\s*\)",
        )
        self.assertRegex(
            dialog_body,
            r"PhCreateEMenuItem\([^;]*ID_WCT_MENU_GOTOTHREAD\s*,\s*"
            r"EtGetUiString\(\s*IDS_ET_WCT_GO_TO_THREAD\s*,\s*L\"Go to Thread\.\.\.\"\s*\)",
        )
        self.assertRegex(
            dialog_body,
            r"PhShowError2\(\s*WindowHandle\s*,\s*"
            r"EtGetUiString\(\s*IDS_ET_WCT_PROCESS_NOT_FOUND\s*,\s*"
            r"L\"The process does not exist\.\"\s*\)",
        )

        tree_callback = function_body(source, "WtcWaitTreeNewCallback")
        self.assertRegex(
            tree_callback,
            r"PhInitializeStringRef\(\s*&getCellText->Text\s*,\s*"
            r"EtGetUiString\(\s*IDS_ET_WCT_TRUE\s*,\s*L\"true\"\s*\)\s*\)",
        )

        status_body = function_body(source, "EtWaitChainSetTreeStatusMessage")
        self.assertRegex(
            status_body,
            r"PhCreateString\(\s*EtGetUiString\(\s*IDS_ET_WCT_NO_THREADS\s*,\s*"
            r"L\"There are no threads to display\.\"\s*\)\s*\)",
        )
        self.assertRegex(
            status_body,
            r"PhCreateString\(\s*EtGetUiString\(\s*IDS_ET_WCT_QUERYING\s*,\s*"
            r"L\"Querying thread wait chain sessions\.\.\.\"\s*\)\s*\)",
        )

    def test_date_format_and_string_lifetimes_are_preserved(self):
        source = masked_source()
        ui_string_declaration = re.search(
            r"PCWSTR\s+EtGetUiString\(\s*_In_\s+ULONG\s+ResourceId\s*,\s*"
            r"_In_\s+PCWSTR\s+Fallback\s*\)\s*;",
            source,
            re.S,
        )
        self.assertIsNotNone(ui_string_declaration)
        self.assertLess(
            ui_string_declaration.start(),
            source.index("typedef struct _WCT_TEXT_ENTRY"),
        )

        date_routes = re.findall(
            r"PhFormatString\(\s*EtGetUiString\(\s*IDS_ET_WCT_DATE_TIME_FORMAT\s*,\s*"
            r"L\"%s %s\"\s*\)\s*,\s*dateString->Buffer\s*,\s*timeString->Buffer\s*\)",
            source,
            re.S,
        )
        self.assertEqual(len(date_routes), 2)

        self.assertRegex(
            source,
            r"PCWSTR\s+WaitChainObjectTypeToString\s*\(",
        )
        self.assertRegex(
            source,
            r"PCWSTR\s+WaitChainObjectStatusToString\s*\(",
        )
        self.assertRegex(
            source,
            r"PhCompareStringZ\(\s*WaitChainObjectTypeToString",
        )
        self.assertRegex(
            source,
            r"PhCompareStringZ\(\s*WaitChainObjectStatusToString",
        )
        self.assertEqual(
            source.count(
                "PhInitializeStringRef(&getCellText->Text, text);"
            ),
            2,
        )
        self.assertNotIn("WaitChainUnknownString", source)
        self.assertNotIn("SREF(L\"", source)

    def test_resources_json_and_cache_boundary_are_exact(self):
        defines, header = parse_defines()
        english = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.zh-cn.rc")
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )

        for symbol, resource_id, en, zh, owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(data[owner].get(en), zh)
                other = "strings" if owner == "native_strings" else "native_strings"
                self.assertNotIn(en, data[other])

        self.assertEqual([row[1] for row in RESOURCES], list(range(61132, 61169)))
        self.assertEqual(sorted(defines.values()), list(range(61000, 61471)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 471)
        self.assertEqual(len(chinese), 471)
        self.assertRegex(
            header,
            r"(?m)^#define IDS_ET_CACHED_LAST\s+IDS_ET_SEARCH_NAMED_PIPES$",
        )
        self.assertRegex(
            header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+61471$"
        )

    def test_no_unwrapped_waitchain_ui_literals_remain(self):
        source = masked_source()

        for function_name, argument_index in (
            ("PhAddTreeNewColumn", 3),
            ("PhCreateEMenuItem", 2),
            ("PhShowError2", 1),
            ("PhCreateString", 0),
            ("PhInitializeStringRef", 1),
            ("PhFormatString", 0),
        ):
            for arguments in parse_calls(source, function_name):
                if len(arguments) > argument_index:
                    self.assertFalse(
                        arguments[argument_index].lstrip().startswith('L"'),
                        (function_name, arguments),
                    )

        expected_resource_ids = Counter(row[0] for row in RESOURCES)
        actual_resource_ids = Counter(
            resource_id
            for resource_id in re.findall(r"\bIDS_ET_WCT_[A-Z0-9_]+\b", source)
            if resource_id in expected_resource_ids
        )
        self.assertEqual(set(actual_resource_ids), set(expected_resource_ids))


if __name__ == "__main__":
    unittest.main()
