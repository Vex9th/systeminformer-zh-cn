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
    (61367, "IDS_ET_DISK_COLUMN_FILE", "File", "文件"),
    (61368, "IDS_ET_DISK_COLUMN_READ_RATE_AVERAGE", "Read rate average", "平均读取速率"),
    (61369, "IDS_ET_DISK_COLUMN_WRITE_RATE_AVERAGE", "Write rate average", "平均写入速率"),
    (61370, "IDS_ET_DISK_COLUMN_TOTAL_RATE_AVERAGE", "Total rate average", "平均总速率"),
    (61371, "IDS_ET_DISK_COLUMN_READ_RATE", "Read rate", "读取速率"),
    (61372, "IDS_ET_DISK_COLUMN_WRITE_RATE", "Write rate", "写入速率"),
    (61373, "IDS_ET_DISK_COLUMN_TOTAL_RATE", "Total rate", "总速率"),
    (61374, "IDS_ET_DISK_COLUMN_IO_PRIORITY", "I/O priority", "I/O 优先级"),
    (61375, "IDS_ET_DISK_COLUMN_RESPONSE_TIME_MS", "Response time (ms)", "响应时间（ms）"),
    (61376, "IDS_ET_MODULE_NOT_REFERENCED_BY_SERVICE", "This module was not referenced by a service.", "该模块未被任何服务引用。"),
    (61377, "IDS_ET_POOL_SEARCH", "Search Pool Tags (Ctrl+K)", "搜索池标记 (Ctrl+K)"),
    (61378, "IDS_ET_ERROR_OPEN_PROCESS", "Unable to open the process.", "无法打开该进程。"),
)

ROUTES = (
    ("disktab.c", "Name", "IDS_ET_WCT_COLUMN_NAME", 1),
    ("disktab.c", "PID", "IDS_ET_FW_COLUMN_PID", 1),
    ("disktab.c", "File", "IDS_ET_DISK_COLUMN_FILE", 1),
    ("disktab.c", "Read rate average", "IDS_ET_DISK_COLUMN_READ_RATE_AVERAGE", 1),
    ("disktab.c", "Write rate average", "IDS_ET_DISK_COLUMN_WRITE_RATE_AVERAGE", 1),
    ("disktab.c", "Total rate average", "IDS_ET_DISK_COLUMN_TOTAL_RATE_AVERAGE", 1),
    ("disktab.c", "Read rate", "IDS_ET_DISK_COLUMN_READ_RATE", 1),
    ("disktab.c", "Write rate", "IDS_ET_DISK_COLUMN_WRITE_RATE", 1),
    ("disktab.c", "Total rate", "IDS_ET_DISK_COLUMN_TOTAL_RATE", 1),
    ("disktab.c", "Read bytes", "IDS_ET_READ_BYTES", 1),
    ("disktab.c", "Write bytes", "IDS_ET_WRITE_BYTES", 1),
    ("disktab.c", "Total bytes", "IDS_ET_TOTAL_BYTES", 1),
    ("disktab.c", "I/O priority", "IDS_ET_DISK_COLUMN_IO_PRIORITY", 1),
    ("disktab.c", "Response time (ms)", "IDS_ET_DISK_COLUMN_RESPONSE_TIME_MS", 1),
    ("disktab.c", "Original name", "IDS_ET_FW_COLUMN_ORIGINAL_NAME", 1),
    ("disktab.c", "The process does not exist.", "IDS_ET_WCT_PROCESS_NOT_FOUND", 1),
    ("gpudetails.c", "Unable to create the window.", "IDS_ET_OBJMGR_ERROR_CREATE_WINDOW", 1),
    ("gpunodes.c", "Unable to create the window.", "IDS_ET_OBJMGR_ERROR_CREATE_WINDOW", 1),
    ("modsrv.c", "This module was not referenced by a service.", "IDS_ET_MODULE_NOT_REFERENCED_BY_SERVICE", 1),
    ("npudetails.c", "Unable to create the window.", "IDS_ET_OBJMGR_ERROR_CREATE_WINDOW", 1),
    ("npunodes.c", "Unable to create the window.", "IDS_ET_OBJMGR_ERROR_CREATE_WINDOW", 1),
    ("pooldialog.c", "Search Pool Tags (Ctrl+K)", "IDS_ET_POOL_SEARCH", 1),
    ("pooldialog.c", "Unable to create the window.", "IDS_ET_OBJMGR_ERROR_CREATE_WINDOW", 1),
    ("unldll.c", "Unable to open the process.", "IDS_ET_ERROR_OPEN_PROCESS", 1),
    ("wswatch.c", "Unable to open the process.", "IDS_ET_ERROR_OPEN_PROCESS", 1),
)

FILES_REQUIRING_DECLARATION = (
    "disktab.c",
    "gpunodes.c",
    "npunodes.c",
    "pooldialog.c",
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
    spec = importlib.util.spec_from_file_location("audit_extended_tools_tree_search_message", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedToolsTreeSearchMessageDynamicUiResourceTests(unittest.TestCase):
    def test_resources_are_contiguous_bilingual_and_cached(self) -> None:
        header, header_source = parse_header()
        english = parse_stringtable(ENGLISH_RC)
        chinese = parse_stringtable(CHINESE_RC)

        self.assertEqual(len(header), 397)
        self.assertEqual(len(english), 397)
        self.assertEqual(len(chinese), 397)
        self.assertEqual(sorted(header.values()), list(range(61000, 61397)))
        self.assertRegex(
            header_source,
            r"(?m)^#define\s+IDS_ET_CACHED_LAST\s+IDS_ET_CONFIRM_THREAD_IO$",
        )
        self.assertRegex(header_source, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61397$")

        for resource_id, symbol, en_text, zh_text in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(header[symbol], resource_id)
                self.assertEqual(english[symbol], en_text)
                self.assertEqual(chinese[symbol], zh_text)

    def test_all_25_routes_use_the_exact_cached_resource(self) -> None:
        self.assertEqual(sum(count for _, _, _, count in ROUTES), 25)
        for filename, english, symbol, count in ROUTES:
            with self.subTest(filename=filename, english=english):
                source = compact((PLUGIN_ROOT / filename).read_text(encoding="utf-8"))
                route = compact(f'EtGetUiString({symbol},L"{english}")')
                self.assertEqual(source.count(route), count)

        for filename in FILES_REQUIRING_DECLARATION:
            with self.subTest(filename=filename):
                source = (PLUGIN_ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("PCWSTR EtGetUiString(", source)

    def test_directed_scan_has_no_tree_search_or_message_entries(self) -> None:
        audit = load_audit_module()
        categories = {"c_treenew_col", "c_search", "c_msgbox"}
        remaining = []

        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            entries = []
            audit.scan_c_file(path, entries)
            remaining.extend(
                (path.name, entry["category"], entry["line"], entry["english"])
                for entry in entries
                if entry["category"] in categories
            )

        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
