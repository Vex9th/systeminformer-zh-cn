#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_translation.py - Validate the zh-CN translation table against the
string manifest and emit an audit report.

Checks performed (exit code 1 on structural failure, 0 otherwise):
  1. manifest freshness is the caller's responsibility; here we join the
     manifest with tools/zhcn/zh-CN.json
  2. duplicate keys in the JSON (json would silently allow them via parser,
     we re-parse raw to detect them)
  3. format specifier consistency between English and Chinese
     (the ordered printf-style conversions must match exactly)
  4. accelerator-key (\t) consistency for menu-style strings
  5. translated / untranslated counts per category and module

Structural failures (1-4) must be fixed before shipping; this report is
audit-oriented and is not a release-level quality guarantee.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

if HERE not in sys.path:
    sys.path.insert(0, HERE)

from translation_contract import (  # noqa: E402
    ALL_CATEGORIES,
    CALLSITE_MIGRATION_CATEGORIES,
    MANIFEST_SCHEMA_VERSION,
    canonical_manifest_key,
    module_for_path,
)

FORMAT_SPEC_RE = re.compile(
    r"(?<![0-9])%(?:%|[-+ #0]*(?:\*|\d+)?(?:\.(?:\*|\d+))?"
    r"(?:I64|I32|ll|hh|[hlLwIjzt])?[diuoxXfFeEgGaAcCsSpn])"
)

# Strings intentionally kept in English: per-CPU graph labels, key names,
# technical acronyms, designer placeholders, product/service names and noise
# fragments. These are excluded from the effective coverage figure and listed
# separately in the report so the exclusion stays transparent.
KEEP_ENGLISH_RULES = [
    r"CPU \d+",
    r"^(Alt|Ctrl|Shift|CPU|I/O|WMI|NTVDM|ANSI|UTF-8|UTF-16|Unicode|DPI|Ping|PCR|PID|RID|RVA|VA|SID|SDDL|MVID|TTL|ASLR|CET|DEP|TID|PnP|DRAM|FPS|GPU|NPU|RAPL|SMART|SMBIOS|SSDEEP|TLSH|DLL|CFG|CLR|CRT|POGO|ProdID|GetProcAddress|SearchControlRegex|SearchControlCaseSensitive)$",
    r"^(PID|TID|MVID|TTL) \(LXSS\)$",
    r"^(Dialog|Static|\(Repurposed\)|<a href=.*|<section placeholder>)$",
    r"^System Informer$",
    r"^(, D |, U |0 ms\.\.\.)$",
    r"^-debug\n$",
    r"^(Hybrid-Analysis|VirusTotal|Worker Factory|PingGraphLayout)$",
]

# Reviewed source formats whose punctuation, units and identifiers are the
# complete UI value. Keep this exact and category-scoped so prose containing a
# format specifier cannot disappear from the untranslated report.
REVIEWED_TECHNICAL_ENTRIES = {
    ("c_runtime_composed", "SystemInformer", " (APP_CONTAINER)"): 1,
    ("c_runtime_composed", "plugins/WindowExplorer", "#%hu"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "%.1f°F (%lu°C)"): 2,
    ("c_runtime_composed", "plugins/ExtendedTools", "%I64u (0x%I64x)"): 2,
    ("c_runtime_composed", "plugins/ExtendedTools", "%I64u MHz"): 2,
    ("c_runtime_composed", "plugins/WindowExplorer", "%lu (0x%x)"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "%lu MB"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "%lu%%"): 2,
    ("c_runtime_composed", "tools/peview", "%lu.%lu"): 8,
    ("c_runtime_composed", "SystemInformer", "%lu: %s\\%s"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "%lu°C"): 2,
    ("c_runtime_composed", "plugins/WindowExplorer", "%s (%s)"): 1,
    ("c_runtime_composed", "tools/peview", "%s (%s)"): 23,
    ("c_runtime_composed", "SystemInformer", "%s (%u)"): 1,
    ("c_runtime_composed", "SystemInformer", "%s (%u) (0x%Ix - 0x%Ix)"): 1,
    ("c_runtime_composed", "tools/peview", "%s - %s"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "%s%s%s"): 1,
    ("c_runtime_composed", "tools/peview", "%s+0x%llx"): 4,
    ("c_runtime_composed", "tools/peview", "%u.%u"): 1,
    ("c_runtime_composed", "SystemInformer", "%ux%u@%u"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "0x%08lx"): 2,
    ("c_runtime_composed", "tools/peview", "0x%I32x"): 3,
    ("c_runtime_composed", "plugins/WindowExplorer", "0x%Ix"): 15,
    ("c_runtime_composed", "plugins/WindowExplorer", "0x%Ix (%s)"): 6,
    ("c_runtime_composed", "tools/peview", "0x%llx"): 3,
    ("c_runtime_composed", "tools/peview", "0x%lx"): 2,
    ("c_runtime_composed", "plugins/WindowExplorer", "0x%x"): 1,
    ("c_runtime_composed", "SystemInformer", "0x%x: %s"): 6,
    ("c_runtime_composed", "tools/peview", "C/C++ (%lu), GS (%lu), sdl (%lu), guardN (%lu), Pre-VC++ 11.00 (%lu)"): 1,
    ("c_runtime_composed", "plugins/ExtendedTools", "WDDM %lu.%lu"): 2,
    ("rc_stringtable", "plugins/HardwareDevices", "%lu°C"): 1,
}

