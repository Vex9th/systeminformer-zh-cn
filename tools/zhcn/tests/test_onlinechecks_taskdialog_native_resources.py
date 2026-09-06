#!/usr/bin/env python3
"""Regression coverage for OnlineChecks TaskDialog native resources."""

import importlib.util
import re
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "OnlineChecks"
AUDIT_PATH = REPO_ROOT / "tools" / "zhcn" / "audit.py"

RESOURCES = {
    "IDS_OC_BUTTON_VIEW_LAST_ANALYSIS": (
        12006,
        "View last analysis\nView the last or outdated analysis page",
        "查看上次分析\n查看上次或过期的分析页面",
    ),
    "IDS_OC_BUTTON_UPLOAD_FILE": (
        12007,
        "Upload file\nUpload fresh sample for updated analysis",
        "上传文件\n上传新样本以获取最新分析",
    ),
    "IDS_OC_UPLOADING_FORMAT": (12008, "Uploading %s...", "正在上传 %s..."),
    "IDS_OC_LAST_ANALYZED_FORMAT": (
        12009,
        "%s was last analyzed %s",
        "%s 上次分析于 %s",
    ),
    "IDS_OC_DETECTIONS_LABEL": (12010, "Detections:", "检测结果："),
    "IDS_OC_FIRST_ANALYZED_LABEL": (12011, "First analyzed:", "首次分析："),
    "IDS_OC_LAST_ANALYZED_LABEL": (12012, "Last analyzed:", "上次分析："),
    "IDS_OC_UPLOAD_SIZE_LABEL": (12013, "Upload size:", "上传大小："),
    "IDS_OC_ANALYSIS_ACTION_PROMPT": (
        12014,
        "You can take a look at the last analysis or upload it again now.",
        "你可以查看上次分析，或立即重新上传。",
    ),
    "IDS_OC_RESCANNING_FORMAT": (12015, "Rescanning %s...", "正在重新扫描 %s..."),
    "IDS_OC_LOCATING_ANALYSIS_FORMAT": (
        12016,
        "Locating analysis for %s...",
        "正在查找 %s 的分析结果...",
    ),
    "IDS_OC_UPLOAD_ERROR_FORMAT": (
        12017,
        "Error uploading %s...",
        "上传 %s 时出错...",
    ),
}

EXPECTED_SOURCE_ROUTES = Counter({
    "IDS_OC_UPLOADING_FORMAT": 4,
    **{resource_id: 1 for resource_id in RESOURCES if resource_id != "IDS_OC_UPLOADING_FORMAT"},
})


