#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest
from collections import Counter


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PEVIEW_ROOT = REPO_ROOT / "tools" / "peview"


# symbol | id | English | zh-CN | source | group | index
#
# Duplicate rows are intentional: Characteristics and Subsystem each have two
# independent call sites that must keep using the same resource.
ROUTE_DATA = r"""
IDS_PV_FIELD_DOS_MAGIC_NUMBER|3134|Magic number|魔数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_MAGIC
IDS_PV_FIELD_DOS_LAST_PAGE_BYTES|3135|Bytes on last page of file|文件最后一页的字节数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_BYTES
IDS_PV_FIELD_DOS_PAGE_COUNT|3136|Pages in file|文件页数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_PAGES
IDS_PV_FIELD_DOS_RELOCATIONS|3137|Relocations|重定位|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_RELOCATIONS
IDS_PV_FIELD_DOS_HEADER_PARAGRAPHS|3138|Size of header in paragraphs|头大小（段落数）|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_PARAGRAPH
IDS_PV_FIELD_DOS_MIN_EXTRA_PARAGRAPHS|3139|Minimum extra paragraphs needed|所需最小附加段落数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_MINPARA
IDS_PV_FIELD_DOS_MAX_EXTRA_PARAGRAPHS|3140|Maximum extra paragraphs needed|所需最大附加段落数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_MAXPARA
IDS_PV_FIELD_DOS_INITIAL_RELATIVE_SS|3141|Initial (relative) SS value|初始（相对）SS 值|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_INITRELSS
IDS_PV_FIELD_DOS_INITIAL_SP|3142|Initial SP value|初始 SP 值|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_INITRELSP
IDS_PV_FIELD_DOS_CHECKSUM|3143|Checksum|校验和|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_CHECKSUM
IDS_PV_FIELD_DOS_INITIAL_IP|3144|Initial IP value|初始 IP 值|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_INITIP
IDS_PV_FIELD_DOS_INITIAL_RELATIVE_CS|3145|Initial (relative) CS value|初始（相对）CS 值|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_INITCS
IDS_PV_FIELD_DOS_RELOCATION_TABLE_ADDRESS|3146|File address of relocation table|重定位表文件偏移|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_RELOCADDR
IDS_PV_FIELD_DOS_OVERLAY_NUMBER|3147|Overlay number|覆盖区编号|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_OVERLAY
IDS_PV_FIELD_DOS_OEM_IDENTIFIER|3148|OEM identifier (for e_oeminfo)|OEM 标识符（供 e_oeminfo 使用）|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_OEMID
IDS_PV_FIELD_DOS_OEM_INFORMATION|3149|OEM information (e_oemid specific)|OEM 信息（由 e_oemid 指定）|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_OEMINFO
IDS_PV_FIELD_DOS_NEW_EXE_HEADER_ADDRESS|3150|File address of new exe header|新 EXE 头文件偏移|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSHDR|PVP_IMAGE_HEADER_INDEX_DOS_EXEHDRADDR
IDS_PV_FIELD_DOS_STUB_SIZE|3151|Stub size|DOS 存根大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_STUBSIZE
IDS_PV_FIELD_DOS_STUB_ENTROPY|3152|Stub entropy|DOS 存根熵|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_STUBENTROPY
IDS_PV_FIELD_DOS_STUB_HASH|3153|Stub hash|DOS 存根哈希|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_STUBHASH
IDS_PV_FIELD_RICH_HEADER_SIZE|3154|Rich size|Rich 头大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_RICHSIZE
IDS_PV_FIELD_RICH_HEADER_ENTROPY|3155|Rich entropy|Rich 头熵|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_RICHENTROPY
IDS_PV_FIELD_RICH_HEADER_HASH|3156|Rich hash|Rich 头哈希|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_RICHHASH
IDS_PV_FIELD_DOS_TOTAL_SIZE|3157|Total size|总大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_SIZE
IDS_PV_FIELD_DOS_TOTAL_ENTROPY|3158|Total entropy|总熵|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_ENTROPY
IDS_PV_FIELD_DOS_TOTAL_HASH|3159|Total hash|总哈希|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_DOSSTUB|PVP_IMAGE_HEADER_INDEX_DOS_HASH
IDS_PV_FIELD_PE_SIGNATURE|3160|Signature|签名|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_NTSIG
IDS_PV_FIELD_FILE_MACHINE|3161|Machine|机器类型|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_MACHINE
IDS_PV_FIELD_FILE_NUMBER_OF_SECTIONS|3162|NumberOfSections|节数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_SECTIONS
IDS_PV_FIELD_FILE_TIMESTAMP|3163|Timestamp|时间戳|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_TIMESTAMP
IDS_PV_FIELD_FILE_POINTER_TO_SYMBOL_TABLE|3164|PointerToSymbolTable|符号表指针|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_SYMTABLEADDR
IDS_PV_FIELD_FILE_NUMBER_OF_SYMBOLS|3165|NumberOfSymbols|符号数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_SYMTABLECOUNT
IDS_PV_FIELD_FILE_SIZE_OF_OPTIONAL_HEADER|3166|SizeOfOptionalHeader|可选头大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_OPTHDRSIZE
IDS_PV_COLUMN_CHARACTERISTICS|3030|Characteristics|特征|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_FILEHDR|PVP_IMAGE_HEADER_INDEX_FILE_CHARACTERISTICS
IDS_PV_FIELD_OPTIONAL_MAGIC|3167|Magic|魔数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_MAGIC
IDS_PV_FIELD_OPTIONAL_LINKER_VERSION|3168|LinkerVersion|链接器版本|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_LINKERVERSION
IDS_PV_FIELD_OPTIONAL_SIZE_OF_CODE|3169|SizeOfCode|代码大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFCODE
IDS_PV_FIELD_OPTIONAL_SIZE_OF_INITIALIZED_DATA|3170|SizeOfInitializedData|已初始化数据大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_INITSIZE
IDS_PV_FIELD_OPTIONAL_SIZE_OF_UNINITIALIZED_DATA|3171|SizeOfUninitializedData|未初始化数据大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_UNINITSIZE
IDS_PV_FIELD_OPTIONAL_ADDRESS_OF_ENTRY_POINT|3172|AddressOfEntryPoint|入口点地址|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_ENTRYPOINT
IDS_PV_FIELD_OPTIONAL_BASE_OF_CODE|3173|BaseOfCode|代码基址|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_BASEOFCODE
IDS_PV_FIELD_OPTIONAL_BASE_OF_DATA|3174|BaseOfData|数据基址|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_BASEOFDATA
IDS_PV_FIELD_OPTIONAL_IMAGE_BASE|3175|ImageBase|映像基址|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_IMAGEBASE
IDS_PV_FIELD_OPTIONAL_SECTION_ALIGNMENT|3176|SectionAlignment|节对齐|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SECTIONALIGN
IDS_PV_FIELD_OPTIONAL_FILE_ALIGNMENT|3177|FileAlignment|文件对齐|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_FILEALIGN
IDS_PV_FIELD_OPTIONAL_OPERATING_SYSTEM_VERSION|3178|OperatingSystemVersion|所需操作系统版本|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_OSVERSION
IDS_PV_FIELD_OPTIONAL_IMAGE_VERSION|3179|ImageVersion|映像版本|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_IMGVERSION
IDS_PV_FIELD_OPTIONAL_SUBSYSTEM_VERSION|3180|SubsystemVersion|所需子系统版本|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SUBSYSTEMVERSION
IDS_PV_FIELD_OPTIONAL_WIN32_VERSION_VALUE|3181|Win32VersionValue|Win32 版本值|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_WIN32VERSION
IDS_PV_FIELD_OPTIONAL_SIZE_OF_IMAGE|3182|SizeOfImage|映像大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFIMAGE
IDS_PV_FIELD_OPTIONAL_SIZE_OF_HEADERS|3183|SizeOfHeaders|头大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFHEADERS
IDS_PV_FIELD_OPTIONAL_CHECKSUM|3184|CheckSum|校验和|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_CHECKSUM
IDS_PV_FIELD_SUBSYSTEM|3185|Subsystem|子系统|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SUBSYSTEM
IDS_PV_FIELD_OPTIONAL_DLL_CHARACTERISTICS|3186|DllCharacteristics|DLL 特征|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_DLLCHARACTERISTICS
IDS_PV_FIELD_OPTIONAL_SIZE_OF_STACK_RESERVE|3187|SizeOfStackReserve|栈保留大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFSTACKRESERVE
IDS_PV_FIELD_OPTIONAL_SIZE_OF_STACK_COMMIT|3188|SizeOfStackCommit|栈提交大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFSTACKCOMMIT
IDS_PV_FIELD_OPTIONAL_SIZE_OF_HEAP_RESERVE|3189|SizeOfHeapReserve|堆保留大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFHEAPRESERVE
IDS_PV_FIELD_OPTIONAL_SIZE_OF_HEAP_COMMIT|3190|SizeOfHeapCommit|堆提交大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_SIZEOFHEAPCOMMIT
IDS_PV_FIELD_OPTIONAL_LOADER_FLAGS|3191|LoaderFlags|加载器标志|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_LOADERFLAGS
IDS_PV_FIELD_OPTIONAL_NUMBER_OF_RVA_AND_SIZES|3192|NumberOfRvaAndSizes|RVA/大小项数|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OPTHDR|PVP_IMAGE_HEADER_INDEX_OPT_NUMBEROFRVA
IDS_PV_FIELD_OVERLAY_DATA_SIZE|3193|Data size|数据大小|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OVERLAY|PVP_IMAGE_HEADER_INDEX_PE_OVERLAY_SIZE
IDS_PV_FIELD_OVERLAY_DATA_ENTROPY|3194|Data entropy|数据熵|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OVERLAY|PVP_IMAGE_HEADER_INDEX_PE_OVERLAY_ENTROPY
IDS_PV_FIELD_OVERLAY_DATA_HASH|3195|Data hash|数据哈希|peheaderprp.c|PVP_IMAGE_HEADER_CATEGORY_OVERLAY|PVP_IMAGE_HEADER_INDEX_PE_OVERLAY_HASH
IDS_PV_FIELD_TARGET_MACHINE|3196|Target machine|目标体系结构|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_NAME
IDS_PV_FIELD_IMAGE_TIMESTAMP|3197|Time stamp|时间戳|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_TIMESTAMP
IDS_PV_FIELD_IMAGE_ENTROPY|3198|Image entropy|映像熵|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_ENTROPY
IDS_PV_FIELD_IMAGE_BASE|3199|Image base|映像基址|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_IMAGEBASE
IDS_PV_FIELD_IMAGE_SIZE|3200|Image size|映像大小|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_IMAGESIZE
IDS_PV_FIELD_ENTRY_POINT|3201|Entry point|入口点|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_ENTRYPOINT
IDS_PV_FIELD_HEADER_CHECKSUM|3202|Header checksum|头部校验和|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_CHECKSUM
IDS_PV_FIELD_HEADER_SPARE|3203|Header spare|头部空余空间|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_HEADERSPARE
IDS_PV_FIELD_SECTION_SLACK|3204|Section slack|节空闲空间|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_SECTIONSLACK
IDS_PV_FIELD_SUBSYSTEM|3185|Subsystem|子系统|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_SUBSYSTEM
IDS_PV_FIELD_IMAGE_SUBSYSTEM_VERSION|3205|Subsystem version|子系统版本|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_SUBSYSTEMVERSION
IDS_PV_COLUMN_CHARACTERISTICS|3030|Characteristics|特征|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_BASICINFO|PVP_IMAGE_GENERAL_INDEX_CHARACTERISTICS
IDS_PV_FIELD_FILE_CREATED_TIME|3206|Created time|创建时间|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_FILEINFO|PVP_IMAGE_GENERAL_INDEX_FILECREATEDTIME
IDS_PV_FIELD_FILE_ACCESSED_TIME|3207|Accessed time|上次访问时间|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_FILEINFO|PVP_IMAGE_GENERAL_INDEX_FILELASTACCESSTIME
IDS_PV_FIELD_FILE_MODIFIED_TIME|3208|Modified time|上次写入时间|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_FILEINFO|PVP_IMAGE_GENERAL_INDEX_FILELASTMODIFIEDTIME
IDS_PV_FIELD_FILE_CHANGED_TIME|3209|Updated time|元数据变更时间|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_FILEINFO|PVP_IMAGE_GENERAL_INDEX_FILELASTWRITETIME
IDS_PV_FIELD_DEBUG_GUID|3210|Guid|GUID|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_DEBUGINFO|PVP_IMAGE_GENERAL_INDEX_DEBUGPDB
IDS_PV_FIELD_DEBUG_IMAGE_NAME|3211|Image name|映像名称|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_DEBUGINFO|PVP_IMAGE_GENERAL_INDEX_DEBUGIMAGE
IDS_PV_FIELD_DEBUG_FEATURE_COUNT|3212|Feature count|特性计数|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_DEBUGINFO|PVP_IMAGE_GENERAL_INDEX_DEBUGVCFEATURE
IDS_PV_FIELD_DEBUG_REPRODUCIBLE_HASH|3213|Reproducible hash|可重现构建哈希|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_DEBUGINFO|PVP_IMAGE_GENERAL_INDEX_DEBUGREPRO
IDS_PV_FIELD_FILE_INDEX|3214|File index|文件索引|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_EXTRAINFO|PVP_IMAGE_GENERAL_INDEX_FILEINDEX
IDS_PV_FIELD_FILE_IDENTIFIER|3215|File identifier|文件标识符|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_EXTRAINFO|PVP_IMAGE_GENERAL_INDEX_FILEID
IDS_PV_FIELD_FILE_OBJECT_IDENTIFIER|3216|File object identifier|文件对象标识符|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_EXTRAINFO|PVP_IMAGE_GENERAL_INDEX_FILEOBJECTID
IDS_PV_FIELD_FILE_LAST_USN|3217|File last USN|文件最新 USN|peprp.c|PVP_IMAGE_GENERAL_CATEGORY_EXTRAINFO|PVP_IMAGE_GENERAL_INDEX_FILEUSN
""".strip()


