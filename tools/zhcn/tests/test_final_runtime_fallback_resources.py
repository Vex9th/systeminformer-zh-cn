#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("final_runtime_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinalRuntimeFallbackResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()

    def test_process_started_time_uses_existing_native_format(self) -> None:
        source = (REPO_ROOT / "SystemInformer" / "prpggen.c").read_text(encoding="utf-8-sig")
        self.assertIn(
            "PhGetApplicationUiString(IDS_PH_RELATIVE_AND_ABSOLUTE_TIME_FORMAT)",
            source,
        )
        entries = []
        self.audit.scan_c_file(str(REPO_ROOT / "SystemInformer" / "prpggen.c"), entries)
        self.assertFalse([entry for entry in entries if entry["category"] == "c_runtime_composed"])

    def test_phlib_close_fallback_is_outside_the_window_text_sink(self) -> None:
        source = (REPO_ROOT / "phlib" / "guisup.c").read_text(encoding="utf-8-sig")
        helper = re.search(
            r"static\s+PPH_STRING\s+PhpLoadPropSheetCloseText\s*\([^{}]*\)\s*\{(.*?)\n\}",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(helper)
        self.assertIn("IDS_PH_CLOSE", helper.group(1))
        self.assertIn('PhCreateString(L"Close")', helper.group(1))
        self.assertIn("closeText = PhpLoadPropSheetCloseText();", source)
        self.assertIn("PhSetDialogItemText(\n                hwndDlg,\n                IDCANCEL,\n                closeText->Buffer", source)

        entries = []
        self.audit.scan_c_file(str(REPO_ROOT / "phlib" / "guisup.c"), entries)
        self.assertFalse([entry for entry in entries if entry["category"] == "c_window_text"])


if __name__ == "__main__":
    unittest.main()
