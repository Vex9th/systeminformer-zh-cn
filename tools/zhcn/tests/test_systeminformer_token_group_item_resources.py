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
RESOURCE_DATA = r"""
IDS_PH_TOKEN_RESOLVING|2442|Resolving...|正在解析...
IDS_PH_TOKEN_TYPE|2443|Type|类型
IDS_PH_TOKEN_IMPERSONATION_LEVEL|2444|Impersonation level|模拟级别
IDS_PH_TOKEN_LUID|2445|Token LUID|令牌 LUID
IDS_PH_TOKEN_AUTHENTICATION_LUID|2446|Authentication LUID|身份验证 LUID
IDS_PH_TOKEN_MODIFIEDID_LUID|2447|ModifiedId LUID|修改 ID LUID
IDS_PH_TOKEN_ORIGIN_LUID|2448|Origin LUID|来源 LUID
IDS_PH_TOKEN_MEMORY_USED|2449|Memory used|已用内存
IDS_PH_TOKEN_MEMORY_AVAILABLE|2450|Memory available|可用内存
IDS_PH_TOKEN_OBJECT_PATH|2451|Token object path|令牌对象路径
IDS_PH_TOKEN_SDDL|2452|Token SDDL|令牌 SDDL
IDS_PH_TOKEN_TRUSTLEVEL_SID|2453|TrustLevel Sid|信任级别 SID
IDS_PH_TOKEN_TRUSTLEVEL_NAME|2454|TrustLevel Name|信任级别名称
IDS_PH_TOKEN_FOLDER_PATH|2455|Folder path|文件夹路径
IDS_PH_TOKEN_REGISTRY_PATH|2456|Registry path|注册表路径
IDS_PH_TOKEN_HWID_PUBLISHER|2457|HWID (Publisher)|HWID（发布者）
IDS_PH_TOKEN_HWID_USER|2458|HWID (User)|HWID（用户）
IDS_PH_TOKEN_NAME|2459|Name|名称
IDS_PH_TOKEN_SID|2460|SID|SID
IDS_PH_TOKEN_NUMBER|2461|Number|编号
IDS_PH_TOKEN_LPAC|2462|LPAC|LPAC
IDS_PH_TOKEN_PATH|2463|Path|路径
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in RESOURCES
]
RESOURCE_BY_SYMBOL = {
    symbol: (resource_id, english, chinese)
    for symbol, resource_id, english, chinese in RESOURCES
}


# symbol | list-view expression | group expression | item-data expression
ROUTE_DATA = r"""
IDS_PH_TOKEN_RESOLVING|TokenPageContext->ListViewHandle|lvitem->GroupId|lvitem
IDS_PH_TOKEN_TYPE|context->ListViewHandle|0|NULL
IDS_PH_TOKEN_IMPERSONATION_LEVEL|context->ListViewHandle|0|NULL
IDS_PH_TOKEN_LUID|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_AUTHENTICATION_LUID|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_MODIFIEDID_LUID|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_ORIGIN_LUID|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_MEMORY_USED|context->ListViewHandle|2|NULL
IDS_PH_TOKEN_MEMORY_AVAILABLE|context->ListViewHandle|2|NULL
IDS_PH_TOKEN_OBJECT_PATH|context->ListViewHandle|3|NULL
IDS_PH_TOKEN_SDDL|context->ListViewHandle|3|NULL
IDS_PH_TOKEN_TRUSTLEVEL_SID|context->ListViewHandle|trustLevelGroupIndex|NULL
IDS_PH_TOKEN_TRUSTLEVEL_NAME|context->ListViewHandle|trustLevelGroupIndex|NULL
IDS_PH_TOKEN_FOLDER_PATH|context->ListViewHandle|profileGroupIndex|NULL
IDS_PH_TOKEN_REGISTRY_PATH|context->ListViewHandle|profileGroupIndex|NULL
IDS_PH_TOKEN_HWID_PUBLISHER|context->ListViewHandle|systemIdGroupIndex|NULL
IDS_PH_TOKEN_HWID_USER|context->ListViewHandle|systemIdGroupIndex|NULL
IDS_PH_TOKEN_NAME|context->ListViewHandle|0|NULL
IDS_PH_TOKEN_TYPE|context->ListViewHandle|0|NULL
IDS_PH_TOKEN_SID|context->ListViewHandle|0|NULL
IDS_PH_TOKEN_NUMBER|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_LPAC|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_OBJECT_PATH|context->ListViewHandle|1|NULL
IDS_PH_TOKEN_NAME|context->ListViewHandle|2|NULL
IDS_PH_TOKEN_SID|context->ListViewHandle|2|NULL
IDS_PH_TOKEN_NAME|context->ListViewHandle|3|NULL
IDS_PH_TOKEN_PATH|context->ListViewHandle|3|NULL
IDS_PH_TOKEN_FOLDER_PATH|context->ListViewHandle|4|NULL
IDS_PH_TOKEN_REGISTRY_PATH|context->ListViewHandle|4|NULL
""".strip()


ROUTES = [tuple(line.split("|")) for line in ROUTE_DATA.splitlines()]
STRING_KEYS = {"Type", "Name", "SID", "Path"}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_si_token_groups", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(expression):
    return re.sub(r"\s+", "", expression)


def parse_active_routes():
    audit = load_audit_module()
    source = (SYSTEM_INFORMER_ROOT / "tokprp.c").read_text(encoding="utf-8")
    masked = audit.mask_c_comments(source)
    english_to_symbol = {
        english: symbol for symbol, _resource_id, english, _chinese in RESOURCES
    }
    expected_symbols = set(RESOURCE_BY_SYMBOL)
    routes = []

    for _name, args, _spans, _start in audit.find_calls(
        masked, {"PhAddListViewGroupItem"}
    ):
        if len(args) != 5:
            continue

        literal_match = re.fullmatch(r'\s*L"([^"]+)"\s*', args[3], re.S)
        getter_match = re.fullmatch(
            r"\s*PhGetApplicationUiString\s*\(\s*(IDS_PH_[A-Z0-9_]+)\s*\)\s*",
            args[3],
            re.S,
        )
        symbol = None
        if literal_match:
            symbol = english_to_symbol.get(literal_match.group(1))
        elif getter_match and getter_match.group(1) in expected_symbols:
            symbol = getter_match.group(1)

        if symbol:
            routes.append((
                symbol if getter_match else None,
                normalize(args[0]),
                normalize(args[1]),
                normalize(args[2]),
                normalize(args[4]),
            ))

    return routes


def parse_defines():
    header = (SYSTEM_INFORMER_ROOT / "resource.h").read_text(encoding="utf-8")
    app_header = (
        REPO_ROOT / "phlib" / "include" / "phappresourceid.h"
    ).read_text(encoding="utf-8")
    numeric = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)\s*$",
            header + "\n" + app_header,
        )
    }
    aliases = dict(re.findall(
        r"(?m)^#define\s+(IDS_PH_(?:FIRST|LAST))\s+(IDS_PH_[A-Z0-9_]+)\s*$",
        header,
    ))
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


class SystemInformerTokenGroupItemResourceTests(unittest.TestCase):
    def test_table_has_exact_resource_and_route_cardinality(self):
        self.assertEqual(len(RESOURCES), 22)
        self.assertEqual(len({symbol for symbol, *_ in RESOURCES}), 22)
        self.assertEqual(len(ROUTES), 29)
        self.assertEqual(
            Counter(symbol for symbol, *_ in ROUTES),
            Counter({
                "IDS_PH_TOKEN_NAME": 3,
                "IDS_PH_TOKEN_SID": 2,
                "IDS_PH_TOKEN_TYPE": 2,
                "IDS_PH_TOKEN_OBJECT_PATH": 2,
                "IDS_PH_TOKEN_FOLDER_PATH": 2,
                "IDS_PH_TOKEN_REGISTRY_PATH": 2,
                **{
                    symbol: 1
                    for symbol, *_ in RESOURCES
                    if symbol not in {
                        "IDS_PH_TOKEN_NAME",
                        "IDS_PH_TOKEN_SID",
                        "IDS_PH_TOKEN_TYPE",
                        "IDS_PH_TOKEN_OBJECT_PATH",
                        "IDS_PH_TOKEN_FOLDER_PATH",
                        "IDS_PH_TOKEN_REGISTRY_PATH",
                    }
                },
            }),
        )

    def test_active_routes_match_exact_order_and_item_data(self):
        expected = [
            (symbol, normalize(list_view), normalize(group), "MAXINT", normalize(item_data))
            for symbol, list_view, group, item_data in ROUTES
        ]
        self.assertEqual(parse_active_routes(), expected)

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        numeric, aliases, header = parse_defines()
        english = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(SYSTEM_INFORMER_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            self.assertEqual(numeric.get(symbol), resource_id, symbol)
            self.assertEqual(english.get(symbol), en, symbol)
            self.assertEqual(chinese.get(symbol), zh, symbol)

        self.assertEqual(aliases.get("IDS_PH_LAST"), "IDS_PH_MENU_VIRTUALIZATION")
        first_id = numeric[aliases["IDS_PH_FIRST"]]
        last_id = numeric[aliases["IDS_PH_LAST"]]
        expected_ids = set(range(first_id, last_id + 1))
        self.assertEqual(
            {value for value in numeric.values() if first_id <= value <= last_id},
            expected_ids,
        )
        self.assertEqual({numeric[symbol] for symbol in english}, expected_ids)
        self.assertEqual({numeric[symbol] for symbol in chinese}, expected_ids)
        self.assertEqual(len(english), 1051)
        self.assertEqual(len(chinese), 1051)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3051$")

    def test_json_layers_reuse_four_strings_and_add_eighteen_native(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        strings = data["strings"]
        native_strings = data["native_strings"]
        self.assertFalse(strings.keys() & native_strings.keys())

        self.assertEqual(len(STRING_KEYS), 4)
        for _symbol, _resource_id, english, chinese in RESOURCES:
            table = strings if english in STRING_KEYS else native_strings
            other = native_strings if english in STRING_KEYS else strings
            self.assertEqual(table.get(english), chinese, english)
            self.assertNotIn(english, other)

    def test_ci_requires_exact_main_resource_count_twice(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("sys_info.exe=1051"), 2)
        self.assertNotIn("sys_info.exe=475", workflow)

    def test_fresh_systeminformer_scan_has_no_group_item_literals(self):
        audit = load_audit_module()
        entries = []
        for path in sorted(SYSTEM_INFORMER_ROOT.rglob("*.c")):
            audit.scan_c_file(str(path), entries)

        remaining = [
            entry for entry in entries
            if entry["category"] == "c_listview_group_item"
        ]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
