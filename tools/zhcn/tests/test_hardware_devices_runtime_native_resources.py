#!/usr/bin/env python3
"""Regression coverage for HardwareDevices runtime UI native resources."""

import importlib.util
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "HardwareDevices"
TARGET_CATEGORIES = {"c_emenu", "c_listview_col", "c_listview_item", "c_msgbox", "c_tab"}


NEW_RESOURCE_DATA = (
    ("IDS_HD_VALUE", "Value", "值"),
    ("IDS_HD_MENU_COPY_ACCELERATOR", "&Copy", "复制(&C)"),
    ("IDS_HD_MENU_ENABLE", "Enable", "启用"),
    ("IDS_HD_MENU_DISABLE", "Disable", "禁用"),
    ("IDS_HD_MENU_RESTART", "Restart", "重启"),
    ("IDS_HD_MENU_UNINSTALL", "Uninstall", "卸载"),
    ("IDS_HD_RESOURCE_TYPE", "Resource type", "资源类型"),
    ("IDS_HD_SETTING", "Setting", "设置"),
    ("IDS_HD_MENU_GO_TO_SERVICE", "Go to service...", "转到服务..."),
    ("IDS_HD_MENU_SEARCH_ONLINE", r"Search &online\bCtrl+M", r"在线搜索(&O)\bCtrl+M"),
    ("IDS_HD_MENU_SEARCH_DRIVER_UPDATE", "Search driver update", "搜索驱动程序更新"),
    ("IDS_HD_MENU_OPEN_KEY", "Open key", "打开注册表项"),
    ("IDS_HD_MENU_HARDWARE", "Hardware", "硬件"),
    ("IDS_HD_MENU_SOFTWARE", "Software", "软件"),
    ("IDS_HD_MENU_USER", "User", "用户"),
    ("IDS_HD_MENU_CONFIG", "Config", "配置"),
    ("IDS_HD_MENU_PROPERTIES", "Properties", "属性"),
    ("IDS_HD_MENU_COPY", "Copy", "复制"),
    ("IDS_HD_MENU_DEVICES", "Devices", "设备"),
    ("IDS_HD_VOLUME_CREATION_TIME", "Volume creation time", "卷创建时间"),
    ("IDS_HD_VOLUME_SERIAL_NUMBER", "Volume serial number", "卷序列号"),
    ("IDS_HD_VOLUME_UNIQUE_IDENTIFIER", "Volume unique identifier", "卷唯一标识符"),
    ("IDS_HD_VOLUME_PARTITION_IDENTIFIERS", "Volume partition identifier(s)", "卷分区标识符"),
    ("IDS_HD_VOLUME_FILE_SYSTEM", "Volume file system", "卷文件系统"),
    ("IDS_HD_VOLUME_VERSION", "Volume version", "卷版本"),
    ("IDS_HD_LFS_VERSION", "LFS version", "LFS 版本"),
    ("IDS_HD_TOTAL_SIZE", "Total size", "总大小"),
    ("IDS_HD_TOTAL_FREE", "Total free", "空闲总计"),
    ("IDS_HD_TOTAL_USED", "Total used", "已用总计"),
    ("IDS_HD_TOTAL_SECTORS", "Total sectors", "扇区总数"),
    ("IDS_HD_TOTAL_CLUSTERS", "Total clusters", "簇总数"),
    ("IDS_HD_FREE_CLUSTERS", "Free clusters", "空闲簇"),
    ("IDS_HD_RESERVED_CLUSTERS", "Reserved clusters", "已保留簇"),
    ("IDS_HD_BYTES_PER_SECTOR", "Bytes per sector", "每扇区字节数"),
    ("IDS_HD_BYTES_PER_CLUSTER", "Bytes per cluster", "每簇字节数"),
    ("IDS_HD_BYTES_PER_FILE_RECORD_SEGMENT", "Bytes per file record segment", "每文件记录段字节数"),
    ("IDS_HD_CLUSTERS_PER_FILE_RECORD_SEGMENT", "Clusters per File record segment", "每文件记录段簇数"),
    ("IDS_HD_MFT_RECORDS", "MFT records", "MFT 记录数"),
    ("IDS_HD_MFT_SIZE", "MFT size", "MFT 大小"),
    ("IDS_HD_MFT_START", "MFT start", "MFT 起始位置"),
    ("IDS_HD_MFT_ZONE_CLUSTERS", "MFT Zone clusters", "MFT 区域簇数"),
    ("IDS_HD_MFT_ZONE_SIZE", "MFT zone size", "MFT 区域大小"),
    ("IDS_HD_MFT_MIRROR_START", "MFT mirror start", "MFT 镜像起始位置"),
    ("IDS_HD_FILE_READS", "File reads", "文件读取数"),
    ("IDS_HD_FILE_WRITES", "File writes", "文件写入数"),
    ("IDS_HD_DISK_READS", "Disk reads", "磁盘读取数"),
    ("IDS_HD_DISK_WRITES", "Disk writes", "磁盘写入数"),
    ("IDS_HD_FILE_READ_BYTES", "File read bytes", "文件读取字节"),
    ("IDS_HD_FILE_WRITE_BYTES", "File write bytes", "文件写入字节"),
    ("IDS_HD_METADATA_READS", "Metadata reads", "元数据读取数"),
    ("IDS_HD_METADATA_WRITES", "Metadata writes", "元数据写入数"),
    ("IDS_HD_METADATA_DISK_READS", "Metadata disk reads", "元数据磁盘读取数"),
    ("IDS_HD_METADATA_DISK_WRITES", "Metadata disk writes", "元数据磁盘写入数"),
    ("IDS_HD_METADATA_READ_BYTES", "Metadata read bytes", "元数据读取字节"),
    ("IDS_HD_METADATA_WRITE_BYTES", "Metadata write bytes", "元数据写入字节"),
    ("IDS_HD_MFT_READS", "Mft reads", "MFT 读取数"),
    ("IDS_HD_MFT_WRITES", "Mft writes", "MFT 写入数"),
    ("IDS_HD_MFT_READ_BYTES", "Mft read bytes", "MFT 读取字节"),
    ("IDS_HD_MFT_WRITE_BYTES", "Mft write bytes", "MFT 写入字节"),
    ("IDS_HD_EXCEPTIONS", "Exceptions", "异常"),
    ("IDS_HD_RESOURCES_EXHAUSTED", "Resources exhausted", "资源耗尽"),
    ("IDS_HD_VOLUME_TRIM_COUNT", "Volume trim count", "卷 TRIM 次数"),
    ("IDS_HD_VOLUME_TRIM_TIME", "Volume trim time", "卷 TRIM 时间"),
    ("IDS_HD_VOLUME_TRIM_BYTES", "Volume trim bytes", "卷 TRIM 字节"),
    ("IDS_HD_VOLUME_TRIM_SKIPPED_COUNT", "Volume trim skipped count", "卷 TRIM 跳过次数"),
    ("IDS_HD_VOLUME_TRIM_SKIPPED_BYTES", "Volume trim skipped bytes", "卷 TRIM 跳过字节"),
    ("IDS_HD_FILE_TRIM_COUNT", "File trim count", "文件 TRIM 次数"),
    ("IDS_HD_FILE_TRIM_TIME", "File trim time", "文件 TRIM 时间"),
    ("IDS_HD_FILE_TRIM_BYTES", "File trim bytes", "文件 TRIM 字节"),
    ("IDS_HD_PROPERTY", "Property", "属性"),
    ("IDS_HD_BEST", "Best", "最佳值"),
    ("IDS_HD_RAW", "Raw", "原始值"),
    ("IDS_HD_RAW_HEX", "Raw (Hex)", "原始值（十六进制）"),
    ("IDS_HD_UNABLE_CREATE_WINDOW", "Unable to create the window.", "无法创建窗口。"),
    ("IDS_HD_DISK_DRIVES", "Disk Drives", "磁盘驱动器"),
    ("IDS_HD_PHYSICAL_LOCATION", "Physical Location", "物理位置"),
    ("IDS_HD_DRIVER_DATE_TITLE", "Driver Date", "驱动程序日期"),
    ("IDS_HD_DRIVER_VERSION_TITLE", "Driver Version", "驱动程序版本"),
    ("IDS_HD_WDDM_VERSION_TITLE", "WDDM Version", "WDDM 版本"),
    ("IDS_HD_VENDOR_ID", "Vendor ID", "供应商 ID"),
    ("IDS_HD_DEVICE_ID", "Device ID", "设备 ID"),
    ("IDS_HD_TOTAL_MEMORY", "Total Memory", "总内存"),
    ("IDS_HD_RESERVED_MEMORY", "Reserved Memory", "预留内存"),
    ("IDS_HD_GPU_FREQUENCY", "GPU Frequency", "GPU 频率"),
    ("IDS_HD_MAX_GPU_FREQUENCY", "Max GPU Frequency", "GPU 最大频率"),
    ("IDS_HD_MEMORY_FREQUENCY", "Memory Frequency", "内存频率"),
    ("IDS_HD_MEMORY_BANDWIDTH", "Memory Bandwidth", "内存带宽"),
    ("IDS_HD_PCIE_BANDWIDTH", "PCIE Bandwidth", "PCIe 带宽"),
    ("IDS_HD_FAN_RPM", "Fan RPM", "风扇转速（RPM）"),
    ("IDS_HD_POWER_USAGE", "Power Usage", "功率使用率"),
    ("IDS_HD_TEMPERATURE", "Temperature", "温度"),
    ("IDS_HD_FAILED_CHANGE_DEVICE_STATE", "Failed to change the device state.", "无法更改设备状态。"),
    ("IDS_HD_FAILED_RESTART_DEVICE", "Failed to restart the device.", "无法重启设备。"),
    ("IDS_HD_FAILED_UNINSTALL_DEVICE", "Failed to uninstall the device.", "无法卸载设备。"),
    ("IDS_HD_MENU_SECURITY", "Secu&rity", "安全(&R)"),
    ("IDS_HD_NETWORK_ADAPTERS", "Network Adapters", "网络适配器"),
    ("IDS_HD_RAPL_DRIVES", "RAPL Drives", "RAPL 设备"),
)


