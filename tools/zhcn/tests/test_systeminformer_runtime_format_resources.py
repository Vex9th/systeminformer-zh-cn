#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCES = (
    ("IDS_PH_MEMORY_RESULTS_TITLE_FORMAT", 2542, "Results - %s (%lu)", "结果 - %s（%lu）"),
    ("IDS_PH_RESULTS_COUNT_FORMAT", 2543, "%s results.", "%s 个结果。"),
    ("IDS_PH_FIND_RESULTS_TITLE_FORMAT", 2544, "%s (%lu results)", "%s（%lu 个结果）"),
    ("IDS_PH_AFFINITY_THREADS_TITLE_FORMAT", 2545, "%s (%lu threads)", "%s（%lu 个线程）"),
    ("IDS_PH_EDIT_ENVIRONMENT_TITLE_FORMAT", 2546, "Edit %s", "编辑 %s"),
    ("IDS_PH_MESSAGE_FROM_FORMAT", 2547, "Message from %s", "来自 %s 的消息"),
    ("IDS_PH_STACK_THREAD_TITLE_FORMAT", 2548, "Stack - thread %lu", "堆栈 - 线程 %lu"),
    (
        "IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT",
        2549,
        "%lu zombie process(es), %lu terminated process(es).",
        "%lu 个僵尸进程，%lu 个已终止进程。",
    ),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("runtime_format_resource_audit", path)
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


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.S)
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


class SystemInformerRuntimeFormatResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: (APP_ROOT / name).read_text(encoding="utf-8-sig")
            for name in (
                "memrslt.c",
                "findobj.c",
                "affinity.c",
                "envdlg.c",
                "sessmsg.c",
                "thrdstk.c",
                "hidnproc.c",
            )
        }

    def test_resources_ids_text_ownership_and_counts_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        app_header = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(
            encoding="utf-8-sig"
        )
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        self.assertEqual([row[1] for row in RESOURCES], list(range(2542, 2550)))
        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(translations["native_strings"].get(en), zh)
                self.assertNotIn(en, translations["strings"])

        numeric_ids = sorted(
            int(value)
            for value in re.findall(
                r"(?m)^#define\s+IDS_PH_[A-Z0-9_]+\s+(\d+)\s*$",
                header + "\n" + app_header,
            )
        )
        self.assertEqual(numeric_ids, list(range(2000, 2550)))
        self.assertEqual(len(english), 550)
        self.assertEqual(len(chinese), 550)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2550$")

        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("sys_info.exe=550"), 2)
        self.assertNotIn("sys_info.exe=542", workflow)

    def test_each_resource_is_bound_to_the_exact_runtime_arguments(self) -> None:
        masked = {name: self.audit.mask_c_comments(source) for name, source in self.sources.items()}
        expected_calls = {
            "memrslt.c": (
                (
                    "IDS_PH_MEMORY_RESULTS_TITLE_FORMAT",
                    "processItem->ProcessName->Buffer",
                    "HandleToUlong(processItem->ProcessId)",
                ),
                (
                    "IDS_PH_RESULTS_COUNT_FORMAT",
                    "PhaFormatUInt64(context->Results->Count, TRUE)->Buffer",
                ),
            ),
            "findobj.c": ((
                "IDS_PH_FIND_RESULTS_TITLE_FORMAT",
                "PhGetStringOrEmpty(context->WindowText)",
                "context->SearchResultsAddIndex",
            ),),
            "affinity.c": ((
                "IDS_PH_AFFINITY_THREADS_TITLE_FORMAT",
                "windowText->Buffer",
                "context->NumberOfThreads",
            ),),
            "envdlg.c": (("IDS_PH_EDIT_ENVIRONMENT_TITLE_FORMAT", "PhGetString(context->Name)"),),
            "sessmsg.c": (("IDS_PH_MESSAGE_FROM_FORMAT", "currentUserName->Buffer"),),
            "thrdstk.c": ((
                "IDS_PH_STACK_THREAD_TITLE_FORMAT",
                "HandleToUlong(context->ThreadId)",
            ),),
            "hidnproc.c": (
                (
                    "IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT",
                    "NumberOfZombieProcesses",
                    "NumberOfTerminatedProcesses",
                ),
                (
                    "IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT",
                    "NumberOfZombieProcesses",
                    "NumberOfTerminatedProcesses",
                ),
            ),
        }

        actual = Counter()
        for file_name, calls in expected_calls.items():
            for name, arguments, _spans, _start in self.audit.find_calls(
                masked[file_name], {"PhaFormatString", "PhFormatString"}
            ):
                if not arguments:
                    continue
                first = compact(arguments[0])
                match = re.fullmatch(r"PhGetApplicationUiString\((IDS_PH_[A-Z0-9_]+)\)", first)
                if match and match.group(1) in {row[0] for row in RESOURCES}:
                    actual[(file_name, match.group(1), *(compact(arg) for arg in arguments[1:]))] += 1

        expected = Counter(
            (file_name, *(compact(part) for part in call))
            for file_name, calls in expected_calls.items()
            for call in calls
        )
        self.assertEqual(actual, expected)

    def test_hidden_process_non_auto_pool_path_keeps_explicit_release(self) -> None:
        source = self.sources["hidnproc.c"]
        cleanup = function_body(source, "PhZombieProcessesCleanupList", self.audit)
        worker = function_body(source, "PhZombieProcessesThread", self.audit)
        dialog = function_body(source, "PhpZombieProcessesDlgProc", self.audit)

        self.assertRegex(
            cleanup,
            r"(?s)PPH_STRING\s+string\s*=\s*PhFormatString\(\s*"
            r"PhGetApplicationUiString\(IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT\).*?"
            r"PhSetDialogItemText\([^;]+string->Buffer\s*\);.*?"
            r"PhDereferenceObject\(string\s*\);",
        )
        self.assertNotIn("PhaFormatString", cleanup)
        self.assertNotIn("PhInitializeAutoPool", worker)
        self.assertRegex(
            worker,
            r"else\s+PhZombieProcessesCleanupList\(processList\s*\)\s*;",
        )
        self.assertEqual(
            len(re.findall(
                r"PhaFormatString\(\s*"
                r"PhGetApplicationUiString\(IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT\)",
                dialog,
            )),
            1,
        )
        self.assertNotRegex(
            dialog,
            r"(?<!Pha)PhFormatString\(\s*"
            r"PhGetApplicationUiString\(IDS_PH_HIDDEN_PROCESS_SUMMARY_FORMAT\)",
        )

    def test_old_complete_runtime_formats_are_absent_from_code(self) -> None:
        all_source = "\n".join(self.audit.mask_c_comments(source) for source in self.sources.values())
        for _symbol, _resource_id, english, _chinese in RESOURCES:
            with self.subTest(english=english):
                self.assertNotIn(f'L"{english}"', all_source)

    def test_fresh_scan_no_longer_reports_migrated_formats(self) -> None:
        entries = []
        for file_name in self.sources:
            self.audit.scan_c_file(str(APP_ROOT / file_name), entries)

        migrated = {row[2] for row in RESOURCES}
        remaining = [
            (entry["category"], entry["english"], entry["file"], entry["line"])
            for entry in entries
            if entry["english"] in migrated
        ]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
