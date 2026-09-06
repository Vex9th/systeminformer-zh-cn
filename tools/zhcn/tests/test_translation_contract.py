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
    def test_contract_lists_every_supported_audit_category(self) -> None:
        contract = load_module("translation_contract")

        self.assertEqual(
            contract.ALL_CATEGORIES,
            {
                "c_balloon",
                "c_combobox",
                "c_confirm",
                "c_emenu",
                "c_listview_col",
                "c_listview_group",
                "c_listview_group_item",
                "c_listview_item",
                "c_listview_item_raw",
                "c_msgbox",
                "c_msgbox_vararg",
                "c_runtime_composed",
                "c_search",
                "c_statusbar",
                "c_tab",
                "c_taskdialog",
                "c_taskdialog_raw",
                "c_toolbar",
                "c_tree_item",
                "c_treenew_col",
                "c_treenew_empty",
                "c_window_text",
                "phlib_internal",
                "rc_dialog",
                "rc_menu",
                "rc_stringtable",
            },
        )

        self.assertIn(
            "c_runtime_composed",
            contract.CALLSITE_MIGRATION_CATEGORIES,
        )
        self.assertIn(
            "c_taskdialog_raw",
            contract.CALLSITE_MIGRATION_CATEGORIES,
        )
        self.assertIn(
            "c_listview_item_raw",
            contract.CALLSITE_MIGRATION_CATEGORIES,
        )

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

    def test_audit_preserves_duplicate_source_occurrences(self) -> None:
        audit = load_module("audit")
        occurrence = {
            "category": "c_emenu",
            "english": "Repeated occurrence",
            "file": "SystemInformer/main.c",
            "line": 1,
        }

        manifest = audit.build_manifest([occurrence, dict(occurrence)])

        self.assertEqual(manifest["total_occurrences"], 2)
        self.assertEqual(
            manifest["unique_strings"][0]["locations"],
            [
                {"file": "SystemInformer/main.c", "line": 1},
                {"file": "SystemInformer/main.c", "line": 1},
            ],
        )

    def test_audit_rejects_unknown_categories(self) -> None:
        audit = load_module("audit")

        with self.assertRaisesRegex(ValueError, "unknown manifest category"):
            audit.build_manifest(
                [
                    {
                        "category": "c_windows_text",
                        "english": "Misspelled category",
                        "file": "SystemInformer/main.c",
                        "line": 1,
                    }
                ]
            )


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

    def test_checker_rejects_unknown_categories(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 1,
            "unique_strings": [
                {
                    "category": "c_windows_text",
                    "english": "Misspelled category",
                    "locations": [
                        {"file": "SystemInformer/main.c", "line": 1}
                    ],
                }
            ],
        }

        result, _ = self.run_checker(
            manifest, {"strings": {}, "native_strings": {}}
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown manifest category", result.stdout)

    def test_checker_rejects_duplicate_canonical_keys(self) -> None:
        translations = {"strings": {}, "native_strings": {}}
        cases = {
            "ordinary": [
                {
                    "category": "c_emenu",
                    "english": "Duplicate",
                    "locations": [{"file": "plugins/A/a.c", "line": 1}],
                },
                {
                    "category": "c_emenu",
                    "english": "Duplicate",
                    "locations": [{"file": "plugins/B/b.c", "line": 2}],
                },
            ],
            "callsite": [
                {
                    "module": "plugins/A",
                    "category": "c_window_text",
                    "english": "Duplicate",
                    "locations": [{"file": "plugins/A/a.c", "line": 1}],
                },
                {
                    "module": "plugins/A",
                    "category": "c_window_text",
                    "english": "Duplicate",
                    "locations": [{"file": "plugins/A/b.c", "line": 2}],
                },
            ],
        }

        for name, entries in cases.items():
            with self.subTest(name=name):
                manifest = {
                    "schema_version": 2,
                    "total_occurrences": 2,
                    "unique_strings": entries,
                }
                result, _ = self.run_checker(manifest, translations)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("duplicate canonical manifest key", result.stdout)

    def test_checker_requires_total_occurrences_to_match_locations(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 2,
            "unique_strings": [
                {
                    "category": "c_emenu",
                    "english": "One occurrence",
                    "locations": [{"file": "SystemInformer/main.c", "line": 1}],
                }
            ],
        }

        result, _ = self.run_checker(
            manifest, {"strings": {}, "native_strings": {}}
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("total_occurrences", result.stdout)

    def test_checker_allows_duplicate_source_locations_when_total_matches(self) -> None:
        manifest = {
            "schema_version": 2,
            "total_occurrences": 2,
            "unique_strings": [
                {
                    "category": "c_emenu",
                    "english": "Repeated occurrence",
                    "locations": [
                        {"file": "SystemInformer/main.c", "line": 1},
                        {"file": "SystemInformer/main.c", "line": 1},
                    ],
                }
            ],
        }

        result, _ = self.run_checker(
            manifest, {"strings": {}, "native_strings": {}}
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_checker_rejects_boolean_occurrence_and_line_values(self) -> None:
        translations = {"strings": {}, "native_strings": {}}
        cases = {
            "boolean total": {
                "schema_version": 2,
                "total_occurrences": True,
                "unique_strings": [
                    {
                        "category": "c_emenu",
                        "english": "Invalid total",
                        "locations": [
                            {"file": "SystemInformer/main.c", "line": 1}
                        ],
                    }
                ],
            },
            "negative total": {
                "schema_version": 2,
                "total_occurrences": -1,
                "unique_strings": [],
            },
            "boolean line": {
                "schema_version": 2,
                "total_occurrences": 1,
                "unique_strings": [
                    {
                        "category": "c_emenu",
                        "english": "Invalid line",
                        "locations": [
                            {"file": "SystemInformer/main.c", "line": True}
                        ],
                    }
                ],
            },
            "zero line": {
                "schema_version": 2,
                "total_occurrences": 1,
                "unique_strings": [
                    {
                        "category": "c_emenu",
                        "english": "Invalid line",
                        "locations": [
                            {"file": "SystemInformer/main.c", "line": 0}
                        ],
                    }
                ],
            },
        }

        for name, manifest in cases.items():
            with self.subTest(name=name):
                result, _ = self.run_checker(manifest, translations)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error: invalid manifest", result.stdout)


if __name__ == "__main__":
    unittest.main()
