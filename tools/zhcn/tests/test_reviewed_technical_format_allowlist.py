#!/usr/bin/env python3

import importlib.util
import pathlib
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CHECKER_PATH = REPO_ROOT / "tools" / "zhcn" / "check_translation.py"


def load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "zhcn_check_translation_technical_formats",
        CHECKER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReviewedTechnicalFormatAllowlistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = load_checker_module()

    @staticmethod
    def manifest_entry(category: str, module: str, text: str, count: int):
        entry = {
            "category": category,
            "english": text,
            "locations": [
                {"file": f"{module}/reviewed-{index}.c", "line": index + 1}
                for index in range(count)
            ],
        }
        if category == "c_runtime_composed":
            entry["module"] = module
        return entry

    def test_reviewed_table_locks_entries_modules_and_location_counts(self) -> None:
        reviewed = self.checker.REVIEWED_TECHNICAL_ENTRIES
        self.assertEqual({"c_runtime_composed", "rc_stringtable"}, {key[0] for key in reviewed})
        self.assertEqual(31, len(reviewed))
        self.assertEqual(
            Counter(
                {
                    "SystemInformer": 6,
                    "plugins/ExtendedTools": 9,
                    "plugins/WindowExplorer": 6,
                    "tools/peview": 9,
                }
            ),
            Counter(module for (category, module, _text) in reviewed if category == "c_runtime_composed"),
        )
        self.assertEqual(
            98,
            sum(count for (category, _module, _text), count in reviewed.items() if category == "c_runtime_composed"),
        )
        self.assertEqual(1, reviewed[("rc_stringtable", "plugins/HardwareDevices", "%lu°C")])

        for (category, module, text), count in reviewed.items():
            with self.subTest(category=category, module=module, text=text):
                self.assertTrue(
                    self.checker.is_reviewed_technical_entry(
                        self.manifest_entry(category, module, text, count)
                    )
                )

    def test_module_category_and_location_mutations_fail_closed(self) -> None:
        entry = self.manifest_entry(
            "c_runtime_composed",
            "tools/peview",
            "%s (%s)",
            23,
        )
        self.assertTrue(self.checker.is_reviewed_technical_entry(entry))

        wrong_module = dict(entry, module="SystemInformer")
        wrong_category = dict(entry, category="c_taskdialog")
        extra_location = dict(entry, locations=entry["locations"] + [{"file": "tools/peview/new.c", "line": 1}])
        changed_text = dict(entry, english="User %s (%s)")
        for mutated in (wrong_module, wrong_category, extra_location, changed_text):
            with self.subTest(mutated=mutated):
                self.assertFalse(self.checker.is_reviewed_technical_entry(mutated))

    def test_report_keys_preserve_module_scoped_canonical_entries(self) -> None:
        window_explorer = self.manifest_entry(
            "c_runtime_composed",
            "plugins/WindowExplorer",
            "%s (%s)",
            1,
        )
        peview = self.manifest_entry(
            "c_runtime_composed",
            "tools/peview",
            "%s (%s)",
            23,
        )
        keys = {
            self.checker.kept_english_manifest_key(window_explorer),
            self.checker.kept_english_manifest_key(peview),
        }
        self.assertEqual(2, len(keys))
        self.assertIn(
            ("plugins/WindowExplorer", "c_runtime_composed", "%s (%s)"),
            keys,
        )
        self.assertIn(
            ("tools/peview", "c_runtime_composed", "%s (%s)"),
            keys,
        )

    def test_nearby_user_visible_prose_remains_untranslated(self) -> None:
        for value in (
            "Downloading update %s...",
            "%s was last analyzed %s",
            "[%lu] Access denied (invalid license key)",
            "Upload size:",
        ):
            with self.subTest(value=value):
                self.assertFalse(
                    self.checker.is_reviewed_technical_entry(
                        self.manifest_entry(
                            "c_runtime_composed",
                            "SystemInformer",
                            value,
                            1,
                        )
                    )
                )


if __name__ == "__main__":
    unittest.main()
