import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
SOURCE_PATH = PLUGIN_ROOT / "objmgr.c"
HEADER_PATH = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "ExtendedTools.rc"
CHINESE_RC = PLUGIN_ROOT / "ExtendedTools.zh-cn.rc"

NEW_RESOURCES = (
    (61281, "IDS_ET_OBJMGR_UNIDENTIFIED_THIRD_PARTY_OBJECT", "Unidentified third party object.", "未识别的第三方对象。"),
    (61282, "IDS_ET_OBJMGR_COLUMN_TARGET", "Target", "目标"),
    (61283, "IDS_ET_OBJMGR_COLUMN_OBJECT_ADDRESS", "Object address", "对象地址"),
    (61284, "IDS_ET_OBJMGR_SEARCH", "Search Objects (Ctrl+K)", "搜索对象 (Ctrl+K)"),
    (61285, "IDS_ET_OBJMGR_MENU_RESET_SORT", "&Reset sort", "重置排序(&R)"),
    (61286, "IDS_ET_OBJMGR_MENU_PROPERTIES_ENTER", "Prope&rties\\bEnter", "属性(&R)\\bEnter"),
    (61287, "IDS_ET_OBJMGR_MENU_PROPERTIES_SHIFT_ENTER", "Prope&rties\\bShift+Enter", "属性(&r)\\bShift+Enter"),
    (61288, "IDS_ET_OBJMGR_MENU_HANDLES", "&Handles\\bCtrl+H", "句柄(&H)\\bCtrl+H"),
    (61289, "IDS_ET_OBJMGR_MENU_OPEN_LINK", "&Open link\\bEnter", "打开链接(&O)\\bEnter"),
    (61290, "IDS_ET_OBJMGR_MENU_GO_TO_UPPER_DEVICE_DRIVER", "Go to &upper device driver", "转到上层设备驱动程序(&u)"),
    (61291, "IDS_ET_OBJMGR_MENU_GO_TO_LOWER_DEVICE_DRIVER", "&Go to lower device driver", "转到下层设备驱动程序(&G)"),
    (61292, "IDS_ET_OBJMGR_MENU_GO_TO_DEVICE_DRIVER", "&Go to device driver", "转到设备驱动程序(&G)"),
    (61293, "IDS_ET_OBJMGR_MENU_GO_TO_PROCESS", "&Go to process...", "转到进程(&G)..."),
    (61294, "IDS_ET_OBJMGR_MENU_GO_TO_THREAD", "&Go to thread...", "转到线程(&G)..."),
    (61295, "IDS_ET_OBJMGR_MENU_OPEN_FILE_LOCATION", "&Open file location", "打开文件位置(&O)"),
    (61296, "IDS_ET_OBJMGR_MENU_SHOW_DRIVE_VOLUME", "Sh&ow drive volume", "显示驱动器卷(&o)"),
    (61297, "IDS_ET_OBJMGR_MENU_SECURITY", "&Security\\bCtrl+Enter", "安全(&S)\\bCtrl+Enter"),
    (61298, "IDS_ET_OBJMGR_MENU_COPY_OBJECT_ADDRESS", "Copy Object &Address\\bCtrl+Shift+C", "复制对象地址(&A)\\bCtrl+Shift+C"),
    (61299, "IDS_ET_OBJMGR_MENU_COPY_FULL_NAME", "Copy &Full Name\\bCtrl+Alt+C", "复制完整名称(&F)\\bCtrl+Alt+C"),
    (61300, "IDS_ET_OBJMGR_ERROR_CREATE_WINDOW", "Unable to create the window.", "无法创建窗口。"),
)

