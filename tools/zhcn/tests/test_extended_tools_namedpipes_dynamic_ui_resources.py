import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
SOURCE_PATH = PLUGIN_ROOT / "namedpipes.c"
HEADER_PATH = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "ExtendedTools.rc"
CHINESE_RC = PLUGIN_ROOT / "ExtendedTools.zh-cn.rc"

NEW_RESOURCES = (
    (61231, "IDS_ET_PIPE_CLIENT", "Client", "客户端"),
    (61232, "IDS_ET_PIPE_SERVER", "Server", "服务器"),
    (61233, "IDS_ET_PIPE_COLUMN_END", "End", "结束"),
    (61234, "IDS_ET_PIPE_COLUMN_PROCESS", "Process", "进程"),
    (61235, "IDS_ET_PIPE_COLUMN_HANDLE", "Handle", "句柄"),
    (61236, "IDS_ET_PIPE_COLUMN_GRANTED_ACCESS", "Granted access", "已授予的权限"),
    (61237, "IDS_ET_PIPE_COLUMN_CONFIGURATION", "Configuration", "配置"),
    (61238, "IDS_ET_PIPE_COLUMN_MAX_INSTANCES", "Max instances", "最大实例数"),
    (61239, "IDS_ET_PIPE_COLUMN_CURRENT_INSTANCES", "Current instances", "当前实例数"),
    (61240, "IDS_ET_PIPE_COLUMN_READ_DATA_AVAILABLE", "Read data available", "可读数据"),
    (61241, "IDS_ET_PIPE_COLUMN_OUTBOUND_QUOTA", "Outbound quota", "输出配额"),
    (61242, "IDS_ET_PIPE_COLUMN_REMOTE_CLIENTS", "Remote clients", "远程客户端数"),
    (61243, "IDS_ET_PIPE_COLUMN_READ_MODE", "Read mode", "读取模式"),
    (61244, "IDS_ET_PIPE_COLUMN_COMPLETION_MODE", "Completion mode", "完成模式"),
    (61470, "IDS_ET_SEARCH_NAMED_PIPES", "Search Named Pipes (Ctrl+K)", "搜索命名管道（Ctrl+K）"),
)

TREE_COLUMNS = (
    ("ET_PIPE_COLUMN_END", "Context->UseKph", 50, "IDS_ET_PIPE_COLUMN_END", "End"),
    ("ET_PIPE_COLUMN_NAME", "TRUE", 200, "IDS_ET_WCT_COLUMN_NAME", "Name"),
    ("ET_PIPE_COLUMN_PROCESS", "TRUE", 200, "IDS_ET_PIPE_COLUMN_PROCESS", "Process"),
    ("ET_PIPE_COLUMN_HANDLE", "Context->UseKph", 80, "IDS_ET_PIPE_COLUMN_HANDLE", "Handle"),
    ("ET_PIPE_COLUMN_GRANTEDACCESS", "Context->UseKph", 140, "IDS_ET_PIPE_COLUMN_GRANTED_ACCESS", "Granted access"),
    ("ET_PIPE_COLUMN_TYPE", "TRUE", 80, "IDS_ET_TYPE", "Type"),
    ("ET_PIPE_COLUMN_CONFIGURATION", "TRUE", 80, "IDS_ET_PIPE_COLUMN_CONFIGURATION", "Configuration"),
    ("ET_PIPE_COLUMN_MAXIMUMINSTANCES", "TRUE", 80, "IDS_ET_PIPE_COLUMN_MAX_INSTANCES", "Max instances"),
    ("ET_PIPE_COLUMN_CURRENTINSTANCES", "TRUE", 80, "IDS_ET_PIPE_COLUMN_CURRENT_INSTANCES", "Current instances"),
    ("ET_PIPE_COLUMN_READDATAAVAILABLE", "TRUE", 80, "IDS_ET_PIPE_COLUMN_READ_DATA_AVAILABLE", "Read data available"),
    ("ET_PIPE_COLUMN_OUTBOUNDQUOTA", "TRUE", 80, "IDS_ET_PIPE_COLUMN_OUTBOUND_QUOTA", "Outbound quota"),
    ("ET_PIPE_COLUMN_STATE", "TRUE", 80, "IDS_ET_STATE", "State"),
    ("ET_PIPE_COLUMN_REMOTECLIENTS", "TRUE", 80, "IDS_ET_PIPE_COLUMN_REMOTE_CLIENTS", "Remote clients"),
    ("ET_PIPE_COLUMN_READMODE", "TRUE", 80, "IDS_ET_PIPE_COLUMN_READ_MODE", "Read mode"),
    ("ET_PIPE_COLUMN_COMPLETIONMODE", "TRUE", 80, "IDS_ET_PIPE_COLUMN_COMPLETION_MODE", "Completion mode"),
)


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "audit_extended_tools_namedpipes_dynamic_ui", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_header() -> tuple[dict[str, int], str]:
    source = HEADER_PATH.read_text(encoding="utf-8")
    return (
        {
            name: int(value)
            for name, value in re.findall(
                r"^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)\b",
                source,
                re.MULTILINE,
            )
        },
        source,
    )


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8-sig")
    return {
        name: value.replace('""', '"')
        for name, value in re.findall(
            r'^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:""|[^"])*)"',
            source,
            re.MULTILINE,
        )
    }


