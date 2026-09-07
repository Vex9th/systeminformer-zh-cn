import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
HEADER_PATH = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "ExtendedTools.rc"
CHINESE_RC = PLUGIN_ROOT / "ExtendedTools.zh-cn.rc"

NEW_RESOURCES = (
    (61327, "IDS_ET_COLUMN_VALUE", "Value", "值"),
    (61328, "IDS_ET_CACHE_COLUMN_SIZE_KB_CYCLES", "size (KB) [cycles]", "大小（KB）[周期]"),
    (61329, "IDS_ET_COLUMN_PROPERTY", "Property", "属性"),
    (61330, "IDS_ET_COLUMN_ACCESS", "Access", "访问权限"),
    (61331, "IDS_ET_COLUMN_SID", "SID", "SID"),
    (61332, "IDS_ET_COLUMN_HEAP_SIZE", "Heap Size", "堆大小"),
    (61333, "IDS_ET_COLUMN_INPUT", "Input", "输入"),
    (61334, "IDS_ET_COLUMN_ADDRESS", "Address", "地址"),
    (61335, "IDS_ET_COLUMN_SIZE", "Size", "大小"),
    (61336, "IDS_ET_POOL_COLUMN_NONPAGED", "NonPaged", "非分页"),
    (61337, "IDS_ET_POWER_COLUMN_SEVERITY", "Severity", "严重性"),
    (61338, "IDS_ET_POWER_COLUMN_LOW_IMPACT", "Low impact", "低影响"),
    (61339, "IDS_ET_POWER_COLUMN_START_TIME", "Start time", "启动时间"),
    (61340, "IDS_ET_POWER_COLUMN_BLOCK_DURATION", "Block duration", "区块时长"),
    (61341, "IDS_ET_POWER_COLUMN_STARTS_IN", "Starts in", "距开始"),
    (61342, "IDS_ET_COLUMN_FILENAME", "Filename", "文件名"),
    (61343, "IDS_ET_REPARSE_COLUMN_FILE_INDEX", "File index", "文件索引"),
    (61344, "IDS_ET_REPARSE_COLUMN_REPARSE_TAG", "Reparse tag", "重分析标记"),
    (61345, "IDS_ET_REPARSE_COLUMN_OBJECT_IDENTIFIER", "Object identifier", "对象标识符"),
    (61346, "IDS_ET_REPARSE_COLUMN_VOLUME", "Volume", "卷"),
    (61347, "IDS_ET_REPARSE_COLUMN_SECURITY_ID", "SecurityID", "安全 ID"),
    (61348, "IDS_ET_REPARSE_COLUMN_HASH", "Hash", "哈希"),
    (61349, "IDS_ET_REPARSE_COLUMN_LENGTH", "Length", "长度"),
    (61350, "IDS_ET_REPARSE_COLUMN_OWNER", "Owner", "所有者"),
    (61351, "IDS_ET_REPARSE_COLUMN_SDDL", "SDDL", "SDDL"),
    (61352, "IDS_ET_TPM_COLUMN_DATA_SIZE", "Data size", "数据大小"),
    (61353, "IDS_ET_TPM_COLUMN_OWNER_RIGHTS", "Owner rights", "所有者权限"),
    (61354, "IDS_ET_TPM_COLUMN_AUTH_RIGHTS", "Auth rights", "授权权限"),
    (61355, "IDS_ET_TPM_COLUMN_PLATFORM_RIGHTS", "Platform rights", "平台权限"),
    (61356, "IDS_ET_UNLOAD_COLUMN_NUMBER", "No.", "序号"),
    (61357, "IDS_ET_COLUMN_BASE_ADDRESS", "Base Address", "基址"),
    (61358, "IDS_ET_COLUMN_TIME_STAMP", "Time Stamp", "时间戳"),
    (61359, "IDS_ET_COLUMN_CHECKSUM", "Checksum", "校验和"),
    (61360, "IDS_ET_COLUMN_VERSION", "Version", "版本"),
    (61361, "IDS_ET_WBCL_COLUMN_PCR", "PCR", "PCR"),
    (61362, "IDS_ET_WBCL_COLUMN_EVENT_TYPE", "Event type", "事件类型"),
    (61363, "IDS_ET_WBCL_COLUMN_DIGEST", "Digest", "摘要"),
    (61364, "IDS_ET_WBCL_COLUMN_DIGEST_VALUE", "Digest value", "摘要值"),
    (61365, "IDS_ET_COLUMN_DETAILS", "Details", "详细信息"),
    (61366, "IDS_ET_COLUMN_COUNT", "Count", "数量"),
)