NATIVE_RESOURCE_CATEGORIES = {
    "rc_dialog",
    "rc_menu",
    "rc_stringtable",
    "c_statusbar",
}

RUNTIME_DICTIONARY_CATEGORIES = {
    "c_emenu",
    "c_listview_col",
    "c_listview_group",
    "c_listview_item",
    "c_msgbox",
    "c_confirm",
    "c_taskdialog",
    "c_search",
    "c_tab",
    "c_toolbar",
    "c_tree_item",
    "c_treenew_col",
    "c_treenew_empty",
    "phlib_internal",
}


def is_keep_english(s: str) -> bool:
    return any(re.fullmatch(k, s) for k in KEEP_ENGLISH_RULES)


def is_reviewed_technical_entry(entry) -> bool:
    category = entry["category"]
    english = entry["english"]
    locations = entry["locations"]
    modules = (
        {entry["module"]}
        if entry.get("module") is not None
        else {module_for_path(location["file"]) for location in locations}
    )
    if len(modules) != 1:
        return False

    expected_locations = REVIEWED_TECHNICAL_ENTRIES.get(
        (category, next(iter(modules)), english)
    )
    return expected_locations == len(locations)


def kept_english_manifest_key(entry):
    return canonical_manifest_key(
        entry["category"],
        entry["english"],
        entry.get("module"),
    )


def translation_is_effective(category: str, translated_value) -> bool:
    """Call-site migration categories stay uncovered while literals remain."""
    return bool(translated_value) and category not in CALLSITE_MIGRATION_CATEGORIES


def format_specs(s: str):
    """Return printf format specifiers in their original order."""
    return [
        match.group(0)
        for match in FORMAT_SPEC_RE.finditer(s)
        if match.group(0) != "%%"
    ]


def check_placeholders(en: str, zh: str):
    a, b = format_specs(en), format_specs(zh)
    if a != b:
        return f"format specifiers differ: en={a} zh={b}"
    return None


def check_tabs(en: str, zh: str):
    if en.count("\t") != zh.count("\t"):
        return f"tab counts differ: en={en.count(chr(9))} zh={zh.count(chr(9))}"
    return None


def find_duplicate_keys(path: str):
    dups = set()
    seen = set()
    key_re = re.compile(r'^\s{4}"((?:[^"\\]|\\.)*)":\s')
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = key_re.match(line)
            if not m:
                continue
            raw = json.loads('"' + m.group(1) + '"')
            if raw in seen:
                dups.add(raw)
            seen.add(raw)
    return dups


def json_unescape_key(raw: str) -> str:
    return json.loads('"' + raw + '"')


def translation_decisions(table: dict) -> dict[str, str]:
    runtime_strings = table.get("strings", {})
    native_strings = table.get("native_strings", {})
    overlap = set(runtime_strings) & set(native_strings)

    if overlap:
        raise ValueError(
            "translation keys cannot appear in both strings and native_strings: "
            + ", ".join(sorted(overlap))
        )

    strings = dict(runtime_strings)
    strings.update(native_strings)
    return strings


