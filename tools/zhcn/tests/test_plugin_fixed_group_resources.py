#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

PLUGIN_SPECS = {
    "HardwareDevices": {
        "source": "deviceprops.c",
        "resources": (
            ("IDS_HD_GROUP_GENERAL", 12096, "General", "常规", "DEVICE_PROPERTIES_CATEGORY_GENERAL"),
            ("IDS_HD_GROUP_CLASS", 12097, "Class", "类", "DEVICE_PROPERTIES_CATEGORY_CLASS"),
        ),
        "count": 396,
        "aps": 12396,
    },
    "WindowExplorer": {
        "source": "wndprp.c",
        "resources": (
            ("IDS_WE_GROUP_GENERAL", 12093, "General", "常规", "WINDOW_PROPERTIES_CATEGORY_GENERAL"),
            ("IDS_WE_GROUP_CLASS", 12094, "Class", "类", "WINDOW_PROPERTIES_CATEGORY_CLASS"),
            ("IDS_WE_GROUP_STATE", 12095, "State", "状态", "WND_UIA_GROUP_STATE"),
        ),
        "count": 169,
        "aps": 12169,
    },
}


def load_audit():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_fixed_groups", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def parse_defines(path: pathlib.Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8-sig")
    return {
        name: int(value)
        for name, value in re.findall(
            r"(?m)^#define\s+(IDS_(?:HD|WE)_[A-Z0-9_]+)\s+(\d+)$",
            text,
        )
    }


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return dict(re.findall(
        r'^\s*(IDS_(?:HD|WE)_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"$',
        path.read_text(encoding="utf-8-sig"),
        re.MULTILINE,
    ))


class PluginFixedGroupResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit()

    def test_hardware_devices_resources_cache_and_routes_are_exact(self) -> None:
        spec = PLUGIN_SPECS["HardwareDevices"]
        root = REPO_ROOT / "plugins" / "HardwareDevices"
        source = self.audit.mask_c_comments(
            (root / spec["source"]).read_text(encoding="utf-8-sig")
        )
        main_source = self.audit.mask_c_comments(
            (root / "main.c").read_text(encoding="utf-8-sig")
        )

        expected_routes = []
        actual_routes = []
        expected_ids = {row[0] for row in spec["resources"]}
        for _name, args, _spans, _call_start in self.audit.find_calls(
            source, {"PhAddListViewGroup"}
        ):
            if len(args) != 3:
                continue
            getter = re.fullmatch(
                r"\s*HardwareDevicesGetUiString\(\s*(IDS_HD_[A-Z0-9_]+)\s*\)\s*",
                args[2],
                re.DOTALL,
            )
            literal = re.fullmatch(r'\s*L"(General|Class)"\s*', args[2])
            if not getter and not literal:
                continue
            actual_routes.append((normalize(args[1]), getter.group(1) if getter else None))

        for resource_id, _numeric_id, _english, _chinese, group_id in spec["resources"]:
            expected_routes.append((group_id, resource_id))

        self.assertEqual(actual_routes, expected_routes)
        self.assertEqual(
            len(re.findall(r"HardwareDevicesGetUiString\(\s*(IDS_HD_GROUP_[A-Z0-9_]+)\s*\)", source)),
            len(expected_ids),
        )
        self.assertRegex(
            main_source,
            r"static PPH_STRING HardwareDevicesUiStrings\[\s*"
            r"IDS_HD_LAST\s*-\s*IDS_HD_FIRST\s*\+\s*1\s*\]",
        )
        self.assertRegex(main_source, r"ResourceId\s*<\s*IDS_HD_FIRST")
        self.assertRegex(main_source, r"ResourceId\s*>\s*IDS_HD_LAST")
        self.assertRegex(main_source, r"id\s*=\s*IDS_HD_FIRST\s*;\s*id\s*<=\s*IDS_HD_LAST")
        self.assertEqual(main_source.count("id - IDS_HD_FIRST"), 1)
        self.assertEqual(main_source.count("ResourceId - IDS_HD_FIRST"), 1)

    def test_window_explorer_routes_use_the_plugin_resource_module(self) -> None:
        spec = PLUGIN_SPECS["WindowExplorer"]
        root = REPO_ROOT / "plugins" / "WindowExplorer"
        source = self.audit.mask_c_comments(
            (root / spec["source"]).read_text(encoding="utf-8-sig")
        )
        expected = []
        actual = []
        target_ids = {row[0] for row in spec["resources"]}

        for _name, args, _spans, _call_start in self.audit.find_calls(
            source, {"PhAddListViewGroup"}
        ):
            if len(args) != 3:
                continue
            getter = re.fullmatch(
                r"\s*PhGetString\(\s*PH_AUTO\(\s*PhLoadUiString\(\s*"
                r"PluginInstance->DllBase\s*,\s*(IDS_WE_[A-Z0-9_]+)\s*,\s*NULL\s*"
                r"\)\s*\)\s*\)\s*",
                args[2],
                re.DOTALL,
            )
            literal = re.fullmatch(r'\s*L"(General|Class|State)"\s*', args[2])
            if getter and getter.group(1) in target_ids:
                actual.append((normalize(args[1]), getter.group(1)))
            elif literal:
                actual.append((normalize(args[1]), None))

        for resource_id, _numeric_id, _english, _chinese, group_id in spec["resources"]:
            expected.append((group_id, resource_id))

        self.assertEqual(actual, expected)

    def test_resources_json_counts_and_boundaries_are_exact_per_dll(self) -> None:
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for plugin, spec in PLUGIN_SPECS.items():
            with self.subTest(plugin=plugin):
                root = REPO_ROOT / "plugins" / plugin
                header = (root / "resource.h").read_text(encoding="utf-8-sig")
                defines = parse_defines(root / "resource.h")
                english = parse_stringtable(root / f"{plugin}.rc")
                chinese = parse_stringtable(root / f"{plugin}.zh-cn.rc")

                for resource_id, numeric_id, en, zh, _group_id in spec["resources"]:
                    self.assertEqual(defines.get(resource_id), numeric_id)
                    self.assertEqual(english.get(resource_id), en)
                    self.assertEqual(chinese.get(resource_id), zh)
                    table = (
                        translations["native_strings"]
                        if en == "General"
                        else translations["strings"]
                    )
                    other = (
                        translations["strings"]
                        if en == "General"
                        else translations["native_strings"]
                    )
                    self.assertEqual(table.get(en), zh)
                    self.assertNotIn(en, other)

                self.assertEqual(len(english), spec["count"])
                self.assertEqual(len(chinese), spec["count"])
                self.assertRegex(
                    header,
                    rf"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+{spec['aps']}$",
                )

        hardware_header = (
            REPO_ROOT / "plugins" / "HardwareDevices" / "resource.h"
        ).read_text(encoding="utf-8-sig")
        self.assertRegex(hardware_header, r"(?m)^#define\s+IDS_HD_FIRST\s+IDS_HD_NO_GRAPHICS_NODES$")
        self.assertRegex(
            hardware_header,
            r"(?m)^#define\s+IDS_HD_LAST\s+IDS_HD_DEVICE_PROPERTY_GPU_PHYSICAL_ADAPTER_INDEX$",
        )

    def test_ci_counts_and_generator_total_are_synchronized(self) -> None:
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml"
        ).read_text(encoding="utf-8")
        generator_test = (
            REPO_ROOT / "tools" / "zhcn" / "tests" / "test_native_resource_generation.py"
        ).read_text(encoding="utf-8")

        self.assertEqual(workflow.count("plugins\\HardwareDevices.dll=396"), 2)
        self.assertEqual(workflow.count("plugins\\WindowExplorer.dll=169"), 2)
        self.assertNotIn("plugins\\HardwareDevices.dll=96", workflow)
        self.assertNotIn("plugins\\WindowExplorer.dll=93", workflow)
        self.assertIn('self.assertIn("3238 strings", result.stdout)', generator_test)

    def test_fixed_group_literals_leave_both_plugins_but_dynamic_group_remains(self) -> None:
        entries = []
        for plugin in ("HardwareDevices", "WindowExplorer"):
            for path in (REPO_ROOT / "plugins" / plugin).glob("*.c"):
                self.audit.scan_c_file(str(path), entries)

        fixed = [
            entry
            for entry in entries
            if entry["category"] == "c_listview_group"
            and entry["english"] in {"General", "Class", "State"}
        ]
        self.assertEqual(fixed, [])

        hardware_source = (
            REPO_ROOT / "plugins" / "HardwareDevices" / "deviceprops.c"
        ).read_text(encoding="utf-8-sig")
        self.assertRegex(
            hardware_source,
            r"PhAddListViewGroup\(\s*Context->InterfacesListViewHandle\s*,\s*"
            r"group\s*,\s*PhGetString\(PhGetDeviceProperty\(",
        )


if __name__ == "__main__":
    unittest.main()