ROUTES = (
    ("acpitable.c", "Name", "IDS_ET_WCT_COLUMN_NAME", 1),
    ("acpitable.c", "Value", "IDS_ET_COLUMN_VALUE", 1),
    ("cacheprp.c", "size (KB) [cycles]", "IDS_ET_CACHE_COLUMN_SIZE_KB_CYCLES", 1),
    ("gpudetails.c", "Property", "IDS_ET_COLUMN_PROPERTY", 1),
    ("gpudetails.c", "Value", "IDS_ET_COLUMN_VALUE", 1),
    ("npudetails.c", "Property", "IDS_ET_COLUMN_PROPERTY", 1),
    ("npudetails.c", "Value", "IDS_ET_COLUMN_VALUE", 1),
    ("objprp.c", "Name", "IDS_ET_WCT_COLUMN_NAME", 2),
    ("objprp.c", "Original name", "IDS_ET_FW_COLUMN_ORIGINAL_NAME", 1),
    ("objprp.c", "Process", "IDS_ET_PIPE_COLUMN_PROCESS", 1),
    ("objprp.c", "Handle", "IDS_ET_PIPE_COLUMN_HANDLE", 1),
    ("objprp.c", "Access", "IDS_ET_COLUMN_ACCESS", 1),
    ("objprp.c", "Attributes", "IDS_ET_FIRMWARE_COLUMN_ATTRIBUTES", 1),
    ("objprp.c", "SID", "IDS_ET_COLUMN_SID", 1),
    ("objprp.c", "Heap Size", "IDS_ET_COLUMN_HEAP_SIZE", 1),
    ("objprp.c", "Input", "IDS_ET_COLUMN_INPUT", 1),
    ("pooldialogbig.c", "Address", "IDS_ET_COLUMN_ADDRESS", 1),
    ("pooldialogbig.c", "Size", "IDS_ET_COLUMN_SIZE", 1),
    ("pooldialogbig.c", "NonPaged", "IDS_ET_POOL_COLUMN_NONPAGED", 1),
    ("pwrgrid.c", "Severity", "IDS_ET_POWER_COLUMN_SEVERITY", 1),
    ("pwrgrid.c", "Low impact", "IDS_ET_POWER_COLUMN_LOW_IMPACT", 1),
    ("pwrgrid.c", "Start time", "IDS_ET_POWER_COLUMN_START_TIME", 1),
    ("pwrgrid.c", "Block duration", "IDS_ET_POWER_COLUMN_BLOCK_DURATION", 1),
    ("pwrgrid.c", "Starts in", "IDS_ET_POWER_COLUMN_STARTS_IN", 1),
    ("reparse.c", "Filename", "IDS_ET_COLUMN_FILENAME", 3),
    ("reparse.c", "File index", "IDS_ET_REPARSE_COLUMN_FILE_INDEX", 2),
    ("reparse.c", "Reparse tag", "IDS_ET_REPARSE_COLUMN_REPARSE_TAG", 1),
    ("reparse.c", "Object identifier", "IDS_ET_REPARSE_COLUMN_OBJECT_IDENTIFIER", 1),
    ("reparse.c", "Volume", "IDS_ET_REPARSE_COLUMN_VOLUME", 1),
    ("reparse.c", "SecurityID", "IDS_ET_REPARSE_COLUMN_SECURITY_ID", 1),
    ("reparse.c", "Hash", "IDS_ET_REPARSE_COLUMN_HASH", 1),
    ("reparse.c", "Length", "IDS_ET_REPARSE_COLUMN_LENGTH", 1),
    ("reparse.c", "Owner", "IDS_ET_REPARSE_COLUMN_OWNER", 1),
    ("reparse.c", "SDDL", "IDS_ET_REPARSE_COLUMN_SDDL", 1),
    ("smbios.c", "Name", "IDS_ET_WCT_COLUMN_NAME", 1),
    ("smbios.c", "Value", "IDS_ET_COLUMN_VALUE", 1),
    ("tpm.c", "Index", "IDS_ET_INDEX", 1),
    ("tpm.c", "Data size", "IDS_ET_TPM_COLUMN_DATA_SIZE", 1),
    ("tpm.c", "Owner rights", "IDS_ET_TPM_COLUMN_OWNER_RIGHTS", 1),
    ("tpm.c", "Auth rights", "IDS_ET_TPM_COLUMN_AUTH_RIGHTS", 1),
    ("tpm.c", "Platform rights", "IDS_ET_TPM_COLUMN_PLATFORM_RIGHTS", 1),
    ("tpm.c", "Attributes", "IDS_ET_FIRMWARE_COLUMN_ATTRIBUTES", 1),
    ("unldll.c", "No.", "IDS_ET_UNLOAD_COLUMN_NUMBER", 1),
    ("unldll.c", "Name", "IDS_ET_WCT_COLUMN_NAME", 1),
    ("unldll.c", "Base Address", "IDS_ET_COLUMN_BASE_ADDRESS", 1),
    ("unldll.c", "Size", "IDS_ET_COLUMN_SIZE", 1),
    ("unldll.c", "Time Stamp", "IDS_ET_COLUMN_TIME_STAMP", 1),
    ("unldll.c", "Checksum", "IDS_ET_COLUMN_CHECKSUM", 1),
    ("unldll.c", "Version", "IDS_ET_COLUMN_VERSION", 1),
    ("wbcl.c", "PCR", "IDS_ET_WBCL_COLUMN_PCR", 1),
    ("wbcl.c", "Event type", "IDS_ET_WBCL_COLUMN_EVENT_TYPE", 1),
    ("wbcl.c", "Digest", "IDS_ET_WBCL_COLUMN_DIGEST", 1),
    ("wbcl.c", "Digest value", "IDS_ET_WBCL_COLUMN_DIGEST_VALUE", 1),
    ("wbcl.c", "Size", "IDS_ET_COLUMN_SIZE", 1),
    ("wbcl.c", "Details", "IDS_ET_COLUMN_DETAILS", 1),
    ("wswatch.c", "Instruction", "IDS_ET_CACHE_TYPE_INSTRUCTION", 1),
    ("wswatch.c", "Filename", "IDS_ET_COLUMN_FILENAME", 1),
    ("wswatch.c", "Count", "IDS_ET_COLUMN_COUNT", 1),
)

