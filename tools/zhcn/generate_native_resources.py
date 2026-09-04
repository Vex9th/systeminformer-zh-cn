#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the main executable's native zh-CN dialog resources.

The English resource script remains the structural source of truth. This
generator copies every DIALOG/DIALOGEX block, replaces only user-visible text,
and assigns an explicit zh-CN language. CI uses --check so an upstream dialog
change cannot silently leave the localized resource stale.
"""

import argparse
import json
import pathlib
import re
import sys


HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SOURCE_RC = REPO_ROOT / "SystemInformer" / "SystemInformer.rc"
OUTPUT_RC = REPO_ROOT / "SystemInformer" / "SystemInformer.zh-cn.rc"
TRANSLATIONS = HERE / "zh-CN.json"

DIALOG_HEADER_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s+DIALOG(?:EX)?\b")
FONT_RE = re.compile(
    r'^(\s*FONT\s+)(\d+)(\s*,\s*)"[^"]+"(.*)$'
)
CAPTION_RE = re.compile(r'^\s*CAPTION\s+"(?:(?:"")|[^"\\]|\\.)*"')
CONTROL_RE = re.compile(
    r"^\s*(?:LTEXT|RTEXT|CTEXT|PUSHBUTTON|DEFPUSHBUTTON|GROUPBOX|CONTROL|"
    r"AUTOCHECKBOX|AUTORADIOBUTTON|AUTO3STATE|CHECKBOX|RADIOBUTTON|"
    r"CONTROL_MS)\b"
)
FIRST_STRING_RE = re.compile(r'"((?:""|[^"\\]|\\.)*)"')


def extract_dialog_blocks(source: str) -> list[list[str]]:
    lines = source.splitlines()
    blocks: list[list[str]] = []
    index = 0

    while index < len(lines):
        if not DIALOG_HEADER_RE.match(lines[index]):
            index += 1
            continue

        start = index
        depth = 0
        found_begin = False

        while index < len(lines):
            token = lines[index].strip()

            if token == "BEGIN":
                found_begin = True
                depth += 1
            elif token == "END" and found_begin:
                depth -= 1
                if depth == 0:
                    blocks.append(lines[start:index + 1])
                    index += 1
                    break

            index += 1
        else:
            raise ValueError(f"unterminated dialog block at line {start + 1}")

    return blocks


def replace_first_string(line: str, translations: dict[str, str]) -> str:
    match = FIRST_STRING_RE.search(line)

    if not match:
        return line

    english = match.group(1).replace('""', '"')
    if not english:
        return line

    if english not in translations:
        raise ValueError(f"missing translation decision for dialog text: {english!r}")

    chinese = translations[english]

    if not chinese:
        raise ValueError(f"empty translation decision for dialog text: {english!r}")

    if chinese == english:
        return line

    chinese = chinese.replace('"', '""')
    return line[:match.start(1)] + chinese + line[match.end(1):]


def localize_dialog_block(
    block: list[str],
    translations: dict[str, str],
) -> list[str]:
    localized: list[str] = []

    for line in block:
        font_match = FONT_RE.match(line)

        if font_match:
            point_size = max(int(font_match.group(2)), 9)
            localized.append(
                f'{font_match.group(1)}{point_size}{font_match.group(3)}'
                f'"Microsoft YaHei UI"{font_match.group(4)}'
            )
            continue

        caption_match = CAPTION_RE.match(line)
        if caption_match:
            localized.append(replace_first_string(line, translations))
            continue

        if CONTROL_RE.match(line):
            localized.append(replace_first_string(line, translations))
            continue

        localized.append(line)

    return localized


def build(source_path: pathlib.Path, translation_path: pathlib.Path) -> str:
    source = source_path.read_text(encoding="utf-8-sig")
    translation_data = json.loads(translation_path.read_text(encoding="utf-8"))
    translations = translation_data["strings"]
    blocks = extract_dialog_blocks(source)

    if not blocks:
        raise ValueError(f"no dialog resources found in {source_path}")

    lines = [
        "// GENERATED FILE - DO NOT EDIT MANUALLY",
        "// Source: SystemInformer/SystemInformer.rc",
        "// Translations: tools/zhcn/zh-CN.json",
        "// Generator: tools/zhcn/generate_native_resources.py",
        "",
        "#pragma code_page(65001)",
        "",
        '#include "resource.h"',
        '#include "winres.h"',
        '#include "include/phappres.h"',
        "",
        "LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED",
        "",
    ]

    for block in blocks:
        lines.extend(localize_dialog_block(block, translations))
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE_RC)
    parser.add_argument("--translation", type=pathlib.Path, default=TRANSLATIONS)
    parser.add_argument("--output", type=pathlib.Path, default=OUTPUT_RC)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        content = build(args.source, args.translation)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1

    if args.check:
        try:
            current = args.output.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        except OSError as exc:
            print(f"error: {exc}")
            return 1

        if current != content:
            print(f"error: {args.output} is stale; regenerate it")
            return 1

        print(f"native zh-CN resources are current ({len(extract_dialog_blocks(content))} dialogs)")
        return 0

    args.output.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    print(f"wrote {args.output} ({len(extract_dialog_blocks(content))} dialogs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
