import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
SOURCE_PATH = PLUGIN_ROOT / "fwtab.c"
HEADER_PATH = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "ExtendedTools.rc"
CHINESE_RC = PLUGIN_ROOT / "ExtendedTools.zh-cn.rc"

NEW_RESOURCES = (
    (61245, "IDS_ET_FW_COLUMN_PID", "PID", "PID"),
    (61246, "IDS_ET_FW_COLUMN_ACTION", "Action", "操作"),
    (61247, "IDS_ET_FW_COLUMN_DIRECTION", "Direction", "方向"),
    (61248, "IDS_ET_FW_COLUMN_RULE", "Rule", "规则"),
    (61249, "IDS_ET_FW_COLUMN_DESCRIPTION", "Description", "描述"),
    (61250, "IDS_ET_FW_COLUMN_FILTER_ORIGIN", "Filter origin", "筛选器来源"),
    (61251, "IDS_ET_FW_COLUMN_LOCAL_ADDRESS", "Local address", "本地地址"),
    (61252, "IDS_ET_FW_COLUMN_LOCAL_PORT", "Local port", "本地端口"),
    (61253, "IDS_ET_FW_COLUMN_LOCAL_HOSTNAME", "Local hostname", "本地主机名"),
    (61254, "IDS_ET_FW_COLUMN_REMOTE_ADDRESS", "Remote address", "远程地址"),
    (61255, "IDS_ET_FW_COLUMN_REMOTE_PORT", "Remote port", "远程端口"),
    (61256, "IDS_ET_FW_COLUMN_REMOTE_HOSTNAME", "Remote hostname", "远程主机名"),
    (61257, "IDS_ET_FW_COLUMN_PROTOCOL", "Protocol", "协议"),
    (61258, "IDS_ET_FW_COLUMN_TIMESTAMP", "Timestamp", "时间戳"),
    (61259, "IDS_ET_FW_COLUMN_USERNAME", "Username", "用户名"),
    (61260, "IDS_ET_FW_COLUMN_COUNTRY", "Country", "国家/地区"),
    (61261, "IDS_ET_FW_COLUMN_LOCAL_ADDRESS_CLASS", "Local address class", "本地地址类别"),
    (61262, "IDS_ET_FW_COLUMN_REMOTE_ADDRESS_CLASS", "Remote address class", "远程地址类别"),
    (61263, "IDS_ET_FW_COLUMN_LOCAL_ADDRESS_SCOPE", "Local address scope", "本地地址作用域"),
    (61264, "IDS_ET_FW_COLUMN_REMOTE_ADDRESS_SCOPE", "Remote address scope", "远程地址作用域"),
    (61265, "IDS_ET_FW_COLUMN_ORIGINAL_NAME", "Original name", "原始名称"),
    (61266, "IDS_ET_FW_COLUMN_LOCAL_PORT_SERVICE", "Local port service", "本地端口服务"),
    (61267, "IDS_ET_FW_COLUMN_REMOTE_PORT_SERVICE", "Remote port service", "远程端口服务"),
    (61268, "IDS_ET_FW_COLUMN_INTERFACE_LUID", "Interface LUID", "接口 LUID"),
    (61269, "IDS_ET_FW_COLUMN_COMPARTMENT_ID", "Compartment ID", "隔离舱 ID"),
    (61270, "IDS_ET_FW_COLUMN_POLICY_APP_ID", "Policy app ID", "策略应用 ID"),
    (61271, "IDS_ET_FW_COLUMN_SERVICE_SIDS", "Service SIDs", "服务 SID"),
    (61272, "IDS_ET_FW_COLUMN_FQBN_NAME", "FQBN name", "FQBN 名称"),
    (61273, "IDS_ET_FW_MENU_PING", "&Ping", "Ping(&P)"),
    (61274, "IDS_ET_FW_MENU_TRACEROUTE", "&Traceroute", "路由跟踪(&T)"),
    (61275, "IDS_ET_FW_MENU_WHOIS", "&Whois", "Whois 查询(&W)"),
    (61276, "IDS_ET_FW_MENU_GO_TO_PROCESS", "&Go to process", "转到进程(&G)"),
    (61277, "IDS_ET_FW_MENU_OPEN_FILE_LOCATION", "Open &file location\\bEnter", "打开文件位置(&f)\\bEnter"),
    (61278, "IDS_ET_FW_MENU_INSPECT", "&Inspect", "检查(&I)"),
    (61279, "IDS_ET_FW_MENU_PROPERTIES", "P&roperties", "属性(&R)"),
    (61280, "IDS_ET_FW_MENU_COPY_SHORTCUT", "&Copy\\bCtrl+C", "复制(&C)\\bCtrl+C"),
)

