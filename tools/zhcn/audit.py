#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit.py - Extract all user-visible strings from the System Informer source
tree into a machine-readable manifest, classified by where the string comes
from and which runtime translation funnel covers it.

The manifest is the single source of truth for translation coverage. It is
regenerated on every check; it is derived data and must not be committed.

Categories (each maps to a runtime translation hook in phlib or the exe):
  rc_dialog        dialog template controls and captions (.rc DIALOG/DIALOGEX)
  rc_menu          menu resources (.rc MENU/MENUEX)
  c_emenu          PhCreateEMenuItem / PhCreateEMenuItemCallback text
  c_listview_col   PhAddListViewColumn* text
  c_treenew_col    PhAddTreeNewColumn* text
  c_msgbox         PhShowMessage* family format/title arguments
  c_confirm        PhShowConfirmMessage verb/object/message arguments
  c_taskdialog     TASKDIALOGCONFIG literal fields (title/content/buttons/...)
  c_balloon        PhNfShowBalloonTip title/text
  c_search         PhCreateSearchControl* banner text
  c_tab            PhTabNew_InsertItem tab labels
  c_statusbar      ToolStatus status bar format templates (patched call sites)
  phlib_internal   literals embedded inside phlib funnel implementations
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------------------
# C wide string literal handling
# ---------------------------------------------------------------------------

C_LITERAL_RE = re.compile(r'L"(?:[^"\\]|\\.)*"')

C_ESCAPES = {
    "t": "\t", "n": "\n", "r": "\r", "\\": "\\", '"': '"',
    "'": "'", "0": "\0", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
}


def c_unescape(body: str) -> str:
    out = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt in C_ESCAPES:
                out.append(C_ESCAPES[nxt])
                i += 2
                continue
            if nxt == "x" or nxt == "X":
                j = i + 2
                hexs = ""
                while j < len(body) and len(hexs) < 4 and body[j] in "0123456789abcdefABCDEF":
                    hexs += body[j]
                    j += 1
                if hexs:
                    out.append(chr(int(hexs, 16)))
                    i = j
                    continue
        out.append(ch)
        i += 1
    return "".join(out)


def literal_text(lit: str) -> str:
    """Return the decoded text of an L"..." literal (without the L and quotes)."""
    return c_unescape(lit[2:-1])


def has_letters(s: str) -> bool:
    return re.search(r"[A-Za-z]", s) is not None


def is_noise(s: str) -> bool:
    """Heuristic filter for strings that are not user-visible prose."""
    if not has_letters(s):
        return True
    stripped = s.strip()
    if not stripped:
        return True
    # Registry paths, URLs, format-only fragments, single characters
    if re.match(r"^(\\\\|https?://|www\.|%[sdluxX]|\*)", stripped):
        return True
    if len(stripped) == 1 and not stripped.isalpha():
        return True
    # Accelerator-only or ellipsis-only fragments
    if re.fullmatch(r"[&.()\[\]{}:,%\s]+", stripped):
        return True
    return False


# ---------------------------------------------------------------------------
# Balanced parenthesis call extraction
# ---------------------------------------------------------------------------

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def find_calls(text: str, func_names):
    """Yield (func_name, args, arg_spans, call_start) for each call of
    func_names. args is a list of raw source strings split at top-level
    commas. Handles nesting of (), [] and {} and string literals."""
    wanted = set(func_names)
    for m in IDENT_RE.finditer(text):
        name = m.group(0)
        if name not in wanted:
            continue
        i = m.end()
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "(":
            continue
        depth = 0
        j = i
        args = []
        spans = []
        start = i + 1
        in_str = False
        while j < len(text):
            ch = text[j]
            if in_str:
                if ch == "\\":
                    j += 2
                    continue
                if ch == '"':
                    in_str = False
                j += 1
                continue
            if ch == '"':
                in_str = True
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    args.append(text[start:j])
                    spans.append((start, j))
                    break
            elif ch == "," and depth == 1:
                args.append(text[start:j])
                spans.append((start, j))
                start = j + 1
            j += 1
        else:
            continue
        yield name, args, spans, m.start()


def first_literal(arg: str):
    m = C_LITERAL_RE.search(arg)
    if m:
        return literal_text(m.group(0))
    return None


