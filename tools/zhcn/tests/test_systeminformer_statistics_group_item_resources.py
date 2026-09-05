#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SYSTEM_INFORMER_ROOT = REPO_ROOT / "SystemInformer"


# symbol | id | English | zh-CN | group | index
ROUTE_DATA = r"""
IDS_PH_STAT_CPU|2340|CPU|CPU|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CPU
IDS_PH_STAT_CPUUSER|2341|CPU (user)|CPU (用户)|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CPUUSER
IDS_PH_STAT_CPUKERNEL|2342|CPU (kernel)|CPU (内核)|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CPUKERNEL
IDS_PH_STAT_CPUAVERAGE|2343|CPU (average)|CPU (平均)|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CPUAVERAGE
IDS_PH_STAT_CPURELATIVE|2344|CPU (relative)|CPU (相对)|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CPURELATIVE
IDS_PH_STAT_CYCLES|2345|Cycles|周期|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CYCLES
IDS_PH_STAT_CYCLESDELTA|2346|Cycles delta|周期增量|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CYCLESDELTA
IDS_PH_STAT_CONTEXTSWITCHES|2347|Context switches|上下文切换|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CONTEXTSWITCHES
IDS_PH_STAT_CONTEXTSWITCHESDELTA|2348|Context switches delta|上下文切换增量|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_CONTEXTSWITCHESDELTA
IDS_PH_STAT_KERNELTIME|2349|Kernel time|内核时间|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_KERNELTIME
IDS_PH_STAT_KERNELDELTA|2350|Kernel delta|内核时间增量|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_KERNELDELTA
IDS_PH_STAT_USERTIME|2351|User time|用户时间|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_USERTIME
IDS_PH_STAT_USERDELTA|2352|User delta|用户时间增量|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_USERDELTA
IDS_PH_STAT_TOTALTIME|2353|Total time|总时间|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_TOTALTIME
IDS_PH_STAT_TOTALDELTA|2354|Total delta|总时间增量|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_TOTALDELTA
IDS_PH_STAT_PRIORITY|2355|Priority|优先级|PH_PROCESS_STATISTICS_CATEGORY_CPU|PH_PROCESS_STATISTICS_INDEX_PRIORITY
IDS_PH_STAT_PRIVATEBYTES|2356|Private bytes|专用字节|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PRIVATEBYTES
IDS_PH_STAT_PRIVATEBYTESDELTA|2357|Private bytes delta|专用字节增量|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PRIVATEBYTESDELTA
IDS_PH_STAT_PEAKPRIVATEBYTES|2358|Peak private bytes|专用字节峰值|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PEAKPRIVATEBYTES
IDS_PH_STAT_VIRTUALSIZE|2359|Virtual size|虚拟大小|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_VIRTUALSIZE
IDS_PH_STAT_PEAKVIRTUALSIZE|2360|Peak virtual size|虚拟大小峰值|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PEAKVIRTUALSIZE
IDS_PH_STAT_PAGEFAULTS|2361|Page faults|页面错误|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PAGEFAULTS
IDS_PH_STAT_PAGEFAULTSDELTA|2362|Page faults delta|页面错误增量|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PAGEFAULTSDELTA
IDS_PH_STAT_HARDFAULTS|2363|Hard faults|硬错误|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_HARDFAULTS
IDS_PH_STAT_HARDFAULTSDELTA|2364|Hard faults delta|硬错误增量|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_HARDFAULTSDELTA
IDS_PH_STAT_WORKINGSET|2365|Working set|工作集|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_WORKINGSET
IDS_PH_STAT_PEAKWORKINGSET|2366|Peak working set|工作集峰值|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PEAKWORKINGSET
IDS_PH_STAT_PRIVATEWS|2367|Private WS|专用 WS|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PRIVATEWS
IDS_PH_STAT_SHAREABLEWS|2368|Shareable WS|可共享 WS|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_SHAREABLEWS
IDS_PH_STAT_SHAREDWS|2369|Shared WS|共享 WS|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_SHAREDWS
IDS_PH_STAT_PAGEDPOOL|2370|Paged pool bytes|分页池字节数|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PAGEDPOOL
IDS_PH_STAT_PEAKPAGEDPOOL|2371|Peak paged pool bytes|分页池字节数峰值|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PEAKPAGEDPOOL
IDS_PH_STAT_NONPAGED|2372|Nonpaged pool bytes|非分页池字节数|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_NONPAGED
IDS_PH_STAT_PEAKNONPAGED|2373|Peak nonpaged pool bytes|非分页池字节数峰值|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PEAKNONPAGED
IDS_PH_STAT_SHAREDCOMMIT|2374|Shared commit|共享提交|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_SHAREDCOMMIT
IDS_PH_STAT_PRIVATECOMMIT|2375|Private commit|专用提交|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PRIVATECOMMIT
IDS_PH_STAT_PEAKPRIVATECOMMIT|2376|Peak private commit|专用提交峰值|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PEAKPRIVATECOMMIT
IDS_PH_STAT_PAGEPRIORITY|2377|Page priority|页优先级|PH_PROCESS_STATISTICS_CATEGORY_MEMORY|PH_PROCESS_STATISTICS_INDEX_PAGEPRIORITY
""".strip()


ROUTES = [tuple(line.split("|")) for line in ROUTE_DATA.splitlines()]
ROUTES = [
    (symbol, int(resource_id), english, chinese, group, index)
    for symbol, resource_id, english, chinese, group, index in ROUTES
]

