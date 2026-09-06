#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "NetworkTools"


RESOURCE_DATA = (
    (
        "IDS_NT_BUTTON_RESTART",
        12023,
        "Restart",
        "重启",
    ),
    (
        "IDS_NT_BUTTON_DOWNLOAD",
        12024,
        "Download",
        "下载",
    ),
    (
        "IDS_NT_ACCESS_DENIED_LICENSE_KEY_FORMAT",
        12025,
        "[%lu] Access denied (invalid license key)",
        "[%lu] 访问被拒绝（许可证密钥无效）",
    ),
    (
        "IDS_NT_GEOLITE_LICENSE_REQUIRED_CONTENT",
        12026,
        "A license key and account number are required to download GeoLite database updates and either the key or number are not configured.\n\n"
        "GeoLite license keys and accounts are free. If you're unsure how to create keys then please review the documentation here: <a href=\"https://support.maxmind.com/hc/en-us/articles/4407111582235-Generate-a-License-Key\">Generate-a-License-Key</a>\n\n"
        "Once you've created the key you can copy/paste the text into the Options window > NetworkTools settings and System Informer can start downloading GeoLite database updates.\n\n"
        "Special thanks to MaxMind (<a href=\"https://www.maxmind.com\">https://www.maxmind.com</a>) for continuing free GeoLite services <3",
        "下载 GeoLite 数据库更新需要许可证密钥和账户编号，但密钥或编号尚未配置。\n\n"
        "GeoLite 许可证密钥和账户可免费获取。如果你不确定如何创建密钥，请查看此处的文档：<a href=\"https://support.maxmind.com/hc/en-us/articles/4407111582235-Generate-a-License-Key\">生成许可证密钥</a>\n\n"
        "创建密钥后，可将文本复制/粘贴到“选项”窗口 > NetworkTools 设置中，之后 System Informer 即可开始下载 GeoLite 数据库更新。\n\n"
        "特别感谢 MaxMind（<a href=\"https://www.maxmind.com\">https://www.maxmind.com</a>）持续提供免费的 GeoLite 服务 <3",
    ),
)


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def masked_source(filename: str) -> str:
    audit = load_module(
        "networktools_taskdialog_audit",
        REPO_ROOT / "tools" / "zhcn" / "audit.py",
    )
    return audit.mask_c_comments(
        (PLUGIN_ROOT / filename).read_text(encoding="utf-8-sig")
    )


def function_body(source: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening_brace = source.find("{", match.start())
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1:index]

    raise AssertionError(f"unterminated function: {name}")


def parse_defines():
    header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    defines = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_NT_[A-Z0-9_]+)\s+(\d+)$",
            header,
        )
    }
    return defines, header