def all_literals(arg: str):
    return [literal_text(m.group(0)) for m in C_LITERAL_RE.finditer(arg)]


# ---------------------------------------------------------------------------
# C/C++ source scanning
# ---------------------------------------------------------------------------

# function name -> {arg index: category} ; None index = "last arg"
CALL_SPECS = {
    "PhCreateEMenuItem": {2: "c_emenu"},
    "PhCreateEMenuItemCallback": {2: "c_emenu"},
    "PhAddListViewColumn": {None: "c_listview_col"},
    "PhAddListViewColumnDpi": {None: "c_listview_col"},
    "PhAddIListViewColumn": {None: "c_listview_col"},
    "PhAddIListViewColumnDpi": {None: "c_listview_col"},
    "PhAddTreeNewColumn": {3: "c_treenew_col"},
    "PhAddTreeNewColumnEx": {3: "c_treenew_col"},
    "PhAddTreeNewColumnEx2": {3: "c_treenew_col"},
    "PhShowMessage": {2: "c_msgbox"},
    "PhShowMessage2": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowError": {2: "c_msgbox"},
    "PhShowWarning": {2: "c_msgbox"},
    "PhShowInformation": {2: "c_msgbox"},
    "PhShowError2": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowWarning2": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowInformation2": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowMessageOneTime": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowMessageOneTime2": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowConfirmMessage": {1: "c_confirm", 2: "c_confirm", 3: "c_confirm"},
    "PhAddListViewItem": {2: "c_listview_item"},
    "PhAddIListViewItem": {2: "c_listview_item"},
    "PhNfShowBalloonTip": {0: "c_balloon", 1: "c_balloon"},
    "PhNfShowBalloonTipEx": {0: "c_balloon", 1: "c_balloon"},
}

# any literal argument counts (few-literal calls)
ANY_LITERAL_SPECS = {
    "PhCreateSearchControl": "c_search",
    "PhCreateSearchControlEx": "c_search",
}

TASKDIALOG_FIELDS_RE = re.compile(
    r"\bpsz(MainInstruction|Content|VerificationText|ButtonText|Footer|"
    r"CollapsedControlText|ExpandedControlText|WindowTitle)\s*=\s*(L\"(?:[^\"\\]|\\.)*\")"
)

# Literals inside the phlib funnel implementations themselves. These are
# covered by dedicated translation hooks; keep in sync with phlib/util.c.
PHLIB_INTERNAL = {
    "phlib/util.c": [
        (1610, "Do you want to "),
        (1612, " Are you sure you want to continue?"),
        (1617, "Cancel"),
        (1636, "Are you sure you want to %s?"),
        (1231, "Don't show this message again"),
        (1463, "Unable to perform the operation."),
    ],
}


def line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_c_file(path: str, entries):
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return

    for name, args, spans, call_start in find_calls(text, set(CALL_SPECS) | set(ANY_LITERAL_SPECS)):
        if name in CALL_SPECS:
            spec = CALL_SPECS[name]
            for idx, cat in spec.items():
                if idx is None:
                    idx = len(args) - 1
                if idx < len(args):
                    t = first_literal(args[idx])
                    if t is not None and not is_noise(t):
                        entries.append({
                            "category": cat, "file": rel,
                            "line": line_of_offset(text, spans[idx][0]),
                            "english": t,
                        })
        else:
            cat = ANY_LITERAL_SPECS[name]
            for a in args:
                for t in all_literals(a):
                    if not is_noise(t):
                        entries.append({
                            "category": cat, "file": rel,
                            "line": line_of_offset(text, call_start),
                            "english": t,
                        })

    for m in TASKDIALOG_FIELDS_RE.finditer(text):
        t = literal_text(m.group(2))
        if is_noise(t):
            continue
        entries.append({
            "category": "c_taskdialog", "file": rel,
            "line": line_of_offset(text, m.start()),
            "english": t,
        })

    if rel in PHLIB_INTERNAL:
        for line, t in PHLIB_INTERNAL[rel]:
            entries.append({
                "category": "phlib_internal", "file": rel, "line": line, "english": t,
            })