EXPECTED_ROUTES = {
    "c_listview_col": {
        "deviceprops.c": ("IDS_HD_NAME", "IDS_HD_VALUE", "IDS_HD_NAME", "IDS_HD_VALUE", "IDS_HD_NAME", "IDS_HD_VALUE", "IDS_HD_RESOURCE_TYPE", "IDS_HD_SETTING"),
        "diskdetails.c": ("IDS_HD_PROPERTY", "IDS_HD_PROPERTY", "IDS_HD_VALUE", "IDS_HD_BEST", "IDS_HD_RAW", "IDS_HD_RAW_HEX"),
        "diskoptions.c": ("IDS_HD_DISK_DRIVES",),
        "gpudetails.c": ("IDS_HD_PROPERTY", "IDS_HD_VALUE"),
        "netdetails.c": ("IDS_HD_PROPERTY", "IDS_HD_VALUE"),
        "netoptions.c": ("IDS_HD_NETWORK_ADAPTERS",),
        "poweroptions.c": ("IDS_HD_RAPL_DRIVES",),
    },
    "c_emenu": {
        "deviceprops.c": ("IDS_HD_MENU_COPY_ACCELERATOR", "IDS_HD_MENU_ENABLE", "IDS_HD_MENU_DISABLE", "IDS_HD_MENU_RESTART", "IDS_HD_MENU_UNINSTALL", "IDS_HD_MENU_COPY_ACCELERATOR", "IDS_HD_MENU_COPY_ACCELERATOR", "IDS_HD_MENU_COPY_ACCELERATOR"),
        "devicetree.c": ("IDS_HD_MENU_GO_TO_SERVICE", "IDS_HD_MENU_SEARCH_ONLINE", "IDS_HD_MENU_SEARCH_DRIVER_UPDATE", "IDS_HD_MENU_ENABLE", "IDS_HD_MENU_DISABLE", "IDS_HD_MENU_RESTART", "IDS_HD_MENU_UNINSTALL", "IDS_HD_MENU_OPEN_KEY", "IDS_HD_MENU_HARDWARE", "IDS_HD_MENU_SOFTWARE", "IDS_HD_MENU_USER", "IDS_HD_MENU_CONFIG", "IDS_HD_MENU_PROPERTIES", "IDS_HD_MENU_COPY", "IDS_HD_MENU_DEVICES"),
        "diskdetails.c": ("IDS_HD_MENU_COPY_ACCELERATOR", "IDS_HD_MENU_COPY_ACCELERATOR"),
        "gpudetails.c": ("IDS_HD_MENU_COPY_ACCELERATOR",),
        "main.c": ("IDS_HD_MENU_ENABLE", "IDS_HD_MENU_DISABLE", "IDS_HD_MENU_RESTART", "IDS_HD_MENU_UNINSTALL", "IDS_HD_MENU_SEARCH_ONLINE", "IDS_HD_MENU_SEARCH_DRIVER_UPDATE", "IDS_HD_MENU_OPEN_KEY", "IDS_HD_MENU_HARDWARE", "IDS_HD_MENU_SOFTWARE", "IDS_HD_MENU_USER", "IDS_HD_MENU_CONFIG", "IDS_HD_MENU_SECURITY", "IDS_HD_MENU_PROPERTIES"),
        "netdetails.c": ("IDS_HD_MENU_COPY_ACCELERATOR",),
    },
    "c_listview_item": {
        "diskdetails.c": (
            "IDS_HD_VOLUME_CREATION_TIME", "IDS_HD_VOLUME_SERIAL_NUMBER", "IDS_HD_VOLUME_UNIQUE_IDENTIFIER", "IDS_HD_VOLUME_PARTITION_IDENTIFIERS", "IDS_HD_VOLUME_FILE_SYSTEM", "IDS_HD_VOLUME_VERSION", "IDS_HD_LFS_VERSION", "IDS_HD_TOTAL_SIZE", "IDS_HD_TOTAL_FREE", "IDS_HD_TOTAL_USED", "IDS_HD_TOTAL_SECTORS", "IDS_HD_TOTAL_CLUSTERS", "IDS_HD_FREE_CLUSTERS", "IDS_HD_RESERVED_CLUSTERS", "IDS_HD_BYTES_PER_SECTOR", "IDS_HD_BYTES_PER_CLUSTER", "IDS_HD_BYTES_PER_FILE_RECORD_SEGMENT", "IDS_HD_CLUSTERS_PER_FILE_RECORD_SEGMENT", "IDS_HD_MFT_RECORDS", "IDS_HD_MFT_SIZE", "IDS_HD_MFT_START", "IDS_HD_MFT_ZONE_CLUSTERS", "IDS_HD_MFT_ZONE_SIZE", "IDS_HD_MFT_MIRROR_START", "IDS_HD_FILE_READS", "IDS_HD_FILE_WRITES", "IDS_HD_DISK_READS", "IDS_HD_DISK_WRITES", "IDS_HD_FILE_READ_BYTES", "IDS_HD_FILE_WRITE_BYTES", "IDS_HD_METADATA_READS", "IDS_HD_METADATA_WRITES", "IDS_HD_METADATA_DISK_READS", "IDS_HD_METADATA_DISK_WRITES", "IDS_HD_METADATA_READ_BYTES", "IDS_HD_METADATA_WRITE_BYTES", "IDS_HD_MFT_READS", "IDS_HD_MFT_WRITES", "IDS_HD_MFT_READ_BYTES", "IDS_HD_MFT_WRITE_BYTES", "IDS_HD_EXCEPTIONS", "IDS_HD_RESOURCES_EXHAUSTED", "IDS_HD_VOLUME_TRIM_COUNT", "IDS_HD_VOLUME_TRIM_TIME", "IDS_HD_VOLUME_TRIM_BYTES", "IDS_HD_VOLUME_TRIM_SKIPPED_COUNT", "IDS_HD_VOLUME_TRIM_SKIPPED_BYTES", "IDS_HD_FILE_TRIM_COUNT", "IDS_HD_FILE_TRIM_TIME", "IDS_HD_FILE_TRIM_BYTES",
        ),
        "gpudetails.c": ("IDS_HD_PHYSICAL_LOCATION", "IDS_HD_DRIVER_DATE_TITLE", "IDS_HD_DRIVER_VERSION_TITLE", "IDS_HD_WDDM_VERSION_TITLE", "IDS_HD_VENDOR_ID", "IDS_HD_DEVICE_ID", "IDS_HD_TOTAL_MEMORY", "IDS_HD_RESERVED_MEMORY", "IDS_HD_GPU_FREQUENCY", "IDS_HD_MAX_GPU_FREQUENCY", "IDS_HD_MEMORY_FREQUENCY", "IDS_HD_MEMORY_BANDWIDTH", "IDS_HD_PCIE_BANDWIDTH", "IDS_HD_FAN_RPM", "IDS_HD_POWER_USAGE", "IDS_HD_TEMPERATURE"),
    },
    "c_msgbox": {
        "diskdetails.c": ("IDS_HD_UNABLE_CREATE_WINDOW",),
        "gpunodes.c": ("IDS_HD_UNABLE_CREATE_WINDOW",),
        "main.c": ("IDS_HD_FAILED_CHANGE_DEVICE_STATE", "IDS_HD_FAILED_CHANGE_DEVICE_STATE", "IDS_HD_FAILED_RESTART_DEVICE", "IDS_HD_FAILED_RESTART_DEVICE", "IDS_HD_FAILED_RESTART_DEVICE", "IDS_HD_FAILED_UNINSTALL_DEVICE", "IDS_HD_FAILED_UNINSTALL_DEVICE"),
        "netdetails.c": ("IDS_HD_UNABLE_CREATE_WINDOW",),
    },
}


