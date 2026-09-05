#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit.py - Extract all user-visible strings from the System Informer source
tree into a machine-readable manifest, classified by where the string comes
from and which runtime translation funnel covers it.

The manifest is the single source of truth for translation coverage. It is
regenerated on every check; it is derived data and must not be committed.

Categories describe the actual UI sink. Categories without a runtime
translation hook are marked by check_translation.py as requiring call-site
migration even when the legacy dictionary contains the same English key.
  rc_dialog        dialog template controls and captions (.rc DIALOG/DIALOGEX)
  rc_menu          menu resources (.rc MENU/MENUEX)
  rc_stringtable   dynamic UI text stored in .rc STRINGTABLE blocks
  c_emenu          PhCreateEMenuItem / PhCreateEMenuItemCallback text
  c_listview_col   PhAddListViewColumn* text
  c_listview_group PhAddListViewGroup text
  c_listview_group_item PhAddListViewGroupItem* text (no translation hook)
  c_window_text    PhSetDialogItemText / PhSetWindowText / SetWindowText text
  c_combobox       ComboBox_AddString text
  c_treenew_col    PhAddTreeNewColumn* text
  c_msgbox         PhShowMessage* family format/title arguments
  c_msgbox_vararg  visible printf arguments not covered by the runtime funnel
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

# ---------------------------------------------------------------------------
# C wide string literal handling
# ---------------------------------------------------------------------------

C_LITERAL_RE = re.compile(r'L"(?:[^"\\]|\\.)*"')
PRINTF_SPEC_RE = re.compile(
    r"%(?:%|[-+ #0]*(?:\*|\d+)?(?:\.(?:\*|\d+))?"
    r"(?:I64|I32|ll|hh|[hlLwIjzt])?[diuoxXfFeEgGaAcCsSpn])"
)

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
    if re.match(r"^(\\\\|https?://|www\.|\*)", stripped):
        return True
    if re.fullmatch(
        r"%[-+ #0]*(?:\*|\d+)?(?:\.(?:\*|\d+))?"
        r"(?:I64|I32|ll|hh|[hlLwIjzt])?[diuoxXfFeEgGaAcCsSpn]"
        r"[\s|,.;:/-]*",
        stripped,
    ):
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


def adjacent_literal_text(arg: str):
    """Return the compile-time value of an argument made only of adjacent
    wide-string literals, or None when the argument contains other syntax."""
    matches = list(C_LITERAL_RE.finditer(arg))
    if not matches or C_LITERAL_RE.sub("", arg).strip():
        return None
    return "".join(literal_text(match.group(0)) for match in matches)


def printf_string_argument_indexes(format_text: str):
    """Return zero-based vararg indexes consumed by string conversions."""
    argument_index = 0
    indexes = []

    for match in PRINTF_SPEC_RE.finditer(format_text):
        specifier = match.group(0)
        if specifier == "%%":
            continue
        argument_index += specifier[:-1].count("*")
        if specifier[-1] in {"s", "S"}:
            indexes.append(argument_index)
        argument_index += 1

    return indexes