COLUMN_ROUTES = (
    ("PhAddTreeNewColumnEx2", "FW_COLUMN_NAME", "IDS_ET_WCT_COLUMN_NAME", "Name"),
    ("PhAddTreeNewColumnEx", "FW_COLUMN_PROCESSID", "IDS_ET_FW_COLUMN_PID", "PID"),
    ("PhAddTreeNewColumn", "FW_COLUMN_ACTION", "IDS_ET_FW_COLUMN_ACTION", "Action"),
    ("PhAddTreeNewColumn", "FW_COLUMN_DIRECTION", "IDS_ET_FW_COLUMN_DIRECTION", "Direction"),
    ("PhAddTreeNewColumn", "FW_COLUMN_RULENAME", "IDS_ET_FW_COLUMN_RULE", "Rule"),
    ("PhAddTreeNewColumn", "FW_COLUMN_RULEDESCRIPTION", "IDS_ET_FW_COLUMN_DESCRIPTION", "Description"),
    ("PhAddTreeNewColumn", "FW_COLUMN_FILTER_ORIGIN", "IDS_ET_FW_COLUMN_FILTER_ORIGIN", "Filter origin"),
    ("PhAddTreeNewColumnEx", "FW_COLUMN_LOCALADDRESS", "IDS_ET_FW_COLUMN_LOCAL_ADDRESS", "Local address"),
    ("PhAddTreeNewColumnEx", "FW_COLUMN_LOCALPORT", "IDS_ET_FW_COLUMN_LOCAL_PORT", "Local port"),
    ("PhAddTreeNewColumn", "FW_COLUMN_LOCALHOSTNAME", "IDS_ET_FW_COLUMN_LOCAL_HOSTNAME", "Local hostname"),
    ("PhAddTreeNewColumnEx", "FW_COLUMN_REMOTEADDRESS", "IDS_ET_FW_COLUMN_REMOTE_ADDRESS", "Remote address"),
    ("PhAddTreeNewColumnEx", "FW_COLUMN_REMOTEPORT", "IDS_ET_FW_COLUMN_REMOTE_PORT", "Remote port"),
    ("PhAddTreeNewColumn", "FW_COLUMN_REMOTEHOSTNAME", "IDS_ET_FW_COLUMN_REMOTE_HOSTNAME", "Remote hostname"),
    ("PhAddTreeNewColumn", "FW_COLUMN_PROTOCOL", "IDS_ET_FW_COLUMN_PROTOCOL", "Protocol"),
    ("PhAddTreeNewColumn", "FW_COLUMN_TIMESTAMP", "IDS_ET_FW_COLUMN_TIMESTAMP", "Timestamp"),
    ("PhAddTreeNewColumn", "FW_COLUMN_USER", "IDS_ET_FW_COLUMN_USERNAME", "Username"),
    ("PhAddTreeNewColumnEx2", "FW_COLUMN_COUNTRY", "IDS_ET_FW_COLUMN_COUNTRY", "Country"),
    ("PhAddTreeNewColumn", "FW_COLUMN_LOCALADDRESSCLASS", "IDS_ET_FW_COLUMN_LOCAL_ADDRESS_CLASS", "Local address class"),
    ("PhAddTreeNewColumn", "FW_COLUMN_REMOTEADDRESSCLASS", "IDS_ET_FW_COLUMN_REMOTE_ADDRESS_CLASS", "Remote address class"),
    ("PhAddTreeNewColumn", "FW_COLUMN_LOCALADDRESSSSCOPE", "IDS_ET_FW_COLUMN_LOCAL_ADDRESS_SCOPE", "Local address scope"),
    ("PhAddTreeNewColumn", "FW_COLUMN_REMOTEADDRESSSCOPE", "IDS_ET_FW_COLUMN_REMOTE_ADDRESS_SCOPE", "Remote address scope"),
    ("PhAddTreeNewColumn", "FW_COLUMN_ORIGINALNAME", "IDS_ET_FW_COLUMN_ORIGINAL_NAME", "Original name"),
    ("PhAddTreeNewColumn", "FW_COLUMN_LOCALSERVICENAME", "IDS_ET_FW_COLUMN_LOCAL_PORT_SERVICE", "Local port service"),
    ("PhAddTreeNewColumn", "FW_COLUMN_REMOTESERVICENAME", "IDS_ET_FW_COLUMN_REMOTE_PORT_SERVICE", "Remote port service"),
    ("PhAddTreeNewColumn", "FW_COLUMN_INTERFACE_LUID", "IDS_ET_FW_COLUMN_INTERFACE_LUID", "Interface LUID"),
    ("PhAddTreeNewColumn", "FW_COLUMN_COMPARTMENT_ID", "IDS_ET_FW_COLUMN_COMPARTMENT_ID", "Compartment ID"),
    ("PhAddTreeNewColumn", "FW_COLUMN_POLICY_APP_ID", "IDS_ET_FW_COLUMN_POLICY_APP_ID", "Policy app ID"),
    ("PhAddTreeNewColumn", "FW_COLUMN_SERVICE_SIDS", "IDS_ET_FW_COLUMN_SERVICE_SIDS", "Service SIDs"),
    ("PhAddTreeNewColumn", "FW_COLUMN_FQBN_NAME", "IDS_ET_FW_COLUMN_FQBN_NAME", "FQBN name"),
)

