#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from typing import Optional


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_LISTVIEW_DISPLAY_NAME", "Display name", "显示名称"),
    ("IDS_PH_LISTVIEW_SESSION", "Session", "会话"),
    ("IDS_PH_LISTVIEW_VIEW", "View", "视图"),
    ("IDS_PH_LISTVIEW_START", "Start", "起始"),
    ("IDS_PH_LISTVIEW_END", "End", "结束"),
    ("IDS_PH_LISTVIEW_USAGE", "Usage", "使用率"),
    ("IDS_PH_LISTVIEW_PEAK_USAGE", "Peak usage", "峰值使用"),
    ("IDS_PH_LISTVIEW_TOTAL", "Total", "总计"),
    ("IDS_PH_LISTVIEW_MINIMUM", "Minimum", "最小值"),
    ("IDS_PH_LISTVIEW_MAXIMUM", "Maximum", "最大值"),
    ("IDS_PH_LISTVIEW_PROCESS", "Process", "进程"),
    ("IDS_PH_LISTVIEW_UNKNOWN_PARENTHESIZED", "(unknown)", "（未知）"),
    ("IDS_PH_LISTVIEW_MODULE_NAME", "Module name", "模块名"),
    ("IDS_PH_LISTVIEW_THREAD_ID", "Thread Id", "线程 ID"),
    ("IDS_PH_LISTVIEW_TASK_ID", "Task Id", "任务 ID"),
    ("IDS_PH_LISTVIEW_ADDRESS", "Address", "地址"),
    ("IDS_PH_LISTVIEW_BASE_ADDRESS", "Base Address", "基址"),
    ("IDS_PH_LISTVIEW_LENGTH", "Length", "长度"),
    ("IDS_PH_LISTVIEW_RESULT", "Result", "结果"),
    ("IDS_PH_LISTVIEW_PRINCIPAL", "Principal", "主体"),
    ("IDS_PH_LISTVIEW_ACCESS", "Access", "访问权限"),
    ("IDS_PH_LISTVIEW_STATUS", "Status", "状态"),
    ("IDS_PH_LISTVIEW_DESCRIPTION", "Description", "描述"),
    ("IDS_PH_LISTVIEW_USE", "Use", "用途"),
    ("IDS_PH_LISTVIEW_INDEX", "Index", "索引"),
    ("IDS_PH_LISTVIEW_IMAGE_BASE", "ImageBase", "映像基址"),
    ("IDS_PH_LISTVIEW_OFFSET", "Offset", "偏移"),
    ("IDS_PH_LISTVIEW_SYMBOL", "Symbol", "符号"),
    ("IDS_PH_LISTVIEW_HANDLE", "Handle", "句柄"),
    ("IDS_PH_LISTVIEW_OBJECT", "Object", "对象"),
    ("IDS_PH_LISTVIEW_USED", "Used", "已用"),
    ("IDS_PH_LISTVIEW_COMMITTED", "Committed", "已提交"),
    ("IDS_PH_LISTVIEW_ENTRIES", "Entries", "条目"),
    ("IDS_PH_LISTVIEW_CLASS", "Class", "类"),
    ("IDS_PH_LISTVIEW_FILENAME", "Filename", "文件名"),
    ("IDS_PH_LISTVIEW_THREAD", "Thread", "线程"),
    ("IDS_PH_LISTVIEW_LOCK_COUNT", "Lock count", "锁定计数"),
    ("IDS_PH_LISTVIEW_CONTENTION_COUNT", "Contention count", "争用计数"),
    ("IDS_PH_LISTVIEW_ENTRY_COUNT", "Entry count", "条目数"),
    ("IDS_PH_LISTVIEW_RECURSION_COUNT", "Recursion count", "递归计数"),
    ("IDS_PH_LISTVIEW_WAITING_SHARED_COUNT", "Waiting shared count", "等待共享计数"),
    ("IDS_PH_LISTVIEW_WAITING_EXCLUSIVE_COUNT", "Waiting exclusive count", "等待独占计数"),
    ("IDS_PH_LISTVIEW_ALLOW_ONLY_ONE_INSTANCE", "Allow only one instance", "仅允许一个实例"),
    ("IDS_PH_LISTVIEW_HIDE_WHEN_CLOSED", "Hide when closed", "关闭时隐藏"),
    ("IDS_PH_LISTVIEW_HIDE_WHEN_MINIMIZED", "Hide when minimized", "最小化时隐藏"),
    ("IDS_PH_LISTVIEW_START_WHEN_LOG_ON", "Start when I log on", "登录时启动"),
    ("IDS_PH_LISTVIEW_START_HIDDEN", "Start hidden", "启动时隐藏"),
    ("IDS_PH_LISTVIEW_ENABLE_WARNINGS", "Enable warnings", "启用警告"),
    ("IDS_PH_LISTVIEW_ENABLE_KERNEL_MODE_DRIVER", "Enable kernel-mode driver", "启用内核驱动"),
    ("IDS_PH_LISTVIEW_ENABLE_MONOSPACE_FONTS", "Enable monospace fonts", "启用等宽字体"),
    ("IDS_PH_LISTVIEW_ENABLE_PLUGINS", "Enable plugins", "启用插件"),
    ("IDS_PH_LISTVIEW_ENABLE_UNDECORATED_SYMBOLS", "Enable undecorated symbols", "启用未修饰符号"),
    ("IDS_PH_LISTVIEW_ENABLE_AVX_EXTENSIONS", "Enable AVX extensions (experimental)", "启用 AVX 扩展（实验性）"),
    ("IDS_PH_LISTVIEW_ENABLE_COLUMN_HEADER_TOTALS", "Enable column header totals (experimental)", "启用列标题总计（实验性）"),
    ("IDS_PH_LISTVIEW_ENABLE_CYCLE_BASED_CPU_USAGE", "Enable cycle-based CPU usage", "启用基于周期的 CPU 使用率"),
    ("IDS_PH_LISTVIEW_ENABLE_LOW_LATENCY_MODE", "Enable low-latency mode (experimental)", "启用低延迟模式（实验性）"),
    ("IDS_PH_LISTVIEW_ENABLE_FIXED_GRAPH_SCALING", "Enable fixed graph scaling (experimental)", "启用固定图表缩放（实验性）"),
    ("IDS_PH_LISTVIEW_ENABLE_TRAY_INFORMATION_WINDOW", "Enable tray information window", "启用托盘信息窗口"),
    ("IDS_PH_LISTVIEW_ENABLE_NEW_MEMORY_STRINGS_DIALOG", "Enable new memory strings dialog", "启用新版内存字符串对话框"),
    ("IDS_PH_LISTVIEW_REMEMBER_LAST_SELECTED_WINDOW", "Remember last selected window", "记住上次选中的窗口"),
    ("IDS_PH_LISTVIEW_ENABLE_THEME_SUPPORT", "Enable theme support (experimental)", "启用主题支持（实验性）"),
    ("IDS_PH_LISTVIEW_ENABLE_START_AS_ADMIN", "Enable start as admin (experimental)", "启用以管理员身份启动（实验性）"),
    ("IDS_PH_LISTVIEW_ENABLE_STREAMER_MODE", "Enable streamer mode (disable window capture) (experimental)", "启用直播模式（禁用窗口捕获）（实验性）"),
    ("IDS_PH_LISTVIEW_RESOLVE_NETWORK_ADDRESSES", "Resolve network addresses", "解析网络地址"),
    ("IDS_PH_LISTVIEW_RESOLVE_DNS_OVER_HTTPS", "Resolve DNS over HTTPS (DoH)", "通过 HTTPS 解析 DNS（DoH）"),
    ("IDS_PH_LISTVIEW_SHOW_TOOLTIPS_INSTANTLY", "Show tooltips instantly", "立即显示工具提示"),
    ("IDS_PH_LISTVIEW_CHECK_IMAGES_FOR_COHERENCY", "Check images for coherency", "检查映像一致性"),
    ("IDS_PH_LISTVIEW_CHECK_IMAGES_FOR_DIGITAL_SIGNATURES", "Check images for digital signatures", "检查映像数字签名"),
    ("IDS_PH_LISTVIEW_CHECK_SERVICES_FOR_DIGITAL_SIGNATURES", "Check services for digital signatures", "检查服务数字签名"),
    ("IDS_PH_LISTVIEW_SINGLE_CLICK_TRAY_ICONS", "Single-click tray icons", "单击打开托盘图标"),
    ("IDS_PH_LISTVIEW_ICON_CLICK_TOGGLES_VISIBILITY", "Icon click toggles visibility", "单击图标切换可见性"),
    ("IDS_PH_LISTVIEW_INCLUDE_COLLAPSED_PROCESS_USAGE", "Include usage of collapsed processes", "包含已折叠进程的使用量"),
    ("IDS_PH_LISTVIEW_ENABLE_PROCESS_MONITOR", "Enable process monitor (experimental)", "启用进程监控（实验性）"),
    ("IDS_PH_LISTVIEW_SHOW_ADVANCED_OPTIONS", "Show advanced options", "显示高级选项"),
    ("IDS_PH_LISTVIEW_POLICY", "Policy", "策略"),
)

