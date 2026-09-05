#!/usr/bin/env python3

import importlib.util
import pathlib
import unittest
import xml.etree.ElementTree as ET


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FontDpiContractTests(unittest.TestCase):
    def test_native_localization_preserves_dialog_font_and_dlu_structure(self) -> None:
        generator = load_module(
            "generate_native_resources_font_contract",
            "tools/zhcn/generate_native_resources.py",
        )
        source = [
            "IDD_SAMPLE DIALOGEX 0, 0, 120, 40",
            "STYLE DS_SETFONT | WS_POPUP",
            'CAPTION "Options"',
            'FONT 8, "MS Shell Dlg", 400, 0, 0x0',
            "BEGIN",
            '    LTEXT "General",IDC_STATIC,6,8,100,12',
            "END",
        ]

        localized = generator.localize_dialog_block(
            source,
            {"Options": "选项", "General": "常规"},
        )

        self.assertEqual(localized[0:2], source[0:2])
        self.assertEqual(localized[3], source[3])
        self.assertEqual(localized[4], source[4])
        self.assertEqual(localized[6], source[6])
        self.assertEqual(localized[2], 'CAPTION "选项"')
        self.assertEqual(localized[5], '    LTEXT "常规",IDC_STATIC,6,8,100,12')

    def test_compiled_validator_requires_identical_font_metrics(self) -> None:
        validator = load_module(
            "validate_templates_font_contract",
            "tools/zhcn/validate_templates.py",
        )
        validator_source = (
            REPO_ROOT / "tools" / "zhcn" / "validate_templates.py"
        ).read_text(encoding="utf-8-sig")
        english = (8, 400, 0, 0, "MS Shell Dlg")

        self.assertEqual(
            validator.dialog_font_attributes(english),
            validator.dialog_font_attributes(english),
        )
        self.assertNotEqual(
            validator.dialog_font_attributes(english),
            validator.dialog_font_attributes((9, 400, 0, 0, "MS Shell Dlg")),
        )
        self.assertNotEqual(
            validator.dialog_font_attributes(english),
            validator.dialog_font_attributes((8, 400, 0, 0, "Microsoft YaHei UI")),
        )
        self.assertNotEqual(
            validator.dialog_font_attributes(english),
            validator.dialog_font_attributes((8, 400, 0, 1, "MS Shell Dlg")),
        )
        self.assertNotIn('font[-1] != "Microsoft YaHei UI"', validator_source)
        self.assertNotIn("font[0] < 9", validator_source)

    def test_runtime_fallback_preserves_template_font_bytes(self) -> None:
        source = (REPO_ROOT / "phlib" / "phtranslation.c").read_text(
            encoding="utf-8-sig"
        )
        start = source.index("PVOID PhTranslateDialogTemplateCopy(")
        end = source.index("PVOID PhTranslateDialogTemplateCached(", start)
        body = source[start:end]

        self.assertIn("PhTlpWrite(&writer, (PVOID)cursor, 6);", body)
        self.assertIn("PhTlpWrite(&writer, (PVOID)cursor, 2);", body)
        self.assertIn(
            "PhTlpCopyTemplateString(&writer, &cursor); // typeface",
            body,
        )
        self.assertNotIn("pointSize < 9", body)
        self.assertNotIn("Microsoft YaHei UI", body)

    def test_standalone_gui_manifests_keep_per_monitor_legacy_fallback(self) -> None:
        for relative_path in (
            "tools/peview/peview.manifest",
            "tools/CustomSetupTool/app.manifest",
        ):
            with self.subTest(manifest=relative_path):
                root = ET.parse(REPO_ROOT / relative_path).getroot()
                dpi_aware = [
                    element.text
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "dpiAware"
                ]
                dpi_awareness = [
                    element.text
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "dpiAwareness"
                ]

                self.assertEqual(dpi_aware, ["true/pm"])
                self.assertEqual(dpi_awareness, ["PerMonitorV2, PerMonitor"])


if __name__ == "__main__":
    unittest.main()
