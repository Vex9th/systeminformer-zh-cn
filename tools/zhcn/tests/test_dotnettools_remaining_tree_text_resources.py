#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "DotNetTools"

EXPECTED = (
    ("IDS_DN_COLUMN_APP_DOMAIN", 2108, "AppDomain", "应用程序域"),
    ("IDS_DN_LOADING_ASSEMBLIES", 2109, "Loading .NET assemblies...", "正在加载 .NET 程序集..."),
    ("IDS_DN_NO_ASSEMBLIES", 2110, "There are no assemblies to display.", "没有可显示的程序集。"),
    ("IDS_DN_UNABLE_START_TRACE_PREFIX", 2111, "Unable to start the event tracing session: ", "无法启动事件跟踪会话："),
    ("IDS_DN_UNKNOWN_ERROR", 2112, "Unknown error", "未知错误"),
)


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return dict(re.findall(r'^\s*(IDS_DN_[A-Z0-9_]+)\s+"((?:[^"\\]|\\.)*)"$', text, re.MULTILINE))


class DotNetToolsRemainingTreeTextResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        cls.header = (PLUGIN_ROOT / "dn.h").read_text(encoding="utf-8-sig")
        cls.resource_header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        cls.asm = (PLUGIN_ROOT / "asmpage.c").read_text(encoding="utf-8-sig")
        cls.tree = (PLUGIN_ROOT / "treeext.c").read_text(encoding="utf-8-sig")
        cls.english = parse_stringtable(PLUGIN_ROOT / "DotNetTools.rc")
        cls.chinese = parse_stringtable(PLUGIN_ROOT / "DotNetTools.zh-cn.rc")

    def test_resources_are_contiguous_and_bilingual(self):
        for name, value, english, chinese in EXPECTED:
            self.assertRegex(self.resource_header, rf"(?m)^#define\s+{name}\s+{value}$")
            self.assertEqual(self.english.get(name), english)
            self.assertEqual(self.chinese.get(name), chinese)
        self.assertRegex(self.resource_header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2113$")

    def test_shared_helper_has_stable_lifetime_and_fallback(self):
        self.assertIn("PCWSTR DotNetGetUiString(", self.header)
        self.assertIn("static PH_INITONCE DotNetUiStringsInitOnce", self.main)
        self.assertIn("static PPH_STRING DotNetUiStrings[", self.main)
        self.assertRegex(
            self.main,
            r"return\s+PhGetStringOrDefault\s*\(\s*DotNetUiStrings"
            r"\[ResourceId\s*-\s*IDS_DN_COLUMN_APP_DOMAIN\]\s*,\s*Fallback\s*\)\s*;",
        )

    def test_all_remaining_tree_text_uses_native_resources(self):
        self.assertIn('DotNetGetUiString(IDS_DN_COLUMN_APP_DOMAIN, L"AppDomain")', self.tree)
        self.assertIn('DotNetGetUiString(IDS_DN_LOADING_ASSEMBLIES, L"Loading .NET assemblies...")', self.asm)
        self.assertIn('DotNetGetUiString(IDS_DN_NO_ASSEMBLIES, L"There are no assemblies to display.")', self.asm)
        self.assertRegex(
            self.asm,
            r'DotNetGetUiString\(\s*IDS_DN_UNABLE_START_TRACE_PREFIX,\s*L"Unable to start the event tracing session: "\s*\)',
        )
        self.assertIn('DotNetGetUiString(IDS_DN_UNKNOWN_ERROR, L"Unknown error")', self.asm)
        self.assertNotIn(
            'AddTreeNewColumn(info, context, DNTHTNC_APPDOMAIN, FALSE, L"AppDomain",',
            self.tree,
        )
        self.assertNotRegex(self.asm, r'PhCreateString\(L"(?:Loading \.NET assemblies\.\.\.|There are no assemblies to display\.)"\)')


if __name__ == "__main__":
    unittest.main()
