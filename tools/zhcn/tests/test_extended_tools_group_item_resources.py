#!/usr/bin/env python3

from collections import Counter
import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


RESOURCE_ROWS = (
    ("IDS_ET_DEDICATED_MEMORY", 61040, "Dedicated memory", "专用内存"),
    ("IDS_ET_SHARED_MEMORY", 61041, "Shared memory", "共享内存"),
    ("IDS_ET_COMMIT_MEMORY", 61042, "Commit memory", "提交内存"),
    ("IDS_ET_TOTAL_MEMORY", 61043, "Total memory", "总内存"),
    ("IDS_ET_READS", 61044, "Reads", "读取"),
    ("IDS_ET_READ_BYTES", 61045, "Read bytes", "读取字节数"),
    ("IDS_ET_READ_BYTES_DELTA", 61046, "Read bytes delta", "读取字节数增量"),
    ("IDS_ET_WRITES", 61047, "Writes", "写入"),
    ("IDS_ET_WRITE_BYTES", 61048, "Write bytes", "写入字节数"),
    ("IDS_ET_WRITE_BYTES_DELTA", 61049, "Write bytes delta", "写入字节数增量"),
    ("IDS_ET_TOTAL", 61050, "Total", "总计"),
    ("IDS_ET_TOTAL_BYTES", 61051, "Total bytes", "总字节数"),
    ("IDS_ET_TOTAL_BYTES_DELTA", 61052, "Total bytes delta", "总字节数增量"),
    ("IDS_ET_RECEIVES", 61053, "Receives", "接收数"),
    ("IDS_ET_RECEIVE_BYTES", 61054, "Receive bytes", "接收字节数"),
    ("IDS_ET_RECEIVE_BYTES_DELTA", 61055, "Receive bytes delta", "接收字节数增量"),
    ("IDS_ET_SENDS", 61056, "Sends", "发送数"),
    ("IDS_ET_SEND_BYTES", 61057, "Send bytes", "发送字节数"),
    ("IDS_ET_SEND_BYTES_DELTA", 61058, "Send bytes delta", "发送字节数增量"),
    ("IDS_ET_VIRTUAL_MEMORY", 61059, "Virtual memory", "虚拟内存"),
    ("IDS_ET_EVICTED_BYTES", 61060, "Evicted bytes", "已逐出字节数"),
    ("IDS_ET_DMA_BUFFER_SIZE", 61061, "DMA buffer size", "DMA 缓冲区大小"),
    ("IDS_ET_DMA_ALLOCATION_LIST", 61062, "DMA allocation list", "DMA 分配列表"),
    ("IDS_ET_DMA_PATCH_LIST", 61063, "DMA patch list", "DMA 修补列表"),
    ("IDS_ET_CONTENTION_EVENTS", 61064, "Contention events", "争用事件"),
    ("IDS_ET_DISPLAY_OUTPUTS", 61065, "Display outputs", "显示输出数"),
    ("IDS_ET_OBJECT_ATTRIBUTES", 61066, "Object attributes", "对象属性"),
    ("IDS_ET_DRIVER_IMAGE", 61067, "Driver Image", "驱动程序映像"),
    ("IDS_ET_DRIVER_SERVICE_NAME", 61068, "Driver Service Name", "驱动程序服务名称"),
    ("IDS_ET_DRIVER_SIZE", 61069, "Driver Size", "驱动程序大小"),
    ("IDS_ET_DRIVER_START_ADDRESS", 61070, "Driver Start Address", "驱动程序起始地址"),
    ("IDS_ET_DRIVER_FLAGS", 61071, "Driver Flags", "驱动程序标志"),
    ("IDS_ET_LOWER_EDGE_DRIVER", 61072, "Lower-edge driver", "下层设备驱动程序"),
    ("IDS_ET_LOWER_EDGE_DRIVER_IMAGE", 61073, "Lower-edge driver image", "下层设备驱动程序映像"),
    ("IDS_ET_UPPER_EDGE_DRIVER", 61074, "Upper-edge driver", "上层设备驱动程序"),
    ("IDS_ET_UPPER_EDGE_DRIVER_IMAGE", 61075, "Upper-edge driver Image", "上层设备驱动程序映像"),
    ("IDS_ET_PNP_DEVICE_NAME", 61076, "PnP Device Name", "PnP 设备名称"),
    ("IDS_ET_TYPE", 61077, "Type", "类型"),
    ("IDS_ET_VISIBLE", 61078, "Visible", "可见"),
    ("IDS_ET_INPUT_DESKTOP", 61079, "Input desktop", "输入桌面"),
    ("IDS_ET_USER_SID", 61080, "User SID", "用户 SID"),
    ("IDS_ET_HEAP_SIZE", 61081, "Heap size", "堆大小"),
    ("IDS_ET_INDEX", 61082, "Index", "索引"),
    ("IDS_ET_OBJECTS", 61083, "Objects", "对象"),
    ("IDS_ET_HANDLES", 61084, "Handles", "句柄"),
    ("IDS_ET_PEAK_OBJECTS", 61085, "Peak Objects", "对象数峰值"),
    ("IDS_ET_PEAK_HANDLES", 61086, "Peak Handles", "句柄数峰值"),
    ("IDS_ET_POOL_TYPE", 61087, "Pool Type", "池类型"),
    ("IDS_ET_DEFAULT_PAGED_CHARGE", 61088, "Default Paged Charge", "默认分页池开销"),
    ("IDS_ET_DEFAULT_NP_CHARGE", 61089, "Default NP Charge", "默认非分页池开销"),
    ("IDS_ET_VALID_ACCESS_MASK", 61090, "Valid Access Mask", "有效访问掩码"),
    ("IDS_ET_GENERIC_READ", 61091, "Generic Read", "通用读取"),
    ("IDS_ET_GENERIC_WRITE", 61092, "Generic Write", "通用写入"),
    ("IDS_ET_GENERIC_EXECUTE", 61093, "Generic Execute", "通用执行"),
    ("IDS_ET_GENERIC_ALL", 61094, "Generic All", "通用全部"),
    ("IDS_ET_INVALID_ATTRIBUTES", 61095, "Invalid Attributes", "无效属性"),
    ("IDS_ET_SESSION_NAME", 61096, "Session Name", "会话名称"),
    ("IDS_ET_SESSION_ID", 61097, "Session ID", "会话 ID"),
    ("IDS_ET_USER_NAME", 61098, "User name", "用户名"),
    ("IDS_ET_STATE", 61099, "State", "状态"),
    ("IDS_ET_LOGON_TIME", 61100, "Logon time", "登录时间"),
    ("IDS_ET_CONNECT_TIME", 61101, "Connect time", "连接时间"),
    ("IDS_ET_DISCONNECT_TIME", 61102, "Disconnect time", "断开连接时间"),
    ("IDS_ET_LAST_INPUT_TIME", 61103, "Last input time", "上次输入时间"),
)

