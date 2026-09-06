import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
ETWSYS_PATH = REPO_ROOT / "plugins" / "ExtendedTools" / "etwsys.c"
MAIN_PATH = REPO_ROOT / "plugins" / "ExtendedTools" / "main.c"
RESOURCE_PATH = REPO_ROOT / "plugins" / "ExtendedTools" / "resource.h"


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location(
        "audit_extended_tools_etwsys_section_resources", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_section_routes(test: unittest.TestCase, source: str) -> None:
    source = compact(source)
    expected_routes = (
        'PhInitializeStringRef(&section.Name,EtGetUiString(IDS_ET_SECTION_DISK,L"Disk"));',
        'PhInitializeStringRef(&section.Name,EtGetUiString(IDS_ET_SECTION_NETWORK,L"Network"));',
    )

    for route in expected_routes:
        test.assertEqual(source.count(compact(route)), 1)

    test.assertNotIn(compact('PhInitializeStringRef(&section.Name,L"Disk");'), source)
    test.assertNotIn(compact('PhInitializeStringRef(&section.Name,L"Network");'), source)


class ExtendedToolsEtwSysSectionResourceTests(unittest.TestCase):
    def test_disk_and_network_section_names_use_existing_module_resources(self) -> None:
        source = ETWSYS_PATH.read_text(encoding="utf-8")
        assert_section_routes(self, source)

        resources = RESOURCE_PATH.read_text(encoding="utf-8")
        self.assertRegex(resources, r"#define\s+IDS_ET_SECTION_DISK\s+61201\b")
        self.assertRegex(resources, r"#define\s+IDS_ET_SECTION_NETWORK\s+61202\b")

    def test_section_name_string_refs_borrow_plugin_lifetime_storage(self) -> None:
        main = compact(MAIN_PATH.read_text(encoding="utf-8"))
        resources = RESOURCE_PATH.read_text(encoding="utf-8")

        self.assertIn(
            compact(
                "static PPH_STRING EtUiStrings["
                "IDS_ET_CACHED_LAST - IDS_ET_CACHED_FIRST + 1];"
            ),
            main,
        )
        self.assertIn(
            compact(
                "return PhGetStringOrDefault("
                "EtUiStrings[ResourceId - IDS_ET_CACHED_FIRST], Fallback);"
            ),
            main,
        )

        numeric_defines = {
            name: int(value)
            for name, value in re.findall(
                r"^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)\b",
                resources,
                re.MULTILINE,
            )
        }
        for resource_id in ("IDS_ET_SECTION_DISK", "IDS_ET_SECTION_NETWORK"):
            self.assertLessEqual(
                numeric_defines["IDS_ET_DEDICATED_MEMORY"],
                numeric_defines[resource_id],
            )
            self.assertLessEqual(
                numeric_defines[resource_id],
                numeric_defines["IDS_ET_OPTIONS_SECTION"],
            )

    def test_directed_audit_has_no_disk_or_network_window_text(self) -> None:
        audit = load_audit_module()
        entries = []
        audit.scan_c_file(ETWSYS_PATH, entries)

        self.assertEqual(
            [
                (entry["category"], entry["english"], entry["line"])
                for entry in entries
                if entry["category"] == "c_window_text"
                and entry["english"] in {"Disk", "Network"}
            ],
            [],
        )

    def test_route_assertions_reject_wrong_id_getter_and_raw_literal(self) -> None:
        source = ETWSYS_PATH.read_text(encoding="utf-8")
        mutations = (
            source.replace(
                "IDS_ET_SECTION_DISK, L\"Disk\"",
                "IDS_ET_SECTION_NETWORK, L\"Disk\"",
                1,
            ),
            source.replace(
                "EtGetUiString(IDS_ET_SECTION_DISK",
                "WrongGetUiString(IDS_ET_SECTION_DISK",
                1,
            ),
            source.replace(
                "EtGetUiString(IDS_ET_SECTION_DISK, L\"Disk\")",
                "L\"Disk\"",
                1,
            ),
        )

        for mutated_source in mutations:
            with self.subTest():
                with self.assertRaises(AssertionError):
                    assert_section_routes(self, mutated_source)


if __name__ == "__main__":
    unittest.main()
