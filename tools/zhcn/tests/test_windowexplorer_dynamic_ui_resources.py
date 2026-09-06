#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "WindowExplorer"

NEW_RESOURCES = (
    ("IDS_WE_UNABLE_CREATE_WINDOW", 12122, "Unable to create the window.", "无法创建窗口。"),
    ("IDS_WE_PROCESS_NOT_FOUND", 12123, "The process does not exist.", "该进程不存在。"),
    ("IDS_WE_PROPERTY_NAME_EMPTY", 12124, "The property name is empty.", "属性名称为空。"),
    ("IDS_WE_SEARCH_WINDOWS", 12125, "Search Windows (Ctrl+K)", "搜索窗口 (Ctrl+K)"),
    ("IDS_WE_MENU_BRING_TO_FRONT", 12126, "Bring to front", "移到最前"),
    ("IDS_WE_MENU_RESTORE", 12127, "Restore", "还原"),
    ("IDS_WE_MENU_MINIMIZE", 12128, "Minimize", "最小化"),
    ("IDS_WE_MENU_MAXIMIZE", 12129, "Maximize", "最大化"),
    ("IDS_WE_MENU_DESTROY", 12130, "Destroy", "销毁"),
    ("IDS_WE_MENU_VISIBLE", 12131, "Visible", "可见"),
    ("IDS_WE_MENU_ENABLED", 12132, "Enabled", "已启用"),
    ("IDS_WE_MENU_ALWAYS_ON_TOP", 12133, "Always on top", "置顶"),
    ("IDS_WE_MENU_OPACITY", 12134, "&Opacity", "不透明度(&O)"),
    ("IDS_WE_MENU_OPAQUE", 12135, "&Opaque", "不透明(&O)"),
    ("IDS_WE_MENU_INSPECT", 12136, "&Inspect", "检查(&I)"),
    ("IDS_WE_MENU_DPI", 12137, "DPI", "DPI"),
    ("IDS_WE_MENU_OPEN_FILE_LOCATION", 12138, "Open &file location", "打开文件位置(&F)"),
    ("IDS_WE_MENU_HIGHLIGHT", 12139, "Highlight", "高亮"),
    ("IDS_WE_MENU_GO_TO_PROCESS", 12140, "Go to process...", "转到进程..."),
    ("IDS_WE_MENU_GO_TO_THREAD", 12141, "Go to thread...", "转到线程..."),
    ("IDS_WE_MENU_PROPERTIES", 12142, "Properties", "属性"),
    ("IDS_WE_MENU_COPY_SHORTCUT", 12143, "Copy\\bCtrl+C", "复制\\bCtrl+C"),
    ("IDS_WE_MENU_ENUMERATE_MESSAGE_ONLY", 12144, "Enumerate message-only windows", "枚举仅消息窗口"),
    ("IDS_WE_MENU_ENUMERATE_NON_VISIBLE", 12145, "Enumerate non-visible windows", "枚举不可见窗口"),
    ("IDS_WE_MENU_HIGHLIGHT_MESSAGE_ONLY", 12146, "Highlight message-only windows", "高亮仅消息窗口"),
    ("IDS_WE_MENU_ENABLE_ICONS", 12147, "Enable icons", "启用图标"),
    ("IDS_WE_MENU_SHOW_DESKTOP_WINDOWS", 12148, "Show desktop windows", "显示桌面窗口"),
    ("IDS_WE_MENU_USE_SNAPSHOT_FINDER", 12149, "Use snapshot window finder", "使用快照窗口查找器"),
    ("IDS_WE_MENU_ENUMERATE_WINDOWS", 12150, "Enumerate windows", "枚举窗口"),
    ("IDS_WE_MENU_ENUMERATE_Z_ORDER", 12151, "Enumerate windows by z-order", "按 Z 序枚举窗口"),
    ("IDS_WE_MENU_ENUMERATE_OWNER", 12152, "Enumerate windows by owner", "按所有者枚举窗口"),
    ("IDS_WE_MENU_COPY", 12153, "&Copy", "复制(&C)"),
    ("IDS_WE_MENU_ADD", 12154, "Add", "添加"),
    ("IDS_WE_MENU_EDIT", 12155, "Edit", "编辑"),
    ("IDS_WE_MENU_DELETE", 12156, "Delete", "删除"),
    ("IDS_WE_MENU_PROPERTIES_MNEMONIC", 12157, "&Properties", "属性(&P)"),
    ("IDS_WE_COLUMN_VALUE", 12158, "Value", "值"),
    ("IDS_WE_COLUMN_ALIAS", 12159, "Alias", "别名"),
    ("IDS_WE_COLUMN_HANDLE", 12160, "Handle", "句柄"),
    ("IDS_WE_COLUMN_TEXT", 12161, "Text", "文本"),
    ("IDS_WE_COLUMN_THREAD_ID", 12162, "Thread ID", "线程 ID"),
    ("IDS_WE_COLUMN_PROCESS", 12163, "Process", "进程"),
    ("IDS_WE_COLUMN_MODULE", 12164, "Module", "模块"),
    ("IDS_WE_ACTION_REMOVE", 12165, "remove", "移除"),
    ("IDS_WE_OBJECT_WINDOW_PROPERTY", 12166, "the window property", "该窗口属性"),
    ("IDS_WE_WINDOW_PROPERTY_DELETE_WARNING", 12167, "The window property will be permanently deleted.", "该窗口属性将被永久删除。"),
)

