/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2011-2016
 *     dmex    2017-2023
 */

#include <phapp.h>
#include <settings.h>
#include <phsettings.h>
#include <winsta.h>

typedef struct _SESSION_HOTKEY_ENTRY
{
    ULONG ResourceId;
    ULONG VirtualKey;
} SESSION_HOTKEY_ENTRY, *PSESSION_HOTKEY_ENTRY;

static CONST SESSION_HOTKEY_ENTRY PhpSessionSpecialKeyEntries[] =
{
    { IDS_PH_SESSION_KEY_BACKSPACE, VK_BACK },
    { IDS_PH_SESSION_KEY_DELETE, VK_DELETE },
    { IDS_PH_SESSION_KEY_DOWN, VK_DOWN },
    { IDS_PH_SESSION_KEY_END, VK_END },
    { IDS_PH_SESSION_KEY_ENTER, VK_RETURN },
    { 0, VK_F2 },
    { 0, VK_F3 },
    { 0, VK_F4 },
    { 0, VK_F5 },
    { 0, VK_F6 },
    { 0, VK_F7 },
    { 0, VK_F8 },
    { 0, VK_F9 },
    { 0, VK_F10 },
    { 0, VK_F11 },
    { 0, VK_F12 },
    { IDS_PH_SESSION_KEY_HOME, VK_HOME },
    { IDS_PH_SESSION_KEY_INSERT, VK_INSERT },
    { IDS_PH_SESSION_KEY_LEFT, VK_LEFT },
    { 0, VK_SUBTRACT },
    { IDS_PH_SESSION_KEY_PAGE_DOWN, VK_NEXT },
    { IDS_PH_SESSION_KEY_PAGE_UP, VK_PRIOR },
    { 0, VK_ADD },
    { IDS_PH_SESSION_KEY_PRINT_SCREEN, VK_SNAPSHOT },
    { IDS_PH_SESSION_KEY_RIGHT, VK_RIGHT },
    { IDS_PH_SESSION_KEY_SPACE, VK_SPACE },
    { 0, VK_MULTIPLY },
    { IDS_PH_SESSION_KEY_TAB, VK_TAB },
    { IDS_PH_SESSION_KEY_UP, VK_UP }
};

static INT PhpAddSessionShadowHotKey(
    _In_ HWND ComboBoxHandle,
    _In_ PCWSTR Text,
    _In_ ULONG VirtualKey
    )
{
    INT itemIndex;

    itemIndex = ComboBox_AddString(ComboBoxHandle, Text);

    if (itemIndex >= 0)
    {
        if (ComboBox_SetItemData(
            ComboBoxHandle,
            itemIndex,
            UlongToPtr(VirtualKey)
            ) != CB_ERR)
        {
            return itemIndex;
        }

        ComboBox_DeleteString(ComboBoxHandle, itemIndex);
    }

    return CB_ERR;
}

static VOID PhpAddSessionShadowSpecialHotKey(
    _In_ HWND ComboBoxHandle,
    _In_ CONST SESSION_HOTKEY_ENTRY* Entry
    )
{
    PPH_STRING formattedText = NULL;
    PCWSTR text;
    WCHAR symbolText[] = L"{ }";

    if (Entry->ResourceId)
    {
        text = PhGetApplicationUiString(Entry->ResourceId);
    }
    else if (Entry->VirtualKey >= VK_F2 && Entry->VirtualKey <= VK_F12)
    {
        formattedText = PhFormatString(L"{F%lu}", Entry->VirtualKey - VK_F1 + 1);
        text = PhGetString(formattedText);
    }
    else
    {
        switch (Entry->VirtualKey)
        {
        case VK_SUBTRACT:
            symbolText[1] = L'-';
            break;
        case VK_ADD:
            symbolText[1] = L'+';
            break;
        case VK_MULTIPLY:
            symbolText[1] = L'*';
            break;
        default:
            return;
        }

        text = symbolText;
    }

    PhpAddSessionShadowHotKey(ComboBoxHandle, text, Entry->VirtualKey);

    if (formattedText)
        PhDereferenceObject(formattedText);
}

