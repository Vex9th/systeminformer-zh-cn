#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
GRAPH_SOURCE = REPO_ROOT / "phlib" / "graphscroll.c"

RESOURCES = (
    ("IDS_PH_SCROLL_HERE", 2598, "Scroll Here", "滚动到此处"),
    ("IDS_PH_SCROLL_LEFT_EDGE", 2599, "Left Edge", "左边缘"),
    ("IDS_PH_SCROLL_TOP", 2600, "Top", "顶部"),
    ("IDS_PH_SCROLL_RIGHT_EDGE", 2601, "Right Edge", "右边缘"),
    ("IDS_PH_SCROLL_BOTTOM", 2602, "Bottom", "底部"),
    ("IDS_PH_SCROLL_PAGE_LEFT", 2603, "Page Left", "向左翻页"),
    ("IDS_PH_SCROLL_PAGE_UP", 2604, "Page Up", "向上翻页"),
    ("IDS_PH_SCROLL_PAGE_RIGHT", 2605, "Page Right", "向右翻页"),
    ("IDS_PH_SCROLL_PAGE_DOWN", 2606, "Page Down", "向下翻页"),
    ("IDS_PH_SCROLL_LEFT", 2607, "Scroll Left", "向左滚动"),
    ("IDS_PH_SCROLL_UP", 2608, "Scroll Up", "向上滚动"),
    ("IDS_PH_SCROLL_RIGHT", 2609, "Scroll Right", "向右滚动"),
    ("IDS_PH_SCROLL_DOWN", 2610, "Scroll Down", "向下滚动"),
)

RUNTIME_RETIRED = {
    "Scroll Here",
    "Left Edge",
    "Right Edge",
    "Page Left",
    "Page Right",
    "Scroll Left",
    "Scroll Right",
}


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("graphscroll_native_audit", path)
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