MENU_ROUTES = Counter({
    "IDS_WE_CLOSE": 1,
    "IDS_WE_MENU_BRING_TO_FRONT": 1,
    "IDS_WE_MENU_RESTORE": 1,
    "IDS_WE_MENU_MINIMIZE": 1,
    "IDS_WE_MENU_MAXIMIZE": 1,
    "IDS_WE_MENU_DESTROY": 1,
    "IDS_WE_MENU_VISIBLE": 1,
    "IDS_WE_MENU_ENABLED": 1,
    "IDS_WE_MENU_ALWAYS_ON_TOP": 1,
    "IDS_WE_MENU_OPACITY": 1,
    "IDS_WE_MENU_OPAQUE": 1,
    "IDS_WE_MENU_INSPECT": 1,
    "IDS_WE_MENU_DPI": 1,
    "IDS_WE_MENU_OPEN_FILE_LOCATION": 1,
    "IDS_WE_MENU_HIGHLIGHT": 1,
    "IDS_WE_MENU_GO_TO_PROCESS": 1,
    "IDS_WE_MENU_GO_TO_THREAD": 1,
    "IDS_WE_MENU_PROPERTIES": 1,
    "IDS_WE_MENU_COPY_SHORTCUT": 1,
    "IDS_WE_MENU_ENUMERATE_MESSAGE_ONLY": 2,
    "IDS_WE_MENU_ENUMERATE_NON_VISIBLE": 2,
    "IDS_WE_MENU_HIGHLIGHT_MESSAGE_ONLY": 2,
    "IDS_WE_MENU_ENABLE_ICONS": 2,
    "IDS_WE_MENU_SHOW_DESKTOP_WINDOWS": 2,
    "IDS_WE_MENU_USE_SNAPSHOT_FINDER": 1,
    "IDS_WE_MENU_ENUMERATE_WINDOWS": 2,
    "IDS_WE_MENU_ENUMERATE_Z_ORDER": 2,
    "IDS_WE_MENU_ENUMERATE_OWNER": 2,
    "IDS_WE_MENU_COPY": 6,
    "IDS_WE_MENU_ADD": 1,
    "IDS_WE_MENU_EDIT": 1,
    "IDS_WE_MENU_DELETE": 1,
    "IDS_WE_MENU_PROPERTIES_MNEMONIC": 1,
})

LISTVIEW_ROUTES = Counter({
    "IDS_WE_WINDOW_PROPERTY_NAME": 5,
    "IDS_WE_COLUMN_VALUE": 5,
    "IDS_WE_COLUMN_ALIAS": 1,
    "IDS_WE_COLUMN_HANDLE": 1,
    "IDS_WE_GROUP_CLASS": 1,
    "IDS_WE_COLUMN_TEXT": 1,
    "IDS_WE_UIA_PROPERTY_PROCESS_ID": 1,
    "IDS_WE_COLUMN_THREAD_ID": 1,
})

