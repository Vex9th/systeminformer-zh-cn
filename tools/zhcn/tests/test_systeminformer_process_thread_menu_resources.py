#!/usr/bin/env python3

import collections
import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_MENU_BOOST", 2984, "&Boost", "提升(&B)"),
    ("IDS_PH_MENU_CLOSE_WINDOW", 2985, "&Close", "关闭(&C)"),
    ("IDS_PH_MENU_COLLAPSE_ALL", 2986, "&Collapse all", "全部折叠(&C)"),
    ("IDS_PH_MENU_PROCESS_CRITICAL", 2987, "&Critical", "关键进程(&C)"),
    ("IDS_PH_MENU_DUMP_CUSTOM", 2988, "&Custom...", "自定义(&C)..."),
    ("IDS_PH_MENU_DETACH_FROM_DEBUGGER", 2989, "&Detach from debugger", "从调试器分离(&D)"),
    ("IDS_PH_MENU_EXPAND_ALL", 2990, "&Expand all", "全部展开(&E)"),
    ("IDS_PH_MENU_THREAD_FREEZE", 2991, "&Freeze", "冻结(&F)"),
    ("IDS_PH_MENU_DUMP_FULL", 2992, "&Full...", "完整(&F)..."),
    ("IDS_PH_MENU_HIDE_OTHER_USER_PROCESSES", 2993, "&Hide processes from other users", "隐藏其他用户的进程(&H)"),
    ("IDS_PH_MENU_INSPECT_SHORTCUT", 2994, r"&Inspect\bEnter", r"检查(&I)\bEnter"),
    ("IDS_PH_MENU_DUMP_LIMITED", 2995, "&Limited...", "有限(&L)..."),
    ("IDS_PH_MENU_DUMP_MINIMAL", 2996, "&Minimal...", "最小(&M)..."),
    ("IDS_PH_MENU_MISCELLANEOUS", 2997, "&Miscellaneous", "杂项(&M)"),
    ("IDS_PH_MENU_DUMP_NORMAL", 2998, "&Normal...", "正常(&N)..."),
    ("IDS_PH_MENU_WINDOW_RESTORE", 2999, "&Restore", "还原(&R)"),
    ("IDS_PH_MENU_RUN_AS", 3000, "&Run as...", "运行身份(&R)..."),
    ("IDS_PH_MENU_THREAD_THAW", 3001, "&Thaw", "解冻(&T)"),
    ("IDS_PH_MENU_TOKEN", 3002, "&Token", "令牌(&T)"),
    ("IDS_PH_MENU_WINDOW", 3003, "&Window", "窗口(&W)"),
    ("IDS_PH_MENU_ACTIVITY_MODERATION", 3004, "Activity moderation", "活动调节"),
    ("IDS_PH_MENU_ANALYZE", 3005, "Analy&ze", "分析(&Z)"),
    ("IDS_PH_MENU_WINDOW_BRING_TO_FRONT", 3006, "Bring to &front", "置于前台(&F)"),
    ("IDS_PH_MENU_CREATE_DUMP_FILE", 3007, "Create dump fi&le", "创建转储文件(&L)"),
    ("IDS_PH_MENU_CREATE_LIVE_KERNEL_DUMP_FILE", 3008, "Create live kernel dump fi&le", "创建实时内核转储文件(&L)"),
    ("IDS_PH_MENU_THREAD_CRITICAL", 3009, "Critical", "关键"),
    ("IDS_PH_MENU_DEBUG", 3010, "De&bug", "调试(&B)"),
    ("IDS_PH_MENU_EFFICIENCY_MODE", 3011, "Efficiency mode", "效率模式"),
    ("IDS_PH_MENU_EXECUTION_REQUIRED", 3012, "Execution required", "需要执行"),
    ("IDS_PH_MENU_FLUSH_HEAPS", 3013, "Flush heaps", "刷新堆"),
    ("IDS_PH_MENU_PROCESS_FREEZE", 3014, "Freeze", "冻结"),
    ("IDS_PH_MENU_GDI_HANDLES", 3015, "GDI &handles...", "GDI 句柄(&H)..."),
    ("IDS_PH_MENU_HEAPS", 3016, "Heaps...", "堆..."),
    ("IDS_PH_MENU_HIDE_SYSTEM_PROCESSES", 3017, "Hide &system processes", "隐藏系统进程(&S)"),
    ("IDS_PH_MENU_HIDE_GUI", 3018, "Hide gui", "隐藏 GUI 线程"),
    ("IDS_PH_MENU_HIDE_SIGNED_PROCESSES", 3019, "Hide si&gned processes", "隐藏已签名进程(&G)"),
    ("IDS_PH_MENU_HIDE_SUSPENDED", 3020, "Hide suspended", "隐藏挂起线程"),
    ("IDS_PH_MENU_HIGHLIGHT_ALERT_BY_THREAD_ID", 3021, "Highlight alert by thread ID", "高亮按线程 ID 警报"),
    ("IDS_PH_MENU_HIGHLIGHT_DELAY_EXECUTION", 3022, "Highlight delay execution", "高亮延迟执行"),
    ("IDS_PH_MENU_HIGHLIGHT_EXECUTIVE", 3023, "Highlight executive", "高亮执行体"),
    ("IDS_PH_MENU_HIGHLIGHT_GUI", 3024, "Highlight gui", "高亮 GUI 线程"),
    ("IDS_PH_MENU_HIGHLIGHT_QUEUE", 3025, "Highlight queue", "高亮队列等待"),
    ("IDS_PH_MENU_HIGHLIGHT_SUSPENDED", 3026, "Highlight suspended", "高亮挂起线程"),
    ("IDS_PH_MENU_HIGHLIGHT_USER_REQUEST", 3027, "Highlight user request", "高亮用户请求"),
    ("IDS_PH_MENU_LOAD_COLUMN_SET", 3028, "Loa&d column set", "加载列集(&D)"),
    ("IDS_PH_MENU_LOCKS", 3029, "Locks...", "锁..."),
    ("IDS_PH_MENU_WINDOW_MAXIMIZE", 3030, "M&aximize", "最大化(&A)"),
    ("IDS_PH_MENU_WINDOW_MINIMIZE", 3031, "M&inimize", "最小化(&I)"),
    ("IDS_PH_MENU_MODIFIED_PAGES", 3032, "Modified pages...", "已修改页..."),
    ("IDS_PH_MENU_ORGANIZE_COLUMN_SETS", 3033, "Organi&ze column sets...", "管理列集(&Z)..."),
    ("IDS_PH_MENU_PERMISSIONS", 3034, "Per&missions", "权限(&M)"),
    ("IDS_PH_MENU_REDUCE_WORKING_SET", 3035, "Reduce working &set", "缩减工作集(&S)"),
    ("IDS_PH_MENU_RESUME_TREE", 3036, "Resume tree", "恢复进程树"),
    ("IDS_PH_MENU_RUN_AS_THIS_USER", 3037, "Run &as this user...", "以该用户身份运行(&A)..."),
    ("IDS_PH_MENU_SAVE_COLUMN_SET", 3038, "Sa&ve column set...", "保存列集(&V)..."),
    ("IDS_PH_MENU_SAVE", 3039, "Save...", "保存..."),
    ("IDS_PH_MENU_SCROLL_TO_NEW_PROCESSES", 3040, "Scrol&l to new processes", "滚动到新进程(&L)"),
    ("IDS_PH_MENU_SEARCH_ONLINE_SHORTCUT", 3041, r"Search &online\bCtrl+M", r"在线搜索(&O)\bCtrl+M"),
    ("IDS_PH_MENU_SECURITY", 3042, "Security", "安全"),
    ("IDS_PH_MENU_SHOW_CPU_BELOW_POINT_ZERO_ONE", 3043, "Show CPU &below 0.01", "显示低于 0.01 的 CPU(&B)"),
    ("IDS_PH_MENU_SORT_CHILD_PROCESSES", 3044, "Sort &child processes", "对子进程排序(&C)"),
    ("IDS_PH_MENU_SORT_ROOT_PROCESSES", 3045, "Sort &root processes", "对根进程排序(&R)"),
    ("IDS_PH_MENU_SUSPEND_TREE", 3046, "Suspend tree", "挂起进程树"),
    ("IDS_PH_MENU_TERMINATE_SHORTCUT", 3047, r"T&erminate\bDel", r"终止(&E)\bDel"),
    ("IDS_PH_MENU_TERMINATE_TREE_SHORTCUT", 3048, r"Terminate tree\bShift+Del", r"终止进程树\bShift+Del"),
    ("IDS_PH_MENU_PROCESS_THAW", 3049, "Thaw", "解冻"),
    ("IDS_PH_MENU_VIRTUALIZATION", 3050, "Virtuali&zation", "虚拟化(&Z)"),
)

