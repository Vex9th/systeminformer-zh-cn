#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_VALUE", 2897, "Value", "值"),
    ("IDS_PH_PID", 2898, "PID", "PID"),
    ("IDS_PH_MENU_COPY", 2899, "&Copy", "复制(&C)"),
    ("IDS_PH_CONFIRM_JOB_OBJECT", 2900, "the job", "该作业"),
    ("IDS_PH_CONFIRM_JOB_TERMINATION_WARNING", 2901, "Terminating a job will terminate all processes assigned to it.", "终止作业将终止分配给该作业的所有进程。"),
    ("IDS_PH_CONFIRM_SELECTED_PROCESSES_OBJECT", 2902, "the selected process(es)", "所选进程"),
    ("IDS_PH_ACTION_WRITE", 2903, "write", "写入"),
    ("IDS_PH_PROCESS_MEMORY_OBJECT", 2904, "process memory", "进程内存"),
    ("IDS_PH_MEMORY_EDIT_WARNING", 2905, "Some programs may restrict access or ban your account when editing the memory of the process.", "编辑进程内存时，某些程序可能会限制访问或封禁你的账户。"),
)

TABLE_ROUTES = {
    "envdlg.c": {"IDS_PH_TOKEN_NAME": 1, "IDS_PH_VALUE": 2},
    "jobprp.c": {"IDS_PH_TOKEN_NAME": 2, "IDS_PH_VALUE": 1},
    "sessprp.c": {"IDS_PH_TOKEN_NAME": 1, "IDS_PH_VALUE": 1},
    "prpgenv.c": {"IDS_PH_TOKEN_NAME": 1, "IDS_PH_VALUE": 1},
    "hndlstat.c": {"IDS_PH_TOKEN_TYPE": 1, "IDS_PH_HANDLE_COUNT": 1},
    "chproc.c": {"IDS_PH_TOKEN_NAME": 1, "IDS_PH_PID": 1, "IDS_PH_SESSION_USER_NAME": 1},
    "hndlprp.c": {"IDS_PH_VALUE": 3},
    "ntobjprp.c": {"IDS_PH_VALUE": 1},
    "options.c": {"IDS_PH_VALUE": 1},
    "prpgstat.c": {"IDS_PH_VALUE": 1},
    "tokprp.c": {"IDS_PH_VALUE": 3},
}

COPY_COUNTS = {
    "gdihndl.c": 1,
    "hndlprp.c": 3,
    "logwnd.c": 1,
    "memmod.c": 1,
    "pagfiles.c": 1,
    "prpgstat.c": 1,
    "sessprp.c": 1,
    "jobprp.c": 1,
    "hidnproc.c": 1,
    "ntobjprp.c": 2,
    "prpgenv.c": 1,
    "prpgvdm.c": 1,
    "prpgwmi.c": 1,
    "srvctl.c": 1,
    "tokprp.c": 3,
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("small_menu_table_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class SystemInformerSmallMenuTableResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def test_new_resources_are_contiguous_and_bilingual(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_STRINGS$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3340$")
        self.assertEqual(1340, len(english))
        self.assertEqual(1340, len(chinese))

    def test_table_columns_use_exact_stable_application_resources(self) -> None:
        for file_name, routes in TABLE_ROUTES.items():
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            for symbol, count in routes.items():
                self.assertEqual(count, len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", source)), (file_name, symbol))

    def test_copy_and_confirmation_calls_use_exact_resources(self) -> None:
        for file_name, count in COPY_COUNTS.items():
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            self.assertEqual(count, len(re.findall(r"PhCreateEMenuItem\([^;]*PhGetApplicationUiString\(IDS_PH_MENU_COPY\)", source)), file_name)

        expected = {
            "jobprp.c": ("IDS_PH_ACTION_TERMINATE", "IDS_PH_CONFIRM_JOB_OBJECT", "IDS_PH_CONFIRM_JOB_TERMINATION_WARNING", "TRUE"),
            "hidnproc.c": ("IDS_PH_ACTION_TERMINATE", "IDS_PH_CONFIRM_SELECTED_PROCESSES_OBJECT", "IDS_PH_ZOMBIE_TERMINATION_WARNING", "TRUE"),
            "memedit.c": ("IDS_PH_ACTION_WRITE", "IDS_PH_PROCESS_MEMORY_OBJECT", "IDS_PH_MEMORY_EDIT_WARNING", "FALSE"),
        }
        for file_name, symbols in expected.items():
            source = self.audit.mask_c_comments((APP_ROOT / file_name).read_text(encoding="utf-8-sig"))
            calls = [args for name, args, _spans, _start in self.audit.find_calls(source, {"PhShowConfirmMessage"})]
            expected_args = tuple(
                symbol if symbol in {"TRUE", "FALSE"} else f"PhGetApplicationUiString({symbol})"
                for symbol in symbols
            )
            normalized_calls = [
                tuple(re.sub(r"\s+", "", arg) for arg in args[1:5])
                for args in calls
            ]
            self.assertIn(expected_args, normalized_calls, file_name)

    def test_targeted_fresh_scan_has_no_selected_literals(self) -> None:
        files = set(TABLE_ROUTES) | set(COPY_COUNTS) | {"memedit.c"}
        targets_by_file = {
            "envdlg.c": {"Name", "Value"},
            "jobprp.c": {"Name", "Value", "&Copy", "terminate", "the job", "Terminating a job will terminate all processes assigned to it."},
            "sessprp.c": {"Name", "Value", "&Copy"},
            "prpgenv.c": {"Name", "Value", "&Copy"},
            "hndlstat.c": {"Type", "Count"},
            "chproc.c": {"Name", "PID", "User name"},
            "gdihndl.c": {"&Copy"},
            "hndlprp.c": {"&Copy", "Value"},
            "ntobjprp.c": {"&Copy", "Value"},
            "options.c": {"Value"},
            "prpgvdm.c": {"&Copy"},
            "prpgwmi.c": {"&Copy"},
            "srvctl.c": {"&Copy"},
            "tokprp.c": {"&Copy", "Value"},
            "logwnd.c": {"&Copy"},
            "memmod.c": {"&Copy"},
            "pagfiles.c": {"&Copy"},
            "prpgstat.c": {"&Copy", "Value"},
            "hidnproc.c": {"&Copy", "terminate", "the selected process(es)"},
            "memedit.c": {"write", "process memory", "Some programs may restrict access or ban your account when editing the memory of the process."},
        }
        unresolved = []
        for file_name in sorted(files):
            entries = []
            self.audit.scan_c_file(str(APP_ROOT / file_name), entries)
            unresolved.extend(
                entry for entry in entries
                if entry["category"] in {"c_emenu", "c_confirm", "c_listview_col", "c_treenew_col"}
                and entry["english"] in targets_by_file[file_name]
            )
        self.assertEqual([], unresolved)

    def test_json_moves_new_strings_to_native_layer(self) -> None:
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        for _symbol, _resource_id, english, chinese in NEW_RESOURCES:
            self.assertEqual(chinese, data["native_strings"].get(english))
            self.assertNotIn(english, data["strings"])


if __name__ == "__main__":
    unittest.main()
