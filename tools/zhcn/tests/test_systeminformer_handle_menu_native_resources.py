#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


RESOURCES = r"""
IDS_PH_MENU_CLOSE_DELETE_SHORTCUT|3340|C&lose\bDel|关闭(&L)\bDel
IDS_PH_MENU_PROTECTED_SHORTCUT|3341|&Protected|保护(&P)
IDS_PH_MENU_INHERIT|3342|&Inherit|继承(&I)
IDS_PH_MENU_SECURITY_SHORTCUT|3343|Secu&rity|安全(&R)
IDS_PH_MENU_PROPERTIES_ENTER_ALT_SHORTCUT|3344|Prope&rties\bEnter|属性(&R)\bEnter
IDS_PH_MENU_HIDE_PROTECTED_HANDLES|3345|Hide protected handles|隐藏受保护句柄
IDS_PH_MENU_HIDE_INHERIT_HANDLES|3346|Hide inherit handles|隐藏可继承句柄
IDS_PH_MENU_HIDE_UNNAMED_HANDLES|3347|Hide unnamed handles|隐藏未命名句柄
IDS_PH_MENU_HIDE_ETW_HANDLES|3348|Hide etw handles|隐藏 ETW 句柄
IDS_PH_MENU_HANDLE_SNAPSHOTS|3349|Handle snapshots|句柄快照
IDS_PH_MENU_HIGHLIGHT_PROTECTED_HANDLES|3350|Highlight protected handles|高亮受保护句柄
IDS_PH_MENU_HIGHLIGHT_INHERIT_HANDLES|3351|Highlight inherit handles|高亮可继承句柄
IDS_PH_MENU_STATISTICS|3352|Statistics|统计
""".strip()


NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in (
        line.split("|") for line in RESOURCES.splitlines()
    )
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("handle_menu_audit", path)
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


class SystemInformerHandleMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            (APP_ROOT / "prpghndl.c").read_text(encoding="utf-8-sig")
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

        self.assertEqual(1, self.source.count("PhGetApplicationUiString(IDS_PH_MENU_COPY_SHORTCUT)"))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_COLLAPSE_ALL_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3370$")

        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "prpghndl.c"), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