static BOOLEAN PhpIsSessionShadowHotKey(
    _In_ ULONG VirtualKey
    )
{
    if (
        (VirtualKey >= L'0' && VirtualKey <= L'9') ||
        (VirtualKey >= L'A' && VirtualKey <= L'Z')
        )
    {
        return TRUE;
    }

    for (ULONG i = 0; i < ARRAYSIZE(PhpSessionSpecialKeyEntries); i++)
    {
        if (PhpSessionSpecialKeyEntries[i].VirtualKey == VirtualKey)
            return TRUE;
    }

    return FALSE;
}

static BOOLEAN PhpGetSessionShadowHotKey(
    _In_ HWND ComboBoxHandle,
    _Out_ PULONG VirtualKey
    )
{
    INT selectedIndex;
    LRESULT selectedData;

    selectedIndex = ComboBox_GetCurSel(ComboBoxHandle);

    if (selectedIndex == CB_ERR)
        return FALSE;

    selectedData = ComboBox_GetItemData(ComboBoxHandle, selectedIndex);

    if (selectedData == CB_ERR || !PhpIsSessionShadowHotKey((ULONG)selectedData))
        return FALSE;

    *VirtualKey = (ULONG)selectedData;
    return TRUE;
}

static BOOLEAN PhpSelectSessionShadowHotKey(
    _In_ HWND ComboBoxHandle,
    _In_ ULONG VirtualKey
    )
{
    for (INT i = 0; i < ComboBox_GetCount(ComboBoxHandle); i++)
    {
        LRESULT itemData;

        itemData = ComboBox_GetItemData(ComboBoxHandle, i);

        if (itemData != CB_ERR && (ULONG)itemData == VirtualKey)
        {
            ComboBox_SetCurSel(ComboBoxHandle, i);
            return TRUE;
        }
    }

    return FALSE;
}

INT_PTR CALLBACK PhpSessionShadowDlgProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    );

VOID PhShowSessionShadowDialog(
    _In_ HWND ParentWindowHandle,
    _In_ ULONG SessionId
    )
{
    ULONG sessionId = ULONG_MAX;

    PhGetProcessSessionId(NtCurrentProcess(), &sessionId);

    if (SessionId == sessionId)
    {
        PhShowError2(ParentWindowHandle, PhGetApplicationUiString(IDS_PH_UNABLE_SHADOW_SESSION), L"%s", PhGetApplicationUiString(IDS_PH_CANNOT_CONTROL_CURRENT_SESSION));
        return;
    }

    PhDialogBox(
        PhInstanceHandle,
        MAKEINTRESOURCE(IDD_SHADOWSESSION),
        ParentWindowHandle,
        PhpSessionShadowDlgProc,
        UlongToPtr(SessionId)
        );
}