REUSED_RESOURCES = {
    "Name": ("IDS_PH_TOKEN_NAME", "名称"),
    "System": ("IDS_PH_GROUP_SYSTEM", "系统"),
    "Unknown": ("IDS_PH_UNKNOWN", "未知"),
    "Size": ("IDS_PH_HANDLE_SIZE", "大小"),
    "Handles": ("IDS_PH_STAT_HANDLES", "句柄"),
    "Type": ("IDS_PH_TOKEN_TYPE", "类型"),
    "SID": ("IDS_PH_TOKEN_SID", "SID"),
    "File": ("IDS_PH_HANDLE_FILE", "文件"),
    "Flags": ("IDS_PH_GROUP_FLAGS", "标志"),
    "Information": ("IDS_PH_MESSAGE_ICON_INFORMATION", "信息"),
}

EXPECTED_ROUTES = {
    "colsetmgr.c": ("IDS_PH_TOKEN_NAME",),
    "srvctl.c": ("IDS_PH_TOKEN_NAME", "IDS_PH_LISTVIEW_DISPLAY_NAME"),
    "ntobjprp.c": ("IDS_PH_LISTVIEW_SESSION", "IDS_PH_GROUP_SYSTEM", "IDS_PH_UNKNOWN", "IDS_PH_LISTVIEW_VIEW", "IDS_PH_LISTVIEW_START", "IDS_PH_LISTVIEW_END", "IDS_PH_HANDLE_SIZE"),
    "pagfiles.c": ("IDS_PH_LISTVIEW_USAGE", "IDS_PH_LISTVIEW_PEAK_USAGE", "IDS_PH_LISTVIEW_TOTAL", "IDS_PH_LISTVIEW_MINIMUM", "IDS_PH_LISTVIEW_MAXIMUM"),
    "hidnproc.c": ("IDS_PH_LISTVIEW_PROCESS", "IDS_PH_STAT_HANDLES", "IDS_PH_LISTVIEW_UNKNOWN_PARENTHESIZED"),
    "prpgvdm.c": ("IDS_PH_LISTVIEW_MODULE_NAME", "IDS_PH_LISTVIEW_THREAD_ID", "IDS_PH_LISTVIEW_TASK_ID"),
    "memrslt.c": ("IDS_PH_LISTVIEW_ADDRESS", "IDS_PH_LISTVIEW_BASE_ADDRESS", "IDS_PH_LISTVIEW_LENGTH", "IDS_PH_LISTVIEW_RESULT"),
    "hndlprp.c": ("IDS_PH_TOKEN_NAME", "IDS_PH_TOKEN_NAME", "IDS_PH_TOKEN_NAME", "IDS_PH_LISTVIEW_PRINCIPAL", "IDS_PH_TOKEN_TYPE", "IDS_PH_LISTVIEW_ACCESS", "IDS_PH_LISTVIEW_PRINCIPAL", "IDS_PH_TOKEN_TYPE", "IDS_PH_LISTVIEW_ACCESS"),
    "netstk.c": ("IDS_PH_TOKEN_NAME",),
    "tokprp.c": ("IDS_PH_TOKEN_NAME", "IDS_PH_LISTVIEW_STATUS", "IDS_PH_LISTVIEW_DESCRIPTION", "IDS_PH_TOKEN_SID", "IDS_PH_TOKEN_TYPE", "IDS_PH_LISTVIEW_USE", "IDS_PH_TOKEN_NAME", "IDS_PH_TOKEN_NAME"),
    "memmod.c": ("IDS_PH_LISTVIEW_INDEX", "IDS_PH_HANDLE_FILE", "IDS_PH_LISTVIEW_IMAGE_BASE", "IDS_PH_LISTVIEW_OFFSET", "IDS_PH_LISTVIEW_ADDRESS", "IDS_PH_LISTVIEW_SYMBOL"),
    "gdihndl.c": ("IDS_PH_TOKEN_TYPE", "IDS_PH_LISTVIEW_HANDLE", "IDS_PH_LISTVIEW_OBJECT", "IDS_PH_MESSAGE_ICON_INFORMATION"),
    "heapinfo.c": ("IDS_PH_LISTVIEW_ADDRESS", "IDS_PH_LISTVIEW_USED", "IDS_PH_LISTVIEW_COMMITTED", "IDS_PH_LISTVIEW_ENTRIES", "IDS_PH_GROUP_FLAGS", "IDS_PH_LISTVIEW_CLASS", "IDS_PH_TOKEN_TYPE", "IDS_PH_TOKEN_TYPE", "IDS_PH_LISTVIEW_ADDRESS", "IDS_PH_LISTVIEW_FILENAME", "IDS_PH_LISTVIEW_THREAD", "IDS_PH_LISTVIEW_LOCK_COUNT", "IDS_PH_LISTVIEW_CONTENTION_COUNT", "IDS_PH_LISTVIEW_ENTRY_COUNT", "IDS_PH_LISTVIEW_RECURSION_COUNT", "IDS_PH_LISTVIEW_WAITING_SHARED_COUNT", "IDS_PH_LISTVIEW_WAITING_EXCLUSIVE_COUNT"),
    "options.c": (
        "IDS_PH_LISTVIEW_ALLOW_ONLY_ONE_INSTANCE", "IDS_PH_LISTVIEW_HIDE_WHEN_CLOSED", "IDS_PH_LISTVIEW_HIDE_WHEN_MINIMIZED", "IDS_PH_LISTVIEW_START_WHEN_LOG_ON", "IDS_PH_LISTVIEW_START_HIDDEN", "IDS_PH_LISTVIEW_ENABLE_WARNINGS", "IDS_PH_LISTVIEW_ENABLE_KERNEL_MODE_DRIVER", "IDS_PH_LISTVIEW_ENABLE_MONOSPACE_FONTS", "IDS_PH_LISTVIEW_ENABLE_PLUGINS", "IDS_PH_LISTVIEW_ENABLE_UNDECORATED_SYMBOLS", "IDS_PH_LISTVIEW_ENABLE_AVX_EXTENSIONS", "IDS_PH_LISTVIEW_ENABLE_COLUMN_HEADER_TOTALS", "IDS_PH_LISTVIEW_ENABLE_CYCLE_BASED_CPU_USAGE", "IDS_PH_LISTVIEW_ENABLE_LOW_LATENCY_MODE", "IDS_PH_LISTVIEW_ENABLE_FIXED_GRAPH_SCALING", "IDS_PH_LISTVIEW_ENABLE_TRAY_INFORMATION_WINDOW", "IDS_PH_LISTVIEW_ENABLE_NEW_MEMORY_STRINGS_DIALOG", "IDS_PH_LISTVIEW_REMEMBER_LAST_SELECTED_WINDOW", "IDS_PH_LISTVIEW_ENABLE_THEME_SUPPORT", "IDS_PH_LISTVIEW_ENABLE_START_AS_ADMIN", "IDS_PH_LISTVIEW_ENABLE_STREAMER_MODE", "IDS_PH_LISTVIEW_RESOLVE_NETWORK_ADDRESSES", "IDS_PH_LISTVIEW_RESOLVE_DNS_OVER_HTTPS", "IDS_PH_LISTVIEW_SHOW_TOOLTIPS_INSTANTLY", "IDS_PH_LISTVIEW_CHECK_IMAGES_FOR_COHERENCY", "IDS_PH_LISTVIEW_CHECK_IMAGES_FOR_DIGITAL_SIGNATURES", "IDS_PH_LISTVIEW_CHECK_SERVICES_FOR_DIGITAL_SIGNATURES", "IDS_PH_LISTVIEW_SINGLE_CLICK_TRAY_ICONS", "IDS_PH_LISTVIEW_ICON_CLICK_TOGGLES_VISIBILITY", "IDS_PH_LISTVIEW_INCLUDE_COLLAPSED_PROCESS_USAGE", "IDS_PH_LISTVIEW_ENABLE_PROCESS_MONITOR", "IDS_PH_LISTVIEW_SHOW_ADVANCED_OPTIONS", "IDS_PH_TOKEN_NAME", "IDS_PH_TOKEN_NAME", "IDS_PH_TOKEN_NAME", "IDS_PH_TOKEN_NAME",
    ),
    "mtgndlg.c": ("IDS_PH_LISTVIEW_POLICY",),
}

