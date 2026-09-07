#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


# symbol | id | English | zh-CN | translation owner
RESOURCE_DATA = r"""
IDS_ET_POWER_GRID_NO_FORECAST|61200|No forecast data available.|无可用的预测数据。|native_strings
IDS_ET_SECTION_DISK|61201|Disk|磁盘|strings
IDS_ET_SECTION_NETWORK|61202|Network|网络|strings
IDS_ET_STATUS_YES|61203|Yes|是|native_strings
IDS_ET_STATUS_NO|61204|No|否|native_strings
IDS_ET_STATUS_TRUE|61205|True|真|native_strings
IDS_ET_STATUS_FALSE|61206|False|假|native_strings
IDS_ET_POOL_NON_PAGED|61207|Non Paged|非分页池|native_strings
IDS_ET_POOL_PAGED|61208|Paged|分页池|native_strings
IDS_ET_POOL_NON_PAGED_NX|61209|Non Paged NX|非分页池 NX|native_strings
IDS_ET_POOL_PAGED_SESSION_NX|61210|Paged Session NX|会话分页池 NX|native_strings
IDS_ET_HANDLE_PROTECTED|61211|Protected|受保护|strings
IDS_ET_HANDLE_INHERIT|61212|Inherit|可继承|native_strings
IDS_ET_HANDLE_PROTECTED_INHERIT|61213|Protected, Inherit|受保护，可继承|native_strings
IDS_ET_HANDLES_BY_TYPE|61214|By type:|按类型：|native_strings
IDS_ET_NTFS_SECURITY_ID|61215|NTFS SecurityID|NTFS 安全 ID|native_strings
IDS_ET_NTFS_REPARSE_POINTS|61216|NTFS Reparse Points|NTFS 重解析点|native_strings
IDS_ET_NTFS_OBJECT_IDENTIFIERS|61217|NTFS Object Identifiers|NTFS 对象标识符|native_strings
IDS_ET_NTFS_SECURITY_DESCRIPTORS|61218|NTFS Security Descriptors|NTFS 安全描述符|native_strings
IDS_ET_TPM_READ_WRITE|61219|Read/Write|读取/写入|native_strings
IDS_ET_TPM_READ|61220|Read|读取|strings
IDS_ET_TPM_WRITE|61221|Write|写入|strings
IDS_ET_TPM_NONE|61222|None|无|strings
IDS_ET_LARGE_ALLOCATIONS_TITLE_FORMAT|61223|Large Allocations (%s)|大型分配（%s）|native_strings
IDS_ET_OBJECTS_CURRENT_DIRECTORY_FORMAT|61224|Objects in current directory: %s|当前目录中的对象数：%s|native_strings
IDS_ET_MODULE_SERVICES_PROCESS_FORMAT|61225|Services referencing %s in %s (%lu):|引用 %s 的服务（进程：%s，PID：%lu）：|native_strings
IDS_ET_MODULE_SERVICES_FORMAT|61226|Services referencing %s:|引用 %s 的服务：|native_strings
IDS_ET_TPM_INDEX_TITLE_FORMAT|61227|TPM index 0x%08lx|TPM 索引 0x%08lx|native_strings
IDS_ET_WORKER_THREAD_START_FORMAT|61228|Worker Thread Start: %s|工作线程入口：%s|native_strings
IDS_ET_WORKER_THREAD_CONTEXT_FORMAT|61229|Worker Thread Context: %s|工作线程上下文：%s|native_strings
""".strip()


NEW_RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in (
        line.split("|") for line in RESOURCE_DATA.splitlines()
    )
]


REUSED_RESOURCES = (
    ("IDS_ET_GROUP_GPU", 61104, "GPU", "GPU", "strings"),
    ("IDS_ET_GROUP_NPU", 61107, "NPU", "NPU", "strings"),
    ("IDS_ET_STATE_ACTIVE", 61120, "Active", "活动", "native_strings"),
)


