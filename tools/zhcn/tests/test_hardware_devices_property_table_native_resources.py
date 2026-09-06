#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import pathlib
import re
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "HardwareDevices"

EXPECTED_PROPERTY_ORDER_SHA256 = (
    "1905aca95a10db1b02d3e066fa6a5b2fb3e790d3cc18824d8358cd26e6cdda78"
)

REUSED_RESOURCES = {
    "PhDevicePropertyName": ("IDS_HD_NAME", 12034),
    "PhDevicePropertyService": ("IDS_HD_SERVICE", 12024),
    "PhDevicePropertyClass": ("IDS_HD_GROUP_CLASS", 12097),
    "PhDevicePropertyEnumeratorName": ("IDS_HD_ENUMERATOR", 12026),
    "PhDevicePropertyInstallDate": ("IDS_HD_INSTALLED", 12010),
    "PhDevicePropertyFirstInstallDate": ("IDS_HD_FIRST_INSTALLED", 12011),
    "PhDevicePropertyLastArrivalDate": ("IDS_HD_LAST_ARRIVAL", 12012),
    "PhDevicePropertyLastRemovalDate": ("IDS_HD_LAST_REMOVAL", 12013),
    "PhDevicePropertyDeviceDesc": ("IDS_HD_DESCRIPTION", 12009),
    "PhDevicePropertyInstanceId": ("IDS_HD_INSTANCE_ID", 12028),
    "PhDevicePropertyParentInstanceId": ("IDS_HD_PARENT_INSTANCE_ID", 12029),
    "PhDevicePropertyPDOName": ("IDS_HD_PDO_NAME", 12027),
    "PhDevicePropertyLocationInfo": ("IDS_HD_LOCATION_INFO", 12030),
    "PhDevicePropertyDriver": ("IDS_HD_DRIVER", 12017),
    "PhDevicePropertyDriverVersion": ("IDS_HD_DRIVER_VERSION", 12021),
    "PhDevicePropertyDriverDate": ("IDS_HD_DRIVER_DATE", 12020),
    "PhDevicePropertyProblemCode": ("IDS_HD_PROBLEM_CODE", 12014),
    "PhDevicePropertyProblemStatus": ("IDS_HD_PROBLEM_STATUS", 12016),
    "PhDevicePropertyHardwareIds": ("IDS_HD_HARDWARE_IDS", 12033),
    "PhDevicePropertySecuritySDS": ("IDS_HD_SECURITY_DESCRIPTOR", 12025),
    "PhDevicePropertyLocationPaths": ("IDS_HD_LOCATION_PATHS", 12031),
    "PhDevicePropertyDriverProblemDesc": ("IDS_HD_PROBLEM_DESCRIPTION", 12015),
    "PhDevicePropertyDriverDesc": ("IDS_HD_DRIVER_DESCRIPTION", 12019),
    "PhDevicePropertyDriverInfSection": ("IDS_HD_DRIVER_INF_SECTION", 12023),
    "PhDevicePropertyMatchingDeviceId": ("IDS_HD_MATCHING_ID", 12032),
    "PhDevicePropertyDriverProvider": ("IDS_HD_DRIVER_PROVIDER", 12018),
    "PhDevicePropertyClassClassName": ("IDS_HD_CLASS_NAME", 12037),
}

CORRECTED_ENGLISH = {
    "PhDevicePropertyHardwareIds": "Hardware IDs",
    "PhDevicePropertyManufacturerAttributes": "Manufacturer attributes",
    "PhDevicePropertyNumaProximityDomain": "NUMA proximity domain",
    "PhDevicePropertyNumaNode": "NUMA node",
    "PhDevicePropertyDriverInfSectionExt": "Driver INF section extension",
    "PhDevicePropertySafeRemovalRequiredOverride": "Safe removal required override",
    "PhDevicePropertyContainerConfigFlags": "Container configuration flags",
    "PhDevicePropertyContainerManufacturer": "Container manufacturer",
    "PhDevicePropertyPciSubClass": "PCI subclass",
    "PhDevicePropertyPciExpressSpecVersion": "PCI Express specification version",
    "PhDevicePropertyStoragePartitionNumber": "Storage partition number",
}

