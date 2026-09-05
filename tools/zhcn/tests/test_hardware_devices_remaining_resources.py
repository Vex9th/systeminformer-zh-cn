#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "HardwareDevices"

RESOURCE_TEXT = {
    "IDS_HD_DESCRIPTION": (12009, "Description", "描述"),
    "IDS_HD_INSTALLED": (12010, "Installed", "安装时间"),
    "IDS_HD_FIRST_INSTALLED": (12011, "First installed", "首次安装时间"),
    "IDS_HD_LAST_ARRIVAL": (12012, "Last arrival", "最近接入时间"),
    "IDS_HD_LAST_REMOVAL": (12013, "Last removal", "最近移除时间"),
    "IDS_HD_PROBLEM_CODE": (12014, "Problem code", "问题代码"),
    "IDS_HD_PROBLEM_DESCRIPTION": (12015, "Problem description", "问题描述"),
    "IDS_HD_PROBLEM_STATUS": (12016, "Problem status", "问题状态"),
    "IDS_HD_DRIVER": (12017, "Driver", "驱动程序"),
    "IDS_HD_DRIVER_PROVIDER": (12018, "Driver provider", "驱动程序提供商"),
    "IDS_HD_DRIVER_DESCRIPTION": (12019, "Driver description", "驱动程序描述"),
    "IDS_HD_DRIVER_DATE": (12020, "Driver date", "驱动程序日期"),
    "IDS_HD_DRIVER_VERSION": (12021, "Driver version", "驱动程序版本"),
    "IDS_HD_DRIVER_INF": (12022, "Driver INF", "驱动程序 INF"),
    "IDS_HD_DRIVER_INF_SECTION": (12023, "Driver INF section", "驱动程序 INF 节"),
    "IDS_HD_SERVICE": (12024, "Service", "服务"),
    "IDS_HD_SECURITY_DESCRIPTOR": (12025, "Security descriptor", "安全描述符"),
    "IDS_HD_ENUMERATOR": (12026, "Enumerator", "枚举器"),
    "IDS_HD_PDO_NAME": (12027, "PDO name", "PDO 名称"),
    "IDS_HD_INSTANCE_ID": (12028, "Instance ID", "实例 ID"),
    "IDS_HD_PARENT_INSTANCE_ID": (12029, "Parent instance ID", "父实例 ID"),
    "IDS_HD_LOCATION_INFO": (12030, "Location info", "位置信息"),
    "IDS_HD_LOCATION_PATHS": (12031, "Location paths", "位置路径"),
    "IDS_HD_MATCHING_ID": (12032, "Matching ID", "匹配 ID"),
    "IDS_HD_HARDWARE_IDS": (12033, "Hardware IDs", "硬件 ID"),
    "IDS_HD_NAME": (12034, "Name", "名称"),
    "IDS_HD_GUID": (12035, "GUID", "GUID"),
    "IDS_HD_DEVICE_NAME": (12036, "Device name", "设备名称"),
    "IDS_HD_CLASS_NAME": (12037, "Class name", "类名"),
    "IDS_HD_INSTALLER": (12038, "Installer", "安装程序"),
    "IDS_HD_DEFAULT_SERVICE": (12039, "Default service", "默认服务"),
    "IDS_HD_PROPERTY_PAGE_PROVIDER": (12040, "Property page provider", "属性页提供程序"),
    "IDS_HD_STATE": (12041, "State", "状态"),
    "IDS_HD_IPV4_ADDRESS": (12042, "IPv4 address", "IPv4 地址"),
    "IDS_HD_IPV4_SUBNET_MASK": (12043, "IPv4 subnet mask", "IPv4 子网掩码"),
    "IDS_HD_IPV4_DEFAULT_GATEWAY": (12044, "IPv4 default gateway", "IPv4 默认网关"),
    "IDS_HD_IPV4_DNS_ADDRESS": (12045, "IPv4 DNS address", "IPv4 DNS 地址"),
    "IDS_HD_IPV6_ADDRESS": (12046, "IPv6 address", "IPv6 地址"),
    "IDS_HD_IPV6_TEMP_ADDRESS": (12047, "IPv6 address (temporary)", "IPv6 地址（临时）"),
    "IDS_HD_IPV6_DEFAULT_GATEWAY": (12048, "IPv6 default gateway", "IPv6 默认网关"),
    "IDS_HD_IPV6_DNS_ADDRESS": (12049, "IPv6 DNS address", "IPv6 DNS 地址"),
    "IDS_HD_DOMAIN": (12050, "Domain", "域"),
    "IDS_HD_LINK_SPEED": (12051, "Link speed", "链路速度"),
    "IDS_HD_SENT": (12052, "Sent", "已发送"),
    "IDS_HD_RECEIVED": (12053, "Received", "已接收"),
    "IDS_HD_TOTAL": (12054, "Total", "总计"),
    "IDS_HD_SENDING": (12055, "Sending", "发送速率"),
    "IDS_HD_RECEIVING": (12056, "Receiving", "接收速率"),
    "IDS_HD_UTILIZATION": (12057, "Utilization", "利用率"),
    "IDS_HD_SENT_PACKETS": (12058, "Sent packets", "已发送数据包"),
    "IDS_HD_RECEIVED_PACKETS": (12059, "Received packets", "已接收数据包"),
    "IDS_HD_TOTAL_PACKETS": (12060, "Total packets", "数据包总数"),
    "IDS_HD_SEND_ERRORS": (12061, "Send errors", "发送错误数"),
    "IDS_HD_RECEIVE_ERRORS": (12062, "Receive errors", "接收错误数"),
    "IDS_HD_TOTAL_ERRORS": (12063, "Total errors", "错误总数"),
    "IDS_HD_SEND_DISCARDS": (12064, "Send discards", "发送丢弃数"),
    "IDS_HD_RECEIVE_DISCARDS": (12065, "Receive discards", "接收丢弃数"),
    "IDS_HD_TOTAL_DISCARDS": (12066, "Total discards", "丢弃总数"),
    "IDS_HD_PERCENT_FORMAT": (12067, "%.0f%%", "%.0f%%"),
    "IDS_HD_MILLISECONDS_FORMAT": (12068, "%.1f ms", "%.1f 毫秒"),
    "IDS_HD_RATE_FORMAT": (12069, "%s/s", "%s/秒"),
    "IDS_HD_QUEUE_DEPTH_FORMAT": (12070, "%lu | %lu", "%lu | %lu"),
    "IDS_HD_VOLUME_FORMAT": (12071, "Volume %wc:", "卷 %wc:"),
    "IDS_HD_VOLUME_LABEL_FORMAT": (12072, "Volume %wc: [%s]", "卷 %wc: [%s]"),
    "IDS_HD_CLOSE": (12073, "Close", "关闭"),
    "IDS_HD_NOT_AVAILABLE": (12074, "N/A", "不适用"),
    "IDS_HD_PENDING": (12075, "Pending...", "正在查询..."),
    "IDS_HD_UNKNOWN": (12076, "Unknown", "未知"),
    "IDS_HD_UNNAMED_DEVICE": (12077, "Unnamed Device", "未命名设备"),
    "IDS_HD_MILLISECONDS_SUFFIX": (12078, " ms", " 毫秒"),
    "IDS_HD_RATE_SUFFIX": (12079, "/s", "/秒"),
    "IDS_HD_QUEUE_SEPARATOR": (12080, " | ", " | "),
    "IDS_HD_RATE_WITH_BITRATE_FORMAT": (12081, "%s/s (%s)", "%s/秒（%s）"),
    "IDS_HD_PRECISE_PERCENT_FORMAT": (12082, "%.2f%%", "%.2f%%"),
    "IDS_HD_SECONDS_FORMAT": (12083, "%.2f seconds", "%.2f 秒"),
    "IDS_HD_UINT64_RANGE_FORMAT": (12084, "%I64u - %I64u", "%I64u - %I64u"),
    "IDS_HD_MEGAHERTZ_FORMAT": (12085, "%I64u MHz", "%I64u MHz"),
    "IDS_HD_INTEGER_PERCENT_FORMAT": (12086, "%lu%%", "%lu%%"),
    "IDS_HD_VERSION_FORMAT": (12087, "%lu.%lu", "%lu.%lu"),
    "IDS_HD_CELSIUS_FORMAT": (12088, "%lu\\u00b0C", "%lu\\u00b0C"),
    "IDS_HD_SIZE_PERCENT_FORMAT": (12089, "%s (%.2f%%)", "%s（%.2f%%）"),
    "IDS_HD_HEX_FORMAT": (12090, "0x%s", "0x%s"),
    "IDS_HD_WDDM_VERSION_FORMAT": (12091, "WDDM %lu.%lu", "WDDM %lu.%lu"),
    "IDS_HD_FILE_SYSTEM_NTFS": (12092, "NTFS", "NTFS"),
    "IDS_HD_FILE_SYSTEM_FAT": (12093, "FAT", "FAT"),
    "IDS_HD_FILE_SYSTEM_REFS": (12094, "ReFS", "ReFS"),
    "IDS_HD_RAPL": (12095, "RAPL", "RAPL"),
}

