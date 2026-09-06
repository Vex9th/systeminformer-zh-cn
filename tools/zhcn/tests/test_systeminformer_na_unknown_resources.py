#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCES = (
    ("IDS_PH_NOT_AVAILABLE", 2560, "N/A", "不适用"),
    ("IDS_PH_UNKNOWN", 2561, "Unknown", "未知"),
)

SOURCE_FILES = (
    "hndlprp.c",
    "memlists.c",
    "procrec.c",
    "prpggen.c",
    "srvprp.c",
    "syssccpu.c",
    "sysscmem.c",
    "tokprp.c",
    "jobprp.c",
    "ntobjprp.c",
)

RESOURCE_SOURCE_COUNTS = {
    "IDS_PH_NOT_AVAILABLE": {
        "hndlprp.c": 15,
        "memlists.c": 1,
        "procrec.c": 7,
        "prpggen.c": 8,
        "srvprp.c": 1,
        "syssccpu.c": 3,
        "sysscmem.c": 23,
        "tokprp.c": 9,
    },
    "IDS_PH_UNKNOWN": {
        "memlists.c": 24,
        "syssccpu.c": 1,
        "tokprp.c": 24,
        "jobprp.c": 17,
        "ntobjprp.c": 5,
    },
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("na_unknown_resource_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


def braced_block(source: str, opening: int) -> tuple[str, int]:
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index], index
    raise AssertionError("unterminated block")


def block_after(source: str, marker: str, start: int = 0) -> tuple[str, int]:
    marker_index = source.index(marker, start)
    opening = source.index("{", marker_index + len(marker))
    return braced_block(source, opening)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"function not found: {name}")
    opening = source.find("{", match.start())
    body, _closing = braced_block(source, opening)
    return body


class SystemInformerNaUnknownResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: cls.audit.mask_c_comments(
                (APP_ROOT / name).read_text(encoding="utf-8-sig")
            )
            for name in SOURCE_FILES
        }

    def test_resource_ids_text_ownership_counts_and_boundaries_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        app_header = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(
            encoding="utf-8-sig"
        )
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for symbol, numeric_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{numeric_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(translations["strings"].get(en), zh)
                self.assertNotIn(en, translations["native_strings"])

        numeric_ids = sorted(
            int(value)
            for value in re.findall(
                r"(?m)^#define\s+IDS_PH_[A-Z0-9_]+\s+(\d+)\s*$",
                header + "\n" + app_header,
            )
        )
        self.assertEqual(numeric_ids, list(range(2000, 2663)))
        self.assertEqual(len(english), 663)
        self.assertEqual(len(chinese), 663)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_HANDLE_SECTION_RESERVE$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2663$")

        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("sys_info.exe=663"), 2)
        self.assertNotIn("sys_info.exe=560", workflow)

    def test_every_resource_source_expression_is_accounted_for_by_file(self) -> None:
        for symbol, file_counts in RESOURCE_SOURCE_COUNTS.items():
            for filename in SOURCE_FILES:
                expected_count = file_counts.get(filename, 0)
                with self.subTest(symbol=symbol, filename=filename):
                    self.assertEqual(
                        self.sources[filename].count(
                            f"PhGetApplicationUiString({symbol})"
                        ),
                        expected_count,
                    )

    def test_helper_and_merged_branches_preserve_the_real_sink_routes(self) -> None:
        prpggen = self.sources["prpggen.c"]
        sysscmem = self.sources["sysscmem.c"]

        self.assertRegex(
            prpggen,
            re.compile(
                r"FORCEINLINE\s+PCWSTR\s+PhpGetStringOrNa\s*\(.*?"
                r"return\s+PhGetApplicationUiString\(IDS_PH_NOT_AVAILABLE\)",
                re.DOTALL,
            ),
        )
        self.assertEqual(prpggen.count("PhpGetStringOrNa("), 10)
        self.assertEqual(
            sysscmem.count("nonPagedLimit = PhGetApplicationUiString(IDS_PH_NOT_AVAILABLE)"),
            3,
        )
        self.assertEqual(
            sysscmem.count(
                "PhSetDialogItemText(MemoryPanel, IDC_ZNONPAGEDLIMIT_V, nonPagedLimit)"
            ),
            1,
        )

    def test_memory_list_query_branches_keep_distinct_fallback_meanings(self) -> None:
        body = function_body(self.sources["memlists.c"], "PhpUpdateMemoryListInfo")
        success, success_end = block_after(
            body,
            "if (NT_SUCCESS(NtQuerySystemInformation(",
        )
        failure, _failure_end = block_after(body, "else", success_end)

        self.assertRegex(
            success,
            re.compile(
                r"if\s*\(WindowsVersion\s*>=\s*WINDOWS_8\).*?"
                r"IDC_ZLISTMODIFIEDPAGEFILE_V.*?PhaFormatSize\(.*?"
                r"else\s*PhSetDialogItemText\(hwndDlg\s*,\s*"
                r"IDC_ZLISTMODIFIEDPAGEFILE_V\s*,\s*"
                r"PhGetApplicationUiString\(IDS_PH_NOT_AVAILABLE\)\)",
                re.DOTALL,
            ),
        )
        self.assertNotIn("IDS_PH_UNKNOWN", success)
        self.assertEqual(failure.count("PhGetApplicationUiString(IDS_PH_UNKNOWN)"), 24)
        self.assertNotIn("IDS_PH_NOT_AVAILABLE", failure)

    def test_fixed_fallbacks_do_not_reuse_stack_buffers_until_formatting_succeeds(self) -> None:
        syssccpu = self.sources["syssccpu.c"]
        tokprp = self.sources["tokprp.c"]

        self.assertRegex(
            syssccpu,
            re.compile(
                r"WCHAR\s+uptimeString\[PH_TIMESPAN_STR_LEN_1\]\s*;\s*"
                r"PCWSTR\s+uptimeText\s*=\s*"
                r"PhGetApplicationUiString\(IDS_PH_UNKNOWN\).*?"
                r"if\s*\(NT_SUCCESS\(PhGetSystemUptime\(&systemUptime\)\)\)\s*\{.*?"
                r"PhPrintTimeSpan\(uptimeString,.*?\);\s*"
                r"uptimeText\s*=\s*uptimeString;\s*\}.*?"
                r"PhSetWindowText\(CpuPanelUptimeLabel,\s*uptimeText\)",
                re.DOTALL,
            ),
        )

        for name in (
            "tokenSourceNameText",
            "tokenSourceLuidText",
            "tokenLuidText",
            "authenticationLuidText",
            "tokenModifiedLuidText",
            "tokenOriginLogonSessionText",
        ):
            with self.subTest(name=name):
                self.assertRegex(
                    tokprp,
                    rf"PCWSTR\s+{name}\s*=\s*PhGetApplicationUiString\(IDS_PH_UNKNOWN\)",
                )
                self.assertRegex(tokprp, rf"{name}\s*=\s*{name[:-4]};")

        self.assertNotRegex(tokprp, r"WCHAR\s+\w+\[[^\]]+\]\s*=\s*\{\s*L\"Unknown\"")
        self.assertRegex(tokprp, r"PCWSTR\s+tokenVirtualization\s*=.*IDS_PH_NOT_AVAILABLE")
        self.assertRegex(tokprp, r"PCWSTR\s+tokenUIAccess\s*=.*IDS_PH_UNKNOWN")
        self.assertRegex(tokprp, r"PCWSTR\s+tokenType\s*=.*IDS_PH_UNKNOWN")
        self.assertRegex(tokprp, r"PCWSTR\s+tokenImpersonationLevel\s*=.*IDS_PH_UNKNOWN")

    def test_token_stack_buffers_become_visible_only_inside_success_branches(self) -> None:
        general = function_body(self.sources["tokprp.c"], "PhpTokenGeneralPageProc")
        source_success, source_success_end = block_after(
            general,
            "if (NT_SUCCESS(PhGetTokenSource(tokenHandle, &tokenSource)))",
        )
        for assignment in (
            "tokenSourceNameText = tokenSourceName;",
            "tokenSourceLuidText = tokenSourceLuid;",
        ):
            with self.subTest(assignment=assignment):
                self.assertEqual(general.count(assignment), 1)
                self.assertIn(assignment, source_success)
        self.assertLess(
            source_success.index("PhCopyStringZFromBytes("),
            source_success.index("tokenSourceNameText = tokenSourceName;"),
        )
        self.assertLess(
            source_success.index("PhPrintPointer(tokenSourceLuid,"),
            source_success.index("tokenSourceLuidText = tokenSourceLuid;"),
        )
        general_sinks = general[source_success_end:]
        self.assertIn("PhSetDialogItemText(hwndDlg, IDC_SOURCENAME, tokenSourceNameText)", general_sinks)
        self.assertIn("PhSetDialogItemText(hwndDlg, IDC_SOURCELUID, tokenSourceLuidText)", general_sinks)

        advanced = function_body(self.sources["tokprp.c"], "PhpTokenAdvancedPageProc")
        statistics_success, statistics_end = block_after(
            advanced,
            "if (NT_SUCCESS(PhGetTokenStatistics(tokenHandle, &statistics)))",
        )
        for buffer_name in ("tokenLuid", "authenticationLuid", "tokenModifiedLuid"):
            assignment = f"{buffer_name}Text = {buffer_name};"
            with self.subTest(assignment=assignment):
                self.assertEqual(advanced.count(assignment), 1)
                self.assertIn(assignment, statistics_success)
                self.assertLess(
                    statistics_success.index(f"PhPrintPointer({buffer_name},"),
                    statistics_success.index(assignment),
                )

        origin_success, origin_end = block_after(
            advanced,
            "if (NT_SUCCESS(PhGetTokenOrigin(tokenHandle, &origin)))",
            statistics_end,
        )
        origin_assignment = "tokenOriginLogonSessionText = tokenOriginLogonSession;"
        self.assertEqual(advanced.count(origin_assignment), 1)
        self.assertIn(origin_assignment, origin_success)
        self.assertLess(
            origin_success.index("PhPrintPointer(tokenOriginLogonSession,"),
            origin_success.index(origin_assignment),
        )

        advanced_sinks = advanced[origin_end:]
        for index, text_name in enumerate(
            (
                "tokenLuidText",
                "authenticationLuidText",
                "tokenModifiedLuidText",
                "tokenOriginLogonSessionText",
            ),
            start=2,
        ):
            with self.subTest(index=index, text_name=text_name):
                self.assertIn(
                    f"PhSetListViewSubItem(context->ListViewHandle, {index}, 1, {text_name})",
                    advanced_sinks,
                )

    def test_fresh_window_text_scan_has_no_na_or_unknown_units(self) -> None:
        entries = []

        for filename in SOURCE_FILES:
            self.audit.scan_c_file(str(APP_ROOT / filename), entries)

        remaining = {
            (entry["category"], entry["english"])
            for entry in entries
            if entry["category"] == "c_window_text"
            and entry["english"] in {"N/A", "Unknown"}
        }
        self.assertEqual(remaining, set())

    def test_other_categories_and_owned_strings_remain_outside_this_batch(self) -> None:
        hndlprp = self.sources["hndlprp.c"]
        prpggen = self.sources["prpggen.c"]
        tokprp = self.sources["tokprp.c"]

        self.assertIn('PhAddListViewItem(\n            ListViewHandle,\n            MAXINT,\n            PhGetStringOrDefault(string, L"N/A")', hndlprp)
        self.assertIn('PhFormatString(L"0x%x: %s",', hndlprp)
        self.assertIn('return PhCreateString(L"N/A");', prpggen)
        self.assertIn('SIP(SREF(L"Unknown"), 0)', tokprp)
        self.assertIn('PhCreateString(L"Unknown")', tokprp)


if __name__ == "__main__":
    unittest.main()
