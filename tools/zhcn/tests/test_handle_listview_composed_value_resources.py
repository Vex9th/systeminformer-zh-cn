#!/usr/bin/env python3

import json
import pathlib
import re
import subprocess
import sys
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"
SOURCE_PATH = APP_ROOT / "hndlprp.c"
TRANSLATION_SOURCE = REPO_ROOT / "phlib" / "phtranslation_zhcn.c"

NEW_RESOURCES = (
    ("IDS_PH_HANDLE_PRINCIPAL_USER_SUFFIX", 2668, " (User)", "（用户）"),
    ("IDS_PH_HANDLE_PRINCIPAL_GROUP_SUFFIX", 2669, " (Group)", "（组）"),
    ("IDS_PH_HANDLE_PRINCIPAL_COMPUTER_SUFFIX", 2670, " (Computer)", "（计算机）"),
    ("IDS_PH_HANDLE_FILE_MODE_ASYNCHRONOUS", 2671, "Asynchronous", "异步"),
    ("IDS_PH_HANDLE_FILE_MODE_WRITE_THROUGH", 2672, "Write through", "直写"),
    ("IDS_PH_HANDLE_FILE_MODE_SEQUENTIAL", 2673, "Sequential", "顺序访问"),
    ("IDS_PH_HANDLE_FILE_MODE_NO_BUFFERING", 2674, "No buffering", "无缓冲"),
    ("IDS_PH_HANDLE_FILE_MODE_SYNCHRONOUS_ALERT", 2675, "Synchronous alert", "同步（可警报）"),
    ("IDS_PH_HANDLE_FILE_MODE_SYNCHRONOUS_NONALERT", 2676, "Synchronous non-alert", "同步（不可警报）"),
    ("IDS_PH_HANDLE_ALPC_LPC_MODE", 2677, "LPC mode", "LPC 模式"),
    ("IDS_PH_HANDLE_ALPC_ALLOW_IMPERSONATION", 2678, "Allow impersonation", "允许模拟"),
    ("IDS_PH_HANDLE_ALPC_ALLOW_LPC_REQUESTS", 2679, "Allow LPC requests", "允许 LPC 请求"),
    ("IDS_PH_HANDLE_ALPC_WAITABLE", 2680, "Waitable", "可等待"),
    ("IDS_PH_HANDLE_ALPC_ALLOW_OBJECT_DUPLICATION", 2681, "Allow object duplication", "允许复制对象"),
    ("IDS_PH_HANDLE_ALPC_SYSTEM_PROCESS_ONLY", 2682, "System process only", "仅限系统进程"),
    ("IDS_PH_HANDLE_ALPC_WAKE_POLICY_1", 2683, "Wake policy (1)", "唤醒策略（1）"),
    ("IDS_PH_HANDLE_ALPC_WAKE_POLICY_2", 2684, "Wake policy (2)", "唤醒策略（2）"),
    ("IDS_PH_HANDLE_ALPC_WAKE_POLICY_3", 2685, "Wake policy (3)", "唤醒策略（3）"),
    ("IDS_PH_HANDLE_ALPC_NO_SHARED_SECTION_DIRECT", 2686, "No shared section (direct)", "无共享节（直接）"),
    ("IDS_PH_HANDLE_ALPC_ALLOW_MULTI_HANDLE_ATTRIBUTES", 2687, "Allow multi-handle attributes", "允许多句柄属性"),
    ("IDS_PH_HANDLE_ALPC_INITIALIZED", 2688, "Initialized", "已初始化"),
    ("IDS_PH_HANDLE_ALPC_CONNECTION_PENDING", 2689, "Connection pending", "连接待处理"),
    ("IDS_PH_HANDLE_ALPC_CONNECTION_REFUSED", 2690, "Connection refused", "连接被拒绝"),
    ("IDS_PH_HANDLE_ALPC_DISCONNECTED", 2691, "Disconnected", "已断开连接"),
    ("IDS_PH_HANDLE_ALPC_CLOSED", 2692, "Closed", "已关闭"),
    ("IDS_PH_HANDLE_ALPC_NO_FLUSH_ON_CLOSE", 2693, "No flush on close", "关闭时不刷新"),
    ("IDS_PH_HANDLE_ALPC_RETURN_EXTENDED_INFO", 2694, "Return extended info", "返回扩展信息"),
    ("IDS_PH_HANDLE_ALPC_DYNAMIC_SECURITY", 2695, "Dynamic security", "动态安全"),
    ("IDS_PH_HANDLE_ALPC_WOW64_COMPLETION_LIST", 2696, "WOW64 completion list", "WOW64 完成列表"),
    ("IDS_PH_HANDLE_ALPC_HAS_COMPLETION_LIST", 2697, "Has completion list", "有完成列表"),
    ("IDS_PH_HANDLE_ALPC_HAD_COMPLETION_LIST", 2698, "Had completion list", "曾有完成列表"),
    ("IDS_PH_HANDLE_ALPC_ENABLE_COMPLETION_LIST", 2699, "Enable completion list", "启用完成列表"),
    ("IDS_PH_HANDLE_ALPC_SERVER_CONNECTION", 2700, "Server connection", "服务器连接"),
    ("IDS_PH_HANDLE_ALPC_CLIENT_COMMUNICATION", 2701, "Client communication", "客户端通信"),
    ("IDS_PH_HANDLE_ALPC_SERVER_COMMUNICATION", 2702, "Server communication", "服务器通信"),
    ("IDS_PH_HANDLE_ALPC_UNCONNECTED", 2703, "Unconnected", "未连接"),
)

