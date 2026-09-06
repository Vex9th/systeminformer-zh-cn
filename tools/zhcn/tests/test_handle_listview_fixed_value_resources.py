#!/usr/bin/env python3

import json
import pathlib
import re
import subprocess
import sys
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"
TRANSLATION_SOURCE = REPO_ROOT / "phlib" / "phtranslation_zhcn.c"

NEW_RESOURCES = (
    ("IDS_PH_HANDLE_NOT_AVAILABLE_SNAPSHOT", 2650, "N/A (snapshot)", "不适用（快照）", "native_strings"),
    ("IDS_PH_HANDLE_PIPE", 2651, "Pipe", "管道", "native_strings"),
    ("IDS_PH_HANDLE_FILE_OR_DIRECTORY", 2652, "File or directory", "文件或目录", "native_strings"),
    ("IDS_PH_HANDLE_CONSOLE", 2653, "Console", "控制台", "native_strings"),
    ("IDS_PH_HANDLE_DIRECTORY", 2654, "Directory", "目录", "native_strings"),
    ("IDS_PH_HANDLE_IO_PRIORITY_VERY_LOW", 2655, "Very Low", "极低", "native_strings"),
    ("IDS_PH_HANDLE_IO_PRIORITY_LOW", 2656, "Low", "低", "strings"),
    ("IDS_PH_HANDLE_IO_PRIORITY_NORMAL", 2657, "Normal", "正常", "strings"),
    ("IDS_PH_HANDLE_IO_PRIORITY_HIGH", 2658, "High", "高", "strings"),
    ("IDS_PH_HANDLE_IO_PRIORITY_CRITICAL", 2659, "Critical", "关键", "strings"),
    ("IDS_PH_HANDLE_SECTION_COMMIT", 2660, "Commit", "提交", "strings"),
    ("IDS_PH_HANDLE_SECTION_IMAGE", 2661, "Image", "映像", "strings"),
    ("IDS_PH_HANDLE_SECTION_RESERVE", 2662, "Reserve", "保留", "native_strings"),
)

FIXED_VALUE_ROUTES = Counter({
    ("PH_HANDLE_GENERAL_INDEX_OBJECT", "IDS_PH_HANDLE_NOT_AVAILABLE_SNAPSHOT"): 1,
    ("PH_HANDLE_GENERAL_INDEX_OBJECT", "IDS_PH_NOT_AVAILABLE"): 1,
    ("PH_HANDLE_GENERAL_INDEX_ACCESSS", "IDS_PH_NOT_AVAILABLE"): 2,
    ("PH_HANDLE_GENERAL_INDEX_ACCESSGENERIC", "IDS_PH_NOT_AVAILABLE"): 1,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_HANDLE_PIPE"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_LOGON_NETWORK"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_HANDLE_FILE_OR_DIRECTORY"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_HANDLE_CONSOLE"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_STAT_OTHER"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_HANDLE_DIRECTORY"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_HANDLE_FILE"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILEPRIORITY", "IDS_PH_HANDLE_IO_PRIORITY_VERY_LOW"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILEPRIORITY", "IDS_PH_HANDLE_IO_PRIORITY_LOW"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILEPRIORITY", "IDS_PH_HANDLE_IO_PRIORITY_NORMAL"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILEPRIORITY", "IDS_PH_HANDLE_IO_PRIORITY_HIGH"): 2,
    ("PH_HANDLE_GENERAL_INDEX_FILEPRIORITY", "IDS_PH_HANDLE_IO_PRIORITY_CRITICAL"): 2,
    ("PH_HANDLE_GENERAL_INDEX_SECTIONFILE", "IDS_PH_NOT_AVAILABLE"): 1,
    ("PH_HANDLE_GENERAL_INDEX_SECTIONSIZE", "IDS_PH_UNKNOWN"): 1,
    ("PH_HANDLE_GENERAL_INDEX_MUTANTABANDONED", "IDS_PH_STATUS_TRUE"): 1,
    ("PH_HANDLE_GENERAL_INDEX_MUTANTABANDONED", "IDS_PH_STATUS_FALSE"): 1,
})

TARGET_LITERALS = (
    "N/A (snapshot)",
    "N/A",
    "Pipe",
    "Network",
    "File or directory",
    "Console",
    "Other",
    "Directory",
    "File",
    "Very Low",
    "Low",
    "Normal",
    "High",
    "Critical",
    "Unknown",
    "True",
    "False",
)


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


def split_arguments(arguments: str) -> list[str]:
    result = []
    start = 0
    depth = 0
    in_string = False
    escaped = False

    for index, character in enumerate(arguments):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
        elif character == "," and depth == 0:
            result.append(arguments[start:index].strip())
            start = index + 1

    result.append(arguments[start:].strip())
    return result


