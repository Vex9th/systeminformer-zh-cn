#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


class RuntimeTranslationRetirementGuardTests(unittest.TestCase):
    def test_unused_runtime_translation_includes_are_removed(self) -> None:
        for relative_path in (
            "SystemInformer/procprp.c",
            "plugins/ExtendedTools/disktab.c",
            "plugins/ExtendedTools/fwtab.c",
        ):
            with self.subTest(relative_path=relative_path):
                source = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertNotIn("#include <phtranslation.h>", source)
                self.assertNotIn("PhTranslateString(", source)

    def test_upstream_sync_cannot_hide_translation_tool_failures(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "sync-upstream.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotRegex(
            workflow,
            r"python3 tools/zhcn/(?:auto_translate|check_translation)\.py[^\n]*\|\|\s*true",
        )
        self.assertIn("python3 tools/zhcn/auto_translate.py", workflow)
        self.assertIn(
            "python3 tools/zhcn/check_translation.py --manifest tools/zhcn/manifest.json "
            "--translation tools/zhcn/zh-CN.json --fail-on-placeholder-error",
            workflow,
        )

    def test_upstream_sync_counts_real_untranslated_items_instead_of_a_heading(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "sync-upstream.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotIn('grep -q "^## 未翻译字符串"', workflow)
        self.assertIn("untranslated_count=", workflow)
        self.assertIn("/^## 未翻译字符串/", workflow)
        self.assertRegex(workflow, r"if \[ \"\$untranslated_count\" -gt 0 \]; then")


if __name__ == "__main__":
    unittest.main()