FILE_MODE_ROUTES = {
    "FILE_FLAG_OVERLAPPED": "IDS_PH_HANDLE_FILE_MODE_ASYNCHRONOUS",
    "FILE_FLAG_WRITE_THROUGH": "IDS_PH_HANDLE_FILE_MODE_WRITE_THROUGH",
    "FILE_FLAG_SEQUENTIAL_SCAN": "IDS_PH_HANDLE_FILE_MODE_SEQUENTIAL",
    "FILE_FLAG_NO_BUFFERING": "IDS_PH_HANDLE_FILE_MODE_NO_BUFFERING",
    "FILE_SYNCHRONOUS_IO_ALERT": "IDS_PH_HANDLE_FILE_MODE_SYNCHRONOUS_ALERT",
    "FILE_SYNCHRONOUS_IO_NONALERT": "IDS_PH_HANDLE_FILE_MODE_SYNCHRONOUS_NONALERT",
}

ALPC_FLAG_ROUTES = {
    "ALPC_PORFLG_LPC_MODE": "IDS_PH_HANDLE_ALPC_LPC_MODE",
    "ALPC_PORFLG_ALLOW_IMPERSONATION": "IDS_PH_HANDLE_ALPC_ALLOW_IMPERSONATION",
    "ALPC_PORFLG_ALLOW_LPC_REQUESTS": "IDS_PH_HANDLE_ALPC_ALLOW_LPC_REQUESTS",
    "ALPC_PORFLG_WAITABLE_PORT": "IDS_PH_HANDLE_ALPC_WAITABLE",
    "ALPC_PORFLG_ALLOW_DUP_OBJECT": "IDS_PH_HANDLE_ALPC_ALLOW_OBJECT_DUPLICATION",
    "ALPC_PORFLG_SYSTEM_PROCESS": "IDS_PH_HANDLE_ALPC_SYSTEM_PROCESS_ONLY",
    "ALPC_PORFLG_WAKE_POLICY1": "IDS_PH_HANDLE_ALPC_WAKE_POLICY_1",
    "ALPC_PORFLG_WAKE_POLICY2": "IDS_PH_HANDLE_ALPC_WAKE_POLICY_2",
    "ALPC_PORFLG_WAKE_POLICY3": "IDS_PH_HANDLE_ALPC_WAKE_POLICY_3",
    "ALPC_PORFLG_DIRECT_MESSAGE": "IDS_PH_HANDLE_ALPC_NO_SHARED_SECTION_DIRECT",
    "ALPC_PORFLG_ALLOW_MULTIHANDLE_ATTRIBUTE": "IDS_PH_HANDLE_ALPC_ALLOW_MULTI_HANDLE_ATTRIBUTES",
}