MENU_ROUTES = (
    ("IDC_RESETSORT", "IDS_ET_OBJMGR_MENU_RESET_SORT", "&Reset sort", 1),
    ("IDC_PROPERTIES", "IDS_ET_OBJMGR_MENU_PROPERTIES_SHIFT_ENTER", "Prope&rties\\bShift+Enter", 1),
    ("IDC_OPENHANDLES", "IDS_ET_OBJMGR_MENU_HANDLES", "&Handles\\bCtrl+H", 2),
    ("IDC_OPENLINK", "IDS_ET_OBJMGR_MENU_OPEN_LINK", "&Open link\\bEnter", 1),
    ("IDC_GOTODRIVER2", "IDS_ET_OBJMGR_MENU_GO_TO_UPPER_DEVICE_DRIVER", "Go to &upper device driver", 1),
    ("IDC_GOTODRIVER", "IDS_ET_OBJMGR_MENU_GO_TO_LOWER_DEVICE_DRIVER", "&Go to lower device driver", 1),
    ("IDC_GOTODRIVER", "IDS_ET_OBJMGR_MENU_GO_TO_DEVICE_DRIVER", "&Go to device driver", 1),
    ("IDC_GOTOPROCESS", "IDS_ET_OBJMGR_MENU_GO_TO_PROCESS", "&Go to process...", 1),
    ("IDC_GOTOTHREAD", "IDS_ET_OBJMGR_MENU_GO_TO_THREAD", "&Go to thread...", 1),
    ("IDC_OPENFILELOCATION", "IDS_ET_OBJMGR_MENU_OPEN_FILE_LOCATION", "&Open file location", 1),
    ("IDC_SECURITY", "IDS_ET_OBJMGR_MENU_SECURITY", "&Security\\bCtrl+Enter", 2),
    ("IDC_COPYOBJECTADDRESS", "IDS_ET_OBJMGR_MENU_COPY_OBJECT_ADDRESS", "Copy Object &Address\\bCtrl+Shift+C", 2),
    ("IDC_COPYPATH", "IDS_ET_OBJMGR_MENU_COPY_FULL_NAME", "Copy &Full Name\\bCtrl+Alt+C", 2),
    ("IDC_COPY", "IDS_ET_FW_MENU_COPY_SHORTCUT", "&Copy\\bCtrl+C", 2),
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
    spec = importlib.util.spec_from_file_location("audit_extended_tools_objmgr", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedToolsObjectManagerDynamicUiResourceTests(unittest.TestCase):
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

    def test_columns_search_status_and_errors_use_cached_resources(self) -> None:
        source = compact(SOURCE_PATH.read_text(encoding="utf-8"))

        for column, width, symbol, english in (
            ("ETOBLVC_NAME", 445, "IDS_ET_WCT_COLUMN_NAME", "Name"),
            ("ETOBLVC_TYPE", 150, "IDS_ET_TYPE", "Type"),
            ("ETOBLVC_TARGET", 200, "IDS_ET_OBJMGR_COLUMN_TARGET", "Target"),
            ("ETOBLVC_OBJECT", 120, "IDS_ET_OBJMGR_COLUMN_OBJECT_ADDRESS", "Object address"),
        ):
            with self.subTest(column=column):
                self.assertIn(
                    compact(
                        f"PhAddListViewColumn(context->ListViewHandle,{column},{column},"
                        f'{column},LVCFMT_LEFT,{width},'
                        f'EtGetUiString({symbol},L"{english}"))'
                    ),
                    source,
                )

        self.assertIn(
            compact('EtGetUiString(IDS_ET_OBJMGR_SEARCH,L"Search Objects (Ctrl+K)")'),
            source,
        )
        self.assertIn(
            compact('PhShowStatus(NULL,EtGetUiString(IDS_ET_OBJMGR_UNIDENTIFIED_THIRD_PARTY_OBJECT,L"Unidentified third party object."),status,0)'),
            source,
        )
        self.assertIn(
            compact('PhShowError2(ParentWindowHandle,EtGetUiString(IDS_ET_OBJMGR_ERROR_CREATE_WINDOW,L"Unable to create the window."),L"%s",L"")'),
            source,
        )

    def test_all_menu_routes_use_cached_resources_with_expected_multiplicity(self) -> None:
        source = compact(SOURCE_PATH.read_text(encoding="utf-8"))

        for command, symbol, english, count in MENU_ROUTES:
            with self.subTest(command=command, symbol=symbol):
                route = compact(f'PhCreateEMenuItem(0,{command},EtGetUiString({symbol},L"{english}")')
                self.assertEqual(source.count(route), count)

        self.assertIn(
            compact(
                'PhCreateEMenuItem(0,IDC_PROPERTIES,!isSymlink?'
                'EtGetUiString(IDS_ET_OBJMGR_MENU_PROPERTIES_ENTER,L"Prope&rties\\bEnter"):'
                'EtGetUiString(IDS_ET_OBJMGR_MENU_PROPERTIES_SHIFT_ENTER,L"Prope&rties\\bShift+Enter"),'
            ),
            source,
        )
        self.assertIn(
            compact(
                'PhCreateEMenuItem(0,IDC_OPENFILELOCATION,targetIsDriveVolume?'
                'EtGetUiString(IDS_ET_OBJMGR_MENU_SHOW_DRIVE_VOLUME,L"Sh&ow drive volume"):'
                'EtGetUiString(IDS_ET_OBJMGR_MENU_OPEN_FILE_LOCATION,L"&Open file location"),'
            ),
            source,
        )

    def test_directed_objmgr_scan_has_no_old_hook_entries(self) -> None:
        audit = load_audit_module()
        entries = []
        audit.scan_c_file(SOURCE_PATH, entries)
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
        self.assertEqual(
            [
                (entry["category"], entry["line"], entry["english"])
                for entry in entries
                if entry["category"] in categories
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()
