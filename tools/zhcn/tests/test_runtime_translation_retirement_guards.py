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
        self.assertIn(
            "python3 tools/zhcn/check_translation.py --fail-on-untranslated",
            workflow,
        )
        self.assertNotIn("auto_translate.py", workflow)

    def test_upstream_sync_fails_before_committing_untranslated_items(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "sync-upstream.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("coverage-report.md", workflow)
        self.assertNotIn("untranslated_count=", workflow)
        self.assertLess(
            workflow.index("check_translation.py --fail-on-untranslated"),
            workflow.index("Commit and push sync"),
        )

    def test_release_notes_state_the_windows_evidence_boundary(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Windows x64 自动冒烟", workflow)
        self.assertIn("10 个插件模块映射", workflow)
        self.assertIn("视觉布局、多 DPI、x86 与 ARM64 真机运行：本工作流未验证", workflow)
        self.assertNotIn("- 运行时冒烟脚本：通过", workflow)


if __name__ == "__main__":
    unittest.main()
