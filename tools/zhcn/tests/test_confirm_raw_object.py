import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("confirm_raw_object_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
    match = re.search(
        rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening_brace = source.find("{", match.start())
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index]

    raise AssertionError(f"unterminated function: {name}")


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


class ConfirmRawObjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.util = (REPO_ROOT / "phlib" / "util.c").read_text(
            encoding="utf-8-sig"
        )
        cls.header = (REPO_ROOT / "phlib" / "include" / "phutil.h").read_text(
            encoding="utf-8-sig"
        )
        cls.actions = (REPO_ROOT / "SystemInformer" / "actions.c").read_text(
            encoding="utf-8-sig"
        )
        cls.envdlg = (REPO_ROOT / "SystemInformer" / "envdlg.c").read_text(
            encoding="utf-8-sig"
        )
        cls.exports = (REPO_ROOT / "SystemInformer" / "SystemInformer.def").read_text(
            encoding="utf-8-sig"
        )

    def calls_in(self, source: str, function: str, call: str):
        body = function_body(source, function, self.audit)
        return [
            tuple(compact(argument) for argument in arguments)
            for name, arguments, _, _ in self.audit.find_calls(body, {call})
            if name == call
        ]

    def test_system_object_is_translated_only_by_legacy_route(self) -> None:
        sink = function_body(self.util, "PhpShowConfirmMessage", self.audit)
        legacy = function_body(self.util, "PhShowConfirmMessage", self.audit)
        raw = function_body(self.util, "PhShowConfirmMessageRawObject", self.audit)

        self.assertEqual(sink.count("PhTranslateString(Object)"), 1)
        self.assertRegex(
            sink,
            r"TranslateObject\s*\?\s*PhTranslateString\(Object\)\s*:\s*Object",
        )
        self.assertRegex(
            legacy,
            r"PhpShowConfirmMessage\s*\([^;]*Object[^;]*TRUE\s*\)",
        )
        self.assertRegex(
            raw,
            r"PhpShowConfirmMessage\s*\([^;]*Object[^;]*FALSE\s*\)",
        )
        self.assertNotIn("PhTranslateString", raw)

        translations = {"System": "系统"}
        legacy_translates_object = compact(legacy).endswith("TRUE);")
        raw_translates_object = compact(raw).endswith("TRUE);")

        self.assertEqual(
            translations.get("System", "System")
            if legacy_translates_object
            else "System",
            "系统",
        )
        self.assertEqual(
            translations.get("System", "System")
            if raw_translates_object
            else "System",
            "System",
        )

    def test_raw_api_is_internal_and_does_not_change_export_ordinals(self) -> None:
        prototype = re.compile(
            r"PHLIBAPI\s+BOOLEAN\s+NTAPI\s+{name}\s*\("
            r"\s*_In_ HWND WindowHandle,"
            r"\s*_In_ PCWSTR Verb,"
            r"\s*_In_ PCWSTR Object,"
            r"\s*_In_opt_ PCWSTR Message,"
            r"\s*_In_ BOOLEAN Warning\s*\)\s*;",
            re.DOTALL,
        )

        self.assertRegex(
            self.header,
            re.compile(prototype.pattern.format(name="PhShowConfirmMessage"), re.DOTALL),
        )
        self.assertRegex(
            self.header,
            re.compile(
                r"#if defined\(_PHLIB_\)\s+BOOLEAN\s+NTAPI\s+"
                r"PhShowConfirmMessageRawObject\s*\("
                r"\s*_In_ HWND WindowHandle,"
                r"\s*_In_ PCWSTR Verb,"
                r"\s*_In_ PCWSTR Object,"
                r"\s*_In_opt_ PCWSTR Message,"
                r"\s*_In_ BOOLEAN Warning\s*\)\s*;\s+#endif",
                re.DOTALL,
            ),
        )
        self.assertNotRegex(
            self.header,
            r"PHLIBAPI\s+BOOLEAN\s+NTAPI\s+PhShowConfirmMessageRawObject",
        )
        self.assertNotIn("PhShowConfirmMessageRawObject", self.exports)

    def test_raw_api_keeps_translatable_arguments_in_the_audit(self) -> None:
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhShowConfirmMessageRawObject"),
            {1: "c_confirm", 3: "c_confirm"},
        )
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhpShowConfirmMessageObject"),
            {1: "c_confirm", 3: "c_confirm"},
        )

        entries = []
        self.audit.scan_c_file(str(REPO_ROOT / "SystemInformer" / "actions.c"), entries)
        self.assertTrue(
            any(
                entry["file"] == "SystemInformer/actions.c"
                and 1700 <= entry["line"] <= 1770
                for entry in entries
            )
        )

    def test_two_process_connector_has_a_real_runtime_translation(self) -> None:
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        generated = (REPO_ROOT / "phlib" / "phtranslation_zhcn.c").read_text(
            encoding="utf-8-sig"
        )

        self.assertEqual(translations["strings"].get(" and "), " 和 ")
        self.assertNotIn(" and ", translations["native_strings"])
        self.assertIn('{ L" and ", L" 和 ", },', generated)

    def test_all_confirmed_dynamic_objects_use_raw_route(self) -> None:
        dynamic_functions = (
            "PhUiTerminateTreeProcess",
            "PhUiSuspendTreeProcess",
            "PhUiResumeTreeProcess",
            "PhUiFreezeTreeProcess",
            "PhUiRestartProcess",
            "PhUiSetExecutionRequiredProcess",
            "PhUiDeleteService",
            "PhUiUnloadModule",
        )

        for function in dynamic_functions:
            with self.subTest(function=function):
                self.assertEqual(
                    len(
                        self.calls_in(
                            self.actions, function, "PhShowConfirmMessageRawObject"
                        )
                    ),
                    1,
                )
                self.assertEqual(
                    len(self.calls_in(self.actions, function, "PhShowConfirmMessage")),
                    0,
                )

        chooser = function_body(
            self.actions, "PhpShowConfirmMessageObject", self.audit
        )
        self.assertRegex(
            chooser,
            r"RawObject\s*\?\s*PhShowConfirmMessageRawObject\s*\([^;]+\)"
            r"\s*:\s*PhShowConfirmMessage\s*\([^;]+\)",
        )

        process_helper = function_body(
            self.actions, "PhpShowContinueMessageProcesses", self.audit
        )
        process_helper_compact = compact(process_helper)
        self.assertIn("if(NumberOfProcesses==1)", process_helper_compact)
        self.assertIn("elseif(NumberOfProcesses==2)", process_helper_compact)
        self.assertEqual(process_helper_compact.count("rawObject=TRUE;"), 2)
        self.assertEqual(process_helper_compact.count("rawObject=FALSE;"), 1)
        self.assertEqual(
            len(
                self.calls_in(
                    self.actions,
                    "PhpShowContinueMessageProcesses",
                    "PhpShowConfirmMessageObject",
                )
            ),
            3,
        )
        masked_actions = self.audit.mask_c_comments(self.actions)
        self.assertEqual(masked_actions.count("PhShowConfirmMessageRawObject("), 9)

    def test_dynamic_object_fragments_are_translated_before_raw_composition(self) -> None:
        process_helper = compact(
            function_body(
                self.actions, "PhpShowContinueMessageProcesses", self.audit
            )
        )
        self.assertIn('PhTranslateString(L"and")', process_helper)

        for function in (
            "PhUiTerminateTreeProcess",
            "PhUiSuspendTreeProcess",
            "PhUiResumeTreeProcess",
        ):
            with self.subTest(function=function):
                body = compact(function_body(self.actions, function, self.audit))
                self.assertIn(
                    'PhaConcatStrings2(Process->ProcessName->Buffer,'
                    'PhTranslateString(L"anditsdescendants"))->Buffer',
                    body,
                )
                self.assertNotIn("PhConcatStringRefZ", body)

        execution_required = compact(
            function_body(
                self.actions, "PhUiSetExecutionRequiredProcess", self.audit
            )
        )
        self.assertIn(
            'PhaConcatStrings2(PhTranslateString(L"of"),'
            "Process->ProcessName->Buffer)->Buffer",
            execution_required,
        )

    def test_formatted_environment_variable_name_uses_raw_route(self) -> None:
        calls = self.calls_in(
            self.envdlg, "EtEnvironmentDelete", "PhShowConfirmMessageRawObject"
        )

        self.assertEqual(len(calls), 1)
        self.assertIn(
            'PhaFormatString(PhTranslateString(L"theenvironmentvariable\\"%s\\"")',
            calls[0][2],
        )
        self.assertEqual(
            len(
                self.calls_in(
                    self.envdlg, "EtEnvironmentDelete", "PhShowConfirmMessage"
                )
            ),
            0,
        )

    def test_fixed_object_confirmations_keep_legacy_route(self) -> None:
        fixed_functions = {
            "PhUiRestartComputer": 7,
            "PhUiShutdownComputer": 4,
            "PhUiHandleComputerBootApplicationMenu": 1,
            "PhUiHandleComputerFirmwareApplicationMenu": 1,
            "PhUiLogoffSession": 1,
            "PhUiSetVirtualizationProcess": 1,
            "PhUiSetCriticalProcess": 2,
            "PhUiSetEcoModeProcess": 1,
            "PhpShowContinueMessageServices": 1,
            "PhpShowContinueMessageThreads": 1,
            "PhUiFreeMemory": 1,
            "PhUiCloseHandles": 2,
        }

        for function, expected_count in fixed_functions.items():
            with self.subTest(function=function):
                self.assertEqual(
                    len(self.calls_in(self.actions, function, "PhShowConfirmMessage")),
                    expected_count,
                )
                self.assertEqual(
                    len(
                        self.calls_in(
                            self.actions, function, "PhShowConfirmMessageRawObject"
                        )
                    ),
                    0,
                )

        masked_actions = self.audit.mask_c_comments(self.actions)
        self.assertEqual(masked_actions.count("PhShowConfirmMessage("), 24)


if __name__ == "__main__":
    unittest.main()
