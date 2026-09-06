#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


RESOURCE_DATA = r'''
IDS_PV_CLR_TABLE_TITLE_FORMAT|3287|CLR Table: %s|CLR 表：%s
IDS_PV_MENU_COPY_COLUMN_FORMAT|3288|Copy "%s"|复制“%s”
IDS_PV_IMAGE_SIZE_OVERLAY_FORMAT|3289|%s (incorrect, %s) (overlay, %s - %s)|%s（不正确，实际为 %s）（覆盖数据，%s - %s）
IDS_PV_CHECKSUM_VERIFYING_FORMAT|3290|0x%I32x (verifying...)|0x%I32x（正在验证...）
IDS_PV_CHECKSUM_MISSING_FORMAT|3291|0x0 (real 0x%I32x)|0x0（实际为 0x%I32x）
IDS_PV_CHECKSUM_MISMATCH_FORMAT|3292|0x%I32x (incorrect, real 0x%I32x)|0x%I32x（不正确，实际为 0x%I32x）
IDS_PV_VERIFIED_LINK_FORMAT|3293|<a>(Verified) %s</a>|<a>（已验证）%s</a>
IDS_PV_VERIFIED_COMPANY_FORMAT|3294|(Verified) %s|（已验证）%s
IDS_PV_UNVERIFIED_COMPANY_FORMAT|3295|(UNVERIFIED) %s|（未验证）%s
IDS_PV_PROPERTIES_TITLE_FORMAT|3296|%s Properties|%s 属性
IDS_PV_CERTIFICATE_SIZE_FORMAT|3297|Size: %s (Certs: %s)|大小：%s（证书：%s）
'''.strip()


RESOURCES = [tuple(row.split("|")) for row in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in RESOURCES
]


RETAINED_RUNTIME_FORMATS = Counter(
    {
        "%lu.%lu": 8,
        "%s (%s)": 23,
        "%s - %s": 1,
        "%s+0x%llx": 4,
        "%u.%u": 1,
        "0x%I32x": 3,
        "0x%llx": 3,
        "0x%lx": 2,
        "C/C++ (%lu), GS (%lu), sdl (%lu), guardN (%lu), Pre-VC++ 11.00 (%lu)": 1,
    }
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "zhcn_audit_peview_remaining_native", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def masked_source(filename):
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PEVIEW_ROOT / filename).read_text(encoding="utf-8-sig")
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
                return text[start + 1 : offset]
    raise AssertionError(f"unterminated function: {function_name}")


def parse_defines():
    text = (PEVIEW_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    defines = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_PV_[A-Z0-9_]+)\s+(\d+)$", text
        )
    }
    return defines, text


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PV_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


