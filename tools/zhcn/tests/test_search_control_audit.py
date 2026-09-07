#!/usr/bin/env python3

import importlib.util
import pathlib
import unittest
from collections import Counter

try:
    from tools.zhcn.tests.temp_source import scan_temporary_source
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    from temp_source import scan_temporary_source


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
AUDIT_PATH = REPO_ROOT / "tools" / "zhcn" / "audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("search_control_audit", AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SearchControlAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def scan_source(self, source: str):
        entries = scan_temporary_source(self.audit.scan_c_file, source)
        return Counter(
            (entry["category"], entry["english"])
            for entry in entries
        )

    def test_search_scanner_ignores_native_getter_fallbacks_only(self) -> None:
        actual = self.scan_source(
            r'''
            void CreateSearchControls(void)
            {
                PhCreateSearchControl(parent, edit, L"Direct search", callback, NULL);
                PhCreateSearchControlEx(
                    parent,
                    edit,
                    ToolStatusGetUiString(IDS_SEARCH, L"Native fallback"),
                    callback,
                    LookupSetting(L"Hidden setting key")
                    );
            }
            '''
        )

        self.assertEqual(actual, Counter({("c_search", "Direct search"): 1}))

    def test_toolstatus_native_search_route_is_not_reported(self) -> None:
        entries = []
        self.audit.scan_c_file(
            str(REPO_ROOT / "plugins" / "ToolStatus" / "toolbar.c"),
            entries,
        )

        self.assertNotIn(
            ("c_search", "Search Processes (Ctrl+K)"),
            {(entry["category"], entry["english"]) for entry in entries},
        )


if __name__ == "__main__":
    unittest.main()