ROUTES = [tuple(line.split("|")) for line in ROUTE_DATA.splitlines()]
ROUTES = [
    (symbol, int(resource_id), english, chinese, source, group, index)
    for symbol, resource_id, english, chinese, source, group, index in ROUTES
]
RUNTIME_KEYS = {
    "Characteristics",
    "Checksum",
    "Data size",
    "Entry point",
    "File index",
    "Guid",
    "ImageBase",
    "Relocations",
    "Subsystem",
    "Time stamp",
    "Timestamp",
    "Total size",
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_peview_groups", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def parse_group_item_routes(source_name, function_name):
    audit = load_audit_module()
    text = audit.mask_c_comments(
        (PEVIEW_ROOT / source_name).read_text(encoding="utf-8")
    )
    body = function_body(text, function_name)
    pattern = re.compile(
        r"PhAddListViewGroupItem\(\s*Context->ListViewHandle\s*,\s*"
        r"(?P<group>PVP_[A-Z0-9_]+)\s*,\s*"
        r"(?P<index>PVP_[A-Z0-9_]+)\s*,\s*"
        r"PvpLoadUiString\(\s*(?P<symbol>IDS_PV_[A-Z0-9_]+)\s*\)\s*,\s*"
        r"NULL\s*\)\s*;",
        re.S,
    )
    return [
        (source_name, match.group("group"), match.group("index"), match.group("symbol"))
        for match in pattern.finditer(body)
    ]


def parse_defines():
    text = (PEVIEW_ROOT / "resource.h").read_text(encoding="utf-8")
    return {
        symbol: int(value)
        for symbol, value in re.findall(r"(?m)^#define\s+(IDS_PV_[A-Z0-9_]+)\s+(\d+)$", text)
    }, text


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PV_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class PeViewGroupItemResourcesTests(unittest.TestCase):
    def test_table_has_expected_unique_resources_and_routes(self):
        by_symbol = {}
        for symbol, resource_id, english, chinese, *_ in ROUTES:
            value = (resource_id, english, chinese)
            if symbol in by_symbol:
                self.assertIn(symbol, {"IDS_PV_COLUMN_CHARACTERISTICS", "IDS_PV_FIELD_SUBSYSTEM"})
                self.assertEqual(by_symbol[symbol], value)
            by_symbol[symbol] = value

        self.assertEqual(len(ROUTES), 87)
        self.assertEqual(len(by_symbol), 85)
        self.assertEqual(Counter(route[4] for route in ROUTES), {"peheaderprp.c": 63, "peprp.c": 24})
        self.assertEqual(Counter(route[0] for route in ROUTES)["IDS_PV_COLUMN_CHARACTERISTICS"], 2)
        self.assertEqual(Counter(route[0] for route in ROUTES)["IDS_PV_FIELD_SUBSYSTEM"], 2)

    def test_resource_ids_and_stringtables_match_table(self):
        defines, header = parse_defines()
        english = parse_stringtable(PEVIEW_ROOT / "peview.rc")
        chinese = parse_stringtable(PEVIEW_ROOT / "peview.zh-cn.rc")

        expected = {}
        for symbol, resource_id, en, zh, *_ in ROUTES:
            expected[symbol] = (resource_id, en, zh)

        for symbol, (resource_id, en, zh) in expected.items():
            self.assertEqual(defines.get(symbol), resource_id, symbol)
            self.assertEqual(english.get(symbol), en, symbol)
            self.assertEqual(chinese.get(symbol), zh, symbol)

        new_ids = sorted(resource_id for symbol, (resource_id, *_rest) in expected.items() if symbol != "IDS_PV_COLUMN_CHARACTERISTICS")
        self.assertEqual(new_ids, list(range(3134, 3218)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(set(defines.values())), 298)
        self.assertEqual(sorted(defines.values()), list(range(3000, 3298)))
        self.assertRegex(header, r"(?m)^#define IDS_PV_FIRST\s+IDS_PV_MENU_ANSI$")
        self.assertRegex(header, r"(?m)^#define IDS_PV_LAST\s+IDS_PV_CERTIFICATE_SIZE_FORMAT$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3298$")
        self.assertEqual(len(english), 298)
        self.assertEqual(len(chinese), 298)

    def test_source_routes_match_table(self):
        actual = (
            parse_group_item_routes("peheaderprp.c", "PvPeUpdateImageHeaderProperties")
            + parse_group_item_routes("peprp.c", "PvpSetPeImageProperties")
        )
        expected = [(source, group, index, symbol) for symbol, _id, _en, _zh, source, group, index in ROUTES]

        self.assertEqual(actual, expected)
        self.assertEqual(Counter(source for source, *_ in actual), {"peheaderprp.c": 63, "peprp.c": 24})

    def test_json_separates_runtime_and_native_strings(self):
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        strings = data["strings"]
        native_strings = data["native_strings"]
        expected = {english: chinese for _symbol, _id, english, chinese, *_ in ROUTES}

        self.assertFalse(strings.keys() & native_strings.keys())
        for english, chinese in expected.items():
            table = strings if english in RUNTIME_KEYS else native_strings
            other = native_strings if english in RUNTIME_KEYS else strings
            self.assertEqual(table.get(english), chinese, english)
            self.assertNotIn(english, other)

    def test_ci_requires_exact_peview_resource_count_twice(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("peview.exe=298"), 2)
        self.assertNotIn("peview.exe=258", workflow)
        self.assertNotIn("peview.exe=247", workflow)
        self.assertNotIn("peview.exe=246", workflow)
        self.assertNotIn("peview.exe=218", workflow)
        self.assertNotIn("peview.exe=134", workflow)

    def test_audit_has_no_peview_group_item_literals(self):
        audit = load_audit_module()
        entries = []
        audit.scan_c_file(str(PEVIEW_ROOT / "peheaderprp.c"), entries)
        audit.scan_c_file(str(PEVIEW_ROOT / "peprp.c"), entries)
        remaining = [entry for entry in entries if entry["category"] == "c_listview_group_item"]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
