#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_UNABLE_REGISTER_WINDOW_CLASS", 2931, "Unable to register window class.", "无法注册窗口类。"),
    ("IDS_PH_UNABLE_COMMIT_DETOURS", 2932, "Unable to commit detours transaction.", "无法提交 Detours 事务。"),
    ("IDS_PH_INFORMER_NO_EVENTS", 2933, "No events to display.", "没有可显示的事件。"),
    ("IDS_PH_APP_POLICY_NONE", 2934, "There are no policies to display.", "没有可显示的策略。"),
    ("IDS_PH_MENU_AFFINITY", 2935, "&Affinity", "处理器关联(&A)"),
    ("IDS_PH_MENU_PRIORITY", 2936, "&Priority", "优先级(&P)"),
    ("IDS_PH_MENU_TIME_CRITICAL", 2937, "Time &critical", "时间关键(&C)"),
    ("IDS_PH_MENU_HIGHEST", 2938, "&Highest", "最高(&H)"),
    ("IDS_PH_MENU_LOWEST", 2939, "&Lowest", "最低(&L)"),
    ("IDS_PH_MENU_PAGE_PRIORITY", 2940, "Pa&ge priority", "页优先级(&G)"),
    ("IDS_PH_MENU_MEDIUM", 2941, "&Medium", "中(&M)"),
    ("IDS_PH_FILE_NAME", 2942, "File name", "文件名"),
    ("IDS_PH_TIMELINE", 2943, "Timeline", "时间线"),
)

RUNTIME_COMPATIBILITY_KEYS = {"&Affinity"}

MENU_ROUTES = {
    "mwpgproc.c": {"IDS_PH_MENU_AFFINITY": 1, "IDS_PH_MENU_PRIORITY": 1, "IDS_PH_MAINWND_MENU_REAL_TIME": 1, "IDS_PH_MAINWND_MENU_HIGH": 2, "IDS_PH_MAINWND_MENU_ABOVE_NORMAL": 1, "IDS_PH_MAINWND_MENU_NORMAL": 3, "IDS_PH_MAINWND_MENU_BELOW_NORMAL": 2, "IDS_PH_MAINWND_MENU_IDLE": 1, "IDS_PH_MAINWND_MENU_I_O_PRIORITY": 1, "IDS_PH_MAINWND_MENU_LOW": 2, "IDS_PH_MAINWND_MENU_VERY_LOW": 2, "IDS_PH_MENU_PAGE_PRIORITY": 1, "IDS_PH_MENU_MEDIUM": 1},
    "procprp.c": {"IDS_PH_MENU_AFFINITY": 1, "IDS_PH_MENU_PRIORITY": 1, "IDS_PH_MAINWND_MENU_REAL_TIME": 1, "IDS_PH_MAINWND_MENU_HIGH": 2, "IDS_PH_MAINWND_MENU_ABOVE_NORMAL": 1, "IDS_PH_MAINWND_MENU_NORMAL": 3, "IDS_PH_MAINWND_MENU_BELOW_NORMAL": 2, "IDS_PH_MAINWND_MENU_IDLE": 1, "IDS_PH_MAINWND_MENU_I_O_PRIORITY": 1, "IDS_PH_MAINWND_MENU_LOW": 2, "IDS_PH_MAINWND_MENU_VERY_LOW": 2, "IDS_PH_MENU_PAGE_PRIORITY": 1, "IDS_PH_MENU_MEDIUM": 1},
    "prpgthrd.c": {"IDS_PH_MENU_AFFINITY": 1, "IDS_PH_MENU_PRIORITY": 2, "IDS_PH_MENU_TIME_CRITICAL": 1, "IDS_PH_MENU_HIGHEST": 1, "IDS_PH_MAINWND_MENU_HIGH": 1, "IDS_PH_MAINWND_MENU_ABOVE_NORMAL": 1, "IDS_PH_MAINWND_MENU_NORMAL": 3, "IDS_PH_MAINWND_MENU_BELOW_NORMAL": 2, "IDS_PH_MENU_LOWEST": 1, "IDS_PH_MAINWND_MENU_IDLE": 1, "IDS_PH_MAINWND_MENU_I_O_PRIORITY": 1, "IDS_PH_MAINWND_MENU_LOW": 2, "IDS_PH_MAINWND_MENU_VERY_LOW": 2, "IDS_PH_MENU_PAGE_PRIORITY": 1, "IDS_PH_MENU_MEDIUM": 1},
}