def scan_statusbar(path: str, entries):
    """ToolStatus status bar templates are patched to route through
    PhTranslateString; every L"" template literal in the file is counted."""
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    for m in C_LITERAL_RE.finditer(text):
        t = literal_text(m.group(0))
        if is_noise(t):
            continue
        entries.append({
            "category": "c_statusbar", "file": rel,
            "line": line_of_offset(text, m.start()), "english": t,
        })


# ---------------------------------------------------------------------------
# TabNew labels
# ---------------------------------------------------------------------------

TABNEW_INSERT_RE = re.compile(
    r"PhTabNew_InsertItem\s*\([^;]*?\)", re.S)
TCITEM_TEXT_RE = re.compile(r"pszText\s*=\s*(?:\(PWSTR\)\s*)?(L\"(?:[^\"\\]|\\.)*\")")


TRANSLATED_CALL_RE = re.compile(r'PhTranslateString\s*\(\s*(L"(?:[^"\\]|\\.)*")\s*\)')

PAGE_NAME_RE = re.compile(r'(\w*PageText\w*)\s*=\s*PH_STRINGREF_INIT\(\s*(L"(?:[^"\\]|\\.)*")\s*\)')


def scan_page_names(path: str, entries):
    """Main tab page labels (PH_STRINGREF constants handed to
    PhMwpCreatePage), translated at runtime by the TabNew hook."""
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    for m in PAGE_NAME_RE.finditer(text):
        t = literal_text(m.group(2))
        if is_noise(t):
            continue
        entries.append({
            "category": "c_tab", "file": rel,
            "line": line_of_offset(text, m.start()), "english": t,
        })


def scan_translated_calls(path: str, entries):
    """Strings routed through PhTranslateString at hand-patched call sites
    (e.g. ToolStatus toolbar button text)."""
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    for m in TRANSLATED_CALL_RE.finditer(text):
        t = literal_text(m.group(1))
        if is_noise(t):
            continue
        entries.append({
            "category": "c_toolbar", "file": rel,
            "line": line_of_offset(text, m.start()), "english": t,
        })


def scan_tabnew(path: str, entries):
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    for m in TABNEW_INSERT_RE.finditer(text):
        call = m.group(0)
        for lm in TCITEM_TEXT_RE.finditer(call):
            t = literal_text(lm.group(1))
            if not is_noise(t):
                entries.append({
                    "category": "c_tab", "file": rel,
                    "line": line_of_offset(text, m.start()), "english": t,
                })


# ---------------------------------------------------------------------------
# .rc resource scanning
# ---------------------------------------------------------------------------

RC_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
RC_CAPTION_RE = re.compile(r'\bCAPTION\s+"((?:[^"\\]|\\.)*)"')
RC_CONTROL_LINE_RE = re.compile(
    r"^\s*(LTEXT|RTEXT|CTEXT|PUSHBUTTON|DEFPUSHBUTTON|GROUPBOX|CONTROL|"
    r"AUTOCHECKBOX|AUTORADIOBUTTON|AUTO3STATE|CHECKBOX|RADIOBUTTON|"
    r"EDITTEXT|COMBOBOX|LISTBOX|SCROLLBAR|ICON|PROGRESS_MS|CONTROL_MS)\b",
    re.M)
RC_QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
RC_MENUITEM_RE = re.compile(r'\b(MENUITEM|POPUP)\s+"((?:[^"\\]|\\.)*)"')
RC_MENU_BLOCK_RE = re.compile(r"\b(MENU|MENUEX)\b")

RC_CONTROL_CLASSES_WITH_TEXT = {
    "LTEXT", "RTEXT", "CTEXT", "PUSHBUTTON", "DEFPUSHBUTTON", "GROUPBOX",
    "AUTOCHECKBOX", "AUTORADIOBUTTON", "AUTO3STATE", "CHECKBOX", "RADIOBUTTON",
    "CONTROL",
}


def rc_unescape(body: str) -> str:
    # .rc strings: "" -> ", \x -> literal handling is rare in this tree
    return body.replace('""', '"')