def parse_stringtable(path: pathlib.Path):
    text = path.read_text(encoding="utf-8-sig")
    return dict(re.findall(r'(?m)^\s*(IDS_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text))


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


class GraphScrollNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.graph_source = GRAPH_SOURCE.read_text(encoding="utf-8-sig")

    def test_shared_ids_resources_translation_ownership_and_counts_are_exact(self) -> None:
        app_ids = (REPO_ROOT / "phlib" / "include" / "phappresourceid.h").read_text(encoding="utf-8-sig")
        system_header = (REPO_ROOT / "SystemInformer" / "resource.h").read_text(encoding="utf-8-sig")
        peview_header = (REPO_ROOT / "tools" / "peview" / "resource.h").read_text(encoding="utf-8-sig")
        system_en = parse_stringtable(REPO_ROOT / "SystemInformer" / "SystemInformer.rc")
        system_zh = parse_stringtable(REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc")
        peview_en = parse_stringtable(REPO_ROOT / "tools" / "peview" / "peview.rc")
        peview_zh = parse_stringtable(REPO_ROOT / "tools" / "peview" / "peview.zh-cn.rc")
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        for symbol, resource_id, english, chinese in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(app_ids, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertNotRegex(system_header, rf"(?m)^#define\s+{symbol}\b")
                self.assertNotRegex(peview_header, rf"(?m)^#define\s+{symbol}\b")
                self.assertEqual(system_en.get(symbol), english)
                self.assertEqual(system_zh.get(symbol), chinese)
                self.assertEqual(peview_en.get(symbol), english)
                self.assertEqual(peview_zh.get(symbol), chinese)
                self.assertEqual(translations["native_strings"].get(english), chinese)
                self.assertNotIn(english, translations["strings"])

        self.assertRegex(system_header, r"(?m)^#include\s+<phappresourceid\.h>$")
        self.assertRegex(peview_header, r"(?m)^#include\s+<phappresourceid\.h>$")
        self.assertEqual(len(system_en), 931)
        self.assertEqual(len(system_zh), 931)
        self.assertEqual(len(peview_en), 311)
        self.assertEqual(len(peview_zh), 311)
        self.assertRegex(system_header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_ENV_EDIT_WARNING$")
        self.assertRegex(system_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2931$")
        self.assertRegex(peview_header, r"(?m)^#define IDS_PV_FIRST\s+IDS_PV_MENU_ANSI$")
        self.assertRegex(peview_header, r"(?m)^#define IDS_PV_LAST\s+IDS_PV_CERTIFICATE_SIZE_FORMAT$")
        self.assertRegex(peview_header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+3298$")

    def test_helper_returns_owned_copy_after_null_safe_resource_release(self) -> None:
        body = function_body(self.graph_source, "PhpScrollNewGetUiString", self.audit)
        conditional_load = body.index("PhApplicationUiResourceInstance ?")
        load = body.index("PhLoadUiString(")
        safe = body.index("PhGetStringOrDefault(resourceString, Fallback)")
        duplicate = body.index("PhDuplicateStringZ(")
        clear = body.index("PhClearReference(&resourceString);")
        returned = body.index("return menuText;")

        self.assertLess(conditional_load, load)
        self.assertLess(load, duplicate)
        self.assertLess(duplicate, safe)
        self.assertLess(safe, clear)
        self.assertLess(clear, returned)
        self.assertEqual(body.count("PhLoadUiString("), 1)
        self.assertEqual(
            body.count("PhLoadUiString(PhApplicationUiResourceInstance, ResourceId, NULL)"),
            1,
        )
        self.assertEqual(body.count("PhDuplicateStringZ("), 1)
        self.assertEqual(body.count("PhClearReference(&resourceString);"), 1)
        self.assertNotIn("resourceString->Buffer", body)

    def test_all_seven_menu_items_own_helper_allocations_and_bind_exact_routes(self) -> None:
        body = compact(function_body(self.graph_source, "PhScrollNewWndProc", self.audit))
        expected = (
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_SCROLL_HERE,PhpScrollNewGetUiString(IDS_PH_SCROLL_HERE,L"Scroll Here"),NULL,NULL)',
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_TOP,PhpScrollNewGetUiString(isHorz?IDS_PH_SCROLL_LEFT_EDGE:IDS_PH_SCROLL_TOP,isHorz?L"Left Edge":L"Top"),NULL,NULL)',
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_BOTTOM,PhpScrollNewGetUiString(isHorz?IDS_PH_SCROLL_RIGHT_EDGE:IDS_PH_SCROLL_BOTTOM,isHorz?L"Right Edge":L"Bottom"),NULL,NULL)',
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_PAGE_UP,PhpScrollNewGetUiString(isHorz?IDS_PH_SCROLL_PAGE_LEFT:IDS_PH_SCROLL_PAGE_UP,isHorz?L"Page Left":L"Page Up"),NULL,NULL)',
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_PAGE_DOWN,PhpScrollNewGetUiString(isHorz?IDS_PH_SCROLL_PAGE_RIGHT:IDS_PH_SCROLL_PAGE_DOWN,isHorz?L"Page Right":L"Page Down"),NULL,NULL)',
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_SCROLL_UP,PhpScrollNewGetUiString(isHorz?IDS_PH_SCROLL_LEFT:IDS_PH_SCROLL_UP,isHorz?L"Scroll Left":L"Scroll Up"),NULL,NULL)',
            'PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,PH_SCROLLNEW_IDM_SCROLL_DOWN,PhpScrollNewGetUiString(isHorz?IDS_PH_SCROLL_RIGHT:IDS_PH_SCROLL_DOWN,isHorz?L"Scroll Right":L"Scroll Down"),NULL,NULL)',
        )

        for route in expected:
            self.assertIn(compact(route), body)
        self.assertEqual(body.count("PhCreateEMenuItem(PH_EMENU_TEXT_OWNED,"), 7)
        self.assertEqual(body.count("PhpScrollNewGetUiString("), 7)
        for menu_id in (
            "PH_SCROLLNEW_IDM_SCROLL_HERE",
            "PH_SCROLLNEW_IDM_TOP",
            "PH_SCROLLNEW_IDM_BOTTOM",
            "PH_SCROLLNEW_IDM_PAGE_UP",
            "PH_SCROLLNEW_IDM_PAGE_DOWN",
            "PH_SCROLLNEW_IDM_SCROLL_UP",
            "PH_SCROLLNEW_IDM_SCROLL_DOWN",
        ):
            self.assertNotRegex(body, rf"PhCreateEMenuItem\(0,{menu_id},")

        create = body.index("menu=PhCreateEMenu();")
        show = body.index("selectedItem=PhShowEMenu(")
        destroy = body.index("PhDestroyEMenu(menu);")
        self.assertLess(create, show)
        self.assertLess(show, destroy)
        self.assertEqual(body.count("PhDestroyEMenu(menu);"), 1)

    def test_peview_sets_application_resource_instance_immediately_after_phlib_init(self) -> None:
        source = (REPO_ROOT / "tools" / "peview" / "main.c").read_text(encoding="utf-8-sig")
        main = compact(function_body(source, "wWinMain", self.audit))
        expected = compact(
            """
            if (!NT_SUCCESS(PhInitializePhLib(L"PE Viewer")))
                return 1;
            PhApplicationUiResourceInstance = PhInstanceHandle;
            PhSetApplicationUiLanguage(
            """
        )
        self.assertIn(expected, main)
        self.assertLess(main.index("PhApplicationUiResourceInstance=PhInstanceHandle;"), main.index("PvpInitializeUiStrings("))
        self.assertLess(main.index("PhApplicationUiResourceInstance=PhInstanceHandle;"), main.index("PhScrollNewWindowInitialization();"))
        self.assertEqual(main.count("PhApplicationUiResourceInstance=PhInstanceHandle;"), 1)

    def test_audit_recognizes_helper_and_removes_all_scroll_menu_fallbacks(self) -> None:
        entries = []
        self.audit.scan_c_file(str(GRAPH_SOURCE), entries)
        scroll_texts = {row[2] for row in RESOURCES}
        unresolved = [
            (entry["category"], entry["english"], entry["line"])
            for entry in entries
            if entry["english"] in scroll_texts
        ]
        self.assertEqual(unresolved, [])

    def test_runtime_entries_are_retired_and_generated_count_is_exact(self) -> None:
        translations = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        generated = (REPO_ROOT / "phlib" / "phtranslation_zhcn.c").read_text(encoding="utf-8-sig")

        for english in RUNTIME_RETIRED:
            with self.subTest(english=english):
                self.assertNotIn(english, translations["strings"])
                self.assertNotRegex(generated, rf'\{{ L"{re.escape(english)}",')

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "zhcn" / "generate_translation.py"), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2275 entries", result.stdout)

    def test_ci_and_native_generator_counts_are_exact(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(encoding="utf-8")
        generator_test = (REPO_ROOT / "tools" / "zhcn" / "tests" / "test_native_resource_generation.py").read_text(encoding="utf-8")

        self.assertEqual(workflow.count(r"sys_info.exe=931"), 2)
        self.assertEqual(workflow.count(r"peview.exe=311"), 2)
        self.assertNotIn(r"sys_info.exe=598", workflow)
        self.assertNotIn(r"peview.exe=298", workflow)
        self.assertIn('self.assertIn("2571 strings", result.stdout)', generator_test)
        self.assertNotIn('self.assertIn("1737 strings", result.stdout)', generator_test)


if __name__ == "__main__":
    unittest.main()
