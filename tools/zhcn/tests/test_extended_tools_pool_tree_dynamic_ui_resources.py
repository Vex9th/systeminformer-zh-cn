import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
SOURCE_PATH = PLUGIN_ROOT / "pooltree.c"
HEADER_PATH = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "ExtendedTools.rc"
CHINESE_RC = PLUGIN_ROOT / "ExtendedTools.zh-cn.rc"

NEW_RESOURCES = (
    (61301, "IDS_ET_POOL_COLUMN_TAG_NAME", "Tag Name", "标签名"),
    (61302, "IDS_ET_POOL_COLUMN_DRIVER", "Driver", "驱动程序"),
    (61303, "IDS_ET_POOL_COLUMN_PAGED_ALLOCATIONS_TOTAL", "Paged allocations (total)", "分页分配数（总计）"),
    (61304, "IDS_ET_POOL_COLUMN_PAGED_FREES_TOTAL", "Paged frees (total)", "分页释放数（总计）"),
    (61305, "IDS_ET_POOL_COLUMN_PAGED_CURRENT_TOTAL", "Paged current (total)", "分页当前值（总计）"),
    (61306, "IDS_ET_POOL_COLUMN_PAGED_BYTES_TOTAL", "Paged bytes (total)", "分页字节数（总计）"),
    (61307, "IDS_ET_POOL_COLUMN_NONPAGED_ALLOCATIONS_TOTAL", "Non-paged allocations (total)", "非分页分配数（总计）"),
    (61308, "IDS_ET_POOL_COLUMN_NONPAGED_FREES_TOTAL", "Non-paged frees (total)", "非分页释放数（总计）"),
    (61309, "IDS_ET_POOL_COLUMN_NONPAGED_CURRENT_TOTAL", "Non-paged current (total)", "非分页当前值（总计）"),
    (61310, "IDS_ET_POOL_COLUMN_NONPAGED_BYTES_TOTAL", "Non-paged bytes (total)", "非分页字节数（总计）"),
    (61311, "IDS_ET_POOL_COLUMN_ALLOCATIONS_TOTAL", "Allocations (total)", "分配数（总计）"),
    (61312, "IDS_ET_POOL_COLUMN_FREES_TOTAL", "Frees (total)", "释放数（总计）"),
    (61313, "IDS_ET_POOL_COLUMN_CURRENT_TOTAL", "Current (total)", "当前值（总计）"),
    (61314, "IDS_ET_POOL_COLUMN_BYTES_TOTAL", "Bytes (total)", "字节数（总计）"),
    (61315, "IDS_ET_POOL_COLUMN_PAGED_ALLOCATIONS_DELTA", "Paged allocations (delta)", "分页分配数（增量）"),
    (61316, "IDS_ET_POOL_COLUMN_PAGED_FREES_DELTA", "Paged frees (delta)", "分页释放数（增量）"),
    (61317, "IDS_ET_POOL_COLUMN_PAGED_CURRENT_DELTA", "Paged current (delta)", "分页当前值（增量）"),
    (61318, "IDS_ET_POOL_COLUMN_PAGED_BYTES_DELTA", "Paged bytes (delta)", "分页字节数（增量）"),
    (61319, "IDS_ET_POOL_COLUMN_NONPAGED_ALLOCATIONS_DELTA", "Non-paged allocations (delta)", "非分页分配数（增量）"),
    (61320, "IDS_ET_POOL_COLUMN_NONPAGED_FREES_DELTA", "Non-paged frees (delta)", "非分页释放数（增量）"),
    (61321, "IDS_ET_POOL_COLUMN_NONPAGED_CURRENT_DELTA", "Non-paged current (delta)", "非分页当前值（增量）"),
    (61322, "IDS_ET_POOL_COLUMN_NONPAGED_BYTES_DELTA", "Non-paged bytes (delta)", "非分页字节数（增量）"),
    (61323, "IDS_ET_POOL_COLUMN_ALLOCATIONS_DELTA", "Allocations (delta)", "分配数（增量）"),
    (61324, "IDS_ET_POOL_COLUMN_FREES_DELTA", "Frees (delta)", "释放数（增量）"),
    (61325, "IDS_ET_POOL_COLUMN_CURRENT_DELTA", "Current (delta)", "当前值（增量）"),
    (61326, "IDS_ET_POOL_COLUMN_BYTES_DELTA", "Bytes (delta)", "字节数（增量）"),
)

