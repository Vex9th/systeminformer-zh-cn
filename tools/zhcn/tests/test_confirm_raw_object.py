import importlib.util
import json
import pathlib
import re
import tempfile
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
        raw_action = function_body(
            self.util, "PhShowConfirmMessageRawAction", self.audit
        )

        self.assertEqual(sink.count("PhTranslateString(Object)"), 1)
        self.assertRegex(
            sink,
            r"TranslateObject\s*\?\s*PhTranslateString\(Object\)\s*:\s*Object",
        )
        self.assertRegex(
            legacy,
            r"PhpShowConfirmMessage\s*\([^;]*Object\s*,\s*NULL[^;]*TRUE\s*\)",
        )
        self.assertRegex(
            raw,
            r"PhpShowConfirmMessage\s*\([^;]*Object\s*,\s*NULL[^;]*FALSE\s*\)",
        )
        self.assertNotIn("PhTranslateString", raw)
        self.assertRegex(
            raw_action,
            r"PhpShowConfirmMessage\s*\([^;]*NULL\s*,\s*Action[^;]*FALSE\s*\)",
        )
        self.assertNotIn("PhTranslateString", raw_action)

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
                r"\s*_In_ BOOLEAN Warning\s*\)\s*;",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            self.header,
            re.compile(
                r"#if defined\(_PHLIB_\).*?"
                r"PhShowConfirmMessageRawAction\s*\("
                r"\s*_In_ HWND WindowHandle,"
                r"\s*_In_ PCWSTR Verb,"
                r"\s*_In_ PCWSTR Action,"
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
        self.assertNotIn("PhShowConfirmMessageRawAction", self.exports)

    def test_raw_api_keeps_translatable_arguments_in_the_audit(self) -> None:
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhShowConfirmMessageRawObject"),
            {1: "c_confirm", 3: "c_confirm"},
        )
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhpShowConfirmMessageObject"),
            {1: "c_confirm", 3: "c_confirm"},
        )
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhShowConfirmMessageRawAction"),
            {1: "c_confirm", 2: "c_confirm", 3: "c_confirm"},
        )

        action_entries = []
        self.audit.scan_c_file(
            str(REPO_ROOT / "SystemInformer" / "actions.c"), action_entries
        )
        dangerous_formats = {
            "You are about to %s one or more system processes.",
            "You are about to %s one or more critical processes.",
            "You are about to %s one or more critical processes. This will shut down the operating system immediately.",
        }
        self.assertFalse(
            dangerous_formats
            & {
                entry["english"]
                for entry in action_entries
                if entry["category"] == "c_confirm"
            }
        )

        resource_entries = []
        self.audit.scan_rc_file(
            str(REPO_ROOT / "SystemInformer" / "SystemInformer.rc"),
            resource_entries,
        )
        self.assertLessEqual(
            dangerous_formats,
            {
                entry["english"]
                for entry in resource_entries
                if entry["category"] == "rc_stringtable"
            },
        )

        helper = compact(
            function_body(
                self.actions, "PhpShowContinueMessageProcesses", self.audit
            )
        )
        for resource_id in (
            "IDS_PH_SYSTEM_PROCESS_ACTION_WARNING_FORMAT",
            "IDS_PH_CRITICAL_PROCESS_ACTION_WARNING_FORMAT",
            "IDS_PH_CRITICAL_PROCESS_TERMINATE_WARNING_FORMAT",
        ):
            self.assertIn(
                f"PhGetApplicationUiString({resource_id}),verb",
                helper,
            )
        self.assertEqual(helper.count("rawObject"), 7)

    def test_raw_action_audit_includes_the_complete_action_argument(self) -> None:
        source = r'''
        void Show(void)
        {
            PhShowConfirmMessageRawAction(
                NULL,
                L"delete",
                L"delete the selected file",
                L"This cannot be undone.",
                FALSE
                );
        }
        '''
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = pathlib.Path(temporary_directory) / "raw_action.c"
            path.write_text(source, encoding="utf-8")
            entries = []
            self.audit.scan_c_file(str(path), entries)

        self.assertEqual(
            [
                entry["english"]
                for entry in entries
                if entry["category"] == "c_confirm"
            ],
            ["delete", "delete the selected file", "This cannot be undone."],
        )

    def test_two_process_connector_uses_a_complete_native_format(self) -> None:
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        generated = (REPO_ROOT / "phlib" / "phtranslation_zhcn.c").read_text(
            encoding="utf-8-sig"
        )

        self.assertEqual(translations["native_strings"].get("%s and %s"), "%s 和 %s")
        self.assertNotIn(" and ", translations["strings"])
        self.assertNotIn('{ L" and ", L" 和 ", },', generated)

    def test_actions_use_native_formats_without_undeclared_translation_calls(self) -> None:
        masked_actions = self.audit.mask_c_comments(self.actions)
        self.assertNotIn("PhTranslateString(", masked_actions)

        header = (REPO_ROOT / "SystemInformer" / "resource.h").read_text(
            encoding="utf-8-sig"
        )
        english_rc = (
            REPO_ROOT / "SystemInformer" / "SystemInformer.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_rc = (
            REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        resources = (
            ("IDS_PH_PROCESS_PAIR_FORMAT", 2663, "%s and %s", "%s 和 %s"),
            (
                "IDS_PH_PROCESS_AND_DESCENDANTS_FORMAT",
                2664,
                "%s and its descendants",
                "%s 及其子进程",
            ),
            (
                "IDS_PH_ACTION_CHANGE_EXECUTION_REQUIRED",
                2665,
                "change the execution required state",
                "更改“需要执行”状态",
            ),
            (
                "IDS_PH_EXECUTION_REQUIRED_ACTION_FORMAT",
                2666,
                "change the execution required state of %s",
                "更改 %s 的“需要执行”状态",
            ),
        )
        for symbol, resource_id, english, chinese in resources:
            with self.subTest(symbol=symbol):
                self.assertRegex(
                    header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$"
                )
                self.assertRegex(
                    english_rc,
                    rf'(?m)^\s*{symbol}\s+"{re.escape(english)}"$',
                )
                self.assertRegex(
                    chinese_rc,
                    rf'(?m)^\s*{symbol}\s+"{re.escape(chinese)}"$',
                )

        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        expected_native = {
            "%s and %s": "%s 和 %s",
            "%s and its descendants": "%s 及其子进程",
            "change the execution required state": "更改“需要执行”状态",
            "change the execution required state of %s": "更改 %s 的“需要执行”状态",
        }
        for english, chinese in expected_native.items():
            with self.subTest(english=english):
                self.assertEqual(translations["native_strings"].get(english), chinese)
                self.assertNotIn(english, translations["strings"])

        for retired_fragment in (" and ", " and its descendants", "of "):
            self.assertNotIn(retired_fragment, translations["strings"])

        execution_required = compact(
            function_body(
                self.actions, "PhUiSetExecutionRequiredProcess", self.audit
            )
        )
        self.assertIn(
            "PhShowConfirmMessageRawAction(WindowHandle,"
            "PhGetApplicationUiString(IDS_PH_ACTION_CHANGE_EXECUTION_REQUIRED),"
            "PhaFormatString(PhGetApplicationUiString("
            "IDS_PH_EXECUTION_REQUIRED_ACTION_FORMAT),"
            "Process->ProcessName->Buffer)->Buffer",
            execution_required,
        )
        self.assertEqual(
            self.audit.CALL_SPECS.get("PhShowConfirmMessageRawAction"),
            {1: "c_confirm", 2: "c_confirm", 3: "c_confirm"},
        )
        self.assertIn("PhShowConfirmMessageRawAction", self.header)
        self.assertNotIn("PhShowConfirmMessageRawAction", self.exports)

    def assert_process_action_id_routes(self, source: str) -> None:
        expected = {
            "PhUiTerminateProcesses": "IDS_PH_ACTION_TERMINATE",
            "PhUiSuspendProcesses": "IDS_PH_ACTION_SUSPEND",
            "PhUiResumeProcesses": "IDS_PH_ACTION_RESUME",
        }
        for function, action_id in expected.items():
            calls = self.calls_in(
                source, function, "PhpShowContinueMessageProcesses"
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], action_id)

    def test_process_action_ids_match_their_callers(self) -> None:
        self.assert_process_action_id_routes(self.actions)

    def test_process_action_id_contract_rejects_swapped_routes(self) -> None:
        mutated = self.actions.replace(
            "WindowHandle,\n        IDS_PH_ACTION_TERMINATE,\n        L\"Terminating",
            "WindowHandle,\n        IDS_PH_ACTION_SUSPEND,\n        L\"Terminating",
            1,
        ).replace(
            "WindowHandle,\n        IDS_PH_ACTION_SUSPEND,\n        NULL,",
            "WindowHandle,\n        IDS_PH_ACTION_TERMINATE,\n        NULL,",
            1,
        )
        self.assertNotEqual(mutated, self.actions)
        with self.assertRaises(AssertionError):
            self.assert_process_action_id_routes(mutated)

    def test_raw_action_branch_never_reads_null_object_or_releases_early(self) -> None:
        sink = function_body(self.util, "PhpShowConfirmMessage", self.audit)
        match = re.search(
            r"if\s*\(RawAction\)\s*\{(?P<raw>.*?)\}\s*else\s*\{",
            sink,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        raw_branch = match.group("raw")
        self.assertIn("action = PhaCreateString(RawAction)", raw_branch)
        self.assertNotIn("Object", raw_branch)
        self.assertNotIn("PhDereferenceObject(action)", sink)

        create_index = sink.index("action = PhaCreateString(RawAction)")
        task_dialog_index = sink.index("PhShowTaskDialog(")
        fallback_index = sink.index("PhShowMessage(")
        self.assertLess(create_index, task_dialog_index)
        self.assertLess(task_dialog_index, fallback_index)

    def test_all_confirmed_dynamic_objects_use_raw_route(self) -> None:
        raw_object_functions = (
            "PhUiTerminateTreeProcess",
            "PhUiSuspendTreeProcess",
            "PhUiResumeTreeProcess",
            "PhUiFreezeTreeProcess",
            "PhUiRestartProcess",
            "PhUiDeleteService",
            "PhUiUnloadModule",
        )

        for function in raw_object_functions:
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

        self.assertEqual(
            len(
                self.calls_in(
                    self.actions,
                    "PhUiSetExecutionRequiredProcess",
                    "PhShowConfirmMessageRawAction",
                )
            ),
            1,
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
        self.assertEqual(masked_actions.count("PhShowConfirmMessageRawObject("), 8)
        self.assertEqual(masked_actions.count("PhShowConfirmMessageRawAction("), 1)

    def test_dynamic_object_formats_are_localizable_as_complete_phrases(self) -> None:
        process_helper = compact(
            function_body(
                self.actions, "PhpShowContinueMessageProcesses", self.audit
            )
        )
        self.assertIn(
            "PhaFormatString(PhGetApplicationUiString(IDS_PH_PROCESS_PAIR_FORMAT),"
            "Processes[0]->ProcessName->Buffer,Processes[1]->ProcessName->Buffer)",
            process_helper,
        )

        for function in (
            "PhUiTerminateTreeProcess",
            "PhUiSuspendTreeProcess",
            "PhUiResumeTreeProcess",
        ):
            with self.subTest(function=function):
                body = compact(function_body(self.actions, function, self.audit))
                self.assertIn(
                    "PhaFormatString(PhGetApplicationUiString("
                    "IDS_PH_PROCESS_AND_DESCENDANTS_FORMAT),"
                    "Process->ProcessName->Buffer)->Buffer",
                    body,
                )
                self.assertNotIn("PhaConcatStrings2", body)

        execution_required = compact(
            function_body(
                self.actions, "PhUiSetExecutionRequiredProcess", self.audit
            )
        )
        self.assertIn(
            "PhaFormatString(PhGetApplicationUiString("
            "IDS_PH_EXECUTION_REQUIRED_ACTION_FORMAT),"
            "Process->ProcessName->Buffer)->Buffer",
            execution_required,
        )

    def assert_environment_variable_delete_route(self, source: str) -> None:
        calls = self.calls_in(
            source, "EtEnvironmentDelete", "PhShowConfirmMessageRawObject"
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], "PhGetApplicationUiString(IDS_PH_ACTION_DELETE)")
        self.assertIn(
            "PhaFormatString(PhGetApplicationUiString("
            "IDS_PH_ENVIRONMENT_VARIABLE_OBJECT_FORMAT)",
            calls[0][2],
        )
        self.assertNotIn("PhTranslateString(", source)
        self.assertEqual(
            len(self.calls_in(source, "EtEnvironmentDelete", "PhShowConfirmMessage")),
            0,
        )

    def test_formatted_environment_variable_name_uses_raw_route(self) -> None:
        self.assert_environment_variable_delete_route(self.envdlg)

        header = (REPO_ROOT / "SystemInformer" / "resource.h").read_text(
            encoding="utf-8-sig"
        )
        english_rc = (
            REPO_ROOT / "SystemInformer" / "SystemInformer.rc"
        ).read_text(encoding="utf-8-sig")
        chinese_rc = (
            REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc"
        ).read_text(encoding="utf-8-sig")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertRegex(
            header,
            r"(?m)^#define\s+IDS_PH_ENVIRONMENT_VARIABLE_OBJECT_FORMAT\s+2667$",
        )
        self.assertRegex(
            english_rc,
            r'(?m)^\s*IDS_PH_ENVIRONMENT_VARIABLE_OBJECT_FORMAT\s+"the environment variable ""%s"""$',
        )
        self.assertRegex(
            chinese_rc,
            r'(?m)^\s*IDS_PH_ENVIRONMENT_VARIABLE_OBJECT_FORMAT\s+"环境变量“%s”"$',
        )
        self.assertEqual(
            translations["native_strings"].get('the environment variable "%s"'),
            "环境变量“%s”",
        )
        self.assertNotIn('the environment variable "%s"', translations["strings"])

    def test_environment_variable_route_rejects_wrong_resource_and_runtime_translation(self) -> None:
        for mutated in (
            self.envdlg.replace(
                "IDS_PH_ENVIRONMENT_VARIABLE_OBJECT_FORMAT",
                "IDS_PH_EDIT_ENVIRONMENT_TITLE_FORMAT",
                1,
            ),
            self.envdlg.replace(
                "PhGetApplicationUiString(IDS_PH_ENVIRONMENT_VARIABLE_OBJECT_FORMAT)",
                'PhTranslateString(L"the environment variable \\"%s\\"")',
                1,
            ),
        ):
            with self.assertRaises(AssertionError):
                self.assert_environment_variable_delete_route(mutated)

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
