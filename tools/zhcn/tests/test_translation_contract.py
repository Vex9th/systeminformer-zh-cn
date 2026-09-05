#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
ZH_CN_TOOLS = REPO_ROOT / "tools" / "zhcn"


def load_module(name: str):
    path = ZH_CN_TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TranslationManifestContractTests(unittest.TestCase):
    def test_module_for_path_preserves_independently_built_modules(self) -> None:
        contract = load_module("translation_contract")

        cases = {
            "SystemInformer/mainwnd.c": "SystemInformer",
            "phlib/guisup.c": "phlib",
            "plugins/ExtendedTools/main.c": "plugins/ExtendedTools",
            "tools/peview/prpsh.c": "tools/peview",
            "tools/CustomSetupTool/main.c": "tools/CustomSetupTool",
            "tools\\CustomSignTool\\main.c": "tools/CustomSignTool",
        }

        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(contract.module_for_path(path), expected)

    def test_audit_splits_callsite_entries_by_module_only(self) -> None:
        audit = load_module("audit")
        entries = [
            {
                "category": "c_window_text",
                "english": "Shared title",
                "file": "plugins/A/a.c",
                "line": 10,
            },
            {
                "category": "c_window_text",
                "english": "Shared title",
                "file": "plugins/A/other.c",
                "line": 11,
            },
            {
                "category": "c_window_text",
                "english": "Shared title",
                "file": "plugins/B/b.c",
                "line": 20,
            },
            {
                "category": "c_emenu",
                "english": "Shared command",
                "file": "plugins/A/a.c",
                "line": 30,
            },
            {
                "category": "c_emenu",
                "english": "Shared command",
                "file": "plugins/B/b.c",
                "line": 40,
            },
        ]

        manifest = audit.build_manifest(entries)

        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["total_occurrences"], 5)
        self.assertEqual(len(manifest["unique_strings"]), 3)

        callsites = [
            entry
            for entry in manifest["unique_strings"]
            if entry["category"] == "c_window_text"
        ]
        self.assertEqual(
            [entry["module"] for entry in callsites],
            ["plugins/A", "plugins/B"],
        )
        for entry in callsites:
            self.assertTrue(
                all(
                    location["file"].startswith(entry["module"] + "/")
                    for location in entry["locations"]
                )
            )

        ordinary = next(
            entry
            for entry in manifest["unique_strings"]
            if entry["category"] == "c_emenu"
        )
        self.assertNotIn("module", ordinary)
        self.assertEqual(
            {location["file"] for location in ordinary["locations"]},
            {"plugins/A/a.c", "plugins/B/b.c"},
        )

    def test_removing_one_callsite_module_keeps_the_other_module_stable(self) -> None:
        audit = load_module("audit")
        entries = [
            {
                "category": "c_listview_group_item",
                "english": "State",
                "file": "plugins/A/a.c",
                "line": 1,
            },
            {
                "category": "c_listview_group_item",
                "english": "State",
                "file": "plugins/B/b.c",
                "line": 2,
            },
        ]

        before = audit.build_manifest(entries)["unique_strings"]
        after = audit.build_manifest(entries[1:])["unique_strings"]

        self.assertEqual(
            [entry["module"] for entry in before], ["plugins/A", "plugins/B"]
        )
        self.assertEqual([entry["module"] for entry in after], ["plugins/B"])
        self.assertEqual(after[0]["locations"], [{"file": "plugins/B/b.c", "line": 2}])