ALPC_STATE_ROUTES = {
    "Initialized": "IDS_PH_HANDLE_ALPC_INITIALIZED",
    "ConnectionPending": "IDS_PH_HANDLE_ALPC_CONNECTION_PENDING",
    "ConnectionRefused": "IDS_PH_HANDLE_ALPC_CONNECTION_REFUSED",
    "Disconnected": "IDS_PH_HANDLE_ALPC_DISCONNECTED",
    "Closed": "IDS_PH_HANDLE_ALPC_CLOSED",
    "NoFlushOnClose": "IDS_PH_HANDLE_ALPC_NO_FLUSH_ON_CLOSE",
    "ReturnExtendedInfo": "IDS_PH_HANDLE_ALPC_RETURN_EXTENDED_INFO",
    "Waitable": "IDS_PH_HANDLE_ALPC_WAITABLE",
    "DynamicSecurity": "IDS_PH_HANDLE_ALPC_DYNAMIC_SECURITY",
    "Wow64CompletionList": "IDS_PH_HANDLE_ALPC_WOW64_COMPLETION_LIST",
    "Lpc": 'L"LPC"',
    "LpcToLpc": 'L"LPC-to-LPC"',
    "HasCompletionList": "IDS_PH_HANDLE_ALPC_HAS_COMPLETION_LIST",
    "HadCompletionList": "IDS_PH_HANDLE_ALPC_HAD_COMPLETION_LIST",
    "EnableCompletionList": "IDS_PH_HANDLE_ALPC_ENABLE_COMPLETION_LIST",
}

PORT_TYPE_ROUTES = Counter({
    "IDS_PH_HANDLE_ALPC_SERVER_CONNECTION": 1,
    "IDS_PH_HANDLE_ALPC_CLIENT_COMMUNICATION": 1,
    "IDS_PH_HANDLE_ALPC_SERVER_COMMUNICATION": 1,
    "IDS_PH_HANDLE_ALPC_UNCONNECTED": 1,
})

TECHNICAL_PERMISSION_SUFFIXES = Counter({
    'L" (APP_PACKAGE)"': 1,
    'L" (APP_CONTAINER)"': 1,
    'L" (APP_CAPABILITY)"': 1,
})


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
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


