#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"
PRINTF_RE = re.compile(
    r"%(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.\d+|\.\*)?"
    r"(?:hh|h|ll|l|I64|I32|w|z|t|j)?[A-Za-z%]"
)

NEW_RESOURCES = (
    ("IDS_PH_HANDLE_OBJECT_ADDRESS", 2625, "Object address", "对象地址", "strings"),
    ("IDS_PH_HANDLE_FULL_PATH", 2626, "FullPath", "完整路径", "native_strings"),
    ("IDS_PH_HANDLE_GRANTED_ACCESS", 2627, "Granted access", "已授予的权限", "strings"),
    ("IDS_PH_HANDLE_GRANTED_ACCESS_GENERIC", 2628, "Granted access (generic)", "已授予的权限（通用）", "native_strings"),
    ("IDS_PH_HANDLE_GRANTED_ACCESS_MASK", 2629, "Granted access (mask)", "已授予的权限（掩码）", "native_strings"),
    ("IDS_PH_HANDLE_SDDL", 2630, "SDDL", "SDDL", "strings"),
    ("IDS_PH_HANDLE_PAGED", 2631, "Paged", "分页池", "native_strings"),
    ("IDS_PH_HANDLE_SEQUENCE_NUMBER", 2632, "Sequence Number", "序列号", "native_strings"),
    ("IDS_PH_HANDLE_PORT_CONTEXT", 2633, "Port Context", "端口上下文", "native_strings"),
    ("IDS_PH_HANDLE_CONNECTION", 2634, "Connection", "连接", "strings"),
    ("IDS_PH_HANDLE_SERVER", 2635, "Server", "服务器", "strings"),
    ("IDS_PH_HANDLE_CLIENT", 2636, "Client", "客户端", "strings"),
    ("IDS_PH_HANDLE_GUID", 2637, "GUID", "GUID", "native_strings"),
    ("IDS_PH_HANDLE_MODE", 2638, "Mode", "模式", "native_strings"),
    ("IDS_PH_HANDLE_POSITION", 2639, "Position", "位置", "native_strings"),
    ("IDS_PH_HANDLE_SIZE", 2640, "Size", "大小", "strings"),
    ("IDS_PH_HANDLE_DRIVER", 2641, "Driver", "驱动程序", "strings"),
    ("IDS_PH_HANDLE_DRIVER_IMAGE", 2642, "Driver Image", "驱动程序映像", "native_strings"),
    ("IDS_PH_HANDLE_FILE", 2643, "File", "文件", "strings"),
    ("IDS_PH_HANDLE_COUNT", 2644, "Count", "数量", "strings"),
    ("IDS_PH_HANDLE_ABANDONED", 2645, "Abandoned", "已放弃", "native_strings"),
    ("IDS_PH_HANDLE_CREATED", 2646, "Created", "创建时间", "strings"),
    ("IDS_PH_HANDLE_EXITED", 2647, "Exited", "退出时间", "native_strings"),
    ("IDS_PH_HANDLE_EXIT_STATUS", 2648, "Exit status", "退出状态", "native_strings"),
    ("IDS_PH_HANDLE_LINK_TARGET", 2649, "Link target", "链接目标", "native_strings"),
)