def call_arguments(source: str, name: str) -> list[list[str]]:
    calls = []

    for match in re.finditer(rf"\b{re.escape(name)}\s*\(", source):
        opening = source.find("(", match.start())
        depth = 0
        in_string = False
        escaped = False

        for index in range(opening, len(source)):
            character = source[index]
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
                continue

            if character == '"':
                in_string = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    calls.append(split_arguments(source[opening + 1:index]))
                    break

    return calls


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class HandleListViewFixedValueResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = (APP_ROOT / "hndlprp.c").read_text(encoding="utf-8-sig")
        cls.body = function_body(source, "PhpUpdateHandleGeneral")
        cls.calls = [
            arguments
            for arguments in call_arguments(cls.body, "PhSetHandleListViewItem")
            if len(arguments) == 4
        ]

    def test_fixed_values_use_exact_33_resource_routes(self) -> None:
        actual = []
        for arguments in self.calls:
            for resource_id in re.findall(
                r"PhGetApplicationUiString\((IDS_PH_[A-Z0-9_]+)\)",
                arguments[3],
            ):
                actual.append((arguments[1], resource_id))

        self.assertEqual(Counter(actual), FIXED_VALUE_ROUTES)
        self.assertEqual(len(actual), 33)
        self.assertEqual(
            sum(
                bool(re.search(r"PhGetApplicationUiString\(IDS_PH_[A-Z0-9_]+\)", arguments[3]))
                for arguments in self.calls
            ),
            30,
        )

        target_pattern = "|".join(
            sorted(map(re.escape, TARGET_LITERALS), key=len, reverse=True)
        )
        for arguments in self.calls:
            self.assertNotRegex(arguments[3], rf'L"(?:{target_pattern})"')

    def test_section_type_is_a_closed_five_resource_state(self) -> None:
        start = self.body.index("PCWSTR sectionType")
        end = self.body.index("sectionSize = PhaFormatSize", start)
        section_type = self.body[start:end]

        self.assertCountEqual(
            re.findall(
                r"sectionType\s*=\s*PhGetApplicationUiString\((IDS_PH_[A-Z0-9_]+)\)",
                section_type,
            ),
            [
                "IDS_PH_UNKNOWN",
                "IDS_PH_HANDLE_SECTION_COMMIT",
                "IDS_PH_HANDLE_FILE",
                "IDS_PH_HANDLE_SECTION_IMAGE",
                "IDS_PH_HANDLE_SECTION_RESERVE",
            ],
        )
        self.assertNotIn('L"', section_type)
        self.assertIn(
            "PhSetHandleListViewItem(Context, PH_HANDLE_GENERAL_INDEX_SECTIONTYPE, 1, sectionType);",
            self.body,
        )

    def test_exit_status_unknown_fallback_uses_native_resource(self) -> None:
        self.assertEqual(
            len(re.findall(
                r"PhGetStringOrDefault\(\s*message\s*,\s*"
                r"PhGetApplicationUiString\(IDS_PH_UNKNOWN\)\s*\)",
                self.body,
            )),
            2,
        )
        self.assertNotRegex(
            self.body,
            r'PhGetStringOrDefault\(\s*message\s*,\s*L"Unknown"\s*\)',
        )

    def test_resources_owners_boundaries_and_exact_counts(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        app_header = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(
            encoding="utf-8-sig"
        )
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for symbol, numeric_id, en, zh, owner in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                other = "native_strings" if owner == "strings" else "strings"
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{numeric_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(translations[owner].get(en), zh)
                self.assertNotIn(en, translations[other])

        self.assertFalse(translations["strings"].keys() & translations["native_strings"].keys())
        definitions = re.findall(
            r"(?m)^#define\s+(IDS_PH_[A-Z0-9_]+)\s+(\d+)\s*$",
            header + "\n" + app_header,
        )
        resource_ids = {}
        for symbol, value in definitions:
            value = int(value)
            if symbol in resource_ids:
                self.assertEqual(resource_ids[symbol], value)
            resource_ids[symbol] = value
        self.assertEqual(sorted(resource_ids.values()), list(range(2000, 2944)))
        self.assertEqual(len(english), 944)
        self.assertEqual(len(chinese), 944)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_TIMELINE$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2944$")

    def test_runtime_ownership_ci_and_generator_counts_are_exact(self) -> None:
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        runtime_source = TRANSLATION_SOURCE.read_text(encoding="utf-8-sig")
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )

        for english in ("Low", "Normal", "High", "Critical", "Commit", "Image"):
            with self.subTest(runtime_owner=english):
                self.assertIn(english, translations["strings"])
                self.assertRegex(runtime_source, rf'\{{ L"{re.escape(english)}", L"')

        for english in ("N/A (snapshot)", "Pipe", "File or directory", "Console", "Directory", "Very Low", "Reserve"):
            with self.subTest(native_owner=english):
                self.assertIn(english, translations["native_strings"])
                self.assertNotRegex(runtime_source, rf'\{{ L"{re.escape(english)}", L"')

        self.assertEqual(workflow.count("sys_info.exe=944"), 2)
        self.assertNotIn("sys_info.exe=650", workflow)
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "zhcn" / "generate_native_resources.py"),
                "--check",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2584 strings", result.stdout)


if __name__ == "__main__":
    unittest.main()
