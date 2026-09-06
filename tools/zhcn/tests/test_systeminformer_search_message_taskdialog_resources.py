#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCE_DATA = r'''
IDS_PH_SETTINGS_FILE_CORRUPT_PROMPT|2872|System Informer's settings file is corrupt. Do you want to reset it?|sys_info 的设置文件已损坏。要重置吗？
IDS_PH_SETTINGS_FILE_CORRUPT_CONTENT|2873|If you select No, the settings system will not function properly.|如果选择“否”，设置系统将无法正常工作。
IDS_PH_FILTERED_NODE_HIDDEN|2874|This node cannot be displayed because it is currently hidden by your active filter settings or preferences.|该节点无法显示，因为它已被当前生效的筛选设置或首选项隐藏。
IDS_PH_UNABLE_LOAD_PLUGINS|2875|Unable to load the following plugin(s)|无法加载以下插件
IDS_PH_SEARCH_ACTIVE_COLUMNS|2876|Active columns...|活动列...
IDS_PH_SEARCH_INACTIVE_COLUMNS|2877|Inactive columns...|非活动列...
IDS_PH_SEARCH_FIND_HANDLES_OR_DLLS|2878|Find Handles or DLLs|查找句柄或 DLL
IDS_PH_SEARCH_ENVIRONMENT|2879|Search Environment (Ctrl+K)|搜索环境变量 (Ctrl+K)
IDS_PH_SEARCH_HANDLES|2880|Search Handles (Ctrl+K)|搜索句柄 (Ctrl+K)
IDS_PH_SEARCH_MEMORY|2881|Search Memory (Ctrl+K)|搜索内存 (Ctrl+K)
IDS_PH_SEARCH_MODULES|2882|Search Modules (Ctrl+K)|搜索模块 (Ctrl+K)
IDS_PH_SEARCH_MONITOR|2883|Search Monitor (Ctrl+K)|搜索监视器 (Ctrl+K)
IDS_PH_SEARCH_PACKAGES|2884|Search Packages|搜索程序包
IDS_PH_SEARCH_SETTINGS|2885|Search settings...|搜索设置...
IDS_PH_SEARCH_STRINGS|2886|Search Strings (Ctrl+K)|搜索字符串 (Ctrl+K)
IDS_PH_SEARCH_THREAD_STACKS|2887|Search Thread Stacks|搜索线程堆栈
IDS_PH_SEARCH_THREADS|2888|Search Threads (Ctrl+K)|搜索线程 (Ctrl+K)
IDS_PH_SEARCH_USERS|2889|Search Users|搜索用户
IDS_PH_SEARCH_WMI_PROVIDERS|2890|Search WMI Providers (Ctrl+K)|搜索 WMI 提供程序 (Ctrl+K)
IDS_PH_CREATING_MINIDUMP_FILE|2891|Creating the minidump file...|正在创建小型转储文件...
IDS_PH_EXECUTING_MEMORY_COMMAND|2892|Executing memory command...|正在执行内存命令...
IDS_PH_EXECUTING_MEMORY_COMMANDS|2893|Executing memory commands...|正在执行多个内存命令...
IDS_PH_LIVE_KERNEL_DUMP_CREATED|2894|Live kernel dump has been created.|已创建实时内核转储。
IDS_PH_PROCESSING_LIVE_KERNEL_DUMP|2895|Processing live kernel dump...|正在处理实时内核转储...
IDS_PH_SEARCHING_MEMORY_STRINGS|2896|Searching memory strings...|正在搜索内存字符串...
'''.strip()

RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in
    (line.split("|", 3) for line in RESOURCE_DATA.splitlines())
)

ROUTES = {
    "plugin.c": (("Unable to load the following plugin(s)", "IDS_PH_UNABLE_LOAD_PLUGINS", 1),),
    "netlist.c": (("This node cannot be displayed because it is currently hidden by your active filter settings or preferences.", "IDS_PH_FILTERED_NODE_HIDDEN", 1),),
    "proctree.c": (("This node cannot be displayed because it is currently hidden by your active filter settings or preferences.", "IDS_PH_FILTERED_NODE_HIDDEN", 1),),
    "srvlist.c": (("This node cannot be displayed because it is currently hidden by your active filter settings or preferences.", "IDS_PH_FILTERED_NODE_HIDDEN", 1),),
    "prpgwmi.c": (
        ("Unknown error.", "IDS_PH_UNKNOWN_ERROR", 1),
        ("Search WMI Providers (Ctrl+K)", "IDS_PH_SEARCH_WMI_PROVIDERS", 1),
    ),
    "chcol.c": (("Inactive columns...", "IDS_PH_SEARCH_INACTIVE_COLUMNS", 1), ("Active columns...", "IDS_PH_SEARCH_ACTIVE_COLUMNS", 1)),
    "findobj.c": (("Find Handles or DLLs", "IDS_PH_SEARCH_FIND_HANDLES_OR_DLLS", 1),),
    "prpgenv.c": (("Search Environment (Ctrl+K)", "IDS_PH_SEARCH_ENVIRONMENT", 1),),
    "prpghndl.c": (("Search Handles (Ctrl+K)", "IDS_PH_SEARCH_HANDLES", 1),),
    "prpgmem.c": (("Search Memory (Ctrl+K)", "IDS_PH_SEARCH_MEMORY", 1),),
    "prpgmod.c": (("Search Modules (Ctrl+K)", "IDS_PH_SEARCH_MODULES", 1),),
    "informerwnd.c": (("Search Monitor (Ctrl+K)", "IDS_PH_SEARCH_MONITOR", 1),),
    "runaspkg.c": (("Search Packages", "IDS_PH_SEARCH_PACKAGES", 1),),
    "options.c": (("Search settings...", "IDS_PH_SEARCH_SETTINGS", 1),),
    "memsrcht.c": (("Search Strings (Ctrl+K)", "IDS_PH_SEARCH_STRINGS", 1),),
    "thrdstks.c": (("Search Thread Stacks", "IDS_PH_SEARCH_THREAD_STACKS", 1),),
    "prpgthrd.c": (("Search Threads (Ctrl+K)", "IDS_PH_SEARCH_THREADS", 1),),
    "usrlist.c": (("Search Users", "IDS_PH_SEARCH_USERS", 1),),
    "mdump.c": (("Creating the minidump file...", "IDS_PH_CREATING_MINIDUMP_FILE", 2),),
    "memlists.c": (("Executing memory commands...", "IDS_PH_EXECUTING_MEMORY_COMMANDS", 1), ("Executing memory command...", "IDS_PH_EXECUTING_MEMORY_COMMAND", 1)),
    "kdump.c": (("Live kernel dump has been created.", "IDS_PH_LIVE_KERNEL_DUMP_CREATED", 1), ("Processing live kernel dump...", "IDS_PH_PROCESSING_LIVE_KERNEL_DUMP", 1)),
    "memsrch.c": (("Searching memory strings...", "IDS_PH_SEARCHING_MEMORY_STRINGS", 1),),
}


def load_audit():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_search_message_taskdialog", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class SystemInformerSearchMessageTaskDialogResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit()

    def test_resource_tail_and_bilingual_values_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(en, english.get(symbol))
                self.assertEqual(zh, chinese.get(symbol))

        self.assertEqual(list(range(2872, 2897)), [row[1] for row in RESOURCES])
        self.assertEqual(1126, len(english))
        self.assertEqual(1126, len(chinese))
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_LISTVIEW_POLICY$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3126$")

    def test_every_runtime_literal_routes_through_the_application_resource_cache(self) -> None:
        for file_name, routes in ROUTES.items():
            source = self.audit.mask_c_comments(
                (APP_ROOT / file_name).read_text(encoding="utf-8-sig")
            )
            for literal, symbol, expected_count in routes:
                with self.subTest(file=file_name, literal=literal):
                    self.assertEqual(
                        expected_count,
                        len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)),
                    )

    def test_startup_settings_messages_load_selected_language_before_cache_initialization(self) -> None:
        source = self.audit.mask_c_comments(
            (APP_ROOT / "main.c").read_text(encoding="utf-8-sig")
        )
        self.assertLess(
            source.index("PhInitializeAppSettings();"),
            source.index("PhpInitializeApplicationUiStrings()"),
        )
        helper_match = re.search(
            r"static PPH_STRING\s+PhpLoadStartupUiString\s*\([^{}]*\)\s*\{(?P<body>.*?)\n\}",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(helper_match)
        helper = helper_match.group("body")
        self.assertIn("PhLoadUiString(PhInstanceHandle, ResourceId, NULL)", helper)
        self.assertIn("PhCreateString(DefaultString)", helper)

        settings_start = source.index("VOID PhInitializeAppSettings(")
        settings_end = source.index("\nVOID PhpEnablePrivileges(", settings_start)
        settings = source[settings_start:settings_end]
        for literal, symbol in (
            ("System Informer's settings file is corrupt. Do you want to reset it?", "IDS_PH_SETTINGS_FILE_CORRUPT_PROMPT"),
            ("If you select No, the settings system will not function properly.", "IDS_PH_SETTINGS_FILE_CORRUPT_CONTENT"),
        ):
            with self.subTest(symbol=symbol):
                self.assertRegex(
                    settings,
                    rf"PhpLoadStartupUiString\(\s*{symbol}\s*,\s*L\"{re.escape(literal)}\"\s*\)",
                )
        self.assertRegex(
            settings,
            r"resourceTitle\s*=\s*PhLoadUiString\(\s*PhInstanceHandle,\s*IDS_PH_UNABLE_LOAD_SETTINGS,\s*NULL\s*\)",
        )
        self.assertIn(
            'resourceTitle = PhCreateString(L"Unable to load the settings file.");',
            settings,
        )
        for variable in ("instruction", "content", "resourceTitle"):
            self.assertEqual(1, settings.count(f"PhClearReference(&{variable});"))
        self.assertNotRegex(
            settings,
            r"PhShow(?:Message2|Status)\([^;]*L\"(?:System Informer's settings file is corrupt|If you select No|Unable to load the settings file)",
        )

    def test_migrated_categories_are_absent_from_fresh_systeminformer_scan(self) -> None:
        entries = []
        for path in sorted(APP_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)
        target_literals = {english for _symbol, _resource_id, english, _chinese in RESOURCES}
        target_literals.update({"Unable to load the settings file.", "Unknown error."})
        remaining = [
            entry for entry in entries
            if entry["category"] in {"c_search", "c_msgbox", "c_taskdialog"}
            and entry["english"] in target_literals
        ]
        self.assertEqual([], remaining)

    def test_json_moves_completed_runtime_keys_to_native_layer(self) -> None:
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        expected = {english: chinese for _symbol, _resource_id, english, chinese in RESOURCES}
        expected["Unable to load the settings file."] = "无法加载设置文件。"
        expected["Unknown error."] = "未知错误。"
        for english, chinese in expected.items():
            with self.subTest(english=english):
                self.assertEqual(chinese, translations["native_strings"].get(english))
                self.assertNotIn(english, translations["strings"])


if __name__ == "__main__":
    unittest.main()
