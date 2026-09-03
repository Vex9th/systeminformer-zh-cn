#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_translation.py - Generate phlib/phtranslation_zhcn.c from
tools/zhcn/zh-CN.json.

The generated file is committed so the Windows build does not depend on
Python. CI regenerates it and fails if the committed copy is stale, keeping
the compiled-in table in sync with the translation source.

The output file is written with a UTF-8 BOM so MSVC parses the source as
UTF-8 regardless of the system code page. The table is sorted by ordinal
UTF-16 code unit order of the English key to match the runtime wcscmp
binary search.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUTPUT = os.path.join(REPO_ROOT, "phlib", "phtranslation_zhcn.c")

ESCAPES = {
    '"': '\\"', "\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r",
}


def c_escape(s: str) -> str:
    out = []
    for ch in s:
        if ch in ESCAPES:
            out.append(ESCAPES[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ch)
        else:
            # Non-ASCII (Chinese text) is emitted literally; the UTF-8 BOM
            # makes MSVC interpret the source correctly.
            out.append(ch)
    return "".join(out)


def utf16_key(s: str):
    """Sort key matching ordinal UTF-16 code unit comparison (wcscmp)."""
    b = s.encode("utf-16-le", "surrogatepass")
    return [b[i] | (b[i + 1] << 8) for i in range(0, len(b), 2)]


def build(translation_path: str):
    with open(translation_path, "r", encoding="utf-8") as f:
        table = json.load(f)
    strings = table.get("strings", {})

    items = [(k, v) for k, v in strings.items() if v and v != k]
    items.sort(key=lambda kv: utf16_key(kv[0]))

    lines = []
    lines.append("/*")
    lines.append(" * GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(" *")
    lines.append(" * Simplified Chinese (zh-CN) string table for the community edition.")
    lines.append(" * Source: tools/zhcn/zh-CN.json")
    lines.append(" * Generator: tools/zhcn/generate_translation.py")
    lines.append(" */")
    lines.append("")
    lines.append("#include <ph.h>")
    lines.append("#include <phtranslation.h>")
    lines.append("")
    lines.append("#include <wchar.h>")
    lines.append("")
    lines.append("const PH_TRANSLATION_ENTRY PhTranslationTableZhCn[%d] =" % len(items))
    lines.append("{")
    for en, zh in items:
        lines.append('    { L"%s", L"%s", },' % (c_escape(en), c_escape(zh)))
    lines.append("};")
    lines.append("")
    lines.append("const ULONG PhTranslationTableZhCnCount = ARRAYSIZE(PhTranslationTableZhCn);")
    lines.append("")
    return "\n".join(lines), len(items)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--translation", default=os.path.join(HERE, "zh-CN.json"))
    ap.add_argument("--output", default=OUTPUT)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed file is up to date instead of writing")
    args = ap.parse_args()

    content, count = build(args.translation)

    if args.check:
        with open(args.output, "rb") as f:
            raw = f.read()
        # Normalize line endings: Windows checkouts may have CRLF.
        current = raw.decode("utf-8-sig").replace("\r\n", "\n")
        if current != content:
            print("error: phlib/phtranslation_zhcn.c is stale; regenerate it")
            return 1
        print("phtranslation_zhcn.c is up to date (%d entries)" % count)
        return 0

    with open(args.output, "wb") as f:
        f.write(b"\xef\xbb\xbf")  # UTF-8 BOM for MSVC
        f.write(content.encode("utf-8"))
    print("wrote %s (%d entries)" % (args.output, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
