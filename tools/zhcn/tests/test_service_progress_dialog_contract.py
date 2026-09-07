#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
ACTIONS_PATH = REPO_ROOT / "SystemInformer" / "actions.c"

RESOURCES = (
    ("IDS_PH_SERVICE_PROGRESS_RETRY", 2611, "Retry", "重试(&R)", "strings"),
    ("IDS_PH_SERVICE_PROGRESS_COMPLETED", 2612, "Completed", "已完成", "native_strings"),
    (
        "IDS_PH_SERVICE_PROGRESS_ELEVATION_CONTENT",
        2613,
        "You will need to provide administrator permission. Click Continue to complete this operation.",
        "你需要提供管理员权限。单击“继续”完成此操作。",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_PROGRESS_UNABLE_FORMAT",
        2614,
        "Unable to %s one or more services:",
        "无法%s一个或多个服务：",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_PROGRESS_ATTEMPT_FORMAT",
        2615,
        "Attempting to %s %s...",
        "正在%s%s...",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_PROGRESS_CONFIRM_FORMAT",
        2616,
        "Do you want to %s %s?",
        "确定要%s%s吗？",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_PROGRESS_CONFIRM_CONTENT_FORMAT",
        2617,
        "%s Are you sure you want to continue?",
        "%s 确定要继续吗？",
        "native_strings",
    ),
    ("IDS_PH_SERVICE_PROGRESS_INITIALIZING", 2618, "Initializing...", "正在初始化...", "strings"),
    (
        "IDS_PH_SERVICE_PROGRESS_UNABLE_CREATE_THREAD",
        2619,
        "Unable to create a service worker thread.",
        "无法创建服务工作线程。",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_START_WARNING",
        2620,
        "Starting a service might prevent the system from functioning properly.",
        "启动服务可能导致系统无法正常运行。",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_CONTINUE_WARNING",
        2621,
        "Continuing a service might prevent the system from functioning properly.",
        "继续运行服务可能导致系统无法正常运行。",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_PAUSE_WARNING",
        2622,
        "Pausing a service might prevent the system from functioning properly.",
        "暂停服务可能导致系统无法正常运行。",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_STOP_WARNING",
        2623,
        "Stopping a service might prevent the system from functioning properly.",
        "停止服务可能导致系统无法正常运行。",
        "native_strings",
    ),
    (
        "IDS_PH_SERVICE_RESTART_WARNING",
        2624,
        "Restarting a service might prevent the system from functioning properly.",
        "重启服务可能导致系统无法正常运行。",
        "native_strings",
    ),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("service_progress_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.S)
    if match is None:
        raise AssertionError(f"function not found: {name}")
    opening = source.find("{", match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated function: {name}")


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def parse_stringtable(path: pathlib.Path):
    return dict(
        re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    )


class ServiceProgressDialogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.actions = ACTIONS_PATH.read_text(encoding="utf-8-sig")

    def test_resources_ids_owners_placeholders_counts_and_ci_are_exact(self) -> None:
        header = (REPO_ROOT / "SystemInformer" / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(REPO_ROOT / "SystemInformer" / "SystemInformer.rc")
        chinese = parse_stringtable(REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc")
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        self.assertEqual([row[1] for row in RESOURCES], list(range(2611, 2625)))
        for symbol, resource_id, en, zh, owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(translations[owner].get(en), zh)
                if owner == "native_strings":
                    self.assertNotIn(en, translations["strings"])
                self.assertEqual(re.findall(r"%(?:%|s)", en), re.findall(r"%(?:%|s)", zh))

        self.assertEqual(len(english), 1423)
        self.assertEqual(len(chinese), 1423)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_MENU_TERMINATE_PLAIN$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3423$")
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("sys_info.exe=1423"), 2)
        self.assertNotIn("sys_info.exe=611", workflow)

    def test_context_stores_resource_ids_and_initializes_text_from_native_resources(self) -> None:
        structure = re.search(
            r"typedef struct _PH_UI_SERVICE_PROGRESS_DIALOG\s*\{(?P<body>.*?)\}\s*PH_UI_SERVICE_PROGRESS_DIALOG",
            self.audit.mask_c_comments(self.actions),
            re.S,
        ).group("body")
        self.assertIn("ULONG VerbId;", structure)
        self.assertIn("ULONG MessageId;", structure)
        self.assertNotRegex(structure, r"PCWSTR\s+(?:Verb|Message)\s*;")

        initialize = function_body(self.actions, "PhpShowServiceProgressInitializeText", self.audit)
        self.assertIn("PhGetApplicationUiString(Context->VerbId)", initialize)
        self.assertIn("PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_SERVICE)", initialize)
        self.assertIn("PhGetApplicationUiString(IDS_PH_CONFIRM_SELECTED_SERVICES)", initialize)

    def test_taskdialog_text_and_composed_sentences_use_exact_resources(self) -> None:
        section = self.actions[
            self.actions.index("#pragma region Service Progress Dialog"):
            self.actions.index("#pragma endregion Service Progress Dialog")
            if "#pragma endregion Service Progress Dialog" in self.actions
            else self.actions.index("BOOLEAN PhUiStartServices(")
        ]
        routes = (
            "IDS_PH_SERVICE_PROGRESS_RETRY",
            "IDS_PH_SERVICE_PROGRESS_COMPLETED",
            "IDS_PH_SERVICE_PROGRESS_ELEVATION_CONTENT",
            "IDS_PH_SERVICE_PROGRESS_UNABLE_FORMAT",
            "IDS_PH_SERVICE_PROGRESS_ATTEMPT_FORMAT",
            "IDS_PH_SERVICE_PROGRESS_CONFIRM_FORMAT",
            "IDS_PH_SERVICE_PROGRESS_CONFIRM_CONTENT_FORMAT",
            "IDS_PH_SERVICE_PROGRESS_INITIALIZING",
            "IDS_PH_SERVICE_PROGRESS_UNABLE_CREATE_THREAD",
            "IDS_PH_CLOSE",
            "IDS_PH_SERVICE_CONTINUE",
            "IDS_PH_CANCEL",
        )
        for route in routes:
            self.assertIn(f"PhGetApplicationUiString({route})", section)

        for _symbol, _resource_id, english, _chinese, _owner in RESOURCES:
            self.assertNotIn(f'L"{english}"', section)
        self.assertNotIn('L"Continue"', section)
        self.assertNotIn('L"Cancel"', section)

    def test_all_five_actions_route_ids_in_progress_and_direct_paths(self) -> None:
        cases = (
            ("PhUiStartServices", "IDS_PH_ACTION_START", "IDS_PH_SERVICE_START_WARNING"),
            ("PhUiContinueServices", "IDS_PH_ACTION_CONTINUE", "IDS_PH_SERVICE_CONTINUE_WARNING"),
            ("PhUiPauseServices", "IDS_PH_ACTION_PAUSE", "IDS_PH_SERVICE_PAUSE_WARNING"),
            ("PhUiStopServices", "IDS_PH_ACTION_STOP", "IDS_PH_SERVICE_STOP_WARNING"),
            ("PhUiRestartServices", "IDS_PH_ACTION_RESTART", "IDS_PH_SERVICE_RESTART_WARNING"),
        )
        for function, verb_id, message_id in cases:
            with self.subTest(function=function):
                body = compact(function_body(self.actions, function, self.audit))
                pair = f"WindowHandle,{verb_id},{message_id},FALSE,Services,NumberOfServices"
                self.assertEqual(body.count(compact("PhShowServiceProgressDialog(" + pair)), 1)
                self.assertEqual(body.count(compact("PhpShowContinueMessageServices(" + pair)), 1)

    def test_thread_creation_failures_balance_references_and_report_native_error(self) -> None:
        callback = compact(function_body(self.actions, "PhpUiServiceProgressDialogCallbackProc", self.audit))
        inner = compact(
            """
            PhReferenceObject(context);
            status = PhCreateThread2(PhpUiServicePendingStartCallback, context);
            if (!NT_SUCCESS(status))
            {
                PhDereferenceObject(context);
                PhpShowServiceProgressThreadError(context, status);
            }
            """
        )
        self.assertIn(inner, callback)

        outer = compact(function_body(self.actions, "PhShowServiceProgressDialog", self.audit))
        self.assertIn("status=PhCreateThread2(PhShowServiceProgressDialogThread,context);", outer)
        self.assertIn(
            compact(
                """
                if (!NT_SUCCESS(status))
                {
                    PhShowStatus(WindowHandle, PhGetApplicationUiString(
                        IDS_PH_SERVICE_PROGRESS_UNABLE_CREATE_THREAD), status, 0);
                    PhDereferenceObject(context);
                }
                """
            ),
            outer,
        )

    def test_background_notifications_are_synchronous_context_bound_and_destroy_safe(self) -> None:
        helper = compact(function_body(self.actions, "PhpSendServiceProgressMessage", self.audit))
        self.assertIn("InterlockedCompareExchangePointer(&Context->WindowHandle,NULL,NULL)", helper)
        self.assertIn("PhSendMessageTimeout(windowHandle,WindowMessage,0,(LPARAM)Context,1000,NULL)", helper)

        complete = function_body(self.actions, "PhUiNavigateServiceCompleteDialogPage", self.audit)
        error = function_body(self.actions, "PhUiNavigateServiceErrorDialogPageFromThread", self.audit)
        self.assertIn("PhpSendServiceProgressMessage(Context, WM_PHSVC_EXIT)", complete)
        self.assertIn("PhpSendServiceProgressMessage(Context, WM_PHSVC_ERROR)", error)
        self.assertNotIn("PostMessage", complete + error)

        wndproc = compact(function_body(self.actions, "PhpUiServiceProgressDialogWndProc", self.audit))
        self.assertEqual(wndproc.count("if((PPH_UI_SERVICE_PROGRESS_DIALOG)lParam!=context)"), 2)
        self.assertIn("caseWM_DESTROY:", wndproc)
        self.assertIn("InterlockedExchangePointer(&context->WindowHandle,NULL)", wndproc)
        self.assertIn("PhUnregisterWindowCallback(WindowHandle);", wndproc)
        self.assertIn("PhRemoveWindowContext(WindowHandle,MAXCHAR);", wndproc)
        self.assertGreaterEqual(wndproc.count("returnTRUE;"), 2)

    def test_context_destructor_releases_pending_status_strings(self) -> None:
        body = compact(function_body(self.actions, "PhServiceProgressContextDeleteProcedure", self.audit))
        self.assertIn("message=InterlockedExchangePointer(&context->StatusMessage,NULL);", body)
        self.assertIn("content=InterlockedExchangePointer(&context->StatusContent,NULL);", body)
        self.assertIn("PhClearReference(&message);", body)
        self.assertIn("PhClearReference(&content);", body)

    def test_generated_translation_table_remains_current(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "zhcn" / "generate_translation.py"), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
