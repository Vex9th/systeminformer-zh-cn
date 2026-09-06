import importlib.util
import pathlib
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("audit_identity_display_routes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_source(audit, root, relative_path, source):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    entries = []
    previous_root = audit.REPO_ROOT
    audit.REPO_ROOT = str(root)
    try:
        audit.scan_c_file(str(path), entries)
        audit.scan_page_names(str(path), entries)
    finally:
        audit.REPO_ROOT = previous_root
    return entries


class AuditIdentityDisplayRouteTests(unittest.TestCase):
    def setUp(self):
        self.audit = load_audit_module()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_tab_identity_is_excluded_only_with_resource_backed_v2_display(self):
        source = r'''
            static CONST PH_STRINGREF FwTreePageText = PH_STRINGREF_INIT(L"Firewall");
            static PH_STRINGREF FwTreePageDisplayText;
            static CONST PH_STRINGREF OrdinaryPageText = PH_STRINGREF_INIT(L"Ordinary");

            void initialize(void)
            {
                PH_MAIN_TAB_PAGE page;
                PhInitializeStringRefLongHint(
                    &FwTreePageDisplayText,
                    EtGetUiString(IDS_ET_TAB_FIREWALL, L"Firewall")
                    );
                page.Name = FwTreePageText;
                PhPluginCreateTabPage2(&page, &FwTreePageDisplayText);

                page.Name = OrdinaryPageText;
                PhPluginCreateTabPage(&page);
            }
        '''
        entries = scan_source(
            self.audit, self.root, pathlib.Path("plugins/ExtendedTools/fwtab.c"), source
        )
        self.assertEqual(
            [(entry["category"], entry["english"]) for entry in entries],
            [("c_tab", "Ordinary")],
        )

        for mutated in (
            source.replace(
                "PhPluginCreateTabPage2(&page, &FwTreePageDisplayText)",
                "PhPluginCreateTabPage(&page)",
                1,
            ),
            source.replace(
                "EtGetUiString(IDS_ET_TAB_FIREWALL, L\"Firewall\")",
                "L\"Firewall\"",
                1,
            ),
        ):
            entries = scan_source(
                self.audit,
                self.root,
                pathlib.Path("plugins/ExtendedTools/fwtab.c"),
                mutated,
            )
            self.assertIn(
                ("c_tab", "Firewall"),
                [(entry["category"], entry["english"]) for entry in entries],
            )

    def test_sysinfo_identity_requires_exact_whitelisted_callback_display_route(self):
        source = r'''
            void initialize(PPH_PLUGIN_SYSINFO_POINTERS Pointers)
            {
                PH_SYSINFO_SECTION section;
                PhInitializeStringRef(&section.Name, L"Disk");
                section.Callback = EtpDiskSysInfoSectionCallback;
                DiskSection = Pointers->CreateSection(&section);
            }

            BOOLEAN EtpDiskSysInfoSectionCallback(
                PPH_SYSINFO_SECTION Section,
                PH_SYSINFO_SECTION_MESSAGE Message,
                PVOID Parameter1,
                PVOID Parameter2
                )
            {
                PPH_SYSINFO_DRAW_PANEL drawPanel = Parameter1;
                drawPanel->Title = PhCreateString(
                    EtGetUiString(IDS_ET_SECTION_DISK, L"Disk")
                    );
                return TRUE;
            }

            void ordinary(void)
            {
                PH_SYSINFO_SECTION section;
                PhInitializeStringRef(&section.Name, L"Ordinary section");
                section.Callback = OrdinaryCallback;
                OtherSection = Pointers->CreateSection(&section);
            }
        '''
        relative_path = pathlib.Path("plugins/ExtendedTools/etwsys.c")
        entries = scan_source(self.audit, self.root, relative_path, source)
        visible = [
            (entry["category"], entry["english"])
            for entry in entries
            if entry["category"] == "c_window_text"
        ]
        self.assertEqual(visible, [("c_window_text", "Ordinary section")])

        for mutated in (
            source.replace(
                "IDS_ET_SECTION_DISK, L\"Disk\"",
                "IDS_ET_SECTION_NETWORK, L\"Disk\"",
                1,
            ),
            source.replace(
                "section.Callback = EtpDiskSysInfoSectionCallback;",
                "section.Callback = WrongCallback;",
                1,
            ),
            source.replace(
                "Pointers->CreateSection(&section)",
                "LegacyCreateSection(&section)",
                1,
            ),
        ):
            entries = scan_source(self.audit, self.root, relative_path, mutated)
            self.assertIn(
                ("c_window_text", "Disk"),
                [
                    (entry["category"], entry["english"])
                    for entry in entries
                    if entry["category"] == "c_window_text"
                ],
            )

    def test_mini_identity_is_excluded_only_when_v2_display_is_resource_backed(self):
        source = r'''
            void initialize(PPH_PLUGIN_MINIINFO_POINTERS Pointers)
            {
                PH_MINIINFO_LIST_SECTION section;
                Pointers->CreateListSection2(
                    L"GPU",
                    EtGetUiString(IDS_ET_GROUP_GPU, L"GPU"),
                    0,
                    &section
                    );
                Pointers->CreateListSection(L"Legacy mini", 0, &section);
            }
        '''
        relative_path = pathlib.Path("plugins/ExtendedTools/gpumini.c")
        entries = scan_source(self.audit, self.root, relative_path, source)
        self.assertEqual(
            [
                (entry["category"], entry["english"])
                for entry in entries
                if entry["category"] == "c_window_text"
            ],
            [("c_window_text", "Legacy mini")],
        )

        for mutated in (
            source.replace(
                "CreateListSection2(\n                    L\"GPU\",\n"
                "                    EtGetUiString(IDS_ET_GROUP_GPU, L\"GPU\"),",
                "CreateListSection(\n                    L\"GPU\",",
                1,
            ),
            source.replace(
                "EtGetUiString(IDS_ET_GROUP_GPU, L\"GPU\")",
                "L\"GPU display\"",
                1,
            ),
        ):
            entries = scan_source(self.audit, self.root, relative_path, mutated)
            visible = [
                (entry["category"], entry["english"])
                for entry in entries
                if entry["category"] == "c_window_text"
            ]
            self.assertTrue(
                ("c_window_text", "GPU") in visible
                or ("c_window_text", "GPU display") in visible
            )


if __name__ == "__main__":
    unittest.main()