def scan_rc_file(path: str, entries):
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    base = os.path.basename(path).lower()
    if base in ("version.rc",):
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    text = RC_COMMENT_RE.sub(lambda m: " " * len(m.group(0)), raw)
    has_menu = RC_MENU_BLOCK_RE.search(text)

    for m in RC_CAPTION_RE.finditer(text):
        t = rc_unescape(m.group(1))
        if not is_noise(t):
            entries.append({
                "category": "rc_dialog", "file": rel,
                "line": line_of_offset(raw, m.start()), "english": t,
            })

    for m in RC_CONTROL_LINE_RE.finditer(text):
        kw = m.group(1)
        if kw not in RC_CONTROL_CLASSES_WITH_TEXT:
            continue
        # first quoted string on the statement is the display text
        rest = text[m.end():m.end() + 600]
        # stop at end of statement (semicolon or newline followed by another keyword)
        stop = re.search(r";|\n\s*\n", rest)
        if stop:
            rest = rest[:stop.start()]
        qm = RC_QUOTED_RE.search(rest)
        if not qm:
            continue
        t = rc_unescape(qm.group(1))
        if not is_noise(t):
            entries.append({
                "category": "rc_dialog", "file": rel,
                "line": line_of_offset(raw, m.start() + m.end() - len(m.group(0))),
                "english": t,
            })

    if has_menu:
        for m in RC_MENUITEM_RE.finditer(text):
            t = rc_unescape(m.group(2))
            if t in ("-", "_", "") or is_noise(t):
                continue
            entries.append({
                "category": "rc_menu", "file": rel,
                "line": line_of_offset(raw, m.start()), "english": t,
            })


# ---------------------------------------------------------------------------
# Walk
# ---------------------------------------------------------------------------

SCAN_DIRS = ["SystemInformer", "plugins", "phlib"]
EXCLUDE_PATHS = {
    "SystemInformer/phsvc",       # headless service component, no UI
    "phlib/tests",
}
EXCLUDE_FILES = {
    "SystemInformer/delayhook.c",
    "SystemInformer/delayload.c",
}


def iter_source_files():
    for top in SCAN_DIRS:
        for root, dirs, files in os.walk(os.path.join(REPO_ROOT, top)):
            rel_root = os.path.relpath(root, REPO_ROOT).replace("\\", "/")
            if any(rel_root == ex or rel_root.startswith(ex + "/") for ex in EXCLUDE_PATHS):
                continue
            for fn in files:
                rel = (rel_root + "/" + fn) if rel_root != "." else fn
                if rel in EXCLUDE_FILES:
                    continue
                if fn.endswith((".c", ".cpp")):
                    yield os.path.join(root, fn)
                elif fn.endswith(".rc"):
                    yield os.path.join(root, fn)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", default=os.path.join(os.path.dirname(__file__), "manifest.json"))
    args = ap.parse_args()

    entries = []
    for path in iter_source_files():
        rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
        if path.endswith(".rc"):
            scan_rc_file(path, entries)
            continue
        if rel == "plugins/ToolStatus/statusbar.c":
            scan_statusbar(path, entries)
        if rel == "plugins/ToolStatus/toolbar.c":
            scan_translated_calls(path, entries)
        if rel == "plugins/ToolStatus/statusbar.c":
            scan_c_file(path, entries)
            scan_tabnew(path, entries)
            continue
        scan_c_file(path, entries)
        scan_tabnew(path, entries)
        scan_page_names(path, entries)

    # Deduplicate identical (category, english) pairs while keeping locations.
    merged = defaultdict(lambda: {"category": None, "english": None, "locations": []})
    for e in entries:
        key = (e["category"], e["english"])
        rec = merged[key]
        rec["category"] = e["category"]
        rec["english"] = e["english"]
        rec["locations"].append({"file": e["file"], "line": e["line"]})

    manifest = {
        "unique_strings": [
            {"category": v["category"], "english": v["english"],
             "locations": sorted(v["locations"], key=lambda x: (x["file"], x["line"]))}
            for v in sorted(merged.values(), key=lambda v: (v["category"], v["english"].lower()))
        ],
        "total_occurrences": len(entries),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    by_cat = defaultdict(int)
    for v in manifest["unique_strings"]:
        by_cat[v["category"]] += 1
    print(f"manifest: {len(manifest['unique_strings'])} unique strings "
          f"({manifest['total_occurrences']} occurrences) -> {args.output}")
    for cat in sorted(by_cat):
        print(f"  {cat:16s} {by_cat[cat]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