def mask_c_comments(source: str) -> str:
    """Replace C comments with spaces while preserving strings and offsets."""
    result = list(source)
    index = 0
    state = "normal"

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == "/" and next_char == "/":
                result[index] = result[index + 1] = " "
                index += 1
                state = "line_comment"
            elif char == "/" and next_char == "*":
                result[index] = result[index + 1] = " "
                index += 1
                state = "block_comment"
        elif state in {"string", "char"}:
            if char == "\\":
                index += 1
            elif (state == "string" and char == '"') or (
                state == "char" and char == "'"
            ):
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
            else:
                result[index] = " "
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                result[index] = result[index + 1] = " "
                index += 1
                state = "normal"
            elif char != "\n":
                result[index] = " "

        index += 1

    return "".join(result)


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
    "PhAddListViewGroup": {2: "c_listview_group"},
    "PhAddListViewGroupItem": {3: "c_listview_group_item"},
    "PhAddIListViewGroupItem": {3: "c_listview_group_item"},
    "PhListView_AddGroup": {2: "c_listview_group"},
    "PhListView_AddGroupItem": {3: "c_listview_group_item"},
    "PhAddTreeNewColumn": {3: "c_treenew_col"},
    "PhAddTreeNewColumnEx": {3: "c_treenew_col"},
    "PhAddTreeNewColumnEx2": {3: "c_treenew_col"},
    "PhShowMessage": {2: "c_msgbox"},
    "PhShowMessage2": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowError": {1: "c_msgbox"},
    "PhShowWarning": {1: "c_msgbox"},
    "PhShowInformation": {1: "c_msgbox"},
    "PhShowError2": {1: "c_msgbox", 2: "c_msgbox"},
    "PhShowWarning2": {1: "c_msgbox", 2: "c_msgbox"},
    "PhShowInformation2": {1: "c_msgbox", 2: "c_msgbox"},
    "PhShowStatus": {1: "c_msgbox"},
    "PhShowContinueStatus": {1: "c_msgbox"},
    "PhShowMessageOneTime": {3: "c_msgbox", 4: "c_msgbox"},
    "PhShowMessageOneTime2": {3: "c_msgbox", 5: "c_msgbox"},
    "PhShowConfirmMessage": {1: "c_confirm", 2: "c_confirm", 3: "c_confirm"},
    "PhAddListViewItem": {2: "c_listview_item"},
    "PhAddIListViewItem": {2: "c_listview_item"},
    "PhSetDialogItemText": {2: "c_window_text"},
    "PhSetWindowText": {1: "c_window_text"},
    "SetWindowText": {1: "c_window_text"},
    "SetWindowTextW": {1: "c_window_text"},
    "ComboBox_AddString": {1: "c_combobox"},
    "PhNfShowBalloonTip": {0: "c_balloon", 1: "c_balloon"},
    "PhNfShowBalloonTipEx": {0: "c_balloon", 1: "c_balloon"},
}

# Message functions can receive user-visible string literals through printf
# varargs after the format argument (for example L"%s", L"Visible text").
FORMAT_ARG_INDEXES = {
    "PhShowMessage": 2,
    "PhShowMessage2": 4,
    "PhShowError": 1,
    "PhShowWarning": 1,
    "PhShowInformation": 1,
    "PhShowError2": 2,
    "PhShowWarning2": 2,
    "PhShowInformation2": 2,
    "PhShowMessageOneTime": 4,
    "PhShowMessageOneTime2": 5,
}

