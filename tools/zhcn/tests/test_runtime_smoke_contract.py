import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SMOKE_PATH = REPO_ROOT / "tools" / "zhcn" / "smoke_test.ps1"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"


class RuntimeSmokeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = SMOKE_PATH.read_text(encoding="utf-8-sig")
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8-sig")

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
            r"\$launchArguments\s*=\s*@\(\s*'-nosettings'\s*,\s*'-newinstance'\s*\)",
        )

    def test_each_iteration_checks_window_response_and_module_mapping(self) -> None:
        self.assertIn("Get-ProcessWindows", self.smoke)
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

    def test_success_path_requests_wm_close_and_requires_clean_exit(self) -> None:
        self.assertIn("PostMessage", self.smoke)
        self.assertIn("0x0010", self.smoke)
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