RUNTIME_DICTIONARY_OWNED = {
    "Description",
    "Driver",
    "Link speed",
    "Name",
    "Service",
    "State",
    "Total",
    "Volume %wc:",
    "Volume %wc: [%s]",
    "Close",
    "N/A",
    "Unknown",
    "RAPL",
}

GROUP_ITEM_IDS = {
    "DEVICE_PROPERTIES_INDEX_DESCRIPTION": "IDS_HD_DESCRIPTION",
    "DEVICE_PROPERTIES_INDEX_INSTALLED": "IDS_HD_INSTALLED",
    "DEVICE_PROPERTIES_INDEX_FIRST_INSTALLED": "IDS_HD_FIRST_INSTALLED",
    "DEVICE_PROPERTIES_INDEX_LAST_ARRIVAL": "IDS_HD_LAST_ARRIVAL",
    "DEVICE_PROPERTIES_INDEX_LAST_REMOVAL": "IDS_HD_LAST_REMOVAL",
    "DEVICE_PROPERTIES_INDEX_PROBLEM_CODE": "IDS_HD_PROBLEM_CODE",
    "DEVICE_PROPERTIES_INDEX_PROBLEM_DESCRIPTION": "IDS_HD_PROBLEM_DESCRIPTION",
    "DEVICE_PROPERTIES_INDEX_PROBLEM_STATUS": "IDS_HD_PROBLEM_STATUS",
    "DEVICE_PROPERTIES_INDEX_DRIVER": "IDS_HD_DRIVER",
    "DEVICE_PROPERTIES_INDEX_DRIVER_PROVIDER": "IDS_HD_DRIVER_PROVIDER",
    "DEVICE_PROPERTIES_INDEX_DRIVER_DESCRIPTION": "IDS_HD_DRIVER_DESCRIPTION",
    "DEVICE_PROPERTIES_INDEX_DRIVER_DATE": "IDS_HD_DRIVER_DATE",
    "DEVICE_PROPERTIES_INDEX_DRIVER_VERSION": "IDS_HD_DRIVER_VERSION",
    "DEVICE_PROPERTIES_INDEX_DRIVER_INF": "IDS_HD_DRIVER_INF",
    "DEVICE_PROPERTIES_INDEX_DRIVER_INF_SECTION": "IDS_HD_DRIVER_INF_SECTION",
    "DEVICE_PROPERTIES_INDEX_SERVICE": "IDS_HD_SERVICE",
    "DEVICE_PROPERTIES_INDEX_SECURITY_DESCRIPTOR": "IDS_HD_SECURITY_DESCRIPTOR",
    "DEVICE_PROPERTIES_INDEX_ENUMERATOR": "IDS_HD_ENUMERATOR",
    "DEVICE_PROPERTIES_INDEX_PDO_NAME": "IDS_HD_PDO_NAME",
    "DEVICE_PROPERTIES_INDEX_INSTANCEID": "IDS_HD_INSTANCE_ID",
    "DEVICE_PROPERTIES_INDEX_PARENT_INSTANCEID": "IDS_HD_PARENT_INSTANCE_ID",
    "DEVICE_PROPERTIES_INDEX_LOCATION_INFO": "IDS_HD_LOCATION_INFO",
    "DEVICE_PROPERTIES_INDEX_LOCATION_PATHS": "IDS_HD_LOCATION_PATHS",
    "DEVICE_PROPERTIES_INDEX_MATCHING_ID": "IDS_HD_MATCHING_ID",
    "DEVICE_PROPERTIES_INDEX_HARDWARE_IDS": "IDS_HD_HARDWARE_IDS",
    "DEVICE_PROPERTIES_INDEX_CLASS_NAME": "IDS_HD_NAME",
    "DEVICE_PROPERTIES_INDEX_CLASS_GUID": "IDS_HD_GUID",
    "DEVICE_PROPERTIES_INDEX_CLASS_DEVICE_NAME": "IDS_HD_DEVICE_NAME",
    "DEVICE_PROPERTIES_INDEX_CLASS_CLASS_NAME": "IDS_HD_CLASS_NAME",
    "DEVICE_PROPERTIES_INDEX_CLASS_INSTALLER": "IDS_HD_INSTALLER",
    "DEVICE_PROPERTIES_INDEX_CLASS_DEFAULT_SERVICE": "IDS_HD_DEFAULT_SERVICE",
    "DEVICE_PROPERTIES_INDEX_CLASS_SECURITY_DESCRIPTOR": "IDS_HD_SECURITY_DESCRIPTOR",
    "DEVICE_PROPERTIES_INDEX_CLASS_PROPERTY_PAGE_PROVIDER": "IDS_HD_PROPERTY_PAGE_PROVIDER",
    "NETADAPTER_DETAILS_INDEX_STATE": "IDS_HD_STATE",
    "NETADAPTER_DETAILS_INDEX_IPV4ADDRESS": "IDS_HD_IPV4_ADDRESS",
    "NETADAPTER_DETAILS_INDEX_IPV4SUBNET": "IDS_HD_IPV4_SUBNET_MASK",
    "NETADAPTER_DETAILS_INDEX_IPV4GATEWAY": "IDS_HD_IPV4_DEFAULT_GATEWAY",
    "NETADAPTER_DETAILS_INDEX_IPV4DNS": "IDS_HD_IPV4_DNS_ADDRESS",
    "NETADAPTER_DETAILS_INDEX_IPV6ADDRESS": "IDS_HD_IPV6_ADDRESS",
    "NETADAPTER_DETAILS_INDEX_IPV6TEMPADDRESS": "IDS_HD_IPV6_TEMP_ADDRESS",
    "NETADAPTER_DETAILS_INDEX_IPV6GATEWAY": "IDS_HD_IPV6_DEFAULT_GATEWAY",
    "NETADAPTER_DETAILS_INDEX_IPV6DNS": "IDS_HD_IPV6_DNS_ADDRESS",
    "NETADAPTER_DETAILS_INDEX_DOMAIN": "IDS_HD_DOMAIN",
    "NETADAPTER_DETAILS_INDEX_LINKSPEED": "IDS_HD_LINK_SPEED",
    "NETADAPTER_DETAILS_INDEX_SENT": "IDS_HD_SENT",
    "NETADAPTER_DETAILS_INDEX_RECEIVED": "IDS_HD_RECEIVED",
    "NETADAPTER_DETAILS_INDEX_TOTAL": "IDS_HD_TOTAL",
    "NETADAPTER_DETAILS_INDEX_SENDING": "IDS_HD_SENDING",
    "NETADAPTER_DETAILS_INDEX_RECEIVING": "IDS_HD_RECEIVING",
    "NETADAPTER_DETAILS_INDEX_UTILIZATION": "IDS_HD_UTILIZATION",
    "NETADAPTER_DETAILS_INDEX_UNICAST_SENTPKTS": "IDS_HD_SENT_PACKETS",
    "NETADAPTER_DETAILS_INDEX_UNICAST_RECVPKTS": "IDS_HD_RECEIVED_PACKETS",
    "NETADAPTER_DETAILS_INDEX_UNICAST_TOTALPKTS": "IDS_HD_TOTAL_PACKETS",
    "NETADAPTER_DETAILS_INDEX_UNICAST_SENT": "IDS_HD_SENT",
    "NETADAPTER_DETAILS_INDEX_UNICAST_RECEIVED": "IDS_HD_RECEIVED",
    "NETADAPTER_DETAILS_INDEX_UNICAST_TOTAL": "IDS_HD_TOTAL",
    "NETADAPTER_DETAILS_INDEX_BROADCAST_SENTPKTS": "IDS_HD_SENT_PACKETS",
    "NETADAPTER_DETAILS_INDEX_BROADCAST_RECVPKTS": "IDS_HD_RECEIVED_PACKETS",
    "NETADAPTER_DETAILS_INDEX_BROADCAST_TOTALPKTS": "IDS_HD_TOTAL_PACKETS",
    "NETADAPTER_DETAILS_INDEX_BROADCAST_SENT": "IDS_HD_SENT",
    "NETADAPTER_DETAILS_INDEX_BROADCAST_RECEIVED": "IDS_HD_RECEIVED",
    "NETADAPTER_DETAILS_INDEX_BROADCAST_TOTAL": "IDS_HD_TOTAL",
    "NETADAPTER_DETAILS_INDEX_MULTICAST_SENTPKTS": "IDS_HD_SENT_PACKETS",
    "NETADAPTER_DETAILS_INDEX_MULTICAST_RECVPKTS": "IDS_HD_RECEIVED_PACKETS",
    "NETADAPTER_DETAILS_INDEX_MULTICAST_TOTALPKTS": "IDS_HD_TOTAL_PACKETS",
    "NETADAPTER_DETAILS_INDEX_MULTICAST_SENT": "IDS_HD_SENT",
    "NETADAPTER_DETAILS_INDEX_MULTICAST_RECEIVED": "IDS_HD_RECEIVED",
    "NETADAPTER_DETAILS_INDEX_MULTICAST_TOTAL": "IDS_HD_TOTAL",
    "NETADAPTER_DETAILS_INDEX_ERRORS_SENTPKTS": "IDS_HD_SEND_ERRORS",
    "NETADAPTER_DETAILS_INDEX_ERRORS_RECVPKTS": "IDS_HD_RECEIVE_ERRORS",
    "NETADAPTER_DETAILS_INDEX_ERRORS_TOTALPKTS": "IDS_HD_TOTAL_ERRORS",
    "NETADAPTER_DETAILS_INDEX_ERRORS_SENT": "IDS_HD_SEND_DISCARDS",
    "NETADAPTER_DETAILS_INDEX_ERRORS_RECEIVED": "IDS_HD_RECEIVE_DISCARDS",
    "NETADAPTER_DETAILS_INDEX_ERRORS_TOTAL": "IDS_HD_TOTAL_DISCARDS",
}


