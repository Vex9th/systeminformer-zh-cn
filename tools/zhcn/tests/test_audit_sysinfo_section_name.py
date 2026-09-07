import importlib.util
import pathlib
import unittest
from unittest import mock

try:
    from tools.zhcn.tests.temp_source import scan_temporary_source
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    from temp_source import scan_temporary_source


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("audit_sysinfo_section_name", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuditSysInfoSectionNameTests(unittest.TestCase):
    def test_scanner_accepts_a_source_on_another_windows_drive(self) -> None:
        audit = load_audit_module()
        with mock.patch.object(
            audit.os.path,
            "relpath",
            side_effect=ValueError("path is on mount 'C:', start on mount 'D:'"),
        ):
            entries = scan_temporary_source(
                audit.scan_c_file,
                'void sample(void) { PhSetWindowText(hwnd, L"Title"); }',
            )

        self.assertEqual(entries[0]["english"], "Title")

    def test_initialize_string_ref_section_name_is_a_visible_ui_sink(self) -> None:
        audit = load_audit_module()
        source = """
            void sample(void) {
                PH_SYSINFO_SECTION first, section;
                PhInitializeStringRef(&section.Name, L"Disk");
                {
                    OTHER other, section;
                    PhInitializeStringRef(&section.Name, L"Comma shadowed field");
                }
                {
                    use(first, section, third);
                    PhInitializeStringRef(&section.Name, L"Visible after function call");
                }
                {
                    {
                        OTHER section;
                        use(section);
                    }
                    PhInitializeStringRef(
                        &section.Name,
                        L"Visible after ended shadow"
                        );
                }
                PH_SYSINFO_SECTION unused, second;
                PhInitializeStringRef(
                    &second.Name,
                    L"Second section"
                    );
                PCWSTR sharedTitle = L"Shared title";
                PH_SYSINFO_SECTION sharedSection;
                PhInitializeStringRef(&sharedSection.Name, sharedTitle);
                PhSetWindowText(hwnd, sharedTitle);
            }
            void unrelated(void) {
                OTHER section;
                PhInitializeStringRef(&section.Name, L"Unrelated field");
            }
        """
        entries = scan_temporary_source(audit.scan_c_file, source)

        visible_entries = [
            entry for entry in entries if entry["category"] == "c_window_text"
        ]
        source_lines = source.splitlines()
        expected_lines = {
            english: next(
                line_number
                for line_number, line in enumerate(source_lines, start=1)
                if f'L"{english}"' in line
            )
            for english in (
                "Disk",
                "Visible after function call",
                "Visible after ended shadow",
                "Second section",
                "Shared title",
            )
        }

        self.assertEqual(
            [(entry["english"], entry["line"]) for entry in visible_entries],
            [
                ("Disk", expected_lines["Disk"]),
                (
                    "Visible after function call",
                    expected_lines["Visible after function call"],
                ),
                (
                    "Visible after ended shadow",
                    expected_lines["Visible after ended shadow"],
                ),
                ("Second section", expected_lines["Second section"]),
                ("Shared title", expected_lines["Shared title"]),
            ],
        )
        self.assertEqual(
            sum(entry["english"] == "Shared title" for entry in visible_entries),
            1,
        )


if __name__ == "__main__":
    unittest.main()
