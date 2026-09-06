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
""".strip()


REUSED_RESOURCE_DATA = r"""
IDS_PH_LOGON_NETWORK|2250|Network|网络
IDS_PH_STAT_HANDLES|2394|Handles|句柄
IDS_PH_STAT_CPU|2340|CPU|CPU
IDS_PH_STAT_OTHER|2386|Other|其他
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

    for source_name in ("options.c", "prpgstat.c", "envdlg.c", "sessprp.c"):
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
        self.assertEqual(len(NEW_RESOURCES), 11)
        self.assertEqual(len(REUSED_RESOURCES), 4)
        self.assertEqual(len(ROUTES), 17)
        self.assertEqual(len({symbol for symbol, *_ in NEW_RESOURCES}), 11)
        self.assertEqual(
            Counter(symbol for *_, symbol in ROUTES),
            Counter(
                {
                    "IDS_PH_GROUP_MEMORY": 2,
                    "IDS_PH_GROUP_USER": 2,
                    **{
                        symbol: 1
                        for symbol, *_ in ALL_RESOURCES
                        if symbol not in {"IDS_PH_GROUP_MEMORY", "IDS_PH_GROUP_USER"}
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

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        numeric, aliases, header = parse_defines()
        english = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in ALL_RESOURCES:
            self.assertEqual(numeric.get(symbol), resource_id, symbol)
            self.assertEqual(english.get(symbol), en, symbol)
            self.assertEqual(chinese.get(symbol), zh, symbol)

        self.assertEqual(aliases.get("IDS_PH_FIRST"), "IDS_PH_RESET_ALL_SETTINGS")
        self.assertEqual(aliases.get("IDS_PH_LAST"), "IDS_PH_GROUP_SYSTEM")
        first_id = numeric[aliases["IDS_PH_FIRST"]]
        last_id = numeric[aliases["IDS_PH_LAST"]]
        expected_ids = set(range(first_id, last_id + 1))
        self.assertEqual(
            {value for value in numeric.values() if first_id <= value <= last_id},
            expected_ids,
        )
        self.assertEqual({numeric[symbol] for symbol in english}, expected_ids)
        self.assertEqual({numeric[symbol] for symbol in chinese}, expected_ids)
        self.assertEqual(len(english), 475)
        self.assertEqual(len(chinese), 475)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2475$")

    def test_json_reuses_only_existing_strings(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        strings = data["strings"]
        native_strings = data["native_strings"]
        self.assertFalse(strings.keys() & native_strings.keys())

        for _symbol, _resource_id, english, chinese in ALL_RESOURCES:
            self.assertEqual(strings.get(english), chinese, english)
            self.assertNotIn(english, native_strings)

    def test_ci_requires_exact_main_resource_count_twice(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("sys_info.exe=475"), 2)
        self.assertNotIn("sys_info.exe=464", workflow)

    def test_fresh_scan_removes_only_batch_a_groups(self):
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

        self.assertEqual(len(remaining), 42)
        self.assertEqual(len(remaining_english), 38)
        self.assertEqual(target_english & remaining_english.keys(), {"Memory"})
        self.assertEqual(remaining_english["Memory"], 1)
        self.assertEqual(
            remaining_files,
            Counter({"hndlprp.c": 14, "ntobjprp.c": 10, "tokprp.c": 18}),
        )


if __name__ == "__main__":
    unittest.main()
