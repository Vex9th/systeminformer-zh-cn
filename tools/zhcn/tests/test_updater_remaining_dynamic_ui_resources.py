import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "Updater"
HEADER_PATH = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "Updater.rc"
CHINESE_RC = PLUGIN_ROOT / "Updater.zh-cn.rc"
TARGET_CATEGORIES = {"c_emenu", "c_listview_col", "c_msgbox", "c_taskdialog"}

RESOURCES = (
    (12018, "IDS_UP_COLUMN_DATE", "Date", "日期", "options.c", 1),
    (12019, "IDS_UP_COLUMN_AUTHOR", "Author", "作者", "options.c", 1),
    (12020, "IDS_UP_COLUMN_COMMENTS", "Comments", "注释", "options.c", 1),
    (12021, "IDS_UP_COLUMN_COMMIT", "Commit", "提交", "options.c", 1),
    (12022, "IDS_UP_MENU_VIEW_ON_GITHUB", "View on Github", "在 Github 上查看", "options.c", 1),
    (12023, "IDS_UP_MENU_COPY", "&Copy", "复制(&C)", "options.c", 1),
    (12024, "IDS_UP_UNABLE_CREATE_WINDOW", "Unable to create the window.", "无法创建窗口。", "updater.c", 1),
    (12025, "IDS_UP_DIALOG_TITLE", "System Informer - Updater", "sys_info - 更新程序", None, 8),
    (12026, "IDS_UP_CHECK_RELEASE_PROMPT", "Check for an updated System Informer release?", "检查 sys_info 的新版本？", "page1.c", 1),
    (12027, "IDS_UP_CLICK_CHECK_CONTINUE", "Click Check to continue.", "单击“检查”以继续。", "page1.c", 1),
    (12028, "IDS_UP_CHECKING_RELEASE_CHANNEL", "Checking the release channel...", "正在检查 Release 通道...", "page2.c", 1),
    (12029, "IDS_UP_CHECKING_CANARY_CHANNEL", "Checking the canary channel...", "正在检查 Canary 通道...", "page2.c", 1),
    (12030, "IDS_UP_CHECKING_CHANNEL", "Checking the channel...", "正在检查通道...", "page2.c", 1),
    (12031, "IDS_UP_CHECKING_UPDATED_RELEASE", "Checking for an updated release...", "正在检查更新版本...", "page2.c", 1),
    (12032, "IDS_UP_DOWNLOAD_RELEASE_PROMPT", "Would you like to download the Release build?", "要下载 Release 版本吗？", "page3.c", 1),
    (12033, "IDS_UP_DOWNLOAD_CANARY_PROMPT", "Would you like to download the Canary build?", "要下载 Canary 版本吗？", "page3.c", 1),
    (12034, "IDS_UP_DOWNLOAD_UPDATE_PROMPT", "Would you like to download the update?", "要下载更新吗？", "page3.c", 1),
    (12035, "IDS_UP_NEWER_BUILD_AVAILABLE", "A newer build of System Informer is available.", "有较新的 sys_info 版本可用。", "page3.c", 1),
    (12036, "IDS_UP_DOWNLOAD_PROGRESS_INITIAL", "Downloaded: ~ of ~ (0%)\r\nSpeed: ~ KB/s", "已下载：~ / ~ (0%)\r\n速度：~ KB/s", None, 3),
    (12037, "IDS_UP_SWITCH_RELEASE_READY", "Ready to switch to the release channel?", "现在切换到 Release 通道吗？", "page5.c", 1),
    (12038, "IDS_UP_SWITCH_CANARY_READY", "Ready to switch to the canary channel?", "现在切换到 Canary 通道吗？", "page5.c", 1),
    (12039, "IDS_UP_SWITCH_CHANNEL_READY", "Ready to switch the channel?", "现在切换通道吗？", "page5.c", 1),
    (12040, "IDS_UP_UPDATE_INSTALLED", "Update installed.", "更新已安装。", "page5.c", 1),
    (12041, "IDS_UP_INSTALL_UPDATE_READY", "Ready to install update?", "现在安装更新吗？", "page5.c", 1),
    (12042, "IDS_UP_CHANNEL_VERIFIED_INSTALL", "The channel has been successfully downloaded and verified.\r\n\r\nClick Install to continue.", "通道已成功下载并通过验证。\r\n\r\n单击“安装”以继续。", "page5.c", 1),
    (12043, "IDS_UP_UPDATE_INSTALLED_RESTART", "The update has been downloaded and installed.\r\n\r\nRestart System Informer to apply the update.", "更新已下载并安装。\r\n\r\n请重启 sys_info 以应用更新。", "page5.c", 1),
    (12044, "IDS_UP_UPDATE_VERIFIED_INSTALL", "The update has been successfully downloaded and verified.\r\n\r\nClick Install to continue.", "更新已成功下载并通过验证。\r\n\r\n单击“安装”以继续。", "page5.c", 1),
    (12045, "IDS_UP_LATEST_VERSION", "You're running the latest version.", "你正在运行最新版本。", "page5.c", 1),
    (12046, "IDS_UP_PRE_RELEASE_BUILD", "You're running a pre-release build.", "你正在运行预发布版本。", "page5.c", 1),
    (12047, "IDS_UP_ERROR_DOWNLOADING_CHANNEL", "Error downloading the channel.", "下载通道时出错。", "page5.c", 1),
    (12048, "IDS_UP_ERROR_DOWNLOADING_UPDATE", "Error downloading the update.", "下载更新时出错。", "page5.c", 1),
    (12049, "IDS_UP_SIGNATURE_FAILED_CHANNEL", "Signature check failed. Click Retry to download the channel again.", "签名校验失败。单击“重试”重新下载通道。", "page5.c", 1),
    (12050, "IDS_UP_SIGNATURE_FAILED_UPDATE", "Signature check failed. Click Retry to download the update again.", "签名校验失败。单击“重试”重新下载更新。", "page5.c", 1),
    (12051, "IDS_UP_HASH_FAILED_CHANNEL", "Hash check failed. Click Retry to download the channel again.", "哈希校验失败。单击“重试”重新下载通道。", "page5.c", 1),
    (12052, "IDS_UP_HASH_FAILED_UPDATE", "Hash check failed. Click Retry to download the update again.", "哈希校验失败。单击“重试”重新下载更新。", "page5.c", 1),
    (12053, "IDS_UP_RETRY_DOWNLOAD_CHANNEL", "Click Retry to download the channel again.", "单击“重试”重新下载通道。", "page5.c", 1),
    (12054, "IDS_UP_RETRY_DOWNLOAD_UPDATE", "Click Retry to download the update again.", "单击“重试”重新下载更新。", "page5.c", 1),
    (12055, "IDS_UP_INITIALIZING", "Initializing...", "正在初始化...", "updater.c", 2),
)


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "audit_updater_remaining_dynamic_ui_resources", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_header() -> dict[str, int]:
    return {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(IDS_UP_[A-Z0-9_]+)\s+(\d+)\b",
            HEADER_PATH.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    }


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8-sig")
    return {
        name: value.replace('""', '"').replace("\\r", "\r").replace("\\n", "\n")
        for name, value in re.findall(
            r'^\s*(IDS_UP_[A-Z0-9_]+)\s+"((?:""|[^"])*)"',
            source,
            re.MULTILINE,
        )
    }


