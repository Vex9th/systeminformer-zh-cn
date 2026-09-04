#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate native zh-CN dialog resources for the executable and plugins.

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
PLUGIN_NAMES = (
    "DotNetTools",
    "ExtendedNotifications",
    "ExtendedServices",
    "ExtendedTools",
    "HardwareDevices",
    "NetworkTools",
    "OnlineChecks",
    "ToolStatus",
    "Updater",
    "UserNotes",
    "WindowExplorer",
)
RESOURCE_MODULES = (
    (SOURCE_RC, OUTPUT_RC),
    *(
        (
            REPO_ROOT / "plugins" / name / f"{name}.rc",
            REPO_ROOT / "plugins" / name / f"{name}.zh-cn.rc",
        )
        for name in PLUGIN_NAMES
    ),
    (
        REPO_ROOT / "tools" / "peview" / "peview.rc",
        REPO_ROOT / "tools" / "peview" / "peview.zh-cn.rc",
    ),
    (
        REPO_ROOT / "tools" / "CustomSetupTool" / "resource.rc",
        REPO_ROOT / "tools" / "CustomSetupTool" / "resource.zh-cn.rc",
    ),
)

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
INCLUDE_RE = re.compile(r'^#include\s+"([^"]+)"\s*$')


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


def source_label(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def source_includes(source: str) -> list[str]:
    includes = []

    for line in source.splitlines():
        match = INCLUDE_RE.match(line)

        if not match:
            continue

        include_path = match.group(1).lower()
        if include_path.endswith((".rc", ".rc2")):
            raise ValueError(f"nested resource script include is not allowed: {match.group(1)}")

        if line not in includes:
            includes.append(line)

    if not includes:
        raise ValueError("resource source contains no direct #include directives")

    return includes


def build(source_path: pathlib.Path, translation_path: pathlib.Path) -> str:
    source = source_path.read_text(encoding="utf-8-sig")
    translation_data = json.loads(translation_path.read_text(encoding="utf-8"))
    translations = translation_data["strings"]
    blocks = extract_dialog_blocks(source)

    if not blocks:
        raise ValueError(f"no dialog resources found in {source_path}")

    lines = [
        "// GENERATED FILE - DO NOT EDIT MANUALLY",
        f"// Source: {source_label(source_path)}",
        "// Translations: tools/zhcn/zh-CN.json",
        "// Generator: tools/zhcn/generate_native_resources.py",
        "",
        *source_includes(source),
        "",
        "LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED",
        "",
    ]

    for block in blocks:
        lines.extend(localize_dialog_block(block, translations))
        lines.append("")

    return "\n".join(lines)


def process_module(
    source: pathlib.Path,
    output: pathlib.Path,
    translation: pathlib.Path,
    check: bool,
) -> tuple[int, int]:
    content = build(source, translation)
    dialog_count = len(extract_dialog_blocks(content))

    if check:
        current = output.read_text(encoding="utf-8-sig").replace("\r\n", "\n")

        if current != content:
            raise ValueError(f"{output} is stale; regenerate it")
    else:
        output.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

    return 1, dialog_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path)
    parser.add_argument("--translation", type=pathlib.Path, default=TRANSLATIONS)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if bool(args.source) != bool(args.output):
        parser.error("--source and --output must be used together")

    modules = (
        ((args.source, args.output),)
        if args.source
        else RESOURCE_MODULES
    )
    module_count = 0
    dialog_count = 0

    try:
        for source, output in modules:
            processed_modules, processed_dialogs = process_module(
                source,
                output,
                args.translation,
                args.check,
            )
            module_count += processed_modules
            dialog_count += processed_dialogs
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1

    if args.check:
        print(
            f"native zh-CN resources are current "
            f"({module_count} modules, {dialog_count} dialogs)"
        )
        return 0

    print(f"wrote {module_count} modules ({dialog_count} dialogs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
