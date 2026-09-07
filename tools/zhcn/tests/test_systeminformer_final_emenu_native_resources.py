#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCES = r"""
IDS_PH_MENU_ADD|3393|&Add|添加(&A)
IDS_PH_MENU_DELETE_PLAIN|3394|&Delete|删除(&D)
IDS_PH_MENU_EDIT|3395|&Edit|编辑(&E)
IDS_PH_MENU_READ_WRITE_MEMORY_SHORTCUT|3396|&Read/Write memory|读/写内存(&R)
IDS_PH_MENU_REFRESH_F5_SHORTCUT|3397|&Refresh\bF5|刷新(&R)\bF5
IDS_PH_MENU_RESET_PLAIN|3398|&Reset|重置(&R)
IDS_PH_MENU_CHOOSE_COLUMNS|3399|Choose columns...|选择列...
IDS_PH_MENU_CONTAINS_CASE_INSENSITIVE|3400|Contains (case-insensitive)...|包含（不区分大小写）...
IDS_PH_MENU_CONTAINS|3401|Contains...|包含...
IDS_PH_MENU_COPY_CTRL_C_PLAIN|3402|Copy\bCtrl+C|复制\bCtrl+C
IDS_PH_MENU_FILE_PROPERTIES|3403|File propert&ies|文件属性(&I)
IDS_PH_MENU_GO_TO_PROCESS_ALT|3404|Go to &process...|转到进程(&P)...
IDS_PH_MENU_GO_TO_THREAD_ALT|3405|Go to t&hread...|转到线程(&H)...
IDS_PH_MENU_HIDE_COLUMN|3406|Hide column|隐藏列
IDS_PH_MENU_HIDE_DEFAULT|3407|Hide default|隐藏默认项
IDS_PH_MENU_HIDE_MODIFIED|3408|Hide modified|隐藏已修改项
IDS_PH_MENU_HIGHLIGHT_DEFAULT|3409|Highlight default|高亮默认项
IDS_PH_MENU_HIGHLIGHT_MODIFIED|3410|Highlight modified|高亮已修改项
IDS_PH_MENU_MOVE_DOWN|3411|Move Down|下移
IDS_PH_MENU_MOVE_UP|3412|Move Up|上移
IDS_PH_MENU_NO_EXECUTE_UP|3413|No-Execute-Up|不得向上执行
IDS_PH_MENU_NO_READ_UP|3414|No-Read-Up|不得向上读取
IDS_PH_MENU_NO_WRITE_UP|3415|No-Write-Up|不得向上写入
IDS_PH_MENU_OPAQUE|3416|Opaque|不透明
IDS_PH_MENU_PROCESS_PROPERTIES|3417|Process propert&ies|进程属性(&I)
IDS_PH_MENU_PROPERTIES_ALT|3418|Prope&rties|属性(&R)
IDS_PH_MENU_READ_WRITE_MEMORY_ALT|3419|Read/Write &memory|读/写内存(&M)
IDS_PH_MENU_REGEX_CASE_INSENSITIVE|3420|Regex (case-insensitive)...|正则表达式（不区分大小写）...
IDS_PH_MENU_REGEX|3421|Regex...|正则表达式...
IDS_PH_MENU_TERMINATE_PLAIN|3422|Terminate|终止
""".strip()

NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in (line.split("|") for line in RESOURCES.splitlines())
)

TARGETS = (
    "envdlg.c", "prpgvdm.c", "miniinfo.c", "memrslt.c", "options.c", "findobj.c",
    "appsup.c", "usrlist.c", "heapinfo.c", "hndlmenu.c", "sysinfo.c", "prpggen.c",
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("final_emenu_audit", path)
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


class SystemInformerFinalEmenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.combined = "\n".join(
            cls.audit.mask_c_comments((APP_ROOT / name).read_text(encoding="utf-8-sig"))
            for name in TARGETS
        )

    def test_new_resources_and_routes_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            expected_count = {
                "IDS_PH_MENU_RESET_PLAIN": 4,
                "IDS_PH_MENU_COPY_CTRL_C_PLAIN": 2,
            }.get(symbol, 1)
            self.assertEqual(
                expected_count,
                self.combined.count(f"PhGetApplicationUiString({symbol})"),
            )

    def test_all_direct_emenu_text_is_eliminated(self) -> None:
        entries = []
        for name in TARGETS:
            self.audit.scan_c_file(str(APP_ROOT / name), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
