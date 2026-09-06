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

APP_RESOURCES = (
    ("IDS_PH_OPTIONS_GENERAL", 2704, "General", "常规"),
    ("IDS_PH_OPTIONS_ADVANCED", 2705, "Advanced", "高级"),
    ("IDS_PH_OPTIONS_HIGHLIGHTING", 2706, "Highlighting", "高亮"),
    ("IDS_PH_OPTIONS_TRAY_ICON", 2707, "Tray Icon", "托盘图标"),
    ("IDS_PH_OPTIONS_GRAPHS", 2708, "Graphs", "图表"),
    ("IDS_PH_OPTIONS_PLUGINS", 2709, "Plugins", "插件"),
)

PLUGIN_RESOURCES = {
    "UserNotes": (
        ("IDS_UN_OPTIONS_SECTION", 2019, "UserNotes", "用户备注"),
    ),
    "ExtendedTools": (
        ("IDS_ET_OPTIONS_SECTION", 61230, "ExtendedTools", "扩展工具"),
    ),
    "ExtendedNotifications": (
        ("IDS_EN_OPTIONS_PROCESSES", 12000, "Notifications - Processes", "通知 - 进程"),
        ("IDS_EN_OPTIONS_SERVICES", 12001, "Notifications - Services", "通知 - 服务"),
        ("IDS_EN_OPTIONS_DEVICES", 12002, "Notifications - Devices", "通知 - 设备"),
        ("IDS_EN_OPTIONS_LOGGING", 12003, "Notifications - Logging", "通知 - 日志"),
    ),
    "HardwareDevices": (
        ("IDS_HD_OPTIONS_DISK_DEVICES", 12098, "Disk Devices", "磁盘设备"),
        ("IDS_HD_OPTIONS_GRAPHICS_DEVICES", 12099, "Graphics Devices", "图形设备"),
        ("IDS_HD_OPTIONS_NETWORK_DEVICES", 12100, "Network Devices", "网络设备"),
        ("IDS_HD_OPTIONS_RAPL_DEVICES", 12101, "RAPL Devices", "RAPL 设备"),
    ),
    "OnlineChecks": (
        ("IDS_OC_OPTIONS_SECTION", 12005, "OnlineChecks", "在线检查"),
    ),
    "NetworkTools": (
        ("IDS_NT_OPTIONS_SECTION", 12022, "NetworkTools", "网络工具"),
    ),
    "ToolStatus": (
        ("IDS_TS_OPTIONS_SECTION", 12103, "ToolStatus", "工具栏和状态栏"),
    ),
    "Updater": (
        ("IDS_UP_OPTIONS_SECTION", 12009, "Updater", "更新检查"),
    ),
}

BUILTIN_CALLS = {
    "General": "IDS_PH_OPTIONS_GENERAL",
    "Advanced": "IDS_PH_OPTIONS_ADVANCED",
    "Highlighting": "IDS_PH_OPTIONS_HIGHLIGHTING",
    "Tray Icon": "IDS_PH_OPTIONS_TRAY_ICON",
    "Graphs": "IDS_PH_OPTIONS_GRAPHS",
    "Plugins": "IDS_PH_OPTIONS_PLUGINS",
}

PLUGIN_CALLS = {
    "UserNotes": {"UserNotes": "IDS_UN_OPTIONS_SECTION"},
    "ExtendedTools": {"ExtendedTools": "IDS_ET_OPTIONS_SECTION"},
    "ExtendedNotifications": {
        "Notifications - Processes": "IDS_EN_OPTIONS_PROCESSES",
        "Notifications - Services": "IDS_EN_OPTIONS_SERVICES",
        "Notifications - Devices": "IDS_EN_OPTIONS_DEVICES",
        "Notifications - Logging": "IDS_EN_OPTIONS_LOGGING",
    },
    "HardwareDevices": {
        "Disk Devices": "IDS_HD_OPTIONS_DISK_DEVICES",
        "Graphics Devices": "IDS_HD_OPTIONS_GRAPHICS_DEVICES",
        "Network Devices": "IDS_HD_OPTIONS_NETWORK_DEVICES",
        "RAPL Devices": "IDS_HD_OPTIONS_RAPL_DEVICES",
    },
    "OnlineChecks": {"OnlineChecks": "IDS_OC_OPTIONS_SECTION"},
    "NetworkTools": {"NetworkTools": "IDS_NT_OPTIONS_SECTION"},
    "ToolStatus": {"ToolStatus": "IDS_TS_OPTIONS_SECTION"},
    "Updater": {"Updater": "IDS_UP_OPTIONS_SECTION"},
}

EXPECTED_COUNTS = {
    "sys_info.exe": 710,
    "ExtendedNotifications.dll": 4,
    "ExtendedTools.dll": 231,
    "HardwareDevices.dll": 102,
    "NetworkTools.dll": 27,
    "OnlineChecks.dll": 18,
    "ToolStatus.dll": 104,
    "Updater.dll": 18,
    "UserNotes.dll": 20,
}

