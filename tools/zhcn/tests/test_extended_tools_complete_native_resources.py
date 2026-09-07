import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
EXTENDED_SERVICES_ROOT = REPO_ROOT / "plugins" / "ExtendedServices"
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCE_DATA = r"""
IDS_ET_PROCESS_COLUMN_DISK_READS|61397|Disk reads|磁盘读取数
IDS_ET_PROCESS_COLUMN_DISK_WRITES|61398|Disk writes|磁盘写入数
IDS_ET_PROCESS_COLUMN_DISK_READ_BYTES|61399|Disk read bytes|磁盘读取字节数
IDS_ET_PROCESS_COLUMN_DISK_WRITE_BYTES|61400|Disk write bytes|磁盘写入字节数
IDS_ET_PROCESS_COLUMN_DISK_TOTAL_BYTES|61401|Disk total bytes|磁盘总字节数
IDS_ET_PROCESS_COLUMN_DISK_READS_DELTA|61402|Disk reads delta|磁盘读取数增量
IDS_ET_PROCESS_COLUMN_DISK_WRITES_DELTA|61403|Disk writes delta|磁盘写入数增量
IDS_ET_PROCESS_COLUMN_DISK_READ_BYTES_DELTA|61404|Disk read bytes delta|磁盘读取字节数增量
IDS_ET_PROCESS_COLUMN_DISK_WRITE_BYTES_DELTA|61405|Disk write bytes delta|磁盘写入字节数增量
IDS_ET_PROCESS_COLUMN_DISK_TOTAL_BYTES_DELTA|61406|Disk total bytes delta|磁盘总字节数增量
IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVES|61407|Network receives|网络接收数
IDS_ET_PROCESS_COLUMN_NETWORK_SENDS|61408|Network sends|网络发送数
IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_BYTES|61409|Network receive bytes|网络接收字节数
IDS_ET_PROCESS_COLUMN_NETWORK_SEND_BYTES|61410|Network send bytes|网络发送字节数
IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_BYTES|61411|Network total bytes|网络总字节数
IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVES_DELTA|61412|Network receives delta|网络接收数增量
IDS_ET_PROCESS_COLUMN_NETWORK_SENDS_DELTA|61413|Network sends delta|网络发送数增量
IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_BYTES_DELTA|61414|Network receive bytes delta|网络接收字节数增量
IDS_ET_PROCESS_COLUMN_NETWORK_SEND_BYTES_DELTA|61415|Network send bytes delta|网络发送字节数增量
IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_BYTES_DELTA|61416|Network total bytes delta|网络总字节数增量
IDS_ET_PROCESS_COLUMN_HARD_FAULTS|61417|Hard faults|硬错误
IDS_ET_PROCESS_COLUMN_HARD_FAULTS_DELTA|61418|Hard faults delta|硬错误增量
IDS_ET_PROCESS_COLUMN_PEAK_THREADS|61419|Peak threads|峰值线程数
IDS_ET_PROCESS_COLUMN_GPU_DEDICATED_RESIDENT|61420|GPU dedicated bytes (resident)|GPU 专用字节数（驻留）
IDS_ET_PROCESS_COLUMN_GPU_SHARED_RESIDENT|61421|GPU shared bytes (resident)|GPU 共享字节数（驻留）
IDS_ET_PROCESS_COLUMN_DISK_READ_RATE|61422|Disk read rate|磁盘读取速率
IDS_ET_PROCESS_COLUMN_DISK_WRITE_RATE|61423|Disk write rate|磁盘写入速率
IDS_ET_PROCESS_COLUMN_DISK_TOTAL_RATE|61424|Disk total rate|磁盘总速率
IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_RATE|61425|Network receive rate|网络接收速率
IDS_ET_PROCESS_COLUMN_NETWORK_SEND_RATE|61426|Network send rate|网络发送速率
IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_RATE|61427|Network total rate|网络总速率
IDS_ET_PROCESS_COLUMN_FPS|61428|FPS|FPS
IDS_ET_PROCESS_COLUMN_NPU_DEDICATED_RESIDENT|61429|NPU dedicated bytes (resident)|NPU 专用字节数（驻留）
IDS_ET_PROCESS_COLUMN_NPU_SHARED_RESIDENT|61430|NPU shared bytes (resident)|NPU 共享字节数（驻留）
IDS_ET_PROCESS_COLUMN_GPU_DEDICATED_COMMITTED|61431|GPU dedicated bytes (committed)|GPU 专用字节数（已提交）
IDS_ET_PROCESS_COLUMN_GPU_SHARED_COMMITTED|61432|GPU shared bytes (committed)|GPU 共享字节数（已提交）
IDS_ET_PROCESS_COLUMN_NPU_DEDICATED_COMMITTED|61433|NPU dedicated bytes (committed)|NPU 专用字节数（已提交）
IDS_ET_PROCESS_COLUMN_NPU_SHARED_COMMITTED|61434|NPU shared bytes (committed)|NPU 共享字节数（已提交）
IDS_ET_PROCESS_COLUMN_FIREWALL_ALLOWS|61435|Firewall allows|防火墙允许数
IDS_ET_PROCESS_COLUMN_FIREWALL_BLOCKS|61436|Firewall blocks|防火墙阻止数
IDS_ET_PROCESS_COLUMN_FIREWALL_ALLOWS_DELTA|61437|Firewall allows delta|防火墙允许数增量
IDS_ET_PROCESS_COLUMN_FIREWALL_BLOCKS_DELTA|61438|Firewall blocks delta|防火墙阻止数增量
IDS_ET_NETWORK_COLUMN_RECEIVES_DELTA|61439|Receives delta|接收数增量
IDS_ET_NETWORK_COLUMN_SENDS_DELTA|61440|Sends delta|发送数增量
IDS_ET_NETWORK_COLUMN_FIREWALL_STATUS|61441|Firewall status|防火墙状态
IDS_ET_NETWORK_COLUMN_RECEIVE_RATE|61442|Receive rate|接收速率
IDS_ET_NETWORK_COLUMN_SEND_RATE|61443|Send rate|发送速率
IDS_ET_MAIN_MENU_SYSTEM|61444|&System|系统(&S)
IDS_ET_MAIN_MENU_POOL_TABLE|61445|Poo&l Table|内存池表(&L)
IDS_ET_MAIN_MENU_SMBIOS|61446|SM&BIOS|SMBIOS(&B)
IDS_ET_MAIN_MENU_ACPI_TABLES|61447|&ACPI Tables|ACPI 表(&A)
IDS_ET_MAIN_MENU_FIRMWARE_TABLE|61448|Firm&ware Table|固件表(&W)
IDS_ET_MAIN_MENU_TPM|61449|&Trusted Platform Module|可信平台模块(&T)
IDS_ET_MAIN_MENU_BOOT_CONFIGURATION_LOG|61450|Boot Configuration &Log|启动配置日志(&L)
IDS_ET_MAIN_MENU_POWER_FORECAST|61451|Power &Forecast|电源预测(&F)
IDS_ET_MAIN_MENU_CACHE_LATENCY|61452|Cache &Latency|缓存延迟(&L)
IDS_ET_MAIN_MENU_NAMED_PIPES|61453|&Named Pipes|命名管道(&N)
IDS_ET_PROCESS_MENU_UNLOADED_MODULES|61454|&Unloaded modules|已卸载模块(&U)
IDS_ET_PROCESS_MENU_WS_WATCH|61455|&WS watch|工作集监视(&W)
IDS_ET_MENU_WAIT_CHAIN_TRAVERSAL|61456|Wait Chain Tra&versal|等待链遍历(&V)
IDS_ET_THREAD_MENU_CANCEL_IO|61457|Ca&ncel I/O|取消 I/O(&N)
IDS_ET_MODULE_MENU_SERVICES|61458|Ser&vices|服务(&V)
IDS_ET_TAB_FIREWALL|61459|Firewall|防火墙
IDS_ET_SEARCH_DISK|61460|Search Disk|搜索磁盘
IDS_ET_SEARCH_FIREWALL|61461|Search Firewall|搜索防火墙
IDS_ET_DISK_EMPTY_ADMIN_REQUIRED|61462|Disk monitoring requires System Informer to be restarted with administrative privileges.|磁盘监控需要使用管理员权限重启 sys_info。
IDS_ET_FIREWALL_EMPTY_ADMIN_REQUIRED|61463|Firewall monitoring requires System Informer to be restarted with administrative privileges.|防火墙监控需要使用管理员权限重启 sys_info。
IDS_ET_DISK_TRACE_ERROR_PREFIX|61464|Unable to start the kernel event tracing session: |无法启动内核事件跟踪会话：
IDS_ET_FIREWALL_TRACE_ERROR_PREFIX|61465|Unable to start the firewall event tracing session: |无法启动防火墙事件跟踪会话：
IDS_ET_MINI_GPU_MEMORY|61466|GPU Memory|GPU 内存
IDS_ET_GPU_ADAPTER_COLUMN_FORMAT|61467|GPU %lu|GPU %lu
IDS_ET_GPU_NODE_COLUMN_NAMED_FORMAT|61468|GPU %lu node %lu (%s)|GPU %lu 节点 %lu（%s）
IDS_ET_GPU_NODE_COLUMN_FORMAT|61469|GPU %lu node %lu|GPU %lu 节点 %lu
""".strip()
RESOURCES = [tuple(line.split("|", 3)) for line in RESOURCE_DATA.splitlines()]

