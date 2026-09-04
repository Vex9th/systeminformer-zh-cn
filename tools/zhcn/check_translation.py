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
     (the multiset of printf-style conversions must match)
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

FORMAT_SPEC_RE = re.compile(r"%(?:%|[0-9]*(?:\.[0-9]+)?(?:I64|ll|l|L|h|hh|w|I)?[a-zA-Z])")

# Strings intentionally kept in English: per-CPU graph labels, key names,
# technical acronyms, designer placeholders, product/service names and noise
# fragments. These are excluded from the effective coverage figure and listed
# separately in the report so the exclusion stays transparent.
KEEP_ENGLISH_RULES = [
    r"CPU \d+",
    r"^(Alt|Ctrl|Shift|CPU|I/O|WMI|NTVDM|ANSI|Unicode|DPI|Ping|PCR|PID|SID|SDDL|MVID|TTL|ASLR|CET|DEP|TID|PnP|DRAM|FPS|GPU|NPU|RAPL|SMART|SMBIOS)$",
    r"^(PID|TID|MVID|TTL) \(LXSS\)$",
    r"^(Dialog|Static|\(Repurposed\)|<a href=.*|<section placeholder>)$",
    r"^System Informer$",
    r"^(, D |, U |0 ms\.\.\.)$",
    r"^-debug\n$",
    r"^(Hybrid-Analysis|VirusTotal|Worker Factory|PingGraphLayout)$",
]


def is_keep_english(s: str) -> bool:
    return any(re.fullmatch(k, s) for k in KEEP_ENGLISH_RULES)


def format_specs(s: str):
    """Return the multiset (sorted list) of printf format specifiers.

    Width/precision are folded to '*' so that legitimate adjustments to
    field widths do not count as mismatches; type and size must match."""
    out = []
    for m in FORMAT_SPEC_RE.finditer(s):
        spec = m.group(0)
        if spec == "%%":
            continue
        body = spec[1:]
        body = re.sub(r"^\d+", "", body)
        body = re.sub(r"^\.\d+", "", body)
        out.append(body)
    return sorted(out)


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
    strings = table.get("strings", {})

    # ---- load manifest ----------------------------------------------------
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # ---- join -------------------------------------------------------------
    errors = []
    untranslated = []          # manifest strings missing from the table
    unused = []                # table keys not present in the manifest
    per_cat = defaultdict(lambda: [0, 0])   # category -> [translated, total]
    per_mod = defaultdict(lambda: [0, 0])   # module    -> [translated, total]

    manifest_keys = set()
    keep_english = []
    for entry in manifest["unique_strings"]:
        en = entry["english"]
        manifest_keys.add(en)
        module = entry["locations"][0]["file"].split("/")[0]
        if "/" in entry["locations"][0]["file"]:
            sub = entry["locations"][0]["file"].split("/")[1]
            if module == "plugins":
                module = f"plugins/{sub}"
        zh = strings.get(en)
        translated = zh is not None and zh != en
        if not translated and is_keep_english(en):
            keep_english.append(entry)
            continue
        per_cat[entry["category"]][1] += 1
        per_mod[module][1] += 1
        if translated:
            per_cat[entry["category"]][0] += 1
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
    lines.append(f"- 清单唯一字符串（不含约定保留英文项）：{total_a}")
    lines.append(f"- 已翻译：{total_t}")
    lines.append(f"- 未翻译：{total_a - total_t}")
    lines.append(f"- 约定保留英文（技术缩写/键名/占位符等）：{len(keep_english)} 项")
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
    lines.append("| 模块 | 已翻译 | 总数 | 未翻译 |")
    lines.append("|---|---|---|---|")
    for mod in sorted(per_mod):
        t, a = per_mod[mod]
        lines.append(f"| {mod} | {t} | {a} | {a - t} |")
    lines.append("")
    if keep_english:
        lines.append("## 约定保留英文 / Kept in English by design")
        lines.append("")
        for e in keep_english[:80]:
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
