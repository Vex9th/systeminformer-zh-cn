#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "OnlineChecks"
RESOURCES = (
    ("IDS_OC_WILDCARD_PATH_TITLE", 12018, "This looks like a wildcard path, not a regular expression.", "这看起来是通配符路径，而不是正则表达式。"),
    ("IDS_OC_WILDCARD_PATH_CONTENT", 12019, "Convert it to a regular expression? Backslashes will be escaped and wildcards expanded.", "要将其转换为正则表达式吗？反斜杠将被转义，通配符将被展开。"),
    ("IDS_OC_UPLOAD_PROGRESS_INITIAL", 12020, "Uploaded: ~ of ~ (0%)\\r\\nSpeed: ~ KB/s", "已上传：~ / ~ (0%)\\r\\n速度：~ KB/s"),
    ("IDS_OC_INITIALIZING", 12021, "Initializing...", "正在初始化..."),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("onlinechecks_remaining_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path):
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_OC_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class OnlineChecksRemainingDynamicResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def test_resource_tail_and_bilingual_values_are_exact(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "OnlineChecks.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "OnlineChecks.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(english.get(symbol), en)
            self.assertEqual(chinese.get(symbol), zh)
        self.assertEqual(len(english), 25)
        self.assertEqual(len(chinese), 25)
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12025$")

    def test_exact_call_sites_use_nullable_safe_module_resources(self) -> None:
        exclude = self.audit.mask_c_comments((PLUGIN_ROOT / "exclude.c").read_text(encoding="utf-8-sig"))
        page3 = self.audit.mask_c_comments((PLUGIN_ROOT / "page3.c").read_text(encoding="utf-8-sig"))
        upload = self.audit.mask_c_comments((PLUGIN_ROOT / "upload.c").read_text(encoding="utf-8-sig"))

        for symbol in ("IDS_OC_WILDCARD_PATH_TITLE", "IDS_OC_WILDCARD_PATH_CONTENT"):
            self.assertIn(
                f"PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, {symbol}, NULL)))",
                exclude,
            )
        self.assertIn(
            "config.pszContent = PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_UPLOAD_PROGRESS_INITIAL, NULL)));",
            page3,
        )
        self.assertIn(
            "config.pszContent = PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_INITIALIZING, NULL)));",
            upload,
        )
        self.assertNotIn('config.pszContent = L"Initializing..."', upload)

    def test_fresh_module_scan_has_no_runtime_dictionary_text(self) -> None:
        entries = []
        for path in PLUGIN_ROOT.glob("*.c"):
            self.audit.scan_c_file(str(path), entries)

        runtime_categories = {
            "c_confirm", "c_emenu", "c_listview_col", "c_listview_item",
            "c_msgbox", "c_search", "c_tab", "c_taskdialog",
            "c_treenew_col", "c_treenew_empty",
        }
        self.assertFalse([entry for entry in entries if entry["category"] in runtime_categories])


if __name__ == "__main__":
    unittest.main()
