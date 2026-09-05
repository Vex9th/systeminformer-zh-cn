import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def read_wizard_source() -> str:
    audit_path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("setup_wizard_dpi_audit", audit_path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    return audit.mask_c_comments(
        (REPO_ROOT / "tools" / "CustomSetupTool" / "wizard.c").read_text(
            encoding="utf-8-sig"
        )
    )


def function_body(source: str, name: str) -> str:
    match = re.search(rf"(?:static\s+)?\w+\s+{name}\(.*?\n\}}", source, re.DOTALL)
    if not match:
        raise AssertionError(f"missing function: {name}")
    return match.group(0)


class SetupWizardDpiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = read_wizard_source()

    def test_fonts_derive_from_the_dpi_aware_system_message_font(self) -> None:
        create_font = function_body(self.source, "SetupCreateWizardFont")
        create_fonts = function_body(self.source, "SetupCreateWizardFonts")

        self.assertIn("CreateFontIndirect", create_font)
        self.assertIn(
            "PhMultiplyDivideSigned(Height, WindowDpi, USER_DEFAULT_SCREEN_DPI)",
            create_font,
        )
        self.assertNotIn("-PhMultiplyDivideSigned", create_font)
        self.assertIn("SPI_GETNONCLIENTMETRICS", create_fonts)
        self.assertIn("metrics.lfMessageFont", create_fonts)
        for face_name in ("Segoe UI", "Tahoma", "Verdana", "MS Shell Dlg"):
            self.assertNotIn(face_name, create_fonts)

    def test_welcome_bitmaps_reload_and_release_owned_handles(self) -> None:
        loader = function_body(self.source, "SetupLoadWelcomeBitmap")
        destroy = function_body(self.source, "SetupDestroyWizardPage")

        self.assertIn("STM_SETIMAGE", loader)
        self.assertIn("oldBitmapHandle = (HBITMAP)SendMessage", loader)
        self.assertIn("STM_GETIMAGE", loader)
        self.assertIn("SETUP_WINDOW_CONTEXT_WELCOME_BITMAP", loader)
        self.assertIn("DeleteBitmap", loader)
        self.assertIn("SETUP_WINDOW_CONTEXT_WELCOME_BITMAP", destroy)
        self.assertIn("DeleteBitmap", destroy)

        set_bitmap = loader.index("oldBitmapHandle = (HBITMAP)SendMessage")
        get_bitmap = loader.index("STM_GETIMAGE")
        restore = loader.index(
            "STM_SETIMAGE, IMAGE_BITMAP, (LPARAM)oldBitmapHandle"
        )
        get_restored_bitmap = loader.index("STM_GETIMAGE", get_bitmap + 1)
        track_restored_bitmap = loader.index(
            "SETUP_WINDOW_CONTEXT_WELCOME_BITMAP, currentBitmapHandle",
            get_restored_bitmap,
        )
        track_bitmap = loader.index(
            "SETUP_WINDOW_CONTEXT_WELCOME_BITMAP, currentBitmapHandle",
            track_restored_bitmap + 1,
        )
        delete_restored_input = loader.index(
            "DeleteBitmap(oldBitmapHandle)", track_restored_bitmap
        )
        delete_old_bitmap = loader.index("DeleteBitmap(oldBitmapHandle)", track_bitmap)
        self.assertLess(set_bitmap, get_bitmap)
        self.assertLess(get_bitmap, restore)
        self.assertLess(restore, get_restored_bitmap)
        self.assertLess(get_restored_bitmap, track_restored_bitmap)
        self.assertLess(track_restored_bitmap, delete_restored_input)
        self.assertLess(get_bitmap, track_bitmap)
        self.assertLess(track_bitmap, delete_old_bitmap)
        self.assertRegex(
            loader,
            re.compile(
                r"if\s*\(currentBitmapHandle\).*?"
                r"PhSetWindowContext\(.*?currentBitmapHandle\);.*?"
                r"if\s*\(currentBitmapHandle\s*!=\s*oldBitmapHandle\)\s*"
                r"DeleteBitmap\(oldBitmapHandle\);",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            loader,
            re.compile(
                r"else\s*\{\s*"
                r"PhRemoveWindowContext\(WindowHandle,\s*"
                r"SETUP_WINDOW_CONTEXT_WELCOME_BITMAP\);\s*"
                r"DeleteBitmap\(oldBitmapHandle\);",
                re.DOTALL,
            ),
        )

        for procedure in (
            "SetupWelcomePageDlgProc",
            "SetupCompletedPageDlgProc",
            "SetupErrorPageDlgProc",
        ):
            body = function_body(self.source, procedure)
            dpi_case = re.search(
                r"case WM_DPICHANGED_AFTERPARENT:.*?break;", body, re.DOTALL
            )
            self.assertIsNotNone(dpi_case, procedure)
            self.assertIn("SetupLoadWelcomeBitmap(WindowHandle)", dpi_case.group(0))

    def test_window_and_page_icons_are_replaced_at_the_current_dpi(self) -> None:
        update_icons = function_body(self.source, "SetupUpdateWizardIcons")
        initialize_title = function_body(self.source, "SetupInitializeWizardTitleFont")
        welcome = function_body(self.source, "SetupWelcomePageDlgProc")
        prop_sheet = function_body(self.source, "PvpPropSheetWndProc")
        show_wizard = function_body(self.source, "SetupShowWizard")

        self.assertEqual(update_icons.count("PhLoadIcon("), 2)
        self.assertIn("WM_SETICON", update_icons)
        self.assertIn("IDC_PAGEICON", update_icons)
        self.assertIn("STM_SETICON", update_icons)
        self.assertIn("DestroyIcon", update_icons)
        self.assertIn("IDC_PAGEICON", initialize_title)
        self.assertIn("STM_SETICON", initialize_title)

        reject_partial = update_icons.index("if (!newLargeIcon || !newSmallIcon)")
        publish = update_icons.index("Context->IconLargeHandle = newLargeIcon")
        destroy = update_icons.index("DestroyIcon(oldLargeIcon)")
        self.assertLess(reject_partial, publish)
        self.assertLess(publish, destroy)
        self.assertLess(update_icons.rindex("WM_SETICON"), destroy)
        self.assertLess(update_icons.rindex("STM_SETICON"), destroy)

        self.assertIn(
            "SetupUpdateWizardIcons(\n"
            "                context,\n"
            "                context->ParentWindowHandle,\n"
            "                PhGetWindowDpi(context->ParentWindowHandle)",
            welcome,
        )
        dpi_case = re.search(r"case WM_DPICHANGED:.*?return result;", prop_sheet, re.DOTALL)
        self.assertIsNotNone(dpi_case)
        self.assertIn("SetupUpdateWizardIcons", dpi_case.group(0))
        self.assertNotIn("PhGetMonitorDpi(NULL, NULL)", show_wizard)
        self.assertEqual(show_wizard.count("SetupDestroyWizardIcons(Context)"), 2)


if __name__ == "__main__":
    unittest.main()
