#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCE_TEXT = {
    "IDS_PH_STATUS_TRUE": (2312, "True", "真"),
    "IDS_PH_STATUS_FALSE": (2313, "False", "假"),
    "IDS_PH_STATUS_ENABLED": (2314, "Enabled", "已启用"),
    "IDS_PH_STATUS_DISABLED": (2315, "Disabled", "已禁用"),
    "IDS_PH_STATUS_ENABLED_MODIFIED": (2316, "Enabled (modified)", "已启用（已修改）"),
    "IDS_PH_STATUS_DISABLED_MODIFIED": (2317, "Disabled (modified)", "已禁用（已修改）"),
    "IDS_PH_STATUS_YES": (2318, "Yes", "是"),
    "IDS_PH_STATUS_NO": (2319, "No", "否"),
    "IDS_PH_STATUS_NOT_ALLOWED": (2320, "Not allowed", "不允许"),
    "IDS_PH_STATUS_NOT_CAPABLE": (2321, "Not capable", "不支持"),
    "IDS_PH_STATUS_VIRTUAL_MACHINE": (2322, "Virtual machine", "虚拟机"),
    "IDS_PH_STATUS_DISABLED_HYPERV": (2323, "Disabled / Hyper-V", "已禁用 / Hyper-V"),
    "IDS_PH_STATUS_UNDEFINED": (2324, "Undefined", "未定义"),
    "IDS_PH_STATUS_NO_DRIVER": (2325, "no driver", "缺少驱动程序"),
    "IDS_PH_STATUS_NO_SYMBOLS": (2326, "no symbols", "缺少符号文件"),
    "IDS_PH_CREATING_DUMP_FILE": (2327, "Creating the dump file...", "正在创建转储文件..."),
    "IDS_PH_RESOLVING_SYMBOLS": (2328, "Resolving symbols...", "正在解析符号..."),
    "IDS_PH_SETTING_EDITOR": (2329, "Setting Editor", "设置编辑器"),
    "IDS_PH_FIND": (2330, "Find", "查找"),
    "IDS_PH_CANCEL": (2331, "Cancel", "取消"),
    "IDS_PH_CLOSE": (2332, "Close", "关闭"),
    "IDS_PH_MAKE_DEFAULT": (2333, "Make default...", "设为默认..."),
    "IDS_PH_RESTORE_DEFAULT": (2334, "Restore default...", "恢复默认..."),
    "IDS_PH_NO_SCHEMA_DESCRIPTION": (2335, "No schema description available.", "无可用的架构说明。"),
    "IDS_PH_NULL_VALUE": (2336, "NULL", "NULL"),
    "IDS_PH_UNKNOWN_SID": (2337, "[Unknown SID]", "[未知 SID]"),
    "IDS_PH_UNNAMED_JOB": (2338, "(unnamed job)", "（未命名作业）"),
    "IDS_PH_STATUS_NOT_ALLOWED_TITLE": (2339, "Not Allowed", "不允许"),
}

RUNTIME_DICTIONARY_OWNED = {
    "Cancel",
    "Close",
    "Enabled",
    "Find",
    "Make default...",
    "Setting Editor",
}

