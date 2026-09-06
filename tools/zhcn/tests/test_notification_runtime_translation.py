import importlib.util
import pathlib
import re
import tempfile
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "notification_runtime_translation_audit", path
    )
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
                return source[opening_brace + 1:index]

    raise AssertionError(f"unterminated function: {name}")


def statement_block(source: str, pattern: str) -> str:
    match = re.search(pattern, source, re.DOTALL)
    if match is None:
        raise AssertionError(f"statement not found: {pattern}")

    opening_brace = source.find("{", match.end())
    if opening_brace == -1:
        raise AssertionError(f"statement block not found: {pattern}")

    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1:index]

    raise AssertionError(f"unterminated statement block: {pattern}")


class NotificationRuntimeTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def assert_only_raw_route(
        self,
        source: str,
        expected_count: int,
        label: str,
    ) -> None:
        self.assertEqual(
            len(re.findall(r"\bPhShowIconNotificationRaw\s*\(", source)),
            expected_count,
            label,
        )
        self.assertNotRegex(source, r"\bPhShowIconNotification\s*\(")

    def test_public_and_raw_routes_share_retired_raw_contract(self) -> None:
        notifico = (APP_ROOT / "notifico.c").read_text(encoding="utf-8-sig")
        mainwnd = (APP_ROOT / "mainwnd.c").read_text(encoding="utf-8-sig")
        exports = (APP_ROOT / "SystemInformer.def").read_text(encoding="utf-8-sig")
        notifico_header = (APP_ROOT / "include" / "notifico.h").read_text(
            encoding="utf-8-sig"
        )
        mainwnd_header = (APP_ROOT / "include" / "mainwnd.h").read_text(
            encoding="utf-8-sig"
        )

        sink = function_body(notifico, "PhNfpShowBalloonTip", self.audit)
        dispatcher = function_body(
            notifico, "PhNfpShowBalloonTipInternal", self.audit
        )
        public_route = function_body(notifico, "PhNfShowBalloonTip", self.audit)
        raw_route = function_body(notifico, "PhNfShowBalloonTipRaw", self.audit)
        extended_route = function_body(
            notifico, "PhNfShowBalloonTipEx", self.audit
        )
        public_app_route = function_body(
            mainwnd, "PhShowIconNotification", self.audit
        )
        raw_app_route = function_body(
            mainwnd, "PhShowIconNotificationRaw", self.audit
        )

        self.assertNotIn("PhTranslateString(", notifico)
        self.assertNotIn("PH_NF_WORKQUEUE_DATA_BALLOON_RAW", notifico)
        self.assertRegex(
            sink,
            r"wcsncpy_s\(\s*notifyIcon\.szInfoTitle\s*,[^;]*,\s*Title\s*,\s*_TRUNCATE\s*\)",
        )
        self.assertRegex(
            sink,
            r"wcsncpy_s\(\s*notifyIcon\.szInfo\s*,[^;]*,\s*Text\s*,\s*_TRUNCATE\s*\)",
        )
        self.assertNotIn("Translate", dispatcher)
        self.assertRegex(
            public_route,
            r"PhNfpShowBalloonTipInternal\s*\(\s*Title\s*,\s*Text\s*,\s*Timeout\s*\)",
        )
        self.assertNotIn("PhTranslateString", raw_route)
        self.assertRegex(
            raw_route,
            r"PhNfpShowBalloonTipInternal\s*\(\s*Title\s*,\s*Text\s*,\s*Timeout\s*\)",
        )
        self.assertNotIn("PhTranslateString", extended_route)
        self.assertRegex(
            extended_route,
            r"PhpShowToastNotification\s*\(\s*BalloonTitle\s*,\s*BalloonText",
        )
        self.assertRegex(
            public_app_route,
            r"PhNfShowBalloonTip\s*\(\s*Title\s*,\s*Text\s*,\s*10\s*\)",
        )
        self.assertNotIn("PhTranslateString", raw_app_route)
        self.assertRegex(
            raw_app_route,
            r"PhNfShowBalloonTipRaw\s*\(\s*Title\s*,\s*Text\s*,\s*10\s*\)",
        )
        self.assertIn("PhNfShowBalloonTipRaw", notifico_header)
        self.assertIn("PhShowIconNotificationRaw", mainwnd_header)
        self.assertRegex(
            mainwnd_header,
            r"PHAPPAPI\s+VOID\s+NTAPI\s+PhShowIconNotification\s*\(\s*"
            r"_In_\s+PCWSTR\s+Title\s*,\s*_In_\s+PCWSTR\s+Text\s*\)\s*;",
        )
        self.assertGreater(
            mainwnd_header.index("PhShowIconNotificationRaw"),
            mainwnd_header.index("// end_phapppub"),
        )
        self.assertEqual(
            len(re.findall(r"(?m)^\s*PhShowIconNotification\s*$", exports)),
            1,
        )
        self.assertEqual(
            len(re.findall(r"(?m)^\s*PhShowIconNotificationEx\s*$", exports)),
            1,
        )
        self.assertRegex(
            exports,
            r"(?m)^\s*PhShowIconNotification\s*\n\s*PhShowIconNotificationEx\s*$",
        )
        self.assertNotRegex(exports, r"(?m)^\s*PhShowIconNotificationRaw\s*$")
        export_names = [
            line.strip()
            for line in exports.splitlines()
            if line.strip() and not line.lstrip().startswith(";")
        ]
        self.assertEqual(export_names[166:169], [
            "PhShowHandleObjectProperties2",
            "PhShowIconNotification",
            "PhShowIconNotificationEx",
        ])

    def test_work_queue_owns_payload_and_drains_every_node_during_exit(self) -> None:
        notifico = self.audit.mask_c_comments(
            (APP_ROOT / "notifico.c").read_text(encoding="utf-8-sig")
        )
        dispatcher = function_body(
            notifico, "PhNfpShowBalloonTipInternal", self.audit
        )
        flush_route = function_body(
            notifico, "PhNfTrayIconFlushWorkQueueData", self.audit
        )

        title_copy = "data->BalloonTitle = Title ? PhCreateString(Title) : NULL;"
        text_copy = "data->BalloonText = Text ? PhCreateString(Text) : NULL;"
        push = "RtlInterlockedPushEntrySList(&PhpTrayIconWorkQueueListHead, &data->ListEntry);"
        self.assertEqual(dispatcher.count(title_copy), 1)
        self.assertEqual(dispatcher.count(text_copy), 1)
        self.assertEqual(dispatcher.count(push), 1)
        self.assertLess(dispatcher.index(title_copy), dispatcher.index(push))
        self.assertLess(dispatcher.index(text_copy), dispatcher.index(push))
        self.assertNotRegex(dispatcher, r"Balloon(?:Title|Text)\s*=\s*(?:Title|Text)\s*;")

        self.assertNotIn("break;", flush_route)
        active_route = statement_block(
            flush_route,
            r"if\s*\(\s*!PhMainWndExiting\s*\)",
        )
        for expected in (
            "PhNfpAddNotifyIcon(data->Icon);",
            "PhNfpRemoveNotifyIcon(data->Icon);",
            "PhpShowToastNotification(",
            "PhNfpShowBalloonTip(",
        ):
            self.assertIn(expected, active_route)

        for reference in ("BalloonTitle", "BalloonText"):
            cleanup = f"PhClearReference(&data->{reference});"
            self.assertEqual(flush_route.count(cleanup), 1)
            self.assertNotIn(cleanup, active_route)
            self.assertLess(
                flush_route.index("PhNfpShowBalloonTip("),
                flush_route.index(cleanup),
            )

        self.assertEqual(flush_route.count("PhFree(data);"), 1)
        self.assertNotIn("PhFree(data);", active_route)
        self.assertLess(
            flush_route.index("PhClearReference(&data->BalloonText);"),
            flush_route.index("PhFree(data);"),
        )

    def test_process_service_and_device_notifications_use_only_raw_route(self) -> None:
        expected_counts = {
            "mwpgproc.c": 2,
            "mwpgsrv.c": 5,
            "mwpgdev.c": 1,
        }

        for filename, expected_count in expected_counts.items():
            source = self.audit.mask_c_comments(
                (APP_ROOT / filename).read_text(encoding="utf-8-sig")
            )
            self.assert_only_raw_route(source, expected_count, filename)

        updater = self.audit.mask_c_comments(
            (REPO_ROOT / "plugins" / "Updater" / "updater.c").read_text(
                encoding="utf-8-sig"
            )
        )
        self.assertEqual(
            len(re.findall(r"\bPhShowIconNotificationEx\s*\(", updater)),
            1,
        )
        self.assertNotRegex(updater, r"\bPhShowIconNotification(?:Raw)?\s*\(")

    def test_internal_notification_route_contract_rejects_public_mutation(self) -> None:
        source = self.audit.mask_c_comments(
            (APP_ROOT / "mwpgdev.c").read_text(encoding="utf-8-sig")
        )
        mutated = source.replace(
            "PhShowIconNotificationRaw(",
            "PhShowIconNotification(",
            1,
        )

        with self.assertRaises(AssertionError):
            self.assert_only_raw_route(mutated, 1, "mwpgdev.c mutation")

    def test_audit_finds_direct_one_hop_and_composed_notification_text(self) -> None:
        audit = self.audit
        source = r'''
            void sample(BOOLEAN removed, PCWSTR dynamicText, PPH_STRING deviceName)
            {
                PCWSTR fixedTitle = L"One-hop title";
                PPH_STRING title;

                PhShowIconNotification(L"Public title", dynamicText);
                PhShowIconNotification(fixedTitle, dynamicText);
                PhShowIconNotification(dynamicText, dynamicText);
                PhShowIconNotificationEx(
                    L"Extended title",
                    L"Extended body",
                    5000,
                    NULL,
                    NULL
                    );
                PhShowIconNotificationRaw(L"Raw title", dynamicText);

                if (removed)
                    title = PhConcatStrings2(deviceName->Buffer, L" Device Removed");
                else
                    title = PhConcatStrings2(deviceName->Buffer, L" Device Arrived");
                PhShowIconNotificationRaw(PhGetString(title), deviceName->Buffer);
            }
        '''
        entries = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", encoding="utf-8"
        ) as source_file:
            source_file.write(source)
            source_file.flush()
            audit.scan_c_file(source_file.name, entries)

        self.assertEqual(
            Counter(
                entry["english"]
                for entry in entries
                if entry["category"] == "c_balloon"
            ),
            Counter(
                {
                    "Public title": 1,
                    "One-hop title": 1,
                    "Extended title": 1,
                    "Extended body": 1,
                    "Raw title": 1,
                }
            ),
        )
        self.assertEqual(
            Counter(
                entry["english"]
                for entry in entries
                if entry["category"] == "c_runtime_composed"
            ),
            Counter({" Device Removed": 1, " Device Arrived": 1}),
        )

    def test_real_fixed_notification_candidates_are_all_visible(self) -> None:
        audit = self.audit
        entries = []
        paths = (
            APP_ROOT / "mwpgproc.c",
            APP_ROOT / "mwpgsrv.c",
            APP_ROOT / "mwpgdev.c",
            REPO_ROOT / "plugins" / "Updater" / "updater.c",
        )

        for path in paths:
            audit.scan_c_file(str(path), entries)

        fixed_candidates = Counter(
            entry["english"]
            for entry in entries
            if entry["category"] == "c_balloon"
        )
        self.assertEqual(
            fixed_candidates,
            Counter(
                {
                }
            ),
        )
        self.assertEqual(
            Counter(
                entry["english"]
                for entry in entries
                if entry["category"] == "c_runtime_composed"
            ),
            Counter(),
        )

        device_source = self.audit.mask_c_comments(
            (APP_ROOT / "mwpgdev.c").read_text(encoding="utf-8-sig")
        )
        device_body = re.sub(
            r"\s+",
            "",
            function_body(device_source, "PhpNotifyForDevice", self.audit),
        )
        for resource_id in (
            "IDS_PH_DEVICE_REMOVED_TITLE_FORMAT",
            "IDS_PH_DEVICE_ARRIVED_TITLE_FORMAT",
        ):
            self.assertIn(
                f"PhFormatString(PhGetApplicationUiString({resource_id}),PhGetString(classification))",
                device_body,
            )
        self.assertNotIn('L"DeviceRemoved"', device_body)
        self.assertNotIn('L"DeviceArrived"', device_body)


if __name__ == "__main__":
    unittest.main()