class PeViewRemainingNativeResourcesTests(unittest.TestCase):
    def test_resources_are_contiguous_and_match_both_stringtables(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCES], list(range(3287, 3298)))
        self.assertEqual(sorted(defines.values()), list(range(3000, 3298)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 298)
        self.assertEqual(len(chinese), 298)
        self.assertRegex(
            header,
            r"(?m)^#define IDS_PV_LAST\s+IDS_PV_CERTIFICATE_SIZE_FORMAT$",
        )
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3298$")

    def test_window_titles_and_certificate_label_use_complete_formats(self):
        clr = function_body(
            masked_source("clrprptables.c"), "PvpPeClrTablePreviewDlgProc"
        )
        tab = function_body(masked_source("peprpwnd.c"), "PvTabWindowDialogProc")
        certificates = function_body(
            masked_source("secprp.c"), "PvpPeEnumerateFileCertificates"
        )

        self.assertRegex(
            clr,
            re.compile(
                r"if\s*\(\s*tableName\s*=\s*PhConvertUtf8ToUtf16\([^)]*\)\s*\)\s*\{"
                r"[^{}]*PhSetWindowText\(\s*hwndDlg\s*,\s*PhaFormatString\(\s*"
                r"PvpLoadUiString\(\s*IDS_PV_CLR_TABLE_TITLE_FORMAT\s*\)\s*,\s*"
                r"tableName->Buffer\s*\)->Buffer\s*\)\s*;"
                r"[^{}]*PhDereferenceObject\(\s*tableName\s*\)\s*;",
                re.S,
            ),
        )
        self.assertRegex(
            tab,
            re.compile(
                r"case\s+WM_INITDIALOG\s*:\s*\{.*?PhSetWindowText\(\s*hwndDlg\s*,\s*"
                r"PhaFormatString\(\s*PvpLoadUiString\(\s*IDS_PV_PROPERTIES_TITLE_FORMAT\s*\)\s*,\s*"
                r"PhGetString\(\s*PvFileName\s*\)\s*\)->Buffer\s*\)\s*;",
                re.S,
            ),
        )
        self.assertRegex(
            certificates,
            re.compile(
                r"if\s*\(\s*certificateDirectoryLength\s*\)\s*\{\s*"
                r"PhSetWindowText\(\s*Context->LabelHandle\s*,\s*PhaFormatString\(\s*"
                r"PvpLoadUiString\(\s*IDS_PV_CERTIFICATE_SIZE_FORMAT\s*\)\s*,\s*"
                r"PhaFormatSize\(\s*certificateDirectoryLength\s*,\s*ULONG_MAX\s*\)->Buffer\s*,\s*"
                r"PhaFormatSize\(\s*Context->TotalSize\s*,\s*ULONG_MAX\s*\)->Buffer\s*"
                r"\)->Buffer\s*\)\s*;",
                re.S,
            ),
        )

    def test_copy_menus_preserve_owned_text_until_delete_callback(self):
        source = masked_source("misc.c")
        cases = (
            (
                "PvInsertCopyListViewEMenuItem",
                "escapedText->Buffer",
                "copyMenuItem",
                "INT_MAX",
                "PhpCopyListViewEMenuItemDeleteFunction",
                "context->MenuItemText",
            ),
            (
                "PhInsertCopyCellEMenuItem",
                "escapedText->Buffer",
                "copyCellItem",
                "ID_COPY_CELL",
                "PhpCopyCellEMenuItemDeleteFunction",
                "context->MenuItemText",
            ),
        )

        for function_name, argument, item, item_id, delete_function, owner in cases:
            with self.subTest(function=function_name):
                body = function_body(source, function_name)
                self.assertRegex(
                    body,
                    r"menuItemText\s*=\s*PhFormatString\(\s*"
                    r"PvpLoadUiString\(\s*IDS_PV_MENU_COPY_COLUMN_FORMAT\s*\)\s*,\s*"
                    + re.escape(argument)
                    + r"\s*\)\s*;",
                )
                self.assertRegex(
                    body,
                    re.compile(
                        r"PhDereferenceObject\(\s*escapedText\s*\)\s*;.*?"
                        + re.escape(item)
                        + r"\s*=\s*PhCreateEMenuItem\(\s*0\s*,\s*"
                        + re.escape(item_id)
                        + r"\s*,\s*menuItemText->Buffer\s*,\s*NULL\s*,\s*context\s*\)\s*;.*?"
                        + re.escape(item)
                        + r"->DeleteFunction\s*=\s*"
                        + re.escape(delete_function)
                        + r"\s*;.*?"
                        + re.escape(owner)
                        + r"\s*=\s*menuItemText\s*;",
                        re.S,
                    ),
                )
                self.assertNotRegex(
                    body,
                    r"PhDereferenceObject\(\s*menuItemText\s*\)",
                )

                delete_body = function_body(source, delete_function)
                self.assertEqual(
                    len(
                        re.findall(
                            r"PhDereferenceObject\(\s*context->MenuItemText\s*\)\s*;",
                            delete_body,
                        )
                    ),
                    1,
                )
                self.assertEqual(
                    len(re.findall(r"PhFree\(\s*context\s*\)\s*;", delete_body)),
                    1,
                )

    def test_image_size_localizes_only_the_incorrect_overlay_branch(self):
        body = function_body(masked_source("peprp.c"), "PvpSetPeImageSize")

        self.assertEqual(
            len(
                re.findall(
                    r"PhFormatString\(\s*PvpLoadUiString\(\s*"
                    r"IDS_PV_IMAGE_SIZE_OVERLAY_FORMAT\s*\)",
                    body,
                )
            ),
            1,
        )
        self.assertRegex(
            body,
            re.compile(
                r"if\s*\(\s*success\s*\)\s*\{\s*"
                r"string\s*=\s*PhFormatSize\([^;]+;\s*\}\s*else\s*\{.*?"
                r"string\s*=\s*PhFormatString\(\s*PvpLoadUiString\(\s*"
                r"IDS_PV_IMAGE_SIZE_OVERLAY_FORMAT\s*\)\s*,\s*"
                r"PhaFormatSize\(\s*lastRawDataOffset\s*,\s*ULONG_MAX\s*\)->Buffer\s*,\s*"
                r"PhaFormatSize\(\s*PvMappedImage.ViewSize\s*,\s*ULONG_MAX\s*\)->Buffer\s*,\s*"
                r"pointer\s*,\s*PhaFormatSize\(\s*PvMappedImage.ViewSize\s*-\s*"
                r"lastRawDataOffset\s*,\s*ULONG_MAX\s*\)->Buffer",
                re.S,
            ),
        )

    def test_checksum_routes_are_bound_to_their_exact_state_branches(self):
        source = masked_source("peprp.c")
        start = function_body(source, "PvpSetPeImageCheckSum")
        dialog = function_body(source, "PvPeGeneralDlgProc")

        self.assertRegex(
            start,
            r"string\s*=\s*PhFormatString\(\s*PvpLoadUiString\(\s*"
            r"IDS_PV_CHECKSUM_VERIFYING_FORMAT\s*\)\s*,\s*"
            r"PvMappedImage.NtHeaders->OptionalHeader.CheckSum\s*\)\s*;",
        )
        self.assertRegex(
            dialog,
            r"if\s*\(\s*headerCheckSum\s*==\s*0\s*\)\s*\{\s*"
            r"string\s*=\s*PhFormatString\(\s*PvpLoadUiString\(\s*"
            r"IDS_PV_CHECKSUM_MISSING_FORMAT\s*\)\s*,\s*realCheckSum\s*\)\s*;",
        )
        self.assertRegex(
            dialog,
            r"else\s+if\s*\(\s*headerCheckSum\s*==\s*realCheckSum\s*\)\s*\{\s*"
            r"string\s*=\s*PhFormatString\(\s*L\"0x%I32x\"\s*,\s*"
            r"headerCheckSum\s*\)\s*;",
        )
        self.assertRegex(
            dialog,
            r"else\s*\{\s*string\s*=\s*PhFormatString\(\s*"
            r"PvpLoadUiString\(\s*IDS_PV_CHECKSUM_MISMATCH_FORMAT\s*\)\s*,\s*"
            r"headerCheckSum\s*,\s*realCheckSum\s*\)\s*;",
        )

    def test_verify_routes_keep_all_four_outcomes_distinct(self):
        body = function_body(masked_source("peprp.c"), "PvPeGeneralDlgProc")

        self.assertRegex(
            body,
            r"if\s*\(\s*PvImageSignerName\s*\)\s*\{\s*"
            r"string\s*=\s*PhFormatString\(\s*PvpLoadUiString\(\s*"
            r"IDS_PV_VERIFIED_LINK_FORMAT\s*\)\s*,\s*PvImageSignerName->Buffer\s*\)\s*;",
        )
        self.assertRegex(
            body,
            r"else\s*\{\s*string\s*=\s*PhFormatString\(\s*"
            r"PvpLoadUiString\(\s*IDS_PV_VERIFIED_COMPANY_FORMAT\s*\)\s*,\s*"
            r"PhGetStringOrEmpty\(\s*PvImageVersionInfo.CompanyName\s*\)\s*\)\s*;",
        )
        self.assertRegex(
            body,
            r"else\s+if\s*\(\s*PvImageVerifyResult\s*!=\s*VrUnknown\s*\)\s*\{\s*"
            r"string\s*=\s*PhFormatString\(\s*PvpLoadUiString\(\s*"
            r"IDS_PV_UNVERIFIED_COMPANY_FORMAT\s*\)\s*,\s*"
            r"PhGetStringOrEmpty\(\s*PvImageVersionInfo.CompanyName\s*\)\s*\)\s*;",
        )
        self.assertRegex(
            body,
            r"else\s*\{\s*PhSetDialogItemText\(\s*hwndDlg\s*,\s*IDC_COMPANYNAME\s*,\s*"
            r"PvpGetStringOrNa\(\s*PvImageVersionInfo.CompanyName\s*\)\s*\)\s*;\s*\}",
        )
        self.assertNotIn('PhConcatStrings2(L"(Verified) "', body)
        self.assertNotIn('PhConcatStrings2(L"(UNVERIFIED) "', body)

    def test_ci_and_fresh_audit_keep_only_the_technical_runtime_formats(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("peview.exe=311"), 2)
        self.assertNotIn("peview.exe=287", workflow)

        audit = load_audit_module()
        entries = []
        for pattern in ("*.c", "*.cpp"):
            for path in sorted(PEVIEW_ROOT.rglob(pattern)):
                audit.scan_c_file(str(path), entries)

        window_text = Counter(
            entry["english"]
            for entry in entries
            if entry["category"] == "c_window_text"
            and entry["file"].startswith("tools/peview/")
        )
        runtime_composed = Counter(
            entry["english"]
            for entry in entries
            if entry["category"] == "c_runtime_composed"
            and entry["file"].startswith("tools/peview/")
        )

        self.assertEqual(window_text, Counter())
        self.assertEqual(runtime_composed, RETAINED_RUNTIME_FORMATS)
        self.assertEqual(sum(runtime_composed.values()), 46)


if __name__ == "__main__":
    unittest.main()