TREE_ROUTES = r"""
ETPRTNC_DISKREADS|IDS_ET_PROCESS_COLUMN_DISK_READS
ETPRTNC_DISKWRITES|IDS_ET_PROCESS_COLUMN_DISK_WRITES
ETPRTNC_DISKREADBYTES|IDS_ET_PROCESS_COLUMN_DISK_READ_BYTES
ETPRTNC_DISKWRITEBYTES|IDS_ET_PROCESS_COLUMN_DISK_WRITE_BYTES
ETPRTNC_DISKTOTALBYTES|IDS_ET_PROCESS_COLUMN_DISK_TOTAL_BYTES
ETPRTNC_DISKREADSDELTA|IDS_ET_PROCESS_COLUMN_DISK_READS_DELTA
ETPRTNC_DISKWRITESDELTA|IDS_ET_PROCESS_COLUMN_DISK_WRITES_DELTA
ETPRTNC_DISKREADBYTESDELTA|IDS_ET_PROCESS_COLUMN_DISK_READ_BYTES_DELTA
ETPRTNC_DISKWRITEBYTESDELTA|IDS_ET_PROCESS_COLUMN_DISK_WRITE_BYTES_DELTA
ETPRTNC_DISKTOTALBYTESDELTA|IDS_ET_PROCESS_COLUMN_DISK_TOTAL_BYTES_DELTA
ETPRTNC_NETWORKRECEIVES|IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVES
ETPRTNC_NETWORKSENDS|IDS_ET_PROCESS_COLUMN_NETWORK_SENDS
ETPRTNC_NETWORKRECEIVEBYTES|IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_BYTES
ETPRTNC_NETWORKSENDBYTES|IDS_ET_PROCESS_COLUMN_NETWORK_SEND_BYTES
ETPRTNC_NETWORKTOTALBYTES|IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_BYTES
ETPRTNC_NETWORKRECEIVESDELTA|IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVES_DELTA
ETPRTNC_NETWORKSENDSDELTA|IDS_ET_PROCESS_COLUMN_NETWORK_SENDS_DELTA
ETPRTNC_NETWORKRECEIVEBYTESDELTA|IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_BYTES_DELTA
ETPRTNC_NETWORKSENDBYTESDELTA|IDS_ET_PROCESS_COLUMN_NETWORK_SEND_BYTES_DELTA
ETPRTNC_NETWORKTOTALBYTESDELTA|IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_BYTES_DELTA
ETPRTNC_HARDFAULTS|IDS_ET_PROCESS_COLUMN_HARD_FAULTS
ETPRTNC_HARDFAULTSDELTA|IDS_ET_PROCESS_COLUMN_HARD_FAULTS_DELTA
ETPRTNC_PEAKTHREADS|IDS_ET_PROCESS_COLUMN_PEAK_THREADS
ETPRTNC_GPUDEDICATEDBYTES|IDS_ET_PROCESS_COLUMN_GPU_DEDICATED_RESIDENT
ETPRTNC_GPUSHAREDBYTES|IDS_ET_PROCESS_COLUMN_GPU_SHARED_RESIDENT
ETPRTNC_DISKREADRATE|IDS_ET_PROCESS_COLUMN_DISK_READ_RATE
ETPRTNC_DISKWRITERATE|IDS_ET_PROCESS_COLUMN_DISK_WRITE_RATE
ETPRTNC_DISKTOTALRATE|IDS_ET_PROCESS_COLUMN_DISK_TOTAL_RATE
ETPRTNC_NETWORKRECEIVERATE|IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_RATE
ETPRTNC_NETWORKSENDRATE|IDS_ET_PROCESS_COLUMN_NETWORK_SEND_RATE
ETPRTNC_NETWORKTOTALRATE|IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_RATE
ETPRTNC_FPS|IDS_ET_PROCESS_COLUMN_FPS
ETPRTNC_NPU|IDS_ET_GROUP_NPU
ETPRTNC_NPUDEDICATEDBYTES|IDS_ET_PROCESS_COLUMN_NPU_DEDICATED_RESIDENT
ETPRTNC_NPUSHAREDBYTES|IDS_ET_PROCESS_COLUMN_NPU_SHARED_RESIDENT
ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES|IDS_ET_PROCESS_COLUMN_GPU_DEDICATED_COMMITTED
ETPRTNC_GPUSHAREDCOMMITTEDBYTES|IDS_ET_PROCESS_COLUMN_GPU_SHARED_COMMITTED
ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES|IDS_ET_PROCESS_COLUMN_NPU_DEDICATED_COMMITTED
ETPRTNC_NPUSHAREDCOMMITTEDBYTES|IDS_ET_PROCESS_COLUMN_NPU_SHARED_COMMITTED
ETPRTNC_FIREWALLALLOWS|IDS_ET_PROCESS_COLUMN_FIREWALL_ALLOWS
ETPRTNC_FIREWALLBLOCKS|IDS_ET_PROCESS_COLUMN_FIREWALL_BLOCKS
ETPRTNC_FIREWALLALLOWSDELTA|IDS_ET_PROCESS_COLUMN_FIREWALL_ALLOWS_DELTA
ETPRTNC_FIREWALLBLOCKSDELTA|IDS_ET_PROCESS_COLUMN_FIREWALL_BLOCKS_DELTA
ETNETNC_RECEIVES|IDS_ET_RECEIVES
ETNETNC_SENDS|IDS_ET_SENDS
ETNETNC_RECEIVEBYTES|IDS_ET_RECEIVE_BYTES
ETNETNC_SENDBYTES|IDS_ET_SEND_BYTES
ETNETNC_TOTALBYTES|IDS_ET_TOTAL_BYTES
ETNETNC_RECEIVESDELTA|IDS_ET_NETWORK_COLUMN_RECEIVES_DELTA
ETNETNC_SENDSDELTA|IDS_ET_NETWORK_COLUMN_SENDS_DELTA
ETNETNC_RECEIVEBYTESDELTA|IDS_ET_RECEIVE_BYTES_DELTA
ETNETNC_SENDBYTESDELTA|IDS_ET_SEND_BYTES_DELTA
ETNETNC_TOTALBYTESDELTA|IDS_ET_TOTAL_BYTES_DELTA
ETNETNC_FIREWALLSTATUS|IDS_ET_NETWORK_COLUMN_FIREWALL_STATUS
ETNETNC_RECEIVERATE|IDS_ET_NETWORK_COLUMN_RECEIVE_RATE
ETNETNC_SENDRATE|IDS_ET_NETWORK_COLUMN_SEND_RATE
ETNETNC_TOTALRATE|IDS_ET_DISK_COLUMN_TOTAL_RATE
""".strip()
EXPECTED_TREE_ROUTES = dict(line.split("|", 1) for line in TREE_ROUTES.splitlines())