# file | symbol | fallback | exact number of migrated source occurrences
FIXED_ROUTE_DATA = r"""
pwrgrid.c|IDS_ET_POWER_GRID_NO_FORECAST|No forecast data available.|1
pwrgrid.c|IDS_ET_STATE_ACTIVE|Active|1
etwsys.c|IDS_ET_SECTION_DISK|Disk|1
etwsys.c|IDS_ET_SECTION_NETWORK|Network|1
gpusys.c|IDS_ET_GROUP_GPU|GPU|2
npusys.c|IDS_ET_GROUP_NPU|NPU|2
pooldialogbig.c|IDS_ET_STATUS_YES|Yes|1
pooldialogbig.c|IDS_ET_STATUS_NO|No|1
objprp.c|IDS_ET_STATUS_TRUE|True|3
objprp.c|IDS_ET_STATUS_FALSE|False|3
objprp.c|IDS_ET_POOL_NON_PAGED|Non Paged|1
objprp.c|IDS_ET_POOL_PAGED|Paged|1
objprp.c|IDS_ET_POOL_NON_PAGED_NX|Non Paged NX|1
objprp.c|IDS_ET_POOL_PAGED_SESSION_NX|Paged Session NX|1
objprp.c|IDS_ET_HANDLE_PROTECTED|Protected|2
objprp.c|IDS_ET_HANDLE_INHERIT|Inherit|2
objprp.c|IDS_ET_HANDLE_PROTECTED_INHERIT|Protected, Inherit|2
objprp.c|IDS_ET_HANDLES_BY_TYPE|By type:|1
reparse.c|IDS_ET_NTFS_SECURITY_ID|NTFS SecurityID|1
reparse.c|IDS_ET_NTFS_REPARSE_POINTS|NTFS Reparse Points|1
reparse.c|IDS_ET_NTFS_OBJECT_IDENTIFIERS|NTFS Object Identifiers|1
reparse.c|IDS_ET_NTFS_SECURITY_DESCRIPTORS|NTFS Security Descriptors|1
tpm.c|IDS_ET_TPM_READ_WRITE|Read/Write|3
tpm.c|IDS_ET_TPM_READ|Read|3
tpm.c|IDS_ET_TPM_WRITE|Write|3
tpm.c|IDS_ET_TPM_NONE|None|3
""".strip()


FIXED_ROUTES = [
    (filename, symbol, fallback, int(count))
    for filename, symbol, fallback, count in (
        line.split("|") for line in FIXED_ROUTE_DATA.splitlines()
    )
]


FORMAT_ROUTES = (
    ("pooldialogbig.c", "IDS_ET_LARGE_ALLOCATIONS_TITLE_FORMAT", "Large Allocations (%s)", 1),
    ("objmgr.c", "IDS_ET_OBJECTS_CURRENT_DIRECTORY_FORMAT", "Objects in current directory: %s", 2),
    ("modsrv.c", "IDS_ET_MODULE_SERVICES_PROCESS_FORMAT", "Services referencing %s in %s (%lu):", 1),
    ("modsrv.c", "IDS_ET_MODULE_SERVICES_FORMAT", "Services referencing %s:", 1),
    ("tpm_editor.c", "IDS_ET_TPM_INDEX_TITLE_FORMAT", "TPM index 0x%08lx", 1),
    ("objprp.c", "IDS_ET_WORKER_THREAD_START_FORMAT", "Worker Thread Start: %s", 2),
    ("objprp.c", "IDS_ET_WORKER_THREAD_CONTEXT_FORMAT", "Worker Thread Context: %s", 1),
)