CORRECTED_CHINESE = {
    "Hardware IDs": "硬件 ID",
    "Manufacturer attributes": "制造商属性",
    "NUMA proximity domain": "NUMA 邻近域",
    "NUMA node": "NUMA 节点",
    "Driver INF section extension": "驱动程序 INF 节扩展",
    "Safe removal required override": "安全移除要求替代值",
    "Container configuration flags": "容器配置标志",
    "Container manufacturer": "容器制造商",
    "PCI subclass": "PCI 子类",
    "PCI Express specification version": "PCI Express 规范版本",
    "Storage partition number": "存储分区号",
}

PROPERTY_TRANSLATIONS_DATA = r"""
Name|名称
Manufacturer|制造商
Service|服务
Class|类
Enumerator|枚举器
Installed|安装时间
First installed|首次安装时间
Last arrival|最近接入时间
Last removal|最近移除时间
Description|描述
Friendly name|友好名称
Instance ID|实例 ID
Parent instance ID|父实例 ID
PDO name|PDO 名称
Location info|位置信息
Class GUID|类 GUID
Driver|驱动程序
Driver version|驱动程序版本
Driver date|驱动程序日期
Firmware date|固件日期
Firmware version|固件版本
Firmware revision|固件修订版本
Has problem|存在问题
Problem code|问题代码
Problem status|问题状态
Node status flags|设备节点状态标志
Capabilities|功能
Upper filters|上层筛选器
Lower filters|下层筛选器
Hardware IDs|硬件 ID
Compatible IDs|兼容 ID
Configuration flags|配置标志
Number|编号
Bus type GUID|总线类型 GUID
Legacy bus type|旧式总线类型
Bus number|总线编号
Security descriptor (binary)|安全描述符（二进制）
Security descriptor|安全描述符
Type|类型
Exclusive|独占
Characteristics|特征
Address|地址
Power data|电源数据
Removal policy|移除策略
Removal policy default|移除策略默认值
Removal policy override|移除策略替代值
Install state|安装状态
Location paths|位置路径
Base container ID|基础容器 ID
Ejection relations|弹出关系
Removal relations|移除关系
Power relations|电源关系
Bus relations|总线关系
Children|子设备
Siblings|同级设备
Transport relations|传输关系
Reported|已报告
Legacy|旧式
Container ID|容器 ID
Local machine container|本地计算机容器
Model|型号
Model ID|型号 ID
Friendly name attributes|友好名称属性
Manufacturer attributes|制造商属性
Presence not for device|存在状态不针对设备
Signal strength|信号强度
Associateable by user action|可通过用户操作关联
Show uninstall UI|显示卸载界面
NUMA proximity domain|NUMA 邻近域
DHP rebalance policy|DHP 重新平衡策略
NUMA node|NUMA 节点
Bus reported description|总线报告的描述
Present|存在
Configuration ID|配置 ID
Reported IDs hash|已报告 ID 哈希
Physical location|物理位置
BIOS name|BIOS 名称
Problem description|问题描述
Debugger safe|调试器安全
Post install in progress|正在执行安装后处理
Stack|堆栈
Extended configuration IDs|扩展配置 ID
Reboot required|需要重启
Dependency providers|依赖提供方
Dependency dependents|依赖方
Soft restart supported|支持软重启
Extended address|扩展地址
Assigned to guest|已分配给来宾
Creator process ID|创建进程 ID
Firmware vendor|固件供应商
Session ID|会话 ID
Driver description|驱动程序描述
Driver INF path|驱动程序 INF 路径
Driver INF section|驱动程序 INF 节
Driver INF section extension|驱动程序 INF 节扩展
Matching ID|匹配 ID
Driver provider|驱动程序提供商
Driver property page provider|驱动程序属性页提供程序
Driver co-installers|驱动程序共同安装程序
Resource picker tags|资源选择器标记
Resource picker exceptions|资源选择器例外
Driver rank|驱动程序等级
Driver LOGO level|驱动程序 LOGO 级别
No connect sound|无连接声音
Generic driver installed|已安装通用驱动程序
Additional software requested|已请求其他软件
Safe removal required|需要安全移除
Safe removal required override|安全移除要求替代值
Package model|软件包型号
Package vendor website|软件包供应商网站
Package description|软件包描述
Package documentation|软件包文档
Package icon|软件包图标
Package branding icon|软件包品牌图标
Class upper filters|类上层筛选器
Class lower filters|类下层筛选器
Class security descriptor (binary)|类安全描述符（二进制）
Class security descriptor|类安全描述符
Class type|类类型
Class exclusive|类独占
Class characteristics|类特性
Class device name|类设备名称
Class name|类名
Class icon|类图标
Class installer|类安装程序
Class property page provider|类属性页提供程序
Class no install|类禁止安装
Class no display|类禁止显示
Class silent install|类静默安装
Class no use class|类禁止使用
Class default service|类默认服务
Class icon path|类图标路径
Class DHP rebalance opt-out|类 DHP 重新平衡选择退出
Class co-installers|类共同安装程序
Interface friendly name|接口友好名称
Interface enabled|接口已启用
Interface class GUID|接口类 GUID
Interface reference|接口引用
Interface restricted|接口受限
Interface unrestricted application capabilities|接口不受限应用功能
Interface schematic name|接口示意名称
Interface class default interface|接口类默认接口
Interface class name|接口类名称
Container address|容器地址
Container discovery method|容器发现方法
Container encrypted|容器已加密
Container authenticated|容器已验证
Container connected|容器已连接
Container paired|容器已配对
Container icon|容器图标
Container version|容器版本
Container last seen|容器最近出现时间
Container last connected|容器最近连接时间
Container show in disconnected state|断开连接时显示容器
Container local machine|容器属于本地计算机
Container metadata path|容器元数据路径
Container metadata search in progress|正在搜索容器元数据
Metadata checksum|元数据校验和
Container not interesting for display|容器不适合显示
Container launch on connect|连接时启动容器
Container launch from explorer|从资源管理器启动容器
Container baseline experience ID|容器基准体验 ID
Container uniquely identifiable|容器可唯一标识
Container association|容器关联
Container description|容器描述
Container description other|容器其他描述
Container has problem|容器存在问题
Container shared device|容器是共享设备
Container network device|容器是网络设备
Container default device|容器是默认设备
Container metadata cabinet|容器元数据包
Container requires pairing elevation|容器配对需要提升权限
Container experience ID|容器体验 ID
Container category|容器类别
Container category description|容器类别描述
Container category description plural|容器类别描述（复数）
Container category icon|容器类别图标
Container category group description|容器类别组描述
Container category group icon|容器类别组图标
Container primary category|容器主要类别
Container unpair uninstall|取消配对时卸载容器
Container requires uninstall elevation|卸载容器需要提升权限
Container function sub-rank|容器功能子等级
Container always show connected|始终将容器显示为已连接
Container configuration flags|容器配置标志
Container privileged package family names|容器特权程序包系列名称
Container custom privileged package family names|容器自定义特权程序包系列名称
Container reboot required|容器需要重启
Container friendly name|容器友好名称
Container manufacturer|容器制造商
Container model name|容器型号名称
Container model number|容器型号编号
Container install in progress|正在安装容器
Object type|对象类型
PCI device type|PCI 设备类型
PCI current speed and mode|PCI 当前速度和模式
PCI base class|PCI 基类
PCI subclass|PCI 子类
PCI programming interface|PCI 编程接口
PCI current payload size|PCI 当前有效负载大小
PCI max payload size|PCI 最大有效负载大小
PCI max read request size|PCI 最大读取请求大小
PCI current link speed|PCI 当前链路速度
PCI current link width|PCI 当前链路宽度
PCI max link speed|PCI 最大链路速度
PCI max link width|PCI 最大链路宽度
PCI Express specification version|PCI Express 规范版本
PCI interrupt support|PCI 中断支持
PCI interrupt message maximum|PCI 中断消息最大值
PCI BAR types|PCI BAR 类型
PCI SR-IOV support|PCI SR-IOV 支持
PCI label ID|PCI 标签 ID
PCI label string|PCI 标签字符串
PCI serial number|PCI 序列号
PCI express capability control|PCI Express 功能控制
PCI native express control|PCI 原生 Express 控制
PCI system MSI support|PCI 系统 MSI 支持
Storage portable|便携式存储
Storage removable media|可移动存储介质
Storage system critical|系统关键存储
Storage disk number|存储磁盘号
Storage partition number|存储分区号
GPU LUID|GPU LUID
GPU physical adapter index|GPU 物理适配器索引
""".strip()
PROPERTY_TRANSLATIONS = [tuple(line.split("|", 1)) for line in PROPERTY_TRANSLATIONS_DATA.splitlines()]

