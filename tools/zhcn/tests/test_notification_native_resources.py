#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"
UPDATER_ROOT = REPO_ROOT / "plugins" / "Updater"


SYSTEM_RESOURCES = (
    ("IDS_PH_NOTIFY_PROCESS_CREATED_TITLE", 2527, "Process Created", "进程已创建"),
    ("IDS_PH_NOTIFY_PROCESS_TERMINATED_TITLE", 2528, "Process Terminated", "进程已终止"),
    ("IDS_PH_NOTIFY_SERVICE_CREATED_TITLE", 2529, "Service Created", "服务已创建"),
    ("IDS_PH_NOTIFY_SERVICE_STARTED_TITLE", 2530, "Service Started", "服务已启动"),
    ("IDS_PH_NOTIFY_SERVICE_STOPPED_TITLE", 2531, "Service Stopped", "服务已停止"),
    ("IDS_PH_NOTIFY_SERVICE_MODIFIED_TITLE", 2532, "Service Modified", "服务已修改"),
    ("IDS_PH_NOTIFY_SERVICE_DELETED_TITLE", 2533, "Service Deleted", "服务已删除"),
    (
        "IDS_PH_NOTIFY_PROCESS_CREATED_FORMAT",
        2534,
        "The process %s (%lu) was created by %s (%lu)",
        "进程 %s（%lu）由 %s（%lu）创建",
    ),
    (
        "IDS_PH_NOTIFY_PROCESS_TERMINATED_FORMAT",
        2535,
        "The process %s (%lu) was terminated with status 0x%x",
        "进程 %s（%lu）已终止，状态为 0x%x",
    ),
    (
        "IDS_PH_NOTIFY_SERVICE_CREATED_FORMAT",
        2536,
        "The service %s (%s) was created",
        "服务 %s（%s）已创建",
    ),
    (
        "IDS_PH_NOTIFY_SERVICE_STARTED_FORMAT",
        2537,
        "The service %s (%s) was started",
        "服务 %s（%s）已启动",
    ),
    (
        "IDS_PH_NOTIFY_SERVICE_STOPPED_FORMAT",
        2538,
        "The service %s (%s) was stopped",
        "服务 %s（%s）已停止",
    ),
    (
        "IDS_PH_NOTIFY_SERVICE_MODIFIED_FORMAT",
        2539,
        "The service %s (%s) was modified",
        "服务 %s（%s）已修改",
    ),
    (
        "IDS_PH_NOTIFY_SERVICE_DELETED_FORMAT",
        2540,
        "The service %s (%s) was deleted",
        "服务 %s（%s）已删除",
    ),
    ("IDS_PH_NOTIFY_UNKNOWN_PROCESS", 2541, "Unknown process", "未知进程"),
)

