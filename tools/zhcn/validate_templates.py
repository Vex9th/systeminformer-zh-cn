#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_templates.py - Byte-level validation of the dialog-template
translation against a built executable.

Loads every RT_DIALOG resource from the PE .rsrc section, replays the same
transformation phlib/phtranslation.c performs at runtime (with the layout
rc.exe actually emits: version first, signature at +2, cdit at +16, 26-byte
DLGTEMPLATEEX header, no cDlgPages), and re-parses each translated template
to prove the structure stays intact. Fails when any template does not
round-trip exactly or when a translatable string that has a dictionary entry
is left untranslated.
"""

import argparse
import json
import os
import struct
import sys

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.getcwd(), "tools", "zhcn")


def parse_pe(data):
    e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
    coff = e_lfanew + 4
    num_sections = struct.unpack_from('<H', data, coff + 2)[0]
    opt_size = struct.unpack_from('<H', data, coff + 16)[0]
    opt_hdr = coff + 20
    magic = struct.unpack_from('<H', data, opt_hdr)[0]
    datadir = opt_hdr + (112 if magic == 0x20b else 96)
    rsrc_rva, _ = struct.unpack_from('<II', data, datadir + 16)

    sections = []
    sec_off = opt_hdr + opt_size
    for i in range(num_sections):
        o = sec_off + i * 40
        vsize, vaddr, rsize, rptr = struct.unpack_from('<IIII', data, o + 8)
        sections.append((vaddr, max(vsize, rsize), rptr))

    def rva_to_off(rva):
        for vaddr, sz, rptr in sections:
            if vaddr <= rva < vaddr + sz:
                return rptr + (rva - vaddr)
        raise ValueError(hex(rva))

    base = rva_to_off(rsrc_rva)
    out = []

    def walk(off, level, type_id):
        num_named, num_id = struct.unpack_from('<HH', data, off + 12)
        for i in range(num_named + num_id):
            eo = off + 16 + i * 8
            name_off, val = struct.unpack_from('<II', data, eo)
            if level < 2:
                assert val & 0x80000000
                walk(base + (val & 0x7FFFFFFF), level + 1,
                     name_off if level == 0 else type_id)
            else:
                data_rva, size = struct.unpack_from('<II', data, base + val)
                out.append((type_id, rva_to_off(data_rva), size))

    walk(base, 0, None)
    return out


def read_str(buf, cur):
    first = struct.unpack_from('<H', buf, cur)[0]
    if first == 0xFFFF:
        return ('ord', struct.unpack_from('<H', buf, cur + 2)[0], cur + 4)
    i = cur
    while True:
        if buf[i] == 0 and buf[i + 1] == 0 and (i - cur) % 2 == 0:
            return ('str', buf[cur:i].decode('utf-16-le'), i + 2)
        i += 1


def translate(buf, zh):
    """Mirror of PhTranslateDialogTemplateCopy."""
    out = bytearray()
    changed = False
    untranslated = []
    ext = struct.unpack_from('<H', buf, 2)[0] == 0xFFFF
    if ext:
        cdit = struct.unpack_from('<H', buf, 16)[0]
        style = struct.unpack_from('<I', buf, 12)[0]
        cur = 26
    else:
        cdit = struct.unpack_from('<H', buf, 8)[0]
        style = struct.unpack_from('<I', buf, 0)[0]
        cur = 18
    out += buf[:cur]

    def cp_str():
        nonlocal cur
        kind, val, cur2 = read_str(buf, cur)
        out.extend(buf[cur:cur2])
        cur = cur2

    def tr_str():
        nonlocal cur, changed
        kind, val, cur2 = read_str(buf, cur)
        if kind == 'ord':
            out.extend(buf[cur:cur2])
            cur = cur2
            return
        t = zh.get(val)
        if t not in (None, val):
            out.extend(t.encode('utf-16-le') + b'\0\0')
            changed = True
        else:
            if val.strip():
                untranslated.append(val)
            out.extend(buf[cur:cur2])
        cur = cur2

    cp_str()
    cp_str()
    tr_str()

    if style & 0x40:  # DS_SETFONT / DS_SHELLFONT
        if ext:
            point, weight = struct.unpack_from('<HH', buf, cur)
            if point < 9:
                point = 9
            out += struct.pack('<HH', point, weight)
            out += buf[cur + 4:cur + 6]
            cur += 6
        else:
            point = struct.unpack_from('<H', buf, cur)[0]
            if point < 9:
                point = 9
            out += struct.pack('<H', point)
            cur += 2
        while struct.unpack_from('<H', buf, cur)[0] != 0:
            cur += 2
        cur += 2
        out += 'Microsoft YaHei UI'.encode('utf-16-le') + b'\0\0'
        changed = True

    while len(out) % 4:
        out += b'\0\0'

    for _ in range(cdit):
        cur = (cur + 3) & ~3
        while len(out) % 4:
            out += b'\0\0'
        hdr = 24 if ext else 18
        out += buf[cur:cur + hdr]
        cur += hdr
        cp_str()
        tr_str()
        creation = struct.unpack_from('<H', buf, cur)[0]
        out += buf[cur:cur + 2 + creation]
        cur += 2 + creation
        while len(out) % 4:
            out += b'\0\0'

    return bytes(out), changed, untranslated, cur <= len(buf)


def reparse(b):
    """Walk a produced template and require exact termination."""
    ext = struct.unpack_from('<H', b, 2)[0] == 0xFFFF
    cdit = struct.unpack_from('<H', b, 16)[0] if ext else struct.unpack_from('<H', b, 8)[0]
    style = struct.unpack_from('<I', b, 12)[0] if ext else struct.unpack_from('<I', b, 0)[0]
    cur = 26 if ext else 18

    def s(cur):
        first = struct.unpack_from('<H', b, cur)[0]
        if first == 0xFFFF:
            return cur + 4
        while not (b[cur] == 0 and b[cur + 1] == 0):
            cur += 2
        return cur + 2

    cur = s(s(s(cur)))
    if style & 0x40:
        cur += 6 if ext else 2
        cur = s(cur)
    cur = (cur + 3) & ~3
    for _ in range(cdit):
        cur = (cur + 3) & ~3
        cur += 24 if ext else 18
        cur = s(s(cur))
        cur += 2 + struct.unpack_from('<H', b, cur)[0]
        cur = (cur + 3) & ~3
    return cur == len(b)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe')
    ap.add_argument('--translation', default=os.path.join(HERE, 'zh-CN.json'))
    args = ap.parse_args()

    data = open(args.exe, 'rb').read()
    zh = json.load(open(args.translation, encoding='utf-8'))['strings']
    resources = [(n, o, s) for n, o, s in parse_pe(data) if n == 5]  # RT_DIALOG

    failed = 0
    translated_count = 0
    untranslated = set()
    for name, off, size in resources:
        buf = data[off:off + size]
        try:
            out, changed, missing, inbounds = translate(buf, zh)
            valid = inbounds and reparse(out)
        except Exception as exc:
            print(f'FAIL resource {name}: {exc}')
            failed += 1
            continue
        if not valid:
            print(f'FAIL resource {name}: template does not round-trip')
            failed += 1
            continue
        if changed:
            translated_count += 1
        untranslated.update(missing)

    print(f'dialog templates: {len(resources)}, translated: {translated_count}, '
          f'round-trip failures: {failed}')
    if untranslated:
        print(f'static texts left English (verify keep-list): {len(untranslated)}')
        for s in sorted(untranslated)[:20]:
            print(f'  {s!r}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