MENU_ROUTES = (
    ("FW_ITEM_COMMAND_ID_PING", "IDS_ET_FW_MENU_PING", "&Ping"),
    ("FW_ITEM_COMMAND_ID_TRACERT", "IDS_ET_FW_MENU_TRACEROUTE", "&Traceroute"),
    ("FW_ITEM_COMMAND_ID_WHOIS", "IDS_ET_FW_MENU_WHOIS", "&Whois"),
    ("FW_ITEM_COMMAND_ID_GOTOPROCESS", "IDS_ET_FW_MENU_GO_TO_PROCESS", "&Go to process"),
    ("FW_ITEM_COMMAND_ID_OPENFILELOCATION", "IDS_ET_FW_MENU_OPEN_FILE_LOCATION", "Open &file location\\bEnter"),
    ("FW_ITEM_COMMAND_ID_INSPECT", "IDS_ET_FW_MENU_INSPECT", "&Inspect"),
    ("FW_ITEM_COMMAND_ID_PROPERTIES", "IDS_ET_FW_MENU_PROPERTIES", "P&roperties"),
    ("FW_ITEM_COMMAND_ID_COPY", "IDS_ET_FW_MENU_COPY_SHORTCUT", "&Copy\\bCtrl+C"),
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
    spec = importlib.util.spec_from_file_location("audit_extended_tools_fwtab", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedToolsFirewallDynamicUiResourceTests(unittest.TestCase):
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

    def test_columns_menus_and_status_use_cached_resources(self) -> None:
        source = compact(SOURCE_PATH.read_text(encoding="utf-8"))

        for function, column, symbol, english in COLUMN_ROUTES:
            with self.subTest(column=column):
                self.assertRegex(
                    source,
                    re.escape(compact(f"{function}(TreeNewHandle,{column},"))
                    + r"(?:TRUE|FALSE),"
                    + re.escape(
                        compact(f'EtGetUiString({symbol},L"{english}"),')
                    ),
                )

        for command, symbol, english in MENU_ROUTES:
            with self.subTest(command=command):
                self.assertIn(
                    compact(
                        f'PhCreateEMenuItem(0,{command},'
                        f'EtGetUiString({symbol},L"{english}"),NULL,NULL)'
                    ),
                    source,
                )

        self.assertIn(
            'PhShowStatus(TreeWindowHandle,EtGetUiString('
            'IDS_ET_WCT_PROCESS_NOT_FOUND,L"Theprocessdoesnotexist."),'
            'STATUS_INVALID_CID,0)',
            source,
        )

    def test_directed_fwtab_scan_has_no_old_hook_entries(self) -> None:
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
