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
    (61379, "IDS_ET_OBJPRP_MENU_CLOSE", "C&lose\\bDel", "关闭(&L)\\bDel"),
    (61380, "IDS_ET_OBJPRP_MENU_PROTECTED", "&Protected", "保护(&P)"),
    (61381, "IDS_ET_OBJPRP_MENU_INHERIT", "&Inherit", "继承(&I)"),
    (61382, "IDS_ET_OBJPRP_MENU_GO_TO_PROCESS", "&Go to process\\bCtrl+Enter", "转到进程(&G)\\bCtrl+Enter"),
    (61383, "IDS_ET_OBJPRP_MENU_SECURITY", "&Security", "安全(&S)"),
    (61384, "IDS_ET_OBJPRP_MENU_SECURITY_ENTER", "&Security\\bEnter", "安全(&S)\\bEnter"),
    (61385, "IDS_ET_POOL_MENU_SHOW_ALLOCATIONS", "Show allocations", "显示分配"),
    (61386, "IDS_ET_REPARSE_MENU_REMOVE", "Remove...", "移除..."),
    (61387, "IDS_ET_REPARSE_MENU_FIND_FILES", "Find files...", "查找文件..."),
    (61388, "IDS_ET_WBCL_MENU_DETAILS", "&Details", "详细信息(&D)"),
    (61389, "IDS_ET_WSWATCH_MENU_OPEN_FILE_LOCATION", "Open &file location", "打开文件位置(&F)"),
    (61390, "IDS_ET_CONFIRM_ACTION_REMOVE", "remove", "移除"),
    (61391, "IDS_ET_CONFIRM_REPARSE_POINT", "the repase point", "该重分析点"),
    (61392, "IDS_ET_CONFIRM_REPARSE_POINT_WARNING", "The repase point will be permanently deleted.", "该重分析点将被永久删除。"),
    (61393, "IDS_ET_CONFIRM_OBJECT_IDENTIFIER", "the object identifier", "对象标识符"),
    (61394, "IDS_ET_CONFIRM_OBJECT_IDENTIFIER_WARNING", "The object identifier will be permanently deleted.", "对象标识符将被永久删除。"),
    (61395, "IDS_ET_CONFIRM_ACTION_END", "end", "结束"),
    (61396, "IDS_ET_CONFIRM_THREAD_IO", "I/O for the selected thread", "所选线程的 I/O"),
)