RUNTIME_DICTIONARY_OWNED = {
    "Dedicated memory", "Shared memory", "Commit memory", "Reads",
    "Read bytes", "Read bytes delta", "Writes", "Write bytes",
    "Write bytes delta", "Total", "Total bytes", "Receives",
    "Receive bytes", "Receive bytes delta", "Sends", "Send bytes",
    "Send bytes delta", "Type", "Visible", "Index", "Objects", "Handles",
    "Session ID", "User name", "State", "Logon time",
}

MAIN_ROUTES = (
    ("ET_PROCESS_STATISTICS_CATEGORY_GPU", "ET_PROCESS_STATISTICS_INDEX_GPUTOTALDEDICATED", "IDS_ET_DEDICATED_MEMORY", "Dedicated memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPU", "ET_PROCESS_STATISTICS_INDEX_GPUTOTALSHARED", "IDS_ET_SHARED_MEMORY", "Shared memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPU", "ET_PROCESS_STATISTICS_INDEX_GPUTOTALCOMMIT", "IDS_ET_COMMIT_MEMORY", "Commit memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPU", "ET_PROCESS_STATISTICS_INDEX_GPUTOTAL", "IDS_ET_TOTAL_MEMORY", "Total memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKREADS", "IDS_ET_READS", "Reads"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKREADBYTES", "IDS_ET_READ_BYTES", "Read bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKREADBYTESDELTA", "IDS_ET_READ_BYTES_DELTA", "Read bytes delta"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKWRITES", "IDS_ET_WRITES", "Writes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKWRITEBYTES", "IDS_ET_WRITE_BYTES", "Write bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKWRITEBYTESDELTA", "IDS_ET_WRITE_BYTES_DELTA", "Write bytes delta"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKTOTAL", "IDS_ET_TOTAL", "Total"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKTOTALBYTES", "IDS_ET_TOTAL_BYTES", "Total bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_DISK", "ET_PROCESS_STATISTICS_INDEX_DISKTOTALBYTESDELTA", "IDS_ET_TOTAL_BYTES_DELTA", "Total bytes delta"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKREADS", "IDS_ET_RECEIVES", "Receives"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKREADBYTES", "IDS_ET_RECEIVE_BYTES", "Receive bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKREADBYTESDELTA", "IDS_ET_RECEIVE_BYTES_DELTA", "Receive bytes delta"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKWRITES", "IDS_ET_SENDS", "Sends"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKWRITEBYTES", "IDS_ET_SEND_BYTES", "Send bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKWRITEBYTESDELTA", "IDS_ET_SEND_BYTES_DELTA", "Send bytes delta"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKTOTAL", "IDS_ET_TOTAL", "Total"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKTOTALBYTES", "IDS_ET_TOTAL_BYTES", "Total bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NETWORK", "ET_PROCESS_STATISTICS_INDEX_NETWORKTOTALBYTESDELTA", "IDS_ET_TOTAL_BYTES_DELTA", "Total bytes delta"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NPU", "ET_PROCESS_STATISTICS_INDEX_NPUTOTALDEDICATED", "IDS_ET_DEDICATED_MEMORY", "Dedicated memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NPU", "ET_PROCESS_STATISTICS_INDEX_NPUTOTALSHARED", "IDS_ET_SHARED_MEMORY", "Shared memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NPU", "ET_PROCESS_STATISTICS_INDEX_NPUTOTALCOMMIT", "IDS_ET_COMMIT_MEMORY", "Commit memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_NPU", "ET_PROCESS_STATISTICS_INDEX_NPUTOTAL", "IDS_ET_TOTAL_MEMORY", "Total memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUVIRTUALMEMORY", "IDS_ET_VIRTUAL_MEMORY", "Virtual memory"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUEVICTED", "IDS_ET_EVICTED_BYTES", "Evicted bytes"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUDMASIZE", "IDS_ET_DMA_BUFFER_SIZE", "DMA buffer size"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUDMAALLOCLIST", "IDS_ET_DMA_ALLOCATION_LIST", "DMA allocation list"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUDMAPATCHLIST", "IDS_ET_DMA_PATCH_LIST", "DMA patch list"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUINTERFERENCE", "IDS_ET_CONTENTION_EVENTS", "Contention events"),
    ("ET_PROCESS_STATISTICS_CATEGORY_GPUADAPTER", "ET_PROCESS_STATISTICS_INDEX_GPUVIDPNSOURCES", "IDS_ET_DISPLAY_OUTPUTS", "Display outputs"),
)