EXPECTED_NEXT_SYMED_VALUES = {
    "SystemInformer": 2710,
    "UserNotes": 2020,
    "ExtendedTools": 61231,
    "ExtendedNotifications": 12004,
    "HardwareDevices": 12102,
    "OnlineChecks": 12018,
    "NetworkTools": 12027,
    "ToolStatus": 12104,
    "Updater": 12018,
}


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*([A-Z][A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_options_sections", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
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


class OptionsSectionNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.options = (APP_ROOT / "options.c").read_text(encoding="utf-8-sig")
        cls.phplug = (APP_ROOT / "include" / "phplug.h").read_text(encoding="utf-8-sig")
        cls.gpuoptions = (
            REPO_ROOT / "plugins" / "HardwareDevices" / "gpuoptions.c"
        ).read_text(encoding="utf-8-sig")
        cls.translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        cls.runtime = (REPO_ROOT / "phlib" / "phtranslation_zhcn.c").read_text(
            encoding="utf-8-sig"
        )
        cls.audit = load_audit_module()

    def test_create_section2_preserves_legacy_abi_and_owns_both_names(self) -> None:
        self.assertRegex(
            self.phplug,
            re.compile(
                r"typedef _Function_class_\(PH_OPTIONS_CREATE_SECTION2\).*?"
                r"PH_OPTIONS_CREATE_SECTION2\s*\(\s*"
                r"_In_ PCWSTR Name,\s*_In_ PVOID Instance,\s*"
                r"_In_ ULONG NameResourceId,.*?"
                r"typedef PH_OPTIONS_CREATE_SECTION2 \*PPH_OPTIONS_CREATE_SECTION2;",
                re.DOTALL,
            ),
        )
        pointers = re.search(
            r"typedef struct _PH_PLUGIN_OPTIONS_POINTERS\s*\{(?P<body>.*?)\}",
            self.phplug,
            re.DOTALL,
        ).group("body")
        self.assertRegex(
            pointers,
            re.compile(
                r"HWND WindowHandle;\s*PPH_OPTIONS_CREATE_SECTION CreateSection;\s*"
                r"PPH_OPTIONS_FIND_SECTION FindSection;\s*"
                r"PPH_OPTIONS_ENTER_SECTION_VIEW EnterSectionView;\s*"
                r"PPH_OPTIONS_CREATE_SECTION2 CreateSection2;\s*$",
                re.DOTALL,
            ),
        )
        self.assertIn("PPH_STRING NameString;", self.phplug)
        self.assertIn("PPH_STRING DisplayName;", self.phplug)

        internal = function_body(self.options, "PhpOptionsCreateSection")
        self.assertEqual(internal.count("section->NameString = PhCreateString(Name);"), 1)
        self.assertEqual(internal.count("section->Name = section->NameString->sr;"), 1)
        self.assertEqual(internal.count("section->DisplayName = PhLoadUiString(Instance, NameResourceId, NULL);"), 1)
        self.assertRegex(
            internal,
            re.compile(
                r"if\s*\(!section->DisplayName\)\s*"
                r"section->DisplayName = PhReferenceObject\(section->NameString\);"
            ),
        )
        self.assertEqual(internal.count("PhGetString(section->DisplayName)"), 1)

        legacy = function_body(self.options, "PhOptionsCreateSection")
        self.assertEqual(legacy.count("PhpOptionsCreateSection(Name, Instance, 0,"), 1)
        destroy = function_body(self.options, "PhOptionsDestroySection")
        self.assertEqual(destroy.count("PhDereferenceObject(Section->NameString);"), 1)
        self.assertEqual(destroy.count("PhDereferenceObject(Section->DisplayName);"), 1)

    def test_tree_display_uses_owned_resource_text_and_advanced_reinsert(self) -> None:
        tree_insert = function_body(self.options, "PhpTreeViewInsertItem")
        self.assertNotIn("PhTranslateString", tree_insert)
        self.assertIn("insert.item.pszText = (PWSTR)Text;", tree_insert)
        show_hide = function_body(self.options, "PhpOptionsShowHideTreeViewItem")
        self.assertIn("PhGetString(advancedSection->DisplayName)", show_hide)
        self.assertNotIn("advancedName.Buffer", show_hide)
        self.assertNotIn("#include <phtranslation.h>", self.options)
        self.assertNotIn("PhTranslateString", self.options)
        self.assertIn(
            "HardwareDevicesGetUiString(IDS_HD_OPTIONS_GRAPHICS_DEVICES)",
            self.gpuoptions,
        )
        self.assertNotIn(
            'PhAddListViewColumn(context->ListViewHandle, 0, 0, 0, LVCFMT_LEFT, 350, L"Graphics Devices")',
            self.gpuoptions,
        )

    def test_all_six_builtin_and_fourteen_plugin_sections_use_resources(self) -> None:
        builtin_routes = re.findall(
            r'PhOptionsCreateSection(?:Advanced|2)\(\s*L"([^"]+)"\s*,\s*'
            r'PhInstanceHandle\s*,\s*(IDS_PH_OPTIONS_[A-Z_]+)\s*,',
            self.options,
        )
        self.assertCountEqual(list(BUILTIN_CALLS.items()), builtin_routes)
        for identity, resource in BUILTIN_CALLS.items():
            with self.subTest(identity=identity):
                pattern = (
                    rf'PhOptionsCreateSection(?:Advanced|2)\(\s*L"{re.escape(identity)}"\s*,\s*'
                    rf'PhInstanceHandle\s*,\s*{resource}\s*,'
                )
                self.assertRegex(self.options, pattern)

        self.assertEqual(self.options.count("pointers.CreateSection2 = PhOptionsCreateSection2;"), 1)
        for plugin, calls in PLUGIN_CALLS.items():
            source = (REPO_ROOT / "plugins" / plugin / "main.c").read_text(encoding="utf-8-sig")
            self.assertNotIn("optionsEntry->CreateSection(", source)
            self.assertEqual(source.count("optionsEntry->CreateSection2("), len(calls))
            expected_instance = "NtCurrentImageBase()" if plugin in {"ExtendedNotifications", "Updater"} else "PluginInstance->DllBase"
            plugin_routes = re.findall(
                r'optionsEntry->CreateSection2\(\s*L"([^"]+)"\s*,\s*'
                + re.escape(expected_instance)
                + r'\s*,\s*([A-Z][A-Z0-9_]+)\s*,',
                source,
            )
            self.assertCountEqual(list(calls.items()), plugin_routes)
            for identity, resource in calls.items():
                with self.subTest(plugin=plugin, identity=identity):
                    self.assertRegex(
                        source,
                        rf'optionsEntry->CreateSection2\(\s*L"{re.escape(identity)}"\s*,\s*'
                        rf'{re.escape(expected_instance)}\s*,\s*{resource}\s*,',
                    )

    def test_resource_backed_identity_literals_are_not_reported_as_tree_labels(self) -> None:
        entries = []
        self.audit.scan_extra_statics(str(APP_ROOT / "options.c"), entries)
        self.assertEqual(
            [],
            [entry for entry in entries if entry["category"] == "c_tree_item"],
        )

    def test_all_twenty_resources_have_exact_native_ownership(self) -> None:
        resources_by_module = {"SystemInformer": APP_RESOURCES, **PLUGIN_RESOURCES}
        for module, resources in resources_by_module.items():
            root = APP_ROOT if module == "SystemInformer" else REPO_ROOT / "plugins" / module
            prefix = "SystemInformer" if module == "SystemInformer" else module
            header = (root / "resource.h").read_text(encoding="utf-8-sig")
            english = parse_stringtable(root / f"{prefix}.rc")
            chinese = parse_stringtable(root / f"{prefix}.zh-cn.rc")
            for symbol, numeric_id, en, zh in resources:
                with self.subTest(module=module, symbol=symbol):
                    self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{numeric_id}$")
                    self.assertEqual(english.get(symbol), en)
                    self.assertEqual(chinese.get(symbol), zh)
                    self.assertEqual(self.translations["native_strings"].get(en), zh)
                    self.assertNotIn(en, self.translations["strings"])
                    self.assertNotRegex(self.runtime, rf'\{{ L"{re.escape(en)}", L"')

            numeric_ids = [numeric_id for _symbol, numeric_id, _en, _zh in resources]
            self.assertEqual(len(numeric_ids), len(set(numeric_ids)))
            self.assertRegex(
                header,
                rf"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+{EXPECTED_NEXT_SYMED_VALUES[module]}$",
            )

        self.assertFalse(
            self.translations["strings"].keys() & self.translations["native_strings"].keys()
        )
        app_header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        self.assertRegex(app_header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_OPTIONS_PLUGINS$")
        self.assertRegex(app_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2710$")

    def test_exact_ci_and_generator_counts(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        for binary, count in EXPECTED_COUNTS.items():
            with self.subTest(binary=binary):
                self.assertEqual(workflow.count(f"{binary}={count}"), 2)

        native = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "zhcn" / "generate_native_resources.py"), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(native.returncode, 0, native.stdout + native.stderr)
        self.assertIn("1900 strings", native.stdout)

        runtime = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "zhcn" / "generate_translation.py"), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(runtime.returncode, 0, runtime.stdout + runtime.stderr)
        self.assertIn("2335 entries", runtime.stdout)


if __name__ == "__main__":
    unittest.main()