COLUMN_ROUTES = (
    ("TREE_COLUMN_ITEM_TAG", "TRUE", "IDS_ET_POOL_COLUMN_TAG_NAME", "Tag Name", 50, "PH_ALIGN_LEFT", "-2", "0"),
    ("TREE_COLUMN_ITEM_DRIVER", "TRUE", "IDS_ET_POOL_COLUMN_DRIVER", "Driver", 82, "PH_ALIGN_LEFT", "0", "0"),
    ("TREE_COLUMN_ITEM_DESCRIPTION", "TRUE", "IDS_ET_FW_COLUMN_DESCRIPTION", "Description", 140, "PH_ALIGN_LEFT", "1", "0"),
    ("TREE_COLUMN_ITEM_PAGEDALLOC", "TRUE", "IDS_ET_POOL_COLUMN_PAGED_ALLOCATIONS_TOTAL", "Paged allocations (total)", 80, "PH_ALIGN_RIGHT", "2", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_PAGEDFREE", "TRUE", "IDS_ET_POOL_COLUMN_PAGED_FREES_TOTAL", "Paged frees (total)", 80, "PH_ALIGN_RIGHT", "3", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_PAGEDCURRENT", "TRUE", "IDS_ET_POOL_COLUMN_PAGED_CURRENT_TOTAL", "Paged current (total)", 80, "PH_ALIGN_RIGHT", "4", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_PAGEDTOTAL", "TRUE", "IDS_ET_POOL_COLUMN_PAGED_BYTES_TOTAL", "Paged bytes (total)", 80, "PH_ALIGN_LEFT", "5", "0"),
    ("TREE_COLUMN_ITEM_NONPAGEDALLOC", "TRUE", "IDS_ET_POOL_COLUMN_NONPAGED_ALLOCATIONS_TOTAL", "Non-paged allocations (total)", 80, "PH_ALIGN_RIGHT", "6", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_NONPAGEDFREE", "TRUE", "IDS_ET_POOL_COLUMN_NONPAGED_FREES_TOTAL", "Non-paged frees (total)", 80, "PH_ALIGN_RIGHT", "7", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_NONPAGEDCURRENT", "TRUE", "IDS_ET_POOL_COLUMN_NONPAGED_CURRENT_TOTAL", "Non-paged current (total)", 80, "PH_ALIGN_RIGHT", "8", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_NONPAGEDTOTAL", "TRUE", "IDS_ET_POOL_COLUMN_NONPAGED_BYTES_TOTAL", "Non-paged bytes (total)", 80, "PH_ALIGN_LEFT", "9", "0"),
    ("TREE_COLUMN_ITEM_ALLOC", "FALSE", "IDS_ET_POOL_COLUMN_ALLOCATIONS_TOTAL", "Allocations (total)", 80, "PH_ALIGN_RIGHT", "2", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_FREE", "FALSE", "IDS_ET_POOL_COLUMN_FREES_TOTAL", "Frees (total)", 80, "PH_ALIGN_RIGHT", "3", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_CURRENT", "FALSE", "IDS_ET_POOL_COLUMN_CURRENT_TOTAL", "Current (total)", 80, "PH_ALIGN_RIGHT", "4", "DT_RIGHT"),
    ("TREE_COLUMN_ITEM_TOTAL", "FALSE", "IDS_ET_POOL_COLUMN_BYTES_TOTAL", "Bytes (total)", 80, "PH_ALIGN_LEFT", "5", "0"),
    ("TREE_COLUMN_ITEM_PAGEDALLOCDELTA", "FALSE", "IDS_ET_POOL_COLUMN_PAGED_ALLOCATIONS_DELTA", "Paged allocations (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_PAGEDFREEDELTA", "FALSE", "IDS_ET_POOL_COLUMN_PAGED_FREES_DELTA", "Paged frees (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_PAGEDCURRENTDELTA", "FALSE", "IDS_ET_POOL_COLUMN_PAGED_CURRENT_DELTA", "Paged current (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_PAGEDTOTALDELTA", "FALSE", "IDS_ET_POOL_COLUMN_PAGED_BYTES_DELTA", "Paged bytes (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_NONPAGEDALLOCDELTA", "FALSE", "IDS_ET_POOL_COLUMN_NONPAGED_ALLOCATIONS_DELTA", "Non-paged allocations (delta)", 80, "PH_ALIGN_RIGHT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_NONPAGEDFREEDELTA", "FALSE", "IDS_ET_POOL_COLUMN_NONPAGED_FREES_DELTA", "Non-paged frees (delta)", 80, "PH_ALIGN_RIGHT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_NONPAGEDCURRENTDELTA", "FALSE", "IDS_ET_POOL_COLUMN_NONPAGED_CURRENT_DELTA", "Non-paged current (delta)", 80, "PH_ALIGN_RIGHT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_NONPAGEDTOTALDELTA", "FALSE", "IDS_ET_POOL_COLUMN_NONPAGED_BYTES_DELTA", "Non-paged bytes (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_ALLOCDELTA", "FALSE", "IDS_ET_POOL_COLUMN_ALLOCATIONS_DELTA", "Allocations (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_FREEDELTA", "FALSE", "IDS_ET_POOL_COLUMN_FREES_DELTA", "Frees (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_CURRENTDELTA", "FALSE", "IDS_ET_POOL_COLUMN_CURRENT_DELTA", "Current (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
    ("TREE_COLUMN_ITEM_TOTALDELTA", "FALSE", "IDS_ET_POOL_COLUMN_BYTES_DELTA", "Bytes (delta)", 80, "PH_ALIGN_LEFT", "ULONG_MAX", "0"),
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
    spec = importlib.util.spec_from_file_location("audit_extended_tools_pooltree", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedToolsPoolTreeDynamicUiResourceTests(unittest.TestCase):
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

    def test_all_tree_columns_use_the_exact_cached_resource_route(self) -> None:
        source = compact(SOURCE_PATH.read_text(encoding="utf-8"))

        for column, visible, symbol, english, width, alignment, sort, flags in COLUMN_ROUTES:
            with self.subTest(column=column):
                self.assertIn(
                    compact(
                        f"PhAddTreeNewColumn(Context->TreeNewHandle,{column},{visible},"
                        f'EtGetUiString({symbol},L"{english}"),{width},{alignment},{sort},{flags})'
                    ),
                    source,
                )

    def test_directed_pooltree_scan_has_no_old_hook_entries(self) -> None:
        audit = load_audit_module()
        entries = []
        audit.scan_c_file(SOURCE_PATH, entries)
        self.assertEqual(
            [
                (entry["category"], entry["line"], entry["english"])
                for entry in entries
                if entry["category"] == "c_treenew_col"
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()