MENU_ROUTES = {
    "0": "IDS_ET_MAIN_MENU_SYSTEM",
    "ID_POOL_TABLE": "IDS_ET_MAIN_MENU_POOL_TABLE",
    "ID_SMBIOS": "IDS_ET_MAIN_MENU_SMBIOS",
    "ID_ACPI": "IDS_ET_MAIN_MENU_ACPI_TABLES",
    "ID_FIRMWARE": "IDS_ET_MAIN_MENU_FIRMWARE_TABLE",
    "ID_TPM": "IDS_ET_MAIN_MENU_TPM",
    "ID_WBCL": "IDS_ET_MAIN_MENU_BOOT_CONFIGURATION_LOG",
    "ID_POWER_GRID": "IDS_ET_MAIN_MENU_POWER_FORECAST",
    "ID_CACHE_LATENCY": "IDS_ET_MAIN_MENU_CACHE_LATENCY",
    "ID_PIPE_ENUM": "IDS_ET_MAIN_MENU_NAMED_PIPES",
    "ID_REPARSE_POINTS": "IDS_ET_NTFS_REPARSE_POINTS",
    "ID_REPARSE_OBJID": "IDS_ET_NTFS_OBJECT_IDENTIFIERS",
    "ID_REPARSE_SDDL": "IDS_ET_NTFS_SECURITY_DESCRIPTORS",
    "ID_PROCESS_UNLOADEDMODULES": "IDS_ET_PROCESS_MENU_UNLOADED_MODULES",
    "ID_PROCESS_WSWATCH": "IDS_ET_PROCESS_MENU_WS_WATCH",
    "ID_PROCESS_WAITCHAIN": "IDS_ET_MENU_WAIT_CHAIN_TRAVERSAL",
    "ID_THREAD_CANCELIO": "IDS_ET_THREAD_MENU_CANCEL_IO",
    "ID_THREAD_WAITCHAIN": "IDS_ET_MENU_WAIT_CHAIN_TRAVERSAL",
    "ID_MODULE_SERVICES": "IDS_ET_MODULE_MENU_SERVICES",
}


