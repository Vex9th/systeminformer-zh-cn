import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def read_c_source(relative_path: str) -> str:
    audit_path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("peview_dpi_audit", audit_path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    return audit.mask_c_comments(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
    )


class PeviewDpiContractTests(unittest.TestCase):
    def test_peview_rebinds_font_before_deleting_old_handle(self) -> None:
        source = read_c_source("tools/peview/prpsh.c")
        function = re.search(
            r"VOID PvpInitializeFont\(.*?\n\}", source, re.DOTALL
        )

        self.assertIsNotNone(function)
        body = function.group(0)
        self.assertNotIn("DeleteFont(PhApplicationFont)", body)
        self.assertNotIn("PhReInitializeWindowTheme", body)
        self.assertIn("if (!newFont)", body)

        create = body.index("newFont = PhCreateMessageFont")
        fail = body.index("if (!newFont)")
        capture = body.index("oldFont = PhApplicationFont")
        publish = body.index("PhApplicationFont = newFont")
        rebind = body.index(
            "SetWindowFont(PropSheet_GetTabControl(hwnd), newFont, TRUE)"
        )
        delete = body.index("DeleteFont(oldFont)")
        self.assertLess(create, fail)
        self.assertLess(fail, capture)
        self.assertLess(capture, publish)
        self.assertLess(publish, rebind)
        self.assertLess(rebind, delete)

    def test_peview_dpi_change_requests_font_rebinding(self) -> None:
        source = read_c_source("tools/peview/prpsh.c")
        dpi_case = re.search(
            r"case WM_DPICHANGED:.*?break;", source, re.DOTALL
        )

        self.assertIsNotNone(dpi_case)
        self.assertIn("PvpInitializeFont(hWnd)", dpi_case.group(0))
        self.assertIn("PvpInitializeFont(hwndDlg)", source)
        self.assertEqual(source.count("PvpInitializeFont("), 3)


if __name__ == "__main__":
    unittest.main()
