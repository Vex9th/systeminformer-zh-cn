#!/usr/bin/env python3

import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


RESOURCE_DATA = r"""
IDS_ET_FIRMWARE_ATTRIBUTE_NON_VOLATILE|61169|Non Volatile|非易失性|native_strings
IDS_ET_FIRMWARE_ATTRIBUTE_BOOT_SERVICE|61170|Boot Service|引导服务访问|native_strings
IDS_ET_FIRMWARE_ATTRIBUTE_RUNTIME_ACCESS|61171|Runtime Access|运行时访问|native_strings
IDS_ET_FIRMWARE_ATTRIBUTE_HARDWARE_ERROR_RECORD|61172|Hardware Error Record|硬件错误记录|native_strings
IDS_ET_FIRMWARE_ATTRIBUTE_AUTHENTICATED_WRITE|61173|Authenticated Write Access|经身份验证的写入访问|native_strings
IDS_ET_FIRMWARE_ATTRIBUTE_TIME_BASED_AUTHENTICATED_WRITE|61174|Authenticated Write Access (Time Based)|基于时间的身份验证写入访问|native_strings
IDS_ET_FIRMWARE_ATTRIBUTE_APPEND_WRITE|61175|Append Write|追加写入|native_strings
IDS_ET_FIRMWARE_COLUMN_NAME|61176|Name|名称|strings
IDS_ET_FIRMWARE_COLUMN_ATTRIBUTES|61177|Attributes|属性|strings
IDS_ET_FIRMWARE_COLUMN_GUID_NAME|61178|Guid Name|GUID 名称|strings
IDS_ET_FIRMWARE_COLUMN_GUID|61179|Guid|GUID|strings
IDS_ET_FIRMWARE_COLUMN_DATA_LENGTH|61180|Data Length|数据长度|strings
IDS_ET_MENU_EDIT|61181|&Edit|编辑(&E)|strings
IDS_ET_MENU_DELETE|61182|&Delete|删除(&D)|strings
IDS_ET_MENU_COPY|61183|&Copy|复制(&C)|strings
IDS_ET_FIRMWARE_LEGACY_BIOS|61184|Windows was installed using legacy BIOS.|Windows 是使用传统 BIOS 安装的。|native_strings
IDS_ET_FILTER_BINARY_FILES|61185|Binary files (*.bin)|二进制文件 (*.bin)|native_strings
IDS_ET_FILTER_ALL_FILES|61186|All files (*.*)|所有文件 (*.*)|native_strings
IDS_ET_UNABLE_CREATE_FILE|61187|Unable to create the file|无法创建文件|strings
""".strip()


RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in (
        line.split("|") for line in RESOURCE_DATA.splitlines()
    )
]


ATTRIBUTE_ROUTES = (
    ("EFI_VARIABLE_NON_VOLATILE", "IDS_ET_FIRMWARE_ATTRIBUTE_NON_VOLATILE", "Non Volatile"),
    ("EFI_VARIABLE_BOOTSERVICE_ACCESS", "IDS_ET_FIRMWARE_ATTRIBUTE_BOOT_SERVICE", "Boot Service"),
    ("EFI_VARIABLE_RUNTIME_ACCESS", "IDS_ET_FIRMWARE_ATTRIBUTE_RUNTIME_ACCESS", "Runtime Access"),
    ("EFI_VARIABLE_HARDWARE_ERROR_RECORD", "IDS_ET_FIRMWARE_ATTRIBUTE_HARDWARE_ERROR_RECORD", "Hardware Error Record"),
    ("EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS", "IDS_ET_FIRMWARE_ATTRIBUTE_AUTHENTICATED_WRITE", "Authenticated Write Access"),
    ("EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS", "IDS_ET_FIRMWARE_ATTRIBUTE_TIME_BASED_AUTHENTICATED_WRITE", "Authenticated Write Access (Time Based)"),
    ("EFI_VARIABLE_APPEND_WRITE", "IDS_ET_FIRMWARE_ATTRIBUTE_APPEND_WRITE", "Append Write"),
)


