#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PHLIB_ROOT = REPO_ROOT / "phlib"
MAIN_ROOT = REPO_ROOT / "SystemInformer"
WINDOW_EXPLORER_ROOT = REPO_ROOT / "plugins" / "WindowExplorer"


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("zhcn_audit_close", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_module()


def source(path):
    return AUDIT.mask_c_comments(path.read_text(encoding="utf-8-sig"))


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


def parse_stringtable(path):
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class CloseNativeResourceTests(unittest.TestCase):
    def test_main_close_id_has_one_shared_definition_and_unchanged_resources(self):
        shared = source(PHLIB_ROOT / "include" / "phappresourceid.h")
        main_header = source(MAIN_ROOT / "resource.h")
        english = parse_stringtable(MAIN_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(MAIN_ROOT / "SystemInformer.zh-cn.rc")

        self.assertRegex(shared, r"(?m)^#define\s+IDS_PH_CLOSE\s+2332$")
        self.assertNotRegex(main_header, r"(?m)^#define\s+IDS_PH_CLOSE\b")
        self.assertIn("#include <phappresourceid.h>", main_header)
        self.assertEqual(english.get("IDS_PH_CLOSE"), "Close")
        self.assertEqual(chinese.get("IDS_PH_CLOSE"), "关闭")

    def test_phlib_property_sheet_close_helper_returns_owned_text_and_releases(self):
        guisup_source = source(PHLIB_ROOT / "guisup.c")
        helper = compact(function_body(guisup_source, "PhpLoadPropSheetCloseText"))
        callback = compact(function_body(guisup_source, "PhModalPropSheetWindowProcedure"))
        load = compact(
            'closeText = PhApplicationUiResourceInstance ? PhLoadUiString('
            'PhApplicationUiResourceInstance, IDS_PH_CLOSE, NULL) : NULL;'
        )
        fallback = compact('if (!closeText) closeText = PhCreateString(L"Close");')
        use = compact(
            'closeText = PhpLoadPropSheetCloseText();'
            'PhSetDialogItemText(hwndDlg, IDCANCEL, closeText->Buffer);'
            'PhClearReference(&closeText);'
        )

        self.assertIn(load, helper)
        self.assertIn(fallback, helper)
        self.assertIn("returncloseText;", helper)
        self.assertIn(use, callback)
        self.assertLess(helper.index(load), helper.index(fallback))
        self.assertLess(
            callback.index("closeText=PhpLoadPropSheetCloseText();"),
            callback.index("PhClearReference(&closeText);"),
        )
        self.assertNotIn("PH_AUTO", helper + callback)

    def test_optional_graph_close_button_copies_text_before_releasing_resource(self):
        graph = compact(function_body(source(PHLIB_ROOT / "graphprp.c"), "PhPropSheetNewWndProc"))
        load = compact(
            'closeText = PhApplicationUiResourceInstance ? PhLoadUiString('
            'PhApplicationUiResourceInstance, IDS_PH_CLOSE, NULL) : NULL;'
        )
        create = compact(
            'context->CloseButton = PhCreateWindow(WC_BUTTON, '
            'PhGetStringOrDefault(closeText, L"Close"),'
        )
        release = compact('PhClearReference(&closeText);')

        self.assertIn("#include<phappresourceid.h>", compact(source(PHLIB_ROOT / "graphprp.c")))
        self.assertIn(load, graph)
        self.assertIn(create, graph)
        self.assertIn(release, graph)
        self.assertLess(graph.index(load), graph.index(create))
        self.assertLess(graph.index(create), graph.index(release))
        close_block = graph[graph.index(load):graph.index(release) + len(release)]
        self.assertNotIn("PH_AUTO", close_block)

    def test_service_error_close_button_uses_runtime_main_resource(self):
        actions = compact(function_body(source(MAIN_ROOT / "actions.c"), "PhUiNavigateServiceErrorDialogPage"))
        self.assertIn("CONSTTASKDIALOG_BUTTONbuttons[2]", actions)
        self.assertIn("CONSTTASKDIALOG_BUTTONbuttonsElevation[2]", actions)
        self.assertNotIn("staticCONSTTASKDIALOG_BUTTON", actions)
        self.assertIn(
            compact('{ IDNO, PhGetApplicationUiString(IDS_PH_CLOSE) }'),
            actions,
        )
        self.assertNotIn(compact('{ IDNO, L"Close" }'), actions)

    def test_window_explorer_resource_json_ci_and_aps_are_exact(self):
        header = source(WINDOW_EXPLORER_ROOT / "resource.h")
        english = parse_stringtable(WINDOW_EXPLORER_ROOT / "WindowExplorer.rc")
        chinese = parse_stringtable(WINDOW_EXPLORER_ROOT / "WindowExplorer.zh-cn.rc")
        translations = json.loads(
            (REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8")
        )
        workflow = (REPO_ROOT / ".github" / "workflows" / "zh-cn-build.yml").read_text(
            encoding="utf-8"
        )

        self.assertRegex(header, r"(?m)^#define\s+IDS_WE_CLOSE\s+12110$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+12168$")
        self.assertEqual(english.get("IDS_WE_CLOSE"), "Close")
        self.assertEqual(chinese.get("IDS_WE_CLOSE"), "关闭")
        self.assertEqual(len(english), 168)
        self.assertEqual(len(chinese), 168)
        self.assertEqual(translations["strings"].get("Close"), "关闭")
        self.assertNotIn("Close", translations["native_strings"])
        self.assertEqual(workflow.count(r"plugins\WindowExplorer.dll=168"), 2)
        self.assertNotIn(r"plugins\WindowExplorer.dll=110", workflow)

    def test_window_explorer_menu_owns_duplicate_after_resource_release(self):
        body = compact(function_body(source(WINDOW_EXPLORER_ROOT / "wnddlg.c"), "WepCreateWindowMenu"))
        helper = compact(function_body(source(WINDOW_EXPLORER_ROOT / "wnddlg.c"), "WepCreateResourceEMenuItem"))
        self.assertIn(compact("menuText = PhLoadUiString(PluginInstance->DllBase, ResourceId, NULL);"), helper)
        self.assertIn(compact("ownedText = PhDuplicateStringZ(PhGetStringOrEmpty(menuText));"), helper)
        self.assertIn(compact("PhClearReference(&menuText);"), helper)
        self.assertIn(compact("PhCreateEMenuItem(Flags | PH_EMENU_TEXT_OWNED, Id, ownedText, NULL, NULL)"), helper)
        self.assertIn(compact("WepCreateResourceEMenuItem(0, ID_WINDOW_CLOSE, IDS_WE_CLOSE)"), body)
        self.assertNotIn("PhFree(ownedText)", helper)
        self.assertNotIn(
            compact('PhCreateEMenuItem(0, ID_WINDOW_CLOSE, L"Close", NULL, NULL)'),
            body,
        )

    def test_close_literals_leave_only_resource_fallbacks(self):
        entries = []
        for path in (
            PHLIB_ROOT / "guisup.c",
            PHLIB_ROOT / "graphprp.c",
            MAIN_ROOT / "actions.c",
            WINDOW_EXPLORER_ROOT / "wnddlg.c",
        ):
            AUDIT.scan_c_file(str(path), entries)

        close_entries = [
            (entry["file"], entry["category"], entry["english"])
            for entry in entries
            if entry["english"] == "Close"
        ]
        self.assertEqual(close_entries, [])
        helper = function_body(
            source(PHLIB_ROOT / "guisup.c"),
            "PhpLoadPropSheetCloseText",
        )
        self.assertEqual(helper.count('L"Close"'), 1)


if __name__ == "__main__":
    unittest.main()