FULL_CONTENT_TRANSLATION_CALLS = {
    "PhShowMessage2",
    "PhShowError2",
    "PhShowWarning2",
    "PhShowInformation2",
    "PhShowMessageOneTime",
    "PhShowMessageOneTime2",
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


def literal_sequences_outside_ui_string_getters(expression: str):
    """Return maximal adjacent literal sequences and offsets outside UI getters."""
    getter_names = {
        match.group(0)
        for match in IDENT_RE.finditer(expression)
        if match.group(0).endswith("GetUiString")
        or match.group(0) == "PhLoadUiString"
    }
    masked = list(expression)

    for _, _, spans, call_start in find_calls(expression, getter_names):
        call_end = spans[-1][1] + 1
        for index in range(call_start, call_end):
            if masked[index] != "\n":
                masked[index] = " "

    masked_expression = "".join(masked)
    matches = list(C_LITERAL_RE.finditer(masked_expression))
    sequences = []

    for match in matches:
        text = literal_text(match.group(0))

        if sequences and not masked_expression[sequences[-1][2]:match.start()].strip():
            previous_text, previous_offset, _ = sequences[-1]
            sequences[-1] = (
                previous_text + text,
                previous_offset,
                match.end(),
            )
        else:
            sequences.append((text, match.start(), match.end()))

    return [(text, offset) for text, offset, _ in sequences]


def literals_outside_ui_string_getters(expression: str):
    """Return literal texts that are not fallbacks inside native UI getters."""
    return [
        text
        for text, _ in literal_sequences_outside_ui_string_getters(expression)
    ]


def c_brace_scopes(text: str):
    """Return matched C brace ranges while ignoring braces in literals."""
    stack = []
    scopes = []
    state = "normal"
    index = 0

    while index < len(text):
        char = text[index]
        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == "{":
                stack.append(index)
            elif char == "}" and stack:
                scopes.append((stack.pop(), index))
        elif state in {"string", "char"}:
            if char == "\\":
                index += 1
            elif (state == "string" and char == '"') or (
                state == "char" and char == "'"
            ):
                state = "normal"
        index += 1

    return scopes


def innermost_c_scope(scopes, offset: int):
    containing = [
        scope for scope in scopes if scope[0] < offset < scope[1]
    ]
    return max(containing, key=lambda scope: scope[0], default=None)


def visible_array_declaration(declarations, offset: int, scopes):
    """Resolve the nearest declaration whose lexical scope contains offset."""
    visible = []
    for declaration in declarations:
        if declaration.start() >= offset:
            continue
        scope = innermost_c_scope(scopes, declaration.start())
        if scope is None or scope[0] < offset < scope[1]:
            visible.append((scope, declaration))

    if not visible:
        return None

    return max(
        visible,
        key=lambda item: (
            item[0][0] if item[0] is not None else -1,
            item[1].start(),
        ),
    )[1]


def scan_combo_box_string_arrays(text: str, scan_text: str, rel: str, entries):
    """Resolve string arrays passed to the no-hook PhAddComboBoxStrings."""
    scopes = c_brace_scopes(scan_text)

    for _, args, spans, call_start in find_calls(
        scan_text, {"PhAddComboBoxStrings"}
    ):
        if len(args) < 2:
            continue

        array_argument = args[1]
        for visible_text in literals_outside_ui_string_getters(array_argument):
            if not is_noise(visible_text):
                entries.append({
                    "category": "c_combobox",
                    "file": rel,
                    "line": line_of_offset(text, spans[1][0]),
                    "english": visible_text,
                })

        identifier_match = re.fullmatch(
            r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*", array_argument
        )
        if not identifier_match:
            continue

        identifier = identifier_match.group(1)
        declaration_re = re.compile(
            rf"\b{re.escape(identifier)}\s*\[[^\]]*\]\s*"
            rf"(?:=\s*\{{(?P<body>.*?)\}})?\s*;",
            re.DOTALL,
        )
        declarations = list(declaration_re.finditer(scan_text))
        declaration = visible_array_declaration(
            declarations, call_start, scopes
        )
        if declaration is None:
            continue

        sources = []
        if declaration.group("body") is not None:
            sources.append((declaration.group("body"), declaration.start("body")))

        declaration_scope = innermost_c_scope(scopes, declaration.start())
        if declaration_scope is not None:
            assignment_region = scan_text[declaration.end():call_start]
            assignment_re = re.compile(
                rf"\b{re.escape(identifier)}\s*\[[^\]]+\]\s*=\s*"
                rf"(?P<value>.*?);",
                re.DOTALL,
            )
            for assignment in assignment_re.finditer(assignment_region):
                assignment_offset = declaration.end() + assignment.start()
                if visible_array_declaration(
                    declarations, assignment_offset, scopes
                ) is not declaration:
                    continue
                # Keep every visible assignment conservatively. If one index
                # is overwritten, reporting both values is preferable to
                # silently dropping a possible user-visible string.
                sources.append((
                    assignment.group("value"),
                    declaration.end() + assignment.start("value"),
                ))

        for source, source_offset in sources:
            for visible_text in literals_outside_ui_string_getters(source):
                if not is_noise(visible_text):
                    entries.append({
                        "category": "c_combobox",
                        "file": rel,
                        "line": line_of_offset(text, source_offset),
                        "english": visible_text,
                    })


def split_c_initializer_fields(initializer: str):
    """Split one flat C initializer using the balanced call parser."""
    wrapped = f"AuditInitializer({initializer})"
    call = next(find_calls(wrapped, {"AuditInitializer"}), None)
    return call[1] if call else []


def resolve_struct_array_member(
    scan_text: str,
    expression: str,
    call_start: int,
    scopes,
):
    member_match = re.fullmatch(
        r"\s*(?:\(\s*[^()]+\s*\)\s*)*"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*\[[^\]]+\]\s*\.\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*",
        expression,
    )
    if not member_match:
        return None

    array_name, member_name = member_match.groups()
    declaration_re = re.compile(
        rf"\b(?:(?:static|extern|CONST|const|volatile)\s+)*"
        rf"(?P<type>[A-Za-z_][A-Za-z0-9_]*)\s+"
        rf"{re.escape(array_name)}\s*\[[^\]]*\]\s*=\s*"
        rf"\{{(?P<body>.*?)\}}\s*;",
        re.DOTALL,
    )
    declarations = list(declaration_re.finditer(scan_text))
    declaration = visible_array_declaration(declarations, call_start, scopes)
    if declaration is None:
        return None

    type_name = declaration.group("type")
    type_re = re.compile(
        rf"\btypedef\s+struct(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*"
        rf"\{{(?P<body>[^{{}}]*)\}}\s*{re.escape(type_name)}\b[^;]*;",
        re.DOTALL,
    )
    field_names = []
    type_match = type_re.search(scan_text)

    if type_match is not None:
        for field in type_match.group("body").split(";"):
            field_match = re.search(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$",
                field.strip(),
            )
            if field_match:
                field_names.append(field_match.group(1))

    return {
        "body": declaration.group("body"),
        "body_offset": declaration.start("body"),
        "member_name": member_name,
        "member_index": (
            field_names.index(member_name) if member_name in field_names else None
        ),
    }