RUNTIME_COMPATIBILITY_KEYS = {
    "Name",
    "Service",
    "Class",
    "Description",
    "Driver",
    "Capabilities",
    "Type",
    "Characteristics",
    "Address",
    "Container ID",
    "Session ID",
}


def load_audit():
    spec = importlib.util.spec_from_file_location(
        "hardware_property_audit", REPO_ROOT / "tools" / "zhcn" / "audit.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def property_resource_symbol(prop_class):
    suffix = prop_class.removeprefix("PhDeviceProperty").replace("_", "")
    suffix = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", suffix)
    suffix = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", suffix)
    return "IDS_HD_DEVICE_PROPERTY_" + suffix.upper()


def parse_table(source):
    body = source.split(
        "const DEVICE_PROPERTY_TABLE_ENTRY DeviceItemPropertyTable[] =", 1
    )[1].split("C_ASSERT", 1)[0]
    return re.findall(
        r'\{\s*(PhDeviceProperty\w+)\s*,\s*(IDS_HD_[A-Z0-9_]+)\s*,\s*'
        r'L"((?:[^"\\]|\\.)*)"\s*,\s*(TRUE|FALSE)\s*,\s*(\d+)\s*,\s*'
        r"([^}]+?)\s*\}",
        body,
    )


class HardwareDevicesPropertyTableNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()
        cls.tree = (PLUGIN_ROOT / "devicetree.c").read_text(encoding="utf-8-sig")
        cls.props = (PLUGIN_ROOT / "deviceprops.c").read_text(encoding="utf-8-sig")
        cls.header = (PLUGIN_ROOT / "devices.h").read_text(encoding="utf-8-sig")
        cls.resource_header = (PLUGIN_ROOT / "resource.h").read_text(
            encoding="utf-8-sig"
        )

    def test_all_224_properties_keep_identity_order_and_exact_resource_route(self):
        rows = parse_table(self.tree)
        self.assertEqual(224, len(rows))
        self.assertEqual(224, len(PROPERTY_TRANSLATIONS))
        self.assertEqual(
            EXPECTED_PROPERTY_ORDER_SHA256,
            hashlib.sha256(
                "\n".join(row[0] for row in rows).encode("utf-8")
            ).hexdigest(),
        )

        defines = {
            symbol: int(value)
            for symbol, value in re.findall(
                r"(?m)^#define\s+(IDS_HD_[A-Z0-9_]+)\s+(\d+)$",
                self.resource_header,
            )
        }
        next_new_id = 12199
        for index, (prop_class, resource_id, english, _visible, _width, _flags) in enumerate(rows):
            if prop_class in REUSED_RESOURCES:
                expected_symbol, expected_id = REUSED_RESOURCES[prop_class]
            else:
                expected_symbol, expected_id = property_resource_symbol(prop_class), next_new_id
                next_new_id += 1
            self.assertEqual(expected_symbol, resource_id, prop_class)
            self.assertEqual(expected_id, defines.get(resource_id), prop_class)
            self.assertEqual(PROPERTY_TRANSLATIONS[index][0], english, prop_class)
            if prop_class in CORRECTED_ENGLISH:
                self.assertEqual(CORRECTED_ENGLISH[prop_class], english, prop_class)

        self.assertEqual(12396, next_new_id)
        self.assertRegex(
            self.resource_header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12396$",
        )

    def test_three_ui_consumers_share_stable_cached_property_name_helper(self):
        self.assertRegex(
            self.header,
            r"DevicePropertyTableEntryGetColumnName\([^)]*\)\s*\{\s*"
            r"return PhGetStringOrDefault\(\s*"
            r"HardwareDevicesGetUiStringObject\(Entry->ResourceId\),\s*"
            r"Entry->ColumnName\s*\);\s*\}",
        )
        self.assertNotRegex(
            self.header,
            r"DevicePropertyTableEntryGetColumnName[\s\S]{0,300}"
            r"(?:PH_AUTO|PhLoadUiString)",
        )
        self.assertRegex(
            self.tree,
            r"PhAddTreeNewColumn\([\s\S]*?"
            r"DevicePropertyTableEntryGetColumnName\(entry\),[\s\S]*?"
            r"entry->ColumnTextFlags\s*\);",
        )
        self.assertRegex(
            self.props,
            r"name\s*=\s*DevicePropertyTableEntryGetColumnName\("
            r"&DeviceItemPropertyTable\[propClass\]\);",
        )
        self.assertRegex(
            self.props,
            r"PhAddListViewGroupItem\(Context->InterfacesListViewHandle,\s*"
            r"group,\s*index,\s*DevicePropertyTableEntryGetColumnName\(entry\),\s*NULL\);",
        )
        self.assertRegex(
            self.tree,
            r"const\s+DEVICE_PROPERTY_TABLE_ENTRY\s+DeviceItemPropertyTable\[\]\s*=",
        )
        self.assertEqual(224, len(parse_table(self.tree)))

    def test_bilingual_resources_and_json_ownership_are_complete(self):
        rows = parse_table(self.tree)
        english_rc = (PLUGIN_ROOT / "HardwareDevices.rc").read_text(
            encoding="utf-8-sig"
        )
        chinese_rc = (PLUGIN_ROOT / "HardwareDevices.zh-cn.rc").read_text(
            encoding="utf-8-sig"
        )
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(
                encoding="utf-8"
            )
        )

        for index, (_prop, resource_id, english, _visible, _width, _flags) in enumerate(rows):
            self.assertRegex(
                english_rc,
                rf'(?m)^\s*{resource_id}\s+"{re.escape(english)}"$',
            )
            chinese_match = re.search(
                rf'(?m)^\s*{resource_id}\s+"([^"]+)"$', chinese_rc
            )
            self.assertIsNotNone(chinese_match, resource_id)
            chinese = chinese_match.group(1)
            self.assertEqual(PROPERTY_TRANSLATIONS[index][1], chinese, resource_id)
            if english in RUNTIME_COMPATIBILITY_KEYS:
                self.assertEqual(chinese, translations["strings"].get(english))
                self.assertNotIn(english, translations["native_strings"])
            else:
                self.assertEqual(chinese, translations["native_strings"].get(english))
                self.assertNotIn(english, translations["strings"])

        for english, chinese in CORRECTED_CHINESE.items():
            self.assertEqual(chinese, translations["native_strings"].get(english))

        self.assertEqual(
            RUNTIME_COMPATIBILITY_KEYS,
            {
                english
                for english, _chinese in PROPERTY_TRANSLATIONS
                if english in translations["strings"]
            },
        )

    def test_physical_location_keeps_sentence_case_resource_distinct(self):
        self.assertIn(
            (
                "PhDevicePropertyPhysicalDeviceLocation",
                "IDS_HD_DEVICE_PROPERTY_PHYSICAL_DEVICE_LOCATION",
                "Physical location",
                "FALSE",
                "80",
                "0",
            ),
            parse_table(self.tree),
        )
        self.assertRegex(
            (PLUGIN_ROOT / "HardwareDevices.rc").read_text(encoding="utf-8-sig"),
            r'(?m)^\s*IDS_HD_PHYSICAL_LOCATION\s+"Physical Location"$',
        )

    def test_audit_models_raw_table_through_all_three_consumers(self):
        fixture = r'''
typedef struct DEVICE_PROPERTY_TABLE_ENTRY
{
    ULONG PropClass;
    PWSTR ColumnName;
} DEVICE_PROPERTY_TABLE_ENTRY;
const DEVICE_PROPERTY_TABLE_ENTRY DeviceItemPropertyTable[] =
{
    { PhDevicePropertyName, L"Name" },
    { PhDevicePropertyManufacturer, L"Manufacturer" },
};
VOID AddTree(VOID)
{
    const DEVICE_PROPERTY_TABLE_ENTRY *entry = &DeviceItemPropertyTable[0];
    PhAddTreeNewColumn(tree, 0, TRUE, entry->ColumnName, 80, 0, 0, 0);
}
VOID AddProps(VOID)
{
    name = DeviceItemPropertyTable[propClass].ColumnName;
    PhAddListViewItem(list, 0, name, NULL);
}
VOID AddInterfaces(VOID)
{
    const DEVICE_PROPERTY_TABLE_ENTRY *entry = &DeviceItemPropertyTable[0];
    PhAddListViewGroupItem(list, 0, 0, entry->ColumnName, NULL);
}
'''
        with tempfile.NamedTemporaryFile("w", suffix=".c", encoding="utf-8") as source:
            source.write(fixture)
            source.flush()
            entries = []
            self.audit.scan_c_file(source.name, entries)

        self.assertEqual(
            {
                ("c_treenew_col", "Name"),
                ("c_treenew_col", "Manufacturer"),
                ("c_listview_item", "Name"),
                ("c_listview_item", "Manufacturer"),
                ("c_listview_group_item", "Name"),
                ("c_listview_group_item", "Manufacturer"),
            },
            {(entry["category"], entry["english"]) for entry in entries},
        )

    def test_current_resourceized_table_has_no_property_name_audit_entries(self):
        entries = []
        self.audit.scan_c_file(str(PLUGIN_ROOT / "devicetree.c"), entries)
        self.audit.scan_c_file(str(PLUGIN_ROOT / "deviceprops.c"), entries)
        property_names = {
            row[2] for row in parse_table(self.tree)
        }
        self.assertEqual(
            [],
            [
                entry
                for entry in entries
                if entry["english"] in property_names
                and entry["category"]
                in {"c_treenew_col", "c_listview_item", "c_listview_group_item"}
            ],
        )

    def test_route_contract_detects_resource_order_and_field_mutations(self):
        rows = parse_table(self.tree)
        expected = [(row[0], row[1]) for row in rows]

        swapped_resources = self.tree.replace(
            "PhDevicePropertyName, IDS_HD_NAME",
            "PhDevicePropertyName, IDS_HD_SERVICE",
            1,
        ).replace(
            "PhDevicePropertyService, IDS_HD_SERVICE",
            "PhDevicePropertyService, IDS_HD_NAME",
            1,
        )
        self.assertNotEqual(expected, [(row[0], row[1]) for row in parse_table(swapped_resources)])

        first_row = re.search(
            r"(?m)^\s*\{ PhDevicePropertyName,[^\n]+$", self.tree
        ).group(0)
        second_row = re.search(
            r"(?m)^\s*\{ PhDevicePropertyManufacturer,[^\n]+$", self.tree
        ).group(0)
        swapped_order = self.tree.replace(first_row, "__FIRST__", 1)
        swapped_order = swapped_order.replace(second_row, first_row, 1)
        swapped_order = swapped_order.replace("__FIRST__", second_row, 1)
        self.assertNotEqual(
            EXPECTED_PROPERTY_ORDER_SHA256,
            hashlib.sha256(
                "\n".join(row[0] for row in parse_table(swapped_order)).encode("utf-8")
            ).hexdigest(),
        )

        missing_resource = self.tree.replace(
            "PhDevicePropertyName, IDS_HD_NAME,",
            "PhDevicePropertyName,",
            1,
        )
        self.assertEqual(223, len(parse_table(missing_resource)))

        swapped_fallbacks = self.tree.replace(
            'IDS_HD_NAME, L"Name"',
            'IDS_HD_NAME, L"Manufacturer"',
            1,
        ).replace(
            'IDS_HD_DEVICE_PROPERTY_MANUFACTURER, L"Manufacturer"',
            'IDS_HD_DEVICE_PROPERTY_MANUFACTURER, L"Name"',
            1,
        )
        self.assertNotEqual(
            [english for english, _chinese in PROPERTY_TRANSLATIONS],
            [row[2] for row in parse_table(swapped_fallbacks)],
        )

    def test_audit_rejects_short_lived_helper_and_missing_resource_id(self):
        fixture = r'''
typedef struct DEVICE_PROPERTY_TABLE_ENTRY
{
    ULONG PropClass;
    ULONG ResourceId;
    PWSTR ColumnName;
} DEVICE_PROPERTY_TABLE_ENTRY;
const DEVICE_PROPERTY_TABLE_ENTRY DeviceItemPropertyTable[] =
{
    { PhDevicePropertyName, IDS_HD_NAME, L"Name" },
    { PhDevicePropertyManufacturer, L"Manufacturer" },
};
PCWSTR DevicePropertyTableEntryGetColumnName(const DEVICE_PROPERTY_TABLE_ENTRY *Entry)
{
    return PhGetString(PH_AUTO(PhLoadUiString(module, Entry->ResourceId, NULL)));
}
VOID AddAll(VOID)
{
    const DEVICE_PROPERTY_TABLE_ENTRY *entry = &DeviceItemPropertyTable[0];
    PhAddTreeNewColumn(tree, 0, TRUE, DevicePropertyTableEntryGetColumnName(entry), 80, 0, 0, 0);
    name = DevicePropertyTableEntryGetColumnName(&DeviceItemPropertyTable[propClass]);
    PhAddListViewItem(list, 0, name, NULL);
    PhAddListViewGroupItem(list, 0, 0, DevicePropertyTableEntryGetColumnName(entry), NULL);
}
'''
        with tempfile.NamedTemporaryFile("w", suffix=".c", encoding="utf-8") as source:
            source.write(fixture)
            source.flush()
            entries = []
            self.audit.scan_c_file(source.name, entries)

        self.assertEqual(6, len(entries))
        self.assertEqual(
            {"c_treenew_col", "c_listview_item", "c_listview_group_item"},
            {entry["category"] for entry in entries},
        )

        stable = fixture.replace(
            "return PhGetString(PH_AUTO(PhLoadUiString(module, Entry->ResourceId, NULL)));",
            "return PhGetStringOrDefault(HardwareDevicesGetUiStringObject(Entry->ResourceId), Entry->ColumnName);",
        )
        with tempfile.NamedTemporaryFile("w", suffix=".c", encoding="utf-8") as source:
            source.write(stable)
            source.flush()
            entries = []
            self.audit.scan_c_file(source.name, entries)

        self.assertEqual(
            {
                ("c_treenew_col", "Manufacturer"),
                ("c_listview_item", "Manufacturer"),
                ("c_listview_group_item", "Manufacturer"),
            },
            {(entry["category"], entry["english"]) for entry in entries},
        )

        helper_mutations = {
            "deleted_fallback": stable.replace(
                "return PhGetStringOrDefault(HardwareDevicesGetUiStringObject(Entry->ResourceId), Entry->ColumnName);",
                "return HardwareDevicesGetUiString(Entry->ResourceId);",
            ),
            "nullable_getter": stable.replace(
                "return PhGetStringOrDefault(HardwareDevicesGetUiStringObject(Entry->ResourceId), Entry->ColumnName);",
                "return PhGetString(HardwareDevicesGetUiStringObject(Entry->ResourceId));",
            ),
            "wrong_fallback_field": stable.replace(
                "Entry->ColumnName);",
                "Entry->OtherName);",
            ),
        }
        for mutation_name, mutated in helper_mutations.items():
            with self.subTest(mutation=mutation_name):
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".c", encoding="utf-8"
                ) as source:
                    source.write(mutated)
                    source.flush()
                    entries = []
                    self.audit.scan_c_file(source.name, entries)
                self.assertEqual(6, len(entries))


if __name__ == "__main__":
    unittest.main()
