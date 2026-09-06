import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_SOURCE = REPO_ROOT / "SystemInformer" / "plugin.c"
PLUGIN_CMAKE = REPO_ROOT / "plugins" / "CMakeLists.txt"
PLUGIN_SOLUTION = REPO_ROOT / "plugins" / "Plugins.sln"
PLUGIN_SOLUTION_XML = REPO_ROOT / "plugins" / "Plugins.slnx"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
ZIP_SOURCE = REPO_ROOT / "tools" / "CustomBuildTool" / "Zip.cs"
UPDATER_ROOT = REPO_ROOT / "plugins" / "Updater"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", source, re.S)
    if not match:
        raise AssertionError(f"function not found: {name}")

    depth = 1
    index = match.end()
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1

    if depth:
        raise AssertionError(f"unterminated function: {name}")

    return source[match.start():index]


class UpdaterDisabledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plugin_source = PLUGIN_SOURCE.read_text(encoding="utf-8-sig")
        cls.cmake = PLUGIN_CMAKE.read_text(encoding="utf-8-sig")
        cls.solution = PLUGIN_SOLUTION.read_text(encoding="utf-8-sig")
        cls.solution_xml = PLUGIN_SOLUTION_XML.read_text(encoding="utf-8-sig")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.zip_source = ZIP_SOURCE.read_text(encoding="utf-8-sig")

    def test_updater_source_is_retained_but_default_builds_exclude_it(self) -> None:
        self.assertTrue((UPDATER_ROOT / "Updater.vcxproj").is_file())
        self.assertTrue((UPDATER_ROOT / "main.c").is_file())
        self.assertNotRegex(self.cmake, r"(?m)^\s*add_subdirectory\s*\(\s*Updater\s*\)")
        self.assertNotIn("Updater\\Updater.vcxproj", self.solution)
        self.assertNotIn("Updater/Updater.vcxproj", self.solution_xml)
        self.assertNotIn("A0C1595C-FA3E-4B7A-936C-306BC6294C5E", self.solution.upper())

    def test_release_workflow_does_not_require_updater_and_rejects_it_from_package(self) -> None:
        self.assertNotIn(r"bin\Release64\plugins\Updater.dll", self.workflow)
        self.assertNotIn(r"plugins\Updater.dll=", self.workflow)
        self.assertRegex(
            self.workflow,
            r"(?s)Expand-Archive[^\n]*\n.*?Get-ChildItem -Path \$staging -Recurse -File \|"
            r".*?\.Name -ieq 'Updater\.dll'.*?if \(\$updaterDll\).*?exit 1",
        )

    def test_every_local_binary_zip_rejects_a_stale_updater_dll(self) -> None:
        body = function_body(self.zip_source, "CreateCompressedFolder")
        guard_index = body.index('Path.GetFileName(file)')
        write_index = body.index("WriteEntry(")
        self.assertLess(guard_index, write_index)
        self.assertIn('"Updater.dll"', body)
        self.assertIn("StringComparison.OrdinalIgnoreCase", body)
        self.assertRegex(
            body,
            r"throw new InvalidOperationException\([^;]*Updater\.dll[^;]*\);",
        )

    def test_updater_is_not_a_default_safe_plugin(self) -> None:
        default_list = self.plugin_source.split(
            "static CONST PH_STRINGREF DefaultPluginName[]", 1
        )[1].split("};", 1)[0]
        self.assertNotIn('L"Updater.dll"', default_list)

    def test_block_policy_matches_exact_basename_case_insensitively(self) -> None:
        helper = function_body(self.plugin_source, "PhpIsPluginBlockedByPolicy")
        self.assertIn('L"Updater.dll"', helper)
        self.assertRegex(helper, r"PhEqualStringRef2\s*\([^;]*L\"Updater\.dll\"\s*,\s*TRUE\s*\)")
        self.assertRegex(helper, r"PhFindLastCharInStringRef\s*\([^;]*L'\\\\'")
        self.assertRegex(helper, r"PhFindLastCharInStringRef\s*\([^;]*L'/'")

    def test_directory_enumeration_rejects_before_any_load_attempt(self) -> None:
        body = function_body(self.plugin_source, "EnumPluginsDirectoryCallback")
        policy_index = body.index("PhpIsPluginBlockedByPolicy")
        native_load_index = body.index("PhLoadPluginImage")
        win32_load_index = body.index("PhLoadPlugin(")
        self.assertLess(policy_index, native_load_index)
        self.assertLess(policy_index, win32_load_index)
        self.assertRegex(
            body,
            r"if\s*\(\s*PhpIsPluginBlockedByPolicy\s*\(\s*&baseName\s*\)\s*\)\s*return\s+TRUE\s*;",
        )

    def test_explicit_path_load_rejects_before_loadlibrary(self) -> None:
        body = function_body(self.plugin_source, "PhLoadPlugin")
        policy_index = body.index("PhpIsPluginBlockedByPolicy")
        load_index = body.index("LoadLibraryEx")
        self.assertLess(policy_index, load_index)
        self.assertRegex(
            body,
            r"if\s*\(\s*PhpIsPluginBlockedByPolicy\s*\(\s*FileName\s*\)\s*\)\s*return\s+STATUS_NOT_SUPPORTED\s*;",
        )

    def test_dynamic_menu_and_background_callbacks_cannot_register(self) -> None:
        dll_main = function_body(
            (UPDATER_ROOT / "main.c").read_text(encoding="utf-8-sig"),
            "DllMain",
        )
        self.assertIn("GeneralCallbackMainWindowShowing", dll_main)
        self.assertIn("GeneralCallbackMainMenuInitializing", dll_main)
        self.assertIn("GeneralCallbackOptionsWindowInitializing", dll_main)

        enum_body = function_body(self.plugin_source, "EnumPluginsDirectoryCallback")
        explicit_body = function_body(self.plugin_source, "PhLoadPlugin")
        self.assertIn("PhpIsPluginBlockedByPolicy", enum_body)
        self.assertIn("PhpIsPluginBlockedByPolicy", explicit_body)


if __name__ == "__main__":
    unittest.main()