ROUTES = (
    ("acpitable.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("disktab.c", "&Go to process", "IDS_ET_FW_MENU_GO_TO_PROCESS", 1),
    ("disktab.c", "Open &file location\\bEnter", "IDS_ET_FW_MENU_OPEN_FILE_LOCATION", 1),
    ("disktab.c", "&Inspect", "IDS_ET_FW_MENU_INSPECT", 1),
    ("disktab.c", "P&roperties", "IDS_ET_FW_MENU_PROPERTIES", 1),
    ("disktab.c", "&Copy\\bCtrl+C", "IDS_ET_FW_MENU_COPY_SHORTCUT", 1),
    ("gpudetails.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("npudetails.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("objprp.c", "C&lose\\bDel", "IDS_ET_OBJPRP_MENU_CLOSE", 1),
    ("objprp.c", "&Protected", "IDS_ET_OBJPRP_MENU_PROTECTED", 1),
    ("objprp.c", "&Inherit", "IDS_ET_OBJPRP_MENU_INHERIT", 1),
    ("objprp.c", "&Go to process\\bCtrl+Enter", "IDS_ET_OBJPRP_MENU_GO_TO_PROCESS", 1),
    ("objprp.c", "&Security", "IDS_ET_OBJPRP_MENU_SECURITY", 1),
    ("objprp.c", "Prope&rties\\bEnter", "IDS_ET_OBJMGR_MENU_PROPERTIES_ENTER", 1),
    ("objprp.c", "&Copy\\bCtrl+C", "IDS_ET_FW_MENU_COPY_SHORTCUT", 2),
    ("objprp.c", "&Security\\bEnter", "IDS_ET_OBJPRP_MENU_SECURITY_ENTER", 1),
    ("pooldialog.c", "Show allocations", "IDS_ET_POOL_MENU_SHOW_ALLOCATIONS", 1),
    ("pooldialog.c", "&Copy\\bCtrl+C", "IDS_ET_FW_MENU_COPY_SHORTCUT", 1),
    ("pooldialogbig.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("reparse.c", "&Copy", "IDS_ET_MENU_COPY", 2),
    ("reparse.c", "Remove...", "IDS_ET_REPARSE_MENU_REMOVE", 1),
    ("reparse.c", "Find files...", "IDS_ET_REPARSE_MENU_FIND_FILES", 1),
    ("smbios.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("tpm.c", "&Edit", "IDS_ET_MENU_EDIT", 1),
    ("tpm.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("unldll.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("wbcl.c", "&Details", "IDS_ET_WBCL_MENU_DETAILS", 1),
    ("wbcl.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("wswatch.c", "&Inspect", "IDS_ET_FW_MENU_INSPECT", 1),
    ("wswatch.c", "Open &file location", "IDS_ET_WSWATCH_MENU_OPEN_FILE_LOCATION", 1),
    ("wswatch.c", "&Copy", "IDS_ET_MENU_COPY", 1),
    ("reparse.c", "remove", "IDS_ET_CONFIRM_ACTION_REMOVE", 2),
    ("reparse.c", "the repase point", "IDS_ET_CONFIRM_REPARSE_POINT", 1),
    ("reparse.c", "The repase point will be permanently deleted.", "IDS_ET_CONFIRM_REPARSE_POINT_WARNING", 1),
    ("reparse.c", "the object identifier", "IDS_ET_CONFIRM_OBJECT_IDENTIFIER", 1),
    ("reparse.c", "The object identifier will be permanently deleted.", "IDS_ET_CONFIRM_OBJECT_IDENTIFIER_WARNING", 1),
    ("thrdact.c", "end", "IDS_ET_CONFIRM_ACTION_END", 1),
    ("thrdact.c", "I/O for the selected thread", "IDS_ET_CONFIRM_THREAD_IO", 1),
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
    spec = importlib.util.spec_from_file_location("audit_extended_tools_menu_confirm", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedToolsMenuConfirmDynamicUiResourceTests(unittest.TestCase):
    def test_resources_are_contiguous_bilingual_and_cached(self) -> None:
        header, header_source = parse_header()
        english = parse_stringtable(ENGLISH_RC)
        chinese = parse_stringtable(CHINESE_RC)

        self.assertEqual(len(header), 470)
        self.assertEqual(len(english), 470)
        self.assertEqual(len(chinese), 470)
        self.assertEqual(sorted(header.values()), list(range(61000, 61470)))
        self.assertRegex(
            header_source,
            r"(?m)^#define\s+IDS_ET_CACHED_LAST\s+IDS_ET_GPU_NODE_COLUMN_FORMAT$",
        )
        self.assertRegex(header_source, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61470$")

        for resource_id, symbol, en_text, zh_text in NEW_RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(header[symbol], resource_id)
                self.assertEqual(english[symbol], en_text)
                self.assertEqual(chinese[symbol], zh_text)

    def test_all_41_routes_use_the_exact_cached_resource(self) -> None:
        self.assertEqual(sum(count for _, _, _, count in ROUTES), 41)

        for filename, english, symbol, count in ROUTES:
            with self.subTest(filename=filename, english=english):
                source = compact((PLUGIN_ROOT / filename).read_text(encoding="utf-8"))
                route = compact(f'EtGetUiString({symbol},L"{english}")')
                self.assertEqual(source.count(route), count)

        self.assertIn(
            "PCWSTR EtGetUiString(",
            (PLUGIN_ROOT / "thrdact.c").read_text(encoding="utf-8"),
        )

    def test_directed_scan_has_no_legacy_dynamic_ui_entries(self) -> None:
        audit = load_audit_module()
        categories = {
            "c_confirm",
            "c_emenu",
            "c_listview_col",
            "c_listview_item",
            "c_msgbox",
            "c_search",
            "c_tab",
            "c_treenew_col",
            "c_treenew_empty",
        }
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
