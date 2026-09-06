#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "tools" / "peview"

EXPECTED = (
    ("expprp.c", "IDS_PV_EMPTY_EXPORTS", 3298, "There are no exports to display.", "没有可显示的导出项。"),
    ("expprp.c", "IDS_PV_LOADING_EXPORTS", 3299, "Loading exports from image...", "正在从映像加载导出项..."),
    ("impprp.c", "IDS_PV_EMPTY_IMPORTS", 3300, "There are no imports to display.", "没有可显示的导入项。"),
    ("impprp.c", "IDS_PV_LOADING_IMPORTS", 3301, "Loading imports from image...", "正在从映像加载导入项..."),
    ("pdbprp.c", "IDS_PV_EMPTY_SYMBOLS", 3302, "There are no symbols to display.", "没有可显示的符号。"),
    ("pdbprp.c", "IDS_PV_LOADING_SYMBOLS", 3303, "Loading symbols...", "正在加载符号..."),
    ("pedirprp.c", "IDS_PV_EMPTY_DIRECTORIES", 3304, "There are no directories to display.", "没有可显示的目录。"),
    ("pedirprp.c", "IDS_PV_LOADING_DIRECTORIES", 3305, "Loading directories from image...", "正在从映像加载目录..."),
    ("pedynrelocprp.c", "IDS_PV_EMPTY_DYNAMIC_RELOCATIONS", 3306, "There are no dynamic relocations to display.", "没有可显示的动态重定位。"),
    ("pedynrelocprp.c", "IDS_PV_LOADING_DYNAMIC_RELOCATIONS", 3307, "Loading dynamic relocations from image...", "正在从映像加载动态重定位..."),
    ("pesectionprp.c", "IDS_PV_EMPTY_SECTIONS", 3308, "There are no sections to display.", "没有可显示的节。"),
    ("pesectionprp.c", "IDS_PV_LOADING_SECTIONS", 3309, "Loading sections from image...", "正在从映像加载节..."),
    ("resprp.c", "IDS_PV_EMPTY_RESOURCES", 3310, "There are no resources to display.", "没有可显示的资源。"),
    ("resprp.c", "IDS_PV_LOADING_RESOURCES", 3311, "Loading resources from image...", "正在从映像加载资源..."),
    ("strings.c", "IDS_PV_EMPTY_STRINGS", 3312, "There are no strings to display.", "没有可显示的字符串。"),
    ("strings.c", "IDS_PV_LOADING_STRINGS", 3313, "Loading strings from image...", "正在从映像加载字符串..."),
)


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return dict(re.findall(r'^\s*(IDS_PV_[A-Z0-9_]+)\s+"((?:[^"\\]|\\.)*)"$', text, re.MULTILINE))


class PeViewEmptyTreeNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        cls.public_header = (PLUGIN_ROOT / "include" / "peview.h").read_text(encoding="utf-8-sig")
        cls.main = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        cls.english = parse_stringtable(PLUGIN_ROOT / "peview.rc")
        cls.chinese = parse_stringtable(PLUGIN_ROOT / "peview.zh-cn.rc")

    def test_resources_are_contiguous_and_bilingual(self):
        for _file, name, value, english, chinese in EXPECTED:
            self.assertRegex(self.header, rf"(?m)^#define\s+{name}\s+{value}$")
            self.assertEqual(self.english.get(name), english)
            self.assertEqual(self.chinese.get(name), chinese)
        self.assertRegex(self.header, r"(?m)^#define\s+IDS_PV_LAST\s+IDS_PV_LOADING_STRINGS$")
        self.assertRegex(self.header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3314$")

    def test_string_ref_accessor_returns_the_persistent_resource_object(self):
        self.assertIn("PPH_STRINGREF PvpLoadUiStringRef(", self.public_header)
        self.assertRegex(
            self.main,
            r"return\s+&PvpUiStrings\[ResourceId\s*-\s*IDS_PV_FIRST\]->sr\s*;",
        )

    def test_all_eight_trees_use_native_empty_and_loading_text(self):
        by_file = {}
        for file_name, name, _value, english, _chinese in EXPECTED:
            source = by_file.setdefault(
                file_name,
                (PLUGIN_ROOT / file_name).read_text(encoding="utf-8-sig"),
            )
            self.assertIn(f"PvpLoadUiStringRef({name})", source)
            self.assertNotIn(f'PH_STRINGREF_INIT(L"{english}")', source)


if __name__ == "__main__":
    unittest.main()