TECHNICAL_FORMATS = {
    ("gpudetails.c", "EtpGpuQueryAdapterPerfInfo", "%.1f\\u00b0F (%lu\\u00b0C)"): 1,
    ("npudetails.c", "EtpNpuQueryAdapterPerfInfo", "%.1f\\u00b0F (%lu\\u00b0C)"): 1,
    ("gpudetails.c", "EtpGpuQueryAdapterPerfInfo", "%I64u MHz"): 1,
    ("npudetails.c", "EtpNpuQueryAdapterPerfInfo", "%I64u MHz"): 1,
    ("gpudetails.c", "EtpGpuQueryAdapterPerfInfo", "%lu%%"): 1,
    ("npudetails.c", "EtpNpuQueryAdapterPerfInfo", "%lu%%"): 1,
    ("gpudetails.c", "EtpGpuQueryAdapterPerfInfo", "%lu\\u00b0C"): 1,
    ("npudetails.c", "EtpNpuQueryAdapterPerfInfo", "%lu\\u00b0C"): 1,
    ("objprp.c", "EtpEnumDesktopsCallback", "%lu MB"): 1,
    ("objprp.c", "EtHandlePropertiesWindowInitialized", "%s%s%s"): 1,
    ("reparse.c", "EtReparseDlgProc", "%I64u (0x%I64x)"): 2,
    ("tpm.c", "EtEnumerateTpmEntries", "0x%08lx"): 1,
    ("wbcl.c", "EtWbclAddEntry", "0x%08lx"): 1,
    ("gpudetails.c", "EtpGpuQueryAdapterDriverModel", "WDDM %lu.%lu"): 1,
    ("npudetails.c", "EtpNpuQueryAdapterDriverModel", "WDDM %lu.%lu"): 1,
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_et_window_runtime", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_module()


def source_text(filename):
    return AUDIT.mask_c_comments(
        (PLUGIN_ROOT / filename).read_text(encoding="utf-8-sig")
    )


def compact(value):
    return re.sub(r"\s+", "", value)


def function_body(text, function_name):
    match = re.search(rf"\b{re.escape(function_name)}\s*\([^;]*?\)\s*\{{", text, re.S)
    if not match:
        raise AssertionError(f"function not found: {function_name}")

    start = match.end() - 1
    depth = 0
    for offset in range(start, len(text)):
        if text[offset] == "{":
            depth += 1
        elif text[offset] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:offset]
    raise AssertionError(f"unterminated function: {function_name}")


def parse_defines():
    header = (PLUGIN_ROOT / "resource.h").read_text(encoding="utf-8-sig")
    defines = {
        symbol: int(value)
        for symbol, value in re.findall(
            r"(?m)^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)$", header
        )
    }
    return defines, header


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


