#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "OnlineChecks"


class OnlineChecksTreeColumnNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        cls.header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        cls.english = (PLUGIN_ROOT / "OnlineChecks.rc").read_text(encoding="utf-8-sig")
        cls.chinese = (PLUGIN_ROOT / "OnlineChecks.zh-cn.rc").read_text(encoding="utf-8-sig")

    def test_brand_columns_have_exact_native_resources(self):
        expected = (
            ("IDS_OC_COLUMN_VIRUSTOTAL", 12022, "VirusTotal"),
            ("IDS_OC_COLUMN_HYBRID_ANALYSIS", 12023, "Hybrid-Analysis"),
        )
        for name, value, text in expected:
            self.assertRegex(self.header, rf"(?m)^#define\s+{name}\s+{value}$")
            pattern = rf'(?m)^\s*{name}\s+"{re.escape(text)}"$'
            self.assertRegex(self.english, pattern)
            self.assertRegex(self.chinese, pattern)
        self.assertRegex(self.header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12025$")

    def test_all_six_columns_use_stable_cached_resources(self):
        self.assertIn("static PH_INITONCE OnlineChecksUiStringsInitOnce", self.source)
        self.assertIn("static PPH_STRING OnlineChecksUiStrings[", self.source)
        self.assertRegex(
            self.source,
            r"return\s+PhGetStringOrDefault\s*\(\s*OnlineChecksUiStrings"
            r"\[ResourceId\s*-\s*IDS_OC_COLUMN_VIRUSTOTAL\]\s*,\s*Fallback\s*\)\s*;",
        )
        self.assertEqual(
            len(re.findall(r'column\.Text\s*=\s*OnlineChecksGetUiString\(IDS_OC_COLUMN_VIRUSTOTAL, L"VirusTotal"\);', self.source)),
            3,
        )
        self.assertEqual(
            len(re.findall(r'column\.Text\s*=\s*OnlineChecksGetUiString\(IDS_OC_COLUMN_HYBRID_ANALYSIS, L"Hybrid-Analysis"\);', self.source)),
            3,
        )
        self.assertNotRegex(self.source, r'column\.Text\s*=\s*L"(?:VirusTotal|Hybrid-Analysis)"\s*;')


if __name__ == "__main__":
    unittest.main()
