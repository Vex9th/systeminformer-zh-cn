#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


RESOURCES = r"""
IDS_PH_MENU_READ_WRITE_MEMORY_PLAIN|3361|Read/Write memory|读/写内存
IDS_PH_MENU_ANSI|3362|ANSI|ANSI
IDS_PH_MENU_UNICODE|3363|Unicode|Unicode
IDS_PH_MENU_EXTENDED_CHARACTER_SET|3364|Extended character set|扩展字符集
IDS_PH_MENU_MINIMUM_LENGTH|3365|Minimum length...|最小长度...
IDS_PH_MENU_REFRESH_F5|3366|Refresh\bF5|刷新\bF5
IDS_PH_MENU_MAPPED|3367|Mapped|映射
""".strip()


NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in (
        line.split("|") for line in RESOURCES.splitlines()
    )
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("memory_search_menu_audit", path)
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


class SystemInformerMemorySearchMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            (APP_ROOT / "memsrcht.c").read_text(encoding="utf-8-sig")
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

        for symbol in (
            "IDS_PH_SEARCH_COPY",
            "IDS_PH_TREENEW_PRIVATE",
            "IDS_PH_HANDLE_SECTION_IMAGE",
            "IDS_PH_MENU_ZERO_PAD_ADDRESSES",
        ):
            self.assertEqual(1, self.source.count(f"PhGetApplicationUiString({symbol})"))

        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "memsrcht.c"), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