REUSED_RESOURCES = (
    ("IDS_PH_MAINWND_MENU_SUSPEND", "&Suspend", "挂起(&S)"),
    ("IDS_PH_GROUP_PROCESSES", "Processes", "进程"),
    ("IDS_PH_MAINWND_MENU_RESTART_PROCESS", "Res&tart", "重启(&T)"),
    ("IDS_PH_MAINWND_MENU_RESUME", "Res&ume", "恢复(&U)"),
)

RUNTIME_COMPATIBILITY_KEYS = {"&Boost", "&Suspend", "Res&ume", "Critical", "Heaps...", "Save..."}

PROCESS_ACTION_ROUTES = (
    ("ID_PROCESS_TERMINATE", "IDS_PH_MENU_TERMINATE_SHORTCUT"),
    ("ID_PROCESS_TERMINATETREE", "IDS_PH_MENU_TERMINATE_TREE_SHORTCUT"),
    ("ID_PROCESS_SUSPEND", "IDS_PH_MAINWND_MENU_SUSPEND"),
    ("ID_PROCESS_SUSPENDTREE", "IDS_PH_MENU_SUSPEND_TREE"),
    ("ID_PROCESS_RESUME", "IDS_PH_MAINWND_MENU_RESUME"),
    ("ID_PROCESS_RESUMETREE", "IDS_PH_MENU_RESUME_TREE"),
    ("ID_PROCESS_FREEZE", "IDS_PH_MENU_PROCESS_FREEZE"),
    ("ID_PROCESS_THAW", "IDS_PH_MENU_PROCESS_THAW"),
    ("ID_PROCESS_RESTART", "IDS_PH_MAINWND_MENU_RESTART_PROCESS"),
)