RESOURCE_USES = {
    "IDS_PH_STATUS_TRUE": {"ntobjprp.c": 2, "tokprp.c": 1},
    "IDS_PH_STATUS_FALSE": {"ntobjprp.c": 2, "tokprp.c": 1},
    "IDS_PH_STATUS_ENABLED": {"syssccpu.c": 1, "tokprp.c": 2},
    "IDS_PH_STATUS_DISABLED": {"syssccpu.c": 1, "tokprp.c": 2},
    "IDS_PH_STATUS_ENABLED_MODIFIED": {"tokprp.c": 1},
    "IDS_PH_STATUS_DISABLED_MODIFIED": {"tokprp.c": 1},
    "IDS_PH_STATUS_YES": {"tokprp.c": 1},
    "IDS_PH_STATUS_NO": {"tokprp.c": 1},
    "IDS_PH_STATUS_NOT_ALLOWED": {"tokprp.c": 1},
    "IDS_PH_STATUS_NOT_CAPABLE": {"syssccpu.c": 1},
    "IDS_PH_STATUS_VIRTUAL_MACHINE": {"syssccpu.c": 1},
    "IDS_PH_STATUS_DISABLED_HYPERV": {"syssccpu.c": 1},
    "IDS_PH_STATUS_UNDEFINED": {"sysscmem.c": 3},
    "IDS_PH_STATUS_NO_DRIVER": {"sysscmem.c": 2},
    "IDS_PH_STATUS_NO_SYMBOLS": {"sysscmem.c": 2},
    "IDS_PH_CREATING_DUMP_FILE": {"mdump.c": 3},
    "IDS_PH_RESOLVING_SYMBOLS": {"memmod.c": 1},
    "IDS_PH_SETTING_EDITOR": {"options.c": 1},
    "IDS_PH_FIND": {"findobj.c": 1},
    "IDS_PH_CANCEL": {"findobj.c": 1},
    "IDS_PH_CLOSE": {"procprp.c": 1},
    "IDS_PH_MAKE_DEFAULT": {"options.c": 1},
    "IDS_PH_RESTORE_DEFAULT": {"options.c": 1},
    "IDS_PH_NO_SCHEMA_DESCRIPTION": {"options.c": 1},
    "IDS_PH_NULL_VALUE": {"hndlprp.c": 2},
    "IDS_PH_UNKNOWN_SID": {"tokprp.c": 1},
    "IDS_PH_UNNAMED_JOB": {"jobprp.c": 1},
    "IDS_PH_STATUS_NOT_ALLOWED_TITLE": {"tokprp.c": 1},
}


