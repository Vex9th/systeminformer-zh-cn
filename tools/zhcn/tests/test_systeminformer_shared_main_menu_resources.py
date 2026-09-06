#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_MENU_HIDE_DEFAULT_SERVICES", 2906, "Hide default services", "隐藏默认服务"),
    ("IDS_PH_MENU_HIDE_DRIVER_SERVICES", 2907, "&Hide driver services", "隐藏驱动服务(&H)"),
    ("IDS_PH_MENU_DELETE_SHORTCUT", 2908, r"&Delete\bDel", r"删除(&D)\bDel"),
    ("IDS_PH_MENU_GO_TO_PROCESS", 2909, "&Go to process", "转到进程(&G)"),
    ("IDS_PH_MENU_OPEN_KEY", 2910, "Open &key", "打开注册表项(&K)"),
    ("IDS_PH_MENU_OPEN_FILE_LOCATION_SHORTCUT", 2911, r"Open &file location\bCtrl+Enter", r"打开文件位置(&F)\bCtrl+Enter"),
    ("IDS_PH_MENU_PROPERTIES_SHORTCUT", 2912, r"P&roperties\bEnter", r"属性(&R)\bEnter"),
    ("IDS_PH_MENU_COPY_SHORTCUT", 2913, r"&Copy\bCtrl+C", r"复制(&C)\bCtrl+C"),
    ("IDS_PH_MENU_HIDE_WAITING_CONNECTIONS", 2914, "&Hide waiting connections", "隐藏等待中的连接(&H)"),
    ("IDS_PH_MENU_GO_TO_PROCESS_SHORTCUT", 2915, r"&Go to process\bEnter", r"转到进程(&G)\bEnter"),
    ("IDS_PH_MENU_GO_TO_SERVICE", 2916, "Go to service", "转到服务"),
    ("IDS_PH_MENU_CLOSE", 2917, "C&lose", "关闭(&L)"),
)

ROUTES = {
    "mwpgsrv.c": {
        "IDS_PH_GROUP_SERVICES": 1, "IDS_PH_MENU_HIDE_DEFAULT_SERVICES": 1,
        "IDS_PH_MENU_HIDE_DRIVER_SERVICES": 1, "IDS_PH_SERVICE_START": 2,
        "IDS_PH_SERVICE_CONTINUE": 2, "IDS_PH_SERVICE_PAUSE": 2,
        "IDS_PH_SERVICE_STOP": 2, "IDS_PH_MENU_DELETE_SHORTCUT": 2,
        "IDS_PH_MENU_GO_TO_PROCESS": 2, "IDS_PH_MENU_OPEN_KEY": 2,
        "IDS_PH_MENU_OPEN_FILE_LOCATION_SHORTCUT": 2,
        "IDS_PH_MENU_PROPERTIES_SHORTCUT": 2, "IDS_PH_MENU_COPY_SHORTCUT": 2,
    },
    "mwpgnet.c": {
        "IDS_PH_LOGON_NETWORK": 1, "IDS_PH_MENU_HIDE_WAITING_CONNECTIONS": 1,
        "IDS_PH_MENU_GO_TO_PROCESS_SHORTCUT": 1, "IDS_PH_MENU_GO_TO_SERVICE": 1,
        "IDS_PH_MENU_CLOSE": 1, "IDS_PH_MENU_COPY_SHORTCUT": 1,
    },
    "informerwnd.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1},
    "findobj.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1},
    "mwpgproc.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1, "IDS_PH_MENU_OPEN_FILE_LOCATION_SHORTCUT": 1, "IDS_PH_MENU_PROPERTIES_SHORTCUT": 1},
    "options.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1},
    "prpghndl.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1},
    "prpgmem.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1},
    "prpgmod.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1, "IDS_PH_MENU_OPEN_FILE_LOCATION_SHORTCUT": 1},
    "prpgthrd.c": {"IDS_PH_MENU_COPY_SHORTCUT": 1},
    "miniinfo.c": {"IDS_PH_MENU_GO_TO_PROCESS": 1},
    "ntobjprp.c": {"IDS_PH_MENU_GO_TO_PROCESS": 1},
    "hndlmenu.c": {"IDS_PH_MENU_OPEN_KEY": 1},
    "procprp.c": {"IDS_PH_MENU_OPEN_FILE_LOCATION_SHORTCUT": 1},
    "srvctl.c": {"IDS_PH_MENU_GO_TO_SERVICE": 1},
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("shared_main_menu_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', path.read_text(encoding="utf-8-sig"))
    }


class SystemInformerSharedMainMenuResourceTests(unittest.TestCase):
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
            json_english = en.replace(r"\b", "\b")
            json_chinese = zh.replace(r"\b", "\b")
            self.assertEqual(json_chinese, data["native_strings"].get(json_english))
            self.assertNotIn(json_english, data["strings"])
        self.assertEqual(1051, len(english))
        self.assertEqual(1051, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_VIRTUALIZATION$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3051$")

    def test_every_shared_menu_literal_uses_the_exact_resource(self) -> None:
        for file_name, expected in ROUTES.items():
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            for symbol, count in expected.items():
                self.assertEqual(count, len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)), (file_name, symbol))

    def test_fresh_scan_has_no_migrated_menu_literals(self) -> None:
        targets = {row[2] for row in NEW_RESOURCES} | {"Services", "Network", "&Start", "C&ontinue", "&Pause", "S&top"}
        unresolved = []
        for file_name in ROUTES:
            entries = []
            self.audit.scan_c_file(str(APP_ROOT / file_name), entries)
            unresolved.extend(entry for entry in entries if entry["category"] == "c_emenu" and entry["english"] in targets)
        self.assertEqual([], unresolved)


if __name__ == "__main__":
    unittest.main()