COLUMN_ROUTES = {
    "IDS_PH_FILE_NAME": {"modlist.c": 1, "pagfiles.c": 1, "proctree.c": 1, "prpgvdm.c": 1, "prpgwmi.c": 1, "srvctl.c": 1, "srvlist.c": 1, "thrdstk.c": 1, "thrdstks.c": 1},
    "IDS_PH_PID": {"hidnproc.c": 1, "informerwnd.c": 1, "netlist.c": 1, "proctree.c": 1, "srvlist.c": 1, "thrdstks.c": 1},
    "IDS_PH_TIMELINE": {"modlist.c": 1, "netlist.c": 1, "proctree.c": 1, "srvlist.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CONTEXTSWITCHES": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CONTEXTSWITCHESDELTA": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CPUKERNEL": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CPURELATIVE": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CPUUSER": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CYCLES": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_CYCLESDELTA": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_PAGEPRIORITY": {"proctree.c": 1, "thrdlist.c": 1},
    "IDS_PH_STAT_PRIVATEWS": {"memlist.c": 1, "proctree.c": 1},
    "IDS_PH_STAT_SHAREABLEWS": {"memlist.c": 1, "proctree.c": 1},
    "IDS_PH_STAT_SHAREDWS": {"memlist.c": 1, "proctree.c": 1},
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("bulk_low_risk_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {symbol: value.replace('""', '"') for symbol, value in re.findall(r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', path.read_text(encoding="utf-8-sig"))}


class SystemInformerBulkLowRiskNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def test_new_resources_are_contiguous_bilingual_and_owned(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            owner = "strings" if en in RUNTIME_COMPATIBILITY_KEYS else "native_strings"
            other = "native_strings" if owner == "strings" else "strings"
            self.assertEqual(zh, data[owner].get(en))
            self.assertNotIn(en, data[other])
        self.assertEqual(944, len(english))
        self.assertEqual(944, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_TIMELINE$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2944$")

    def test_small_runtime_sinks_use_stable_resources(self) -> None:
        delay = self.audit.mask_c_comments((APP_ROOT / "delayhook.c").read_text(encoding="utf-8-sig"))
        self.assertEqual(8, len(re.findall(r"PhShowStatus\(\s*NULL,\s*PhGetApplicationUiString\(IDS_PH_UNABLE_REGISTER_WINDOW_CLASS\)", delay)))
        self.assertEqual(1, len(re.findall(r"PhShowStatus\(\s*NULL,\s*PhGetApplicationUiString\(IDS_PH_UNABLE_COMMIT_DETOURS\)", delay)))
        for file_name, symbol, static_name in (("informerwnd.c", "IDS_PH_INFORMER_NO_EVENTS", "PhpInformerEmptyText"), ("tokprp.c", "IDS_PH_APP_POLICY_NONE", "PhAppPolicyEmptyText")):
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            self.assertNotIn(f"{static_name} = PH_STRINGREF_INIT", source)
            self.assertRegex(source, rf"PhInitializeStringRef\([^;]+PhGetApplicationUiString\({symbol}\)\)")

    def test_priority_menu_routes_are_exact(self) -> None:
        for file_name, expected in MENU_ROUTES.items():
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            for symbol, count in expected.items():
                self.assertEqual(count, len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)), (file_name, symbol))

        runtime_consumers = []
        for path in REPO_ROOT.rglob("*"):
            if path.suffix.lower() not in {".c", ".cc", ".cpp", ".cxx"}:
                continue
            if path == REPO_ROOT / "phlib" / "phtranslation_zhcn.c":
                continue
            source = self.audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            runtime_consumers.extend(
                path.relative_to(REPO_ROOT).as_posix()
                for _match in re.finditer(r'\bL"&Affinity"', source)
            )
        self.assertEqual(["plugins/UserNotes/main.c"], runtime_consumers)

    def test_column_routes_use_application_lifetime_strings(self) -> None:
        for symbol, files in COLUMN_ROUTES.items():
            for file_name, count in files.items():
                source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
                self.assertEqual(count, len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)), (file_name, symbol))


if __name__ == "__main__":
    unittest.main()