class TranslationCheckerContractTests(unittest.TestCase):
    def run_checker(self, manifest: dict, translations: dict):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            manifest_path = temp_path / "manifest.json"
            translation_path = temp_path / "zh-CN.json"
            report_path = temp_path / "coverage-report.md"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            translation_path.write_text(
                json.dumps(translations, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ZH_CN_TOOLS / "check_translation.py"),
                    "--manifest",
                    str(manifest_path),
                    "--translation",
                    str(translation_path),
                    "--report",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            report = (
                report_path.read_text(encoding="utf-8")
                if report_path.exists()
                else ""
            )
            return result, report

    def test_checker_counts_callsite_units_and_ordinary_module_occurrences(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 6,
            "unique_strings": [
                {
                    "module": "plugins/A",
                    "category": "c_window_text",
                    "english": "Shared title",
                    "locations": [{"file": "plugins/A/a.c", "line": 1}],
                },
                {
                    "module": "plugins/B",
                    "category": "c_window_text",
                    "english": "Shared title",
                    "locations": [{"file": "plugins/B/b.c", "line": 2}],
                },
                {
                    "category": "c_emenu",
                    "english": "Shared command",
                    "locations": [
                        {"file": "plugins/A/a.c", "line": 3},
                        {"file": "plugins/B/b.c", "line": 4},
                    ],
                },
                {
                    "category": "rc_stringtable",
                    "english": "Shared resource",
                    "locations": [
                        {"file": "tools/peview/peview.rc", "line": 5},
                        {"file": "tools/CustomSetupTool/resource.rc", "line": 6},
                    ],
                },
            ],
        }
        translations = {
            "strings": {
                "Shared title": "共享标题",
                "Shared command": "共享命令",
            },
            "native_strings": {"Shared resource": "共享资源"},
        }

        result, report = self.run_checker(manifest, translations)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "translation audit: translated 2/4, untranslated 2", result.stdout
        )
        self.assertIn("| plugins/A | 1 | 2 | 1 |", report)
        self.assertIn("| plugins/B | 1 | 2 | 1 |", report)
        self.assertIn("| tools/peview | 1 | 1 | 0 |", report)
        self.assertIn("| tools/CustomSetupTool | 1 | 1 | 0 |", report)
        self.assertIn("模块表统计各模块中的有效出现量", report)

    def test_checker_validates_cross_module_placeholder_once(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 2,
            "unique_strings": [
                {
                    "category": "c_emenu",
                    "english": "Open %s",
                    "locations": [
                        {"file": "plugins/A/a.c", "line": 1},
                        {"file": "plugins/B/b.c", "line": 2},
                    ],
                }
            ],
        }
        translations = {"strings": {"Open %s": "打开 %lu"}, "native_strings": {}}

        result, _ = self.run_checker(manifest, translations)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("format specifiers differ"), 1)

    def test_checker_deduplicates_kept_english_across_callsite_modules(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 2,
            "unique_strings": [
                {
                    "module": "plugins/A",
                    "category": "c_window_text",
                    "english": "CPU",
                    "locations": [{"file": "plugins/A/a.c", "line": 1}],
                },
                {
                    "module": "plugins/B",
                    "category": "c_window_text",
                    "english": "CPU",
                    "locations": [{"file": "plugins/B/b.c", "line": 2}],
                },
            ],
        }

        result, report = self.run_checker(
            manifest, {"strings": {}, "native_strings": {}}
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "translation audit: translated 0/0, untranslated 0", result.stdout
        )
        self.assertIn("约定保留英文（技术缩写/键名/占位符等）：1 项", report)
        self.assertEqual(report.count("- `CPU` (c_window_text)"), 1)

    def test_checker_rejects_legacy_or_invalid_callsite_manifests(self) -> None:
        translations = {"strings": {}, "native_strings": {}}
        cases = {
            "legacy schema": {
                "unique_strings": [],
                "total_occurrences": 0,
            },
            "missing module": {
                "schema_version": 2,
                "unique_strings": [
                    {
                        "category": "c_window_text",
                        "english": "Title",
                        "locations": [{"file": "plugins/A/a.c", "line": 1}],
                    }
                ],
                "total_occurrences": 1,
            },
            "cross-module locations": {
                "schema_version": 2,
                "unique_strings": [
                    {
                        "module": "plugins/A",
                        "category": "c_window_text",
                        "english": "Title",
                        "locations": [
                            {"file": "plugins/A/a.c", "line": 1},
                            {"file": "plugins/B/b.c", "line": 2},
                        ],
                    }
                ],
                "total_occurrences": 2,
            },
        }

        for name, manifest in cases.items():
            with self.subTest(name=name):
                result, _ = self.run_checker(manifest, translations)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error: invalid manifest", result.stdout)


if __name__ == "__main__":
    unittest.main()