PROCESS_DUMP_ROUTES = (
    ("ID_PROCESS_CREATEDUMPFILE", "IDS_PH_MENU_CREATE_LIVE_KERNEL_DUMP_FILE"),
    ("ID_PROCESS_DUMP_MINIMAL", "IDS_PH_MENU_DUMP_MINIMAL"),
    ("ID_PROCESS_DUMP_NORMAL", "IDS_PH_MENU_DUMP_NORMAL"),
    ("ID_PROCESS_DUMP_FULL", "IDS_PH_MENU_DUMP_FULL"),
    ("ID_PROCESS_DUMP_CUSTOM", "IDS_PH_MENU_DUMP_CUSTOM"),
    ("ID_PROCESS_CREATEDUMPFILE", "IDS_PH_MENU_CREATE_DUMP_FILE"),
    ("ID_PROCESS_DUMP_MINIMAL", "IDS_PH_MENU_DUMP_MINIMAL"),
    ("ID_PROCESS_DUMP_LIMITED", "IDS_PH_MENU_DUMP_LIMITED"),
    ("ID_PROCESS_DUMP_NORMAL", "IDS_PH_MENU_DUMP_NORMAL"),
    ("ID_PROCESS_DUMP_FULL", "IDS_PH_MENU_DUMP_FULL"),
    ("ID_PROCESS_DUMP_CUSTOM", "IDS_PH_MENU_DUMP_CUSTOM"),
)