RUNTIME_COMPATIBILITY_KEYS = {
    "Address", "Description", "Display name", "Handle", "Handles",
    "Class", "File", "Flags", "ImageBase", "Index", "Information", "Length", "Name",
    "Policy", "Process", "Result", "SID", "Size", "Status", "Symbol", "System",
    "Thread", "Total", "Type", "Unknown", "Use",
}

COLUMN_APIS = {"PhAddListViewColumn", "PhAddListViewColumnDpi", "PhAddIListViewColumn", "PhAddIListViewColumnDpi"}
ITEM_APIS = {"PhAddListViewItem", "PhAddIListViewItem"}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("listview_native_audit", path)
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


class SystemInformerListViewNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.target_symbols = {symbol for symbol, _en, _zh in NEW_RESOURCES} | {symbol for symbol, _zh in REUSED_RESOURCES.values()}

    def routed_symbols(self, file_name: str, source: Optional[str] = None) -> tuple:
        if source is None:
            source = (APP_ROOT / file_name).read_text(encoding="utf-8-sig")
        source = self.audit.mask_c_comments(source)
        routed = []
        for name, args, _spans, _start in self.audit.find_calls(source, COLUMN_APIS | ITEM_APIS):
            text_index = 7 if name.endswith("ColumnDpi") else 6 if name.endswith("Column") else 2
            match = re.search(r"PhGetApplicationUiString\(\s*(IDS_PH_[A-Z0-9_]+)\s*\)", args[text_index])
            if match and match.group(1) in self.target_symbols:
                routed.append(match.group(1))
        return tuple(routed)

    def assert_route_contract(self, sources: Optional[dict] = None) -> None:
        sources = sources or {}
        actual = {
            file_name: self.routed_symbols(file_name, sources.get(file_name))
            for file_name in EXPECTED_ROUTES
        }
        self.assertEqual(EXPECTED_ROUTES, actual)
        self.assertEqual(107, sum(map(len, actual.values())))

    def test_all_107_calls_use_the_exact_native_resource_route(self) -> None:
        self.assert_route_contract()

    def test_route_contract_rejects_a_reused_resource_swap(self) -> None:
        source = (APP_ROOT / "colsetmgr.c").read_text(encoding="utf-8-sig")
        mutated = source.replace("PhGetApplicationUiString(IDS_PH_TOKEN_NAME)", "PhGetApplicationUiString(IDS_PH_TOKEN_TYPE)", 1)
        self.assertNotEqual(source, mutated)
        with self.assertRaises(AssertionError):
            self.assert_route_contract({"colsetmgr.c": mutated})

        source = (APP_ROOT / "srvctl.c").read_text(encoding="utf-8-sig")
        mutated = source.replace("IDS_PH_LISTVIEW_DISPLAY_NAME", "IDS_PH_LISTVIEW_SESSION", 1)
        self.assertNotEqual(source, mutated)
        with self.assertRaises(AssertionError):
            self.assert_route_contract({"srvctl.c": mutated})

    def test_unknown_fallback_preserves_dynamic_file_name_before_native_default(self) -> None:
        source = self.audit.mask_c_comments((APP_ROOT / "hidnproc.c").read_text(encoding="utf-8-sig"))
        self.assertRegex(
            source,
            r"PhAddListViewItem\(\s*PhZombieProcessesListViewHandle\s*,\s*MAXINT\s*,\s*"
            r"PhGetStringOrDefault\(\s*entry->FileName\s*,\s*"
            r"PhGetApplicationUiString\(IDS_PH_LISTVIEW_UNKNOWN_PARENTHESIZED\)\s*\)\s*,\s*entry\s*\)",
        )

    def test_resources_are_contiguous_bilingual_and_owned_by_one_layer(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        for resource_id, (symbol, en, zh) in enumerate(NEW_RESOURCES, 3051):
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))

        all_labels = {en: zh for _symbol, en, zh in NEW_RESOURCES}
        all_labels.update({en: zh for en, (_symbol, zh) in REUSED_RESOURCES.items()})
        for en, zh in all_labels.items():
            expected_layer = "strings" if en in RUNTIME_COMPATIBILITY_KEYS else "native_strings"
            other_layer = "native_strings" if expected_layer == "strings" else "strings"
            self.assertEqual(zh, data[expected_layer].get(en), en)
            self.assertNotIn(en, data[other_layer], en)

        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_TERMINATE_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3423$")
        self.assertEqual(1423, len(english))
        self.assertEqual(1423, len(chinese))

    def test_thread_stays_runtime_owned_for_indirect_informer_menu_consumer(self) -> None:
        informer = self.audit.mask_c_comments((APP_ROOT / "informerwnd.c").read_text(encoding="utf-8-sig"))
        emenu = self.audit.mask_c_comments((REPO_ROOT / "phlib" / "emenu.c").read_text(encoding="utf-8-sig"))

        self.assertRegex(
            informer,
            r"\{\s*PH_INFORMER_CATEGORY_THREAD\s*,\s*L\"Thread\"\s*\}",
        )
        self.assertRegex(
            informer,
            r"PhCreateEMenuItem\(\s*0\s*,\s*categories\[i\]\.Id\s*,\s*"
            r"categories\[i\]\.Text\s*,\s*NULL\s*,\s*NULL\s*\)",
        )
        self.assertRegex(
            emenu,
            r"PhCreateEMenuItem\([\s\S]*?item->Text\s*=\s*\(PWSTR\)Text",
        )

    def test_shared_listview_keys_keep_cross_module_runtime_compatibility(self) -> None:
        sources = {
            "extended_main": (REPO_ROOT / "plugins" / "ExtendedTools" / "main.c").read_text(encoding="utf-8-sig"),
            "extended_tpm": (REPO_ROOT / "plugins" / "ExtendedTools" / "tpm.c").read_text(encoding="utf-8-sig"),
            "hardware_tree": (REPO_ROOT / "plugins" / "HardwareDevices" / "devicetree.c").read_text(encoding="utf-8-sig"),
            "window_tree": (REPO_ROOT / "plugins" / "WindowExplorer" / "wndtree.c").read_text(encoding="utf-8-sig"),
            "pe_header": (REPO_ROOT / "tools" / "peview" / "peheaderprp.c").read_text(encoding="utf-8-sig"),
            "clr_map": (REPO_ROOT / "phlib" / "mapclr.c").read_text(encoding="utf-8-sig"),
            "tree_helper": (REPO_ROOT / "phlib" / "treenew.c").read_text(encoding="utf-8-sig"),
        }

        self.assertEqual(2, sources["extended_main"].count('EtGetUiString(IDS_ET_TOTAL, L"Total")'))
        self.assertIn('EtGetUiString(IDS_ET_INDEX, L"Index")', sources["extended_tpm"])
        self.assertIn(
            '{ PhDevicePropertyClass, IDS_HD_GROUP_CLASS, L"Class", TRUE, 120, 0 }',
            sources["hardware_tree"],
        )
        self.assertIn('PhAddTreeNewColumn(', sources["hardware_tree"])
        self.assertIn('WepAddTreeNewResourceColumn(TreeNewHandle, columnTextList, WEWNTLC_CLASS, IDS_WE_GROUP_CLASS', sources["window_tree"])
        self.assertIn('PvpLoadUiString(IDS_PV_FIELD_OPTIONAL_IMAGE_BASE)', sources["pe_header"])
        self.assertIn('[PH_CLR_TABLE_LOCALVARIABLE] = { L"Attributes", L"Index", L"Name" }', sources["clr_map"])
        self.assertIn('[PH_CLR_TABLE_INTERFACEIMPL] = { L"Class", L"Interface" }', sources["clr_map"])
        self.assertIn('realColumn->Text = Column->Text;', sources["tree_helper"])

    def test_systeminformer_has_no_runtime_listview_findings(self) -> None:
        unresolved = []
        for path in APP_ROOT.glob("*.c"):
            entries = []
            self.audit.scan_c_file(str(path), entries)
            unresolved.extend(entry for entry in entries if entry["category"] in {"c_listview_col", "c_listview_item"})
        self.assertEqual([], unresolved)

    def test_shared_listview_helpers_no_longer_translate_and_raw_api_remains(self) -> None:
        source = (REPO_ROOT / "phlib" / "guisuplistview.cpp").read_text(encoding="utf-8-sig")
        self.assertEqual(0, source.count("PhTranslateString("))
        self.assertEqual(2, source.count("column.pszText = const_cast<PWSTR>(Text);"))
        self.assertEqual(6, source.count("item.pszText = const_cast<PWSTR>(Text);"))
        self.assertEqual(2, source.count("group.pszHeader = const_cast<PWSTR>(Text);"))
        self.assertEqual(1, len(re.findall(r"LONG\s+PhAddListViewItemRaw\s*\(", source)))
        self.assertRegex(source, r"PhAddListViewItemRaw[\s\S]*?PhpAddListViewItem\(\s*ListViewHandle\s*,\s*Index\s*,\s*Text\s*,\s*Param\s*\)")


if __name__ == "__main__":
    unittest.main()