def c_literal(text: str) -> str:
    return 'L"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'


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


class UpdaterRemainingDynamicUiResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in PLUGIN_ROOT.glob("*.c")
        }

    def test_new_resources_are_contiguous_bilingual_and_complete(self) -> None:
        header = parse_header()
        english = parse_stringtable(ENGLISH_RC)
        chinese = parse_stringtable(CHINESE_RC)

        self.assertEqual(len(header), 56)
        self.assertEqual(len(english), 56)
        self.assertEqual(len(chinese), 56)
        self.assertRegex(
            HEADER_PATH.read_text(encoding="utf-8"),
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12056$",
        )

        for resource_id, symbol, en_text, zh_text, _, _ in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(header[symbol], resource_id)
                self.assertEqual(english[symbol], en_text)
                self.assertEqual(chinese[symbol], zh_text)

        self.assertEqual(english["IDS_UP_MENU_COPY"].count("&"), 1)
        self.assertEqual(chinese["IDS_UP_MENU_COPY"].count("&"), 1)

    def test_every_resource_load_count_and_raw_literal_removal_is_exact(self) -> None:
        audit = load_audit_module()
        combined = "\n".join(self.sources.values())
        masked_combined = audit.mask_c_comments(combined)
        masked_sources = {
            filename: audit.mask_c_comments(source)
            for filename, source in self.sources.items()
        }

        for _, symbol, english, _, filename, expected_count in RESOURCES:
            with self.subTest(symbol=symbol):
                target = combined if filename is None else self.sources[filename]
                self.assertEqual(
                    len(
                        re.findall(
                            rf"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*"
                            rf"{re.escape(symbol)}\s*,\s*NULL\s*\)",
                            target,
                        )
                    ),
                    expected_count,
                )
                masked_target = (
                    masked_combined
                    if filename is None
                    else masked_sources[filename]
                )
                self.assertNotIn(c_literal(english), masked_target)

    def test_menu_commands_and_columns_keep_exact_routes(self) -> None:
        options = compact(self.sources["options.c"])

        for command_id, symbol in (
            (1, "IDS_UP_MENU_VIEW_ON_GITHUB"),
            (2, "IDS_UP_MENU_COPY"),
        ):
            self.assertIn(
                compact(
                    f"PhCreateEMenuItem(0,{command_id},"
                    "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString("
                    f"PluginInstance->DllBase,{symbol},NULL))),NULL,NULL)"
                ),
                options,
            )

        for indices, width, symbol in (
            ("0,0,0", 120, "IDS_UP_COLUMN_DATE"),
            ("1,1,1", 100, "IDS_UP_COLUMN_AUTHOR"),
            ("2,2,2", 250, "IDS_UP_COLUMN_COMMENTS"),
            ("3,3,3", 100, "IDS_UP_COLUMN_COMMIT"),
        ):
            self.assertIn(
                compact(
                    "PhAddListViewColumn(context->ListViewHandle,"
                    f"{indices},LVCFMT_LEFT,{width},"
                    "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString("
                    f"PluginInstance->DllBase,{symbol},NULL))))"
                ),
                options,
            )

    def test_navigation_pages_hold_loaded_strings_until_the_sink(self) -> None:
        function_resources = {
            "ShowCheckForUpdatesDialog": ("page1.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_CHECK_RELEASE_PROMPT", "IDS_UP_CLICK_CHECK_CONTINUE"),
            "ShowCheckingForUpdatesDialog": ("page2.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_CHECKING_RELEASE_CHANNEL", "IDS_UP_CHECKING_CANARY_CHANNEL", "IDS_UP_CHECKING_CHANNEL", "IDS_UP_CHECKING_UPDATED_RELEASE"),
            "ShowAvailableDialog": ("page3.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_DOWNLOAD_RELEASE_PROMPT", "IDS_UP_DOWNLOAD_CANARY_PROMPT", "IDS_UP_DOWNLOAD_UPDATE_PROMPT", "IDS_UP_NEWER_BUILD_AVAILABLE"),
            "ShowProgressDialog": ("page4.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_DOWNLOAD_PROGRESS_INITIAL"),
            "ShowUpdateInstallDialog": ("page5.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_SWITCH_RELEASE_READY", "IDS_UP_SWITCH_CANARY_READY", "IDS_UP_SWITCH_CHANNEL_READY", "IDS_UP_UPDATE_INSTALLED", "IDS_UP_INSTALL_UPDATE_READY", "IDS_UP_CHANNEL_VERIFIED_INSTALL", "IDS_UP_UPDATE_INSTALLED_RESTART", "IDS_UP_UPDATE_VERIFIED_INSTALL"),
            "ShowLatestVersionDialog": ("page5.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_LATEST_VERSION"),
            "ShowNewerVersionDialog": ("page5.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_PRE_RELEASE_BUILD"),
            "ShowUpdateFailedDialog": ("page5.c", "IDS_UP_DIALOG_TITLE", "IDS_UP_ERROR_DOWNLOADING_CHANNEL", "IDS_UP_ERROR_DOWNLOADING_UPDATE", "IDS_UP_SIGNATURE_FAILED_CHANNEL", "IDS_UP_SIGNATURE_FAILED_UPDATE", "IDS_UP_HASH_FAILED_CHANNEL", "IDS_UP_HASH_FAILED_UPDATE", "IDS_UP_RETRY_DOWNLOAD_CHANNEL", "IDS_UP_RETRY_DOWNLOAD_UPDATE"),
        }

        for function_name, (filename, *symbols) in function_resources.items():
            body = function_body(self.sources[filename], function_name)
            sink = body.index("PhTaskDialogNavigatePage(")
            for symbol in symbols:
                with self.subTest(function=function_name, symbol=symbol):
                    self.assertIn(symbol, body)
                    self.assertLess(body.index(symbol), sink)
            self.assertIn("PhGetStringOrEmpty(", body)

    def test_blocking_dialog_strings_outlive_the_synchronous_calls(self) -> None:
        updater = self.sources["updater.c"]
        for function_name in ("ShowUpdateDialogThread", "ShowStartupUpdateDialog"):
            body = function_body(updater, function_name)
            self.assertIn("IDS_UP_INITIALIZING", body)
            self.assertLess(body.index("IDS_UP_INITIALIZING"), body.index("PhShowTaskDialog("))
            self.assertIn("config.pszContent = PhGetStringOrEmpty(initializingText);", body)

        show_dialog = function_body(updater, "ShowUpdateDialog")
        self.assertIn("IDS_UP_UNABLE_CREATE_WINDOW", show_dialog)
        self.assertLess(
            show_dialog.index("IDS_UP_UNABLE_CREATE_WINDOW"),
            show_dialog.index("PhShowError2("),
        )
        self.assertLess(
            show_dialog.index("PhShowError2("),
            show_dialog.index("PhClearReference(&errorText)"),
        )

        for filename, function_name in (
            ("updater.c", "UpdateDownloadThread"),
            ("toastnotify.c", "UpdateSetDialogInitialProgressText"),
        ):
            body = function_body(self.sources[filename], function_name)
            self.assertLess(
                body.index("IDS_UP_DOWNLOAD_PROGRESS_INITIAL"),
                body.index("TDE_CONTENT"),
            )
            self.assertLess(
                body.index("TDE_CONTENT"),
                body.index("PhClearReference(&progressText)"),
            )

    def test_directed_scan_has_no_remaining_target_categories(self) -> None:
        audit = load_audit_module()
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            audit.scan_c_file(path, entries)

        self.assertEqual(
            [
                (entry["category"], entry["file"], entry["line"], entry["english"])
                for entry in entries
                if entry["category"] in TARGET_CATEGORIES
                and entry["file"].startswith("plugins/Updater/")
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()