def translation_for_category(table: dict, category: str, english: str):
    runtime_strings = table.get("strings", {})

    if category in NATIVE_RESOURCE_CATEGORIES:
        value = runtime_strings.get(english)
        if value is not None:
            return value
        return table.get("native_strings", {}).get(english)
    if category in RUNTIME_DICTIONARY_CATEGORIES:
        return runtime_strings.get(english)
    return None


def is_reviewed_native_identity(table: dict, category: str, english: str) -> bool:
    return (
        category in NATIVE_RESOURCE_CATEGORIES
        and table.get("native_strings", {}).get(english) == english
    )


def validate_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {MANIFEST_SCHEMA_VERSION}; regenerate with audit.py"
        )
    if not isinstance(manifest.get("unique_strings"), list):
        raise ValueError("unique_strings must be a list")
    if type(manifest.get("total_occurrences")) is not int:
        raise ValueError("total_occurrences must be an integer")
    if manifest["total_occurrences"] < 0:
        raise ValueError("total_occurrences must not be negative")

    canonical_keys = set()
    location_count = 0

    for entry in manifest["unique_strings"]:
        category = entry.get("category")
        english = entry.get("english")
        locations = entry.get("locations")

        if not isinstance(category, str) or not isinstance(english, str):
            raise ValueError("every entry must have string category and english fields")
        if category not in ALL_CATEGORIES:
            raise ValueError(f"unknown manifest category: {category!r}")
        if not isinstance(locations, list) or not locations:
            raise ValueError(f"entry {category}/{english!r} must have locations")
        location_count += len(locations)
        for location in locations:
            if not isinstance(location, dict):
                raise ValueError(f"entry {category}/{english!r} has an invalid location")
            line = location.get("line")
            if (
                not isinstance(location.get("file"), str)
                or type(line) is not int
                or line < 1
            ):
                raise ValueError(
                    f"entry {category}/{english!r} locations need file and positive line"
                )

        if category in CALLSITE_MIGRATION_CATEGORIES:
            module = entry.get("module")
            if not isinstance(module, str) or not module:
                raise ValueError(
                    f"call-site entry {category}/{english!r} must declare module"
                )
            location_modules = {
                module_for_path(location["file"]) for location in locations
            }
            if location_modules != {module}:
                raise ValueError(
                    f"call-site entry {category}/{english!r} module {module!r} "
                    f"does not match locations {sorted(location_modules)!r}"
                )
        elif "module" in entry:
            raise ValueError(
                f"ordinary entry {category}/{english!r} must not declare module"
            )

        key = canonical_manifest_key(category, english, entry.get("module"))
        if key in canonical_keys:
            raise ValueError(f"duplicate canonical manifest key: {key!r}")
        canonical_keys.add(key)

    if manifest["total_occurrences"] != location_count:
        raise ValueError(
            "total_occurrences does not match the number of locations: "
            f"{manifest['total_occurrences']} != {location_count}"
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=os.path.join(HERE, "manifest.json"))
    ap.add_argument("--translation", default=os.path.join(HERE, "zh-CN.json"))
    ap.add_argument("--report", default=os.path.join(HERE, "coverage-report.md"))
    ap.add_argument("--fail-on-placeholder-error", action="store_true", default=True)
    args = ap.parse_args()

    fail = False

    # ---- load translation -------------------------------------------------
    if not os.path.exists(args.translation):
        print(f"error: translation file not found: {args.translation}")
        return 1
    dups = find_duplicate_keys(args.translation)
    if dups:
        print("error: duplicate keys in translation table:")
        for d in sorted(dups):
            print(f"  {d!r}")
        fail = True
    with open(args.translation, "r", encoding="utf-8") as f:
        table = json.load(f)
    try:
        strings = translation_decisions(table)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    # ---- load manifest ----------------------------------------------------
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    try:
        validate_manifest(manifest)
    except ValueError as exc:
        print(f"error: invalid manifest: {exc}")
        return 1

    # ---- join -------------------------------------------------------------
    errors = []
    untranslated = []          # manifest strings missing from the table
    unused = []                # table keys not present in the manifest
    per_cat = defaultdict(lambda: [0, 0])   # category -> [translated, total]
    per_mod = defaultdict(lambda: [0, 0])   # module    -> [translated, total]

    manifest_keys = set()
    keep_english = {}
    for entry in manifest["unique_strings"]:
        en = entry["english"]
        manifest_keys.add(en)
        category = entry["category"]
        zh = translation_for_category(table, category, en)
        translated = translation_is_effective(
            category,
            zh is not None and zh != en,
        )
        if not translated and (
            is_keep_english(en)
            or is_reviewed_technical_entry(entry)
            or is_reviewed_native_identity(table, category, en)
        ):
            keep_english.setdefault(kept_english_manifest_key(entry), entry)
            continue

        if category in CALLSITE_MIGRATION_CATEGORIES:
            modules = {entry["module"]}
        else:
            modules = {
                module_for_path(location["file"])
                for location in entry["locations"]
            }

        per_cat[category][1] += 1
        for module in modules:
            per_mod[module][1] += 1
        if translated:
            per_cat[category][0] += 1
            for module in modules:
                per_mod[module][0] += 1
            err = check_placeholders(en, zh) or check_tabs(en, zh)
            if err:
                errors.append((en, zh, err))
        else:
            untranslated.append(entry)

    for key in strings:
        if key not in manifest_keys:
            unused.append(key)

    if errors:
        print("error: placeholder/accelerator inconsistencies:")
        for en, zh, err in errors:
            print(f"  {en!r} -> {zh!r}: {err}")
        fail = True

    # ---- report -----------------------------------------------------------
    total_t = sum(v[0] for v in per_cat.values())
    total_a = sum(v[1] for v in per_cat.values())
    untranslated = [e for e in untranslated if not is_keep_english(e["english"])]

    lines = []
    lines.append("# 翻译审计报告 / Translation Audit Report")
    lines.append("")
    lines.append(f"- 有效翻译单元（不含约定保留英文项）：{total_a}")
    lines.append(f"- 已翻译：{total_t}")
    lines.append(f"- 未翻译：{total_a - total_t}")
    lines.append(f"- 约定保留英文（技术缩写/键名/占位符等）：{len(keep_english)} 项")
    migration_categories = "`, `".join(sorted(CALLSITE_MIGRATION_CATEGORIES))
    lines.append(
        f"- `{migration_categories}` 必须迁移调用点；"
        "即使字典存在同名项也不计为已翻译"
    )
    lines.append("")
    lines.append("## 按类别 / By category")
    lines.append("")
    lines.append("| 类别 | 已翻译 | 总数 | 未翻译 |")
    lines.append("|---|---|---|---|")
    for cat in sorted(per_cat):
        t, a = per_cat[cat]
        lines.append(f"| {cat} | {t} | {a} | {a - t} |")
    lines.append("")
    lines.append("## 按模块 / By module")
    lines.append("")
    lines.append(
        "> 模块表统计各模块中的有效出现量；同一普通字符串可在多个模块各计一次，"
        "因此模块行合计不等于上方全局唯一字符串数。"
    )
    lines.append("")
    lines.append("| 模块 | 已翻译 | 总数 | 未翻译 |")
    lines.append("|---|---|---|---|")
    for mod in sorted(per_mod):
        t, a = per_mod[mod]
        lines.append(f"| {mod} | {t} | {a} | {a - t} |")
    lines.append("")
    if keep_english:
        lines.append("## 约定保留英文 / Kept in English by design")
        lines.append("")
        for e in list(keep_english.values())[:80]:
            lines.append(f"- `{e['english']}` ({e['category']})")
        lines.append("")

    if untranslated:
        lines.append("## 未翻译字符串 / Untranslated")
        lines.append("")
        by_cat = defaultdict(list)
        for e in untranslated:
            by_cat[e["category"]].append(e)
        for cat in sorted(by_cat):
            lines.append(f"### {cat} ({len(by_cat[cat])})")
            lines.append("")
            for e in sorted(by_cat[cat], key=lambda x: x["english"].lower())[:400]:
                loc = e["locations"][0]
                lines.append(f"- `{e['english']}` ({loc['file']}:{loc['line']})")
            lines.append("")
    if unused:
        lines.append(f"## 翻译表中存在但清单未引用的条目 / Unused keys ({len(unused)})")
        lines.append("")
        for k in sorted(unused):
            lines.append(f"- `{k}`")
        lines.append("")

    with open(args.report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"translation audit: translated {total_t}/{total_a}, untranslated {total_a - total_t}")
    print(f"untranslated: {len(untranslated)}, unused keys: {len(unused)}, "
          f"placeholder errors: {len(errors)}")
    print(f"report written to {args.report}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