OBJ_ROUTES = (
    ("PH_PLUGIN_HANDLE_GENERAL_CATEGORY_BASICINFO", "OBJECT_GENERAL_INDEX_ATTRIBUTES", "IDS_ET_OBJECT_ATTRIBUTES", "Object attributes"),
    ("OBJECT_GENERAL_CATEGORY_DRIVER", "OBJECT_GENERAL_INDEX_DRIVERIMAGE", "IDS_ET_DRIVER_IMAGE", "Driver Image"),
    ("OBJECT_GENERAL_CATEGORY_DRIVER", "OBJECT_GENERAL_INDEX_DRIVERSERVICE", "IDS_ET_DRIVER_SERVICE_NAME", "Driver Service Name"),
    ("OBJECT_GENERAL_CATEGORY_DRIVER", "OBJECT_GENERAL_INDEX_DRIVERSIZE", "IDS_ET_DRIVER_SIZE", "Driver Size"),
    ("OBJECT_GENERAL_CATEGORY_DRIVER", "OBJECT_GENERAL_INDEX_DRIVERSTART", "IDS_ET_DRIVER_START_ADDRESS", "Driver Start Address"),
    ("OBJECT_GENERAL_CATEGORY_DRIVER", "OBJECT_GENERAL_INDEX_DRIVERFLAGS", "IDS_ET_DRIVER_FLAGS", "Driver Flags"),
    ("OBJECT_GENERAL_CATEGORY_DEVICE", "OBJECT_GENERAL_INDEX_DEVICEDRVLOW", "IDS_ET_LOWER_EDGE_DRIVER", "Lower-edge driver"),
    ("OBJECT_GENERAL_CATEGORY_DEVICE", "OBJECT_GENERAL_INDEX_DEVICEDRVLOWPATH", "IDS_ET_LOWER_EDGE_DRIVER_IMAGE", "Lower-edge driver image"),
    ("OBJECT_GENERAL_CATEGORY_DEVICE", "OBJECT_GENERAL_INDEX_DEVICEDRVHIGH", "IDS_ET_UPPER_EDGE_DRIVER", "Upper-edge driver"),
    ("OBJECT_GENERAL_CATEGORY_DEVICE", "OBJECT_GENERAL_INDEX_DEVICEDRVHIGHPATH", "IDS_ET_UPPER_EDGE_DRIVER_IMAGE", "Upper-edge driver Image"),
    ("OBJECT_GENERAL_CATEGORY_DEVICE", "OBJECT_GENERAL_INDEX_DEVICEPNPNAME", "IDS_ET_PNP_DEVICE_NAME", "PnP Device Name"),
    ("OBJECT_GENERAL_CATEGORY_WINDOWSTATION", "OBJECT_GENERAL_INDEX_WINSTATYPE", "IDS_ET_TYPE", "Type"),
    ("OBJECT_GENERAL_CATEGORY_WINDOWSTATION", "OBJECT_GENERAL_INDEX_WINSTAVISIBLE", "IDS_ET_VISIBLE", "Visible"),
    ("OBJECT_GENERAL_CATEGORY_DESKTOP", "OBJECT_GENERAL_INDEX_DESKTOPIO", "IDS_ET_INPUT_DESKTOP", "Input desktop"),
    ("OBJECT_GENERAL_CATEGORY_DESKTOP", "OBJECT_GENERAL_INDEX_DESKTOPSID", "IDS_ET_USER_SID", "User SID"),
    ("OBJECT_GENERAL_CATEGORY_DESKTOP", "OBJECT_GENERAL_INDEX_DESKTOPHEAP", "IDS_ET_HEAP_SIZE", "Heap size"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEINDEX", "IDS_ET_INDEX", "Index"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEOBJECTS", "IDS_ET_OBJECTS", "Objects"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEHANDLES", "IDS_ET_HANDLES", "Handles"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEPEAKOBJECTS", "IDS_ET_PEAK_OBJECTS", "Peak Objects"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEPEAKHANDLES", "IDS_ET_PEAK_HANDLES", "Peak Handles"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEPOOLTYPE", "IDS_ET_POOL_TYPE", "Pool Type"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPEPAGECHARGE", "IDS_ET_DEFAULT_PAGED_CHARGE", "Default Paged Charge"),
    ("OBJECT_GENERAL_CATEGORY_TYPE", "OBJECT_GENERAL_INDEX_TYPENPAGECHARGE", "IDS_ET_DEFAULT_NP_CHARGE", "Default NP Charge"),
    ("OBJECT_GENERAL_CATEGORY_TYPE_ACCESS", "OBJECT_GENERAL_INDEX_TYPEVALIDMASK", "IDS_ET_VALID_ACCESS_MASK", "Valid Access Mask"),
    ("OBJECT_GENERAL_CATEGORY_TYPE_ACCESS", "OBJECT_GENERAL_INDEX_TYPEGENERICREAD", "IDS_ET_GENERIC_READ", "Generic Read"),
    ("OBJECT_GENERAL_CATEGORY_TYPE_ACCESS", "OBJECT_GENERAL_INDEX_TYPEGENERICWRITE", "IDS_ET_GENERIC_WRITE", "Generic Write"),
    ("OBJECT_GENERAL_CATEGORY_TYPE_ACCESS", "OBJECT_GENERAL_INDEX_TYPEGENERICEXECUTE", "IDS_ET_GENERIC_EXECUTE", "Generic Execute"),
    ("OBJECT_GENERAL_CATEGORY_TYPE_ACCESS", "OBJECT_GENERAL_INDEX_TYPEGENERICALL", "IDS_ET_GENERIC_ALL", "Generic All"),
    ("OBJECT_GENERAL_CATEGORY_TYPE_ACCESS", "OBJECT_GENERAL_INDEX_TYPEINVALIDATTRIBUTES", "IDS_ET_INVALID_ATTRIBUTES", "Invalid Attributes"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONNAME", "IDS_ET_SESSION_NAME", "Session Name"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONID", "IDS_ET_SESSION_ID", "Session ID"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONUSERNAME", "IDS_ET_USER_NAME", "User name"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONSTATE", "IDS_ET_STATE", "State"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONLOGON", "IDS_ET_LOGON_TIME", "Logon time"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONCONNECT", "IDS_ET_CONNECT_TIME", "Connect time"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONDISCONNECT", "IDS_ET_DISCONNECT_TIME", "Disconnect time"),
    ("OBJECT_GENERAL_CATEGORY_SESSION", "OBJECT_GENERAL_INDEX_SESSIONLASTINPUT", "IDS_ET_LAST_INPUT_TIME", "Last input time"),
)


def load_tool(name: str):
    path = REPO_ROOT / "tools" / "zhcn" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(expression: str) -> str:
    return re.sub(r"\s+", "", expression)


class ExtendedToolsGroupItemResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_tool("audit")

    def test_resources_have_exact_ids_text_layers_and_boundaries(self) -> None:
        header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english_rc = (PLUGIN_ROOT / "ExtendedTools.rc").read_text(encoding="utf-8-sig")
        chinese_rc = (PLUGIN_ROOT / "ExtendedTools.zh-cn.rc").read_text(encoding="utf-8-sig")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        self.assertEqual(len(RESOURCE_ROWS), 64)
        self.assertEqual([row[1] for row in RESOURCE_ROWS], list(range(61040, 61104)))
        for resource_id, numeric_id, english, chinese in RESOURCE_ROWS:
            with self.subTest(resource_id=resource_id):
                self.assertRegex(header, rf"(?m)^#define\s+{resource_id}\s+{numeric_id}$")
                self.assertRegex(english_rc, rf'(?m)^\s*{resource_id}\s+"{re.escape(english)}"$')
                self.assertRegex(chinese_rc, rf'(?m)^\s*{resource_id}\s+"{re.escape(chinese)}"$')
                table = "strings" if english in RUNTIME_DICTIONARY_OWNED else "native_strings"
                other_table = "native_strings" if table == "strings" else "strings"
                self.assertEqual(translations[table].get(english), chinese)
                self.assertNotIn(english, translations[other_table])

        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_RESOURCE_VALUE\s+60043$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+61104$")
        self.assertEqual(len(re.findall(r'(?m)^\s*IDS_ET_[A-Z0-9_]+\s+"', english_rc)), 104)
        self.assertEqual(len(re.findall(r'(?m)^\s*IDS_ET_[A-Z0-9_]+\s+"', chinese_rc)), 104)

    def parse_routes(self, filename: str):
        source = self.audit.mask_c_comments(
            (PLUGIN_ROOT / filename).read_text(encoding="utf-8-sig")
        )
        routes = []
        text_pattern = re.compile(
            r'^EtGetUiString\s*\(\s*(IDS_ET_[A-Z0-9_]+)\s*,'
            r'\s*L"((?:\\.|[^"\\])*)"\s*\)$',
            re.DOTALL,
        )

        for _, args, _, call_start in self.audit.find_calls(
            source, {"PhAddListViewGroupItem"}
        ):
            self.assertEqual(len(args), 5)
            match = text_pattern.fullmatch(args[3].strip())
            self.assertIsNotNone(match, args[3])
            resource_id, fallback = match.groups()
            if filename == "main.c":
                group_match = re.fullmatch(
                    r"block->ListViewGroupCache\[\s*([A-Z0-9_]+)\s*\]",
                    args[1].strip(),
                )
                self.assertIsNotNone(group_match, args[1])
                prefix = source[max(0, call_start - 180):call_start]
                index_match = re.search(
                    r"block->ListViewRowCache\[\s*([A-Z0-9_]+)\s*\]\s*=\s*$",
                    prefix,
                )
                self.assertIsNotNone(index_match, prefix)
                self.assertEqual(normalize(args[2]), "MAXINT")
                group = group_match.group(1)
                index = index_match.group(1)
            else:
                group = normalize(args[1])
                index = normalize(args[2])
            routes.append((group, index, resource_id, fallback))

        return routes

    def test_all_71_calls_keep_their_exact_group_index_resource_and_fallback(self) -> None:
        expected = Counter(("main.c", *route) for route in MAIN_ROUTES)
        expected.update(("objprp.c", *route) for route in OBJ_ROUTES)
        actual = Counter()
        for filename in ("main.c", "objprp.c"):
            actual.update((filename, *route) for route in self.parse_routes(filename))

        self.assertEqual(sum(expected.values()), 71)
        self.assertEqual(len({row[3] for row in expected}), 64)
        self.assertEqual(actual, expected)

    def test_ui_string_helper_uses_the_plugin_resource_cache_without_auto_pool(self) -> None:
        main_source = self.audit.mask_c_comments(
            (PLUGIN_ROOT / "main.c").read_text(encoding="utf-8-sig")
        )
        obj_source = self.audit.mask_c_comments(
            (PLUGIN_ROOT / "objprp.c").read_text(encoding="utf-8-sig")
        )
        helper = main_source.split("PCWSTR EtGetUiString(", 1)[1].split(
            "_Function_class_(PH_CALLBACK_FUNCTION)", 1
        )[0]

        self.assertIn("static PH_INITONCE EtUiStringsInitOnce", main_source)
        self.assertIn("static PPH_STRING EtUiStrings[", main_source)
        self.assertRegex(
            helper,
            r"PhLoadUiString\(\s*PluginInstance->DllBase,\s*resourceId,\s*NULL\s*\)",
        )
        self.assertIn("PhGetStringOrDefault(", helper)
        self.assertIn("Fallback", helper)
        self.assertNotIn("PH_AUTO", helper)
        self.assertIn("PCWSTR EtGetUiString(", obj_source)

    def test_migrated_group_item_literals_leave_the_fresh_audit(self) -> None:
        expected_english = {row[2] for row in RESOURCE_ROWS}
        remaining = []
        for filename in ("main.c", "objprp.c"):
            entries = []
            self.audit.scan_c_file(str(PLUGIN_ROOT / filename), entries)
            remaining.extend(
                entry
                for entry in entries
                if entry["category"] == "c_listview_group_item"
                and entry["english"] in expected_english
            )
        self.assertEqual(remaining, [])

    def test_ci_requires_all_104_extended_tools_strings(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            workflow.count("bin\\Release64\\plugins\\ExtendedTools.dll=104"),
            2,
        )
        self.assertNotIn("bin\\Release64\\plugins\\ExtendedTools.dll=40", workflow)


if __name__ == "__main__":
    unittest.main()
