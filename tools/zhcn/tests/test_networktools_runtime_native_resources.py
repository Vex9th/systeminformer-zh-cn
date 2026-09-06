#!/usr/bin/env python3
"""Regression coverage for NetworkTools runtime UI native resources."""

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "NetworkTools"
TARGET_CATEGORIES = {"c_emenu", "c_msgbox", "c_taskdialog", "c_treenew_col"}


RESOURCE_DATA = (
    ("IDS_NT_GEOLITE_UPDATER_TITLE", 12027, "Network Tools - GeoLite Updater", "网络工具 - GeoLite 更新程序"),
    ("IDS_NT_GEOLITE_DOWNLOAD_QUESTION", 12028, "Download the latest GeoLite database?", "下载最新的 GeoLite 数据库？"),
    (
        "IDS_NT_GEOLITE_DOWNLOAD_SOURCE_CONTENT",
        12029,
        "This product includes GeoLite2 data created by MaxMind, available from <a href=\"https://www.maxmind.com\">https://www.maxmind.com</a>\r\n\r\nSelect download to continue.",
        "本产品包含由 MaxMind 创建的 GeoLite2 数据，可从 <a href=\"https://www.maxmind.com\">https://www.maxmind.com</a> 获取\r\n\r\n单击“下载”以继续。",
    ),
    ("IDS_NT_GEOLITE_DOWNLOADING", 12030, "Downloading", "正在下载"),
    ("IDS_NT_GEOLITE_DOWNLOAD_PROGRESS", 12031, "Downloaded: ~ of ~ (~%%)\r\nSpeed: ~/s", "已下载：~ / ~ (~%%)\r\n速度：~/s"),
    ("IDS_NT_GEOLITE_UPDATED", 12032, "The GeoLite database has been updated.", "GeoLite 数据库已更新。"),
    ("IDS_NT_GEOLITE_RESTART_REQUIRED", 12033, "Please restart System Informer for the changes to take effect...", "请重启 sys_info 以使更改生效..."),
    ("IDS_NT_GEOLITE_DOWNLOAD_ERROR", 12034, "Error downloading GeoLite database.", "下载 GeoLite 数据库时出错。"),
    ("IDS_NT_GEOLITE_RETRY_DOWNLOAD", 12035, "Click Retry to download the update again.", "单击“重试”重新下载更新。"),
    ("IDS_NT_GEOLITE_UPDATE_UNAVAILABLE", 12036, "Unable to download GeoLite update.", "无法下载 GeoLite 更新。"),
    (
        "IDS_NT_GEOLITE_INVALID_SETTINGS",
        12037,
        "Please check the Options > Network Tools > GeoLite ID or Key are configured before downloading geoLite updates.",
        "下载 GeoLite 更新前，请确认已在“设置 > 网络工具”中配置 GeoLite ID 或密钥。",
    ),
    ("IDS_NT_UNABLE_CREATE_WINDOW", 12038, "Unable to create the window.", "无法创建窗口。"),
    ("IDS_NT_GEOLITE_INITIALIZING", 12039, "Initializing...", "正在初始化..."),
    ("IDS_NT_GEOLITE_UPDATES_UNAVAILABLE", 12040, "Unable to download GeoLite database updates.", "无法下载 GeoLite 数据库更新。"),
    ("IDS_NT_MENU_PING", 12041, "Ping", "Ping"),
    ("IDS_NT_MENU_TRACEROUTE", 12042, "Traceroute", "路由跟踪"),
    ("IDS_NT_MENU_WHOIS", 12043, "Whois", "Whois 查询"),
    ("IDS_NT_MENU_COPY", 12044, "Copy", "复制"),
    ("IDS_NT_MENU_COPY_ACCELERATOR", 12045, "&Copy", "复制(&C)"),
    ("IDS_NT_MENU_SELECT_ALL", 12046, "&Select all", "全选(&S)"),
    ("IDS_NT_COLUMN_TTL", 12047, "TTL", "TTL"),
    ("IDS_NT_COLUMN_TIME_1", 12048, "Time 1", "时间 1"),
    ("IDS_NT_COLUMN_TIME_2", 12049, "Time 2", "时间 2"),
    ("IDS_NT_COLUMN_TIME_3", 12050, "Time 3", "时间 3"),
    ("IDS_NT_COLUMN_TIME_4", 12051, "Time 4", "时间 4"),
    ("IDS_NT_COLUMN_IP_ADDRESS", 12052, "IP Address", "IP 地址"),
    ("IDS_NT_COLUMN_HOSTNAME", 12053, "Hostname", "主机名"),
    ("IDS_NT_COLUMN_COUNTRY", 12054, "Country", "国家/地区"),
)


