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
  c_listview_item  PhAddListViewItem* text (runtime translation hook)
  c_listview_item_raw PhAddListViewItemRaw text (no translation hook)
  c_window_text    PhSetDialogItemText / PhSetWindowText / SetWindowText text
  c_combobox       ComboBox_AddString text
  c_treenew_col    PhAddTreeNewColumn* text
  c_msgbox         PhShowMessage* family format/title arguments
  c_msgbox_vararg  visible printf arguments not covered by the runtime funnel
  c_confirm        PhShowConfirmMessage verb/object/message arguments
  c_runtime_composed source templates/fragments composed before runtime hooks
  c_taskdialog     TASKDIALOGCONFIG literal fields (title/content/buttons/...)
  c_taskdialog_raw TaskDialog button text passed through a raw navigation sink
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
            if nxt in {"u", "U"}:
                digit_count = 4 if nxt == "u" else 8
                hexs = body[i + 2:i + 2 + digit_count]
                if len(hexs) == digit_count and all(
                    character in "0123456789abcdefABCDEF"
                    for character in hexs
                ):
                    try:
                        out.append(chr(int(hexs, 16)))
                        i += 2 + digit_count
                        continue
                    except ValueError:
                        pass
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


def is_c_integer_zero(expression: str) -> bool:
    """Return true for the simple integer-zero forms used by C count fields."""
    normalized = re.sub(r"\s+", "", expression)
    return re.fullmatch(
        r"(?:\([A-Za-z_][A-Za-z0-9_]*\))*"
        r"\(*(?:NULL|FALSE|0[xX]0+|0[bB]0+|0+)[uUlL]*\)*",
        normalized,
    ) is not None


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


def is_resource_ui_getter(expression: str, fallback: str, resource_id=None):
    """Return whether an expression is exactly a native UI getter call."""
    getter_names = {
        match.group(0)
        for match in IDENT_RE.finditer(expression)
        if match.group(0).endswith("GetUiString")
    }
    calls = list(find_calls(expression, getter_names))

    if len(calls) != 1:
        return False

    _name, args, spans, call_start = calls[0]
    if len(args) < 2:
        return False
    if expression[:call_start].strip() or expression[spans[-1][1] + 1:].strip():
        return False
    if resource_id is not None and args[0].strip() != resource_id:
        return False

    return adjacent_literal_text(args[1]) == fallback


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


def mask_c_literals(source: str) -> str:
    """Mask string and character literals while preserving source offsets."""
    result = list(source)
    state = "normal"
    index = 0

    while index < len(source):
        char = source[index]
        if state == "normal":
            if char == '"':
                state = "string"
                result[index] = " "
            elif char == "'":
                state = "char"
                result[index] = " "
        else:
            if char not in "\r\n":
                result[index] = " "
            if char == "\\" and index + 1 < len(source):
                index += 1
                if source[index] not in "\r\n":
                    result[index] = " "
            elif (state == "string" and char == '"') or (
                state == "char" and char == "'"
            ):
                state = "normal"
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
    "PhAddHandleListViewItem": {3: "c_listview_group_item"},
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
    "PhShowConfirmMessageRawObject": {1: "c_confirm", 3: "c_confirm"},
    "PhShowConfirmMessageRawAction": {
        1: "c_confirm",
        2: "c_confirm",
        3: "c_confirm",
    },
    "PhpShowConfirmMessageObject": {1: "c_confirm", 3: "c_confirm"},
    "PhAddListViewItem": {2: "c_listview_item"},
    "PhAddIListViewItem": {2: "c_listview_item"},
    "PhAddListViewItemRaw": {2: "c_listview_item_raw"},
    "PhSetDialogItemText": {2: "c_window_text"},
    "PhSetWindowText": {1: "c_window_text"},
    "PhSetListViewSubItem": {3: "c_window_text"},
    "PhSetHandleListViewItem": {3: "c_window_text"},
    "SetWindowText": {1: "c_window_text"},
    "SetWindowTextW": {1: "c_window_text"},
    "ComboBox_AddString": {1: "c_combobox"},
    "PhNfShowBalloonTip": {0: "c_balloon", 1: "c_balloon"},
    "PhNfShowBalloonTipEx": {0: "c_balloon", 1: "c_balloon"},
    "PhNfShowBalloonTipRaw": {0: "c_balloon", 1: "c_balloon"},
    "PhShowIconNotification": {0: "c_balloon", 1: "c_balloon"},
    "PhShowIconNotificationEx": {0: "c_balloon", 1: "c_balloon"},
    "PhShowIconNotificationRaw": {0: "c_balloon", 1: "c_balloon"},
    "PhCreateSearchControl": {2: "c_search"},
    "PhCreateSearchControlEx": {2: "c_search"},
}

