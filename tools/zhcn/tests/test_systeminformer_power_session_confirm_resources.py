#!/usr/bin/env python3

import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_CONFIRM_COMPUTER_OBJECT", 2950, "the computer", "该计算机"),
    ("IDS_PH_ACTION_UPDATE_AND_RESTART", 2951, "update and restart", "更新并重启"),
    ("IDS_PH_CONFIRM_DEFENDER_OFFLINE_COMPUTER_OBJECT", 2952, "the computer for Windows Defender Offline Scan", "该计算机以运行 Windows Defender 脱机扫描"),
    ("IDS_PH_ACTION_SHUT_DOWN", 2953, "shut down", "关闭"),
    ("IDS_PH_ACTION_UPDATE_AND_SHUTDOWN", 2954, "update and shutdown", "更新并关闭"),
    ("IDS_PH_ACTION_LOGOFF", 2955, "logoff", "注销"),
    ("IDS_PH_CONFIRM_USER_OBJECT", 2956, "the user", "该用户"),
)

ROUTES = {
    "IDS_PH_ACTION_RESTART": 9,
    "IDS_PH_CONFIRM_COMPUTER_OBJECT": 12,
    "IDS_PH_ACTION_UPDATE_AND_RESTART": 1,
    "IDS_PH_CONFIRM_DEFENDER_OFFLINE_COMPUTER_OBJECT": 1,
    "IDS_PH_ACTION_SHUT_DOWN": 3,
    "IDS_PH_ACTION_UPDATE_AND_SHUTDOWN": 1,
    "IDS_PH_ACTION_LOGOFF": 1,
    "IDS_PH_CONFIRM_USER_OBJECT": 1,
}

MIGRATED_KEYS = {
    "restart",
    *(english for _symbol, _resource_id, english, _chinese in NEW_RESOURCES),
}


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class SystemInformerPowerSessionConfirmResourcesTests(unittest.TestCase):
    def test_resources_are_contiguous_bilingual_and_native_owned(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))

        self.assertEqual(984, len(english))
        self.assertEqual(984, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_CONFIRM_EXECUTION_REQUIRED_WARNING$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+2984$")

        for en in MIGRATED_KEYS:
            self.assertIn(en, data["native_strings"])
            self.assertNotIn(en, data["strings"])

    def test_all_29_confirm_arguments_use_application_resources(self) -> None:
        source = (APP_ROOT / "actions.c").read_text(encoding="utf-8-sig")
        pairs = Counter(re.findall(
            r"PhShowConfirmMessage\(\s*WindowHandle,\s*PhGetApplicationUiString\(\s*(IDS_PH_[A-Z0-9_]+)\s*\),\s*PhGetApplicationUiString\(\s*(IDS_PH_[A-Z0-9_]+)\s*\),",
            source,
            re.S,
        ))
        migrated_symbols = set(ROUTES)
        migrated_pairs = Counter({pair: count for pair, count in pairs.items() if pair[0] in migrated_symbols or pair[1] in migrated_symbols})
        self.assertEqual(
            Counter({
                ("IDS_PH_ACTION_RESTART", "IDS_PH_CONFIRM_COMPUTER_OBJECT"): 7,
                ("IDS_PH_ACTION_UPDATE_AND_RESTART", "IDS_PH_CONFIRM_COMPUTER_OBJECT"): 1,
                ("IDS_PH_ACTION_RESTART", "IDS_PH_CONFIRM_DEFENDER_OFFLINE_COMPUTER_OBJECT"): 1,
                ("IDS_PH_ACTION_SHUT_DOWN", "IDS_PH_CONFIRM_COMPUTER_OBJECT"): 3,
                ("IDS_PH_ACTION_UPDATE_AND_SHUTDOWN", "IDS_PH_CONFIRM_COMPUTER_OBJECT"): 1,
                ("IDS_PH_ACTION_LOGOFF", "IDS_PH_CONFIRM_USER_OBJECT"): 1,
            }),
            migrated_pairs,
        )
        self.assertEqual(1, len(re.findall(
            r"PhShowConfirmMessageRawObject\(\s*WindowHandle,\s*PhGetApplicationUiString\(\s*IDS_PH_ACTION_RESTART\s*\),\s*Process->ProcessName->Buffer,",
            source,
            re.S,
        )))

    def test_migrated_confirm_literals_are_absent(self) -> None:
        occurrences = []
        for path in REPO_ROOT.rglob("*"):
            if path.suffix.lower() not in {".c", ".cc", ".cpp", ".cxx"}:
                continue
            if path == REPO_ROOT / "phlib" / "phtranslation_zhcn.c":
                continue
            source = path.read_text(encoding="utf-8-sig")
            for english in MIGRATED_KEYS:
                occurrences.extend(
                    (path.relative_to(REPO_ROOT).as_posix(), english)
                    for _match in re.finditer(rf'\bL"{re.escape(english)}"', source)
                )
        self.assertEqual([], occurrences)


if __name__ == "__main__":
    unittest.main()
