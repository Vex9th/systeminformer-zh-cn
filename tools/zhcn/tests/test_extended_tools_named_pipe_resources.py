#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


# symbol | id | English | zh-CN | translation owner
RESOURCE_DATA = r"""
IDS_ET_PIPE_STREAM|61188|Stream|字节流|native_strings
IDS_ET_PIPE_MESSAGE|61189|Message|消息|strings
IDS_ET_PIPE_INBOUND|61190|Inbound|入站|native_strings
IDS_ET_PIPE_OUTBOUND|61191|Outbound|出站|native_strings
IDS_ET_PIPE_DUPLEX|61192|Duplex|双工|native_strings
IDS_ET_PIPE_UNLIMITED|61193|Unlimited|不限|native_strings
IDS_ET_PIPE_LISTENING|61194|Listening|正在侦听|native_strings
IDS_ET_PIPE_CLOSING|61195|Closing|正在关闭|native_strings
IDS_ET_PIPE_REJECT|61196|Reject|拒绝|native_strings
IDS_ET_PIPE_ACCEPT|61197|Accept|接受|native_strings
IDS_ET_PIPE_QUEUE|61198|Queue|排队|native_strings
IDS_ET_PIPE_COMPLETE|61199|Complete|立即完成|native_strings
""".strip()


RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in (
        line.split("|") for line in RESOURCE_DATA.splitlines()
    )
]


ROUTES = {
    "Stream": "IDS_ET_PIPE_STREAM",
    "Message": "IDS_ET_PIPE_MESSAGE",
    "Inbound": "IDS_ET_PIPE_INBOUND",
    "Outbound": "IDS_ET_PIPE_OUTBOUND",
    "Duplex": "IDS_ET_PIPE_DUPLEX",
    "Unlimited": "IDS_ET_PIPE_UNLIMITED",
    "Disconnected": "IDS_ET_SESSION_STATE_DISCONNECTED",
    "Listening": "IDS_ET_PIPE_LISTENING",
    "Connected": "IDS_ET_SESSION_STATE_CONNECTED",
    "Closing": "IDS_ET_PIPE_CLOSING",
    "Reject": "IDS_ET_PIPE_REJECT",
    "Accept": "IDS_ET_PIPE_ACCEPT",
    "Queue": "IDS_ET_PIPE_QUEUE",
    "Complete": "IDS_ET_PIPE_COMPLETE",
}


EXPECTED_OCCURRENCES = {
    "Stream": 4,
    "Message": 4,
    "Inbound": 2,
    "Outbound": 2,
    "Duplex": 2,
    "Unlimited": 2,
    "Disconnected": 2,
    "Listening": 2,
    "Connected": 2,
    "Closing": 2,
    "Reject": 2,
    "Accept": 2,
    "Queue": 2,
    "Complete": 2,
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_et_named_pipe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_text():
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PLUGIN_ROOT / "namedpipes.c").read_text(encoding="utf-8-sig")
    )


def function_body(source, name):
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening_brace = source.find("{", match.start())
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index]

    raise AssertionError(f"unterminated function: {name}")


def compact(value):
    return re.sub(r"\s+", "", value)


def parse_defines():
    header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    return {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)$", header
        )
    }, header


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