def access_entry_routes(body: str) -> dict[str, str]:
    routes = {}
    pattern = re.compile(
        r'\{\s*L"(?P<name>[^"]+)"\s*,\s*[^,]+,\s*FALSE\s*,\s*FALSE\s*,\s*'
        r'(?:(?:PhGetApplicationUiString\((?P<resource>IDS_PH_[A-Z0-9_]+)\))|'
        r'(?P<literal>L"[^"]+"))\s*\}',
    )
    for match in pattern.finditer(body):
        routes[match.group("name")] = match.group("resource") or match.group("literal")
    return routes


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class HandleListViewComposedValueResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE_PATH.read_text(encoding="utf-8-sig")
        cls.general_body = function_body(cls.source, "PhpUpdateHandleGeneral")

    def test_access_entry_helpers_have_exact_localized_routes(self) -> None:
        self.assertNotRegex(
            self.source,
            r"CONST\s+PH_ACCESS_ENTRY\s+(?:FileModeAccessEntries|AlpcFlags|AlpcStateFlags)\[\]",
        )
        expected = {
            "PhpGetFileModeAccessString": FILE_MODE_ROUTES,
            "PhpGetAlpcFlagsString": ALPC_FLAG_ROUTES,
            "PhpGetAlpcStateFlagsString": ALPC_STATE_ROUTES,
        }
        for helper, routes in expected.items():
            with self.subTest(helper=helper):
                body = function_body(self.source, helper)
                self.assertEqual(access_entry_routes(body), routes)
                self.assertEqual(body.count("PhGetAccessString("), 1)

        self.assertEqual(self.general_body.count("PhpGetFileModeAccessString("), 2)
        self.assertEqual(self.general_body.count("PhpGetAlpcFlagsString("), 2)
        self.assertEqual(self.general_body.count("PhpGetAlpcStateFlagsString("), 1)
        self.assertEqual(
            self.general_body.count(
                "PhSetHandleListViewItem(Context, PH_HANDLE_GENERAL_INDEX_FILEMODE"
            ),
            2,
        )
        self.assertEqual(
            self.general_body.count(
                "PhSetHandleListViewItem(Context, PH_HANDLE_GENERAL_INDEX_FLAGS"
            ),
            2,
        )
        self.assertEqual(
            self.general_body.count(
                "PhSetHandleListViewItem(Context, PH_HANDLE_GENERAL_INDEX_ALPCSTATE"
            ),
            1,
        )

    def test_permission_suffixes_and_port_types_use_exact_resources(self) -> None:
        permission_functions = (
            "PhAddHandlePermissionsTrustee",
            "PhUpdateHandlePermissionsOwnerSecurity",
            "PhUpdateHandlePermissionsGroupSecurity",
        )
        permission_resources = (
            "IDS_PH_HANDLE_PRINCIPAL_USER_SUFFIX",
            "IDS_PH_HANDLE_PRINCIPAL_GROUP_SUFFIX",
            "IDS_PH_HANDLE_PRINCIPAL_COMPUTER_SUFFIX",
        )
        for function in permission_functions:
            body = function_body(self.source, function)
            for resource in permission_resources:
                with self.subTest(function=function, resource=resource):
                    self.assertEqual(
                        body.count(f"PhGetApplicationUiString({resource})"),
                        1,
                    )
            self.assertNotRegex(body, r'L" \((?:User|Group|Computer)\)"')
            self.assertEqual(
                Counter(re.findall(
                    r"PhConcatStringRefZ\(&string->sr,\s*(L\" \(APP_[A-Z]+\)\")\)",
                    body,
                )),
                TECHNICAL_PERMISSION_SUFFIXES,
            )

        trustee_body = function_body(self.source, "PhAddHandlePermissionsTrustee")
        self.assertEqual(
            trustee_body.count(
                "PhGetStringOrDefault(string, PhGetApplicationUiString(IDS_PH_NOT_AVAILABLE))"
            ),
            2,
        )
        self.assertNotIn('PhGetStringOrDefault(string, L"N/A")', trustee_body)

        state_start = self.general_body.index("PCWSTR portTypeString")
        state_end = self.general_body.index("stateFlagsString =", state_start)
        port_routes = Counter(re.findall(
            r"portTypeString\s*=\s*PhGetApplicationUiString\((IDS_PH_[A-Z0-9_]+)\)",
            self.general_body[state_start:state_end],
        ))
        self.assertEqual(port_routes, PORT_TYPE_ROUTES)

    def test_resources_ownership_boundaries_and_counts_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        app_header = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(
            encoding="utf-8-sig"
        )
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        runtime_source = TRANSLATION_SOURCE.read_text(encoding="utf-8-sig")

        for symbol, numeric_id, en, zh in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{numeric_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(translations["native_strings"].get(en), zh)
                self.assertNotIn(en, translations["strings"])
                self.assertNotRegex(runtime_source, rf'\{{ L"{re.escape(en)}", L"')

        self.assertFalse(
            translations["strings"].keys() & translations["native_strings"].keys()
        )
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
        self.assertEqual(len(english), 1370)
        self.assertEqual(len(chinese), 1370)
        self.assertRegex(
            header,
            r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_MENU_COLLAPSE_ALL_PLAIN$",
        )
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3370$")

    def test_ci_and_generator_counts_are_exact(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("sys_info.exe=1370"), 2)
        self.assertNotIn("sys_info.exe=668", workflow)
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "zhcn" / "generate_native_resources.py"),
                "--check",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("3312 strings", result.stdout)


if __name__ == "__main__":
    unittest.main()
