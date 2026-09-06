#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PHLIB_ROOT = REPO_ROOT / "phlib"

RESOURCE_DATA = (
    ("IDS_PH_UNABLE_LOAD_PLUGIN", 2177, "Unable to load plugin.", "无法加载插件。"),
    ("IDS_PH_PLUGIN_IMPORT_BY_ORDINAL", 2178, r"Name: %s\r\nOrdinal: %u\r\nModule: %hs", r"名称：%s\r\n序号：%u\r\n模块：%hs"),
    ("IDS_PH_PLUGIN_IMPORT_BY_NAME", 2179, r"Name: %s\r\nFunction: %hs\r\nModule: %hs", r"名称：%s\r\n函数：%hs\r\n模块：%hs"),
    ("IDS_PH_LOCATION_NOT_FOUND", 2180, "The location could not be found.", "找不到该位置。"),
    ("IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT", 2181, "Unable to create the window context.", "无法创建窗口上下文。"),
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("phlib_messagebox_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_body(source: str, name: str, audit) -> str:
    source = audit.mask_c_comments(source)
    match = re.search(
        rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening_brace = source.find("{", match.start())
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index]

    raise AssertionError(f"unterminated function: {name}")


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def braced_block(source: str, opening_brace: int) -> tuple[str, int]:
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index], index

    raise AssertionError("unterminated block")


def if_else_branches(source: str, condition: str) -> tuple[str, str]:
    condition_index = source.index(condition)
    opening_brace = source.index("{", condition_index)
    true_branch, closing_brace = braced_block(source, opening_brace)
    else_match = re.match(r"\s*else\s*", source[closing_brace + 1 :])
    if else_match is None:
        raise AssertionError(f"else branch not found: {condition}")

    else_index = closing_brace + 1 + else_match.end()
    else_opening_brace = source.index("{", else_index)
    false_branch, _ = braced_block(source, else_opening_brace)
    return true_branch, false_branch


def call_tuples(source: str, call: str, audit) -> list[tuple[str, ...]]:
    return [
        tuple(argument.strip() for argument in arguments)
        for name, arguments, _spans, _start in audit.find_calls(source, {call})
        if name == call
    ]


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class PhlibMessageboxNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: (PHLIB_ROOT / name).read_text(encoding="utf-8-sig")
            for name in ("mapldr.c", "guisup.c", "util.c")
        }

    def test_five_resources_keep_runtime_compatibility_ownership(self) -> None:
        app_root = REPO_ROOT / "SystemInformer"
        phlib_ids = (PHLIB_ROOT / "include" / "phappresourceid.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(app_root / "SystemInformer.rc")
        chinese = parse_stringtable(app_root / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        self.assertEqual(list(range(2177, 2182)), [row[1] for row in RESOURCE_DATA])
        for symbol, resource_id, en, zh in RESOURCE_DATA:
            with self.subTest(symbol=symbol):
                self.assertRegex(phlib_ids, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(en, english.get(symbol))
                self.assertEqual(zh, chinese.get(symbol))
                json_en = en.replace(r"\r", "\r").replace(r"\n", "\n")
                json_zh = zh.replace(r"\r", "\r").replace(r"\n", "\n")
                self.assertEqual(json_zh, data["strings"].get(json_en))
                self.assertNotIn(json_en, data["native_strings"])

    def test_shared_fallback_loader_is_owned_nonnull_and_used_by_all_three_files(self) -> None:
        internal_header = (PHLIB_ROOT / "include" / "phintrnl.h").read_text(encoding="utf-8-sig")
        self.assertRegex(
            internal_header,
            r"_Ret_notnull_\s+PPH_STRING\s+PhpLoadApplicationUiStringOrDefault\s*\(",
        )

        loader = function_body(
            self.sources["mapldr.c"],
            "PhpLoadApplicationUiStringOrDefault",
            self.audit,
        )
        self.assertIn("PhLoadUiString(PhApplicationUiResourceInstance,ResourceId,NULL)", compact(loader))
        self.assertRegex(loader, r"if\s*\(\s*!resourceText\s*\)\s*resourceText\s*=\s*PhCreateString\(FallbackText\)")
        self.assertRegex(loader, r"return\s+resourceText\s*;")

        expected_routes = {
            "mapldr.c": {
                "IDS_PH_UNABLE_LOAD_PLUGIN": 'L"Unable to load plugin."',
                "IDS_PH_PLUGIN_IMPORT_BY_ORDINAL": 'L"Name: %s\\r\\nOrdinal: %u\\r\\nModule: %hs"',
                "IDS_PH_PLUGIN_IMPORT_BY_NAME": 'L"Name: %s\\r\\nFunction: %hs\\r\\nModule: %hs"',
            },
            "guisup.c": {
                "IDS_PH_UNABLE_CREATE_WINDOW_CONTEXT": 'L"Unable to create the window context."',
            },
            "util.c": {
                "IDS_PH_LOCATION_NOT_FOUND": 'L"The location could not be found."',
            },
        }

        for file_name, routes in expected_routes.items():
            masked = self.audit.mask_c_comments(self.sources[file_name])
            calls = {
                compact(arguments[0]): compact(arguments[1])
                for name, arguments, _spans, _start in self.audit.find_calls(
                    masked,
                    {"PhpLoadApplicationUiStringOrDefault"},
                )
                if name == "PhpLoadApplicationUiStringOrDefault"
                and len(arguments) == 2
                and compact(arguments[0]) in routes
            }
            self.assertEqual(
                {resource_id: compact(fallback) for resource_id, fallback in routes.items()},
                calls,
                file_name,
            )

    def assert_plugin_import_error_contract(self, source: str) -> None:
        body = function_body(source, "PhLoaderEntrySnapShowErrorMessage", self.audit)
        ordinal_branch, name_branch = if_else_branches(
            body,
            "if (IMAGE_SNAP_BY_ORDINAL(OriginalThunk->u1.Ordinal))",
        )

        branch_contracts = (
            (
                ordinal_branch,
                (
                    "IDS_PH_PLUGIN_IMPORT_BY_ORDINAL",
                    'L"Name: %s\\r\\nOrdinal: %u\\r\\nModule: %hs"',
                ),
                (
                    "NULL",
                    "resourceTitle->Buffer",
                    "resourceFormat->Buffer",
                    "PhGetStringOrEmpty(fileName)",
                    "IMAGE_ORDINAL(OriginalThunk->u1.Ordinal)",
                    "ImportName",
                ),
            ),
            (
                name_branch,
                (
                    "IDS_PH_PLUGIN_IMPORT_BY_NAME",
                    'L"Name: %s\\r\\nFunction: %hs\\r\\nModule: %hs"',
                ),
                (
                    "NULL",
                    "resourceTitle->Buffer",
                    "resourceFormat->Buffer",
                    "PhGetStringOrEmpty(fileName)",
                    "importByName->Name",
                    "ImportName",
                ),
            ),
        )

        for branch, expected_loader, expected_sink in branch_contracts:
            self.assertEqual(
                [expected_loader],
                call_tuples(branch, "PhpLoadApplicationUiStringOrDefault", self.audit),
            )
            self.assertEqual(
                [expected_sink],
                call_tuples(branch, "PhShowError2", self.audit),
            )
            self.assertEqual(1, branch.count("PhClearReference(&resourceFormat)"))
            self.assertLess(
                branch.index("PhShowError2("),
                branch.index("PhClearReference(&resourceFormat)"),
            )

    def test_plugin_import_error_routes_bind_formats_arguments_and_lifetimes(self) -> None:
        self.assert_plugin_import_error_contract(self.sources["mapldr.c"])

    def test_plugin_import_error_contract_rejects_route_argument_and_release_mutations(self) -> None:
        source = self.sources["mapldr.c"]
        mutations = (
            source.replace("PhClearReference(&resourceFormat);", "", 1),
            source.replace("IDS_PH_PLUGIN_IMPORT_BY_ORDINAL", "IDS_PH_PLUGIN_IMPORT_BY_NAME", 1),
            source.replace("Ordinal: %u", "Ordinal: %hs", 1),
            source.replace(
                "IMAGE_ORDINAL(OriginalThunk->u1.Ordinal),\n                ImportName",
                "ImportName,\n                IMAGE_ORDINAL(OriginalThunk->u1.Ordinal)",
                1,
            ),
            source.replace(
                "importByName->Name,\n                ImportName",
                "ImportName,\n                importByName->Name",
                1,
            ),
        )

        for mutated in mutations:
            self.assertNotEqual(source, mutated)
            with self.assertRaises(AssertionError):
                self.assert_plugin_import_error_contract(mutated)

    def test_messagebox_sinks_release_owned_text_and_have_no_runtime_findings(self) -> None:
        lifetime_contracts = (
            ("mapldr.c", "PhLoaderEntrySnapShowErrorMessage", "PhShowError2", "PhClearReference(&resourceTitle)"),
            ("guisup.c", "PhGetWindowContextHashTable", "PhShowStatus", "PhClearReference(&resourceTitle)"),
            ("util.c", "PhShellExploreFile", "PhShowError2", "PhClearReference(&resourceTitle)"),
        )

        for file_name, function_name, sink, release in lifetime_contracts:
            body = function_body(self.sources[file_name], function_name, self.audit)
            self.assertLess(body.index(sink + "("), body.rindex(release), file_name)

        for file_name in self.sources:
            entries = []
            self.audit.scan_c_file(str(PHLIB_ROOT / file_name), entries)
            self.assertEqual(
                [],
                [entry for entry in entries if entry["category"] == "c_msgbox"],
                file_name,
            )

    def assert_confirm_language_spacing_contract(self, source: str) -> None:
        worker = function_body(source, "PhpShowConfirmMessage", self.audit)

        self.assertNotIn("PhTranslationEnabled", worker)
        self.assertNotIn("TranslateObject", worker)
        self.assertNotRegex(worker, r"PhTranslateString\(\s*(?:Verb|Object|Message)\s*\)")
        self.assertRegex(
            worker,
            r"PhGetApplicationUiLanguage\(\)\s*==\s*MAKELANGID\(\s*LANG_CHINESE\s*,\s*SUBLANG_CHINESE_SIMPLIFIED\s*\)",
        )
        spacing_branches = re.search(
            r"if\s*\(\s*PhGetApplicationUiLanguage\(\)\s*==\s*"
            r"MAKELANGID\(\s*LANG_CHINESE\s*,\s*SUBLANG_CHINESE_SIMPLIFIED\s*\)\s*\)\s*"
            r"(?P<chinese>action\s*=\s*PhaConcatStrings\([^;]+;)\s*"
            r"else\s*(?P<english>action\s*=\s*PhaConcatStrings\([^;]+;)",
            worker,
        )
        self.assertIsNotNone(spacing_branches)
        self.assertEqual(
            [("2", "verb->Buffer", "Object")],
            call_tuples(spacing_branches.group("chinese"), "PhaConcatStrings", self.audit),
        )
        self.assertEqual(
            [("3", "verb->Buffer", 'L" "', "Object")],
            call_tuples(spacing_branches.group("english"), "PhaConcatStrings", self.audit),
        )
        raw_branch = worker.index("if (RawAction)")
        object_read = worker.index("PhaConcatStrings", raw_branch)
        self.assertLess(raw_branch, object_read)
        self.assertRegex(worker, r"RawAction[\s\S]*?PhaCreateString\(RawAction\)[\s\S]*?else")
        self.assertIn("PhaConcatStrings(2,verb->Buffer,Object)", compact(worker))
        self.assertRegex(
            worker,
            r'PhaConcatStrings\(\s*3\s*,\s*verb->Buffer\s*,\s*L" "\s*,\s*Object\s*\)',
        )

        self.assertEqual(0, worker.count("PhTranslateString("))

    def test_confirm_worker_uses_ui_language_not_runtime_translation(self) -> None:
        self.assert_confirm_language_spacing_contract(self.sources["util.c"])

    def test_confirm_language_spacing_contract_rejects_swapped_branches(self) -> None:
        source = self.sources["util.c"]
        expected = (
            "if (PhGetApplicationUiLanguage() == MAKELANGID(LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED))\n"
            "            action = PhaConcatStrings(2, verb->Buffer, Object);\n"
            "        else\n"
            "            action = PhaConcatStrings(3, verb->Buffer, L\" \", Object);"
        )
        swapped = (
            "if (PhGetApplicationUiLanguage() == MAKELANGID(LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED))\n"
            "            action = PhaConcatStrings(3, verb->Buffer, L\" \", Object);\n"
            "        else\n"
            "            action = PhaConcatStrings(2, verb->Buffer, Object);"
        )
        mutated = source.replace(expected, swapped, 1)

        self.assertNotEqual(source, mutated)
        with self.assertRaises(AssertionError):
            self.assert_confirm_language_spacing_contract(mutated)


if __name__ == "__main__":
    unittest.main()
