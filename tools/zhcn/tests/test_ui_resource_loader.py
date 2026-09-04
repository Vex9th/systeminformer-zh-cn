#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def read_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")


class UiResourceLoaderContractTests(unittest.TestCase):
    def test_public_api_exposes_explicit_ui_language_loading(self) -> None:
        header = read_source("phlib/include/mapldr.h")

        for symbol in (
            "PhLoadResourceForLanguage",
            "PhLoadResourceCopyForLanguage",
            "PhSetApplicationUiLanguage",
            "PhGetApplicationUiLanguage",
            "PhLoadUiResource",
            "PhLoadUiResourceCopy",
            "PhLoadUiString",
        ):
            self.assertIn(symbol, header)

    def test_ui_resource_api_is_exported_for_plugins(self) -> None:
        exports = read_source("SystemInformer/SystemInformer.def")

        for symbol in (
            "PhLoadResourceForLanguage",
            "PhLoadResourceCopyForLanguage",
            "PhSetApplicationUiLanguage",
            "PhGetApplicationUiLanguage",
            "PhLoadUiResource",
            "PhLoadUiResourceCopy",
            "PhLoadUiString",
        ):
            self.assertRegex(exports, rf"(?m)^\s+{symbol}$")

    def test_ui_resource_loader_falls_back_to_english(self) -> None:
        source = read_source("phlib/mapldr.c")
        function = re.search(
            r"NTSTATUS PhLoadUiResource\s*\(.*?^}\n",
            source,
            re.MULTILINE | re.DOTALL,
        )

        self.assertIsNotNone(function)
        body = function.group(0)
        self.assertIn("PhGetApplicationUiLanguage()", body)
        self.assertIn("LANG_ENGLISH", body)
        self.assertIn("SUBLANG_ENGLISH_US", body)
        self.assertIn("FallbackToEnglish", body)

    def test_explicit_language_lookup_skips_system_mui_fallback(self) -> None:
        source = read_source("phlib/mapldr.c")
        function = re.search(
            r"static NTSTATUS PhpLoadResource\s*\(.*?^}\n",
            source,
            re.MULTILINE | re.DOTALL,
        )

        self.assertIsNotNone(function)
        body = function.group(0)
        self.assertIn("LdrFindResourceEx_U", body)
        self.assertIn("LDR_RES_SEARCH_SKIP_MUI", body)
        self.assertIn("LdrFindResource_U", body)
        self.assertIn("ExactLanguage", body)

        legacy = re.search(
            r"NTSTATUS PhLoadResource\s*\(.*?^}\n",
            source,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(legacy)
        self.assertIn("FALSE", legacy.group(0))

    def test_string_resource_length_does_not_drop_last_character(self) -> None:
        source = read_source("phlib/mapldr.c")
        function = re.search(
            r"static PPH_STRING PhpCreateStringFromResource\s*\(.*?^}\n",
            source,
            re.MULTILINE | re.DOTALL,
        )

        self.assertIsNotNone(function)
        body = function.group(0)
        self.assertIn("stringBuffer->Length * sizeof(WCHAR)", body)
        self.assertNotIn("- sizeof(UNICODE_NULL)", body)

    def test_translated_font_writes_one_terminator(self) -> None:
        source = read_source("phlib/phtranslation.c")
        start = source.index("static const WCHAR zhCnFont[]")
        end = source.index("changed = TRUE", start)
        font_write = source[start:end]

        self.assertIn("(wcslen(zhCnFont) + 1) * sizeof(WCHAR)", font_write)
        self.assertNotIn("PhTlpWriteWord(&writer, 0)", font_write)

    def test_legacy_template_font_check_uses_setfont_bit(self) -> None:
        source = read_source("phlib/phtranslation.c")

        self.assertIn("& DS_SETFONT)", source)
        self.assertNotIn("& (DS_SETFONT | DS_SHELLFONT)", source)

    def test_missing_string_slot_falls_back_to_english(self) -> None:
        source = read_source("phlib/mapldr.c")
        probe = read_source("tools/tests/phlib-test/t_resource.c")
        resources = read_source("tools/tests/phlib-test/phlib-test.rc")

        self.assertIn("PhLoadResourceForLanguage", source)
        self.assertIn("IDS_UI_RESOURCE_ENGLISH_ONLY", probe)
        self.assertEqual(resources.count("IDS_UI_RESOURCE_ENGLISH_ONLY"), 1)
        self.assertIn("fallbackToEnglish", probe)

    def test_main_maps_only_supported_language_names(self) -> None:
        source = read_source("SystemInformer/main.c")

        self.assertRegex(
            source,
            r"PhEqualStringZ\([^;]+L\"zh-CN\"[^;]+PhSetApplicationUiLanguage\(\s*MAKELANGID\(LANG_CHINESE",
        )
        self.assertRegex(
            source,
            r"PhEqualStringZ\([^;]+L\"en\"[^;]+PhSetApplicationUiLanguage\(\s*MAKELANGID\(LANG_ENGLISH",
        )
        self.assertIn("PhTranslationEnabled = FALSE", source)

    def test_dialog_and_menu_helpers_use_ui_resource_loader(self) -> None:
        source = read_source("phlib/guisup.c")

        self.assertRegex(
            source,
            r"PhLoadUiResourceCopy\(\s*Instance,\s*Template,\s*RT_DIALOG",
        )
        self.assertRegex(
            source,
            r"PhLoadUiResource\(\s*DllBase,\s*MenuName,\s*RT_MENU",
        )
        self.assertIn("nativeLocalized", source)

    def test_windows_loader_probe_is_built_and_run_by_ci(self) -> None:
        project = read_source("tools/tests/phlib-test/phlib-test.vcxproj")
        main = read_source("tools/tests/phlib-test/main.c")
        probe = read_source("tools/tests/phlib-test/t_resource.c")
        workflow = read_source(".github/workflows/zh-cn-build.yml")

        self.assertIn('<ClCompile Include="t_resource.c" />', project)
        self.assertIn('<ResourceCompile Include="phlib-test.rc" />', project)
        self.assertNotIn("<PlatformToolset>v143</PlatformToolset>", project)
        self.assertEqual(project.count("$(DefaultPlatformToolset)"), 6)
        self.assertIn("Test_resource();", main)
        self.assertIn("if (!NT_SUCCESS(status))", main)
        self.assertNotIn("assert(", probe)
        self.assertIn("abort();", probe)
        self.assertIn("phlib-test.sln", workflow)
        self.assertIn("phlib-test.exe", workflow)
        self.assertIn("IDD_UI_RESOURCE_TEST", probe)
        self.assertIn("IDM_UI_RESOURCE_TEST", probe)
        self.assertIn("PhCreateDialog(", probe)
        self.assertIn("PhDialogBox(", probe)
        self.assertIn("PhCreatePropertySheetPage(", probe)
        self.assertIn("PhLoadMenu(", probe)
        self.assertIn("PropertySheet(&header)", probe)
        self.assertIn("PhTranslationEnabled = TRUE", probe)

    def test_unsafe_window_rewrite_and_modal_hook_are_removed(self) -> None:
        header = read_source("phlib/include/phtranslation.h")
        source = read_source("phlib/phtranslation.c")

        for symbol in (
            "PhTranslateWindowTree",
            "PhTranslateModalDialogBegin",
            "PhTranslateModalDialogEnd",
        ):
            self.assertNotIn(symbol, header)
            self.assertNotIn(symbol, source)


if __name__ == "__main__":
    unittest.main()