PAGE_ROUTES = {
    "ShowDbCheckForUpdatesDialog": (
        ("pszWindowTitle", "IDS_NT_GEOLITE_UPDATER_TITLE"),
        ("pszMainInstruction", "IDS_NT_GEOLITE_DOWNLOAD_QUESTION"),
        ("pszContent", "IDS_NT_GEOLITE_DOWNLOAD_SOURCE_CONTENT"),
    ),
    "ShowDbCheckingForUpdatesDialog": (
        ("pszWindowTitle", "IDS_NT_GEOLITE_UPDATER_TITLE"),
        ("pszMainInstruction", "IDS_NT_GEOLITE_DOWNLOADING"),
        ("pszContent", "IDS_NT_GEOLITE_DOWNLOAD_PROGRESS"),
    ),
    "ShowDbInstallRestartDialog": (
        ("pszWindowTitle", "IDS_NT_GEOLITE_UPDATER_TITLE"),
        ("pszMainInstruction", "IDS_NT_GEOLITE_UPDATED"),
        ("pszContent", "IDS_NT_GEOLITE_RESTART_REQUIRED"),
    ),
    "ShowDbUpdateFailedDialog": (
        ("pszWindowTitle", "IDS_NT_GEOLITE_UPDATER_TITLE"),
        ("pszMainInstruction", "IDS_NT_GEOLITE_DOWNLOAD_ERROR"),
    ),
    "ShowDbInvalidSettingsDialog": (
        ("pszWindowTitle", "IDS_NT_GEOLITE_UPDATER_TITLE"),
        ("pszMainInstruction", "IDS_NT_GEOLITE_UPDATE_UNAVAILABLE"),
        ("pszContent", "IDS_NT_GEOLITE_INVALID_SETTINGS"),
    ),
}