def struct_array_member_literals(resolved_member):
    member_index = resolved_member["member_index"]
    if member_index is None:
        return

    array_body = resolved_member["body"]
    array_body_offset = resolved_member["body_offset"]

    for initializer_match in re.finditer(r"\{(?P<body>[^{}]*)\}", array_body):
        fields = split_c_initializer_fields(initializer_match.group("body"))
        if member_index >= len(fields):
            continue

        for visible_text in literals_outside_ui_string_getters(fields[member_index]):
            if not is_noise(visible_text):
                yield (
                    visible_text,
                    array_body_offset + initializer_match.start("body"),
                )


def scan_struct_array_member_calls(
    text: str,
    scan_text: str,
    rel: str,
    entries,
    call_specs,
):
    scopes = c_brace_scopes(scan_text)

    for name, args, _, call_start in find_calls(scan_text, call_specs):
        argument_index, category = call_specs[name]
        if argument_index >= len(args):
            continue

        resolved_member = resolve_struct_array_member(
            scan_text, args[argument_index], call_start, scopes
        )
        if resolved_member is None:
            continue

        for visible_text, source_offset in struct_array_member_literals(
            resolved_member
        ):
            entries.append({
                "category": category,
                "file": rel,
                "line": line_of_offset(text, source_offset),
                "english": visible_text,
            })


def scan_combo_box_struct_arrays(text: str, scan_text: str, rel: str, entries):
    """Resolve string fields from struct arrays passed to ComboBox_AddString."""
    scopes = c_brace_scopes(scan_text)

    for _, args, _, call_start in find_calls(scan_text, {"ComboBox_AddString"}):
        if len(args) < 2:
            continue

        resolved_member = resolve_struct_array_member(
            scan_text, args[1], call_start, scopes
        )
        if resolved_member is None:
            continue

        array_body = resolved_member["body"]
        array_body_offset = resolved_member["body_offset"]
        member_name = resolved_member["member_name"]

        for visible_text, source_offset in struct_array_member_literals(
            resolved_member
        ):
            entries.append({
                "category": "c_combobox",
                "file": rel,
                "line": line_of_offset(text, source_offset),
                "english": visible_text,
            })

        sip_field_indexes = {"Key": 0, "Value": 1}
        sip_member_index = sip_field_indexes.get(member_name)

        if sip_member_index is not None:
            for _, sip_args, sip_spans, _ in find_calls(array_body, {"SIP"}):
                if sip_member_index >= len(sip_args):
                    continue

                for visible_text in literals_outside_ui_string_getters(
                    sip_args[sip_member_index]
                ):
                    if not is_noise(visible_text):
                        entries.append({
                            "category": "c_combobox",
                            "file": rel,
                            "line": line_of_offset(
                                text,
                                array_body_offset + sip_spans[sip_member_index][0],
                            ),
                            "english": visible_text,
                        })


