#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


class RemainingDirectWindowAndTabResourceTests(unittest.TestCase):
    def test_hardware_devices_tab_reuses_the_native_devices_resource(self):
        source = (REPO_ROOT / "plugins" / "HardwareDevices" / "devicetree.c").read_text(encoding="utf-8-sig")
        self.assertIn(
            'static CONST PH_STRINGREF DevicePageText = PH_STRINGREF_INIT(L"Devices");',
            source,
        )
        self.assertIn('static PH_STRINGREF DevicePageDisplayText;', source)
        self.assertIn(
            'HardwareDevicesPageGetUiString(IDS_HD_MENU_DEVICES, L"Devices")',
            source,
        )
        self.assertIn('page.Name = DevicePageText;', source)
        self.assertIn(
            'DevicesAddedTabPage = PhPluginCreateTabPage2(&page, &DevicePageDisplayText);',
            source,
        )
        self.assertNotIn('HardwareDevicesGetUiStringObject(IDS_HD_MENU_DEVICES)->sr', source)

    def test_gpu_and_npu_sections_reuse_stable_native_resources(self):
        gpu = (REPO_ROOT / "plugins" / "ExtendedTools" / "gpusys.c").read_text(encoding="utf-8-sig")
        npu = (REPO_ROOT / "plugins" / "ExtendedTools" / "npusys.c").read_text(encoding="utf-8-sig")
        self.assertIn('PhInitializeStringRef(&section.Name, EtGetUiString(IDS_ET_GROUP_GPU, L"GPU"));', gpu)
        self.assertIn('PhInitializeStringRef(&section.Name, EtGetUiString(IDS_ET_GROUP_NPU, L"NPU"));', npu)
        self.assertNotIn('PH_STRINGREF_INIT(L"GPU")', gpu)
        self.assertNotIn('PhInitializeStringRef(&section.Name, L"NPU")', npu)

    def test_online_partner_link_uses_its_own_native_resource(self):
        root = REPO_ROOT / "plugins" / "OnlineChecks"
        source = (root / "partner.c").read_text(encoding="utf-8-sig")
        header = (root / "resource.h").read_text(encoding="utf-8-sig")
        english = (root / "OnlineChecks.rc").read_text(encoding="utf-8-sig")
        chinese = (root / "OnlineChecks.zh-cn.rc").read_text(encoding="utf-8-sig")
        text = '<a href=""https://www.hybrid-analysis.com/"">hybrid-analysis.com</a>'

        self.assertRegex(header, r"(?m)^#define\s+IDS_OC_PARTNER_LINK\s+12024$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12025$")
        self.assertRegex(english, rf'(?m)^\s*IDS_OC_PARTNER_LINK\s+"{re.escape(text)}"$')
        self.assertRegex(chinese, rf'(?m)^\s*IDS_OC_PARTNER_LINK\s+"{re.escape(text)}"$')
        self.assertIn(
            "PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_PARTNER_LINK, NULL))",
            source,
        )
        self.assertIn('static CONST PH_STRINGREF PartnerLinkFallback = PH_STRINGREF_INIT(', source)
        self.assertIn('PhGetStringOrDefault(', source)
        self.assertIn('PartnerLinkFallback.Buffer', source)
        self.assertNotRegex(
            source,
            r'PhSetDialogItemText\(\s*WindowHandle,\s*IDC_PARTNER_LINK,\s*L"<a href=',
        )


if __name__ == "__main__":
    unittest.main()