ROUTES = (
    ("PH_HANDLE_GENERAL_CATEGORY_BASICINFO", "PH_HANDLE_GENERAL_INDEX_NAME", "IDS_PH_TOKEN_NAME"),
    ("PH_HANDLE_GENERAL_CATEGORY_BASICINFO", "PH_HANDLE_GENERAL_INDEX_TYPE", "IDS_PH_TOKEN_TYPE"),
    ("PH_HANDLE_GENERAL_CATEGORY_BASICINFO", "PH_HANDLE_GENERAL_INDEX_OBJECT", "IDS_PH_HANDLE_OBJECT_ADDRESS"),
    ("PH_HANDLE_GENERAL_CATEGORY_BASICINFO", "PH_HANDLE_GENERAL_INDEX_FULLNAME", "IDS_PH_HANDLE_FULL_PATH"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECURITY", "PH_HANDLE_GENERAL_INDEX_ACCESSS", "IDS_PH_HANDLE_GRANTED_ACCESS"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECURITY", "PH_HANDLE_GENERAL_INDEX_ACCESSGENERIC", "IDS_PH_HANDLE_GRANTED_ACCESS_GENERIC"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECURITY", "PH_HANDLE_GENERAL_INDEX_ACCESSMASK", "IDS_PH_HANDLE_GRANTED_ACCESS_MASK"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECURITY", "PH_HANDLE_GENERAL_INDEX_SDDL", "IDS_PH_HANDLE_SDDL"),
    ("PH_HANDLE_GENERAL_CATEGORY_REFERENCES", "PH_HANDLE_GENERAL_INDEX_REFERENCES", "IDS_PH_GROUP_REFERENCES"),
    ("PH_HANDLE_GENERAL_CATEGORY_REFERENCES", "PH_HANDLE_GENERAL_INDEX_HANDLES", "IDS_PH_STAT_HANDLES"),
    ("PH_HANDLE_GENERAL_CATEGORY_QUOTA", "PH_HANDLE_GENERAL_INDEX_PAGED", "IDS_PH_HANDLE_PAGED"),
    ("PH_HANDLE_GENERAL_CATEGORY_QUOTA", "PH_HANDLE_GENERAL_INDEX_NONPAGED", "IDS_PH_STAT_VIRTUALSIZE"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_FLAGS", "IDS_PH_GROUP_FLAGS"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_SEQUENCENUMBER", "IDS_PH_HANDLE_SEQUENCE_NUMBER"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_PORTCONTEXT", "IDS_PH_HANDLE_PORT_CONTEXT"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_ALPCSTATE", "IDS_PH_SESSION_STATE"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_ALPCCONNECTION", "IDS_PH_HANDLE_CONNECTION"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_ALPCSERVER", "IDS_PH_HANDLE_SERVER"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_ALPCCLIENT", "IDS_PH_HANDLE_CLIENT"),
    ("PH_HANDLE_GENERAL_CATEGORY_ALPC", "PH_HANDLE_GENERAL_INDEX_ALPCOWNER", "IDS_PH_HANDLE_SECURITY_OWNER"),
    ("PH_HANDLE_GENERAL_CATEGORY_ETW", "PH_HANDLE_GENERAL_INDEX_ETWORIGINALNAME", "IDS_PH_HANDLE_GUID"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILETYPE", "IDS_PH_TOKEN_TYPE"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILEMODE", "IDS_PH_HANDLE_MODE"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILEPOSITION", "IDS_PH_HANDLE_POSITION"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILESIZE", "IDS_PH_HANDLE_SIZE"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILEPRIORITY", "IDS_PH_STAT_PRIORITY"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILEDRIVER", "IDS_PH_HANDLE_DRIVER"),
    ("PH_HANDLE_GENERAL_CATEGORY_FILE", "PH_HANDLE_GENERAL_INDEX_FILEDRIVERIMAGE", "IDS_PH_HANDLE_DRIVER_IMAGE"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECTION", "PH_HANDLE_GENERAL_INDEX_SECTIONTYPE", "IDS_PH_TOKEN_TYPE"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECTION", "PH_HANDLE_GENERAL_INDEX_SECTIONFILE", "IDS_PH_HANDLE_FILE"),
    ("PH_HANDLE_GENERAL_CATEGORY_SECTION", "PH_HANDLE_GENERAL_INDEX_SECTIONSIZE", "IDS_PH_HANDLE_SIZE"),
    ("PH_HANDLE_GENERAL_CATEGORY_MUTANT", "PH_HANDLE_GENERAL_INDEX_MUTANTCOUNT", "IDS_PH_HANDLE_COUNT"),
    ("PH_HANDLE_GENERAL_CATEGORY_MUTANT", "PH_HANDLE_GENERAL_INDEX_MUTANTABANDONED", "IDS_PH_HANDLE_ABANDONED"),
    ("PH_HANDLE_GENERAL_CATEGORY_MUTANT", "PH_HANDLE_GENERAL_INDEX_MUTANTOWNER", "IDS_PH_HANDLE_SECURITY_OWNER"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADNAME", "IDS_PH_TOKEN_NAME"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADCREATETIME", "IDS_PH_HANDLE_CREATED"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADEXITTIME", "IDS_PH_HANDLE_EXITED"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADEXITCODE", "IDS_PH_HANDLE_EXIT_STATUS"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADNAME", "IDS_PH_TOKEN_NAME"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADCREATETIME", "IDS_PH_HANDLE_CREATED"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADEXITTIME", "IDS_PH_HANDLE_EXITED"),
    ("PH_HANDLE_GENERAL_CATEGORY_PROCESSTHREAD", "PH_HANDLE_GENERAL_INDEX_PROCESSTHREADEXITCODE", "IDS_PH_HANDLE_EXIT_STATUS"),
    ("PH_HANDLE_GENERAL_CATEGORY_SYMBOLICLINK", "PH_HANDLE_GENERAL_INDEX_SYMBOLICLINKLINK", "IDS_PH_HANDLE_LINK_TARGET"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("handle_native_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class HandleListViewNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = (APP_ROOT / "hndlprp.c").read_text(encoding="utf-8-sig")

    def test_general_listview_uses_exact_43_resource_routes(self) -> None:
        body = function_body(
            self.audit.mask_c_comments(self.source),
            "PhpUpdateHandleGeneralListViewGroups",
        )
        actual = re.findall(
            r"PhAddHandleListViewItem\(\s*Context->ListViewClass\s*,\s*"
            r"(PH_HANDLE_GENERAL_CATEGORY_[A-Z0-9_]+)\s*,\s*"
            r"(PH_HANDLE_GENERAL_INDEX_[A-Z0-9_]+)\s*,\s*"
            r"PhGetApplicationUiString\((IDS_PH_[A-Z0-9_]+)\)\s*\)\s*;",
            body,
        )

        self.assertEqual(tuple(actual), ROUTES)
        self.assertEqual(len(actual), 43)
        self.assertNotRegex(
            body,
            r"PhAddHandleListViewItem\([^;]*,\s*L\"",
        )

    def test_wrapper_keeps_the_caller_owned_text_raw(self) -> None:
        body = function_body(self.source, "PhAddHandleListViewItem")
        listview_source = (
            REPO_ROOT / "phlib" / "guisuplistview.cpp"
        ).read_text(encoding="utf-8-sig")

        self.assertRegex(
            body,
            r"PhListView_AddGroupItem\(ListViewClass, GroupId, Index, Text, UlongToPtr\(Index\)\)",
        )
        self.assertNotIn("PhTranslateString", body)
        self.assertNotIn("PhGetApplicationUiString", body)
        for function in (
            "PhAddListViewGroupItem",
            "PhAddIListViewGroupItem",
        ):
            with self.subTest(function=function):
                downstream = function_body(listview_source, function)
                self.assertIn(
                    "item.pszText = const_cast<PWSTR>(Text);",
                    downstream,
                )
                self.assertNotIn("PhTranslateString", downstream)
                self.assertRegex(
                    downstream,
                    r"(?:ListView_InsertItem|ListView->InsertItem)\s*\(",
                )

    def test_resource_ids_text_ownership_counts_and_boundaries_are_exact(self) -> None:
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
                self.assertEqual(PRINTF_RE.findall(en), PRINTF_RE.findall(zh))

        self.assertFalse(translations["strings"].keys() & translations["native_strings"].keys())
        numeric_ids = sorted(
            int(value)
            for value in re.findall(
                r"(?m)^#define\s+IDS_PH_[A-Z0-9_]+\s+(\d+)\s*$",
                header + "\n" + app_header,
            )
        )
        self.assertEqual(numeric_ids, list(range(2000, 2710)))
        self.assertEqual(len(english), 710)
        self.assertEqual(len(chinese), 710)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_OPTIONS_PLUGINS$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2710$")

    def test_ci_and_generator_lock_the_new_exact_counts(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("sys_info.exe=710"), 2)
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
        self.assertIn("1900 strings", result.stdout)


if __name__ == "__main__":
    unittest.main()