FILES_REQUIRING_DECLARATION = (
    "acpitable.c",
    "gpudetails.c",
    "npudetails.c",
    "smbios.c",
    "unldll.c",
    "wbcl.c",
    "wswatch.c",
)


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def parse_header() -> tuple[dict[str, int], str]:
    source = HEADER_PATH.read_text(encoding="utf-8")
    return (
        {
            name: int(value)
            for name, value in re.findall(
                r"^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)\b", source, re.MULTILINE
            )
        },
        source,
    )


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8-sig")
    return {
        name: value.replace('""', '"')
        for name, value in re.findall(
            r'^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:""|[^"])*)"', source, re.MULTILINE
        )
    }


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("audit_extended_tools_columns", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedToolsListViewColumnDynamicUiResourceTests(unittest.TestCase):
    def test_resources_are_contiguous_bilingual_and_cached(self) -> None:
        header, header_source = parse_header()
        english = parse_stringtable(ENGLISH_RC)
        chinese = parse_stringtable(CHINESE_RC)

        self.assertEqual(len(header), 471)
        self.assertEqual(len(english), 471)
        self.assertEqual(len(chinese), 471)
        self.assertEqual(sorted(header.values()), list(range(61000, 61471)))
        self.assertRegex(
            header_source,
            r"(?m)^#define\s+IDS_ET_CACHED_LAST\s+IDS_ET_SEARCH_NAMED_PIPES$",
        )
        self.assertRegex(header_source, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61471$")

        for resource_id, symbol, en_text, zh_text in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(header[symbol], resource_id)
                self.assertEqual(english[symbol], en_text)
                self.assertEqual(chinese[symbol], zh_text)

    def test_all_62_columns_use_the_exact_cached_resource_route(self) -> None:
        self.assertEqual(sum(count for _, _, _, count in ROUTES), 62)
        for filename, english, symbol, count in ROUTES:
            with self.subTest(filename=filename, english=english):
                source = compact((PLUGIN_ROOT / filename).read_text(encoding="utf-8"))
                route = compact(f'EtGetUiString({symbol},L"{english}")')
                self.assertEqual(source.count(route), count)

        for filename in FILES_REQUIRING_DECLARATION:
            with self.subTest(filename=filename):
                file_source = (PLUGIN_ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("PCWSTR EtGetUiString(", file_source)

    def test_directed_extended_tools_scan_has_no_listview_column_entries(self) -> None:
        audit = load_audit_module()
        remaining = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            entries = []
            audit.scan_c_file(path, entries)
            remaining.extend(
                (path.name, entry["line"], entry["english"])
                for entry in entries
                if entry["category"] == "c_listview_col"
            )

        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
