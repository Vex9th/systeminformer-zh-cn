#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


# symbol | id | English | zh-CN | source | group
ROUTE_DATA = r"""
IDS_PV_GROUP_MUI|3218|MUI|多语言用户界面（MUI）|pemuiprp.c|0
IDS_PV_GROUP_CHECKSUMS|3219|Checksums|校验和|pemuiprp.c|1
IDS_PV_GROUP_MAIN_NAME_TYPES|3220|MainNameTypes|主名称类型（MainNameTypes）|pemuiprp.c|2
IDS_PV_GROUP_MAIN_TYPE_IDS|3221|MainTypeIDs|主类型 ID（MainTypeIDs）|pemuiprp.c|3
IDS_PV_GROUP_TYPE_NAMES|3222|TypeNames|类型名称（TypeNames）|pemuiprp.c|4
IDS_PV_GROUP_TYPE_IDS|3223|TypeIDs|类型 ID（TypeIDs）|pemuiprp.c|5
IDS_PV_GROUP_FIXED_FILE_INFO|3224|FixedFileInfo|固定文件信息（FixedFileInfo）|versioninfoprp.c|0
IDS_PV_GROUP_STRING_FILE_INFO|3225|StringFileInfo|字符串文件信息（StringFileInfo）|versioninfoprp.c|1
IDS_PV_GROUP_VAR_FILE_INFO|3226|VarFileInfo|变量文件信息（VarFileInfo）|versioninfoprp.c|2
IDS_PV_GROUP_APPX_MANIFEST|3227|AppxManifest|Appx 清单|versioninfoprp.c|3
IDS_PV_GROUP_VOLATILE_RANGE_TABLE|3228|Volatile Range Table|易失性范围表|volatileprp.c|2
IDS_PV_GROUP_VOLATILE_RVA_TABLE|3229|Volatile RVA Table|易失性 RVA 表|volatileprp.c|1
IDS_PV_GROUP_DOS_HEADER|3230|DOS Header|DOS 头|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR
IDS_PV_GROUP_DOS_STUB|3231|DOS Stub|DOS 存根|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB
IDS_PV_GROUP_FILE_HEADER|3232|File Header|文件头|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR
IDS_PV_GROUP_OPTIONAL_HEADER|3233|Optional Header|可选头|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR
IDS_PV_GROUP_OVERLAY_STUB|3234|Overlay Stub|覆盖数据|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OVERLAY
IDS_PV_GROUP_IMAGE_INFORMATION|3235|Image information|映像信息|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO
IDS_PV_GROUP_FILE_INFORMATION|3236|File information|文件信息|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_FILEINFO
IDS_PV_GROUP_DEBUG_INFORMATION|3237|Debug information|调试信息|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_DEBUGINFO
IDS_PV_GROUP_INTERNAL_INFORMATION|3238|Internal information|内部信息|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_EXTRAINFO
""".strip()


ROUTES = [tuple(line.split("|")) for line in ROUTE_DATA.splitlines()]
ROUTES = [
    (symbol, int(resource_id), english, chinese, source, group)
    for symbol, resource_id, english, chinese, source, group in ROUTES
]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_groups", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_defines():
    text = (PEVIEW_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    defines = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PV_[A-Z0-9_]+)\s+(\d+)$",
            text,
        )
    }
    return defines, text


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PV_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


def parse_group_routes(source_name):
    audit = load_audit_module()
    text = audit.mask_c_comments(
        (PEVIEW_ROOT / source_name).read_text(encoding="utf-8-sig")
    )
    pattern = re.compile(
        r"\bPhAddListViewGroup\(\s*[^,]+,\s*"
        r"(?P<group>[A-Z0-9_]+|\d+)\s*,\s*"
        r"PvpLoadUiString\(\s*(?P<symbol>IDS_PV_GROUP_[A-Z0-9_]+)\s*\)\s*"
        r"\)\s*;",
        re.S,
    )
    return [
        (source_name, match.group("group"), match.group("symbol"))
        for match in pattern.finditer(text)
    ]