class ExtendedToolsWindowRuntimeResourceTests(unittest.TestCase):
    def test_resource_ids_rc_json_cache_and_ci_are_exact(self):
        defines, header = parse_defines()
        english = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.zh-cn.rc")
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        self.assertEqual([row[1] for row in NEW_RESOURCES], list(range(61200, 61230)))
        self.assertEqual(sorted(defines.values()), list(range(61000, 61471)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 471)
        self.assertEqual(len(chinese), 471)

        for symbol, resource_id, en, zh, owner in NEW_RESOURCES + list(REUSED_RESOURCES):
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(data[owner].get(en), zh)
                other = "strings" if owner == "native_strings" else "native_strings"
                self.assertNotIn(en, data[other])

        self.assertRegex(
            header,
            r"(?m)^#define IDS_ET_CACHED_LAST\s+IDS_ET_SEARCH_NAMED_PIPES$",
        )
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+61471$")

        workflow = (REPO_ROOT / ".github/workflows/zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("plugins\\ExtendedTools.dll=471"), 2)
        self.assertNotIn("plugins\\ExtendedTools.dll=200", workflow)

    def test_all_43_visible_fixed_text_occurrences_use_the_exact_resource(self):
        self.assertEqual(sum(row[3] for row in FIXED_ROUTES), 43)

        for filename, symbol, fallback, expected_count in FIXED_ROUTES:
            with self.subTest(filename=filename, symbol=symbol):
                source = source_text(filename)
                actual = len(
                    re.findall(
                        rf'EtGetUiString\(\s*{re.escape(symbol)}\s*,\s*'
                        rf'L"{re.escape(fallback)}"\s*\)',
                        source,
                    )
                )
                self.assertEqual(actual, expected_count)

        pwrgrid = compact(source_text("pwrgrid.c"))
        self.assertIn(
            compact(
                'if (!Summary || Summary->TotalBlocks == 0) {'
                'SetWindowText(SummaryHandle, EtGetUiString('
                'IDS_ET_POWER_GRID_NO_FORECAST, L"No forecast data available."));'
                'return;}'
            ),
            pwrgrid,
        )
        self.assertIn(
            compact(
                'if (param->ActiveFlag) { PhSetListViewSubItem('
                'context->ListViewHandle, index, 4, '
                'EtGetUiString(IDS_ET_STATE_ACTIVE, L"Active")); } else {'
            ),
            pwrgrid,
        )

        etwsys = compact(source_text("etwsys.c"))
        self.assertIn(
            compact('PhInitializeStringRef(&section.Name, L"Disk");'),
            etwsys,
        )
        self.assertIn(
            compact('drawPanel->Title = PhCreateString(EtGetUiString(IDS_ET_SECTION_DISK, L"Disk"));'),
            etwsys,
        )
        self.assertIn(
            compact('PhInitializeStringRef(&section.Name, L"Network");'),
            etwsys,
        )
        self.assertIn(
            compact('drawPanel->Title = PhCreateString(EtGetUiString(IDS_ET_SECTION_NETWORK, L"Network"));'),
            etwsys,
        )

        gpu = compact(source_text("gpusys.c"))
        self.assertIn(
            compact('PhInitializeStringRef(&section.Name, EtGetUiString(IDS_ET_GROUP_GPU, L"GPU"));'),
            gpu,
        )
        self.assertIn(
            compact('drawPanel->Title = PhCreateString(EtGetUiString(IDS_ET_GROUP_GPU, L"GPU"));'),
            gpu,
        )

        npu = compact(source_text("npusys.c"))
        self.assertIn(
            compact('PhInitializeStringRef(&section.Name, EtGetUiString(IDS_ET_GROUP_NPU, L"NPU"));'),
            npu,
        )
        self.assertIn(
            compact('drawPanel->Title = PhCreateString(EtGetUiString(IDS_ET_GROUP_NPU, L"NPU"));'),
            npu,
        )

        iconext = compact(source_text("iconext.c"))
        for stable_name in ("GPU", "NPU", "Disk", "Network"):
            self.assertEqual(iconext.count(f'data->SectionName=L"{stable_name}";'), 1)
            self.assertEqual(
                iconext.count(f'PhShowSystemInformationDialog(L"{stable_name}");'),
                1,
            )

    def test_boolean_pool_handle_and_tpm_branches_are_exact(self):
        pool = compact(function_body(source_text("pooldialogbig.c"), "EtUpdateBigPoolTable"))
        yes_call = compact(
            'PhSetListViewSubItem(Context->ListViewHandle, itemIndex, 2, '
            'EtGetUiString(IDS_ET_STATUS_YES, L"Yes"));'
        )
        no_call = compact(
            'PhSetListViewSubItem(Context->ListViewHandle, itemIndex, 2, '
            'EtGetUiString(IDS_ET_STATUS_NO, L"No"));'
        )

        def assert_pool_routes(value):
            self.assertIn(f'if(poolTagInfo.NonPaged){{{yes_call}}}else{{{no_call}}}', value)

        assert_pool_routes(pool)
        swapped_pool = pool.replace(yes_call, "__YES_CALL__", 1)
        swapped_pool = swapped_pool.replace(no_call, yes_call, 1)
        swapped_pool = swapped_pool.replace("__YES_CALL__", no_call, 1)
        with self.assertRaises(AssertionError):
            assert_pool_routes(swapped_pool)

        objprp = compact(source_text("objprp.c"))

        self.assertEqual(
            objprp.count(
                '?EtGetUiString(IDS_ET_STATUS_TRUE,L"True"):'
                'EtGetUiString(IDS_ET_STATUS_FALSE,L"False")'
            ),
            3,
        )

        pool_cases = (
            ("NonPagedPool", "IDS_ET_POOL_NON_PAGED", "Non Paged"),
            ("PagedPool", "IDS_ET_POOL_PAGED", "Paged"),
            ("NonPagedPoolNx", "IDS_ET_POOL_NON_PAGED_NX", "Non Paged NX"),
            ("PagedPoolSessionNx", "IDS_ET_POOL_PAGED_SESSION_NX", "Paged Session NX"),
        )
        for case, symbol, fallback in pool_cases:
            self.assertIn(
                compact(
                    f'case {case}: poolTypeString = EtGetUiString('
                    f'{symbol}, L"{fallback}"); break;'
                ),
                objprp,
            )

        self.assertIn(
            compact(
                'if (isTypeObject) PhSetDialogItemText('
                'Context->WindowHandle, IDC_OBJ_HANDLESBYNAME_L, '
                'EtGetUiString(IDS_ET_HANDLES_BY_TYPE, L"By type:"));'
            ),
            objprp,
        )

        handle_cases = (
            ("OBJ_PROTECT_CLOSE", "IDS_ET_HANDLE_PROTECTED", "Protected"),
            ("OBJ_INHERIT", "IDS_ET_HANDLE_INHERIT", "Inherit"),
            (
                "OBJ_PROTECT_CLOSE|OBJ_INHERIT",
                "IDS_ET_HANDLE_PROTECTED_INHERIT",
                "Protected, Inherit",
            ),
        )
        for case, symbol, fallback in handle_cases:
            for context_name in ("Context", "context"):
                self.assertEqual(
                    objprp.count(
                        compact(
                            f'case {case}: PhSetListViewSubItem('
                            f'{context_name}->ListViewHandle, lvItemIndex, ETHNLVC_ATTRIBUTES, '
                            f'EtGetUiString({symbol}, L"{fallback}"));'
                        )
                    ),
                    1,
                    msg=f"missing {context_name} route for {case}",
                )

        tpm = compact(source_text("tpm.c"))
        def assert_tpm_routes(value):
            for prefix, column in (("OWNER", 2), ("AUTH", 3), ("PP", 4)):
                read_mask = f"TPMA_NV_{prefix}READ"
                write_mask = f"TPMA_NV_{prefix}WRITE"
                self.assertIn(
                    compact(
                        f'if ((attributes & ({read_mask} | {write_mask})) == '
                        f'({read_mask} | {write_mask})) '
                        f'PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, {column}, '
                        'EtGetUiString(IDS_ET_TPM_READ_WRITE, L"Read/Write")); '
                        f'else if ((attributes & {read_mask}) == {read_mask}) '
                        f'PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, {column}, '
                        'EtGetUiString(IDS_ET_TPM_READ, L"Read")); '
                        f'else if ((attributes & {write_mask}) == {write_mask}) '
                        f'PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, {column}, '
                        'EtGetUiString(IDS_ET_TPM_WRITE, L"Write")); '
                        f'else PhSetListViewSubItem(Context->ListViewHandle, lvItemIndex, {column}, '
                        'EtGetUiString(IDS_ET_TPM_NONE, L"None"));'
                    ),
                    value,
                )

        assert_tpm_routes(tpm)
        read_call = 'EtGetUiString(IDS_ET_TPM_READ,L"Read")'
        write_call = 'EtGetUiString(IDS_ET_TPM_WRITE,L"Write")'
        swapped_tpm = tpm.replace(read_call, "__READ_CALL__", 1)
        swapped_tpm = swapped_tpm.replace(write_call, read_call, 1)
        swapped_tpm = swapped_tpm.replace("__READ_CALL__", write_call, 1)
        with self.assertRaises(AssertionError):
            assert_tpm_routes(swapped_tpm)

    def test_reparse_title_branches_are_exact(self):
        security = compact(function_body(source_text("reparse.c"), "EtFindSecurityIdsDlgProc"))
        self.assertIn(
            compact(
                'PhSetWindowText(WindowHandle, EtGetUiString('
                'IDS_ET_NTFS_SECURITY_ID, L"NTFS SecurityID"));'
            ),
            security,
        )

        reparse = compact(function_body(source_text("reparse.c"), "EtReparseDlgProc"))
        for menu_id, symbol, fallback in (
            ("ID_REPARSE_POINTS", "IDS_ET_NTFS_REPARSE_POINTS", "NTFS Reparse Points"),
            ("ID_REPARSE_OBJID", "IDS_ET_NTFS_OBJECT_IDENTIFIERS", "NTFS Object Identifiers"),
            ("ID_REPARSE_SDDL", "IDS_ET_NTFS_SECURITY_DESCRIPTORS", "NTFS Security Descriptors"),
        ):
            self.assertIn(
                compact(
                    f'case {menu_id}: PhSetWindowText(WindowHandle, EtGetUiString('
                    f'{symbol}, L"{fallback}")); break;'
                ),
                reparse,
            )

    def test_all_9_semantic_format_calls_preserve_arguments_and_ownership(self):
        self.assertEqual(sum(row[3] for row in FORMAT_ROUTES), 9)
        for filename, symbol, fallback, expected_count in FORMAT_ROUTES:
            with self.subTest(filename=filename, symbol=symbol):
                source = source_text(filename)
                self.assertEqual(
                    len(
                        re.findall(
                            rf'EtGetUiString\(\s*{symbol}\s*,\s*L"{re.escape(fallback)}"\s*\)',
                            source,
                        )
                    ),
                    expected_count,
                )

        pool = compact(function_body(source_text("pooldialogbig.c"), "EtBigPoolMonDlgProc"))
        self.assertIn(
            compact(
                'PhSetWindowText(WindowHandle, PhaFormatString(EtGetUiString('
                'IDS_ET_LARGE_ALLOCATIONS_TITLE_FORMAT, L"Large Allocations (%s)"), '
                'context->TagString)->Buffer);'
            ),
            pool,
        )

        modsrv = compact(function_body(source_text("modsrv.c"), "EtpModuleServicesDlgProc"))
        self.assertIn(
            compact(
                'message = PhFormatString(EtGetUiString(IDS_ET_MODULE_SERVICES_PROCESS_FORMAT, '
                'L"Services referencing %s in %s (%lu):"), PhGetString(context->ModuleName), '
                'PhGetStringOrEmpty(processItem->ProcessName), '
                'HandleToUlong(processItem->ProcessId));'
            ),
            modsrv,
        )
        self.assertIn(
            compact(
                'message = PhFormatString(EtGetUiString(IDS_ET_MODULE_SERVICES_FORMAT, '
                'L"Services referencing %s:"), PhGetString(context->ModuleName));'
            ),
            modsrv,
        )
        self.assertIn(compact('PhSetDialogItemText(WindowHandle, IDC_MESSAGE, PhGetString(message));'), modsrv)
        self.assertIn(compact('PhDereferenceObject(message);'), modsrv)

        for function in (
            "EtEnumCurrentDirectoryObjects",
            "EtpObjectManagerSearchControlCallback",
        ):
            objmgr = compact(function_body(source_text("objmgr.c"), function))
            self.assertIn(
                compact(
                    'PhFormatString(EtGetUiString('
                    'IDS_ET_OBJECTS_CURRENT_DIRECTORY_FORMAT, '
                    'L"Objects in current directory: %s"), string)'
                ),
                objmgr,
            )

        tpm_editor = compact(function_body(source_text("tpm_editor.c"), "EtTpmEditorDlgProc"))
        self.assertIn(
            compact(
                'PhaFormatString(EtGetUiString(IDS_ET_TPM_INDEX_TITLE_FORMAT, '
                'L"TPM index 0x%08lx"), context->Index.Value)->Buffer'
            ),
            tpm_editor,
        )

        worker = compact(function_body(source_text("objprp.c"), "EtpTpWorkerFactoryPageDlgProc"))
        self.assertEqual(
            worker.count(
                compact(
                    'PhaFormatString(EtGetUiString(IDS_ET_WORKER_THREAD_START_FORMAT, '
                    'L"Worker Thread Start: %s"),'
                )
            ),
            2,
        )
        self.assertIn(
            compact(
                'PhaFormatString(EtGetUiString(IDS_ET_WORKER_THREAD_CONTEXT_FORMAT, '
                'L"Worker Thread Context: %s"), value)->Buffer'
            ),
            worker,
        )
        self.assertIn(
            compact(
                'if (symbol) { PhSetDialogItemText(hwndDlg, IDC_WORKERTHREADSTART, '
                'PhaFormatString(EtGetUiString(IDS_ET_WORKER_THREAD_START_FORMAT, '
                'L"Worker Thread Start: %s"), symbol->Buffer)->Buffer); '
                'PhDereferenceObject(symbol); } else { '
                'PhPrintPointer(value, basicInfo.StartRoutine); '
                'PhSetDialogItemText(hwndDlg, IDC_WORKERTHREADSTART, '
                'PhaFormatString(EtGetUiString(IDS_ET_WORKER_THREAD_START_FORMAT, '
                'L"Worker Thread Start: %s"), value)->Buffer); }'
            ),
            worker,
        )

    def test_technical_formats_remain_untranslated_and_outside_resources(self):
        self.assertEqual(sum(TECHNICAL_FORMATS.values()), 16)

        for (filename, function, value), expected_count in TECHNICAL_FORMATS.items():
            with self.subTest(filename=filename, function=function, value=value):
                source = function_body(source_text(filename), function)
                self.assertEqual(
                    len(re.findall(rf'L"{re.escape(value)}"', source)),
                    expected_count,
                )
                self.assertNotRegex(
                    source,
                    rf'EtGetUiString\([^;]*L"{re.escape(value)}"',
                )

        english = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.rc")
        resource_values = set(english.values())
        for _filename, _function, value in TECHNICAL_FORMATS:
            self.assertNotIn(value.replace("\\u00b0", "°"), resource_values)

    def test_fresh_scan_removes_migrated_text_and_keeps_only_technical_formats(self):
        filenames = sorted(
            {row[0] for row in FIXED_ROUTES}
            | {row[0] for row in FORMAT_ROUTES}
            | {row[0] for row in TECHNICAL_FORMATS}
        )
        entries = []
        for filename in filenames:
            AUDIT.scan_c_file(str(PLUGIN_ROOT / filename), entries)

        migrated = (
            {row[2] for row in NEW_RESOURCES}
            | {row[2] for row in REUSED_RESOURCES}
        )
        self.assertFalse(
            {
                entry["english"]
                for entry in entries
                if entry["category"] in {"c_window_text", "c_runtime_composed"}
            }
            & migrated
        )

        actual_window_text = Counter(
            entry["english"]
            for entry in entries
            if entry["category"] == "c_window_text"
        )
        self.assertEqual(actual_window_text, Counter())

        expected = Counter()
        for (_filename, _function, value), count in TECHNICAL_FORMATS.items():
            expected[value.replace("\\u00b0", "°")] += count
        actual = Counter(
            entry["english"]
            for entry in entries
            if entry["category"] == "c_runtime_composed"
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