def load_tool(name: str):
    path = REPO_ROOT / "tools" / "zhcn" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HardwareDevicesRemainingResourceTests(unittest.TestCase):
    def test_remaining_resources_have_exact_ids_and_translations(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english_rc = (PLUGIN_ROOT / "HardwareDevices.rc").read_text(encoding="utf-8-sig")
        chinese_rc = (PLUGIN_ROOT / "HardwareDevices.zh-cn.rc").read_text(encoding="utf-8-sig")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for resource_id, (numeric_id, english, chinese) in RESOURCE_TEXT.items():
            with self.subTest(resource_id=resource_id):
                self.assertRegex(header, rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$")
                self.assertRegex(english_rc, rf'(?m)^\s*{resource_id}\s+"{re.escape(english)}"$')
                self.assertRegex(chinese_rc, rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese)}"$')
                table = "strings" if english in RUNTIME_DICTIONARY_OWNED else "native_strings"
                other_table = "native_strings" if table == "strings" else "strings"
                self.assertEqual(translations[table].get(english), chinese)
                self.assertNotIn(english, translations[other_table])

        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12096$")
        self.assertEqual(len(re.findall(r"(?m)^\s*IDS_HD_[A-Z0-9_]+\s+\"", english_rc)), 96)
        self.assertEqual(len(re.findall(r"(?m)^\s*IDS_HD_[A-Z0-9_]+\s+\"", chinese_rc)), 96)

    def test_group_item_indexes_use_the_exact_resource(self) -> None:
        audit = load_tool("audit")
        actual = {}

        for filename in ("deviceprops.c", "netdetails.c"):
            source = (PLUGIN_ROOT / filename).read_text(encoding="utf-8-sig")
            masked = audit.mask_c_comments(source)
            for _, args, _, _ in audit.find_calls(masked, {"HardwareDevicesAddListViewGroupItem"}):
                index = args[2].strip()
                self.assertNotIn(index, actual)
                actual[index] = args[3].strip()

        self.assertEqual(actual, GROUP_ITEM_IDS)

    def test_all_remaining_calls_use_native_resources_and_complete_formats(self) -> None:
        audit = load_tool("audit")
        contract = load_tool("translation_contract")
        entries = []
        sources = {}

        for path in PLUGIN_ROOT.glob("*.c"):
            sources[path.name] = path.read_text(encoding="utf-8-sig")
            audit.scan_c_file(str(path), entries)

        remaining = [
            entry
            for entry in entries
            if entry["category"] in contract.CALLSITE_MIGRATION_CATEGORIES
        ]
        self.assertEqual(remaining, [])

        all_source = "\n".join(sources.values())
        self.assertIn("PCWSTR HardwareDevicesGetUiString(", sources["main.c"])
        self.assertIn("PCWSTR HardwareDevicesGetUiString(", (PLUGIN_ROOT / "devices.h").read_text(encoding="utf-8-sig"))
        for resource_id in (
            "IDS_HD_PERCENT_FORMAT",
            "IDS_HD_MILLISECONDS_FORMAT",
            "IDS_HD_RATE_FORMAT",
            "IDS_HD_QUEUE_DEPTH_FORMAT",
            "IDS_HD_VOLUME_FORMAT",
            "IDS_HD_VOLUME_LABEL_FORMAT",
            "IDS_HD_CLOSE",
            "IDS_HD_NOT_AVAILABLE",
            "IDS_HD_PENDING",
            "IDS_HD_UNKNOWN",
            "IDS_HD_UNNAMED_DEVICE",
        ):
            with self.subTest(callsite_resource=resource_id):
                self.assertIn(f"HardwareDevicesGetUiString({resource_id})", all_source)

        self.assertNotRegex(
            audit.mask_c_comments(sources["netgraph.c"]),
            r'PhaConcatStrings\w*\([^;]*L"/s"',
        )

    def test_frequently_refreshed_panels_keep_the_buffer_formatting_path(self) -> None:
        main_source = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        disk_source = (PLUGIN_ROOT / "diskgraph.c").read_text(encoding="utf-8-sig")
        net_source = (PLUGIN_ROOT / "netgraph.c").read_text(encoding="utf-8-sig")

        self.assertIn("static PH_INITONCE HardwareDevicesUiStringsInitOnce", main_source)
        self.assertIn("static PPH_STRING HardwareDevicesUiStrings[", main_source)
        self.assertIn("PhBeginInitOnce(&HardwareDevicesUiStringsInitOnce)", main_source)
        self.assertIn("PhEndInitOnce(&HardwareDevicesUiStringsInitOnce)", main_source)

        disk_update = disk_source.split("VOID DiskDeviceUpdatePanel(", 1)[1].split(
            "VOID DiskDeviceUpdateTitle(", 1
        )[0]
        net_update = net_source.split("VOID NetworkDeviceUpdatePanel(", 1)[1].split(
            "INT_PTR CALLBACK NetworkDevicePanelDialogProc(", 1
        )[0]

        self.assertGreaterEqual(disk_update.count("PhFormatToBuffer("), 8)
        self.assertGreaterEqual(net_update.count("PhFormatToBuffer("), 5)
        self.assertIn("IDS_HD_MILLISECONDS_SUFFIX", disk_update)
        self.assertIn("IDS_HD_RATE_SUFFIX", disk_update)
        self.assertIn("IDS_HD_QUEUE_SEPARATOR", disk_update)
        self.assertIn("IDS_HD_RATE_SUFFIX", net_update)

    def test_dynamic_formats_are_bound_to_their_exact_arguments(self) -> None:
        disk_graph = (PLUGIN_ROOT / "diskgraph.c").read_text(encoding="utf-8-sig")
        net_graph = (PLUGIN_ROOT / "netgraph.c").read_text(encoding="utf-8-sig")
        disk_details = (PLUGIN_ROOT / "diskdetails.c").read_text(encoding="utf-8-sig")
        net_details = (PLUGIN_ROOT / "netdetails.c").read_text(encoding="utf-8-sig")

        for source, pattern in (
            (disk_graph, r"PhaFormatString\(\s*HardwareDevicesGetUiString\(IDS_HD_PERCENT_FORMAT\),\s*Context->DiskEntry->ActiveTime\s*\)"),
            (disk_graph, r"PhaFormatString\(\s*HardwareDevicesGetUiString\(IDS_HD_MILLISECONDS_FORMAT\),\s*Context->DiskEntry->ResponseTime / PH_TICKS_PER_MS\s*\)"),
            (disk_graph, r"(?s)PhaFormatString\(\s*HardwareDevicesGetUiString\(IDS_HD_RATE_FORMAT\),\s*PhaFormatSize\(\s*Context->DiskEntry->BytesReadDelta\.Delta \+ Context->DiskEntry->BytesWrittenDelta\.Delta,\s*ULONG_MAX\s*\)->Buffer\s*\)"),
            (disk_graph, r"(?s)PhaFormatString\(\s*HardwareDevicesGetUiString\(IDS_HD_QUEUE_DEPTH_FORMAT\),\s*Context->DiskEntry->QueueDepth,\s*Context->DiskEntry->ReadCountDelta\.Delta \+ Context->DiskEntry->WriteCountDelta\.Delta\s*\)"),
            (net_graph, r"(?s)PhaFormatString\(\s*HardwareDevicesGetUiString\(IDS_HD_RATE_FORMAT\),\s*PhaFormatSize\(linkSpeedValue / BITS_IN_ONE_BYTE, ULONG_MAX\)->Buffer\s*\)"),
            (net_graph, r"(?s)PhaFormatString\(\s*HardwareDevicesGetUiString\(IDS_HD_RATE_FORMAT\),\s*PhaFormatSize\(\s*Context->AdapterEntry->CurrentNetworkReceive \+ Context->AdapterEntry->CurrentNetworkSend,\s*ULONG_MAX\s*\)->Buffer\s*\)"),
            (disk_details, r"(?s)HardwareDevicesGetUiString\(IDS_HD_VOLUME_LABEL_FORMAT\), entry->DeviceLetter,\s*PhaCreateStringEx\(volumeInfo->VolumeLabel, volumeInfo->VolumeLabelLength\)->Buffer"),
        ):
            with self.subTest(pattern=pattern):
                self.assertRegex(source, pattern)

        self.assertEqual(
            len(re.findall(
                r"HardwareDevicesGetUiString\(IDS_HD_VOLUME_FORMAT\), entry->DeviceLetter\s*\)",
                disk_details,
            )),
            2,
        )
        self.assertEqual(
            net_details.count("HardwareDevicesGetUiString(IDS_HD_RATE_WITH_BITRATE_FORMAT)"),
            3,
        )
        self.assertRegex(
            net_details,
            r"(?s)HardwareDevicesGetUiString\(IDS_HD_PRECISE_PERCENT_FORMAT\),\s*100\.0 \* utilization",
        )


if __name__ == "__main__":
    unittest.main()
