#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "Updater"

RESOURCES = (
    ("IDS_UP_BUTTON_CHECK", 12010, "Check", "检查"),
    ("IDS_UP_CHANNEL_STABLE_RECOMMENDED", 12011, "Stable\\n - Recommended", "稳定版\\n - 推荐"),
    ("IDS_UP_CHANNEL_CANARY_PREVIEW", 12012, "Canary\\n - Preview", "Canary\\n - 预览"),
    ("IDS_UP_BUTTON_DOWNLOAD", 12013, "Download", "下载"),
    (
        "IDS_UP_AVAILABLE_DETAILS_FORMAT",
        12014,
        'Version: %s\\r\\nDownload size: %s\\r\\n\\r\\n<A HREF="changelog.txt">View the changelog</A>',
        '版本：%s\\r\\n下载大小：%s\\r\\n\\r\\n<A HREF="changelog.txt">查看更新日志</A>',
    ),
    ("IDS_UP_BUTTON_INSTALL", 12015, "Install", "安装"),
    ("IDS_UP_DOWNLOADING_CHANNEL_FORMAT", 12016, "Downloading%s channel %s...", "正在下载%s通道 %s..."),
    ("IDS_UP_DOWNLOADING_UPDATE_FORMAT", 12017, "Downloading update %s...", "正在下载更新 %s..."),
)

SOURCE_FILES = ("page1.c", "page3.c", "page4.c", "page5.c")
TARGET_ENGLISH = {row[2].replace("\\r", "\r").replace("\\n", "\n") for row in RESOURCES}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("updater_taskdialog_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_UP_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
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


class UpdaterTaskDialogNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: (PLUGIN_ROOT / name).read_text(encoding="utf-8-sig")
            for name in SOURCE_FILES
        }

    def test_eight_resources_and_module_boundaries_are_exact(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "Updater.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "Updater.zh-cn.rc")

        for symbol, numeric_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{numeric_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        numeric_ids = sorted(
            int(value)
            for value in re.findall(
                r"(?m)^#define\s+IDS_UP_[A-Z0-9_]+\s+(\d+)\s*$",
                header,
            )
        )
        self.assertEqual(numeric_ids, list(range(12000, 12018)))
        self.assertEqual(len(english), 18)
        self.assertEqual(len(chinese), 18)
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12018$")

    def test_button_arrays_are_local_and_hold_loaded_strings_through_navigation(self) -> None:
        page1 = function_body(self.sources["page1.c"], "ShowCheckForUpdatesDialog")
        page3 = function_body(self.sources["page3.c"], "ShowAvailableDialog")
        page5 = function_body(self.sources["page5.c"], "ShowUpdateInstallDialog")

        self.assertNotRegex(
            self.audit.mask_c_comments(self.sources["page1.c"]),
            r"static\s+TASKDIALOG_BUTTON",
        )
        self.assertNotRegex(
            self.audit.mask_c_comments(self.sources["page3.c"]),
            r"static\s+TASKDIALOG_BUTTON",
        )
        self.assertNotRegex(page5, r"\bstatic\s+TASKDIALOG_BUTTON")

        expected = (
            (page1, "checkButtonText", "IDS_UP_BUTTON_CHECK", "updateTaskDialogButtonArray[0]"),
            (page1, "stableChannelText", "IDS_UP_CHANNEL_STABLE_RECOMMENDED", "checkForUpdatesRadioButtons[0]"),
            (page1, "canaryChannelText", "IDS_UP_CHANNEL_CANARY_PREVIEW", "checkForUpdatesRadioButtons[1]"),
            (page3, "downloadButtonText", "IDS_UP_BUTTON_DOWNLOAD", "taskDialogButtonArray[0]"),
            (page5, "installButtonText", "IDS_UP_BUTTON_INSTALL", "taskDialogButtonArray[0]"),
        )
        for body, variable, resource, button in expected:
            with self.subTest(resource=resource):
                self.assertRegex(
                    body,
                    rf"{variable}\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
                    rf"PluginInstance->DllBase,\s*{resource},\s*NULL\s*\)\)",
                )
                self.assertIn(
                    f"{button}.pszButtonText = PhGetStringOrEmpty({variable});",
                    body,
                )
                self.assertLess(body.index(resource), body.index("PhTaskDialogNavigatePage("))

        for body in (page1, page3, page5):
            self.assertIn("PhGetStringOrEmpty(", body)
            self.assertEqual(body.count("PhTaskDialogNavigatePage("), 1)

    def test_complete_format_resources_preserve_placeholders_and_html_route(self) -> None:
        page3 = function_body(self.sources["page3.c"], "ShowAvailableDialog")
        page4 = function_body(self.sources["page4.c"], "ShowProgressDialog")

        self.assertRegex(
            page3,
            r"PhaFormatString\(\s*PhGetStringOrEmpty\(availableDetailsFormat\),\s*"
            r"PhGetStringOrEmpty\(Context->Version\),\s*"
            r"PhGetStringOrEmpty\(Context->SetupFileLength\)",
        )
        self.assertRegex(
            page3,
            r"availableDetailsFormat\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
            r"PluginInstance->DllBase,\s*IDS_UP_AVAILABLE_DETAILS_FORMAT,\s*NULL\s*\)\)",
        )

        for variable, resource, arguments in (
            (
                "downloadingChannelFormat",
                "IDS_UP_DOWNLOADING_CHANNEL_FORMAT",
                r"channelName,\s*PhGetStringOrEmpty\(Context->Version\)",
            ),
            (
                "downloadingUpdateFormat",
                "IDS_UP_DOWNLOADING_UPDATE_FORMAT",
                r"PhGetStringOrEmpty\(Context->Version\)",
            ),
        ):
            with self.subTest(resource=resource):
                self.assertRegex(
                    page4,
                    rf"{variable}\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
                    rf"PluginInstance->DllBase,\s*{resource},\s*NULL\s*\)\)",
                )
                self.assertRegex(
                    page4,
                    rf"PhaFormatString\(PhGetStringOrEmpty\({variable}\),\s*"
                    rf"{arguments}\)->Buffer",
                )

    def test_target_literals_leave_fresh_updater_c_audit(self) -> None:
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)

        remaining_categories = [
            entry
            for entry in entries
            if entry["category"] in {"c_taskdialog_raw", "c_runtime_composed"}
        ]
        self.assertEqual(remaining_categories, [])

        remaining = {
            entry["english"]
            for entry in entries
            if entry["english"] in TARGET_ENGLISH
        }
        self.assertEqual(remaining, set())

        masked = "\n".join(
            self.audit.mask_c_comments(source)
            for source in self.sources.values()
        )
        for english in TARGET_ENGLISH:
            with self.subTest(raw_literal=english):
                escaped = english.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
                self.assertNotIn(f'L"{escaped}"', masked)


if __name__ == "__main__":
    unittest.main()