class ExtendedToolsNamedPipesDynamicUiResourceTests(unittest.TestCase):
    def test_resources_are_contiguous_bilingual_and_inside_the_module_cache(self) -> None:
        header, header_source = parse_header()
        english = parse_stringtable(ENGLISH_RC)
        chinese = parse_stringtable(CHINESE_RC)

        self.assertEqual(len(header), 471)
        self.assertEqual(len(english), 471)
        self.assertEqual(len(chinese), 471)
        self.assertRegex(
            header_source,
            r"(?m)^#define\s+IDS_ET_CACHED_LAST\s+IDS_ET_SEARCH_NAMED_PIPES$",
        )
        self.assertRegex(
            header_source,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61471$",
        )

        for resource_id, symbol, en_text, zh_text in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(header[symbol], resource_id)
                self.assertEqual(english[symbol], en_text)
                self.assertEqual(chinese[symbol], zh_text)

    def test_client_server_items_and_all_visible_columns_use_cached_resources(self) -> None:
        source = compact(SOURCE_PATH.read_text(encoding="utf-8"))

        for symbol, english in (
            ("IDS_ET_PIPE_CLIENT", "Client"),
            ("IDS_ET_PIPE_SERVER", "Server"),
        ):
            self.assertIn(
                compact(
                    "EtSetPipeNodeColumn(node,ET_PIPE_COLUMN_END,"
                    f"EtGetUiString({symbol},L\"{english}\"))"
                ),
                source,
            )

        for column, visible, width, symbol, english in TREE_COLUMNS:
            with self.subTest(column=column, symbol=symbol):
                self.assertIn(
                    compact(
                        "PhAddTreeNewColumn(Context->TreeNewHandle,"
                        f"{column},{visible},EtGetUiString({symbol},L\"{english}\"),"
                        f"{width},PH_ALIGN_LEFT,index++,0)"
                    ),
                    source,
                )

        self.assertIn(
            compact(
                "PhCreateSearchControl(WindowHandle,context->SearchBoxHandle,"
                "EtGetUiString(IDS_ET_SEARCH_NAMED_PIPES,"
                "L\"Search Named Pipes (Ctrl+K)\")"
            ),
            source,
        )

    def test_directed_namedpipes_scan_has_no_old_hook_entries(self) -> None:
        audit = load_audit_module()
        entries = []
        audit.scan_c_file(SOURCE_PATH, entries)

        self.assertEqual(
            [
                (entry["category"], entry["line"], entry["english"])
                for entry in entries
                if entry["category"] in {"c_listview_col", "c_listview_item"}
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()
