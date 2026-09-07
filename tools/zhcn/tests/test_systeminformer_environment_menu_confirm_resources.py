#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCES = (
    ("IDS_PH_ENV_MENU_EDIT", 2918, "Edit", "编辑"),
    ("IDS_PH_ENV_MENU_HIDE_PROCESS", 2919, "Hide process", "隐藏进程"),
    ("IDS_PH_ENV_MENU_HIDE_USER", 2920, "Hide user", "隐藏用户"),
    ("IDS_PH_ENV_MENU_HIDE_SYSTEM", 2921, "Hide system", "隐藏系统"),
    ("IDS_PH_ENV_MENU_HIDE_CMD", 2922, "Hide cmd", "隐藏 cmd"),
    ("IDS_PH_ENV_MENU_HIGHLIGHT_PROCESS", 2923, "Highlight process", "高亮进程"),
    ("IDS_PH_ENV_MENU_HIGHLIGHT_USER", 2924, "Highlight user", "高亮用户"),
    ("IDS_PH_ENV_MENU_HIGHLIGHT_SYSTEM", 2925, "Highlight system", "高亮系统"),
    ("IDS_PH_ENV_MENU_HIGHLIGHT_CMD", 2926, "Highlight cmd", "高亮 cmd"),
    ("IDS_PH_ENV_MENU_NEW_VARIABLE", 2927, "New variable...", "新建变量..."),
    ("IDS_PH_ACTION_EDIT", 2928, "edit", "编辑"),
    ("IDS_PH_ENV_SELECTED_VARIABLE_OBJECT", 2929, "the selected environment variable", "所选环境变量"),
    ("IDS_PH_ENV_EDIT_WARNING", 2930, "Some programs may restrict access or ban your account when editing the environment variable(s) of the process.", "编辑进程的环境变量时，某些程序可能会限制访问或封禁你的账户。"),
)

ROUTES = {
    "IDS_PH_ENV_MENU_EDIT": 1,
    "IDS_PH_SEARCH_DELETE": 1,
    "IDS_PH_ENV_MENU_HIDE_PROCESS": 1,
    "IDS_PH_ENV_MENU_HIDE_USER": 1,
    "IDS_PH_ENV_MENU_HIDE_SYSTEM": 1,
    "IDS_PH_ENV_MENU_HIDE_CMD": 1,
    "IDS_PH_ENV_MENU_HIGHLIGHT_PROCESS": 1,
    "IDS_PH_ENV_MENU_HIGHLIGHT_USER": 1,
    "IDS_PH_ENV_MENU_HIGHLIGHT_SYSTEM": 1,
    "IDS_PH_ENV_MENU_HIGHLIGHT_CMD": 1,
    "IDS_PH_ENV_MENU_NEW_VARIABLE": 1,
    "IDS_PH_ACTION_EDIT": 2,
    "IDS_PH_ACTION_DELETE": 1,
    "IDS_PH_ENV_SELECTED_VARIABLE_OBJECT": 3,
    "IDS_PH_ENV_EDIT_WARNING": 3,
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("environment_menu_confirm_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', path.read_text(encoding="utf-8-sig"))
    }


class SystemInformerEnvironmentMenuConfirmResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def test_resources_are_contiguous_bilingual_and_owned(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        for symbol, resource_id, en, zh in RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            self.assertEqual(zh, data["native_strings"].get(en))
            self.assertNotIn(en, data["strings"])
        self.assertEqual(1423, len(english))
        self.assertEqual(1423, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_TERMINATE_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3423$")

    def test_menu_and_confirmation_routes_are_exact(self) -> None:
        source = self.audit.mask_c_comments((APP_ROOT / "prpgenv.c").read_text(encoding="utf-8-sig"))
        for symbol, count in ROUTES.items():
            self.assertEqual(count, len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)), symbol)
        calls = [args for _name, args, _spans, _start in self.audit.find_calls(source, {"PhShowConfirmMessage"})]
        normalized = [tuple(re.sub(r"\s+", "", arg) for arg in args[1:5]) for args in calls]
        edit = ("PhGetApplicationUiString(IDS_PH_ACTION_EDIT)", "PhGetApplicationUiString(IDS_PH_ENV_SELECTED_VARIABLE_OBJECT)", "PhGetApplicationUiString(IDS_PH_ENV_EDIT_WARNING)", "FALSE")
        delete = ("PhGetApplicationUiString(IDS_PH_ACTION_DELETE)", "PhGetApplicationUiString(IDS_PH_ENV_SELECTED_VARIABLE_OBJECT)", "PhGetApplicationUiString(IDS_PH_ENV_EDIT_WARNING)", "FALSE")
        self.assertEqual(2, normalized.count(edit))
        self.assertEqual(1, normalized.count(delete))

    def test_shared_hide_system_and_fresh_scan_are_complete(self) -> None:
        module_source = self.audit.mask_c_comments((APP_ROOT / "prpgmod.c").read_text(encoding="utf-8-sig"))
        self.assertEqual(1, len(re.findall(r"PhGetApplicationUiString\(IDS_PH_ENV_MENU_HIDE_SYSTEM\)", module_source)))
        targets = {row[2] for row in RESOURCES} | {"Delete", "delete"}
        unresolved = []
        for file_name in ("prpgenv.c", "prpgmod.c"):
            entries = []
            self.audit.scan_c_file(str(APP_ROOT / file_name), entries)
            unresolved.extend(entry for entry in entries if entry["category"] in {"c_emenu", "c_confirm"} and entry["english"] in targets)
        self.assertEqual([], unresolved)


if __name__ == "__main__":
    unittest.main()
