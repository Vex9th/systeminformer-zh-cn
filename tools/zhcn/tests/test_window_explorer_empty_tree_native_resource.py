#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "WindowExplorer"


class WindowExplorerEmptyTreeNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (PLUGIN_ROOT / "wnddlg.c").read_text(encoding="utf-8-sig")
        cls.header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        cls.english = (PLUGIN_ROOT / "WindowExplorer.rc").read_text(encoding="utf-8-sig")
        cls.chinese = (PLUGIN_ROOT / "WindowExplorer.zh-cn.rc").read_text(encoding="utf-8-sig")

    def test_empty_text_has_exact_native_resource(self):
        self.assertRegex(self.header, r"(?m)^#define\s+IDS_WE_NO_WINDOWS\s+12168$")
        self.assertRegex(self.header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12169$")
        self.assertRegex(self.english, r'(?m)^\s*IDS_WE_NO_WINDOWS\s+"There are no windows to display\."$')
        self.assertRegex(self.chinese, r'(?m)^\s*IDS_WE_NO_WINDOWS\s+"没有可显示的窗口。"$')

    def test_empty_text_is_cached_for_tree_lifetime(self):
        self.assertIn("static PH_INITONCE WepEmptyWindowsTextInitOnce", self.source)
        self.assertIn("static PPH_STRING WepEmptyWindowsText", self.source)
        self.assertIn("static PPH_STRINGREF WepGetEmptyWindowsText(", self.source)
        self.assertRegex(
            self.source,
            r"PhLoadUiString\(\s*PluginInstance->DllBase,\s*IDS_WE_NO_WINDOWS,\s*NULL\s*\)",
        )
        self.assertEqual(
            len(re.findall(r"(?m)^(?!\s*//).*TreeNew_SetEmptyText\([^;]*WepGetEmptyWindowsText\(\)", self.source)),
            2,
        )
        self.assertNotIn('PH_STRINGREF_INIT(L"There are no windows to display.")', self.source)


if __name__ == "__main__":
    unittest.main()
