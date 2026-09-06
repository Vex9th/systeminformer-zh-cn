#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "UserNotes"

RESOURCES = (
    ("IDS_UN_COLUMN_TYPE", 2040, "Type", "类型"),
    ("IDS_UN_COLUMN_NAME", 2041, "Name", "名称"),
    ("IDS_UN_COLUMN_COMMENT", 2042, "Comment", "备注"),
    ("IDS_UN_COLUMN_PRIORITY", 2043, "Priority", "优先级"),
    ("IDS_UN_COLUMN_IO_PRIORITY", 2044, "IO priority", "IO 优先级"),
    ("IDS_UN_COLUMN_BACK_COLOR", 2045, "BackColor", "背景色"),
    ("IDS_UN_COLUMN_COLLAPSE", 2046, "Collapse", "折叠"),
    ("IDS_UN_COLUMN_AFFINITY", 2047, "Affinity", "处理器关联"),
    ("IDS_UN_COLUMN_PAGE_PRIORITY", 2048, "Page priority", "页优先级"),
    ("IDS_UN_COLUMN_EFFICIENCY", 2049, "Efficiency", "效率"),
    ("IDS_UN_MENU_DELETE", 2050, "&Delete", "删除(&D)"),
    ("IDS_UN_MENU_COPY", 2051, "&Copy", "复制(&C)"),
)

COLUMN_ROUTES = tuple((index + 1, width, row[0]) for index, (row, width) in enumerate(zip(RESOURCES[:10], (100, 100, 100, 80, 80, 80, 80, 80, 80, 80))))


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("usernotes_remaining_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_UN_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"function not found: {name}")
    opening = source.find("{", match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated function: {name}")


class UserNotesRemainingNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.main = cls.audit.mask_c_comments((PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig"))
        cls.options = cls.audit.mask_c_comments((PLUGIN_ROOT / "options.c").read_text(encoding="utf-8-sig"))

    def test_resources_extend_the_existing_tail_exactly(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "UserNotes.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "UserNotes.zh-cn.rc")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(r"(?m)^#define\s+(IDS_UN_[A-Z0-9_]+)\s+(\d+)$", header)
        }

        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(sorted(defines.values()), list(range(2000, 2052)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 52)
        self.assertEqual(len(chinese), 52)
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2052$")

    def test_columns_load_in_order_and_release_only_after_insert(self) -> None:
        body = function_body(self.options, "OptionsDlgProc")
        expected = tuple(
            (str(index), str(width), resource)
            for index, width, resource in COLUMN_ROUTES
        )
        actual = tuple(re.findall(
            r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(IDS_UN_COLUMN_[A-Z0-9_]+)\s*\}",
            body,
        ))
        self.assertEqual(actual, expected)
        self.assertRegex(
            body,
            r"columnText\s*=\s*PhLoadUiString\(\s*PluginInstance->DllBase,\s*columns\[i\]\.ResourceId,\s*NULL\s*\)",
        )
        insert = body.index("PhAddListViewColumn(", body.index("columnText ="))
        release = body.index("PhClearReference(&columnText);", insert)
        self.assertGreater(release, insert)
        self.assertIn("PhGetStringOrEmpty(columnText)", body[insert:release])

    def test_context_menu_owns_resource_text_through_show_and_destroy(self) -> None:
        body = function_body(self.options, "OptionsDlgProc")
        for variable, resource, item_id in (
            ("deleteMenuText", "IDS_UN_MENU_DELETE", "1"),
            ("copyMenuText", "IDS_UN_MENU_COPY", "PHAPP_IDC_COPY"),
        ):
            self.assertRegex(
                body,
                rf"{variable}\s*=\s*PhLoadUiString\(\s*PluginInstance->DllBase,\s*{resource},\s*NULL\s*\)",
            )
            self.assertRegex(
                body,
                rf"PhCreateEMenuItem\(0,\s*{item_id},\s*PhGetStringOrEmpty\({variable}\)",
            )
            self.assertEqual(body.count(f"PhClearReference(&{variable});"), 1)
            self.assertLess(body.index("PhShowEMenu("), body.index("PhDestroyEMenu(menu);"))
            self.assertLess(body.index("PhDestroyEMenu(menu);"), body.index(f"PhClearReference(&{variable});"))

        self.assertRegex(
            body,
            r"PhClearReference\(&copyMenuText\);\s*PhFree\(listviewItems\);\s*\}",
        )

    def test_affinity_information_reuses_existing_resource_and_is_null_safe(self) -> None:
        self.assertEqual(self.main.count("IDS_UN_UNABLE_QUERY_PROCESS_AFFINITY"), 4)
        for resource, count in (
            ("IDS_UN_UNABLE_QUERY_PROCESS_AFFINITY", 4),
            ("IDS_UN_MULTI_GROUP_AFFINITY", 2),
            ("IDS_UN_AFFINITY_INDIVIDUAL_THREADS", 2),
        ):
            pattern = (
                r"PhGetStringOrEmpty\(PH_AUTO\(PhLoadUiString\(\s*"
                rf"PluginInstance->DllBase,\s*{resource},\s*NULL\s*\)\)\)"
            )
            self.assertEqual(len(re.findall(pattern, self.main)), count)
        self.assertNotIn('L"Unable to query the current affinity."', self.main)

    def test_all_usernotes_runtime_dictionary_categories_are_empty(self) -> None:
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)
        runtime_categories = {"c_emenu", "c_listview_col", "c_msgbox", "c_taskdialog", "c_taskdialog_raw", "c_runtime_composed"}
        remaining = Counter(
            (entry["category"], entry["english"])
            for entry in entries
            if entry["category"] in runtime_categories
        )
        self.assertEqual(remaining, Counter())


if __name__ == "__main__":
    unittest.main()