def scan_c_file(path: str, entries):
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return

    scan_text = mask_c_comments(text)

    scan_combo_box_string_arrays(text, scan_text, rel, entries)
    scan_combo_box_struct_arrays(text, scan_text, rel, entries)
    scan_struct_array_member_calls(
        text,
        scan_text,
        rel,
        entries,
        {
            "PhAddListViewGroupItem": (3, "c_listview_group_item"),
            "PhAddIListViewGroupItem": (3, "c_listview_group_item"),
            "PhListView_AddGroupItem": (3, "c_listview_group_item"),
        },
    )

    for name, args, spans, call_start in find_calls(scan_text, set(CALL_SPECS) | set(ANY_LITERAL_SPECS)):
        if name in CALL_SPECS:
            spec = CALL_SPECS[name]
            for idx, cat in spec.items():
                if idx is None:
                    idx = len(args) - 1
                if idx < len(args):
                    for t, relative_offset in literal_sequences_outside_ui_string_getters(
                        args[idx]
                    ):
                        if not is_noise(t):
                            entries.append({
                                "category": cat, "file": rel,
                                "line": line_of_offset(
                                    text,
                                    spans[idx][0] + relative_offset,
                                ),
                                "english": t,
                            })
            if name in FORMAT_ARG_INDEXES:
                format_index = FORMAT_ARG_INDEXES[name]
                if format_index >= len(args):
                    continue
                format_texts = [
                    text
                    for text, _ in literal_sequences_outside_ui_string_getters(
                        args[format_index]
                    )
                ]
                varargs = args[format_index + 1:]
                string_argument_indexes = sorted({
                    argument_index
                    for format_text in format_texts
                    for argument_index in printf_string_argument_indexes(format_text)
                })
                direct_content = (
                    name in FULL_CONTENT_TRANSLATION_CALLS
                    and adjacent_literal_text(args[format_index]) == "%s"
                    and len(varargs) == 1
                )
                for vararg_index in string_argument_indexes:
                    idx = format_index + 1 + vararg_index
                    if idx >= len(args):
                        continue
                    category = (
                        "c_msgbox"
                        if direct_content or "PhTranslateString" in args[idx]
                        else "c_msgbox_vararg"
                    )
                    for t, relative_offset in literal_sequences_outside_ui_string_getters(
                        args[idx]
                    ):
                        if not is_noise(t):
                            entries.append({
                                "category": category, "file": rel,
                                "line": line_of_offset(
                                    text,
                                    spans[idx][0] + relative_offset,
                                ),
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

    for m in TASKDIALOG_FIELDS_RE.finditer(scan_text):
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
    """Count only status bar fallbacks routed through native resources."""
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = mask_c_comments(f.read())
    for name, args, spans, call_start in find_calls(
        text, {"ToolStatusGetUiString"}
    ):
        if len(args) < 2:
            continue
        for t in all_literals(args[1]):
            if is_noise(t):
                continue
            entries.append({
                "category": "c_statusbar", "file": rel,
                "line": line_of_offset(text, spans[1][0]), "english": t,
            })


# ---------------------------------------------------------------------------
# TabNew labels
# ---------------------------------------------------------------------------

TABNEW_INSERT_RE = re.compile(
    r"PhTabNew_InsertItem\s*\([^;]*?\)", re.S)
TCITEM_TEXT_RE = re.compile(r"pszText\s*=\s*(?:\(PWSTR\)\s*)?(L\"(?:[^\"\\]|\\.)*\")")


TRANSLATED_CALL_RE = re.compile(r'PhTranslateString\s*\(\s*(L"(?:[^"\\]|\\.)*")\s*\)')

PAGE_NAME_RE = re.compile(r'(\w*PageText\w*)\s*=\s*PH_STRINGREF_INIT\(\s*(L"(?:[^"\\]|\\.)*")\s*\)')

EMPTY_TEXT_RE = re.compile(r'(\w*EmptyText\w*)\s*=\s*PH_STRINGREF_INIT\(\s*(L"(?:[^"\\]|\\.)*")\s*\)')

OPTIONS_SECTION_RE = re.compile(r'PhOptionsCreateSection\w*\(\s*(L"(?:[^"\\]|\\.)*")')


def scan_extra_statics(path: str, entries):
    """TreeNew empty-list hints and options section tree labels."""
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = mask_c_comments(f.read())
    for m in EMPTY_TEXT_RE.finditer(text):
        t = literal_text(m.group(2))
        if not is_noise(t):
            entries.append({"category": "c_treenew_empty", "file": rel,
                            "line": line_of_offset(text, m.start()), "english": t})
    for m in OPTIONS_SECTION_RE.finditer(text):
        t = literal_text(m.group(1))
        if not is_noise(t):
            entries.append({"category": "c_tree_item", "file": rel,
                            "line": line_of_offset(text, m.start()), "english": t})


def scan_page_names(path: str, entries):
    """Main tab page labels (PH_STRINGREF constants handed to
    PhMwpCreatePage), translated at runtime by the TabNew hook."""
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = mask_c_comments(f.read())
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
        text = mask_c_comments(f.read())
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
        text = mask_c_comments(f.read())
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

RC_STRING_BODY = r'(?:(?:"")|[^"\\]|\\.)*'
RC_CAPTION_RE = re.compile(rf'\bCAPTION\s+"({RC_STRING_BODY})"')
RC_CONTROL_LINE_RE = re.compile(
    r"^\s*(LTEXT|RTEXT|CTEXT|PUSHBUTTON|DEFPUSHBUTTON|GROUPBOX|CONTROL|"
    r"AUTOCHECKBOX|AUTORADIOBUTTON|AUTO3STATE|CHECKBOX|RADIOBUTTON|"
    r"EDITTEXT|COMBOBOX|LISTBOX|SCROLLBAR|ICON|PROGRESS_MS|CONTROL_MS)\b",
    re.M)
RC_QUOTED_RE = re.compile(rf'"({RC_STRING_BODY})"')
RC_MENUITEM_RE = re.compile(rf'\b(MENUITEM|POPUP)\s+"({RC_STRING_BODY})"')
RC_MENU_BLOCK_RE = re.compile(r"\b(MENU|MENUEX)\b")
RC_STRINGTABLE_BLOCK_RE = re.compile(
    r"(?ms)^\s*STRINGTABLE\b[^\r\n]*\r?\n\s*BEGIN\s*\r?\n"
    r"(.*?)^\s*END\s*$"
)
RC_STRINGTABLE_ENTRY_RE = re.compile(
    rf'(?m)^\s*(?:[A-Z][A-Z0-9_]*|\d+)\s+"({RC_STRING_BODY})"'
)

RC_CONTROL_CLASSES_WITH_TEXT = {
    "LTEXT", "RTEXT", "CTEXT", "PUSHBUTTON", "DEFPUSHBUTTON", "GROUPBOX",
    "AUTOCHECKBOX", "AUTORADIOBUTTON", "AUTO3STATE", "CHECKBOX", "RADIOBUTTON",
    "CONTROL",
}


def rc_unescape(body: str) -> str:
    # .rc strings: "" -> ", \x -> literal handling is rare in this tree
    return body.replace('""', '"')


def mask_rc_comments(source: str) -> str:
    """Mask comments without treating URLs inside RC strings as comments."""
    result = list(source)
    index = 0
    in_string = False

    while index < len(source):
        if in_string:
            if source[index] == '"':
                if index + 1 < len(source) and source[index + 1] == '"':
                    index += 2
                    continue
                in_string = False
            elif source[index] == "\\" and index + 1 < len(source):
                index += 2
                continue
            index += 1
            continue

        if source[index] == '"':
            in_string = True
            index += 1
            continue

        if source.startswith("//", index):
            end = source.find("\n", index)
            if end == -1:
                end = len(source)
            for position in range(index, end):
                result[position] = " "
            index = end
            continue

        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            end = len(source) if end == -1 else end + 2
            for position in range(index, end):
                if result[position] not in "\r\n":
                    result[position] = " "
            index = end
            continue

        index += 1

    return "".join(result)


def scan_rc_file(path: str, entries):
    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    base = os.path.basename(path).lower()
    if base == "version.rc" or base.endswith(".zh-cn.rc"):
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    text = mask_rc_comments(raw)
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

    for block_match in RC_STRINGTABLE_BLOCK_RE.finditer(text):
        block = block_match.group(1)

        for entry_match in RC_STRINGTABLE_ENTRY_RE.finditer(block):
            t = c_unescape(rc_unescape(entry_match.group(1)))

            if is_noise(t):
                continue

            entries.append({
                "category": "rc_stringtable",
                "file": rel,
                "line": line_of_offset(raw, block_match.start(1) + entry_match.start()),
                "english": t,
            })


# ---------------------------------------------------------------------------
# Walk
# ---------------------------------------------------------------------------

SCAN_DIRS = [
    "SystemInformer",
    "plugins",
    "phlib",
    "tools/peview",
    "tools/CustomSetupTool",
    "tools/CustomSignTool",
]
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


def build_manifest(entries):
    """Build a schema-v2 manifest from raw audit occurrences."""
    merged = defaultdict(
        lambda: {"category": None, "english": None, "module": None, "locations": []}
    )

    for entry in entries:
        category = entry["category"]
        english = entry["english"]
        if category not in ALL_CATEGORIES:
            raise ValueError(f"unknown manifest category: {category!r}")
        module = (
            module_for_path(entry["file"])
            if category in CALLSITE_MIGRATION_CATEGORIES
            else None
        )
        key = canonical_manifest_key(category, english, module)
        record = merged[key]
        record["category"] = category
        record["english"] = english
        record["module"] = module
        record["locations"].append(
            {"file": entry["file"], "line": entry["line"]}
        )

    unique_strings = []
    for record in sorted(
        merged.values(),
        key=lambda value: (
            value["category"],
            value["english"].lower(),
            value["english"],
            value["module"] or "",
        ),
    ):
        manifest_entry = {
            "category": record["category"],
            "english": record["english"],
            "locations": sorted(
                record["locations"],
                key=lambda location: (location["file"], location["line"]),
            ),
        }
        if record["module"] is not None:
            manifest_entry["module"] = record["module"]
        unique_strings.append(manifest_entry)

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "unique_strings": unique_strings,
        "total_occurrences": len(entries),
    }


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
        if rel in ("plugins/ToolStatus/toolbar.c", "plugins/ExtendedTools/fwtab.c",
                   "plugins/ExtendedTools/disktab.c"):
            scan_translated_calls(path, entries)
        if rel == "plugins/ToolStatus/statusbar.c":
            scan_c_file(path, entries)
            scan_tabnew(path, entries)
            continue
        scan_c_file(path, entries)
        scan_tabnew(path, entries)
        scan_page_names(path, entries)
        scan_extra_statics(path, entries)

    manifest = build_manifest(entries)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    by_cat = defaultdict(int)
    for v in manifest["unique_strings"]:
        by_cat[v["category"]] += 1
    print(f"manifest: {len(manifest['unique_strings'])} schema entries "
          f"({manifest['total_occurrences']} occurrences) -> {args.output}")
    for cat in sorted(by_cat):
        print(f"  {cat:16s} {by_cat[cat]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