UPDATER_RESOURCES = (
    (
        "IDS_UP_NEW_VERSION_AVAILABLE",
        12007,
        "New version of System Informer available",
        "System Informer 有新版本可用",
    ),
    (
        "IDS_UP_CHECK_FOR_UPDATES",
        12008,
        "Help menu > Check for updates",
        "帮助菜单 > 检查更新",
    ),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("notification_native_audit", path)
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


def parse_stringtable(path: pathlib.Path, prefix: str):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            rf'(?m)^\s*({prefix}[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


class NotificationNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.notifico = (APP_ROOT / "notifico.c").read_text(encoding="utf-8-sig")
        cls.processes = (APP_ROOT / "mwpgproc.c").read_text(encoding="utf-8-sig")
        cls.services = (APP_ROOT / "mwpgsrv.c").read_text(encoding="utf-8-sig")
        cls.updater = (UPDATER_ROOT / "updater.c").read_text(encoding="utf-8-sig")

    def test_resource_ids_text_layers_and_counts_are_exact(self) -> None:
        system_header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        updater_header = (UPDATER_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        system_en = parse_stringtable(APP_ROOT / "SystemInformer.rc", "IDS_PH_")
        system_zh = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc", "IDS_PH_")
        updater_en = parse_stringtable(UPDATER_ROOT / "Updater.rc", "IDS_UP_")
        updater_zh = parse_stringtable(UPDATER_ROOT / "Updater.zh-cn.rc", "IDS_UP_")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        self.assertEqual([row[1] for row in SYSTEM_RESOURCES], list(range(2527, 2542)))
        self.assertEqual([row[1] for row in UPDATER_RESOURCES], list(range(12007, 12009)))

        for header, english, chinese, rows in (
            (system_header, system_en, system_zh, SYSTEM_RESOURCES),
            (updater_header, updater_en, updater_zh, UPDATER_RESOURCES),
        ):
            for symbol, resource_id, en, zh in rows:
                with self.subTest(symbol=symbol):
                    self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                    self.assertEqual(english.get(symbol), en)
                    self.assertEqual(chinese.get(symbol), zh)
                    self.assertEqual(translations["native_strings"].get(en), zh)
                    self.assertNotIn(en, translations["strings"])

        self.assertFalse(translations["strings"].keys() & translations["native_strings"].keys())
        self.assertEqual(len(system_en), 1126)
        self.assertEqual(len(system_zh), 1126)
        self.assertEqual(len(updater_en), 56)
        self.assertEqual(len(updater_zh), 56)
        self.assertRegex(system_header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_LISTVIEW_POLICY$")
        self.assertRegex(system_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3126$")
        self.assertRegex(updater_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12056$")

        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("sys_info.exe=1126"), 2)
        self.assertNotIn(r"plugins\Updater.dll=", workflow)

    def test_process_notifications_format_resources_in_exact_argument_order(self) -> None:
        created = function_body(self.processes, "PhMwpOnProcessAdded", self.audit)
        terminated = function_body(self.processes, "PhMwpOnProcessRemoved", self.audit)

        self.assertRegex(
            created,
            r"(?s)notificationText\s*=\s*PhFormatString\(\s*"
            r"PhGetApplicationUiString\(IDS_PH_NOTIFY_PROCESS_CREATED_FORMAT\)\s*,\s*"
            r"PhGetString\(ProcessItem->ProcessName\)\s*,\s*"
            r"HandleToUlong\(ProcessItem->ProcessId\)\s*,\s*"
            r"PhGetStringOrDefault\(parentName\s*,\s*PhGetApplicationUiString\(IDS_PH_NOTIFY_UNKNOWN_PROCESS\)\)\s*,\s*"
            r"HandleToUlong\(ProcessItem->ParentProcessId\)\s*\)\s*;.*?"
            r"PhShowIconNotificationRaw\(\s*PhGetApplicationUiString\(IDS_PH_NOTIFY_PROCESS_CREATED_TITLE\)\s*,\s*"
            r"PhGetString\(notificationText\)\s*\)\s*;.*?PhDereferenceObject\(notificationText\)",
        )
        self.assertRegex(
            terminated,
            r"(?s)notificationText\s*=\s*PhFormatString\(\s*"
            r"PhGetApplicationUiString\(IDS_PH_NOTIFY_PROCESS_TERMINATED_FORMAT\)\s*,\s*"
            r"PhGetString\(ProcessItem->ProcessName\)\s*,\s*"
            r"HandleToUlong\(ProcessItem->ProcessId\)\s*,\s*exitStatus\s*\)\s*;.*?"
            r"PhShowIconNotificationRaw\(\s*PhGetApplicationUiString\(IDS_PH_NOTIFY_PROCESS_TERMINATED_TITLE\)\s*,\s*"
            r"PhGetString\(notificationText\)\s*\)\s*;.*?PhDereferenceObject\(notificationText\)",
        )

    def test_service_notifications_use_exact_resource_pairs_and_arguments(self) -> None:
        source = self.audit.mask_c_comments(self.services)
        expected_routes = (
            ("IDS_PH_NOTIFY_SERVICE_CREATED_TITLE", "IDS_PH_NOTIFY_SERVICE_CREATED_FORMAT", "ServiceItem"),
            ("IDS_PH_NOTIFY_SERVICE_STARTED_TITLE", "IDS_PH_NOTIFY_SERVICE_STARTED_FORMAT", "serviceItem"),
            ("IDS_PH_NOTIFY_SERVICE_STOPPED_TITLE", "IDS_PH_NOTIFY_SERVICE_STOPPED_FORMAT", "serviceItem"),
            ("IDS_PH_NOTIFY_SERVICE_MODIFIED_TITLE", "IDS_PH_NOTIFY_SERVICE_MODIFIED_FORMAT", "serviceItem"),
            ("IDS_PH_NOTIFY_SERVICE_DELETED_TITLE", "IDS_PH_NOTIFY_SERVICE_DELETED_FORMAT", "ServiceItem"),
        )

        for title_id, format_id, item_name in expected_routes:
            with self.subTest(title_id=title_id):
                route = (
                    r"(?s)notificationText\s*=\s*PhFormatString\(\s*"
                    rf"PhGetApplicationUiString\({format_id}\)\s*,\s*"
                    rf"PhGetString\({item_name}->Name\)\s*,\s*"
                    rf"PhGetString\({item_name}->DisplayName\)\s*\)\s*;.*?"
                    r"PhShowIconNotificationRaw\(\s*"
                    rf"PhGetApplicationUiString\({title_id}\)\s*,\s*"
                    r"PhGetString\(notificationText\)\s*\)\s*;.*?"
                    r"PhDereferenceObject\(notificationText\)"
                )
                self.assertEqual(len(re.findall(route, source)), 1)

        self.assertEqual(source.count("notificationText = PhFormatString("), 5)
        self.assertEqual(source.count("PhShowIconNotificationRaw("), 5)
        self.assertEqual(source.count("PhDereferenceObject(notificationText);"), 5)
        self.assertNotIn("PH_FORMAT format[5]", source)
        self.assertNotIn("WCHAR formatBuffer[260]", source)

        for old_fragment in (
            'L"The service "',
            'L") was created"',
            'L") was started"',
            'L") was stopped"',
            'L") was modified"',
            'L") was deleted"',
        ):
            self.assertNotIn(old_fragment, source)

    def test_updater_helper_loads_owns_and_releases_plugin_resources(self) -> None:
        helper = function_body(self.updater, "UpdaterShowAvailableNotification", self.audit)
        self.assertEqual(len(re.findall(
            r"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*IDS_UP_NEW_VERSION_AVAILABLE\s*,\s*NULL\s*\)",
            helper,
        )), 1)
        self.assertEqual(len(re.findall(
            r"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*IDS_UP_CHECK_FOR_UPDATES\s*,\s*NULL\s*\)",
            helper,
        )), 1)
        call = helper.index("PhShowIconNotificationEx(")
        self.assertLess(helper.index("title = PhLoadUiString("), call)
        self.assertLess(helper.index("text = PhLoadUiString("), call)
        self.assertGreater(helper.index("PhClearReference(&title);"), call)
        self.assertGreater(helper.index("PhClearReference(&text);"), call)
        for function in ("UpdateCheckSilentThread", "ShowStartupUpdateDialog"):
            body = function_body(self.updater, function, self.audit)
            self.assertEqual(
                len(re.findall(r"\bUpdaterShowAvailableNotification\s*\(\s*\)", body)),
                1,
            )

    def test_balloon_extended_route_releases_both_temporary_strings(self) -> None:
        body = function_body(self.notifico, "PhNfShowBalloonTipEx", self.audit)
        for expected in (
            "BalloonTitle = PhCreateString(Title);",
            "BalloonText = PhCreateString(Text);",
            "PhClearReference(&BalloonTitle);",
            "PhClearReference(&BalloonText);",
        ):
            self.assertIn(expected, body)
        call = body.index("PhpShowToastNotification(")
        self.assertLess(body.index("BalloonTitle = PhCreateString(Title);"), call)
        self.assertLess(body.index("BalloonText = PhCreateString(Text);"), call)
        self.assertGreater(body.index("PhClearReference(&BalloonTitle);"), call)
        self.assertGreater(body.index("PhClearReference(&BalloonText);"), call)
        self.assertRegex(body, r"result\s*=\s*PhpShowToastNotification\(")
        self.assertRegex(body, r"return\s+result\s*;")

    def test_toast_xml_escapes_copies_and_cleans_every_owned_string(self) -> None:
        body = function_body(self.notifico, "PhpShowToastNotification", self.audit)
        for expected in (
            "escapedIconFileName = PhEscapeStringForXml(PhGetString(iconFileName));",
            "escapedTitle = PhEscapeStringForXml(PhGetString(Title));",
            "escapedText = PhEscapeStringForXml(PhGetString(Text));",
            "CleanupExit:",
        ):
            self.assertIn(expected, body)
        initialize = body.index("result = PhInitializeToastRuntime();")
        escape_icon = body.index("escapedIconFileName = PhEscapeStringForXml(PhGetString(iconFileName));")
        escape_title = body.index("escapedTitle = PhEscapeStringForXml(PhGetString(Title));")
        escape_text = body.index("escapedText = PhEscapeStringForXml(PhGetString(Text));")
        publish = body.index("result = PhShowToastStringRef(")
        cleanup = body.index("CleanupExit:")

        self.assertLess(initialize, escape_icon)
        self.assertLess(escape_icon, escape_title)
        self.assertLess(escape_title, publish)
        self.assertLess(escape_text, publish)
        self.assertLess(publish, cleanup)
        self.assertRegex(
            body,
            r"if\s*\(HR_FAILED\(result\)\)\s*goto\s+CleanupExit\s*;",
        )
        self.assertIn("PhInitFormatSR(&format[1], escapedIconFileName->sr);", body)
        self.assertIn("PhInitFormatSR(&format[3], escapedTitle->sr);", body)
        self.assertIn("PhInitFormatSR(&format[5], escapedText->sr);", body)
        self.assertNotIn("PhInitFormatSR(&format[1], iconFileName->sr);", body)
        self.assertNotIn("PhInitFormatSR(&format[3], Title->sr);", body)
        self.assertNotIn("PhInitFormatSR(&format[5], Text->sr);", body)
        self.assertRegex(body, r"PPH_STRING\s+escapedIconFileName\s*=\s*NULL\s*;")
        self.assertRegex(body, r"PPH_STRING\s+escapedTitle\s*=\s*NULL\s*;")
        self.assertRegex(body, r"PPH_STRING\s+escapedText\s*=\s*NULL\s*;")
        self.assertRegex(body, r"PPH_STRING\s+toastXml\s*=\s*NULL\s*;")
        owned_scope = body[body.index("PhAppResolverGetAppIdForProcess("):cleanup]
        self.assertNotRegex(owned_scope, r"\breturn\b")
        for variable in ("toastXml", "escapedIconFileName", "escapedTitle", "escapedText", "processAppId"):
            self.assertEqual(body.count(f"PhClearReference(&{variable});"), 1, variable)
            self.assertGreater(body.index(f"PhClearReference(&{variable});"), cleanup)
        self.assertEqual(len(re.findall(r"\breturn\s+result\s*;", body)), 1)

    def test_fresh_scan_no_longer_reports_migrated_notification_literals(self) -> None:
        entries = []
        for path in (
            APP_ROOT / "mwpgproc.c",
            APP_ROOT / "mwpgsrv.c",
            UPDATER_ROOT / "updater.c",
        ):
            self.audit.scan_c_file(str(path), entries)

        migrated = {row[2] for row in SYSTEM_RESOURCES + UPDATER_RESOURCES}
        remaining = [
            (entry["category"], entry["english"], entry["file"], entry["line"])
            for entry in entries
            if entry["english"] in migrated
        ]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