def load_tool(name: str):
    path = REPO_ROOT / "tools" / "zhcn" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SystemInformerLowRiskResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_tool("audit")

    def active_source(self, filename: str) -> str:
        return self.audit.mask_c_comments(
            (APP_ROOT / filename).read_text(encoding="utf-8-sig")
        )

    def test_resources_have_exact_ids_translations_and_boundaries(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english_rc = (APP_ROOT / "SystemInformer.rc").read_text(encoding="utf-8-sig")
        chinese_rc = (APP_ROOT / "SystemInformer.zh-cn.rc").read_text(encoding="utf-8-sig")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for resource_id, (numeric_id, english, chinese) in RESOURCE_TEXT.items():
            with self.subTest(resource_id=resource_id):
                self.assertRegex(header, rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$")
                self.assertRegex(english_rc, rf'(?m)^\s*{resource_id}\s+"{re.escape(english)}"$')
                self.assertRegex(chinese_rc, rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese)}"$')
                table = "strings" if english in RUNTIME_DICTIONARY_OWNED else "native_strings"
                other_table = "native_strings" if table == "strings" else "strings"
                self.assertEqual(translations[table].get(english), chinese)
                self.assertNotIn(english, translations[other_table])

        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_GROUP_PACKAGE$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2511$")
        self.assertEqual(len(re.findall(r'(?m)^\s*IDS_PH_[A-Z0-9_]+\s+"', english_rc)), 511)
        self.assertEqual(len(re.findall(r'(?m)^\s*IDS_PH_[A-Z0-9_]+\s+"', chinese_rc)), 511)

    def test_each_callsite_uses_the_exact_resource(self) -> None:
        for resource_id, file_counts in RESOURCE_USES.items():
            for filename, expected_count in file_counts.items():
                with self.subTest(resource_id=resource_id, filename=filename):
                    source = self.active_source(filename)
                    self.assertEqual(
                        source.count(f"PhGetApplicationUiString({resource_id})"),
                        expected_count,
                    )

    def test_branch_pairs_keep_their_exact_resource_routes(self) -> None:
        route_patterns = {
            "ntobjprp.c": (
                r"basicInfo\.EventState\s*>\s*0\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_TRUE\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_FALSE\)",
                r"basicInfo\.TimerState\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_TRUE\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_FALSE\)",
            ),
            "options.c": (
                r"if\s*\(PhpIsDefaultTaskManager\(\)\).*?"
                r"IDS_PH_RESTORE_DEFAULT.*?else.*?IDS_PH_MAKE_DEFAULT",
                r"PhSetWindowText\(hwndDlg,\s*"
                r"PhGetApplicationUiString\(IDS_PH_SETTING_EDITOR\)\)",
                r"PhSetDialogItemText\(hwndDlg,\s*IDC_DESCRIPTION,\s*"
                r"PhGetApplicationUiString\(IDS_PH_NO_SCHEMA_DESCRIPTION\)\)",
            ),
            "findobj.c": (
                r"if\s*\(!context->SearchThreadHandle\).*?IDS_PH_CANCEL",
                r"case\s+WM_PH_SEARCH_FINISHED:.*?IDS_PH_FIND",
            ),
            "sysscmem.c": (
                r"KsiLevel\(\)\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_NO_SYMBOLS\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_NO_DRIVER\)",
                r"if\s*\(KsiLevel\(\)\).*?IDS_PH_STATUS_NO_SYMBOLS.*?"
                r"else.*?IDS_PH_STATUS_NO_DRIVER",
            ),
            "tokprp.c": (
                r"State\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_ENABLED_MODIFIED\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_DISABLED_MODIFIED\)",
                r"isVirtualizationEnabled\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_YES\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_NO\)",
                r"PhSetDialogItemText\(\s*hwndDlg,\s*IDC_VIRTUALIZED,\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_NOT_ALLOWED\)\s*\)",
                r"tokenVirtualization\s*=\s*isVirtualizationEnabled\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_ENABLED\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_DISABLED\)",
                r"else\s*\{\s*tokenVirtualization\s*=\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_NOT_ALLOWED_TITLE\)",
                r"tokenUIAccess\s*=\s*isUIAccessEnabled\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_ENABLED\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_DISABLED\)",
                r"isLessPrivilegedAppContainer\s*\?\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_TRUE\)\s*:\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_FALSE\)",
            ),
            "syssccpu.c": (
                r"case\s+PhVirtualStatusVirtualMachine:\s*"
                r"PhSetWindowText\(CpuVirtualizationLabel,\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_VIRTUAL_MACHINE\)\)",
                r"case\s+PhVirtualStatusEnabledHyperV:\s*"
                r"case\s+PhVirtualStatusEnabledFirmware:\s*"
                r"PhSetWindowText\(CpuVirtualizationLabel,\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_ENABLED\)\)",
                r"case\s+PhVirtualStatusDisabledWithHyperV:\s*"
                r"PhSetWindowText\(CpuVirtualizationLabel,\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_DISABLED_HYPERV\)\)",
                r"case\s+PhVirtualStatusDisabled:\s*"
                r"PhSetWindowText\(CpuVirtualizationLabel,\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_DISABLED\)\)",
                r"case\s+PhVirtualStatusNotCapable:\s*default:\s*"
                r"PhSetWindowText\(CpuVirtualizationLabel,\s*"
                r"PhGetApplicationUiString\(IDS_PH_STATUS_NOT_CAPABLE\)\)",
            ),
        }

        for filename, patterns in route_patterns.items():
            source = self.active_source(filename)
            for pattern in patterns:
                with self.subTest(filename=filename, pattern=pattern):
                    self.assertRegex(source, re.compile(pattern, re.DOTALL))

    def test_migrated_window_text_is_absent_from_the_fresh_scan(self) -> None:
        audit = load_tool("audit")
        entries = []

        for filename in {name for counts in RESOURCE_USES.values() for name in counts}:
            audit.scan_c_file(str(APP_ROOT / filename), entries)

        remaining = {
            entry["english"]
            for entry in entries
            if entry["category"] == "c_window_text"
        }
        expected_removed = {english for _, english, _ in RESOURCE_TEXT.values()}
        expected_removed.add("Not Allowed")
        self.assertEqual(remaining & expected_removed, set())


if __name__ == "__main__":
    unittest.main()
