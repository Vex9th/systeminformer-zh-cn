#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "UserNotes"


class UserNotesSharedLabelNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        cls.comment_page = (PLUGIN_ROOT / "prpcmpage.c").read_text(encoding="utf-8-sig")
        cls.header = (PLUGIN_ROOT / "usernotes.h").read_text(encoding="utf-8-sig")

    def test_helper_keeps_plugin_strings_alive_and_has_fallbacks(self):
        self.assertIn("PCWSTR UserNotesGetUiString(", self.header)
        self.assertIn("static PH_INITONCE UserNotesUiStringsInitOnce", self.main)
        self.assertIn("static PPH_STRING UserNotesUiStrings[", self.main)
        self.assertRegex(
            self.main,
            r"return\s+PhGetStringOrDefault\s*\(\s*UserNotesUiStrings"
            r"\[ResourceId\s*-\s*IDS_UN_COLUMN_COMMENT\]\s*,\s*Fallback\s*\)\s*;",
        )

    def test_tree_columns_and_property_title_use_native_resources(self):
        self.assertEqual(
            len(re.findall(r'column\.Text\s*=\s*UserNotesGetUiString\(IDS_UN_COLUMN_COMMENT, L"Comment"\);', self.main)),
            2,
        )
        self.assertIn(
            'affinity.Text = UserNotesGetUiString(IDS_UN_COLUMN_AFFINITY, L"Affinity");',
            self.main,
        )
        self.assertIn(
            'propSheetPage.pszTitle = UserNotesGetUiString(IDS_UN_COLUMN_COMMENT, L"Comment");',
            self.main,
        )
        self.assertNotRegex(self.main, r'(?:column|affinity)\.Text\s*=\s*L"(?:Comment|Affinity)"\s*;')

    def test_message_box_title_uses_the_same_native_resource(self):
        self.assertIn(
            'UserNotesGetUiString(IDS_UN_COLUMN_COMMENT, L"Comment"),',
            self.comment_page,
        )
        self.assertNotRegex(self.comment_page, r'MessageBox\([^;]*,\s*L"Comment"\s*,')


if __name__ == "__main__":
    unittest.main()
