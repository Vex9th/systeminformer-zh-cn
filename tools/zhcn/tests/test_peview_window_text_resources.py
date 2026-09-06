#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


# symbol | id | English | zh-CN | translation owner
RESOURCE_DATA = r"""
IDS_PV_UNNAMED|3239|(unnamed)|（未命名）|native_strings
IDS_PV_CALCULATING|3240|Calculating...|正在计算...|native_strings
IDS_PV_CLOSE|3241|Close|关闭|strings
IDS_PV_ERROR|3242|ERROR|错误|strings
IDS_PV_LOADING|3243|Loading...|正在加载...|native_strings
IDS_PV_NOT_AVAILABLE|3244|N/A|不适用|strings
IDS_PV_RESOLVING|3245|Resolving...|正在解析...|native_strings
IDS_PV_VERIFYING_COMPANY|3246|(Verifying...) %s|（正在验证...）%s|native_strings
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in RESOURCES
]


# file | API | arguments before the localized text | resource
DIRECT_ROUTE_DATA = r"""
cfgprp.c|PhSetListViewSubItem|ListViewHandle,lvItemIndex,3|IDS_PV_UNNAMED
ehcontprp.c|PhSetListViewSubItem|ListViewHandle,lvItemIndex,2|IDS_PV_UNNAMED
pepogoprp.c|PhSetListViewSubItem|ListViewHandle,lvItemIndex,2|IDS_PV_UNNAMED
volatileprp.c|PhSetListViewSubItem|ListViewHandle,lvItemIndex,2|IDS_PV_UNNAMED
peprp.c|PhSetListViewSubItem|ListViewHandle,PVP_IMAGE_GENERAL_INDEX_ENTROPY,1|IDS_PV_CALCULATING
prpsh.c|PhSetDialogItemText|hwnd,IDCANCEL|IDS_PV_CLOSE
hashprp.c|PhSetListViewSubItem|ListViewHandle,lvItemIndex,2|IDS_PV_ERROR
exlfprp.c|PhSetDialogItemText|WindowHandle,IDC_NAME|IDS_PV_LOADING
exlfprp.c|PhSetDialogItemText|WindowHandle,IDC_COMPANYNAME|IDS_PV_LOADING
exlfprp.c|PhSetDialogItemText|WindowHandle,IDC_VERSION|IDS_PV_LOADING
peheaderprp.c|PhSetListViewSubItem|Context->ListViewHandle,PVP_IMAGE_HEADER_INDEX_OPT_BASEOFDATA,1|IDS_PV_NOT_AVAILABLE
peprp.c|PhSetListViewSubItem|ListViewHandle,PVP_IMAGE_GENERAL_INDEX_DEBUGREPRO,1|IDS_PV_NOT_AVAILABLE
peprp.c|PhSetListViewSubItem|ListViewHandle,PVP_IMAGE_GENERAL_INDEX_DEBUGVCFEATURE,1|IDS_PV_NOT_AVAILABLE
peprp.c|PhSetListViewSubItem|ListViewHandle,PVP_IMAGE_GENERAL_INDEX_ENTRYPOINT,1|IDS_PV_RESOLVING
""".strip()


DIRECT_ROUTES = [tuple(line.split("|")) for line in DIRECT_ROUTE_DATA.splitlines()]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_window_text", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_text(source_name):
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PEVIEW_ROOT / source_name).read_text(encoding="utf-8-sig")
    )


def normalized(expression):
    return re.sub(r"\s+", "", expression)


def parse_resource_calls(source_name):
    audit = load_audit_module()
    text = source_text(source_name)
    apis = {"PhSetDialogItemText", "PhSetListViewSubItem"}
    routes = []

    for api, args, _spans, _start in audit.find_calls(text, apis):
        for argument_index, argument in enumerate(args):
            match = re.fullmatch(
                r"\s*PvpLoadUiString\(\s*(IDS_PV_[A-Z0-9_]+)\s*\)\s*",
                argument,
                re.S,
            )
            if match:
                routes.append(
                    (
                        source_name,
                        api,
                        ",".join(normalized(arg) for arg in args[:argument_index]),
                        match.group(1),
                    )
                )

        if api == "PhSetListViewSubItem" and len(args) == 4:
            match = re.fullmatch(
                r"\s*ErrorText\s*\?\s*ErrorText\s*:\s*"
                r"PvpLoadUiString\(\s*(IDS_PV_[A-Z0-9_]+)\s*\)\s*",
                args[3],
                re.S,
            )
            if match:
                routes.append(
                    (
                        source_name,
                        api,
                        ",".join(normalized(arg) for arg in args[:3]),
                        match.group(1),
                    )
                )

    return routes


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


class PeViewWindowTextResourcesTests(unittest.TestCase):
    def test_direct_routes_keep_exact_api_and_argument_positions(self):
        source_order = (
            "cfgprp.c",
            "ehcontprp.c",
            "pepogoprp.c",
            "volatileprp.c",
            "peprp.c",
            "prpsh.c",
            "hashprp.c",
            "exlfprp.c",
            "peheaderprp.c",
        )
        actual = [
            route
            for source_name in source_order
            for route in parse_resource_calls(source_name)
            if route[3] in {resource[0] for resource in RESOURCES}
        ]
        expected = [
            (source, api, normalized(arguments), symbol)
            for source, api, arguments, symbol in DIRECT_ROUTES
        ]

        self.assertEqual(Counter(actual), Counter(expected))

    def test_exlf_indirect_routes_are_const_and_exact(self):
        source = source_text("exlfprp.c")

        self.assertEqual(
            len(re.findall(
                r"\bPCWSTR\s+type\s*=\s*"
                r"PvpLoadUiString\(\s*IDS_PV_NOT_AVAILABLE\s*\)\s*;",
                source,
            )),
            2,
        )
        self.assertEqual(
            len(re.findall(
                r"\btype\s*=\s*PvpLoadUiString\(\s*IDS_PV_ERROR\s*\)\s*;",
                source,
            )),
            2,
        )
        self.assertNotRegex(source, r"\bPWSTR\s+type\b")

    def test_na_fallbacks_preserve_borrowed_and_owned_lifetimes(self):
        header = source_text("include/peview.h")
        clr_source = source_text("clrprp.c")

        self.assertRegex(
            header,
            r"FORCEINLINE\s+PCWSTR\s+PvpGetStringOrNa\s*\(\s*"
            r"_In_opt_\s+PPH_STRING\s+String",
        )
        self.assertRegex(
            header,
            r"return\s+PhGetStringOrDefault\(\s*String\s*,\s*"
            r"PvpLoadUiString\(\s*IDS_PV_NOT_AVAILABLE\s*\)\s*\)\s*;",
        )
        self.assertEqual(
            len(re.findall(
                r"return\s+PhCreateString\(\s*"
                r"PvpLoadUiString\(\s*IDS_PV_NOT_AVAILABLE\s*\)\s*\)\s*;",
                clr_source,
            )),
            2,
        )

    def test_verifying_company_uses_one_localized_owned_format(self):
        source = source_text("peprp.c")

        self.assertRegex(
            source,
            r"\bstring\s*=\s*PhFormatString\(\s*"
            r"PvpLoadUiString\(\s*IDS_PV_VERIFYING_COMPANY\s*\)\s*,\s*"
            r"PvpGetStringOrNa\(\s*PvImageVersionInfo\.CompanyName\s*\)\s*"
            r"\)\s*;",
        )
        self.assertNotIn('PhConcatStrings2(L"(Verifying...) "', source)

    def test_hash_helper_accepts_const_text_and_localizes_all_fallbacks(self):
        source = source_text("hashprp.c")
        signature = re.search(
            r"\bVOID\s+PvPeHashesAddListViewItem\s*\((.*?)\)\s*\{",
            source,
            re.S,
        )
        self.assertIsNotNone(signature)
        self.assertRegex(signature.group(1), r"_In_opt_\s+PCWSTR\s+ErrorText")
        self.assertRegex(signature.group(1), r"_In_\s+PCWSTR\s+Text")
        self.assertEqual(
            len(re.findall(
                r"PvPeHashesAddListViewItem\([^;]*?FALSE\s*,\s*"
                r"PvpLoadUiString\(\s*IDS_PV_NOT_AVAILABLE\s*\)\s*,",
                source,
                re.S,
            )),
            3,
        )

    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for symbol, resource_id, en, zh, _owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(sorted(defines.values()), list(range(3000, 3278)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 278)
        self.assertEqual(len(chinese), 278)
        self.assertRegex(
            header,
            r"(?m)^#define IDS_PV_LAST\s+IDS_PV_MACHINE_ARM64_ARM64X$",
        )
        self.assertRegex(
            header,
            r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3278$",
        )

    def test_json_uses_existing_owner_and_has_no_layer_overlap(self):
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        strings = data["strings"]
        native_strings = data["native_strings"]

        self.assertFalse(strings.keys() & native_strings.keys())
        for _symbol, _id, english, chinese, owner in RESOURCES:
            with self.subTest(english=english):
                table = data[owner]
                other = strings if owner == "native_strings" else native_strings
                self.assertEqual(table.get(english), chinese)
                self.assertNotIn(english, other)

    def test_ci_requires_exact_peview_resource_count_twice(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")

        self.assertEqual(workflow.count("peview.exe=278"), 2)
        self.assertNotIn("peview.exe=258", workflow)
        self.assertNotIn("peview.exe=247", workflow)
        self.assertNotIn("peview.exe=246", workflow)

    def test_audit_fresh_peview_window_text_boundary_is_exact(self):
        audit = load_audit_module()
        entries = []

        for path in sorted(PEVIEW_ROOT.rglob("*.c")):
            audit.scan_c_file(str(path), entries)

        remaining = [
            entry
            for entry in entries
            if entry["category"] == "c_window_text"
            and entry["file"].startswith("tools/peview/")
        ]
        self.assertEqual(len({entry["english"] for entry in remaining}), 9)
        self.assertEqual(len(remaining), 9)
        self.assertFalse(
            {entry["english"] for entry in remaining}
            & {resource[2] for resource in RESOURCES}
        )


if __name__ == "__main__":
    unittest.main()
