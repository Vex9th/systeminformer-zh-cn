import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedServices"
RESOURCE_HEADER = PLUGIN_ROOT / "resource.h"
ENGLISH_RC = PLUGIN_ROOT / "ExtendedServices.rc"
CHINESE_RC = PLUGIN_ROOT / "ExtendedServices.zh-cn.rc"
TARGET_CATEGORIES = {"c_emenu", "c_listview_col", "c_msgbox", "c_taskdialog"}

RESOURCE_ROUTES = (
    (2070, "IDS_ES_MENU_ENABLE", "Enable", "启用", "svcpnp.c"),
    (2071, "IDS_ES_MENU_DISABLE", "Disable", "禁用", "svcpnp.c"),
    (2072, "IDS_ES_MENU_RESTART", "Restart", "重启", "svcpnp.c"),
    (2073, "IDS_ES_MENU_UNINSTALL", "Uninstall", "卸载", "svcpnp.c"),
    (2074, "IDS_ES_MENU_OPEN_KEY", "Open key", "打开注册表项", "svcpnp.c"),
    (2075, "IDS_ES_MENU_HARDWARE", "Hardware", "硬件", "svcpnp.c"),
    (2076, "IDS_ES_MENU_SOFTWARE", "Software", "软件", "svcpnp.c"),
    (2077, "IDS_ES_MENU_USER", "User", "用户", "svcpnp.c"),
    (2078, "IDS_ES_MENU_CONFIG", "Config", "配置", "svcpnp.c"),
    (2079, "IDS_ES_MENU_PROPERTIES", "Properties", "属性", "svcpnp.c"),
    (2080, "IDS_ES_COLUMN_PNP_DEVICES", "PnP Devices", "PnP 设备", "svcpnp.c"),
    (2081, "IDS_ES_COLUMN_TRIGGER", "Trigger", "触发器", "trigger.c"),
    (2082, "IDS_ES_COLUMN_ACTION", "Action", "操作", "trigger.c"),
    (2083, "IDS_ES_COLUMN_DATA", "Data", "数据", "trigger.c"),
    (2084, "IDS_ES_COLUMN_PRIVILEGE_NAME", "Name", "名称", "other.c"),
    (
        2085,
        "IDS_ES_COLUMN_PRIVILEGE_DISPLAY_NAME",
        "Display name",
        "显示名称",
        "other.c",
    ),
    (
        2086,
        "IDS_ES_INVALID_GUID_HINT",
        'Please ensure that the string is a valid GUID: "{x-x-x-x-x}".',
        "请确保该字符串是有效的 GUID：“{x-x-x-x-x}”。",
        "trigger.c",
    ),
    (
        2087,
        "IDS_ES_PRIVILEGE_ALREADY_ADDED",
        "The selected privilege has already been added.",
        "所选特权已添加。",
        "other.c",
    ),
    (
        2088,
        "IDS_ES_SERVICE_PROTECTION_WARNING",
        "Setting service protection will prevent the service from being controlled, modified, or deleted.",
        "设置服务保护将阻止该服务被控制、修改或删除。",
        "other.c",
    ),
    (
        2089,
        "IDS_ES_CONTINUE_PROMPT",
        "Do you want to continue?",
        "要继续吗？",
        "other.c",
    ),
)


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "audit_extended_services_dynamic_ui_resources", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_header_ids() -> dict[str, int]:
    return {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(IDS_ES_[A-Z0-9_]+)\s+(\d+)\b",
            RESOURCE_HEADER.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    }


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8-sig")
    return {
        name: value.replace('""', '"')
        for name, value in re.findall(
            r'^\s*(IDS_ES_[A-Z0-9_]+)\s+"((?:""|[^"])*)"',
            source,
            re.MULTILINE,
        )
    }


