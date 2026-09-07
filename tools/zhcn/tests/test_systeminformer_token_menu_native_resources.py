#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


NEW_RESOURCES = (
    ("IDS_PH_MENU_PROTECTED_PLAIN", 3296, "Protected", "受保护"),
    ("IDS_PH_MENU_MEDIUM_PLUS", 3297, "Medium +", "中+"),
    ("IDS_PH_MENU_MEDIUM_PLAIN", 3298, "Medium", "中"),
    ("IDS_PH_MENU_UNTRUSTED", 3299, "Untrusted", "不受信任"),
    ("IDS_PH_MENU_CUSTOM", 3300, "Custom...", "自定义..."),
    ("IDS_PH_MENU_INTERMEDIATE_LEVEL", 3301, "Intermediate level", "中间级别"),
    ("IDS_PH_MENU_ENABLE_SHORTCUT", 3302, "&Enable", "启用(&E)"),
    ("IDS_PH_MENU_DISABLE_SHORTCUT", 3303, "&Disable", "禁用(&D)"),
    ("IDS_PH_MENU_RESET_SHORTCUT", 3304, "Re&set", "重置(&S)"),
    ("IDS_PH_MENU_REMOVE_SHORTCUT", 3305, "&Remove", "移除(&R)"),
)


ROUTES = {
    "IDS_PH_MENU_PROTECTED_PLAIN": 1,
    "IDS_PH_GROUP_SYSTEM": 1,
    "IDS_PH_HANDLE_IO_PRIORITY_HIGH": 1,
    "IDS_PH_MENU_MEDIUM_PLUS": 1,
    "IDS_PH_MENU_MEDIUM_PLAIN": 1,
    "IDS_PH_HANDLE_IO_PRIORITY_LOW": 1,
    "IDS_PH_MENU_UNTRUSTED": 1,
    "IDS_PH_MENU_CUSTOM": 1,
    "IDS_PH_MENU_INTERMEDIATE_LEVEL": 1,
    "IDS_PH_MENU_ENABLE_SHORTCUT": 2,
    "IDS_PH_MENU_DISABLE_SHORTCUT": 2,
    "IDS_PH_MENU_RESET_SHORTCUT": 2,
    "IDS_PH_MENU_REMOVE_SHORTCUT": 2,
    "IDS_PH_SEARCH_COPY": 4,
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("token_menu_audit", path)
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


class SystemInformerTokenMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            (APP_ROOT / "tokprp.c").read_text(encoding="utf-8-sig")
        )

    def test_new_resources_are_contiguous_and_bilingual(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))

        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_TERMINATE_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3423$")

    def test_all_token_menu_routes_use_application_resources(self) -> None:
        for symbol, count in ROUTES.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    count,
                    len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", self.source)),
                )

    def test_fresh_scan_has_no_token_menu_literals(self) -> None:
        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "tokprp.c"), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
