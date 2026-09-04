#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate embedded en-US and zh-CN dialog resources in a built PE file.

This checks the compiled resource tree rather than replaying the retired
runtime text-rewrite algorithm. Every en-US dialog must have a zh-CN resource
with the same structural template, and every zh-CN font must be explicit and
usable without font fallback.
"""

import argparse
import struct
import sys


RT_DIALOG = 5
LANG_EN_US = 0x0409
LANG_ZH_CN = 0x0804
DS_SETFONT = 0x0040


def unpack_from(fmt: str, data: bytes, offset: int):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise ValueError(f"read outside resource at {offset:#x}")
    return struct.unpack_from(fmt, data, offset)


def parse_pe_resources(data: bytes):
    e_lfanew = unpack_from("<I", data, 0x3C)[0]
    coff = e_lfanew + 4
    number_of_sections = unpack_from("<H", data, coff + 2)[0]
    optional_header_size = unpack_from("<H", data, coff + 16)[0]
    optional_header = coff + 20
    magic = unpack_from("<H", data, optional_header)[0]
    data_directory = optional_header + (112 if magic == 0x20B else 96)
    resource_rva, _ = unpack_from("<II", data, data_directory + 16)
    section_table = optional_header + optional_header_size
    sections = []

    for index in range(number_of_sections):
        offset = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = unpack_from(
            "<IIII", data, offset + 8
        )
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))

    def rva_to_offset(rva: int) -> int:
        for virtual_address, size, raw_pointer in sections:
            if virtual_address <= rva < virtual_address + size:
                return raw_pointer + rva - virtual_address
        raise ValueError(f"RVA outside sections: {rva:#x}")

    resource_base = rva_to_offset(resource_rva)
    resources = []

    def entry_key(raw_key: int):
        if not raw_key & 0x80000000:
            return raw_key

        offset = resource_base + (raw_key & 0x7FFFFFFF)
        length = unpack_from("<H", data, offset)[0]
        start = offset + 2
        end = start + length * 2
        if end > len(data):
            raise ValueError("resource name outside file")
        return data[start:end].decode("utf-16-le")

    def walk(directory_offset: int, path: tuple):
        named_count, id_count = unpack_from("<HH", data, directory_offset + 12)

        for index in range(named_count + id_count):
            entry_offset = directory_offset + 16 + index * 8
            raw_key, raw_value = unpack_from("<II", data, entry_offset)
            key = entry_key(raw_key)

            if raw_value & 0x80000000:
                walk(resource_base + (raw_value & 0x7FFFFFFF), path + (key,))
                continue

            if len(path) != 2:
                raise ValueError(f"unexpected PE resource path: {path + (key,)}")

            data_entry = resource_base + raw_value
            data_rva, size = unpack_from("<II", data, data_entry)
            offset = rva_to_offset(data_rva)
            if offset + size > len(data):
                raise ValueError("resource data outside file")
            resources.append((path[0], path[1], key, data[offset:offset + size]))

    walk(resource_base, ())
    return resources


def read_template_value(data: bytes, offset: int):
    first = unpack_from("<H", data, offset)[0]

    if first == 0xFFFF:
        return ("ordinal", unpack_from("<H", data, offset + 2)[0]), offset + 4

    end = offset
    while unpack_from("<H", data, end)[0] != 0:
        end += 2

    return ("string", data[offset:end].decode("utf-16-le")), end + 2


def parse_dialog_template(data: bytes):
    extended = unpack_from("<H", data, 2)[0] == 0xFFFF

    if extended:
        item_count = unpack_from("<H", data, 16)[0]
        style = unpack_from("<I", data, 12)[0]
        header = data[:26]
        offset = 26
    else:
        item_count = unpack_from("<H", data, 8)[0]
        style = unpack_from("<I", data, 0)[0]
        header = data[:18]
        offset = 18

    menu, offset = read_template_value(data, offset)
    window_class, offset = read_template_value(data, offset)
    caption, offset = read_template_value(data, offset)
    font = None

    if style & DS_SETFONT:
        if extended:
            point_size, weight = unpack_from("<HH", data, offset)
            italic, charset = unpack_from("<BB", data, offset + 4)
            offset += 6
            font_prefix = (point_size, weight, italic, charset)
        else:
            point_size = unpack_from("<H", data, offset)[0]
            offset += 2
            font_prefix = (point_size,)

        typeface, offset = read_template_value(data, offset)
        if typeface[0] != "string":
            raise ValueError("dialog typeface is not a string")
        font = font_prefix + (typeface[1],)

    offset = (offset + 3) & ~3
    controls = []
    visible_strings = [caption[1]] if caption[0] == "string" else []

    for _ in range(item_count):
        offset = (offset + 3) & ~3
        item_header_size = 24 if extended else 18
        item_header = data[offset:offset + item_header_size]
        if len(item_header) != item_header_size:
            raise ValueError("truncated dialog item header")
        offset += item_header_size
        item_class, offset = read_template_value(data, offset)
        item_text, offset = read_template_value(data, offset)
        creation_size = unpack_from("<H", data, offset)[0]
        creation_bytes = creation_size if creation_size else 2
        creation_data = data[offset:offset + creation_bytes]
        if len(creation_data) != creation_bytes:
            raise ValueError("truncated dialog creation data")
        offset += creation_bytes
        structural_text = item_text if item_text[0] == "ordinal" else ("string",)
        controls.append((item_header, item_class, structural_text, creation_data))
        if item_text[0] == "string":
            visible_strings.append(item_text[1])

    trailing = data[offset:]
    if len(trailing) > 3 or any(trailing):
        raise ValueError(f"dialog parser ended at {offset}, resource size is {len(data)}")

    structure = (extended, header, menu, window_class, tuple(controls))
    return {
        "structure": structure,
        "font": font,
        "strings": visible_strings,
    }


def dialog_font_attributes(font):
    if not font:
        return None
    if len(font) == 5:
        return font[1:4]
    if len(font) == 2:
        return ()
    raise ValueError(f"unexpected dialog font tuple: {font!r}")


def contains_han(text: str) -> bool:
    return any("\u3400" <= character <= "\u9fff" for character in text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe")
    args = parser.parse_args()

    try:
        with open(args.exe, "rb") as file:
            resources = parse_pe_resources(file.read())
    except (OSError, ValueError, struct.error, UnicodeDecodeError) as exc:
        print(f"error: {exc}")
        return 1

    dialogs = {}
    for resource_type, resource_name, language_id, resource_data in resources:
        if resource_type == RT_DIALOG:
            dialogs[(resource_name, language_id)] = resource_data

    english_ids = {name for name, language in dialogs if language == LANG_EN_US}
    chinese_ids = {name for name, language in dialogs if language == LANG_ZH_CN}
    missing_chinese = sorted(english_ids - chinese_ids, key=str)
    unexpected_chinese = sorted(chinese_ids - english_ids, key=str)
    failures = 0
    chinese_dialogs_with_han = 0

    if missing_chinese:
        print(f"FAIL missing zh-CN dialogs: {missing_chinese}")
        failures += len(missing_chinese)
    if unexpected_chinese:
        print(f"FAIL zh-CN dialogs without en-US source: {unexpected_chinese}")
        failures += len(unexpected_chinese)

    for resource_name in sorted(english_ids & chinese_ids, key=str):
        try:
            english = parse_dialog_template(dialogs[(resource_name, LANG_EN_US)])
            chinese = parse_dialog_template(dialogs[(resource_name, LANG_ZH_CN)])
        except (ValueError, struct.error, UnicodeDecodeError) as exc:
            print(f"FAIL dialog {resource_name}: {exc}")
            failures += 1
            continue

        if english["structure"] != chinese["structure"]:
            print(f"FAIL dialog {resource_name}: structural resource mismatch")
            failures += 1

        font = chinese["font"]
        if not font or font[0] < 9 or font[-1] != "Microsoft YaHei UI":
            print(f"FAIL dialog {resource_name}: invalid zh-CN font {font!r}")
            failures += 1
        elif dialog_font_attributes(english["font"]) != dialog_font_attributes(font):
            print(f"FAIL dialog {resource_name}: zh-CN font attributes changed")
            failures += 1

        if any(contains_han(text) for text in chinese["strings"]):
            chinese_dialogs_with_han += 1

    if not english_ids:
        print("FAIL no en-US dialog resources found")
        failures += 1
    if not chinese_ids:
        print("FAIL no zh-CN dialog resources found")
        failures += 1
    if chinese_ids and not chinese_dialogs_with_han:
        print("FAIL zh-CN dialogs contain no Chinese text")
        failures += 1

    print(
        f"native dialogs: en-US {len(english_ids)}, zh-CN {len(chinese_ids)}, "
        f"zh-CN dialogs with Chinese text {chinese_dialogs_with_han}, failures {failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
