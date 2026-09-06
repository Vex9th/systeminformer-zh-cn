#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"


# symbol | id | English | zh-CN | translation owner
RESOURCE_DATA = r"""
IDS_ET_CACHE_TYPE_DATA|61116|Data|数据|strings
IDS_ET_CACHE_TYPE_INSTRUCTION|61117|Instruction|指令|strings
IDS_ET_CACHE_TYPE_UNIFIED|61118|Unified|统一|native_strings
IDS_ET_UNKNOWN|61119|Unknown|未知|strings
IDS_ET_STATE_ACTIVE|61120|Active|活动|native_strings
IDS_ET_SESSION_STATE_CONNECTED|61121|Connected|已连接|native_strings
IDS_ET_SESSION_STATE_CONNECT_QUERY|61122|ConnectQuery|连接查询|native_strings
IDS_ET_SESSION_STATE_SHADOW|61123|Shadow|影子会话|native_strings
IDS_ET_SESSION_STATE_DISCONNECTED|61124|Disconnected|已断开连接|native_strings
IDS_ET_SESSION_STATE_IDLE|61125|Idle|空闲|native_strings
IDS_ET_SESSION_STATE_LISTEN|61126|Listen|侦听|native_strings
IDS_ET_SESSION_STATE_RESET|61127|Reset|重置|strings
IDS_ET_SESSION_STATE_DOWN|61128|Down|已停止|native_strings
IDS_ET_SESSION_STATE_INIT|61129|Init|初始化中|native_strings
IDS_ET_CACHE_LATENCY_SUMMARY_FORMAT|61130|L%lu %s latency: %lu cycles (%lu KB)|L%lu %s缓存延迟：%lu 个周期（%lu KB）|native_strings
IDS_ET_DRAM_LATENCY_SUMMARY_FORMAT|61131|DRAM latency: %lu cycles (%lu KB)|DRAM 延迟：%lu 个周期（%lu KB）|native_strings
""".strip()


RESOURCES = [tuple(line.split("|")) for line in RESOURCE_DATA.splitlines()]
RESOURCES = [
    (symbol, int(resource_id), english, chinese, owner)
    for symbol, resource_id, english, chinese, owner in RESOURCES
]


CACHE_ROUTES = (
    ("1", "IDS_ET_CACHE_TYPE_DATA", "Data"),
    ("2", "IDS_ET_CACHE_TYPE_INSTRUCTION", "Instruction"),
    ("3", "IDS_ET_CACHE_TYPE_UNIFIED", "Unified"),
    ("default", "IDS_ET_UNKNOWN", "Unknown"),
)


SESSION_ROUTES = (
    ("State_Active", "IDS_ET_STATE_ACTIVE", "Active"),
    ("State_Connected", "IDS_ET_SESSION_STATE_CONNECTED", "Connected"),
    ("State_ConnectQuery", "IDS_ET_SESSION_STATE_CONNECT_QUERY", "ConnectQuery"),
    ("State_Shadow", "IDS_ET_SESSION_STATE_SHADOW", "Shadow"),
    ("State_Disconnected", "IDS_ET_SESSION_STATE_DISCONNECTED", "Disconnected"),
    ("State_Idle", "IDS_ET_SESSION_STATE_IDLE", "Idle"),
    ("State_Listen", "IDS_ET_SESSION_STATE_LISTEN", "Listen"),
    ("State_Reset", "IDS_ET_SESSION_STATE_RESET", "Reset"),
    ("State_Down", "IDS_ET_SESSION_STATE_DOWN", "Down"),
    ("State_Init", "IDS_ET_SESSION_STATE_INIT", "Init"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_et_cache_session", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def masked_source(filename):
    audit = load_audit_module()
    return audit.mask_c_comments(
        (PLUGIN_ROOT / filename).read_text(encoding="utf-8-sig")
    )


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
            r"(?m)^#define\s+(IDS_ET_[A-Z0-9_]+)\s+(\d+)$",
            header,
        )
    }
    return defines, header


def parse_stringtable(path):
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_ET_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            text,
        )
    }


