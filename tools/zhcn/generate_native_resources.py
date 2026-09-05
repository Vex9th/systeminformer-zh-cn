#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate native zh-CN UI resources for the executable, plugins and tools.

The English resource script remains the structural source of truth. This
generator copies every DIALOG/DIALOGEX and STRINGTABLE block, replaces only
user-visible text, and assigns an explicit zh-CN language. CI uses --check so
an upstream UI resource change cannot silently leave the localized resource
stale.
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
STRINGTABLE_HEADER_RE = re.compile(r"^\s*STRINGTABLE\b")
STRING_ENTRY_RE = re.compile(r'^\s*(?:[A-Z][A-Z0-9_]*|\d+)\s+"')
CAPTION_RE = re.compile(r'^\s*CAPTION\s+"(?:(?:"")|[^"\\]|\\.)*"')
CONTROL_RE = re.compile(
    r"^\s*(?:LTEXT|RTEXT|CTEXT|PUSHBUTTON|DEFPUSHBUTTON|GROUPBOX|CONTROL|"
    r"AUTOCHECKBOX|AUTORADIOBUTTON|AUTO3STATE|CHECKBOX|RADIOBUTTON|"
    r"CONTROL_MS)\b"
)
FIRST_STRING_RE = re.compile(r'"((?:""|[^"\\]|\\.)*)"')
INCLUDE_RE = re.compile(r'^#include\s+"([^"]+)"\s*$')
RC_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
}


def decode_rc_string(value: str) -> str:
    value = value.replace('""', '"')
    decoded: list[str] = []
    index = 0

    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            escaped = RC_ESCAPES.get(value[index + 1])
            if escaped is not None:
                decoded.append(escaped)
                index += 2
                continue

        decoded.append(value[index])
        index += 1

    return "".join(decoded)


def encode_rc_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\a", "\\a")
        .replace("\b", "\\b")
        .replace("\f", "\\f")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\v", "\\v")
        .replace('"', '""')
    )


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


def extract_stringtable_blocks(source: str) -> list[list[str]]:
    lines = source.splitlines()
    blocks: list[list[str]] = []
    index = 0

    while index < len(lines):
        if not STRINGTABLE_HEADER_RE.match(lines[index]):
            index += 1
            continue

        start = index
        found_begin = False

        while index < len(lines):
            token = lines[index].strip()

            if token == "BEGIN":
                found_begin = True
            elif token == "END" and found_begin:
                blocks.append(lines[start:index + 1])
                index += 1
                break

            index += 1
        else:
            raise ValueError(f"unterminated string table block at line {start + 1}")

    return blocks


def replace_first_string(
    line: str,
    translations: dict[str, str],
    decode_escapes: bool = False,
) -> str:
    match = FIRST_STRING_RE.search(line)

    if not match:
        return line

    english = (
        decode_rc_string(match.group(1))
        if decode_escapes
        else match.group(1).replace('""', '"')
    )
    if not english:
        return line

    if english not in translations:
        raise ValueError(f"missing translation decision for UI resource text: {english!r}")

    chinese = translations[english]

    if not chinese:
        raise ValueError(f"empty translation decision for UI resource text: {english!r}")

    if chinese == english:
        return line

    chinese = (
        encode_rc_string(chinese)
        if decode_escapes
        else chinese.replace('"', '""')
    )
    return line[:match.start(1)] + chinese + line[match.end(1):]


def localize_dialog_block(
    block: list[str],
    translations: dict[str, str],
) -> list[str]:
    localized: list[str] = []

    for line in block:
        caption_match = CAPTION_RE.match(line)
        if caption_match:
            localized.append(replace_first_string(line, translations))
            continue

        if CONTROL_RE.match(line):
            localized.append(replace_first_string(line, translations))
            continue

        localized.append(line)

    return localized


def localize_stringtable_block(
    block: list[str],
    translations: dict[str, str],
) -> list[str]:
    localized: list[str] = []

    for line in block:
        if STRING_ENTRY_RE.match(line):
            localized.append(replace_first_string(line, translations, decode_escapes=True))
        else:
            localized.append(line)

    return localized


def source_label(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def translation_decisions(translation_data: dict) -> dict[str, str]:
    runtime_strings = translation_data.get("strings", {})
    native_strings = translation_data.get("native_strings", {})
    overlap = set(runtime_strings) & set(native_strings)

    if overlap:
        raise ValueError(
            "translation keys cannot appear in both strings and native_strings: "
            + ", ".join(sorted(overlap))
        )

    translations = dict(runtime_strings)
    translations.update(native_strings)
    return translations


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
    translations = translation_decisions(translation_data)
    blocks = extract_dialog_blocks(source)
    stringtable_blocks = extract_stringtable_blocks(source)

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

    for block in stringtable_blocks:
        lines.extend(localize_stringtable_block(block, translations))
        lines.append("")

    return "\n".join(lines)


def process_module(
    source: pathlib.Path,
    output: pathlib.Path,
    translation: pathlib.Path,
    check: bool,
) -> tuple[int, int, int]:
    content = build(source, translation)
    dialog_count = len(extract_dialog_blocks(content))
    string_count = sum(
        sum(1 for line in block if STRING_ENTRY_RE.match(line))
        for block in extract_stringtable_blocks(content)
    )

    if check:
        current = output.read_text(encoding="utf-8-sig").replace("\r\n", "\n")

        if current != content:
            raise ValueError(f"{output} is stale; regenerate it")
    else:
        output.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

    return 1, dialog_count, string_count


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
    string_count = 0

    try:
        for source, output in modules:
            processed_modules, processed_dialogs, processed_strings = process_module(
                source,
                output,
                args.translation,
                args.check,
            )
            module_count += processed_modules
            dialog_count += processed_dialogs
            string_count += processed_strings
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1

    if args.check:
        print(
            f"native zh-CN resources are current "
            f"({module_count} modules, {dialog_count} dialogs, "
            f"{string_count} strings)"
        )
        return 0

    print(
        f"wrote {module_count} modules "
        f"({dialog_count} dialogs, {string_count} strings)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
