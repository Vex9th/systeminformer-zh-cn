#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SOURCE_PATH = REPO_ROOT / "SystemInformer" / "mainwnd.c"
RESOURCE_DATA = (
    ("IDS_PH_MAINWND_MENU_COMPUTER", 2749, "&Computer", "计算机(&C)"),
    ("IDS_PH_MAINWND_MENU_LOCK", 2750, "&Lock", "锁定(&L)"),
    ("IDS_PH_MAINWND_MENU_LOG_OFF", 2751, "Log o&ff", "注销(&F)"),
    ("IDS_PH_MAINWND_MENU_SLEEP", 2752, "&Sleep", "睡眠(&S)"),
    ("IDS_PH_MAINWND_MENU_HIBERNATE", 2753, "&Hibernate", "休眠(&H)"),
    ("IDS_PH_MAINWND_MENU_UPDATE_AND_RESTART", 2754, "Update and restart", "更新并重启"),
    ("IDS_PH_MAINWND_MENU_UPDATE_AND_SHUT_DOWN", 2755, "Update and shut down", "更新并关机"),
    ("IDS_PH_MAINWND_MENU_RESTART_COMPUTER", 2756, "R&estart", "重启(&E)"),
    ("IDS_PH_MAINWND_MENU_RESTART_TO_ADVANCED_OPTIONS", 2757, "Restart to advanced options", "重启进入高级选项"),
    ("IDS_PH_MAINWND_MENU_RESTART_TO_BOOT_OPTIONS", 2758, "Restart to boot options", "重启进入引导选项"),
    ("IDS_PH_MAINWND_MENU_RESTART_TO_FIRMWARE_OPTIONS", 2759, "Restart to firmware options", "重启进入固件选项"),
    ("IDS_PH_MAINWND_MENU_WINDOWS_DEFENDER_OFFLINE_SCAN", 2760, "Windows Defender Offline Scan", "Windows Defender 脱机扫描"),
    ("IDS_PH_MAINWND_MENU_SHUT_DOWN", 2761, "Shu&t down", "关机(&T)"),
    ("IDS_PH_MAINWND_MENU_HYBRID_SHUT_DOWN", 2762, "H&ybrid shut down", "混合关机(&Y)"),
    ("IDS_PH_MAINWND_MENU_RESTART_NATIVE", 2763, "R&estart (Native)", "重启(&E)（原生）"),
    ("IDS_PH_MAINWND_MENU_SHUT_DOWN_NATIVE", 2764, "Shu&t down (Native)", "关机(&T)（原生）"),
    ("IDS_PH_MAINWND_MENU_RESTART_CRITICAL", 2765, "R&estart (Critical)", "重启(&E)（强制）"),
    ("IDS_PH_MAINWND_MENU_SHUT_DOWN_CRITICAL", 2766, "Shu&t down (Critical)", "关机(&T)（强制）"),
    ("IDS_PH_MAINWND_MENU_RUN_SHORTCUT", 2767, "&Run...\\bCtrl+R", "运行(&R)...\\bCtrl+R"),
    ("IDS_PH_MAINWND_MENU_RUN_AS_SHORTCUT", 2768, "Run &as...\\bCtrl+Shift+R", "运行身份(&A)...\\bCtrl+Shift+R"),
    ("IDS_PH_MAINWND_MENU_RUN_AS_PACKAGE_SHORTCUT", 2769, "Run as &package...\\bCtrl+Shift+P", "以应用包身份运行(&P)...\\bCtrl+Shift+P"),
    ("IDS_PH_MAINWND_MENU_SHOW_DETAILS_FOR_ALL_PROCESSES", 2770, "Show &details for all processes", "显示所有进程的详细信息(&D)"),
    ("IDS_PH_MAINWND_MENU_SAVE_SHORTCUT", 2771, "&Save...\\bCtrl+S", "保存(&S)...\\bCtrl+S"),
    ("IDS_PH_MAINWND_MENU_FIND_HANDLES_OR_DLLS_SHORTCUT", 2772, "&Find handles or DLLs...\\bCtrl+F", "查找句柄或 DLL(&F)...\\bCtrl+F"),
    ("IDS_PH_MAINWND_MENU_OPTIONS", 2773, "&Options...", "选项(&O)..."),
    ("IDS_PH_MAINWND_MENU_EXIT", 2774, "E&xit", "退出(&X)"),
    ("IDS_PH_MAINWND_MENU_SYSTEM_INFORMATION_SHORTCUT", 2775, "System &information\\bCtrl+I", "系统信息(&I)\\bCtrl+I"),
    ("IDS_PH_MAINWND_MENU_TRAY_ICONS", 2776, "&Tray icons", "托盘图标(&T)"),
    ("IDS_PH_MAINWND_MENU_SECTION_PLACEHOLDER", 2777, "<section placeholder>", "<section placeholder>"),
    ("IDS_PH_MAINWND_MENU_ALWAYS_ON_TOP", 2778, "&Always on top", "始终置顶(&A)"),
    ("IDS_PH_MAINWND_MENU_OPACITY", 2779, "&Opacity", "不透明度(&O)"),
    ("IDS_PH_MAINWND_MENU_OPAQUE", 2780, "&Opaque", "不透明(&O)"),
    ("IDS_PH_MAINWND_MENU_REFRESH_SHORTCUT", 2781, "&Refresh\\bF5", "刷新(&R)\\bF5"),
    ("IDS_PH_MAINWND_MENU_REFRESH_INTERVAL", 2782, "Refresh i&nterval", "刷新间隔(&N)"),
    ("IDS_PH_MAINWND_MENU_FAST_0_5S", 2783, "&Fast (0.5s)", "快速(&F) (0.5s)"),
    ("IDS_PH_MAINWND_MENU_NORMAL_1S", 2784, "&Normal (1s)", "正常(&N) (1s)"),
    ("IDS_PH_MAINWND_MENU_BELOW_NORMAL_2S", 2785, "&Below normal (2s)", "低于正常(&B) (2s)"),
    ("IDS_PH_MAINWND_MENU_SLOW_5S", 2786, "&Slow (5s)", "慢速(&S) (5s)"),
    ("IDS_PH_MAINWND_MENU_VERY_SLOW_10S", 2787, "&Very slow (10s)", "极慢(&V) (10s)"),
    ("IDS_PH_MAINWND_MENU_REFRESH_AUTOMATICALLY_SHORTCUT", 2788, "Refresh a&utomatically\\bF6", "自动刷新(&U)\\bF6"),
    ("IDS_PH_MAINWND_MENU_CREATE_SERVICE", 2789, "&Create service...", "创建服务(&C)..."),
    ("IDS_PH_MAINWND_MENU_CREATE_LIVE_DUMP", 2790, "&Create live dump...", "创建实时转储(&C)..."),
    ("IDS_PH_MAINWND_MENU_INSPECT_EXECUTABLE_FILE", 2791, "Inspect e&xecutable file...", "检查可执行文件(&X)..."),
    ("IDS_PH_MAINWND_MENU_SEARCH_THREAD_STACKS", 2792, "&Search thread stacks", "搜索线程堆栈(&S)"),
    ("IDS_PH_MAINWND_MENU_ZOMBIE_PROCESSES", 2793, "&Zombie processes", "僵尸进程(&Z)"),
    ("IDS_PH_MAINWND_MENU_PAGEFILES", 2794, "&Pagefiles", "页面文件(&P)"),
    ("IDS_PH_MAINWND_MENU_ENVIRONMENT_VARIABLES", 2795, "&Environment variables", "环境变量(&E)"),
    ("IDS_PH_MAINWND_MENU_PROCESS_MONITOR", 2796, "&Process monitor", "进程监视器(&P)"),
    ("IDS_PH_MAINWND_MENU_START_TASK_MANAGER", 2797, "Start &Task Manager", "启动任务管理器(&T)"),
    ("IDS_PH_MAINWND_MENU_START_RESOURCE_MONITOR", 2798, "Start &Resource Monitor", "启动资源监视器(&R)"),
    ("IDS_PH_MAINWND_MENU_START_PERFORMANCE_MONITOR", 2799, "Start &Performance Monitor", "启动性能监视器(&P)"),
    ("IDS_PH_MAINWND_MENU_TERMINATE_WSL_PROCESSES", 2800, "T&erminate WSL processes", "终止 WSL 进程(&E)"),
    ("IDS_PH_MAINWND_MENU_PERMISSIONS", 2801, "&Permissions", "权限(&P)"),
    ("IDS_PH_MAINWND_MENU_CURRENT_POWER_SCHEME", 2802, "Current Power Scheme", "当前电源计划"),
    ("IDS_PH_MAINWND_MENU_SERVICE_CONTROL_MANAGER", 2803, "Service Control Manager", "服务控制管理器"),
    ("IDS_PH_MAINWND_MENU_TERMINAL_SERVER_LISTENER", 2804, "Terminal Server Listener", "终端服务器侦听程序"),
    ("IDS_PH_MAINWND_MENU_WMI_ROOT_NAMESPACE", 2805, "WMI Root Namespace", "WMI 根命名空间"),
    ("IDS_PH_MAINWND_MENU_COM_ACCESS_PERMISSIONS", 2806, "COM Access Permissions", "COM 访问权限"),
    ("IDS_PH_MAINWND_MENU_COM_ACCESS_RESTRICTIONS", 2807, "COM Access Restrictions", "COM 访问限制"),
    ("IDS_PH_MAINWND_MENU_COM_LAUNCH_PERMISSIONS", 2808, "COM Launch Permissions", "COM 启动权限"),
    ("IDS_PH_MAINWND_MENU_COM_LAUNCH_RESTRICTIONS", 2809, "COM Launch Restrictions", "COM 启动限制"),
    ("IDS_PH_MAINWND_MENU_CURRENT_WINDOW_DESKTOP", 2810, "Current Window Desktop", "当前窗口桌面"),
    ("IDS_PH_MAINWND_MENU_CURRENT_WINDOW_STATION", 2811, "Current Window Station", "当前窗口站"),
    ("IDS_PH_MAINWND_MENU_USER_LIST", 2812, "User list...", "用户列表..."),
    ("IDS_PH_MAINWND_MENU_LOG_SHORTCUT", 2813, "&Log\\bCtrl+L", "日志(&L)\\bCtrl+L"),
    ("IDS_PH_MAINWND_MENU_DEBUG_CONSOLE", 2814, "Debu&g console", "调试控制台(&G)"),
    ("IDS_PH_MAINWND_MENU_ABOUT", 2815, "&About", "关于(&A)"),
    ("IDS_PH_MAINWND_MENU_SYSTEM", 2816, "&System", "系统(&S)"),
    ("IDS_PH_MAINWND_MENU_VIEW", 2817, "&View", "查看(&V)"),
    ("IDS_PH_MAINWND_MENU_TOOLS", 2818, "&Tools", "工具(&T)"),
    ("IDS_PH_MAINWND_MENU_USERS", 2819, "&Users", "用户(&U)"),
    ("IDS_PH_MAINWND_MENU_HELP", 2820, "&Help", "帮助(&H)"),
    ("IDS_PH_MAINWND_MENU_NOTIFICATIONS", 2821, "N&otifications", "通知(&O)"),
    ("IDS_PH_MAINWND_MENU_ENABLE_ALL", 2822, "&Enable all", "全部启用(&E)"),
    ("IDS_PH_MAINWND_MENU_DISABLE_ALL", 2823, "&Disable all", "全部禁用(&D)"),
    ("IDS_PH_MAINWND_MENU_NEW_PROCESSES", 2824, "New &processes", "新进程(&P)"),
    ("IDS_PH_MAINWND_MENU_TERMINATED_PROCESSES", 2825, "T&erminated processes", "已终止的进程(&E)"),
    ("IDS_PH_MAINWND_MENU_NEW_SERVICES", 2826, "New &services", "新服务(&S)"),
    ("IDS_PH_MAINWND_MENU_STARTED_SERVICES", 2827, "St&arted services", "已启动的服务(&A)"),
    ("IDS_PH_MAINWND_MENU_STOPPED_SERVICES", 2828, "St&opped services", "已停止的服务(&O)"),
    ("IDS_PH_MAINWND_MENU_DELETED_SERVICES", 2829, "&Deleted services", "已删除的服务(&D)"),
    ("IDS_PH_MAINWND_MENU_MODIFIED_SERVICES", 2830, "&Modified services", "已修改的服务(&M)"),
    ("IDS_PH_MAINWND_MENU_ARRIVED_DEVICES", 2831, "&Arrived devices", "新到设备(&A)"),
    ("IDS_PH_MAINWND_MENU_REMOVED_DEVICES", 2832, "&Removed devices", "已移除的设备(&R)"),
    ("IDS_PH_MAINWND_MENU_SETTINGS", 2833, "Settings", "设置"),
    ("IDS_PH_MAINWND_MENU_ENABLE_INITIALIZATION_DELAY", 2834, "Enable initialization delay", "启用初始化延迟"),
    ("IDS_PH_MAINWND_MENU_ENABLE_PERSISTENT_LAYOUT", 2835, "Enable persistent layout", "启用持久布局"),
    ("IDS_PH_MAINWND_MENU_ENABLE_TRANSPARENT_ICONS", 2836, "Enable transparent icons", "启用透明图标"),
    ("IDS_PH_MAINWND_MENU_ENABLE_SINGLE_CLICK_ICONS", 2837, "Enable single click icons", "启用单击图标"),
    ("IDS_PH_MAINWND_MENU_RESET_PERSISTENT_LAYOUT", 2838, "Reset persistent layout", "重置持久布局"),
    ("IDS_PH_MAINWND_MENU_SHOW_HIDE_SYSTEM_INFORMER", 2839, "&Show/Hide System Informer", "显示/隐藏 sys_info(&S)"),
    ("IDS_PH_MAINWND_MENU_SYSTEM_INFORMATION", 2840, "System &information", "系统信息(&I)"),
    ("IDS_PH_MAINWND_MENU_PROCESSES", 2841, "&Processes", "进程(&P)"),
    ("IDS_PH_MAINWND_MENU_PRIORITY_CLASS", 2842, "&Priority class", "优先级类(&P)"),
    ("IDS_PH_MAINWND_MENU_REAL_TIME", 2843, "&Real time", "实时(&R)"),
    ("IDS_PH_MAINWND_MENU_HIGH", 2844, "&High", "高(&H)"),
    ("IDS_PH_MAINWND_MENU_ABOVE_NORMAL", 2845, "&Above normal", "高于正常(&A)"),
    ("IDS_PH_MAINWND_MENU_NORMAL", 2846, "&Normal", "正常(&N)"),
    ("IDS_PH_MAINWND_MENU_BELOW_NORMAL", 2847, "&Below normal", "低于正常(&B)"),
    ("IDS_PH_MAINWND_MENU_IDLE", 2848, "&Idle", "空闲(&I)"),
    ("IDS_PH_MAINWND_MENU_I_O_PRIORITY", 2849, "&I/O priority", "I/O 优先级(&I)"),
    ("IDS_PH_MAINWND_MENU_LOW", 2850, "&Low", "低(&L)"),
    ("IDS_PH_MAINWND_MENU_VERY_LOW", 2851, "&Very low", "非常低(&V)"),
    ("IDS_PH_MAINWND_MENU_TERMINATE", 2852, "T&erminate", "终止(&E)"),
    ("IDS_PH_MAINWND_MENU_SUSPEND", 2853, "&Suspend", "挂起(&S)"),
    ("IDS_PH_MAINWND_MENU_RESUME", 2854, "Res&ume", "恢复(&U)"),
    ("IDS_PH_MAINWND_MENU_RESTART_PROCESS", 2855, "Res&tart", "重启(&T)"),
    ("IDS_PH_MAINWND_MENU_PROPERTIES", 2856, "P&roperties", "属性(&R)"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("mainwnd_menu_audit", path)
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


class MainWindowMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(SOURCE_PATH.read_text(encoding="utf-8-sig"))

    def test_new_resources_are_exact_contiguous_and_bilingual(self) -> None:
        root = REPO_ROOT / "SystemInformer"
        header = (root / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(root / "SystemInformer.rc")
        chinese = parse_stringtable(root / "SystemInformer.zh-cn.rc")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)$",
                header,
            )
        }

        self.assertEqual([row[1] for row in RESOURCE_DATA], list(range(2749, 2857)))
        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(len(english), 957)
        self.assertEqual(len(chinese), 957)
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_CONFIRM_USER_OBJECT$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2957$")

    def test_resource_menu_helper_transfers_owned_copy_to_menu(self) -> None:
        helper = re.search(
            r"static\s+PPH_EMENU_ITEM\s+PhpCreateResourceEMenuItem\s*\([^{}]*\)\s*\{(.*?)\n\}",
            self.source,
            re.S,
        )
        self.assertIsNotNone(helper)
        body = helper.group(1)
        load = body.index("PhLoadUiString(PhInstanceHandle, ResourceId, NULL)")
        duplicate = body.index("PhDuplicateStringZ(PhGetStringOrEmpty(menuText))")
        release = body.index("PhClearReference(&menuText)")
        sink = body.index("PhCreateEMenuItem(")
        self.assertLess(load, duplicate)
        self.assertLess(duplicate, release)
        self.assertLess(release, sink)
        self.assertIn("Flags | PH_EMENU_TEXT_OWNED", body)
        self.assertIn("Context", body)

    def test_all_expected_menu_routes_use_native_resource_ids(self) -> None:
        actual = Counter(re.findall(
            r"PhpCreateResourceEMenuItem\([^;]*?\b(IDS_PH_MAINWND_MENU_[A-Z0-9_]+)\b[^;]*?\)",
            self.source,
            re.S,
        ))
        expected = Counter(row[0] for row in RESOURCE_DATA)
        expected["IDS_PH_MAINWND_MENU_EXIT"] = 2
        expected["IDS_PH_MAINWND_MENU_HIGH"] = 2
        expected["IDS_PH_MAINWND_MENU_NORMAL"] = 2
        self.assertEqual(actual, expected)
        self.assertEqual(sum(actual.values()), 111)

    def test_mainwnd_runtime_menu_category_is_empty(self) -> None:
        entries = []
        self.audit.scan_c_file(str(SOURCE_PATH), entries)
        remaining = [
            entry for entry in entries
            if entry["category"] == "c_emenu"
        ]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
