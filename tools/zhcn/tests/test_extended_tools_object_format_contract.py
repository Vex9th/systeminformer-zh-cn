#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ExtendedTools"
OBJECT_MANAGER_PATH = PLUGIN_ROOT / "objmgr.c"
OBJECT_PROPERTIES_PATH = PLUGIN_ROOT / "objprp.c"


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("extended_tools_object_format_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.S)
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening = source.find("{", match.start())
    depth = 0

    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]

    raise AssertionError(f"unterminated function: {name}")


class ExtendedToolsObjectFormatContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.object_manager = OBJECT_MANAGER_PATH.read_text(encoding="utf-8-sig")
        cls.object_properties = OBJECT_PROPERTIES_PATH.read_text(encoding="utf-8-sig")

    def test_object_type_counts_keep_unsigned_width_and_argument_order(self) -> None:
        body = function_body(
            self.object_manager,
            "EtpTargetResolverWorkThreadStart",
            self.audit,
        )

        self.assertRegex(
            body,
            r'PhFormatString\(\s*L"Index: %d, Objects: %lu, Handles: %lu",\s*'
            r'objectType->TypeIndex,\s*'
            r'objectType->TotalNumberOfObjects,\s*'
            r'objectType->TotalNumberOfHandles\s*\)',
        )
        self.assertNotIn('L"Index: %d, Objects: %d, Handles: %d"', body)

    def test_semaphore_long_counts_use_long_format_specifiers(self) -> None:
        body = function_body(
            self.object_manager,
            "EtpTargetResolverWorkThreadStart",
            self.audit,
        )

        self.assertRegex(
            body,
            r'PhFormatString\(\s*L"Current count: %ld/%ld",\s*'
            r'basicInfo\.CurrentCount,\s*basicInfo\.MaximumCount\s*\)',
        )
        self.assertNotIn('L"Current count: %d/%d"', body)

    def test_object_manager_session_nonempty_branch_uses_fixed_separator(self) -> None:
        body = function_body(
            self.object_manager,
            "EtpTargetResolverWorkThreadStart",
            self.audit,
        )

        self.assertRegex(
            body,
            r'if\s*\(\s*winStationInfo\.Domain\[0\]\s*==\s*UNICODE_NULL\s*\|\|\s*'
            r'winStationInfo\.UserName\[0\]\s*==\s*UNICODE_NULL\s*\)\s*\{\s*'
            r'entry->Target\s*=\s*PhFormatString\(\s*L"%s \(%s\)",\s*'
            r'winStationInfo\.WinStationName,\s*EtMapSessionConnectState\('
            r'winStationInfo\.ConnectState\)\s*\)\s*;\s*\}\s*else\s*\{\s*'
            r'entry->Target\s*=\s*PhFormatString\(\s*L"%s%c%s \(%s\)",\s*'
            r'winStationInfo\.Domain,\s*OBJ_NAME_PATH_SEPARATOR,\s*'
            r'winStationInfo\.UserName,\s*EtMapSessionConnectState\('
            r'winStationInfo\.ConnectState\)\s*\)\s*;\s*\}',
        )
        self.assertNotRegex(
            body,
            r'winStationInfo\.Domain\[0\]\s*!=\s*UNICODE_NULL\s*\?\s*'
            r'OBJ_NAME_PATH_SEPARATOR\s*:\s*UNICODE_NULL',
        )

    def test_property_username_uses_string_separator_without_embedded_null(self) -> None:
        body = function_body(
            self.object_properties,
            "EtHandlePropertiesWindowInitialized",
            self.audit,
        )

        self.assertRegex(
            body,
            r'PhaFormatString\(\s*L"%s%s%s",\s*'
            r'winStationInfo\.Domain,\s*'
            r'winStationInfo\.Domain\[0\]\s*!=\s*UNICODE_NULL\s*\?\s*'
            r'L"\\\\"\s*:\s*L"",\s*'
            r'winStationInfo\.UserName\s*\)->Buffer',
        )
        self.assertNotIn('L"%s%c%s"', body)
        self.assertNotRegex(
            body,
            r'OBJ_NAME_PATH_SEPARATOR\s*:\s*UNICODE_NULL',
        )

    def test_desktop_heap_ulong_uses_unsigned_long_format(self) -> None:
        body = function_body(
            self.object_properties,
            "EtpEnumDesktopsCallback",
            self.audit,
        )

        self.assertRegex(
            body,
            r'(?s)ULONG\s+vInfo\s*=\s*0\s*;.*?'
            r'if\s*\(\s*GetUserObjectInformation\(\s*hDesktop,\s*UOI_HEAPSIZE,\s*'
            r'&vInfo,\s*sizeof\(vInfo\),\s*NULL\s*\)\s*\)\s*\{\s*'
            r'PPH_STRING\s+size\s*=\s*PH_AUTO\(PhFormatString\('
            r'L"%lu MB",\s*vInfo\s*/\s*1024\s*\)\)\s*;',
        )
        self.assertNotIn('PhFormatString(L"%d MB", vInfo / 1024)', body)

    def test_object_resolver_call_chain_is_active(self) -> None:
        resolver = function_body(
            self.object_manager,
            "EtpObjectManagerStartResolver",
            self.audit,
        )
        resolver_thread = function_body(
            self.object_manager,
            "EtpTargetResolverThreadStart",
            self.audit,
        )

        self.assertIn("EtpTargetResolverThreadStart", resolver)
        self.assertIn("EtpTargetResolverWorkThreadStart", resolver_thread)


if __name__ == "__main__":
    unittest.main()