TREE_ROUTES = (
    ("TREE_COLUMN_ITEM_TTL", "IDS_NT_COLUMN_TTL"),
    ("TREE_COLUMN_ITEM_PING1", "IDS_NT_COLUMN_TIME_1"),
    ("TREE_COLUMN_ITEM_PING2", "IDS_NT_COLUMN_TIME_2"),
    ("TREE_COLUMN_ITEM_PING3", "IDS_NT_COLUMN_TIME_3"),
    ("TREE_COLUMN_ITEM_PING4", "IDS_NT_COLUMN_TIME_4"),
    ("TREE_COLUMN_ITEM_IPADDR", "IDS_NT_COLUMN_IP_ADDRESS"),
    ("TREE_COLUMN_ITEM_HOSTNAME", "IDS_NT_COLUMN_HOSTNAME"),
    ("TREE_COLUMN_ITEM_COUNTRY", "IDS_NT_COLUMN_COUNTRY"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("networktools_runtime_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str) -> str:
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


def parse_stringtable(path: pathlib.Path):
    return {
        symbol: value.replace('""', '"').replace(r"\r", "\r").replace(r"\n", "\n")
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_NT_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


def auto_getter(resource: str) -> str:
    return (
        r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
        rf"PluginInstance->DllBase\s*,\s*{resource}\s*,\s*NULL\s*\)\)\)"
    )


class NetworkToolsRuntimeNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit_module()
        cls.sources = {
            path.name: cls.audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in PLUGIN_ROOT.glob("*.c")
        }

    def test_resources_are_exact_contiguous_and_preserve_contracts(self):
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_NT_[A-Z0-9_]+)\s+(\d+)$",
                header,
            )
        }
        english = parse_stringtable(PLUGIN_ROOT / "NetworkTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "NetworkTools.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCE_DATA], list(range(12027, 12055)))
        self.assertEqual(sorted(defines.values()), list(range(12000, 12062)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 62)
        self.assertEqual(len(chinese), 62)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12062$")

        for table in (english, chinese):
            self.assertEqual(table["IDS_NT_GEOLITE_DOWNLOAD_PROGRESS"].count("~"), 4)
            self.assertIn("~%%", table["IDS_NT_GEOLITE_DOWNLOAD_PROGRESS"])
            self.assertEqual(table["IDS_NT_GEOLITE_DOWNLOAD_SOURCE_CONTENT"].count("https://www.maxmind.com"), 2)
            self.assertEqual(table["IDS_NT_GEOLITE_DOWNLOAD_SOURCE_CONTENT"].count("<a href=\""), 1)
            self.assertEqual(table["IDS_NT_GEOLITE_DOWNLOAD_SOURCE_CONTENT"].count("</a>"), 1)
        self.assertEqual(english["IDS_NT_MENU_COPY_ACCELERATOR"].count("&"), 1)
        self.assertEqual(english["IDS_NT_MENU_SELECT_ALL"].count("&"), 1)

    def test_taskdialogs_and_message_box_use_live_native_resources(self):
        pages = self.sources["pages.c"]
        for function_name, routes in PAGE_ROUTES.items():
            body = function_body(pages, function_name)
            for field, resource in routes:
                with self.subTest(function=function_name, field=field):
                    self.assertRegex(
                        body,
                        rf"config\.{field}\s*=\s*{auto_getter(resource)}\s*;",
                    )
            self.assertLess(body.index("config.pszWindowTitle"), body.index("PhTaskDialogNavigatePage("))

        failed = function_body(pages, "ShowDbUpdateFailedDialog")
        self.assertRegex(
            failed,
            rf"else\s*\{{\s*config\.pszContent\s*=\s*{auto_getter('IDS_NT_GEOLITE_RETRY_DOWNLOAD')}\s*;",
        )

        update = self.sources["update.c"]
        thread = function_body(update, "GeoLiteUpdateTaskDialogThread")
        self.assertRegex(thread, rf"config\.pszContent\s*=\s*{auto_getter('IDS_NT_GEOLITE_INITIALIZING')}\s*;")
        self.assertLess(thread.index("config.pszContent"), thread.index("PhShowTaskDialog(&config"))

        show = function_body(update, "ShowGeoLiteUpdateDialog")
        self.assertRegex(show, rf"config\.pszWindowTitle\s*=\s*{auto_getter('IDS_NT_GEOLITE_UPDATER_TITLE')}\s*;")
        self.assertRegex(show, rf"config\.pszMainInstruction\s*=\s*{auto_getter('IDS_NT_GEOLITE_UPDATES_UNAVAILABLE')}\s*;")
        self.assertRegex(
            show,
            rf"PhShowError2\(\s*ParentWindowHandle\s*,\s*{auto_getter('IDS_NT_UNABLE_CREATE_WINDOW')}\s*,\s*L\"%s\"",
        )

    def test_menus_and_tree_columns_use_exact_resource_routes(self):
        tracert = function_body(self.sources["tracert.c"], "TracertDlgProc")
        tracert_menu = tuple(re.findall(
            r"PhCreateEMenuItem\(\s*0\s*,\s*([A-Z0-9_]+)\s*,\s*"
            r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*"
            r"(IDS_NT_[A-Z0-9_]+)\s*,\s*NULL\s*\)\)\)",
            tracert,
            re.S,
        ))
        self.assertEqual(tracert_menu, (
            ("MAINMENU_ACTION_PING", "IDS_NT_MENU_PING"),
            ("NETWORK_ACTION_TRACEROUTE", "IDS_NT_MENU_TRACEROUTE"),
            ("NETWORK_ACTION_WHOIS", "IDS_NT_MENU_WHOIS"),
            ("MENU_ACTION_COPY", "IDS_NT_MENU_COPY"),
        ))

        whois = function_body(self.sources["whois.c"], "WhoisDlgProc")
        whois_menu = tuple(re.findall(
            r"PhCreateEMenuItem\(\s*0\s*,\s*(\d+)\s*,\s*"
            r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*"
            r"(IDS_NT_[A-Z0-9_]+)\s*,\s*NULL\s*\)\)\)",
            whois,
            re.S,
        ))
        self.assertEqual(whois_menu, (
            ("10", "IDS_NT_MENU_COPY_ACCELERATOR"),
            ("11", "IDS_NT_MENU_SELECT_ALL"),
        ))

        tree_source = self.sources["tracetree.c"]
        helper = function_body(tree_source, "TracertTreeGetUiString")
        self.assertRegex(tree_source, r"static\s+PH_INITONCE\s+TracertTreeUiStringsInitOnce\s*=\s*PH_INITONCE_INIT\s*;")
        self.assertRegex(helper, r"PhBeginInitOnce\(&TracertTreeUiStringsInitOnce\)")
        self.assertRegex(helper, r"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*resourceId\s*,\s*NULL\s*\)")
        self.assertRegex(helper, r"PhEndInitOnce\(&TracertTreeUiStringsInitOnce\)")

        tree = function_body(tree_source, "InitializeTracertTree")
        actual_tree = tuple(re.findall(
            r"PhAddTreeNewColumn(?:Ex2)?\(\s*Context->TreeNewHandle\s*,\s*([A-Z0-9_]+)\s*,[^,]+,\s*"
            r"TracertTreeGetUiString\((IDS_NT_[A-Z0-9_]+)\)",
            tree,
            re.S,
        ))
        self.assertEqual(actual_tree, TREE_ROUTES)

    def test_fresh_module_has_no_target_runtime_categories(self):
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)
        remaining = Counter(
            (entry["category"], entry["english"], entry["file"])
            for entry in entries
            if entry["category"] in TARGET_CATEGORIES
        )
        self.assertEqual(remaining, Counter())

if __name__ == "__main__":
    unittest.main()
