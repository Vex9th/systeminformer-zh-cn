#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "NetworkTools"

EXPECTED = (
    ("IDS_NT_COLUMN_COUNTRY", 12054, "Country", "国家/地区"),
    ("IDS_NT_COLUMN_LOCAL_SERVICE", 12055, "Local service", "本地服务"),
    ("IDS_NT_COLUMN_REMOTE_SERVICE", 12056, "Remote service", "远程服务"),
    ("IDS_NT_COLUMN_TOTAL_BYTES_IN", 12057, "Total bytes in", "接收总字节数"),
    ("IDS_NT_COLUMN_TOTAL_BYTES_OUT", 12058, "Total bytes out", "发送总字节数"),
    ("IDS_NT_COLUMN_PACKET_LOSS", 12059, "Packet loss", "丢包数"),
    ("IDS_NT_COLUMN_JITTER_MS", 12060, "Jitter (ms)", "抖动（毫秒）"),
    ("IDS_NT_COLUMN_LATENCY_MS", 12061, "Latency (ms)", "延迟（毫秒）"),
)


class NetworkToolsPluginColumnNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        cls.header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        cls.english = (PLUGIN_ROOT / "NetworkTools.rc").read_text(encoding="utf-8-sig")
        cls.chinese = (PLUGIN_ROOT / "NetworkTools.zh-cn.rc").read_text(encoding="utf-8-sig")

    def test_resources_are_contiguous_and_bilingual(self):
        for name, value, english, chinese in EXPECTED:
            self.assertRegex(self.header, rf"(?m)^#define\s+{name}\s+{value}$")
            self.assertRegex(self.english, rf'(?m)^\s*{name}\s+"{re.escape(english)}"$')
            self.assertRegex(self.chinese, rf'(?m)^\s*{name}\s+"{re.escape(chinese)}"$')
        self.assertRegex(self.header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12062$")

    def test_plugin_columns_use_stable_cached_resources_with_fallbacks(self):
        self.assertIn("static PH_INITONCE NetworkToolsUiStringsInitOnce", self.source)
        self.assertIn("static PPH_STRING NetworkToolsUiStrings[", self.source)
        self.assertRegex(
            self.source,
            r"return\s+PhGetStringOrDefault\s*\(\s*NetworkToolsUiStrings"
            r"\[ResourceId\s*-\s*IDS_NT_COLUMN_COUNTRY\]\s*,\s*Fallback\s*\)\s*;",
        )
        for name, _value, english, _chinese in EXPECTED:
            self.assertRegex(
                self.source,
                rf'column\.Text\s*=\s*NetworkToolsGetUiString\s*\(\s*{name}\s*,\s*L"{re.escape(english)}"\s*\)\s*;',
            )

    def test_raw_plugin_column_literals_are_not_assigned_directly(self):
        for _name, _value, english, _chinese in EXPECTED:
            self.assertNotRegex(self.source, rf'column\.Text\s*=\s*L"{re.escape(english)}"\s*;')


if __name__ == "__main__":
    unittest.main()