PROCESS_MISC_ROUTES = (
    ("ID_PROCESS_MISCELLANEOUS", "IDS_PH_MENU_MISCELLANEOUS"),
    ("ID_MISCELLANEOUS_ACTIVITY", "IDS_PH_MENU_ACTIVITY_MODERATION"),
    ("ID_MISCELLANEOUS_SETCRITICAL", "IDS_PH_MENU_PROCESS_CRITICAL"),
    ("ID_MISCELLANEOUS_DETACHFROMDEBUGGER", "IDS_PH_MENU_DETACH_FROM_DEBUGGER"),
    ("ID_MISCELLANEOUS_ECOMODE", "IDS_PH_MENU_EFFICIENCY_MODE"),
    ("ID_MISCELLANEOUS_EXECUTIONREQUIRED", "IDS_PH_MENU_EXECUTION_REQUIRED"),
    ("ID_MISCELLANEOUS_GDIHANDLES", "IDS_PH_MENU_GDI_HANDLES"),
    ("ID_MISCELLANEOUS_HEAPS", "IDS_PH_MENU_HEAPS"),
    ("ID_MISCELLANEOUS_LOCKS", "IDS_PH_MENU_LOCKS"),
    ("ID_MISCELLANEOUS_FLUSHHEAPS", "IDS_PH_MENU_FLUSH_HEAPS"),
    ("ID_MISCELLANEOUS_PAGESMODIFIED", "IDS_PH_MENU_MODIFIED_PAGES"),
    ("ID_MISCELLANEOUS_REDUCEWORKINGSET", "IDS_PH_MENU_REDUCE_WORKING_SET"),
    ("ID_MISCELLANEOUS_RUNAS", "IDS_PH_MENU_RUN_AS"),
    ("ID_MISCELLANEOUS_RUNASTHISUSER", "IDS_PH_MENU_RUN_AS_THIS_USER"),
    ("ID_PROCESS_VIRTUALIZATION", "IDS_PH_MENU_VIRTUALIZATION"),
)