class ExtendedServicesDynamicUiResourceTests(unittest.TestCase):
    def test_resources_are_contiguous_and_bilingual(self) -> None:
        header_ids = parse_header_ids()
        english = parse_stringtable(ENGLISH_RC)
        chinese = parse_stringtable(CHINESE_RC)

        self.assertEqual(len(header_ids), 90)
        self.assertEqual(len(english), 90)
        self.assertEqual(len(chinese), 90)
        self.assertEqual(
            re.search(
                r"#define\s+_APS_NEXT_SYMED_VALUE\s+(\d+)",
                RESOURCE_HEADER.read_text(encoding="utf-8"),
            ).group(1),
            "2090",
        )

        for resource_id, symbol, en_text, zh_text, _ in RESOURCE_ROUTES:
            with self.subTest(symbol=symbol):
                self.assertEqual(header_ids[symbol], resource_id)
                self.assertEqual(english[symbol], en_text)
                self.assertEqual(chinese[symbol], zh_text)
                if symbol.startswith("IDS_ES_MENU_"):
                    self.assertEqual(en_text.count("&"), zh_text.count("&"))

    def test_each_dynamic_ui_string_uses_its_native_resource_once(self) -> None:
        sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in PLUGIN_ROOT.glob("*.c")
        }

        for _, symbol, english, _, filename in RESOURCE_ROUTES:
            with self.subTest(symbol=symbol):
                source = sources[filename]
                self.assertEqual(
                    len(
                        re.findall(
                            rf"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*"
                            rf"{re.escape(symbol)}\s*,\s*NULL\s*\)",
                            source,
                        )
                    ),
                    1,
                )
                self.assertNotIn(f'L"{english}"', source)

    def test_menu_commands_and_columns_keep_their_exact_routes(self) -> None:
        sources = {
            path.name: compact(path.read_text(encoding="utf-8"))
            for path in PLUGIN_ROOT.glob("*.c")
        }

        for command_id, symbol in (
            (0, "IDS_ES_MENU_ENABLE"),
            (1, "IDS_ES_MENU_DISABLE"),
            (2, "IDS_ES_MENU_RESTART"),
            (3, "IDS_ES_MENU_UNINSTALL"),
            (0, "IDS_ES_MENU_OPEN_KEY"),
            (4, "IDS_ES_MENU_HARDWARE"),
            (5, "IDS_ES_MENU_SOFTWARE"),
            (6, "IDS_ES_MENU_USER"),
            (7, "IDS_ES_MENU_CONFIG"),
            (10, "IDS_ES_MENU_PROPERTIES"),
        ):
            resource_text = (
                "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString("
                f"PluginInstance->DllBase,{symbol},NULL)))"
            )
            self.assertIn(
                compact(
                    f"PhCreateEMenuItem(0,{command_id},{resource_text},NULL,NULL)"
                ),
                sources["svcpnp.c"],
            )

        for filename, target, indices, width, symbol in (
            (
                "svcpnp.c",
                "context->ListViewHandle",
                "0,0,0",
                350,
                "IDS_ES_COLUMN_PNP_DEVICES",
            ),
            ("trigger.c", "TriggersLv", "0,0,0", 300, "IDS_ES_COLUMN_TRIGGER"),
            ("trigger.c", "TriggersLv", "1,1,1", 60, "IDS_ES_COLUMN_ACTION"),
            ("trigger.c", "lvHandle", "0,0,0", 280, "IDS_ES_COLUMN_DATA"),
            (
                "other.c",
                "privilegesLv",
                "0,0,0",
                140,
                "IDS_ES_COLUMN_PRIVILEGE_NAME",
            ),
            (
                "other.c",
                "privilegesLv",
                "1,1,1",
                220,
                "IDS_ES_COLUMN_PRIVILEGE_DISPLAY_NAME",
            ),
        ):
            resource_text = (
                "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString("
                f"PluginInstance->DllBase,{symbol},NULL)))"
            )
            self.assertIn(
                compact(
                    f"PhAddListViewColumn({target},{indices},LVCFMT_LEFT,"
                    f"{width},{resource_text})"
                ),
                sources[filename],
            )

    def test_message_format_and_taskdialog_lifetimes_are_preserved(self) -> None:
        trigger = compact((PLUGIN_ROOT / "trigger.c").read_text(encoding="utf-8"))
        other = compact((PLUGIN_ROOT / "other.c").read_text(encoding="utf-8"))

        self.assertIn(
            compact(
                "PhShowError2(WindowHandle,"
                "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase,"
                "IDS_ES_CUSTOM_SUBTYPE_INVALID,NULL))),L\"%s\","
                "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase,"
                "IDS_ES_INVALID_GUID_HINT,NULL))));"
            ),
            trigger,
        )
        self.assertIn(
            compact(
                "mainInstruction = PH_AUTO(PhLoadUiString(PluginInstance->DllBase,"
                "IDS_ES_SERVICE_PROTECTION_WARNING,NULL));"
                "content = PH_AUTO(PhLoadUiString(PluginInstance->DllBase,"
                "IDS_ES_CONTINUE_PROMPT,NULL));"
            ),
            other,
        )
        self.assertIn(
            compact(
                "config.pszMainInstruction = PhGetStringOrEmpty(mainInstruction);"
                "config.pszContent = PhGetStringOrEmpty(content);"
            ),
            other,
        )

    def test_module_has_no_remaining_target_runtime_hook_entries(self) -> None:
        audit = load_audit_module()
        entries = []

        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            audit.scan_c_file(path, entries)

        self.assertEqual(
            [
                (entry["category"], entry["file"], entry["line"], entry["english"])
                for entry in entries
                if entry["category"] in TARGET_CATEGORIES
                and entry["file"].startswith("plugins/ExtendedServices/")
            ],
            [],
        )

    def test_route_checks_reject_id_text_and_lifetime_mutations(self) -> None:
        header = RESOURCE_HEADER.read_text(encoding="utf-8")
        english = ENGLISH_RC.read_text(encoding="utf-8-sig")
        other = (PLUGIN_ROOT / "other.c").read_text(encoding="utf-8")
        svcpnp = (PLUGIN_ROOT / "svcpnp.c").read_text(encoding="utf-8")

        mutations = (
            header.replace("IDS_ES_MENU_ENABLE", "IDS_ES_MENU_ENABLE_BROKEN", 1),
            re.sub(
                r'(IDS_ES_MENU_ENABLE\s+)"Enable"',
                r'\1"Disabled"',
                english,
                count=1,
            ),
            other.replace("PhGetStringOrEmpty(mainInstruction)", 'L"Broken"', 1),
            svcpnp.replace("IDS_ES_MENU_ENABLE", "IDS_ES_MENU_DISABLE", 1),
        )

        with self.assertRaises(AssertionError):
            self.assertRegex(
                mutations[0],
                r"#define\s+IDS_ES_MENU_ENABLE\s+2070\b",
            )
        with self.assertRaises(AssertionError):
            self.assertEqual(
                parse_stringtable_text(mutations[1])["IDS_ES_MENU_ENABLE"],
                "Enable",
            )
        with self.assertRaises(AssertionError):
            self.assertIn(
                compact("config.pszMainInstruction = PhGetStringOrEmpty(mainInstruction);"),
                compact(mutations[2]),
            )
        with self.assertRaises(AssertionError):
            self.assertIn(
                compact(
                    "PhCreateEMenuItem(0,0,"
                    "PhGetStringOrEmpty(PH_AUTO(PhLoadUiString("
                    "PluginInstance->DllBase,IDS_ES_MENU_ENABLE,NULL))),"
                    "NULL,NULL)"
                ),
                compact(mutations[3]),
            )


def parse_stringtable_text(source: str) -> dict[str, str]:
    return {
        name: value.replace('""', '"')
        for name, value in re.findall(
            r'^\s*(IDS_ES_[A-Z0-9_]+)\s+"((?:""|[^"])*)"',
            source,
            re.MULTILINE,
        )
    }


if __name__ == "__main__":
    unittest.main()
