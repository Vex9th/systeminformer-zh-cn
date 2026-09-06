#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def read_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")


def function_body(source: str, function_name: str) -> str:
    match = re.search(rf"\b{re.escape(function_name)}\s*\([^;]*?\)\s*\{{", source, re.S)
    if not match:
        raise AssertionError(f"function not found: {function_name}")

    start = match.end() - 1
    depth = 0
    for offset in range(start, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:offset]
    raise AssertionError(f"unterminated function: {function_name}")


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

    def test_dialog_template_rewriter_and_process_cache_are_removed(self) -> None:
        header = read_source("phlib/include/phtranslation.h")
        source = read_source("phlib/phtranslation.c")

        for symbol in (
            "PH_TL_WRITER",
            "PhTlp",
            "PhTlTemplateCache",
            "PhTranslateDialogTemplateCopy",
            "PhTranslateDialogTemplateCached",
        ):
            self.assertNotIn(symbol, header)
            self.assertNotIn(symbol, source)

        self.assertIn("PhTranslationEnabled", header)
        self.assertIn("PhTranslateString", header)
        self.assertIn("PhTranslationTableZhCn", source)

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

    def test_dialog_entrypoints_use_native_templates_and_exact_english_retry(self) -> None:
        source = read_source("phlib/guisup.c")

        create = function_body(source, "PhCreateDialog")
        self.assertRegex(
            create,
            r"PhLoadUiResource\(\s*Instance\s*,\s*Template\s*,\s*RT_DIALOG\s*,\s*"
            r"NULL\s*,\s*&dialogTemplate\s*,\s*&fallbackToEnglish\s*\)",
        )
        self.assertRegex(create, r"if\s*\(\s*!dialogHandle\s*&&\s*nativeLocalized\s*\)")
        self.assertIn("PhLoadResourceForLanguage(", create)
        self.assertIn("MAKELANGID(LANG_ENGLISH, SUBLANG_ENGLISH_US)", create)
        self.assertNotIn("PhTranslate", create)

        dialog_box = function_body(source, "PhDialogBox")
        self.assertIn("PhLoadUiResource(", dialog_box)
        self.assertRegex(
            dialog_box,
            r"if\s*\(\s*dialogResult\s*==\s*INT_ERROR\s*&&\s*nativeLocalized\s*\)",
        )
        self.assertIn("PhLoadResourceForLanguage(", dialog_box)
        self.assertNotIn("PhTranslate", dialog_box)

        property_page = function_body(source, "PhCreatePropertySheetPage")
        self.assertRegex(
            property_page,
            r"if\s*\(\s*Page->dwFlags\s*&\s*PSP_DLGINDIRECT\s*\)\s*"
            r"return\s+CreatePropertySheetPage\(Page\)\s*;",
        )
        self.assertIn("PhLoadUiResource(", property_page)
        self.assertIn("page.dwFlags |= PSP_DLGINDIRECT", property_page)
        self.assertIn("page.pResource = dialogTemplate", property_page)
        self.assertRegex(
            property_page,
            r"if\s*\(\s*!propSheetPageHandle\s*&&\s*nativeLocalized\s*\)",
        )
        self.assertIn("PhLoadResourceForLanguage(", property_page)
        self.assertNotIn("PhTranslate", property_page)

    def test_from_template_styles_each_owned_copy_and_frees_it_once(self) -> None:
        source = read_source("phlib/guisup.c")
        body = function_body(source, "PhCreateDialogFromTemplate")

        self.assertIn("PhLoadUiResourceCopy(", body)
        self.assertIn("PhLoadResourceCopyForLanguage(", body)
        self.assertEqual(body.count("dialogTemplate->style = Style"), 2)
        self.assertEqual(body.count("((DLGTEMPLATE *)dialogTemplate)->style = Style"), 2)
        self.assertEqual(body.count("PhFree(dialogTemplate)"), 2)
        self.assertNotIn("PhTranslate", body)

    def test_process_property_page_title_parser_is_bounded_and_not_retranslated(self) -> None:
        source = read_source("SystemInformer/procprp.c")
        parser = function_body(source, "PhpParseDialogTemplateSzOrOrd")
        reader = function_body(source, "PhpReadDialogTemplateTitle")
        add_page = function_body(source, "PhAddProcessPropPage")

        self.assertIn("ResourceEnd", parser)
        self.assertIn("sizeof(USHORT)", parser)
        self.assertIn("0xFFFF", parser)
        self.assertRegex(parser, r"return\s+FALSE\s*;")
        self.assertIn("PhLoadUiResource(", reader)
        self.assertIn("&resourceLength", reader)
        self.assertIn("PhpParseDialogTemplateSzOrOrd", reader)
        self.assertIn("PhCreateStringEx(title, titleLength)", reader)
        self.assertNotIn("PhCountStringZ", reader)
        self.assertNotIn("PhTranslateString(titles", add_page)

    def test_windows_loader_probe_is_built_and_run_by_ci(self) -> None:
        project = read_source("tools/tests/phlib-test/phlib-test.vcxproj")
        main = read_source("tools/tests/phlib-test/main.c")
        probe = read_source("tools/tests/phlib-test/t_resource.c")
        resources = read_source("tools/tests/phlib-test/phlib-test.rc")
        workflow = read_source(".github/workflows/zh-cn-build.yml")

        self.assertIn('<ClCompile Include="t_resource.c" />', project)
        self.assertIn('<ResourceCompile Include="phlib-test.rc" />', project)
        self.assertNotIn("#pragma code_page", resources)
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
        self.assertIn("PhCreateDialogFromTemplate(", probe)
        self.assertIn("WS_SYSMENU", probe)

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