NATIVE_KEYS = {
    "Kernel delta",
    "User delta",
    "Total time",
    "Total delta",
    "Hard faults",
    "Hard faults delta",
    "Paged pool bytes",
    "Peak paged pool bytes",
    "Nonpaged pool bytes",
    "Peak nonpaged pool bytes",
    "Private commit",
    "Peak private commit",
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_si_statistics", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(masked_text, function_name):
    match = re.search(
        rf"\b{re.escape(function_name)}\s*\([^;]*?\)\s*\{{",
        masked_text,
        re.S,
    )
    if not match:
        raise AssertionError(f"function not found: {function_name}")

    start = match.end() - 1
    depth = 0
    for offset in range(start, len(masked_text)):
        if masked_text[offset] == "{":
            depth += 1
        elif masked_text[offset] == "}":
            depth -= 1
            if depth == 0:
                return masked_text[start + 1:offset]

    raise AssertionError(f"unterminated function: {function_name}")


def parse_statistics_routes():
    audit = load_audit_module()
    text = (SYSTEM_INFORMER_ROOT / "prpgstat.c").read_text(encoding="utf-8")
    body = function_body(audit.mask_c_comments(text), "PhpUpdateStatisticsAddListViewGroups")
    target_indices = {index for *_prefix, index in ROUTES}
    routes = []

    for _name, args, _spans, _start in audit.find_calls(
        body, {"PhListView_AddGroupItem"}
    ):
        if len(args) != 5 or args[2].strip() not in target_indices:
            continue

        match = re.fullmatch(
            r"\s*PhGetApplicationUiString\s*\(\s*(IDS_PH_[A-Z0-9_]+)\s*\)\s*",
            args[3],
            re.S,
        )
        routes.append((
            args[1].strip(),
            args[2].strip(),
            match.group(1) if match else None,
            re.sub(r"\s+", "", args[4]),
        ))

    return routes


def parse_defines():
    text = (SYSTEM_INFORMER_ROOT / "resource.h").read_text(encoding="utf-8")
    numeric = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)\s*$", text
        )
    }
    app_resource_ids = (
        REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
    ).read_text(encoding="utf-8")
    numeric.update({
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)\s*$",
            app_resource_ids,
        )
    })
    aliases = {
        symbol: value
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PH_(?:FIRST|LAST))\s+(IDS_PH_[A-Z0-9_]+)\s*$",
            text,
        )
    }
    return numeric, aliases, text


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class SystemInformerStatisticsGroupItemResourcesTests(unittest.TestCase):
    def test_table_has_exact_cpu_and_memory_scope(self):
        self.assertEqual(len(ROUTES), 38)
        self.assertEqual(len({symbol for symbol, *_ in ROUTES}), 38)
        self.assertEqual(
            Counter(group for *_prefix, group, _index in ROUTES),
            {
                "PH_PROCESS_STATISTICS_CATEGORY_CPU": 16,
                "PH_PROCESS_STATISTICS_CATEGORY_MEMORY": 22,
            },
        )

    def test_active_source_routes_match_in_order(self):
        actual = parse_statistics_routes()
        expected = [
            (group, index, symbol, f"(PVOID){index}")
            for symbol, _resource_id, _en, _zh, group, index in ROUTES
        ]

        self.assertEqual(actual, expected)

    def test_resource_ids_and_full_cached_range_are_contiguous(self):
        numeric, aliases, header = parse_defines()
        english = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh, *_ in ROUTES:
            self.assertEqual(numeric.get(symbol), resource_id, symbol)
            self.assertEqual(english.get(symbol), en, symbol)
            self.assertEqual(chinese.get(symbol), zh, symbol)

        self.assertEqual(aliases.get("IDS_PH_FIRST"), "IDS_PH_RESET_ALL_SETTINGS")
        self.assertEqual(aliases.get("IDS_PH_LAST"), "IDS_PH_STAT_PAGEPRIORITY")
        first_id = numeric[aliases["IDS_PH_FIRST"]]
        last_id = numeric[aliases["IDS_PH_LAST"]]
        expected_ids = set(range(first_id, last_id + 1))

        self.assertEqual(
            {value for value in numeric.values() if first_id <= value <= last_id},
            expected_ids,
        )
        self.assertEqual({numeric[symbol] for symbol in english}, expected_ids)
        self.assertEqual({numeric[symbol] for symbol in chinese}, expected_ids)
        self.assertEqual(len(english), len(expected_ids))
        self.assertEqual(len(chinese), len(expected_ids))
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2378$")

    def test_json_uses_existing_strings_and_twelve_native_strings(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        strings = data["strings"]
        native_strings = data["native_strings"]

        self.assertEqual(len(NATIVE_KEYS), 12)
        self.assertFalse(strings.keys() & native_strings.keys())
        for _symbol, _resource_id, english, chinese, *_ in ROUTES:
            table = native_strings if english in NATIVE_KEYS else strings
            other = strings if english in NATIVE_KEYS else native_strings
            self.assertEqual(table.get(english), chinese, english)
            self.assertNotIn(english, other)

    def test_ci_requires_exact_system_informer_resource_count_twice(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")

        self.assertEqual(workflow.count("sys_info.exe=378"), 2)
        self.assertNotIn("sys_info.exe=340", workflow)

    def test_audit_removes_batch_and_preserves_expected_remainder(self):
        audit = load_audit_module()
        entries = []
        for path in sorted(SYSTEM_INFORMER_ROOT.rglob("*.c")):
            audit.scan_c_file(str(path), entries)

        remaining = [
            entry for entry in entries
            if entry["category"] == "c_listview_group_item"
        ]
        target_english = {
            english for _symbol, _id, english, *_ in ROUTES
            if english != "Cycles"  # The out-of-scope Energy group reuses this label.
        }

        self.assertFalse(target_english & {entry["english"] for entry in remaining})
        self.assertEqual(len(remaining), 94)
        self.assertEqual(len({entry["english"] for entry in remaining}), 87)


if __name__ == "__main__":
    unittest.main()