TREE_ROUTES = (
    "IDS_WE_GROUP_CLASS",
    "IDS_WE_COLUMN_HANDLE",
    "IDS_WE_COLUMN_TEXT",
    "IDS_WE_COLUMN_PROCESS",
    "IDS_WE_WINDOW_PROPERTY_THREAD",
    "IDS_WE_COLUMN_MODULE",
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("windowexplorer_dynamic_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_WE_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class WindowExplorerDynamicUiResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            path.name: cls.audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in sorted(PLUGIN_ROOT.glob("*.c"))
        }

    def test_resources_extend_existing_tail_exactly_and_bilingually(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "WindowExplorer.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "WindowExplorer.zh-cn.rc")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_WE_[A-Z0-9_]+)\s+(\d+)$",
                header,
            )
        }

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(sorted(defines.values()), list(range(12000, 12169)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 169)
        self.assertEqual(len(chinese), 169)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12169$")

    def test_every_resource_menu_item_owns_its_text(self) -> None:
        actual = Counter()

        for name in ("wnddlg.c", "wndprp.c"):
            source = self.sources[name]
            helper = re.search(
                r"static\s+PPH_EMENU_ITEM\s+WepCreateResourceEMenuItem\s*\([^{}]*\)\s*\{(.*?)\n\}",
                source,
                re.S,
            )
            self.assertIsNotNone(helper, name)
            self.assertIn("PhDuplicateStringZ(PhGetStringOrEmpty(menuText))", helper.group(1))
            self.assertIn("PH_EMENU_TEXT_OWNED", helper.group(1))
            self.assertLess(helper.group(1).index("PhDuplicateStringZ"), helper.group(1).index("PhClearReference(&menuText)"))

            actual.update(re.findall(
                r"WepCreateResourceEMenuItem\([^;]*?\b(IDS_WE_[A-Z0-9_]+)\b[^;]*?\)",
                source,
                re.S,
            ))

        self.assertEqual(actual, MENU_ROUTES)

    def test_listview_columns_copy_resource_text_before_release(self) -> None:
        source = self.sources["wndprp.c"]
        helper = re.search(
            r"static\s+VOID\s+WepAddListViewResourceColumn\s*\([^{}]*\)\s*\{(.*?)\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(helper)
        body = helper.group(1)
        self.assertLess(body.index("PhLoadUiString("), body.index("PhAddListViewColumn("))
        self.assertLess(body.index("PhAddListViewColumn("), body.index("PhClearReference(&columnText)"))
        self.assertIn("PhGetStringOrEmpty(columnText)", body)

        actual = Counter(re.findall(
            r"WepAddListViewResourceColumn\([^;]*?\b(IDS_WE_[A-Z0-9_]+)\b[^;]*?\)",
            source,
            re.S,
        ))
        self.assertEqual(actual, LISTVIEW_ROUTES)

    def test_treenew_column_text_is_retained_until_columns_are_removed(self) -> None:
        source = self.sources["wndtree.c"]
        self.assertIn("WE_WINDOW_TREE_COLUMN_TEXT_CONTEXT", source)
        self.assertIn("PhSetWindowContext(TreeNewHandle, WE_WINDOW_TREE_COLUMN_TEXT_CONTEXT, columnTextList);", source)
        actual = tuple(re.findall(
            r"WepAddTreeNewResourceColumn\([^;]*?\b(IDS_WE_[A-Z0-9_]+)\b[^;]*?\)",
            source,
            re.S,
        ))
        self.assertEqual(actual, TREE_ROUTES)

        remove = source.index("TreeNew_RemoveColumn(Context->TreeNewHandle, i);")
        release = source.index("PhDereferenceObjects(columnTextList->Items, columnTextList->Count);")
        detach = source.index("PhRemoveWindowContext(Context->TreeNewHandle, WE_WINDOW_TREE_COLUMN_TEXT_CONTEXT);")
        self.assertLess(remove, release)
        self.assertLess(detach, release)

    def test_message_search_and_confirm_routes_are_native_and_null_safe(self) -> None:
        all_source = "\n".join(self.sources.values())
        for resource, count in (
            ("IDS_WE_UNABLE_CREATE_WINDOW", 1),
            ("IDS_WE_PROCESS_NOT_FOUND", 4),
            ("IDS_WE_PROPERTY_NAME_EMPTY", 1),
            ("IDS_WE_SEARCH_WINDOWS", 2),
        ):
            pattern = (
                r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
                rf"PluginInstance->DllBase,\s*{resource},\s*NULL\s*\)\)\)"
            )
            self.assertEqual(len(re.findall(pattern, all_source)), count, resource)

        confirm = re.search(
            r"PhShowConfirmMessage\(\s*WindowHandle,\s*"
            r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(PluginInstance->DllBase,\s*(IDS_WE_[A-Z0-9_]+),\s*NULL\)\)\),\s*"
            r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(PluginInstance->DllBase,\s*(IDS_WE_[A-Z0-9_]+),\s*NULL\)\)\),\s*"
            r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(PluginInstance->DllBase,\s*(IDS_WE_[A-Z0-9_]+),\s*NULL\)\)\),\s*FALSE\s*\)",
            self.sources["wndprp.c"],
            re.S,
        )
        self.assertIsNotNone(confirm)
        self.assertEqual(confirm.groups(), (
            "IDS_WE_ACTION_REMOVE",
            "IDS_WE_OBJECT_WINDOW_PROPERTY",
            "IDS_WE_WINDOW_PROPERTY_DELETE_WARNING",
        ))

    def test_target_runtime_dictionary_categories_are_empty(self) -> None:
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)

        target_categories = {
            "c_confirm",
            "c_emenu",
            "c_listview_col",
            "c_msgbox",
            "c_search",
            "c_treenew_col",
        }
        remaining = Counter(
            (entry["category"], entry["english"])
            for entry in entries
            if entry["category"] in target_categories
        )
        self.assertEqual(remaining, Counter())


if __name__ == "__main__":
    unittest.main()