# These business wrappers accept an already-rendered label/value. Resolve only
# direct text and a single unambiguous local definition so unrelated literals
# in arbitrary producer calls cannot be mistaken for UI text.
STRICT_LITERAL_CALLS = {
    "PhAddHandleListViewItem",
    "PhSetHandleListViewItem",
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

RUNTIME_COMPOSER_CALLS = {
    "PhaFormatString",
    "PhFormatString",
    "PhConcatStringRefZ",
}

LOCAL_UI_TEXT_DECLARATION_RE = re.compile(
    r"\b(?:(?:static|const|CONST|volatile)\s+)*"
    r"(?P<type>PWSTR|PCWSTR|PPH_STRING|WCHAR|PH_STRINGREF)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P<array>\s*\[[^\]]*\])?\s*"
    r"(?:=\s*(?P<initializer>.*?))?;",
    re.DOTALL,
)

# Calls without a stable text argument are intentionally not guessed.
ANY_LITERAL_SPECS = {}

TASKDIALOG_TEXT_FIELDS = {
    "pszMainInstruction",
    "pszContent",
    "pszVerificationText",
    "pszFooter",
    "pszCollapsedControlText",
    "pszExpandedControlText",
    "pszExpandedInformation",
    "pszWindowTitle",
}

TASKDIALOG_CONFIG_DECLARATION_RE = re.compile(
    r"\b(?:(?:static|const|CONST|volatile)\s+)*"
    r"(?P<type>TASKDIALOGCONFIG(?:EX)?)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?:=\s*(?P<initializer>.*?))?;",
    re.DOTALL,
)

TASKDIALOG_BUTTON_DECLARATION_RE = re.compile(
    r"\b(?:(?:static|extern|const|CONST|volatile)\s+)*"
    r"TASKDIALOG_BUTTON\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\[[^\]]*\]\s*(?P<assignment>=)?",
    re.DOTALL,
)

# Fixed phlib funnel text is now application-resource backed. Keep this hook
# for any future internal literals that cannot be discovered from call sites.
PHLIB_INTERNAL = {}


def line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def literal_sequences_outside_ui_string_getters(
    expression: str,
    mask_explicit_translation: bool = False,
):
    """Return adjacent literals outside native getters and translation calls."""
    getter_names = {
        match.group(0)
        for match in IDENT_RE.finditer(expression)
        if match.group(0).endswith("GetUiString")
        or match.group(0)
        in {
            "PhLoadUiString",
            "PhGetApplicationUiStringOrDefault",
            "PhGetStringSetting",
            "PhaGetStringSetting",
        }
        or (
            mask_explicit_translation
            and match.group(0) == "PhTranslateString"
        )
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


def is_runtime_composer(name: str) -> bool:
    return (
        name in RUNTIME_COMPOSER_CALLS
        or name.startswith("PhaConcatStrings")
        or name.startswith("PhConcatStrings")
    )


def runtime_composer_names(expression: str):
    return {
        match.group(0)
        for match in IDENT_RE.finditer(expression)
        if is_runtime_composer(match.group(0))
    }


def expression_call_ranges(expression: str):
    call_names = {
        match.group(0) for match in IDENT_RE.finditer(expression)
    }
    return [
        (name, call_start, spans[-1][1])
        for name, _, spans, call_start in find_calls(expression, call_names)
        if spans
    ]


def expression_source_literals(expression: str, default_category: str):
    """Return visible literal sources and their categories for one expression."""
    calls = expression_call_ranges(expression)
    return [
        (
            "c_runtime_composed"
            if any(
                is_runtime_composer(name) and start < offset < end
                for name, start, end in calls
            )
            else default_category,
            text,
            offset,
        )
        for text, offset in literal_sequences_outside_ui_string_getters(expression)
        if not is_noise(text)
    ]


def one_hop_expression_source_literals(
    expression: str,
    default_category: str,
    allow_string_fallback: bool = False,
    mask_explicit_translation: bool = False,
):
    """Accept only literal expressions or explicitly supported composers."""
    calls = expression_call_ranges(expression)
    sources = []

    for text, offset in literal_sequences_outside_ui_string_getters(
        expression,
        mask_explicit_translation=mask_explicit_translation,
    ):
        if is_noise(text):
            continue
        enclosing_calls = [
            name for name, start, end in calls if start < offset < end
        ]
        if any(is_runtime_composer(name) for name in enclosing_calls):
            sources.append(("c_runtime_composed", text, offset))
        elif not enclosing_calls or all(
            name == "PH_STRINGREF_INIT"
            or (allow_string_fallback and name == "PhGetStringOrDefault")
            for name in enclosing_calls
        ):
            sources.append((default_category, text, offset))

    return sources


def runtime_target_identifier(expression: str):
    match = re.fullmatch(
        r"\s*([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s*(?:->|\.)\s*Buffer)?\s*",
        expression,
    )
    if match:
        return match.group(1)

    string_getter_match = re.fullmatch(
        r"\s*PhGetString\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*",
        expression,
    )
    return string_getter_match.group(1) if string_getter_match else None


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


def visible_local_text_declaration(declarations, identifier, offset, scopes):
    """Resolve a supported local binding without crossing lexical scopes."""
    visible = []

    for declaration in declarations:
        if declaration.group("name") != identifier or declaration.start() >= offset:
            continue
        scope = innermost_c_scope(scopes, declaration.start())
        if scope is not None and scope[0] < offset < scope[1]:
            visible.append((scope, declaration))

    if not visible:
        return None

    return max(
        visible,
        key=lambda item: (item[0][0], item[1].start()),
    )[1]


def has_closer_local_shadow(
    syntax_text: str,
    declaration,
    identifier: str,
    offset: int,
    scopes,
) -> bool:
    """Return true when a nearer local of any supported C type hides a name."""
    binding_scope = innermost_c_scope(scopes, declaration.start())

    declaration_re = re.compile(
        r"(?:^|(?<=[;{}]))\s*"
        r"(?:(?:static|const|CONST|volatile|register|extern)\s+)*"
        r"(?:"
        r"(?:struct|union|enum)\s+[A-Za-z_][A-Za-z0-9_]*"
        r"|(?:unsigned|signed)(?:\s+(?:char|short|int|long)){0,2}"
        r"|(?:void|char|short|int|long|float|double)"
        r"|(?P<type_name>[A-Za-z_][A-Za-z0-9_]*)"
        r")(?=\s|\*)\s*(?P<body>[^;]*);",
        re.DOTALL,
    )

    for statement in declaration_re.finditer(
        syntax_text, declaration.end(), offset
    ):
        if statement.group("type_name") in {
            "break",
            "case",
            "continue",
            "default",
            "do",
            "else",
            "goto",
            "return",
            "sizeof",
            "switch",
            "throw",
            "typedef",
        }:
            continue
        body = statement.group("body")
        body_offset = statement.start("body")
        segment_start = 0
        depth = 0

        for index in range(len(body) + 1):
            char = body[index] if index < len(body) else ","
            if char in "([{":
                depth += 1
            elif char in ")]}" and depth:
                depth -= 1
            elif char == "," and depth == 0:
                segment = body[segment_start:index]
                name_match = re.match(
                    r"\s*(?:\*+\s*)*(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
                    segment,
                )
                if name_match and name_match.group("name") == identifier:
                    name_offset = (
                        body_offset + segment_start + name_match.start("name")
                    )
                    shadow_scope = innermost_c_scope(scopes, name_offset)
                    if (
                        shadow_scope is not None
                        and (
                            binding_scope is None
                            or binding_scope[0] < shadow_scope[0]
                        )
                        and shadow_scope[0] < offset < shadow_scope[1]
                    ):
                        return True
                segment_start = index + 1

    return False


def visible_taskdialog_config_declaration(
    syntax_text: str,
    declarations,
    identifier: str,
    offset: int,
    scopes,
):
    declaration = visible_local_text_declaration(
        declarations, identifier, offset, scopes
    )
    if declaration is None or has_closer_local_shadow(
        syntax_text, declaration, identifier, offset, scopes
    ):
        return None
    return declaration


def is_conditionally_guarded(
    scan_text: str, offset: int, binding_scope, scopes
) -> bool:
    nested_scopes = sorted(
        (
            scope
            for scope in scopes
            if binding_scope[0] < scope[0] < offset < scope[1] < binding_scope[1]
        ),
        key=lambda scope: scope[0],
    )
    for scope in nested_scopes:
        prefix = scan_text[binding_scope[0]:scope[0]]
        if re.search(
            r"(?:\b(?:if|switch|for|while)\s*\([^{}]*\)|\belse|\bdo)\s*$",
            prefix,
            re.DOTALL,
        ):
            return True

    prefix = scan_text[binding_scope[0]:offset]
    return bool(
        re.search(
            r"\b(?:if|for|while)\s*\([^{}]*\)\s*$",
            prefix,
            re.DOTALL,
        )
        or re.search(r"\b(?:else|do)\s*$", prefix)
    )


def indexed_binding_mutation_offsets(
    syntax_text: str,
    identifier: str,
    start_offset: int,
    end_offset: int,
):
    """Yield writes through one or more balanced array index expressions."""
    identifier_re = re.compile(rf"(?<![.>])\b{re.escape(identifier)}\b")

    for match in identifier_re.finditer(syntax_text, start_offset, end_offset):
        cursor = match.end()

        while cursor < end_offset and syntax_text[cursor].isspace():
            cursor += 1
        if cursor >= end_offset or syntax_text[cursor] != "[":
            continue

        while cursor < end_offset and syntax_text[cursor] == "[":
            depth = 0
            while cursor < end_offset:
                character = syntax_text[cursor]
                if character == "[":
                    depth += 1
                elif character == "]":
                    depth -= 1
                    if depth == 0:
                        cursor += 1
                        break
                cursor += 1

            if depth != 0:
                break
            while cursor < end_offset and syntax_text[cursor].isspace():
                cursor += 1

        if re.match(
            r"(?:=(?!=)|(?:<<|>>|[+\-*/%&|^])=|\+\+|--)",
            syntax_text[cursor:end_offset],
        ):
            yield match.start()


def one_hop_runtime_sources(
    scan_text: str,
    identifier: str,
    sink_offset: int,
    default_category: str,
    simple_only: bool = False,
    fail_closed_writes: bool = False,
    mask_explicit_translation: bool = False,
    allow_string_fallback: bool = False,
):
    """Resolve conservative reaching definitions for one local UI binding."""
    scopes = c_brace_scopes(scan_text)
    syntax_text = mask_c_literals(scan_text)
    declarations = list(LOCAL_UI_TEXT_DECLARATION_RE.finditer(syntax_text))
    declaration = visible_local_text_declaration(
        declarations, identifier, sink_offset, scopes
    )
    if declaration is None:
        return None

    binding_scope = innermost_c_scope(scopes, declaration.start())
    events = []
    covered_ranges = []

    initializer = declaration.group("initializer")
    state = []
    simple_definition_count = 0
    if initializer is not None:
        initializer = scan_text[
            declaration.start("initializer"):declaration.end("initializer")
        ]
        state = [
            (category, text, declaration.start("initializer") + offset)
            for category, text, offset in one_hop_expression_source_literals(
                initializer,
                default_category,
                allow_string_fallback=(
                    simple_only or allow_string_fallback
                ),
                mask_explicit_translation=mask_explicit_translation,
            )
        ]
        simple_definition_count = 1
        if simple_only and (
            not state
            or any(category != default_category for category, _, _ in state)
        ):
            return []

    assignment_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*=(?!=)\s*(?P<value>.*?);",
        re.DOTALL,
    )
    for assignment in assignment_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_local_text_declaration(
            declarations, identifier, assignment.start(), scopes
        ) is not declaration:
            continue
        value = scan_text[
            assignment.start("value"):assignment.end("value")
        ]
        sources = [
            (category, text, assignment.start("value") + offset)
            for category, text, offset in one_hop_expression_source_literals(
                value,
                default_category,
                allow_string_fallback=(
                    simple_only or allow_string_fallback
                ),
                mask_explicit_translation=mask_explicit_translation,
            )
        ]
        events.append((assignment.start(), "definition", sources))
        covered_ranges.append((assignment.start(), assignment.end()))

    call_names = {
        match.group(0)
        for match in IDENT_RE.finditer(
            syntax_text[declaration.end():sink_offset]
        )
    }
    for name, _, spans, call_start in find_calls(syntax_text, call_names):
        if call_start < declaration.end() or call_start >= sink_offset:
            continue
        args = [scan_text[start:end] for start, end in spans]
        if visible_local_text_declaration(
            declarations, identifier, call_start, scopes
        ) is not declaration:
            continue
        if any(start <= call_start < end for start, end in covered_ranges):
            continue

        if name == "swprintf_s" and len(args) >= 3:
            target = re.fullmatch(
                rf"\s*{re.escape(identifier)}\s*", args[0]
            )
            if target:
                format_sources = literal_sequences_outside_ui_string_getters(
                    args[2]
                )
                has_conversion = any(
                    PRINTF_SPEC_RE.search(text) for text, _ in format_sources
                )
                category = (
                    "c_runtime_composed" if has_conversion else default_category
                )
                sources = [
                    (category, text, spans[2][0] + offset)
                    for text, offset in format_sources
                    if not is_noise(text)
                ]
                events.append((call_start, "definition", sources))
                covered_ranges.append((call_start, spans[-1][1] + 1))
                continue

        if is_runtime_composer(name):
            continue

        mutates_binding = any(
            re.fullmatch(
                rf"\s*&\s*{re.escape(identifier)}\s*", argument
            )
            or re.fullmatch(
                rf"\s*{re.escape(identifier)}\s*(?:->|\.)\s*Buffer\s*",
                argument,
            )
            or (
                declaration.group("array") is not None
                and re.fullmatch(
                    rf"\s*{re.escape(identifier)}\s*", argument
                )
            )
            for argument in args
        )
        if mutates_binding:
            events.append((call_start, "mutation", []))

    field_assignment_re = re.compile(
        rf"\b{re.escape(identifier)}\s*(?:->|\.)\s*Buffer\s*="
    )
    for assignment in field_assignment_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_local_text_declaration(
            declarations, identifier, assignment.start(), scopes
        ) is declaration:
            events.append((assignment.start(), "mutation", []))

    if simple_only or fail_closed_writes:
        binding_mutation_re = re.compile(
            rf"(?:\+\+|--)\s*\b{re.escape(identifier)}\b"
            rf"|(?<![.>])\b{re.escape(identifier)}\b\s*"
            rf"(?:(?:\+\+|--)|(?:<<|>>|[+\-*/%&|^])=)"
        )
        for mutation in binding_mutation_re.finditer(
            syntax_text, declaration.end(), sink_offset
        ):
            if visible_local_text_declaration(
                declarations, identifier, mutation.start(), scopes
            ) is declaration:
                events.append((mutation.start(), "mutation", []))
        for mutation_offset in indexed_binding_mutation_offsets(
            syntax_text,
            identifier,
            declaration.end(),
            sink_offset,
        ):
            if visible_local_text_declaration(
                declarations, identifier, mutation_offset, scopes
            ) is declaration:
                events.append((mutation_offset, "mutation", []))

    for offset, event_kind, sources in sorted(events, key=lambda event: event[0]):
        conditional = is_conditionally_guarded(
            scan_text, offset, binding_scope, scopes
        )
        if simple_only:
            if (
                event_kind != "definition"
                or conditional
                or not sources
                or simple_definition_count
                or any(
                    category != default_category
                    for category, _, _ in sources
                )
            ):
                return []
            state = sources
            simple_definition_count = 1
            continue
        if event_kind == "mutation" or not sources:
            if not conditional:
                state = []
        elif conditional:
            state.extend(sources)
        else:
            state = sources

    return state


def is_taskdialog_technical_format(text: str) -> bool:
    """Return true for formats whose rendered value contains no prose."""
    if not PRINTF_SPEC_RE.search(text):
        return False

    remainder = PRINTF_SPEC_RE.sub("", text)
    remainder = re.sub(r"0[xX]", "", remainder)
    return re.fullmatch(r"[\d\s\W_]*", remainder) is not None


def taskdialog_expression_sources(
    scan_text: str,
    expression: str,
    expression_offset: int,
    assignment_offset: int,
):
    """Resolve supported untranslated sources for one TaskDialog field."""
    identifier = runtime_target_identifier(expression)

    if identifier is not None:
        sources = one_hop_runtime_sources(
            scan_text,
            identifier,
            assignment_offset,
            "c_taskdialog",
            fail_closed_writes=True,
            mask_explicit_translation=True,
            allow_string_fallback=True,
        )
        if sources is not None:
            return [
                source for source in sources
                if not is_taskdialog_technical_format(source[1])
            ]

    sources = one_hop_expression_source_literals(
        expression,
        "c_taskdialog",
        allow_string_fallback=True,
        mask_explicit_translation=True,
    )
    return [
        (category, visible_text, expression_offset + relative_offset)
        for category, visible_text, relative_offset in sources
        if not is_taskdialog_technical_format(visible_text)
    ]


def taskdialog_designated_initializer_events(
    scan_text: str,
    syntax_text: str,
    declaration,
):
    """Return supported text-field definitions from one config initializer."""
    if declaration.group("initializer") is None:
        return []

    initializer_start = declaration.start("initializer")
    initializer_end = declaration.end("initializer")
    initializer_syntax = syntax_text[initializer_start:initializer_end]
    initializer_match = re.fullmatch(
        r"\s*\{(?P<body>.*)\}\s*",
        initializer_syntax,
        re.DOTALL,
    )
    if initializer_match is None:
        return []

    body_syntax = initializer_match.group("body")
    body_offset = initializer_start + initializer_match.start("body")
    wrapper_prefix = "AuditInitializer("
    wrapped_syntax = f"{wrapper_prefix}{body_syntax})"
    initializer_call = next(
        find_calls(wrapped_syntax, {"AuditInitializer"}),
        None,
    )
    if initializer_call is None:
        return []

    field_names = "|".join(
        sorted(map(re.escape, TASKDIALOG_TEXT_FIELDS), key=len, reverse=True)
    )
    events = []
    _, arguments, spans, _ = initializer_call

    for argument, (argument_start, _) in zip(arguments, spans):
        field_match = re.fullmatch(
            rf"\s*\.\s*(?P<field>{field_names})\s*=(?!=)\s*"
            rf"(?P<value>.*)",
            argument,
            re.DOTALL,
        )
        if field_match is None:
            continue

        value_start = (
            body_offset
            + argument_start
            - len(wrapper_prefix)
            + field_match.start("value")
        )
        value_end = (
            body_offset
            + argument_start
            - len(wrapper_prefix)
            + field_match.end("value")
        )
        sources = taskdialog_expression_sources(
            scan_text,
            scan_text[value_start:value_end],
            value_start,
            value_start,
        )
        events.append((value_start, "field", field_match.group("field"), sources))

    return events


def reaching_taskdialog_field_sources(
    scan_text: str,
    syntax_text: str,
    declaration,
    sink_offset: int,
    declarations,
    scopes,
):
    """Resolve TaskDialog text fields that can reach one concrete sink."""
    identifier = declaration.group("name")
    binding_scope = innermost_c_scope(scopes, declaration.start())
    if binding_scope is None:
        return []

    field_names = "|".join(
        sorted(map(re.escape, TASKDIALOG_TEXT_FIELDS), key=len, reverse=True)
    )
    assignment_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*\.\s*"
        rf"(?P<field>{field_names})\s*=(?!=)\s*(?P<value>.*?);",
        re.DOTALL,
    )
    states = defaultdict(list)
    events = taskdialog_designated_initializer_events(
        scan_text,
        syntax_text,
        declaration,
    )
    covered_ranges = []

    for assignment in assignment_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_taskdialog_config_declaration(
            syntax_text,
            declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is not declaration:
            continue

        value_start = assignment.start("value")
        sources = taskdialog_expression_sources(
            scan_text,
            scan_text[value_start:assignment.end("value")],
            value_start,
            assignment.start(),
        )
        events.append((
            assignment.start(),
            "field",
            assignment.group("field"),
            sources,
        ))
        covered_ranges.append((assignment.start(), assignment.end()))

    whole_assignment_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*=(?!=)\s*.*?;",
        re.DOTALL,
    )
    for assignment in whole_assignment_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_taskdialog_config_declaration(
            syntax_text,
            declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is declaration:
            events.append((assignment.start(), "mutation", None, []))
            covered_ranges.append((assignment.start(), assignment.end()))

    call_names = {
        match.group(0)
        for match in IDENT_RE.finditer(
            syntax_text[declaration.end():sink_offset]
        )
    } - {
        "_Alignof",
        "_Generic",
        "_Static_assert",
        "__alignof",
        "__alignof__",
        "__typeof",
        "__typeof__",
        "alignof",
        "catch",
        "decltype",
        "defined",
        "for",
        "if",
        "noexcept",
        "return",
        "sizeof",
        "static_assert",
        "switch",
        "typeid",
        "typeof",
        "while",
    }
    for _, args, spans, call_start in find_calls(syntax_text, call_names):
        if call_start < declaration.end() or call_start >= sink_offset:
            continue
        if any(start <= call_start < end for start, end in covered_ranges):
            continue
        if visible_taskdialog_config_declaration(
            syntax_text,
            declarations,
            identifier,
            call_start,
            scopes,
        ) is not declaration:
            continue
        if any(
            re.fullmatch(rf"\s*&\s*{re.escape(identifier)}\s*", argument)
            for argument in args
        ):
            events.append((call_start, "mutation", None, []))

    for offset, event_kind, field, sources in sorted(events):
        conditional = is_conditionally_guarded(
            scan_text, offset, binding_scope, scopes
        )
        if event_kind == "mutation":
            if not conditional:
                states.clear()
        elif conditional:
            states[field].extend(sources)
        else:
            states[field] = sources

    return [source for field_sources in states.values() for source in field_sources]


def scan_taskdialog_fields(text: str, scan_text: str, rel: str, entries):
    """Scan text reaching type-confirmed local TaskDialog configurations."""
    if "TASKDIALOGCONFIG" not in scan_text or not any(
        sink_name in scan_text
        for sink_name in (
            "PhShowTaskDialog",
            "TaskDialogIndirect",
            "PhTaskDialogNavigatePage",
        )
    ):
        return

    scopes = c_brace_scopes(scan_text)
    syntax_text = mask_c_literals(scan_text)
    declarations = list(TASKDIALOG_CONFIG_DECLARATION_RE.finditer(syntax_text))
    seen = set()
    sink_specs = {
        "PhShowTaskDialog": 0,
        "TaskDialogIndirect": 0,
        "PhTaskDialogNavigatePage": 1,
    }

    for name, args, _, sink_offset in find_calls(scan_text, sink_specs):
        argument_index = sink_specs[name]
        if argument_index >= len(args):
            continue

        argument = re.fullmatch(
            r"\s*&\s*([A-Za-z_][A-Za-z0-9_]*)\s*",
            args[argument_index],
        )
        if argument is None:
            continue

        identifier = argument.group(1)
        declaration = visible_taskdialog_config_declaration(
            syntax_text, declarations, identifier, sink_offset, scopes
        )
        if declaration is None:
            continue

        sources = reaching_taskdialog_field_sources(
            scan_text,
            syntax_text,
            declaration,
            sink_offset,
            declarations,
            scopes,
        )

        for category, visible_text, source_offset in sources:
            source_key = (category, source_offset, visible_text)
            if source_key in seen:
                continue
            seen.add(source_key)
            entries.append({
                "category": category,
                "file": rel,
                "line": line_of_offset(text, source_offset),
                "english": visible_text,
            })


def taskdialog_button_declarations(syntax_text: str, scopes):
    """Return type-confirmed button arrays and their balanced initializers."""
    scope_ends = {start: end for start, end in scopes}
    declarations = []

    for match in TASKDIALOG_BUTTON_DECLARATION_RE.finditer(syntax_text):
        cursor = match.end()
        while cursor < len(syntax_text) and syntax_text[cursor].isspace():
            cursor += 1

        initializer_start = None
        initializer_end = None
        if match.group("assignment") is not None:
            if cursor >= len(syntax_text) or syntax_text[cursor] != "{":
                continue
            closing = scope_ends.get(cursor)
            if closing is None:
                continue
            initializer_start = cursor + 1
            initializer_end = closing
            cursor = closing + 1

        while cursor < len(syntax_text) and syntax_text[cursor].isspace():
            cursor += 1
        if cursor >= len(syntax_text) or syntax_text[cursor] != ";":
            continue

        declarations.append({
            "match": match,
            "name": match.group("name"),
            "start": match.start(),
            "end": cursor + 1,
            "initializer_start": initializer_start,
            "initializer_end": initializer_end,
        })

    return declarations


def visible_taskdialog_button_declaration(
    syntax_text: str,
    declarations,
    identifier: str,
    offset: int,
    scopes,
):
    """Resolve a visible typed button array without crossing a local shadow."""
    visible = []
    for declaration in declarations:
        if declaration["name"] != identifier or declaration["start"] >= offset:
            continue
        scope = innermost_c_scope(scopes, declaration["start"])
        if scope is None or scope[0] < offset < scope[1]:
            visible.append((scope, declaration))

    if not visible:
        return None

    declaration = max(
        visible,
        key=lambda item: (
            item[0][0] if item[0] is not None else -1,
            item[1]["start"],
        ),
    )[1]
    declaration_match = declaration["match"]
    declaration_scope = innermost_c_scope(scopes, declaration["start"])
    if declaration_scope is None:
        local_shadow_re = re.compile(
            r"(?:^|(?<=[;{}]))\s*"
            r"(?:(?:static|const|CONST|volatile|register|extern)\s+)*"
            r"[A-Za-z_][A-Za-z0-9_]*\s+(?:\*+\s*)?"
            rf"(?P<name>{re.escape(identifier)})\b(?=\s*(?:\[|=|,|;))",
            re.DOTALL,
        )
        for shadow in local_shadow_re.finditer(
            syntax_text, declaration["end"], offset
        ):
            shadow_scope = innermost_c_scope(scopes, shadow.start("name"))
            if (
                shadow_scope is not None
                and shadow_scope[0] < offset < shadow_scope[1]
            ):
                return None
    if has_closer_local_shadow(
        syntax_text,
        declaration_match,
        identifier,
        offset,
        scopes,
    ):
        return None
    return declaration


def split_c_initializer_field_spans(initializer: str):
    """Split one initializer and preserve field spans in the input string."""
    wrapper_prefix = "AuditInitializer("
    wrapped = f"{wrapper_prefix}{initializer})"
    call = next(find_calls(wrapped, {"AuditInitializer"}), None)
    if call is None:
        return []
    _, arguments, spans, _ = call
    return [
        (argument, start - len(wrapper_prefix), end - len(wrapper_prefix))
        for argument, (start, end) in zip(arguments, spans)
    ]


def taskdialog_button_expression_sources(
    scan_text: str,
    expression_start: int,
    expression_end: int,
):
    return taskdialog_expression_sources(
        scan_text,
        scan_text[expression_start:expression_end],
        expression_start,
        expression_start,
    )


def taskdialog_button_text_expression_span(initializer: str):
    """Return the pszButtonText expression span from one button initializer."""
    fields = split_c_initializer_field_spans(initializer)
    for field, field_start, _ in fields:
        designated = re.fullmatch(
            r"\s*\.\s*pszButtonText\s*=(?!=)\s*(?P<value>.*)",
            field,
            re.DOTALL,
        )
        if designated is not None:
            return (
                field_start + designated.start("value"),
                field_start + designated.end("value"),
            )
    if len(fields) >= 2:
        return fields[1][1], fields[1][2]
    return None


def taskdialog_button_initializer_state(
    scan_text: str,
    syntax_text: str,
    declaration,
    scopes,
):
    initializer_start = declaration["initializer_start"]
    initializer_end = declaration["initializer_end"]
    if initializer_start is None:
        return {}

    outer_start = initializer_start - 1
    element_scopes = sorted(
        scope
        for scope in scopes
        if outer_start < scope[0] < scope[1] < initializer_end
        and not any(
            outer_start < parent[0] < scope[0]
            and scope[1] < parent[1] < initializer_end
            for parent in scopes
        )
    )
    state = {}
    for slot, (opening, closing) in enumerate(element_scopes):
        expression_span = taskdialog_button_text_expression_span(
            syntax_text[opening + 1:closing]
        )
        if expression_span is None:
            continue
        field_start, field_end = expression_span
        expression_start = opening + 1 + field_start
        expression_end = opening + 1 + field_end
        state[str(slot)] = taskdialog_button_expression_sources(
            scan_text,
            expression_start,
            expression_end,
        )
    return state


def taskdialog_button_slot_key(index: str, offset: int):
    normalized = re.sub(r"\s+", "", index)
    if "++" in normalized or "--" in normalized:
        return f"dynamic@{offset}"
    return normalized


def reaching_taskdialog_button_sources(
    scan_text: str,
    syntax_text: str,
    declaration,
    sink_offset: int,
    declarations,
    scopes,
):
    """Resolve button text definitions that may reach one concrete sink."""
    identifier = declaration["name"]
    binding_scope = innermost_c_scope(scopes, declaration["start"])
    state = taskdialog_button_initializer_state(
        scan_text,
        syntax_text,
        declaration,
        scopes,
    )
    events = []
    covered_ranges = []

    compound_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*"
        r"\[(?P<index>[^\]]+)\]\s*=(?!=)\s*"
        r"(?:\(\s*TASKDIALOG_BUTTON\s*\)\s*)?"
        r"\{(?P<body>[^{}]*)\}\s*;",
        re.DOTALL,
    )
    for assignment in compound_re.finditer(
        syntax_text, declaration["end"], sink_offset
    ):
        if visible_taskdialog_button_declaration(
            syntax_text,
            declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is not declaration:
            continue
        expression_span = taskdialog_button_text_expression_span(
            assignment.group("body")
        )
        if expression_span is None:
            continue
        field_start, field_end = expression_span
        expression_start = assignment.start("body") + field_start
        expression_end = assignment.start("body") + field_end
        events.append((
            assignment.start(),
            "definition",
            taskdialog_button_slot_key(
                assignment.group("index"), assignment.start()
            ),
            taskdialog_button_expression_sources(
                scan_text,
                expression_start,
                expression_end,
            ),
        ))
        covered_ranges.append((assignment.start(), assignment.end()))

    member_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*"
        r"\[(?P<index>[^\]]+)\]\s*\.\s*pszButtonText\s*"
        r"=(?!=)\s*(?P<value>.*?);",
        re.DOTALL,
    )
    for assignment in member_re.finditer(
        syntax_text, declaration["end"], sink_offset
    ):
        if visible_taskdialog_button_declaration(
            syntax_text,
            declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is not declaration:
            continue
        value_start = assignment.start("value")
        events.append((
            assignment.start(),
            "definition",
            taskdialog_button_slot_key(
                assignment.group("index"), assignment.start()
            ),
            taskdialog_button_expression_sources(
                scan_text,
                value_start,
                assignment.end("value"),
            ),
        ))
        covered_ranges.append((assignment.start(), assignment.end()))

    element_assignment_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*"
        r"\[(?P<index>[^\]]+)\]\s*=(?!=)\s*.*?;",
        re.DOTALL,
    )
    for assignment in element_assignment_re.finditer(
        syntax_text, declaration["end"], sink_offset
    ):
        if any(start <= assignment.start() < end for start, end in covered_ranges):
            continue
        if visible_taskdialog_button_declaration(
            syntax_text,
            declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is not declaration:
            continue
        events.append((
            assignment.start(),
            "definition",
            taskdialog_button_slot_key(
                assignment.group("index"), assignment.start()
            ),
            [],
        ))
        covered_ranges.append((assignment.start(), assignment.end()))

    call_names = {
        match.group(0)
        for match in IDENT_RE.finditer(
            syntax_text[declaration["end"]:sink_offset]
        )
    } - {
        "ARRAYSIZE",
        "RTL_NUMBER_OF",
        "_Alignof",
        "_Generic",
        "_Static_assert",
        "alignof",
        "for",
        "if",
        "sizeof",
        "switch",
        "while",
    }
    for _, arguments, _, call_start in find_calls(syntax_text, call_names):
        if call_start < declaration["end"] or call_start >= sink_offset:
            continue
        if any(start <= call_start < end for start, end in covered_ranges):
            continue
        if visible_taskdialog_button_declaration(
            syntax_text,
            declarations,
            identifier,
            call_start,
            scopes,
        ) is not declaration:
            continue
        mutation_arguments = [
            match
            for argument in arguments
            if (
                match := re.fullmatch(
                    rf"\s*&?\s*{re.escape(identifier)}"
                    r"(?:\s*\[(?P<index>[^\]]+)\])?\s*",
                    argument,
                )
            )
        ]
        for mutation_argument in mutation_arguments:
            index = mutation_argument.group("index")
            if index is None:
                events.append((call_start, "mutation", None, []))
            else:
                events.append((
                    call_start,
                    "slot_mutation",
                    taskdialog_button_slot_key(index, call_start),
                    [],
                ))

    for offset, event_kind, slot, sources in sorted(events):
        conditional = (
            binding_scope is not None
            and is_conditionally_guarded(scan_text, offset, binding_scope, scopes)
        )
        if event_kind == "mutation":
            if not conditional:
                state.clear()
        elif event_kind == "slot_mutation":
            if not conditional:
                state.pop(slot, None)
        elif conditional:
            state.setdefault(slot, []).extend(sources)
        else:
            state[slot] = sources

    return [source for sources in state.values() for source in sources]


def reaching_taskdialog_button_bindings(
    scan_text: str,
    syntax_text: str,
    declaration,
    sink_offset: int,
    config_declarations,
    button_declarations,
    scopes,
):
    """Resolve live pButtons/pRadioButtons bindings and nonzero counts."""
    identifier = declaration.group("name")
    binding_scope = innermost_c_scope(scopes, declaration.start())
    pointer_states = {"Buttons": [], "RadioButtons": []}
    count_states = {"Buttons": False, "RadioButtons": False}
    events = []
    covered_ranges = []

    initializer = declaration.group("initializer")
    if initializer is not None:
        initializer_start = declaration.start("initializer")
        initializer_syntax = syntax_text[
            initializer_start:declaration.end("initializer")
        ]
        initializer_match = re.fullmatch(
            r"\s*\{(?P<body>.*)\}\s*",
            initializer_syntax,
            re.DOTALL,
        )
        if initializer_match is not None:
            body = initializer_match.group("body")
            body_offset = initializer_start + initializer_match.start("body")
            for field, field_start, _ in split_c_initializer_field_spans(body):
                pointer = re.fullmatch(
                    r"\s*\.\s*p(?P<kind>Buttons|RadioButtons)\s*"
                    r"=(?!=)\s*(?P<value>[A-Za-z_][A-Za-z0-9_]*)\s*",
                    field,
                    re.DOTALL,
                )
                if pointer is not None:
                    button_declaration = visible_taskdialog_button_declaration(
                        syntax_text,
                        button_declarations,
                        pointer.group("value"),
                        body_offset + field_start,
                        scopes,
                    )
                    if button_declaration is not None:
                        pointer_states[pointer.group("kind")].append(
                            button_declaration
                        )
                    continue

                count = re.fullmatch(
                    r"\s*\.\s*c(?P<kind>Buttons|RadioButtons)\s*"
                    r"=(?!=)\s*(?P<value>.*)",
                    field,
                    re.DOTALL,
                )
                if count is not None:
                    count_states[count.group("kind")] = not is_c_integer_zero(
                        count.group("value")
                    )

    pointer_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*\.\s*"
        r"p(?P<kind>Buttons|RadioButtons)\s*=(?!=)\s*"
        r"(?P<value>.*?);",
        re.DOTALL,
    )
    for assignment in pointer_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_taskdialog_config_declaration(
            syntax_text,
            config_declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is not declaration:
            continue
        value = re.fullmatch(
            r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*",
            assignment.group("value"),
        )
        button_declaration = None
        if value is not None:
            button_declaration = visible_taskdialog_button_declaration(
                syntax_text,
                button_declarations,
                value.group(1),
                assignment.start(),
                scopes,
            )
        events.append((
            assignment.start(),
            "pointer",
            assignment.group("kind"),
            button_declaration,
        ))
        covered_ranges.append((assignment.start(), assignment.end()))

    count_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*\.\s*"
        r"c(?P<kind>Buttons|RadioButtons)\s*=(?!=)\s*"
        r"(?P<value>.*?);",
        re.DOTALL,
    )
    for assignment in count_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_taskdialog_config_declaration(
            syntax_text,
            config_declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is not declaration:
            continue
        events.append((
            assignment.start(),
            "count",
            assignment.group("kind"),
            not is_c_integer_zero(assignment.group("value")),
        ))
        covered_ranges.append((assignment.start(), assignment.end()))

    whole_assignment_re = re.compile(
        rf"(?<![.>])\b{re.escape(identifier)}\s*=(?!=)\s*.*?;",
        re.DOTALL,
    )
    for assignment in whole_assignment_re.finditer(
        syntax_text, declaration.end(), sink_offset
    ):
        if visible_taskdialog_config_declaration(
            syntax_text,
            config_declarations,
            identifier,
            assignment.start(),
            scopes,
        ) is declaration:
            events.append((assignment.start(), "mutation", None, None))
            covered_ranges.append((assignment.start(), assignment.end()))

    call_names = {
        match.group(0)
        for match in IDENT_RE.finditer(
            syntax_text[declaration.end():sink_offset]
        )
    } - {
        "ARRAYSIZE",
        "RTL_NUMBER_OF",
        "_Alignof",
        "_Generic",
        "_Static_assert",
        "alignof",
        "for",
        "if",
        "sizeof",
        "switch",
        "while",
    }
    read_only_sinks = {
        "PhShowTaskDialog",
        "TaskDialogIndirect",
        "PhTaskDialogNavigatePage",
    }
    for call_name, arguments, _, call_start in find_calls(syntax_text, call_names):
        if call_start < declaration.end() or call_start >= sink_offset:
            continue
        if call_name in read_only_sinks:
            continue
        if any(start <= call_start < end for start, end in covered_ranges):
            continue
        if visible_taskdialog_config_declaration(
            syntax_text,
            config_declarations,
            identifier,
            call_start,
            scopes,
        ) is not declaration:
            continue
        if any(
            re.fullmatch(rf"\s*&\s*{re.escape(identifier)}\s*", argument)
            for argument in arguments
        ):
            events.append((call_start, "mutation", None, None))

    for offset, event_kind, kind, value in sorted(events):
        conditional = is_conditionally_guarded(
            scan_text, offset, binding_scope, scopes
        )
        if event_kind == "mutation":
            if not conditional:
                pointer_states = {"Buttons": [], "RadioButtons": []}
                count_states = {"Buttons": False, "RadioButtons": False}
        elif event_kind == "pointer":
            if conditional:
                if value is not None:
                    pointer_states[kind].append(value)
            else:
                pointer_states[kind] = [value] if value is not None else []
        elif conditional:
            count_states[kind] = count_states[kind] or value
        else:
            count_states[kind] = value

    return [
        button_declaration
        for kind in ("Buttons", "RadioButtons")
        if count_states[kind]
        for button_declaration in pointer_states[kind]
    ]


def scan_taskdialog_buttons(text: str, scan_text: str, rel: str, entries):
    """Scan text reaching type-confirmed TaskDialog button arrays."""
    if (
        "TASKDIALOG_BUTTON" not in scan_text
        or "TASKDIALOGCONFIG" not in scan_text
        or not any(
            sink_name in scan_text
            for sink_name in (
                "PhShowTaskDialog",
                "TaskDialogIndirect",
                "PhTaskDialogNavigatePage",
            )
        )
    ):
        return

    scopes = c_brace_scopes(scan_text)
    syntax_text = mask_c_literals(scan_text)
    config_declarations = list(
        TASKDIALOG_CONFIG_DECLARATION_RE.finditer(syntax_text)
    )
    button_declarations = taskdialog_button_declarations(syntax_text, scopes)
    sink_specs = {
        "PhShowTaskDialog": (0, False),
        "TaskDialogIndirect": (0, True),
        "PhTaskDialogNavigatePage": (1, True),
    }
    seen = set()

    for name, arguments, _, sink_offset in find_calls(scan_text, sink_specs):
        argument_index, raw_sink = sink_specs[name]
        if argument_index >= len(arguments):
            continue
        config_argument = re.fullmatch(
            r"\s*&\s*([A-Za-z_][A-Za-z0-9_]*)\s*",
            arguments[argument_index],
        )
        if config_argument is None:
            continue
        config_declaration = visible_taskdialog_config_declaration(
            syntax_text,
            config_declarations,
            config_argument.group(1),
            sink_offset,
            scopes,
        )
        if config_declaration is None:
            continue

        bindings = reaching_taskdialog_button_bindings(
            scan_text,
            syntax_text,
            config_declaration,
            sink_offset,
            config_declarations,
            button_declarations,
            scopes,
        )
        for button_declaration in bindings:
            sources = reaching_taskdialog_button_sources(
                scan_text,
                syntax_text,
                button_declaration,
                sink_offset,
                button_declarations,
                scopes,
            )
            for category, visible_text, source_offset in sources:
                if raw_sink and category == "c_taskdialog":
                    category = "c_taskdialog_raw"
                source_key = (category, source_offset, visible_text)
                if source_key in seen:
                    continue
                seen.add(source_key)
                entries.append({
                    "category": category,
                    "file": rel,
                    "line": line_of_offset(text, source_offset),
                    "english": visible_text,
                })


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


def append_runtime_target_entries(
    text: str,
    scan_text: str,
    rel: str,
    entries,
    expression: str,
    expression_offset: int,
    sink_offset: int,
    default_category: str,
    one_hop_seen,
    strict_literals: bool = False,
):
    identifier = runtime_target_identifier(expression)
    sources = None
    resolved_one_hop = False

    if identifier is not None:
        sources = one_hop_runtime_sources(
            scan_text,
            identifier,
            sink_offset,
            default_category,
            simple_only=strict_literals,
        )
        resolved_one_hop = sources is not None

    if sources is None:
        if strict_literals:
            source_literals = one_hop_expression_source_literals(
                expression,
                default_category,
                allow_string_fallback=True,
            )
        else:
            source_literals = expression_source_literals(
                expression,
                default_category,
            )
        sources = [
            (category, visible_text, expression_offset + relative_offset)
            for category, visible_text, relative_offset in source_literals
        ]

    for category, visible_text, source_offset in sources:
        entry = {
            "category": category,
            "file": rel,
            "line": line_of_offset(text, source_offset),
            "english": visible_text,
        }
        if resolved_one_hop:
            source_key = (category, source_offset, visible_text)
            if source_key in one_hop_seen:
                continue
            one_hop_seen.add(source_key)
        entries.append(entry)


SYSINFO_IDENTITY_DISPLAY_ROUTES = {
    "plugins/ExtendedTools/etwsys.c": {
        "Disk": ("EtpDiskSysInfoSectionCallback", "IDS_ET_SECTION_DISK"),
        "Network": ("EtpNetworkSysInfoSectionCallback", "IDS_ET_SECTION_NETWORK"),
    },
}


def scan_sysinfo_text_sinks(text: str, scan_text: str, rel: str, entries, one_hop_seen):
    """Scan custom System Information titles that bypass window-text setters."""
    syntax_text = mask_c_literals(scan_text)
    scopes = c_brace_scopes(scan_text)

    def declarators(body, body_start):
        declarations = []
        segment_start = 0
        depth = 0

        for index, char in enumerate(body):
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth = max(0, depth - 1)
            elif char == "," and depth == 0:
                segment = body[segment_start:index]
                name_match = re.match(
                    r"\s*(?:\*+\s*)*(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
                    segment,
                )
                if name_match:
                    declarations.append((
                        name_match.group("name"),
                        body_start + segment_start + name_match.start("name"),
                    ))
                segment_start = index + 1

        segment = body[segment_start:]
        name_match = re.match(
            r"\s*(?:\*+\s*)*(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
            segment,
        )
        if name_match:
            declarations.append((
                name_match.group("name"),
                body_start + segment_start + name_match.start("name"),
            ))

        return declarations

    def typed_declarations(type_name):
        declarations = []
        statement_re = re.compile(
            rf"\b{re.escape(type_name)}\b(?P<body>[^;]*);",
            re.DOTALL,
        )

        for statement in statement_re.finditer(syntax_text):
            declarations.extend(declarators(
                statement.group("body"),
                statement.start("body"),
            ))

        return declarations

    def nested_shadow_declarations(start, end):
        declaration_re = re.compile(
            r"(?:^|(?<=[;{}]))\s*"
            r"(?:(?:static|const|volatile|register|extern)\s+)*"
            r"(?:"
            r"(?:struct|union|enum)\s+[A-Za-z_][A-Za-z0-9_]*"
            r"|[A-Z_][A-Za-z0-9_]*"
            r"|(?:unsigned|signed)(?:\s+(?:char|short|int|long)){0,2}"
            r"|(?:void|char|short|int|long|float|double)"
            r")(?=\s|\*)\s*(?P<body>(?:\*+\s*)?[A-Za-z_][A-Za-z0-9_]*[^;]*);",
            re.DOTALL,
        )
        declarations = []
        fragment = syntax_text[start:end]

        for statement in declaration_re.finditer(fragment):
            declarations.extend(declarators(
                statement.group("body"),
                start + statement.start("body"),
            ))

        return declarations

    draw_panel_declarations = typed_declarations("PPH_SYSINFO_DRAW_PANEL")
    section_declarations = typed_declarations("PH_SYSINFO_SECTION")

    def has_nested_shadow(declaration, identifier, offset):
        declaration_scope = innermost_c_scope(scopes, declaration[1])
        if declaration_scope is None:
            return False

        for name, declaration_offset in nested_shadow_declarations(
            declaration_scope[0] + 1,
            offset,
        ):
            if name != identifier:
                continue
            shadow_scope = innermost_c_scope(scopes, declaration_offset)
            if (
                shadow_scope is not None and
                declaration_scope[0] < shadow_scope[0] < offset < shadow_scope[1]
                ):
                return True

        return False

    def has_visible_declaration(declarations, identifier, offset):
        visible = []

        for declaration in declarations:
            if declaration[0] != identifier or declaration[1] >= offset:
                continue
            scope = innermost_c_scope(scopes, declaration[1])
            if scope is not None and scope[0] < offset < scope[1]:
                visible.append((scope, declaration))

        declaration = max(
            visible,
            key=lambda item: (item[0][0], item[1][1]),
            default=(None, None),
        )[1]
        return declaration is not None and not has_nested_shadow(
            declaration,
            identifier,
            offset,
        )

    def is_whitelisted_identity_display_route(identifier, value, offset):
        route = SYSINFO_IDENTITY_DISPLAY_ROUTES.get(rel, {}).get(value)
        if not route:
            return False

        callback_name, resource_id = route
        scope = innermost_c_scope(scopes, offset)
        if scope is None:
            return False
        body = scan_text[scope[0] + 1:scope[1]]
        if not re.search(
            rf"\b{re.escape(identifier)}\s*\.\s*Callback\s*=\s*"
            rf"{re.escape(callback_name)}\s*;",
            body,
        ):
            return False
        if not re.search(
            rf"\b[A-Za-z_][A-Za-z0-9_]*\s*->\s*CreateSection\s*"
            rf"\(\s*&\s*{re.escape(identifier)}\s*\)",
            body,
        ):
            return False

        signature = re.search(
            rf"\b{re.escape(callback_name)}\s*\([^;]*?\)\s*\{{",
            syntax_text,
            re.DOTALL,
        )
        if not signature:
            return False
        callback_scope = next(
            (
                candidate
                for candidate in scopes
                if candidate[0] == signature.end() - 1
            ),
            None,
        )
        if callback_scope is None:
            return False
        callback_body = scan_text[callback_scope[0] + 1:callback_scope[1]]
        display_assignment = re.search(
            r"\b[A-Za-z_][A-Za-z0-9_]*\s*->\s*Title\s*=\s*"
            r"PhCreateString\s*\((?P<value>.*?)\)\s*;",
            callback_body,
            re.DOTALL,
        )
        return bool(
            display_assignment
            and is_resource_ui_getter(
                display_assignment.group("value"),
                value,
                resource_id,
            )
        )

    for name, args, spans, call_start in find_calls(
        scan_text, {"PhMoveReference", "PhSetReference"}
    ):
        if len(args) < 2:
            continue
        target_match = re.fullmatch(
            r"\s*&\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:->|\.)\s*Title\s*",
            args[0],
        )
        if not target_match or not has_visible_declaration(
            draw_panel_declarations,
            target_match.group(1),
            call_start,
        ):
            continue
        append_runtime_target_entries(
            text,
            scan_text,
            rel,
            entries,
            args[1],
            spans[1][0],
            call_start,
            "c_window_text",
            one_hop_seen,
        )

    for _, args, spans, call_start in find_calls(
        scan_text, {"PhInitializeStringRef"}
    ):
        if len(args) < 2:
            continue
        target_match = re.fullmatch(
            r"\s*&\s*([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*Name\s*",
            args[0],
        )
        if not target_match or not has_visible_declaration(
            section_declarations,
            target_match.group(1),
            call_start,
        ):
            continue
        identity = adjacent_literal_text(args[1])
        if (
            identity is not None
            and is_whitelisted_identity_display_route(
                target_match.group(1),
                identity,
                call_start,
            )
        ):
            continue
        append_runtime_target_entries(
            text,
            scan_text,
            rel,
            entries,
            args[1],
            spans[1][0],
            call_start,
            "c_window_text",
            one_hop_seen,
        )

    assignment_specs = (
        (
            re.compile(
                r"\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?:->|\.)\s*Title\s*=(?!=)\s*(?P<value>.*?);",
                re.DOTALL,
            ),
            draw_panel_declarations,
        ),
        (
            re.compile(
                r"\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*Name\s*=(?!=)\s*(?P<value>.*?);",
                re.DOTALL,
            ),
            section_declarations,
        ),
    )
    for assignment_re, declarations in assignment_specs:
        for assignment in assignment_re.finditer(syntax_text):
            if not has_visible_declaration(
                declarations,
                assignment.group("name"),
                assignment.start(),
            ):
                continue
            value_start = assignment.start("value")
            append_runtime_target_entries(
                text,
                scan_text,
                rel,
                entries,
                scan_text[value_start:assignment.end("value")],
                value_start,
                assignment.start(),
                "c_window_text",
                one_hop_seen,
            )


def split_c_initializer_fields(initializer: str):
    """Split one flat C initializer using the balanced call parser."""
    wrapped = f"AuditInitializer({initializer})"
    call = next(find_calls(wrapped, {"AuditInitializer"}), None)
    return call[1] if call else []


def scan_device_property_table_routes(
    text: str,
    scan_text: str,
    rel: str,
    entries,
    related_sources=None,
):
    """Resolve HardwareDevices property labels through their three UI sinks."""
    declaration = re.search(
        r"\bDeviceItemPropertyTable\s*\[\s*\]\s*=\s*"
        r"\{(?P<body>.*?)\}\s*;",
        scan_text,
        re.DOTALL,
    )
    if declaration is None:
        return

    rows = []
    for initializer in re.finditer(r"\{(?P<body>[^{}]*)\}", declaration.group("body")):
        fields = split_c_initializer_fields(initializer.group("body"))
        literal_field = next(
            (
                (index, adjacent_literal_text(field))
                for index, field in enumerate(fields)
                if adjacent_literal_text(field) is not None
            ),
            None,
        )
        if literal_field is None or is_noise(literal_field[1]):
            continue
        literal_index, visible_text = literal_field
        resourceized = any(
            re.fullmatch(r"\s*IDS_HD_[A-Z0-9_]+\s*", field)
            for field in fields[:literal_index]
        )
        rows.append((
            visible_text,
            resourceized,
            declaration.start("body") + initializer.start("body"),
        ))

    if not rows:
        return

    sources = [(rel, text, scan_text)]
    if related_sources:
        sources.extend(related_sources)

    helper_is_stable = False
    helper_re = re.compile(
        r"\bDevicePropertyTableEntryGetColumnName\s*\([^;{}]*\)\s*"
        r"\{(?P<body>[^{}]*)\}",
        re.DOTALL,
    )
    for _source_rel, _source_text, source_scan_text in sources:
        helper = helper_re.search(source_scan_text)
        if helper is None:
            continue
        helper_body = helper.group("body")
        if (
            re.search(
                r"\breturn\s+PhGetStringOrDefault\s*\(\s*"
                r"HardwareDevicesGetUiStringObject\s*"
                r"\(\s*Entry\s*->\s*ResourceId\s*\)\s*,\s*"
                r"Entry\s*->\s*ColumnName\s*\)\s*;",
                helper_body,
            )
            and "PH_AUTO" not in helper_body
            and "PhLoadUiString" not in helper_body
        ):
            helper_is_stable = True
            break

    routes = {
        "c_treenew_col": (
            re.compile(
                r"\bPhAddTreeNewColumn\s*\([^;]*?"
                r"DevicePropertyTableEntryGetColumnName\s*\(\s*entry\s*\)",
                re.DOTALL,
            ),
            re.compile(
                r"\bPhAddTreeNewColumn\s*\([^;]*?"
                r"entry\s*->\s*ColumnName",
                re.DOTALL,
            ),
        ),
        "c_listview_item": (
            re.compile(
                r"\bname\s*=\s*DevicePropertyTableEntryGetColumnName\s*"
                r"\(\s*&\s*DeviceItemPropertyTable\s*\[\s*propClass\s*\]\s*\)\s*;"
                r"[\s\S]*?\bPhAddListViewItem\s*\([^;]*?\bname\b",
            ),
            re.compile(
                r"\bname\s*=\s*DeviceItemPropertyTable\s*"
                r"\[\s*propClass\s*\]\s*\.\s*ColumnName\s*;"
                r"[\s\S]*?\bPhAddListViewItem\s*\([^;]*?\bname\b",
            ),
        ),
        "c_listview_group_item": (
            re.compile(
                r"\bPhAddListViewGroupItem\s*\([^;]*?"
                r"DevicePropertyTableEntryGetColumnName\s*\(\s*entry\s*\)",
                re.DOTALL,
            ),
            re.compile(
                r"\bPhAddListViewGroupItem\s*\([^;]*?"
                r"entry\s*->\s*ColumnName",
                re.DOTALL,
            ),
        ),
    }

    for category, (native_route, raw_route) in routes.items():
        route_source = next(
            (
                source
                for source in sources
                if native_route.search(source[2]) or raw_route.search(source[2])
            ),
            None,
        )
        if route_source is None:
            continue

        source_rel, source_text, source_scan_text = route_source
        raw = raw_route.search(source_scan_text)
        native = native_route.search(source_scan_text)
        route_is_native = native is not None and raw is None and helper_is_stable
        route_offset = (native or raw).start() if (native or raw) else 0

        for visible_text, resourceized, table_offset in rows:
            if route_is_native and resourceized:
                continue
            entries.append({
                "category": category,
                "file": source_rel,
                "line": line_of_offset(
                    source_text,
                    route_offset if raw is not None or native is not None else table_offset,
                ),
                "english": visible_text,
            })


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
    one_hop_seen = set()

    related_device_property_sources = []
    if rel == "plugins/HardwareDevices/devicetree.c":
        for related_name in ("deviceprops.c", "devices.h"):
            related_path = os.path.join(os.path.dirname(path), related_name)
            try:
                with open(
                    related_path,
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as related_file:
                    related_text = related_file.read()
            except OSError:
                continue
            related_device_property_sources.append((
                os.path.relpath(related_path, REPO_ROOT).replace("\\", "/"),
                related_text,
                mask_c_comments(related_text),
            ))

    scan_device_property_table_routes(
        text,
        scan_text,
        rel,
        entries,
        related_device_property_sources,
    )

    scan_sysinfo_text_sinks(text, scan_text, rel, entries, one_hop_seen)
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
                    append_runtime_target_entries(
                        text,
                        scan_text,
                        rel,
                        entries,
                        args[idx],
                        spans[idx][0],
                        call_start,
                        cat,
                        one_hop_seen,
                        strict_literals=name in STRICT_LITERAL_CALLS,
                    )
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
                    append_runtime_target_entries(
                        text,
                        scan_text,
                        rel,
                        entries,
                        args[idx],
                        spans[idx][0],
                        call_start,
                        category,
                        one_hop_seen,
                    )
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

    scan_taskdialog_fields(text, scan_text, rel, entries)
    scan_taskdialog_buttons(text, scan_text, rel, entries)

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

OPTIONS_SECTION_RE = re.compile(r'\bPhOptionsCreateSection\s*\(\s*(L"(?:[^"\\]|\\.)*")')


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

    def is_resource_backed_tab_identity(variable, identity):
        assignment_re = re.compile(
            rf"\b(?P<page>[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*Name\s*=\s*"
            rf"{re.escape(variable)}\s*;"
        )
        page_assignments = list(assignment_re.finditer(text))

        for assignment in page_assignments:
            page = assignment.group("page")
            next_assignment = re.search(
                rf"\b{re.escape(page)}\s*\.\s*Name\s*=",
                text[assignment.end():],
            )
            route_end = (
                assignment.end() + next_assignment.start()
                if next_assignment
                else len(text)
            )
            route_text = text[assignment.end():route_end]
            route = next(
                find_calls(route_text, {"PhPluginCreateTabPage2"}),
                None,
            )
            if not route or len(route[1]) < 2:
                continue
            if not re.fullmatch(
                rf"\s*&\s*{re.escape(page)}\s*",
                route[1][0],
            ):
                continue
            display_match = re.fullmatch(
                r"\s*&\s*([A-Za-z_][A-Za-z0-9_]*)\s*",
                route[1][1],
            )
            if not display_match:
                continue
            display_variable = display_match.group(1)

            for _, args, _, _ in find_calls(
                text, {"PhInitializeStringRefLongHint"}
            ):
                if len(args) < 2 or not re.fullmatch(
                    rf"\s*&\s*{re.escape(display_variable)}\s*",
                    args[0],
                ):
                    continue
                if is_resource_ui_getter(args[1], identity):
                    return True

        return False

    for m in PAGE_NAME_RE.finditer(text):
        t = literal_text(m.group(2))
        if is_noise(t):
            continue
        if is_resource_backed_tab_identity(m.group(1), t):
            continue
        entries.append({
            "category": "c_tab", "file": rel,
            "line": line_of_offset(text, m.start()), "english": t,
        })

    for name, args, spans, call_start in find_calls(
        text, {"CreateListSection", "CreateListSection2"}
    ):
        if not args:
            continue
        identity = adjacent_literal_text(args[0])
        if identity is None or is_noise(identity):
            continue

        display_is_native = (
            name == "CreateListSection2"
            and len(args) >= 2
            and is_resource_ui_getter(args[1], identity)
        )
        if not display_is_native:
            entries.append({
                "category": "c_window_text",
                "file": rel,
                "line": line_of_offset(text, spans[0][0]),
                "english": identity,
            })

        if name == "CreateListSection2" and len(args) >= 2:
            for display_text, display_offset in literal_sequences_outside_ui_string_getters(
                args[1]
            ):
                if not is_noise(display_text):
                    entries.append({
                        "category": "c_window_text",
                        "file": rel,
                        "line": line_of_offset(
                            text,
                            spans[1][0] + display_offset,
                        ),
                        "english": display_text,
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