def load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "zhcn_audit_onlinechecks_taskdialog",
        AUDIT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: Path):
    return {
        resource_id: value.replace('""', '"').replace(r"\n", "\n")
        for resource_id, value in re.findall(
            r'(?m)^\s*(IDS_OC_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
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


class OnlineChecksTaskDialogNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            path.name: path.read_text(encoding="utf-8-sig")
            for path in PLUGIN_ROOT.glob("*.c")
        }

    def test_resources_are_contiguous_bilingual_and_exact_count(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "OnlineChecks.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "OnlineChecks.zh-cn.rc")

        for resource_id, (numeric_id, english_text, chinese_text) in RESOURCES.items():
            with self.subTest(resource_id=resource_id):
                self.assertRegex(
                    header,
                    rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$",
                )
                self.assertEqual(english.get(resource_id), english_text)
                self.assertEqual(chinese.get(resource_id), chinese_text)
                english_specifiers = self.audit.PRINTF_SPEC_RE.findall(english_text)
                chinese_specifiers = self.audit.PRINTF_SPEC_RE.findall(chinese_text)
                self.assertEqual(
                    [item for item in english_specifiers if item != "%%"],
                    [item for item in chinese_specifiers if item != "%%"],
                )

        self.assertEqual(22, len(english))
        self.assertEqual(22, len(chinese))
        self.assertRegex(
            header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12022$",
        )

    def test_every_target_uses_the_plugin_resource_and_leaves_no_c_literal(self) -> None:
        source = "\n".join(
            self.audit.mask_c_comments(text) for text in self.sources.values()
        )
        actual_routes = Counter(re.findall(r"\b(IDS_OC_[A-Z0-9_]+)\b", source))
        self.assertEqual(
            EXPECTED_SOURCE_ROUTES,
            Counter({
                resource_id: actual_routes[resource_id]
                for resource_id in EXPECTED_SOURCE_ROUTES
            }),
        )

        for _resource_id, (_numeric_id, english_text, _chinese_text) in RESOURCES.items():
            with self.subTest(english_text=english_text):
                self.assertNotIn(english_text, source)

    def test_loaded_text_lifetimes_cover_navigation_and_worker_update(self) -> None:
        page2 = function_body(
            self.audit.mask_c_comments(self.sources["page2.c"]),
            "ShowFileFoundDialog",
        )
        self.assertNotRegex(page2, r"static\s+TASKDIALOG_BUTTON\s+TaskDialogButtonArray")
        self.assertEqual(2, page2.count("PhLoadUiString(PluginInstance->DllBase, IDS_OC_BUTTON_"))
        routes = {
            "viewLastAnalysisText": "IDS_OC_BUTTON_VIEW_LAST_ANALYSIS",
            "uploadFileText": "IDS_OC_BUTTON_UPLOAD_FILE",
            "lastAnalyzedFormat": "IDS_OC_LAST_ANALYZED_FORMAT",
            "detectionsLabel": "IDS_OC_DETECTIONS_LABEL",
            "firstAnalyzedLabel": "IDS_OC_FIRST_ANALYZED_LABEL",
            "lastAnalyzedLabel": "IDS_OC_LAST_ANALYZED_LABEL",
            "uploadSizeLabel": "IDS_OC_UPLOAD_SIZE_LABEL",
            "analysisActionPrompt": "IDS_OC_ANALYSIS_ACTION_PROMPT",
        }
        for variable, resource in routes.items():
            with self.subTest(variable=variable):
                self.assertIn(
                    f"{variable} = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, {resource}, NULL));",
                    page2,
                )
                self.assertIn(f"PhGetStringOrEmpty({variable})", page2)
        self.assertEqual(
            page2.count("= PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_"),
            len(routes),
        )
        self.assertIn(
            "TaskDialogButtonArray[0].pszButtonText = PhGetStringOrEmpty(viewLastAnalysisText);",
            page2,
        )
        self.assertIn(
            "TaskDialogButtonArray[1].pszButtonText = PhGetStringOrEmpty(uploadFileText);",
            page2,
        )
        self.assertRegex(
            page2,
            re.compile(
                r"TASKDIALOG_BUTTON\s+TaskDialogButtonArray\[\]\s*=\s*\{\s*"
                r"\{\s*IDYES\s*,\s*NULL\s*\}\s*,\s*"
                r"\{\s*IDOK\s*,\s*NULL\s*\}\s*,?\s*\}\s*;",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            page2,
            r"PhaFormatString\(\s*PhGetStringOrEmpty\(lastAnalyzedFormat\),\s*"
            r"PhGetStringOrEmpty\(Context->BaseFileName\),\s*"
            r"PhGetStringOrEmpty\(Context->LastAnalysisDate\)",
        )
        self.assertRegex(
            page2,
            re.compile(
                r'PhaFormatString\(\s*L"%s %s\\r\\n%s %s\\r\\n%s %s\\r\\n%s %s\\r\\n\\r\\n%s"\s*,\s*'
                r"PhGetStringOrEmpty\(detectionsLabel\)\s*,\s*PhGetStringOrEmpty\(Context->Detected\)\s*,\s*"
                r"PhGetStringOrEmpty\(firstAnalyzedLabel\)\s*,\s*PhGetStringOrEmpty\(Context->FirstAnalysisDate\)\s*,\s*"
                r"PhGetStringOrEmpty\(lastAnalyzedLabel\)\s*,\s*PhGetStringOrEmpty\(Context->LastAnalysisDate\)\s*,\s*"
                r"PhGetStringOrEmpty\(uploadSizeLabel\)\s*,\s*PhGetStringOrEmpty\(Context->FileSize\)\s*,\s*"
                r"PhGetStringOrEmpty\(analysisActionPrompt\)",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            page2,
            re.compile(
                r'PhaFormatString\(\s*L"%s %s\\r\\n%s %s\\r\\n\\r\\n%s"\s*,\s*'
                r"PhGetStringOrEmpty\(detectionsLabel\)\s*,\s*PhGetStringOrEmpty\(Context->Detected\)\s*,\s*"
                r"PhGetStringOrEmpty\(uploadSizeLabel\)\s*,\s*PhGetStringOrEmpty\(Context->FileSize\)\s*,\s*"
                r"PhGetStringOrEmpty\(analysisActionPrompt\)",
                re.DOTALL,
            ),
        )
        self.assertLess(page2.index("IDS_OC_BUTTON_VIEW_LAST_ANALYSIS"), page2.index("PhTaskDialogNavigatePage"))

        upload = function_body(self.sources["upload.c"], "UploadFileThreadStart")
        load_index = upload.index("IDS_OC_UPLOADING_FORMAT")
        format_index = upload.index("msg = PhFormatString", load_index)
        update_index = upload.index("TDM_UPDATE_ELEMENT_TEXT", load_index)
        message_release_index = upload.index("PhClearReference(&msg)", update_index)
        format_release_index = upload.index("PhClearReference(&uploadingFormat)", update_index)
        self.assertLess(load_index, format_index)
        self.assertLess(format_index, update_index)
        self.assertLess(update_index, message_release_index)
        self.assertLess(message_release_index, format_release_index)
        self.assertIn("PhGetStringOrEmpty(uploadingFormat)", upload)
        self.assertIn("PhGetStringOrEmpty(msg)", upload)

    def test_onlinechecks_taskdialog_migration_gaps_are_zero(self) -> None:
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)

        gaps = [
            entry
            for entry in entries
            if entry["category"] in {"c_runtime_composed", "c_taskdialog_raw"}
        ]
        self.assertEqual([], gaps)


if __name__ == "__main__":
    unittest.main()
