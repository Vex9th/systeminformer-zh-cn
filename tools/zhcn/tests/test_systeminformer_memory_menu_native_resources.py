#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


RESOURCES = r"""
IDS_PH_MENU_DECOMMIT|3324|&Decommit|解除提交(&D)
IDS_PH_MENU_EMPTY_WORKING_SET|3325|&Empty working set...|清空工作集(&E)...
IDS_PH_MENU_FREE|3326|&Free|释放(&F)
IDS_PH_MENU_READ_WRITE_MEMORY|3327|&Read/Write memory...|读/写内存(&R)...
IDS_PH_MENU_SAVE_SHORTCUT|3328|&Save...|保存(&S)...
IDS_PH_MENU_CHANGE_PROTECTION|3329|Change &protection...|更改保护属性(&P)...
IDS_PH_MENU_HIDE_FREE_PAGES|3330|Hide free pages|隐藏空闲页
IDS_PH_MENU_HIDE_GUARD_PAGES|3331|Hide guard pages|隐藏保护页
IDS_PH_MENU_HIDE_RESERVED_PAGES|3332|Hide reserved pages|隐藏保留页
IDS_PH_MENU_HIGHLIGHT_CFG_PAGES|3333|Highlight CFG pages|高亮 CFG 页
IDS_PH_MENU_HIGHLIGHT_EXECUTABLE_PAGES|3334|Highlight executable pages|高亮可执行页
IDS_PH_MENU_HIGHLIGHT_PRIVATE_PAGES|3335|Highlight private pages|高亮专用页
IDS_PH_MENU_HIGHLIGHT_SYSTEM_PAGES|3336|Highlight system pages|高亮系统页
IDS_PH_MENU_MODIFIED|3337|Modified...|已修改...
IDS_PH_MENU_READ_WRITE_ADDRESS|3338|Read/Write &address...|读/写地址(&A)...
IDS_PH_MENU_STRINGS|3339|Strings...|字符串...
""".strip()


NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in (
        line.split("|") for line in RESOURCES.splitlines()
    )
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("memory_menu_audit", path)
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


class SystemInformerMemoryMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            (APP_ROOT / "prpgmem.c").read_text(encoding="utf-8-sig")
        )

    def test_resources_routes_tail_and_scan_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            self.assertEqual(1, self.source.count(f"PhGetApplicationUiString({symbol})"))

        for symbol in ("IDS_PH_MENU_HEAPS", "IDS_PH_MENU_SAVE", "IDS_PH_MENU_ZERO_PAD_ADDRESSES"):
            self.assertEqual(1, self.source.count(f"PhGetApplicationUiString({symbol})"))

        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_TERMINATE_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3423$")

        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "prpgmem.c"), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