COLUMN_ROUTES = (
    (0, "IDS_ET_FIRMWARE_COLUMN_NAME", "Name"),
    (1, "IDS_ET_FIRMWARE_COLUMN_ATTRIBUTES", "Attributes"),
    (2, "IDS_ET_FIRMWARE_COLUMN_GUID_NAME", "Guid Name"),
    (3, "IDS_ET_FIRMWARE_COLUMN_GUID", "Guid"),
    (4, "IDS_ET_FIRMWARE_COLUMN_DATA_LENGTH", "Data Length"),
)


MENU_ROUTES = (
    ("1", "IDS_ET_MENU_EDIT", "&Edit"),
    ("2", "IDS_ET_MENU_DELETE", "&Delete"),
    ("PHAPP_IDC_COPY", "IDS_ET_MENU_COPY", "&Copy"),
)


def source_text(name):
    return (PLUGIN_ROOT / name).read_text(encoding="utf-8-sig")


def parse_defines():
    text = source_text("resource.h")
    return {
        symbol: int(value)
        for symbol, value in re.findall(r"(?m)^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)\s*$", text)
    }


def parse_stringtable(name):
    text = source_text(name)
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


class ExtendedToolsFirmwareResourceTests(unittest.TestCase):
    def test_resource_ids_and_boundaries_are_exact(self):
        defines = parse_defines()

        for symbol, resource_id, _, _, _ in RESOURCES:
            self.assertEqual(defines.get(symbol), resource_id)

        self.assertEqual([row[1] for row in RESOURCES], list(range(61169, 61188)))
        header = source_text("resource.h")
        self.assertRegex(
            header,
            r"(?m)^#define IDS_ET_CACHED_LAST\s+IDS_ET_WORKER_THREAD_CONTEXT_FORMAT$",
        )
        self.assertRegex(
            header,
            r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+61230$",
        )

    def test_english_chinese_and_json_owners_are_exact(self):
        english_rc = parse_stringtable("ExtendedTools.rc")
        chinese_rc = parse_stringtable("ExtendedTools.zh-cn.rc")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8-sig"
            )
        )

        self.assertFalse(set(translations["strings"]) & set(translations["native_strings"]))
        for symbol, _, english, chinese, owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(english_rc.get(symbol), english)
                self.assertEqual(chinese_rc.get(symbol), chinese)
                self.assertEqual(translations[owner].get(english), chinese)
                other = "strings" if owner == "native_strings" else "native_strings"
                self.assertNotIn(english, translations[other])

    def test_firmware_attributes_columns_and_menus_use_native_resources(self):
        source = source_text("firmware.c")

        self.assertRegex(
            source,
            r"PCWSTR\s+EtGetUiString\(\s*_In_\s+ULONG\s+ResourceId\s*,\s*"
            r"_In_\s+PCWSTR\s+Fallback\s*\)\s*;",
        )

        for flag, symbol, fallback in ATTRIBUTE_ROUTES:
            with self.subTest(attribute=flag):
                self.assertRegex(
                    source,
                    rf"if\s*\(Attribute\s*&\s*{flag}\)\s*"
                    rf"EtAppendFirmwareAttribute\(\s*&sb,\s*{symbol},\s*L\"{re.escape(fallback)}\"\s*\)",
                )
        self.assertRegex(
            source,
            r"EtAppendFirmwareAttribute\([\s\S]+?"
            r"PhAppendStringBuilder2\(Builder,\s*EtGetUiString\(ResourceId,\s*Fallback\)\);[\s\S]+?"
            r'PhAppendStringBuilder2\(Builder,\s*L\", \"\);',
        )
        for column, symbol, fallback in COLUMN_ROUTES:
            with self.subTest(column=column):
                self.assertRegex(
                    source,
                    rf"PhAddListViewColumn\([^;]+?\b{column}\s*,\s*{column}\s*,\s*{column}\s*,[^;]+?"
                    rf"EtGetUiString\(\s*{symbol},\s*L\"{re.escape(fallback)}\"\s*\)\s*\)",
                )
        for item_id, symbol, fallback in MENU_ROUTES:
            with self.subTest(menu=item_id):
                self.assertRegex(
                    source,
                    rf"PhCreateEMenuItem\(\s*0\s*,\s*{re.escape(item_id)}\s*,\s*"
                    rf"EtGetUiString\(\s*{symbol},\s*L\"{re.escape(fallback)}\"\s*\)",
                )

        self.assertRegex(
            source,
            r"PhShowError2\([^;]+?L\"%s\"\s*,\s*EtGetUiString\(\s*"
            r"IDS_ET_FIRMWARE_LEGACY_BIOS\s*,\s*"
            r'L"Windows was installed using legacy BIOS\."\s*\)\s*\)',
        )

    def test_both_editors_hold_filter_resources_and_keep_runtime_file_names(self):
        for filename, expected_name_format in (
            ("firmware_editor.c", 'L"%s.bin"'),
            ("tpm_editor.c", 'L"TPM-%08lx.bin"'),
        ):
            with self.subTest(editor=filename):
                source = source_text(filename)
                self.assertRegex(
                    source,
                    r"PCWSTR\s+EtGetUiString\(\s*_In_\s+ULONG\s+ResourceId\s*,\s*"
                    r"_In_\s+PCWSTR\s+Fallback\s*\)\s*;",
                )
                self.assertRegex(
                    source,
                    r"PPH_STRING\s+binaryFilesFilter\s*;[\s\S]+?"
                    r"binaryFilesFilter\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
                    r"PluginInstance->DllBase\s*,\s*IDS_ET_FILTER_BINARY_FILES\s*,\s*NULL\s*\)\)",
                )
                self.assertRegex(
                    source,
                    r"PPH_STRING\s+allFilesFilter\s*;[\s\S]+?"
                    r"allFilesFilter\s*=\s*PH_AUTO\(PhLoadUiString\(\s*"
                    r"PluginInstance->DllBase\s*,\s*IDS_ET_FILTER_ALL_FILES\s*,\s*NULL\s*\)\)",
                )
                self.assertRegex(
                    source,
                    r"filters\[0\]\.Name\s*=\s*binaryFilesFilter\s*\?\s*"
                    r'binaryFilesFilter->Buffer\s*:\s*L"Binary files \(\*\.bin\)"\s*;',
                )
                self.assertRegex(
                    source,
                    r"filters\[1\]\.Name\s*=\s*allFilesFilter\s*\?\s*"
                    r'allFilesFilter->Buffer\s*:\s*L"All files \(\*\.\*\)"\s*;',
                )
                self.assertIn('filters[0].Filter = L"*.bin";', source)
                self.assertIn('filters[1].Filter = L"*.*";', source)
                self.assertIn(expected_name_format, source)
                self.assertRegex(
                    source,
                    r"PhShowStatus\(\s*WindowHandle\s*,\s*EtGetUiString\(\s*"
                    r"IDS_ET_UNABLE_CREATE_FILE\s*,\s*L\"Unable to create the file\"\s*\)",
                )

        firmware = source_text("firmware_editor.c")
        self.assertIn("PhGetString(context->Name)", firmware)
        self.assertNotIn("IDS_ET_FIRMWARE_COLUMN_NAME", firmware)

    def test_extended_tools_pe_count_is_updated_in_both_ci_checks(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8-sig"
        )
        self.assertEqual(workflow.count("plugins\\ExtendedTools.dll=230"), 2)
        self.assertNotIn("plugins\\ExtendedTools.dll=188", workflow)


if __name__ == "__main__":
    unittest.main()
