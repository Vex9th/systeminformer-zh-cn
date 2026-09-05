#!/usr/bin/env python3
"""Shared manifest contract for the zh-CN audit tools."""


MANIFEST_SCHEMA_VERSION = 2

CALLSITE_MIGRATION_CATEGORIES = {
    "c_balloon",
    "c_combobox",
    "c_listview_group_item",
    "c_msgbox_vararg",
    "c_window_text",
}


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