class ExtendedToolsNamedPipeResourceTests(unittest.TestCase):
    def test_all_32_fixed_enum_values_use_the_correct_case_and_column(self):
        source = source_text()
        functions = {
            "EtEnumerateNamedPipeDirectory": {
                "type": 3,
                "configuration": 4,
                "maximum": 5,
                "state": 9,
                "remote": 10,
                "read": 11,
                "completion": 12,
            },
            "EtAddNamedPipeHandleToListView": {
                "type": 5,
                "configuration": 6,
                "maximum": 7,
                "state": 11,
                "remote": 12,
                "read": 13,
                "completion": 14,
            },
        }
        case_routes = (
            ("FILE_PIPE_BYTE_STREAM_TYPE", "type", "IDS_ET_PIPE_STREAM", "Stream"),
            ("FILE_PIPE_MESSAGE_TYPE", "type", "IDS_ET_PIPE_MESSAGE", "Message"),
            ("FILE_PIPE_INBOUND", "configuration", "IDS_ET_PIPE_INBOUND", "Inbound"),
            ("FILE_PIPE_OUTBOUND", "configuration", "IDS_ET_PIPE_OUTBOUND", "Outbound"),
            ("FILE_PIPE_FULL_DUPLEX", "configuration", "IDS_ET_PIPE_DUPLEX", "Duplex"),
            ("FILE_PIPE_DISCONNECTED_STATE", "state", "IDS_ET_SESSION_STATE_DISCONNECTED", "Disconnected"),
            ("FILE_PIPE_LISTENING_STATE", "state", "IDS_ET_PIPE_LISTENING", "Listening"),
            ("FILE_PIPE_CONNECTED_STATE", "state", "IDS_ET_SESSION_STATE_CONNECTED", "Connected"),
            ("FILE_PIPE_CLOSING_STATE", "state", "IDS_ET_PIPE_CLOSING", "Closing"),
            ("FILE_PIPE_BYTE_STREAM_MODE", "read", "IDS_ET_PIPE_STREAM", "Stream"),
            ("FILE_PIPE_MESSAGE_MODE", "read", "IDS_ET_PIPE_MESSAGE", "Message"),
            ("FILE_PIPE_QUEUE_OPERATION", "completion", "IDS_ET_PIPE_QUEUE", "Queue"),
            ("FILE_PIPE_COMPLETE_OPERATION", "completion", "IDS_ET_PIPE_COMPLETE", "Complete"),
        )

        for function, columns in functions.items():
            body = compact(function_body(source, function))
            self.assertEqual(body.count("EtGetUiString("), 16)

            for case, column_kind, symbol, english in case_routes:
                with self.subTest(function=function, case=case):
                    self.assertIn(
                        f'case{case}:PhSetListViewSubItem(Context->ListViewWndHandle,'
                        f'lvItemIndex,{columns[column_kind]},EtGetUiString({symbol},'
                        f'L"{english}"));break;',
                        body,
                    )

            self.assertIn(
                "if(pipeLocalInfo.MaximumInstances==FILE_PIPE_UNLIMITED_INSTANCES)"
                f"PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,{columns['maximum']},"
                'EtGetUiString(IDS_ET_PIPE_UNLIMITED,L"Unlimited"));else'
                f"PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,{columns['maximum']},"
                "PhaFormatUInt64(pipeLocalInfo.MaximumInstances,FALSE)->Buffer);",
                body,
            )
            self.assertIn(
                "if(pipeLocalInfo.NamedPipeType&FILE_PIPE_REJECT_REMOTE_CLIENTS)"
                f"PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,{columns['remote']},"
                'EtGetUiString(IDS_ET_PIPE_REJECT,L"Reject"));else'
                f"PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,{columns['remote']},"
                'EtGetUiString(IDS_ET_PIPE_ACCEPT,L"Accept"));',
                body,
            )

        for english, symbol in ROUTES.items():
            with self.subTest(resource=symbol):
                self.assertEqual(
                    len(re.findall(
                        rf"EtGetUiString\(\s*{symbol}\s*,\s*L\"{re.escape(english)}\"\s*\)",
                        source,
                    )),
                    EXPECTED_OCCURRENCES[english],
                )

    def test_runtime_pipe_data_paths_are_unchanged(self):
        source = source_text()
        direct_routes = {
            "EtEnumerateNamedPipeDirectory": (
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,1,pipeName->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,2,PH_AUTO_T(PH_STRING,PhStdGetClientIdName(&clientId))->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,6,PhaFormatUInt64(pipeLocalInfo.CurrentInstances,FALSE)->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,7,PhaFormatSize(pipeLocalInfo.ReadDataAvailable,FALSE)->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,8,PhaFormatSize(pipeLocalInfo.OutboundQuota,FALSE)->Buffer);",
            ),
            "EtAddNamedPipeHandleToListView": (
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,1,PhGetString(PipeName));",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,2,PH_AUTO_T(PH_STRING,PhStdGetClientIdName(&clientId))->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,3,handle);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,4,access);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,8,PhaFormatUInt64(pipeLocalInfo.CurrentInstances,FALSE)->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,9,PhaFormatSize(pipeLocalInfo.ReadDataAvailable,FALSE)->Buffer);",
                "PhSetListViewSubItem(Context->ListViewWndHandle,lvItemIndex,10,PhaFormatSize(pipeLocalInfo.OutboundQuota,FALSE)->Buffer);",
            ),
        }

        for function, expected in direct_routes.items():
            body = compact(function_body(source, function))
            for route in expected:
                with self.subTest(function=function, route=route):
                    self.assertIn(route, body)

    def test_resources_json_and_build_counts_are_exact(self):
        defines, header = parse_defines()
        english = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.zh-cn.rc")
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for symbol, resource_id, en, zh, owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(data[owner].get(en), zh)
                other = "strings" if owner == "native_strings" else "native_strings"
                self.assertNotIn(en, data[other])

        self.assertEqual([row[1] for row in RESOURCES], list(range(61188, 61200)))
        self.assertEqual(sorted(defines.values()), list(range(61000, 61230)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 230)
        self.assertEqual(len(chinese), 230)
        self.assertRegex(
            header, r"(?m)^#define IDS_ET_CACHED_LAST\s+IDS_ET_WORKER_THREAD_CONTEXT_FORMAT$"
        )
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+61230$")

        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("plugins\\ExtendedTools.dll=230"), 2)

        generator_test = (
            REPO_ROOT / "tools" / "zhcn" / "tests" / "test_native_resource_generation.py"
        ).read_text(encoding="utf-8")
        self.assertIn('self.assertIn("1671 strings", result.stdout)', generator_test)

    def test_migrated_enum_literals_leave_the_fresh_audit(self):
        audit = load_audit_module()
        entries = []
        audit.scan_c_file(str(PLUGIN_ROOT / "namedpipes.c"), entries)

        migrated = set(ROUTES)
        self.assertFalse({entry["english"] for entry in entries} & migrated)


if __name__ == "__main__":
    unittest.main()
