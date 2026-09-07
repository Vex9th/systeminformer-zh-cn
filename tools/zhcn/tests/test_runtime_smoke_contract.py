import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SMOKE_PATH = REPO_ROOT / "tools" / "zhcn" / "smoke_test.ps1"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
RESOURCE_HEADER_PATH = REPO_ROOT / "SystemInformer" / "resource.h"
SETTINGS_SOURCE_PATH = REPO_ROOT / "SystemInformer" / "settings.c"
ONLINE_CHECKS_HEADER_PATH = REPO_ROOT / "plugins" / "OnlineChecks" / "onlnchk.h"
ONLINE_CHECKS_PARTNER_PATH = REPO_ROOT / "plugins" / "OnlineChecks" / "partner.c"


class RuntimeSmokeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = SMOKE_PATH.read_text(encoding="utf-8-sig")
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8-sig")
        cls.resource_header = RESOURCE_HEADER_PATH.read_text(encoding="utf-8-sig")
        cls.settings_source = SETTINGS_SOURCE_PATH.read_text(encoding="utf-8-sig")
        cls.online_checks_header = ONLINE_CHECKS_HEADER_PATH.read_text(encoding="utf-8-sig")
        cls.online_checks_partner = ONLINE_CHECKS_PARTNER_PATH.read_text(encoding="utf-8-sig")

    def test_default_iterations_and_isolated_launch_arguments_are_locked(self) -> None:
        self.assertRegex(
            self.smoke,
            r"\[int\]\$Iterations\s*=\s*3",
        )
        self.assertRegex(
            self.smoke,
            r"for\s*\(\s*\$iteration\s*=\s*1\s*;\s*"
            r"\$iteration\s*-le\s*\$Iterations\s*;\s*\$iteration\+\+\s*\)",
        )
        self.assertRegex(
            self.smoke,
            r"(?s)Start-Process\s+`.*?-ArgumentList\s+\$launchArguments\s+`.*?"
            r"-WorkingDirectory\s+\$workingDirectory\s+`.*?-PassThru",
        )
        self.assertRegex(
            self.smoke,
            r'\$launchArguments\s*=\s*"-settings\s+`"\$settingsFile`"\s+-newinstance"',
        )
        self.assertNotIn("'-nosettings'", self.smoke)

    def test_isolated_settings_suppress_partner_prompt_without_enabling_network_checks(self) -> None:
        self.assertRegex(
            self.smoke,
            r"sys_info-smoke-\{0\}\.settings\.json",
        )
        expected_settings = {
            "Language": "'zh-CN'",
            "FirstRun": "0",
            "OnlineChecks.PartnerPromptShown": "'1'",
            "OnlineChecks.EnableScanning": "'0'",
            "OnlineChecks.HybridAnalysisEnableLookups": "'0'",
            "OnlineChecks.HybridAnalysisEnableAutoSubmit": "'0'",
            "OnlineChecks.VirusTotalEnableLookups": "'0'",
        }
        for name, value in expected_settings.items():
            self.assertRegex(
                self.smoke,
                rf"'{re.escape(name)}'\s*=\s*{value}",
            )
        setting_definitions = {
            "SETTING_NAME_SCAN_ENABLED": "EnableScanning",
            "SETTING_NAME_HYBRIDANALYSIS_LOOKUPS_ENABLED": "HybridAnalysisEnableLookups",
            "SETTING_NAME_HYBRIDANALYSIS_SUBMIT_ENABLED": "HybridAnalysisEnableAutoSubmit",
            "SETTING_NAME_VIRUSTOTAL_LOOKUPS_ENABLED": "VirusTotalEnableLookups",
            "SETTING_NAME_PARTNER_PROMPT_SHOWN": "PartnerPromptShown",
        }
        for macro, suffix in setting_definitions.items():
            self.assertRegex(
                self.online_checks_header,
                rf"#define\s+{macro}\s+\(PLUGIN_NAME\s+L\"\.{suffix}\"\)",
            )
        self.assertRegex(
            self.online_checks_partner,
            r"if\s*\(PhGetIntegerSetting\(SETTING_NAME_PARTNER_PROMPT_SHOWN\)\)\s*"
            r"return\s*;",
        )
        self.assertIn("[System.IO.File]::WriteAllText", self.smoke)
        loop_index = self.smoke.index("for ($iteration = 1")
        write_index = self.smoke.index("[System.IO.File]::WriteAllText")
        launch_index = self.smoke.index("Start-Process")
        cleanup_index = self.smoke.index("Remove-Item -LiteralPath $settingsFile -Force")
        self.assertLess(loop_index, write_index)
        self.assertLess(write_index, launch_index)
        self.assertLess(launch_index, cleanup_index)
        iteration_block = self.smoke[
            loop_index : self.smoke.index('Write-Host "PASS:', loop_index)
        ]
        self.assertRegex(
            iteration_block,
            r"(?s)finally\s*\{.*?"
            r"if\s*\(\$settingsFile\s+-and\s+"
            r"\(Test-Path\s+-LiteralPath\s+\$settingsFile\)\)\s*\{\s*"
            r"Remove-Item\s+-LiteralPath\s+\$settingsFile\s+-Force\s*\}",
        )

    def test_expandable_strings_do_not_use_ambiguous_colon_interpolation(self) -> None:
        self.assertNotRegex(
            self.smoke,
            r'"[^"\n]*\$(?:iteration|Iterations):',
        )

    def test_each_iteration_checks_window_response_and_module_mapping(self) -> None:
        self.assertIn("Get-ProcessWindows", self.smoke)
        self.assertIn("GetClassName", self.smoke)
        self.assertIn("$_.ClassName -eq 'sys_infoMainWindow'", self.smoke)
        self.assertNotIn("$_.Title -match 'sys_info'", self.smoke)
        self.assertIn("observed visible windows", self.smoke)
        self.assertRegex(
            self.smoke,
            r"(?s)\$observedWindows\s*=\s*@\(\s*"
            r"\$windows\s*\|\s*ForEach-Object\s*\{.*?"
            r"\$_\.ClassName.*?\$_\.Title.*?"
            r"\}\s*\)\s*-join\s*'; '",
        )
        self.assertRegex(
            self.smoke,
            r"(?s)if\s*\(\s*-not\s+\$observedWindows\s*\)\s*\{\s*"
            r"\$observedWindows\s*=\s*'<none>'\s*\}",
        )
        self.assertRegex(
            self.smoke,
            r"observed visible windows:\s*\$observedWindows",
        )
        self.assertRegex(
            self.settings_source,
            r'PhpAddStringSetting\(SETTING_MAIN_WINDOW_CLASS_NAME, L"sys_infoMainWindow"\)',
        )
        self.assertRegex(
            self.smoke,
            r"SendMessageTimeout\([^\n]*0x0000",
        )
        expected_modules = (
            "ToolStatus.dll",
            "ExtendedTools.dll",
            "ExtendedServices.dll",
            "DotNetTools.dll",
            "HardwareDevices.dll",
            "NetworkTools.dll",
            "OnlineChecks.dll",
            "UserNotes.dll",
            "WindowExplorer.dll",
            "ExtendedNotifications.dll",
        )
        for module in expected_modules:
            self.assertIn(f"'{module}'", self.smoke)
        self.assertEqual(len(expected_modules), 10)
        self.assertRegex(
            self.smoke,
            r"\$mappedModules\s+-contains\s+'Updater\.dll'",
        )
        self.assertIn("forbidden plugin module mapping: Updater.dll", self.smoke)
        self.assertIn("$expectedModuleMappings.Count", self.smoke)
        self.assertNotIn("11 plugin module mappings present", self.smoke)
        self.assertIn("module mapping", self.smoke)
        self.assertNotIn("plugins loaded", self.smoke.lower())

    def test_blocking_window_diagnostic_includes_child_control_identity_and_text(self) -> None:
        self.assertIn("EnumChildWindows", self.smoke)
        self.assertIn("GetDlgCtrlID", self.smoke)
        helper_match = re.search(
            r"(?s)function Get-ChildWindowDescriptions\b.*?"
            r"(?=\nfunction Get-NewDumpFiles\b)",
            self.smoke,
        )
        self.assertIsNotNone(helper_match)
        helper = helper_match.group(0)
        self.assertRegex(
            helper,
            r"GetWindowText\(\$windowHandle,\s*\$text,\s*1024\)",
        )
        self.assertRegex(
            helper,
            r"GetClassName\(\$windowHandle,\s*\$className,\s*256\)",
        )
        self.assertRegex(
            helper,
            r"ControlId\s*=\s*\[Native\.Win\]::GetDlgCtrlID\(\$windowHandle\)",
        )
        self.assertIn('.Replace("`r", \' \').Replace("`n", \' \')', helper)
        self.assertRegex(
            helper,
            r"EnumChildWindows\(\$ParentHandle,\s*\$callback,\s*"
            r"\[IntPtr\]::Zero\)",
        )
        self.assertRegex(
            self.smoke,
            r"(?s)Get-ChildWindowDescriptions\s+\$_\.Handle\s*\|\s*"
            r"ForEach-Object\s*\{.*?ControlId.*?ClassName.*?Text",
        )
        self.assertRegex(
            self.smoke,
            r"children=\[\$childWindows\]",
        )

    def test_success_path_requests_application_exit_and_requires_clean_exit(self) -> None:
        self.assertIn("PostMessage", self.smoke)
        self.assertIn("$exitCommandId = 10001", self.smoke)
        self.assertRegex(
            self.resource_header,
            r"#define\s+ID_HACKER_EXIT\s+10001\b",
        )
        self.assertRegex(
            self.smoke,
            r"PostMessage\([^\n]*0x0111[^\n]*\$exitCommandId",
        )
        self.assertNotIn("0x0010", self.smoke)
        self.assertIn("WaitForExit(30000)", self.smoke)
        self.assertRegex(self.smoke, r"\$process\.ExitCode\s*-ne\s*0")

        cleanup_start = self.smoke.index("finally {\n            if ($process)")
        cleanup_end = self.smoke.index("\n        }\n    }", cleanup_start)
        failure_cleanup = self.smoke[cleanup_start:cleanup_end]
        self.assertEqual(self.smoke.count("Stop-Process"), 1)
        self.assertIn("-not $iterationSucceeded", failure_cleanup)
        self.assertIn("Stop-Process -Id $process.Id -Force", failure_cleanup)

    def test_local_dumps_are_fail_closed_scoped_and_cleaned(self) -> None:
        key = (
            "HKCU:\\Software\\Microsoft\\Windows\\Windows Error Reporting"
            "\\LocalDumps\\sys_info.exe"
        )
        self.assertIn(key, self.smoke)
        self.assertIn("[string]$DumpDirectory", self.smoke)
        self.assertRegex(
            self.smoke,
            r"Test-Path\s+-LiteralPath\s+\$dumpRegistryKey",
        )
        self.assertRegex(
            self.smoke,
            r"New-Item\s+-Path\s+\$dumpRegistryKey",
        )
        self.assertIn("DumpFolder", self.smoke)
        self.assertIn("$dumpKeyCreated = $true", self.smoke)
        self.assertIn("$dumpParentKeys = @(", self.smoke)
        self.assertIn("$createdDumpParentKeys", self.smoke)
        self.assertRegex(
            self.smoke,
            r"foreach\s*\(\$dumpParentKey\s+in\s+\$dumpParentKeys\)",
        )
        self.assertIn("$createdDumpParentKeys.Count - 1", self.smoke)
        self.assertRegex(
            self.smoke,
            r"if\s*\(\$dumpKeyCreated\)\s*\{[^}]*"
            r"Remove-Item\s+-LiteralPath\s+\$dumpRegistryKey",
        )
        self.assertRegex(self.smoke, r"Get-ChildItem[^\n]*\*\.dmp")
        self.assertRegex(self.smoke, r"new crash dump")

        test_index = self.smoke.index("Test-Path -LiteralPath $dumpRegistryKey")
        create_index = self.smoke.index("New-Item -Path $dumpRegistryKey")
        self.assertLess(test_index, create_index)
        create_line = self.smoke[create_index:self.smoke.index("\n", create_index)]
        self.assertNotIn("-Force", create_line)
        self.assertNotIn("Set-ItemProperty", self.smoke)

    def test_both_workflow_gates_use_runner_temp_and_three_iterations(self) -> None:
        self.assertEqual(self.workflow.count("Windows x64 smoke gate"), 2)
        self.assertEqual(self.workflow.count("-Iterations 3"), 2)
        self.assertEqual(self.workflow.count("${{ runner.temp }}"), 2)
        self.assertEqual(self.workflow.count("-DumpDirectory"), 2)
        self.assertNotIn("Runtime translation smoke test", self.workflow)

    def test_old_exaggerated_success_text_is_removed(self) -> None:
        self.assertNotIn("PASS all 11 plugins loaded", self.smoke)
        self.assertNotIn("ALL RUNTIME SMOKE CHECKS PASSED", self.smoke)
        self.assertNotIn("verifies the main window title and that every plugin is", self.smoke)
        self.assertNotIn("loaded", self.smoke.lower())
        self.assertNotRegex(self.smoke, r"\bALL\b")


if __name__ == "__main__":
    unittest.main()