EXPECTED_ROUTES = {
    "mwpgproc.c": (
        ("0", "IDS_PH_GROUP_PROCESSES"),
        ("ID_VIEW_COLLAPSEALL", "IDS_PH_MENU_COLLAPSE_ALL"),
        ("ID_VIEW_EXPANDALL", "IDS_PH_MENU_EXPAND_ALL"),
        ("ID_VIEW_HIDEPROCESSESFROMOTHERUSERS", "IDS_PH_MENU_HIDE_OTHER_USER_PROCESSES"),
        ("ID_VIEW_HIDESIGNEDPROCESSES", "IDS_PH_MENU_HIDE_SIGNED_PROCESSES"),
        ("ID_VIEW_HIDEMICROSOFTPROCESSES", "IDS_PH_MENU_HIDE_SYSTEM_PROCESSES"),
        ("ID_VIEW_SCROLLTONEWPROCESSES", "IDS_PH_MENU_SCROLL_TO_NEW_PROCESSES"),
        ("ID_VIEW_SORTCHILDPROCESSES", "IDS_PH_MENU_SORT_CHILD_PROCESSES"),
        ("ID_VIEW_SORTROOTPROCESSES", "IDS_PH_MENU_SORT_ROOT_PROCESSES"),
        ("ID_VIEW_SHOWCPUBELOW001", "IDS_PH_MENU_SHOW_CPU_BELOW_POINT_ZERO_ONE"),
        ("ID_VIEW_ORGANIZECOLUMNSETS", "IDS_PH_MENU_ORGANIZE_COLUMN_SETS"),
        ("ID_VIEW_SAVECOLUMNSET", "IDS_PH_MENU_SAVE_COLUMN_SET"),
        ("0", "IDS_PH_MENU_LOAD_COLUMN_SET"),
    )
    + PROCESS_ACTION_ROUTES
    + PROCESS_DUMP_ROUTES
    + (("ID_PROCESS_DEBUG", "IDS_PH_MENU_DEBUG"),)
    + PROCESS_MISC_ROUTES
    + (
        ("ID_PROCESS_WINDOW", "IDS_PH_MENU_WINDOW"),
        ("ID_WINDOW_BRINGTOFRONT", "IDS_PH_MENU_WINDOW_BRING_TO_FRONT"),
        ("ID_WINDOW_RESTORE", "IDS_PH_MENU_WINDOW_RESTORE"),
        ("ID_WINDOW_MINIMIZE", "IDS_PH_MENU_WINDOW_MINIMIZE"),
        ("ID_WINDOW_MAXIMIZE", "IDS_PH_MENU_WINDOW_MAXIMIZE"),
        ("ID_WINDOW_CLOSE", "IDS_PH_MENU_CLOSE_WINDOW"),
        ("ID_PROCESS_SEARCHONLINE", "IDS_PH_MENU_SEARCH_ONLINE_SHORTCUT"),
    ),
    "procprp.c": PROCESS_ACTION_ROUTES
    + PROCESS_DUMP_ROUTES
    + (("ID_PROCESS_DEBUG", "IDS_PH_MENU_DEBUG"),)
    + PROCESS_MISC_ROUTES
    + (
        ("ID_PROCESS_SEARCHONLINE", "IDS_PH_MENU_SEARCH_ONLINE_SHORTCUT"),
        ("ID_HANDLE_SECURITY", "IDS_PH_MENU_SECURITY"),
    ),
    "prpgthrd.c": (
        ("ID_THREAD_INSPECT", "IDS_PH_MENU_INSPECT_SHORTCUT"),
        ("ID_THREAD_TERMINATE", "IDS_PH_MENU_TERMINATE_SHORTCUT"),
        ("ID_THREAD_SUSPEND", "IDS_PH_MAINWND_MENU_SUSPEND"),
        ("ID_THREAD_RESUME", "IDS_PH_MAINWND_MENU_RESUME"),
        ("ID_THREAD_FREEZE", "IDS_PH_MENU_THREAD_FREEZE"),
        ("ID_THREAD_THAW", "IDS_PH_MENU_THREAD_THAW"),
        ("ID_ANALYZE_WAIT", "IDS_PH_MENU_ANALYZE"),
        ("ID_THREAD_BOOST", "IDS_PH_MENU_BOOST"),
        ("ID_THREAD_CRITICAL", "IDS_PH_MENU_THREAD_CRITICAL"),
        ("ID_THREAD_PERMISSIONS", "IDS_PH_MENU_PERMISSIONS"),
        ("ID_THREAD_TOKEN", "IDS_PH_MENU_TOKEN"),
        ("PH_THREAD_TREELIST_MENUITEM_HIDE_SUSPENDED", "IDS_PH_MENU_HIDE_SUSPENDED"),
        ("PH_THREAD_TREELIST_MENUITEM_HIDE_GUITHREADS", "IDS_PH_MENU_HIDE_GUI"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_SUSPENDED", "IDS_PH_MENU_HIGHLIGHT_SUSPENDED"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_DELAYEXECUTION", "IDS_PH_MENU_HIGHLIGHT_DELAY_EXECUTION"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_USERREQUEST", "IDS_PH_MENU_HIGHLIGHT_USER_REQUEST"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_ALERTBYTHREADID", "IDS_PH_MENU_HIGHLIGHT_ALERT_BY_THREAD_ID"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_QUEUE", "IDS_PH_MENU_HIGHLIGHT_QUEUE"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_EXECUTIVE", "IDS_PH_MENU_HIGHLIGHT_EXECUTIVE"),
        ("PH_THREAD_TREELIST_MENUITEM_HIGHLIGHT_GUITHREADS", "IDS_PH_MENU_HIGHLIGHT_GUI"),
        ("PH_THREAD_TREELIST_MENUITEM_SAVE", "IDS_PH_MENU_SAVE"),
    ),
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("process_thread_menu_audit", path)
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


class SystemInformerProcessThreadMenuResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def test_resource_contract_and_json_ownership_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))

        for symbol, en, zh in REUSED_RESOURCES:
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))

        for _symbol, _resource_id, en, zh in NEW_RESOURCES:
            json_en = en.replace(r"\b", "\b")
            json_zh = zh.replace(r"\b", "\b")
            owner = "strings" if json_en in RUNTIME_COMPATIBILITY_KEYS else "native_strings"
            other = "native_strings" if owner == "strings" else "strings"
            self.assertEqual(json_zh, data[owner].get(json_en), en)
            self.assertNotIn(json_en, data[other], en)

        for _symbol, en, zh in REUSED_RESOURCES:
            owner = "strings" if en in RUNTIME_COMPATIBILITY_KEYS else "native_strings"
            other = "native_strings" if owner == "strings" else "strings"
            self.assertEqual(zh, data[owner].get(en), en)
            self.assertNotIn(en, data[other], en)

        self.assertEqual(1340, len(english))
        self.assertEqual(1340, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_STRINGS$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3340$")

    def test_all_115_routes_are_resource_backed_and_no_raw_menu_remains(self) -> None:
        target_symbols = {row[0] for row in NEW_RESOURCES} | {row[0] for row in REUSED_RESOURCES}
        total = 0

        for file_name, expected in EXPECTED_ROUTES.items():
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            actual = []

            for _name, arguments, _spans, _start in self.audit.find_calls(source, {"PhCreateEMenuItem"}):
                if len(arguments) < 3:
                    continue
                match = re.fullmatch(
                    r"\s*PhGetApplicationUiString\(\s*(IDS_PH_[A-Z0-9_]+)\s*\)\s*",
                    arguments[2],
                )
                if match and match.group(1) in target_symbols:
                    actual.append((" ".join(arguments[1].split()), match.group(1)))

            self.assertEqual(expected, tuple(actual), file_name)
            total += len(actual)

            entries = []
            self.audit.scan_c_file(str(APP_ROOT / file_name), entries)
            self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"], file_name)

        self.assertEqual(115, total)

    def test_only_six_shared_keys_keep_runtime_ownership(self) -> None:
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        all_keys = {
            en.replace(r"\b", "\b")
            for _symbol, _resource_id, en, _zh in NEW_RESOURCES
        } | {en for _symbol, en, _zh in REUSED_RESOURCES}
        self.assertEqual(RUNTIME_COMPATIBILITY_KEYS, all_keys & data["strings"].keys())

    def test_boost_runtime_compatibility_has_one_cross_module_consumer(self) -> None:
        consumers = []

        for root in (APP_ROOT, REPO_ROOT / "plugins"):
            for path in sorted(root.rglob("*.c")):
                source = self.audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))

                for name, arguments, _spans, _start in self.audit.find_calls(
                    source,
                    {"PhCreateEMenuItem", "PhPluginCreateEMenuItem"},
                ):
                    text_index = 2 if name == "PhCreateEMenuItem" else 3
                    command_index = 1 if name == "PhCreateEMenuItem" else 2

                    if len(arguments) > text_index and arguments[text_index].strip() == 'L"&Boost"':
                        consumers.append(
                            (
                                path.relative_to(REPO_ROOT).as_posix(),
                                name,
                                " ".join(arguments[command_index].split()),
                            )
                        )

        self.assertEqual(
            [("plugins/UserNotes/main.c", "PhPluginCreateEMenuItem", "0")],
            consumers,
        )


if __name__ == "__main__":
    unittest.main()