class ExtendedToolsCacheSessionResourceTests(unittest.TestCase):
    def test_cache_type_helper_uses_all_four_exact_resources(self):
        body = function_body(masked_source("cacheprp.c"), "EtCacheLatencyTypeString")
        pattern = re.compile(
            r"(?:\bcase\s+([0-9]+)\s*:|\b(default)\s*:)\s*"
            r"return\s+EtGetUiString\(\s*(IDS_ET_[A-Z0-9_]+)\s*,\s*"
            r'L"([^"\r\n]+)"\s*\)\s*;'
        )
        actual = tuple(
            (match.group(1) or match.group(2), match.group(3), match.group(4))
            for match in pattern.finditer(body)
        )

        self.assertEqual(actual, CACHE_ROUTES)

    def test_session_state_switch_is_exact_and_invalid_state_stays_null(self):
        body = function_body(masked_source("objprp.c"), "EtMapSessionConnectState")
        pattern = re.compile(
            r"\bcase\s+(State_[A-Za-z]+)\s*:\s*"
            r"return\s+EtGetUiString\(\s*(IDS_ET_[A-Z0-9_]+)\s*,\s*"
            r'L"([^"\r\n]+)"\s*\)\s*;'
        )

        self.assertEqual(tuple(pattern.findall(body)), SESSION_ROUTES)
        self.assertRegex(body, r"\bswitch\s*\(\s*State\s*\)")
        self.assertRegex(body, r"\bdefault\s*:\s*return\s+NULL\s*;")
        self.assertNotIn("PH_KEY_VALUE_PAIR", body)

    def test_summary_formats_preserve_arguments_and_instruction_skip(self):
        body = function_body(masked_source("cacheprp.c"), "EtCacheLatencyAddSummaryRows")
        self.assertRegex(body, r"if\s*\(\s*cache->Type\s*==\s*2\s*\)\s*continue\s*;")
        self.assertRegex(
            body,
            r"PhaFormatString\(\s*EtGetUiString\(\s*"
            r"IDS_ET_CACHE_LATENCY_SUMMARY_FORMAT\s*,\s*"
            r'L"L%lu %s latency: %lu cycles \(%lu KB\)"\s*\)\s*,\s*'
            r"cache->Level\s*,\s*EtCacheLatencyTypeString\(cache->Type\)\s*,\s*"
            r"samples\s*\?\s*\(ULONG\)\(sum\s*/\s*samples\)\s*:\s*0\s*,\s*"
            r"\(ULONG\)\(\s*1u\s*<<\s*row\s*\)\s*\)",
        )
        self.assertRegex(
            body,
            r"PhaFormatString\(\s*EtGetUiString\(\s*"
            r"IDS_ET_DRAM_LATENCY_SUMMARY_FORMAT\s*,\s*"
            r'L"DRAM latency: %lu cycles \(%lu KB\)"\s*\)\s*,\s*'
            r"dramSamples\s*\?\s*\(ULONG\)\(dramSum\s*/\s*dramSamples\)\s*:\s*0\s*,\s*"
            r"\(ULONG\)\(\s*1u\s*<<\s*dramRow\s*\)\s*\)",
        )

    def test_cached_range_aliases_cover_every_loaded_resource(self):
        _defines, header = parse_defines()
        main = masked_source("main.c")
        helper = function_body(main, "EtGetUiString")

        self.assertRegex(header, r"(?m)^#define IDS_ET_CACHED_FIRST\s+IDS_ET_DEDICATED_MEMORY$")
        self.assertRegex(header, r"(?m)^#define IDS_ET_CACHED_LAST\s+IDS_ET_CONFIRM_THREAD_IO$")
        self.assertRegex(
            main,
            r"static\s+PPH_STRING\s+EtUiStrings\[IDS_ET_CACHED_LAST\s*-\s*IDS_ET_CACHED_FIRST\s*\+\s*1\]",
        )
        self.assertRegex(
            helper,
            r"ResourceId\s*<\s*IDS_ET_CACHED_FIRST\s*\|\|\s*ResourceId\s*>\s*IDS_ET_CACHED_LAST",
        )
        self.assertRegex(
            helper,
            r"for\s*\(ULONG resourceId\s*=\s*IDS_ET_CACHED_FIRST;\s*"
            r"resourceId\s*<=\s*IDS_ET_CACHED_LAST;\s*resourceId\+\+\)",
        )
        self.assertEqual(helper.count("resourceId - IDS_ET_CACHED_FIRST"), 1)
        self.assertEqual(helper.count("ResourceId - IDS_ET_CACHED_FIRST"), 1)
        self.assertRegex(
            helper,
            r"if\s*\(PhBeginInitOnce\(&EtUiStringsInitOnce\)\)\s*\{\s*"
            r"for\s*\(ULONG resourceId\s*=\s*IDS_ET_CACHED_FIRST;\s*"
            r"resourceId\s*<=\s*IDS_ET_CACHED_LAST;\s*resourceId\+\+\)\s*\{\s*"
            r"EtUiStrings\[resourceId\s*-\s*IDS_ET_CACHED_FIRST\]\s*=\s*"
            r"PhLoadUiString\(\s*PluginInstance->DllBase\s*,\s*resourceId\s*,\s*NULL\s*\);\s*"
            r"\}\s*PhEndInitOnce\(&EtUiStringsInitOnce\);\s*\}",
        )
        self.assertEqual(helper.count("PhBeginInitOnce(&EtUiStringsInitOnce)"), 1)
        self.assertEqual(helper.count("PhEndInitOnce(&EtUiStringsInitOnce)"), 1)
        self.assertEqual(helper.count("PluginInstance->DllBase"), 1)

    def test_resources_json_ci_and_generator_boundaries_are_exact(self):
        defines, header = parse_defines()
        english = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.rc")
        chinese = parse_stringtable(PLUGIN_ROOT / "ExtendedTools.zh-cn.rc")
        data = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )

        for symbol, resource_id, en, zh, owner in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertEqual(defines.get(symbol), resource_id)
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)
                self.assertEqual(data[owner].get(en), zh)
                other = "strings" if owner == "native_strings" else "native_strings"
                self.assertNotIn(en, data[other])

        self.assertEqual([row[1] for row in RESOURCES], list(range(61116, 61132)))
        self.assertEqual(sorted(defines.values()), list(range(61000, 61397)))
        self.assertEqual(set(defines), set(english))
        self.assertEqual(set(defines), set(chinese))
        self.assertEqual(len(english), 397)
        self.assertEqual(len(chinese), 397)
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+61397$")

        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("plugins\\ExtendedTools.dll=397"), 2)
        self.assertNotIn("plugins\\ExtendedTools.dll=116", workflow)

        generator_test = (
            REPO_ROOT / "tools" / "zhcn" / "tests" / "test_native_resource_generation.py"
        ).read_text(encoding="utf-8")
        self.assertIn('self.assertIn("2624 strings", result.stdout)', generator_test)

    def test_migrated_literals_leave_the_fresh_audit(self):
        audit = load_audit_module()
        entries = []
        for filename in ("cacheprp.c", "objprp.c"):
            audit.scan_c_file(str(PLUGIN_ROOT / filename), entries)

        migrated = {row[2] for row in RESOURCES}
        self.assertFalse({entry["english"] for entry in entries} & migrated)


if __name__ == "__main__":
    unittest.main()