class PeViewListViewGroupResourcesTests(unittest.TestCase):
    def test_route_table_is_complete_and_has_no_accidental_reuse(self):
        self.assertEqual(len(ROUTES), 21)
        self.assertEqual(len({route[0] for route in ROUTES}), 21)
        self.assertEqual(len({route[2] for route in ROUTES}), 21)
        self.assertEqual(
            Counter(route[4] for route in ROUTES),
            {
                "pemuiprp.c": 6,
                "versioninfoprp.c": 4,
                "volatileprp.c": 2,
                "peheaderprp.c": 5,
                "peprp.c": 4,
            },
        )

    def test_source_routes_match_exact_file_group_and_resource(self):
        source_order = (
            "pemuiprp.c",
            "versioninfoprp.c",
            "volatileprp.c",
            "peheaderprp.c",
            "peprp.c",
        )
        actual = [
            route
            for source_name in source_order
            for route in parse_group_routes(source_name)
        ]
        expected = [
            (source, group, symbol)
            for symbol, _id, _en, _zh, source, group in ROUTES
        ]

        self.assertEqual(actual, expected)

        audit = load_audit_module()
        for source_name in source_order:
            source = audit.mask_c_comments(
                (PEVIEW_ROOT / source_name).read_text(encoding="utf-8-sig")
            )
            for _symbol, _id, english, _zh, route_source, _group in ROUTES:
                if route_source == source_name:
                    self.assertNotRegex(
                        source,
                        rf"PhAddListViewGroup\([^;]*L\"{re.escape(english)}\"[^;]*\);",
                    )

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for symbol, resource_id, en, zh, *_ in ROUTES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(
            [resource_id for _symbol, resource_id, *_rest in ROUTES],
            list(range(3218, 3239)),
        )
        self.assertEqual(sorted(defines.values()), list(range(3000, 3298)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 298)
        self.assertEqual(len(chinese), 298)
        self.assertRegex(
            header,
            r"(?m)^#define IDS_PV_FIRST\s+IDS_PV_MENU_ANSI$",
        )
        self.assertRegex(
            header,
            r"(?m)^#define IDS_PV_LAST\s+IDS_PV_CERTIFICATE_SIZE_FORMAT$",
        )
        self.assertRegex(
            header,
            r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3298$",
        )

    def test_json_owns_all_group_names_as_native_strings(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        strings = data["strings"]
        native_strings = data["native_strings"]

        self.assertFalse(strings.keys() & native_strings.keys())
        for _symbol, _id, english, chinese, *_ in ROUTES:
            with self.subTest(english=english):
                self.assertEqual(native_strings.get(english), chinese)
                self.assertNotIn(english, strings)

    def test_ci_requires_exact_peview_resource_count_twice(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")

        self.assertEqual(workflow.count("peview.exe=311"), 2)
        self.assertNotIn("peview.exe=258", workflow)
        self.assertNotIn("peview.exe=247", workflow)
        self.assertNotIn("peview.exe=246", workflow)
        self.assertNotIn("peview.exe=218", workflow)

    def test_ui_string_cache_covers_new_last_id_before_ui_startup(self):
        source = (PEVIEW_ROOT / "main.c").read_text(encoding="utf-8-sig")

        self.assertIn(
            "PvpUiStrings[IDS_PV_LAST - IDS_PV_FIRST + 1]",
            source,
        )
        self.assertRegex(
            source,
            r"for \(resourceId = IDS_PV_FIRST; resourceId <= IDS_PV_LAST; "
            r"resourceId\+\+\)",
        )
        self.assertLess(
            source.index("if (!PvpInitializeUiStrings())"),
            source.index("PvpInitializeMutant();"),
        )

    def test_audit_has_no_peview_listview_group_literals(self):
        audit = load_audit_module()
        entries = []

        for source_name in {
            "pemuiprp.c",
            "versioninfoprp.c",
            "volatileprp.c",
            "peheaderprp.c",
            "peprp.c",
        }:
            audit.scan_c_file(str(PEVIEW_ROOT / source_name), entries)

        remaining = [
            entry
            for entry in entries
            if entry["category"] == "c_listview_group"
            and entry["file"].startswith("tools/peview/")
        ]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
