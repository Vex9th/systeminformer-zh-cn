#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


RESOURCES = r"""
IDS_PH_MENU_GO_TO_PROCESS_ELLIPSIS|3353|Go to process...|转到进程...
IDS_PH_MENU_GO_TO_THREAD_ELLIPSIS|3354|Go to thread...|转到线程...
IDS_PH_MENU_HIDE_USER_FRAMES|3355|Hide user frames|隐藏用户帧
IDS_PH_MENU_HIDE_SYSTEM_FRAMES|3356|Hide system frames|隐藏系统帧
IDS_PH_MENU_HIDE_INLINE_FRAMES|3357|Hide inline frames|隐藏内联帧
IDS_PH_MENU_HIGHLIGHT_USER_FRAMES|3358|Highlight user frames|高亮用户帧
IDS_PH_MENU_HIGHLIGHT_SYSTEM_FRAMES|3359|Highlight system frames|高亮系统帧
IDS_PH_MENU_HIGHLIGHT_INLINE_FRAMES|3360|Highlight inline frames|高亮内联帧
IDS_PH_MENU_EXPAND_ALL_PLAIN|3368|Expand all|全部展开
IDS_PH_MENU_COLLAPSE_ALL_PLAIN|3369|Collapse all|全部折叠
""".strip()


NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in (
        line.split("|") for line in RESOURCES.splitlines()
    )
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("thread_stack_menu_audit", path)
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


class SystemInformerThreadStackMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            (APP_ROOT / "thrdstks.c").read_text(encoding="utf-8-sig")
        )

    def test_resources_routes_and_scan_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            self.assertEqual(1, self.source.count(f"PhGetApplicationUiString({symbol})"))

        self.assertEqual(1, self.source.count("PhGetApplicationUiString(IDS_PH_SEARCH_COPY)"))

        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "thrdstks.c"), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