def load_audit():
    spec = importlib.util.spec_from_file_location("et_complete_audit", REPO_ROOT / "tools" / "zhcn" / "audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path):
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class ExtendedToolsCompleteNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()
        cls.tree = (PLUGIN_ROOT / "treeext.c").read_text(encoding="utf-8-sig")
        cls.main = (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")

    def test_resources_are_contiguous_bilingual_native_owned_and_exact(self):
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        self.assertEqual(list(range(61397, 61470)), [int(row[1]) for row in RESOURCES])
        runtime_compatibility = {"Ser&vices": "服务(&V)"}

        for symbol, resource_id, en, zh in RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol), symbol)
            self.assertEqual(zh, chinese.get(symbol), symbol)
            if en in runtime_compatibility:
                self.assertEqual(runtime_compatibility[en], data["strings"].get(en), en)
                self.assertNotIn(en, data["native_strings"], en)
            else:
                self.assertEqual(zh, data["native_strings"].get(en), en)
                self.assertNotIn(en, data["strings"], en)

        self.assertEqual(470, len(english))
        self.assertEqual(470, len(chinese))
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61470$")

    def test_services_menu_keeps_exact_cross_module_runtime_consumers(self):
        services = self.audit.mask_c_comments(
            (EXTENDED_SERVICES_ROOT / "main.c").read_text(encoding="utf-8-sig")
        )
        plugin = (APP_ROOT / "plugin.c").read_text(encoding="utf-8-sig")
        emenu = (REPO_ROOT / "phlib" / "emenu.c").read_text(encoding="utf-8-sig")

        consumers = []
        for name, args, _spans, _start in self.audit.find_calls(
            services, {"PhPluginCreateEMenuItem"}
        ):
            if len(args) >= 4 and args[3].strip() == 'L"Ser&vices"':
                consumers.append((name, tuple(arg.strip() for arg in args[:5])))

        self.assertEqual(
            [
                (
                    "PhPluginCreateEMenuItem",
                    ("PluginInstance", "0", "0", 'L"Ser&vices"', "NULL"),
                ),
                (
                    "PhPluginCreateEMenuItem",
                    ("PluginInstance", "0", "0", 'L"Ser&vices"', "NULL"),
                ),
            ],
            consumers,
        )
        self.assertRegex(
            plugin,
            r"item\s*=\s*PhCreateEMenuItem\(Flags,\s*ID_PLUGIN_MENU_ITEM,\s*Text,\s*NULL,\s*pluginMenuItem\);",
        )
        self.assertRegex(
            emenu,
            r"item->Text\s*=\s*\(PWSTR\)Text;",
        )

    def test_all_57_static_tree_columns_route_enum_to_exact_stable_resource(self):
        pattern = re.compile(
            r"\{\s*(ET(?:PRT|NET)NC_[A-Z0-9_]+)\s*,\s*(IDS_ET_[A-Z0-9_]+)\s*,\s*L\"[^\"]+\"\s*,"
        )
        actual = dict(pattern.findall(self.audit.mask_c_comments(self.tree)))
        self.assertEqual(EXPECTED_TREE_ROUTES, actual)
        self.assertEqual(57, len(actual))
        self.assertRegex(
            self.tree,
            r"EtpAddTreeNewColumn\(treeNewInfo, columns\[i\]\.SubId,\s*"
            r"EtGetUiString\(columns\[i\]\.TextResourceId, columns\[i\]\.Text\)",
        )

    def test_tree_route_contract_rejects_resource_swap(self):
        mutated = self.tree.replace(
            "ETPRTNC_DISKREADS, IDS_ET_PROCESS_COLUMN_DISK_READS",
            "ETPRTNC_DISKREADS, IDS_ET_PROCESS_COLUMN_DISK_WRITES",
            1,
        )
        pattern = re.compile(r"\{\s*(ET(?:PRT|NET)NC_[A-Z0-9_]+)\s*,\s*(IDS_ET_[A-Z0-9_]+)\s*,")
        self.assertNotEqual(EXPECTED_TREE_ROUTES, dict(pattern.findall(mutated)))

    def test_gpu_dynamic_column_formats_keep_exact_arguments_and_owned_lifetime(self):
        self.assertIn(
            "PhFormatString(EtGetUiString(IDS_ET_GPU_ADAPTER_COLUMN_FORMAT, L\"GPU %lu\"), i)",
            self.tree,
        )
        self.assertIn(
            "EtGetUiString(IDS_ET_GPU_NODE_COLUMN_NAMED_FORMAT, L\"GPU %lu node %lu (%s)\")",
            self.tree,
        )
        self.assertIn(
            "EtGetUiString(IDS_ET_GPU_NODE_COLUMN_FORMAT, L\"GPU %lu node %lu\")",
            self.tree,
        )
        self.assertEqual(2, self.tree.count("PhAddItemList(EtGpuNodeColumnTextList, columnText);"))
        self.assertIn("PhDereferenceObjects(EtGpuNodeColumnTextList->Items, EtGpuNodeColumnTextList->Count);", self.tree)

    def test_all_19_plugin_menu_routes_and_system_lookup_are_exact(self):
        source = self.audit.mask_c_comments(self.main)
        actual = Counter()
        for _name, args, _spans, _start in self.audit.find_calls(source, {"PhPluginCreateEMenuItem"}):
            if len(args) < 4:
                continue
            match = re.fullmatch(r"EtGetUiString\((IDS_ET_[A-Z0-9_]+),\s*L\"(?:[^\"]|\\.)*\"\)", args[3].strip())
            if match:
                actual[(args[2].strip(), match.group(1))] += 1
        expected = Counter((command, resource) for command, resource in MENU_ROUTES.items())
        self.assertEqual(expected, actual)
        self.assertEqual(19, sum(actual.values()))
        self.assertRegex(
            source,
            r"PhFindEMenuItem\(menuInfo->Menu,\s*0,\s*"
            r"EtGetUiString\(IDS_ET_MAIN_MENU_SYSTEM, L\"&System\"\),\s*0\)",
        )

    def test_tab_identity_and_display_use_compatible_versioned_api(self):
        header = (APP_ROOT / "include" / "mainwnd.h").read_text(encoding="utf-8-sig")
        core = (APP_ROOT / "mainwnd.c").read_text(encoding="utf-8-sig")
        disk = (PLUGIN_ROOT / "disktab.c").read_text(encoding="utf-8-sig")
        firewall = (PLUGIN_ROOT / "fwtab.c").read_text(encoding="utf-8-sig")

        self.assertIn("PhPluginCreateTabPage2", header)
        self.assertIn("Reserved[0] = (PVOID)DisplayName;", header)
        self.assertIn("return PhPluginCreateTabPage(Page);", header)
        self.assertRegex(core, r"displayName\s*=\s*Template->Reserved\[0\]\s*\?[^;]+:\s*&page->Name;")
        self.assertIn("static CONST PH_STRINGREF DiskPageText = PH_STRINGREF_INIT(L\"Disk\");", disk)
        self.assertIn("CONST PH_STRINGREF FwTreePageText = PH_STRINGREF_INIT(L\"Firewall\");", firewall)
        self.assertIn("PhPluginCreateTabPage2(&page, &DiskPageDisplayText)", disk)
        self.assertIn("PhPluginCreateTabPage2(&page, &FwTreePageDisplayText)", firewall)

    def test_mini_identity_display_and_sysinfo_identity_are_separate(self):
        public = (APP_ROOT / "include" / "phplug.h").read_text(encoding="utf-8-sig")
        private = (APP_ROOT / "include" / "miniinfo.h").read_text(encoding="utf-8-sig")
        core = (APP_ROOT / "miniinfo.c").read_text(encoding="utf-8-sig")
        self.assertIn("PPH_MINIINFO_CREATE_LIST_SECTION2 CreateListSection2;", public)
        self.assertNotIn("PH_STRINGREF DisplayName;", private)
        self.assertIn("section.Reserved1[0] = (PVOID)DisplayName;", core)
        self.assertIn("section->Reserved1[0] = Template->Reserved1[0];", core)
        self.assertIn("pointers.CreateListSection2 = PhMipCreateListSection2;", core)
        self.assertIn("PhMipCreateListSection2(Name, Name, Flags, Template)", core)
        self.assertIn("PhConcatStringRef2(&DownArrowPrefix, &displayName)", core)

        routes = {
            "gpumini.c": (("GPU", "IDS_ET_GROUP_GPU"), ("GPU Memory", "IDS_ET_MINI_GPU_MEMORY")),
            "npumini.c": (("NPU", "IDS_ET_GROUP_NPU"),),
            "etwmini.c": (("Disk", "IDS_ET_SECTION_DISK"), ("Network", "IDS_ET_SECTION_NETWORK")),
        }
        for file_name, pairs in routes.items():
            source = (PLUGIN_ROOT / file_name).read_text(encoding="utf-8-sig")
            for identity, resource in pairs:
                self.assertRegex(
                    source,
                    rf'CreateListSection2\(L"{re.escape(identity)}",\s*EtGetUiString\({resource},\s*L"{re.escape(identity)}"\)',
                )

        etwsys = (PLUGIN_ROOT / "etwsys.c").read_text(encoding="utf-8-sig")
        self.assertEqual(1, etwsys.count("PhInitializeStringRef(&section.Name, L\"Disk\");"))
        self.assertEqual(1, etwsys.count("PhInitializeStringRef(&section.Name, L\"Network\");"))
        self.assertIn("drawPanel->Title = PhCreateString(EtGetUiString(IDS_ET_SECTION_DISK, L\"Disk\"));", etwsys)
        self.assertIn("drawPanel->Title = PhCreateString(EtGetUiString(IDS_ET_SECTION_NETWORK, L\"Network\"));", etwsys)

        icon = (PLUGIN_ROOT / "iconext.c").read_text(encoding="utf-8-sig")
        for identity in ("GPU", "GPU Memory", "NPU", "Disk", "Network"):
            self.assertIn(f'data->SectionName = L"{identity}";', icon)

    def test_search_empty_and_error_text_use_stable_plugin_resources(self):
        disk = (PLUGIN_ROOT / "disktab.c").read_text(encoding="utf-8-sig")
        firewall = (PLUGIN_ROOT / "fwtab.c").read_text(encoding="utf-8-sig")
        for source, prefix, search_id, empty_id, error_id in (
            (disk, "Disk", "IDS_ET_SEARCH_DISK", "IDS_ET_DISK_EMPTY_ADMIN_REQUIRED", "IDS_ET_DISK_TRACE_ERROR_PREFIX"),
            (firewall, "FwTree", "IDS_ET_SEARCH_FIREWALL", "IDS_ET_FIREWALL_EMPTY_ADMIN_REQUIRED", "IDS_ET_FIREWALL_TRACE_ERROR_PREFIX"),
        ):
            self.assertRegex(source, rf"PhInitializeStringRefLongHint\(&{prefix}BannerText,\s*EtGetUiString\({search_id},")
            self.assertRegex(source, rf"PhInitializeStringRefLongHint\(&{prefix}EmptyText,\s*EtGetUiString\({empty_id},")
            self.assertEqual(2, source.count(f"EtGetUiString({error_id},"))
            self.assertNotRegex(source, rf"PH_AUTO[^\n]*{search_id}|PH_AUTO[^\n]*{empty_id}")

    def test_only_nine_reviewed_technical_runtime_formats_remain(self):
        entries = []
        for path in PLUGIN_ROOT.rglob("*.c"):
            self.audit.scan_c_file(str(path), entries)
        actual = {entry["english"] for entry in entries if entry["category"] == "c_runtime_composed"}
        self.assertEqual(
            {"WDDM %lu.%lu", "%I64u MHz", "%lu%%", "%.1f°F (%lu°C)", "%lu°C", "%s%s%s", "%lu MB", "%I64u (0x%I64x)", "0x%08lx"},
            actual,
        )


if __name__ == "__main__":
    unittest.main()
