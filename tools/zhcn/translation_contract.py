#!/usr/bin/env python3
"""Shared manifest contract for the zh-CN audit tools."""


MANIFEST_SCHEMA_VERSION = 2

ALL_CATEGORIES = {
    "c_balloon",
    "c_combobox",
    "c_confirm",
    "c_emenu",
    "c_listview_col",
    "c_listview_group",
    "c_listview_group_item",
    "c_listview_item",
    "c_listview_item_raw",
    "c_msgbox",
    "c_msgbox_vararg",
    "c_runtime_composed",
    "c_search",
    "c_statusbar",
    "c_tab",
    "c_taskdialog",
    "c_toolbar",
    "c_tree_item",
    "c_treenew_col",
    "c_treenew_empty",
    "c_window_text",
    "phlib_internal",
    "rc_dialog",
    "rc_menu",
    "rc_stringtable",
}

CALLSITE_MIGRATION_CATEGORIES = {
    "c_balloon",
    "c_combobox",
    "c_listview_group_item",
    "c_listview_item_raw",
    "c_msgbox_vararg",
    "c_runtime_composed",
    "c_window_text",
}


def canonical_manifest_key(category: str, english: str, module=None):
    """Return the schema-v2 aggregation key for one manifest entry."""
    if category in CALLSITE_MIGRATION_CATEGORIES:
        return module, category, english
    return category, english


def module_for_path(path: str) -> str:
    """Return the independently built application or plugin for a source path."""
    parts = [part for part in path.replace("\\", "/").split("/") if part]

    if not parts:
        raise ValueError("source location path must not be empty")
    if parts[0] in {"plugins", "tools"}:
        if len(parts) < 2:
            raise ValueError(f"source location path has no module name: {path!r}")
        return f"{parts[0]}/{parts[1]}"
    return parts[0]