INT_PTR CALLBACK PhpSessionShadowDlgProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    )
{
    switch (uMsg)
    {
    case WM_INITDIALOG:
        {
            HWND virtualKeyComboBox;
            PH_INTEGER_PAIR hotkey;

            PhSetWindowContext(hwndDlg, PH_WINDOW_CONTEXT_DEFAULT, UlongToPtr((ULONG)lParam));

            PhCenterWindow(hwndDlg, GetParent(hwndDlg));

            hotkey = PhGetIntegerPairSetting(SETTING_SESSION_SHADOW_HOTKEY);

            // Set up the hotkeys.

            virtualKeyComboBox = GetDlgItem(hwndDlg, IDC_VIRTUALKEY);

            for (WCHAR key = L'0'; key <= L'9'; key++)
            {
                WCHAR keyText[2] = { key, UNICODE_NULL };

                PhpAddSessionShadowHotKey(virtualKeyComboBox, keyText, key);
            }

            for (WCHAR key = L'A'; key <= L'Z'; key++)
            {
                WCHAR keyText[2] = { key, UNICODE_NULL };

                PhpAddSessionShadowHotKey(virtualKeyComboBox, keyText, key);
            }

            for (ULONG i = 0; i < ARRAYSIZE(PhpSessionSpecialKeyEntries); i++)
                PhpAddSessionShadowSpecialHotKey(virtualKeyComboBox, &PhpSessionSpecialKeyEntries[i]);

            if (!PhpSelectSessionShadowHotKey(virtualKeyComboBox, (ULONG)hotkey.X))
                PhpSelectSessionShadowHotKey(virtualKeyComboBox, VK_MULTIPLY);

            // Set up the modifiers.

            Button_SetCheck(GetDlgItem(hwndDlg, IDC_SHIFT), hotkey.Y & KBDSHIFT);
            Button_SetCheck(GetDlgItem(hwndDlg, IDC_CTRL), hotkey.Y & KBDCTRL);
            Button_SetCheck(GetDlgItem(hwndDlg, IDC_ALT), hotkey.Y & KBDALT);

            PhInitializeWindowTheme(hwndDlg, PhEnableThemeSupport);
        }
        break;
    case WM_DESTROY:
        {
            PhRemoveWindowContext(hwndDlg, PH_WINDOW_CONTEXT_DEFAULT);
        }
        break;
    case WM_COMMAND:
        {
            switch (LOWORD(wParam))
            {
            case IDCANCEL:
                EndDialog(hwndDlg, IDCANCEL);
                break;
            case IDOK:
                {
                    ULONG sessionId = PtrToUlong(PhGetWindowContext(hwndDlg, PH_WINDOW_CONTEXT_DEFAULT));
                    ULONG virtualKey;
                    ULONG modifiers;
                    PPH_STRING computerName;

                    if (!PhpGetSessionShadowHotKey(
                        GetDlgItem(hwndDlg, IDC_VIRTUALKEY),
                        &virtualKey
                        ))
                    {
                        break;
                    }

                    modifiers = 0;

                    if (Button_GetCheck(GetDlgItem(hwndDlg, IDC_SHIFT)) == BST_CHECKED)
                        modifiers |= KBDSHIFT;
                    if (Button_GetCheck(GetDlgItem(hwndDlg, IDC_CTRL)) == BST_CHECKED)
                        modifiers |= KBDCTRL;
                    if (Button_GetCheck(GetDlgItem(hwndDlg, IDC_ALT)) == BST_CHECKED)
                        modifiers |= KBDALT;

                    if (computerName = PhGetActiveComputerName())
                    {
                        if (WinStationShadow(NULL, PhGetString(computerName), sessionId, (UCHAR)virtualKey, (USHORT)modifiers))
                        {
                            PH_INTEGER_PAIR hotkey;

                            hotkey.X = virtualKey;
                            hotkey.Y = modifiers;
                            PhSetIntegerPairSetting(SETTING_SESSION_SHADOW_HOTKEY, hotkey);

                            EndDialog(hwndDlg, IDOK);
                        }
                        else
                        {
                            PhShowStatus(hwndDlg, PhGetApplicationUiString(IDS_PH_UNABLE_REMOTE_CONTROL_SESSION), 0, GetLastError());
                        }

                        PhDereferenceObject(computerName);
                    }
                    else
                    {
                        PhShowStatus(hwndDlg, PhGetApplicationUiString(IDS_PH_UNABLE_REMOTE_CONTROL_SESSION), 0, ERROR_DS_NAME_TOO_LONG);
                    }
                }
                break;
            }
        }
        break;
    case WM_CTLCOLORBTN:
        return HANDLE_WM_CTLCOLORBTN(hwndDlg, wParam, lParam, PhWindowThemeControlColor);
    case WM_CTLCOLORDLG:
        return HANDLE_WM_CTLCOLORDLG(hwndDlg, wParam, lParam, PhWindowThemeControlColor);
    case WM_CTLCOLORSTATIC:
        return HANDLE_WM_CTLCOLORSTATIC(hwndDlg, wParam, lParam, PhWindowThemeControlColor);
    }

    return FALSE;
}
