#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


class RuntimeTranslationLayerRetiredTests(unittest.TestCase):
    def test_compatibility_export_is_identity_only(self) -> None:
        source = (REPO_ROOT / "phlib" / "phtranslation.c").read_text(encoding="utf-8-sig")
        self.assertNotIn("PhTranslationTableZhCn", source)
        self.assertNotIn("wcscmp", source)
        body = re.search(
            r"PCWSTR\s+PhTranslateString\s*\([^)]*\)\s*\{(?P<body>.*?)\n\}",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(body)
        self.assertEqual("return English;", " ".join(body.group("body").split()))

    def test_generated_dictionary_and_generator_are_removed(self) -> None:
        self.assertFalse((REPO_ROOT / "phlib" / "phtranslation_zhcn.c").exists())
        self.assertFalse((REPO_ROOT / "tools" / "zhcn" / "generate_translation.py").exists())
        self.assertFalse((REPO_ROOT / "tools" / "zhcn" / "auto_translate.py").exists())

        build_files = (
            REPO_ROOT / "phlib" / "phlib.vcxproj",
            REPO_ROOT / "phlib" / "phlib.vcxproj.filters",
            REPO_ROOT / "phlib" / "CMakeLists.txt",
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml",
            REPO_ROOT / ".github" / "workflows" / "sync-upstream.yml",
        )
        for path in build_files:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8-sig")
                self.assertNotIn("phtranslation_zhcn", text)
                self.assertNotIn("generate_translation.py", text)

        sync_workflow = build_files[-1].read_text(encoding="utf-8-sig")
        self.assertNotIn("LLM_API_KEY", sync_workflow)
        self.assertNotIn("auto_translate.py", sync_workflow)
        self.assertNotIn("coverage-report.md", sync_workflow)
        self.assertIn("generate_native_resources.py --check", sync_workflow)
        self.assertIn("python3 -m unittest discover -s tools/zhcn/tests -q", sync_workflow)

    def test_generic_ui_funnels_do_not_rewrite_caller_text(self) -> None:
        for relative in (
            "phlib/emenu.c",
            "phlib/treenew.c",
            "phlib/searchbox.c",
            "phlib/util.c",
        ):
            with self.subTest(relative=relative):
                source = (REPO_ROOT / relative).read_text(encoding="utf-8-sig")
                self.assertNotRegex(source, r"\bPhTranslateString\s*\(")
                self.assertNotIn("#include <phtranslation.h>", source)

    def test_production_code_cannot_call_the_compatibility_export(self) -> None:
        excluded = {
            REPO_ROOT / "phlib" / "phtranslation.c",
            REPO_ROOT / "phlib" / "include" / "phtranslation.h",
        }
        roots = (
            REPO_ROOT / "SystemInformer",
            REPO_ROOT / "phlib",
            REPO_ROOT / "plugins",
            REPO_ROOT / "tools" / "peview",
            REPO_ROOT / "tools" / "CustomSetupTool",
            REPO_ROOT / "tools" / "CustomSignTool",
        )

        for root in roots:
            for path in root.rglob("*"):
                if path.suffix.lower() not in {".c", ".cpp", ".h"} or path in excluded:
                    continue
                with self.subTest(path=path.relative_to(REPO_ROOT)):
                    source = path.read_text(encoding="utf-8-sig", errors="replace")
                    self.assertNotRegex(source, r"\bPhTranslateString\s*\(")

    def test_programs_select_resource_language_without_enabling_dictionary(self) -> None:
        for relative in (
            "SystemInformer/main.c",
            "tools/peview/main.c",
            "tools/CustomSetupTool/main.c",
        ):
            with self.subTest(relative=relative):
                source = (REPO_ROOT / relative).read_text(encoding="utf-8-sig")
                self.assertNotIn("PhTranslationEnabled", source)
                self.assertNotIn("#include <phtranslation.h>", source)

    def test_audit_does_not_treat_compatibility_calls_as_translation(self) -> None:
        source = (REPO_ROOT / "tools" / "zhcn" / "audit.py").read_text(
            encoding="utf-8-sig"
        )
        self.assertNotIn("TRANSLATED_CALL_RE", source)
        self.assertNotIn("scan_translated_calls", source)
        self.assertNotIn('match.group(0) == "PhTranslateString"', source)

    def test_translation_report_is_opt_in(self) -> None:
        source = (REPO_ROOT / "tools" / "zhcn" / "check_translation.py").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn('ap.add_argument("--report")', source)
        self.assertNotIn('default=os.path.join(HERE, "coverage-report.md")', source)


if __name__ == "__main__":
    unittest.main()