CALL_PATTERNS = {
    "c_listview_col": r"PhAddListViewColumn(?:Ex)?\([^;]*?HardwareDevicesGetUiString\((IDS_HD_[A-Z0-9_]+)\)[^;]*?\);",
    "c_emenu": r"PhCreateEMenuItem\([^;]*?HardwareDevicesGetUiString\((IDS_HD_[A-Z0-9_]+)\)[^;]*?\)",
    "c_listview_item": r"PhAddListViewItem\([^;]*?HardwareDevicesGetUiString\((IDS_HD_[A-Z0-9_]+)\)[^;]*?\);",
    "c_msgbox": r"PhShow(?:Error2|Message\w*|Status)\([^;]*?HardwareDevicesGetUiString\((IDS_HD_[A-Z0-9_]+)\)[^;]*?\);",
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("hardware_devices_runtime_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path):
    return {
        symbol: value.replace('""', '"').replace(r"\r", "\r").replace(r"\n", "\n")
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_HD_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class HardwareDevicesRuntimeNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit_module()
        cls.sources = {
            path.name: cls.audit.mask_c_comments(path.read_text(encoding="utf-8-sig"))
            for path in PLUGIN_ROOT.glob("*.c")
        }
        cls.migration_symbols = {"IDS_HD_NAME", *(row[0] for row in NEW_RESOURCE_DATA)}

    def test_resources_are_exact_contiguous_and_cached_for_plugin_lifetime(self):
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        defines = {
            symbol: int(value)
            for symbol, value in re.findall(r"(?m)^#define\s+(IDS_HD_[A-Z0-9_]+)\s+(\d+)$", header)
        }
        english = parse_stringtable(PLUGIN_ROOT / "HardwareDevices.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "HardwareDevices.zh-cn.rc")

        for offset, (symbol, en, zh) in enumerate(NEW_RESOURCE_DATA, start=12102):
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), offset)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual(defines["IDS_HD_NAME"], 12034)
        self.assertEqual(english["IDS_HD_NAME"], "Name")
        self.assertEqual(chinese["IDS_HD_NAME"], "名称")
        self.assertEqual(sorted(defines.values()), list(range(12000, 12396)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 396)
        self.assertEqual(len(chinese), 396)
        self.assertRegex(header, r"(?m)^#define IDS_HD_LAST\s+IDS_HD_DEVICE_PROPERTY_GPU_PHYSICAL_ADAPTER_INDEX$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+12396$")

        main = self.sources["main.c"]
        self.assertRegex(main, r"static\s+PPH_STRING\s+HardwareDevicesUiStrings\s*\[\s*IDS_HD_LAST\s*-\s*IDS_HD_FIRST\s*\+\s*1\s*\]")
        self.assertRegex(main, r"for\s*\(ULONG id\s*=\s*IDS_HD_FIRST\s*;\s*id\s*<=\s*IDS_HD_LAST\s*;\s*id\+\+\)")
        self.assertRegex(main, r"return\s+HardwareDevicesUiStrings\[ResourceId\s*-\s*IDS_HD_FIRST\]\s*;")

    def test_all_137_calls_use_the_exact_native_resource_routes(self):
        actual_count = 0
        for category, expected_files in EXPECTED_ROUTES.items():
            pattern = CALL_PATTERNS[category]
            for filename, expected in expected_files.items():
                actual = tuple(
                    symbol
                    for symbol in re.findall(pattern, self.sources[filename], re.S)
                    if symbol in self.migration_symbols
                )
                with self.subTest(category=category, filename=filename):
                    self.assertEqual(actual, expected)
                actual_count += len(actual)
        self.assertEqual(actual_count, 137)

    def test_shortcuts_and_technical_labels_are_preserved(self):
        english = parse_stringtable(PLUGIN_ROOT / "HardwareDevices.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "HardwareDevices.zh-cn.rc")
        self.assertEqual(english["IDS_HD_MENU_SEARCH_ONLINE"], r"Search &online\bCtrl+M")
        self.assertEqual(chinese["IDS_HD_MENU_SEARCH_ONLINE"], r"在线搜索(&O)\bCtrl+M")
        self.assertEqual(english["IDS_HD_MENU_COPY_ACCELERATOR"].count("&"), 1)
        self.assertEqual(chinese["IDS_HD_MENU_COPY_ACCELERATOR"].count("&"), 1)
        self.assertEqual(english["IDS_HD_MENU_SECURITY"].count("&"), 1)
        self.assertEqual(chinese["IDS_HD_MENU_SECURITY"].count("&"), 1)
        self.assertEqual(chinese["IDS_HD_LFS_VERSION"], "LFS 版本")
        self.assertEqual(chinese["IDS_HD_MFT_RECORDS"], "MFT 记录数")
        self.assertEqual(chinese["IDS_HD_WDDM_VERSION_TITLE"], "WDDM 版本")
        self.assertEqual(chinese["IDS_HD_PCIE_BANDWIDTH"], "PCIe 带宽")

    def test_fresh_module_has_no_target_runtime_categories(self):
        entries = []
        for path in sorted(PLUGIN_ROOT.glob("*.c")):
            self.audit.scan_c_file(str(path), entries)
        remaining = Counter(
            (entry["category"], entry["english"], entry["file"])
            for entry in entries
            if entry["category"] in TARGET_CATEGORIES
        )
        self.assertEqual(remaining, Counter())


if __name__ == "__main__":
    unittest.main()