def parse_stringtable(path: pathlib.Path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"').replace(r"\n", "\n")
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_NT_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class NetworkToolsTaskDialogNativeResourceTests(unittest.TestCase):
    def test_resources_are_exact_and_extend_only_the_plugin_tail(self):
        defines, header = parse_defines()
        english = parse_stringtable(PLUGIN_ROOT / "NetworkTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "NetworkTools.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(
            [resource_id for _symbol, resource_id, _en, _zh in RESOURCE_DATA],
            list(range(12023, 12027)),
        )
        self.assertEqual(sorted(defines.values()), list(range(12000, 12062)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 62)
        self.assertEqual(len(chinese), 62)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12062$")

    def test_format_and_html_contracts_are_preserved(self):
        english = parse_stringtable(PLUGIN_ROOT / "NetworkTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "NetworkTools.zh-cn.rc")

        en_format = english["IDS_NT_ACCESS_DENIED_LICENSE_KEY_FORMAT"]
        zh_format = chinese["IDS_NT_ACCESS_DENIED_LICENSE_KEY_FORMAT"]
        self.assertEqual(re.findall(r"%[A-Za-z]+", en_format), ["%lu"])
        self.assertEqual(re.findall(r"%[A-Za-z]+", zh_format), ["%lu"])

        for table in (english, chinese):
            content = table["IDS_NT_GEOLITE_LICENSE_REQUIRED_CONTENT"]
            self.assertEqual(content.count("\n\n"), 3)
            self.assertEqual(content.count("<a href=\""), 2)
            self.assertEqual(content.count("</a>"), 2)
            self.assertEqual(
                content.count(
                    "https://support.maxmind.com/hc/en-us/articles/"
                    "4407111582235-Generate-a-License-Key"
                ),
                1,
            )
            self.assertEqual(content.count("https://www.maxmind.com"), 2)
            self.assertTrue(content.endswith("<3"))

    def test_raw_navigation_buttons_use_live_local_resource_objects(self):
        source = masked_source("pages.c")
        self.assertNotRegex(
            source,
            r"(?m)^\s*TASKDIALOG_BUTTON\s+(?:Restart|Download)ButtonArray\s*\[",
        )

        routes = (
            (
                "ShowDbCheckForUpdatesDialog",
                "downloadButtonText",
                "downloadButtonArray",
                "IDOK",
                "IDS_NT_BUTTON_DOWNLOAD",
            ),
            (
                "ShowDbInstallRestartDialog",
                "restartButtonText",
                "restartButtonArray",
                "IDYES",
                "IDS_NT_BUTTON_RESTART",
            ),
        )
        for function_name, text_name, array_name, button_id, resource in routes:
            with self.subTest(function=function_name):
                body = function_body(source, function_name)
                self.assertRegex(
                    body,
                    rf"PPH_STRING\s+{text_name}\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
                    rf"PluginInstance->DllBase\s*,\s*{resource}\s*,\s*NULL\s*\)\)\s*;",
                )
                self.assertRegex(
                    body,
                    rf"TASKDIALOG_BUTTON\s+{array_name}\s*\[\]\s*=\s*\{{\s*"
                    rf"\{{\s*{button_id}\s*,\s*PhGetStringOrEmpty\({text_name}\)\s*\}}\s*,?\s*\}}\s*;",
                )
                self.assertRegex(body, rf"config\.pButtons\s*=\s*{array_name}\s*;")
                self.assertLess(body.index(f"PPH_STRING {text_name}"), body.index("PhTaskDialogNavigatePage("))
                self.assertNotIn(f"PhDereferenceObject({text_name});", body)

        self.assertNotIn('L"Restart"', source)
        self.assertNotIn('L"Download"', source)

    def test_composed_error_and_long_content_use_native_resources(self):
        pages = masked_source("pages.c")
        update = masked_source("update.c")
        failed = function_body(pages, "ShowDbUpdateFailedDialog")
        geolite = function_body(update, "ShowGeoLiteUpdateDialog")

        self.assertRegex(
            failed,
            r"PhaFormatString\(\s*PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
            r"PluginInstance->DllBase\s*,\s*IDS_NT_ACCESS_DENIED_LICENSE_KEY_FORMAT\s*,\s*"
            r"NULL\s*\)\)\)\s*,\s*Context->ErrorCode\s*\)",
        )
        self.assertNotIn('L"[%lu] Access denied (invalid license key)"', pages)

        self.assertRegex(
            geolite,
            r"PPH_STRING\s+licenseRequiredContent\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
            r"PluginInstance->DllBase\s*,\s*IDS_NT_GEOLITE_LICENSE_REQUIRED_CONTENT\s*,\s*"
            r"NULL\s*\)\)\s*;",
        )
        self.assertRegex(
            geolite,
            r"config\.pszContent\s*=\s*PhGetStringOrEmpty\(licenseRequiredContent\)\s*;",
        )
        self.assertLess(geolite.index("PPH_STRING licenseRequiredContent"), geolite.index("PhShowTaskDialog(&config"))
        self.assertNotIn("PhDereferenceObject(licenseRequiredContent);", geolite)
        self.assertNotIn("A license key and account number are required", update)

    def test_fresh_module_has_no_taskdialog_translation_gaps(self):
        audit = load_module(
            "networktools_taskdialog_fresh_audit",
            REPO_ROOT / "tools" / "zhcn" / "audit.py",
        )
        sys.path.insert(0, str(REPO_ROOT / "tools" / "zhcn"))
        try:
            check_translation = load_module(
                "networktools_taskdialog_check_translation",
                REPO_ROOT / "tools" / "zhcn" / "check_translation.py",
            )
        finally:
            sys.path.pop(0)

        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            audit.scan_c_file(str(path), entries)

        table = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )
        categories = {"c_taskdialog_raw", "c_runtime_composed", "c_taskdialog"}
        gaps = [
            (entry["category"], entry["english"], entry["file"], entry["line"])
            for entry in entries
            if entry["category"] in categories
            and not check_translation.is_keep_english(entry["english"])
            and not check_translation.translation_is_effective(
                entry["category"],
                check_translation.translation_for_category(
                    table,
                    entry["category"],
                    entry["english"],
                ),
            )
        ]
        self.assertEqual(gaps, [])


if __name__ == "__main__":
    unittest.main()
