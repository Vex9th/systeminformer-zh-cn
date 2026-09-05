/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2010-2013
 *     dmex    2019-2023
 *
 */

#include <phapp.h>
#include <lsasup.h>
#include <winsta.h>

typedef struct _PHP_MESSAGE_ICON_ENTRY
{
    ULONG ResourceId;
    ULONG Icon;
} PHP_MESSAGE_ICON_ENTRY, *PPHP_MESSAGE_ICON_ENTRY;

static CONST PHP_MESSAGE_ICON_ENTRY PhpMessageIcons[] =
{
    { IDS_PH_MESSAGE_ICON_NONE, MB_OK },
    { IDS_PH_MESSAGE_ICON_INFORMATION, MB_ICONINFORMATION },
    { IDS_PH_MESSAGE_ICON_WARNING, MB_ICONWARNING },
    { IDS_PH_MESSAGE_ICON_ERROR, MB_ICONERROR },
    { IDS_PH_MESSAGE_ICON_QUESTION, MB_ICONQUESTION }
};

INT_PTR CALLBACK PhpSessionSendMessageDlgProc(
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
            HWND iconComboBox;
            PPH_STRING currentUserName;

            PhSetWindowContext(hwndDlg, PH_WINDOW_CONTEXT_DEFAULT, UlongToPtr((ULONG)lParam));

            PhCenterWindow(hwndDlg, GetParent(hwndDlg));

            iconComboBox = GetDlgItem(hwndDlg, IDC_TYPE);
            for (ULONG i = 0; i < ARRAYSIZE(PhpMessageIcons); i++)
            {
                INT itemIndex;

                itemIndex = ComboBox_AddString(
                    iconComboBox,
                    PhGetApplicationUiString(PhpMessageIcons[i].ResourceId)
                    );

                if (itemIndex >= 0)
                {
                    if (ComboBox_SetItemData(
                        iconComboBox,
                        itemIndex,
                        UlongToPtr(PhpMessageIcons[i].Icon)
                        ) == CB_ERR)
                    {
                        ComboBox_DeleteString(iconComboBox, itemIndex);
                        continue;
                    }

                    if (PhpMessageIcons[i].Icon == MB_OK)
                        ComboBox_SetCurSel(iconComboBox, itemIndex);
                }
            }

            if (currentUserName = PhGetTokenUserString(PhGetOwnTokenAttributes().TokenHandle, TRUE))
            {
                PhSetDialogItemText(
                    hwndDlg,
                    IDC_TITLE,
                    PhaFormatString(L"Message from %s", currentUserName->Buffer)->Buffer
                    );
                PhDereferenceObject(currentUserName);
            }

            PhSetDialogFocus(hwndDlg, GetDlgItem(hwndDlg, IDC_TEXT));

            PhInitializeWindowTheme(hwndDlg, PhEnableThemeSupport); // HACK (dmex)
        }
        break;
    case WM_DESTROY:
        {
            PhRemoveWindowContext(hwndDlg, PH_WINDOW_CONTEXT_DEFAULT);
        }
        break;
    case WM_COMMAND:
        {
            switch (GET_WM_COMMAND_ID(wParam, lParam))
            {
            case IDCANCEL:
                EndDialog(hwndDlg, IDCANCEL);
                break;
            case IDOK:
                {
                    ULONG sessionId = PtrToUlong(PhGetWindowContext(hwndDlg, PH_WINDOW_CONTEXT_DEFAULT));
                    PPH_STRING title;
                    PPH_STRING text;
                    ULONG icon = 0;
                    ULONG64 timeout = 0;
                    ULONG response;
                    HWND iconComboBox;
                    INT selectedIndex;
                    LRESULT selectedIcon;

                    title = PhaGetDlgItemText(hwndDlg, IDC_TITLE);
                    text = PhaGetDlgItemText(hwndDlg, IDC_TEXT);
                    iconComboBox = GetDlgItem(hwndDlg, IDC_TYPE);

                    selectedIndex = ComboBox_GetCurSel(iconComboBox);

                    if (selectedIndex == CB_ERR)
                        break;

                    selectedIcon = ComboBox_GetItemData(iconComboBox, selectedIndex);

                    if (selectedIcon == CB_ERR)
                        break;

                    icon = (ULONG)selectedIcon;

                    PhStringToInteger64(
                        &PhaGetDlgItemText(hwndDlg, IDC_TIMEOUT)->sr,
                        10,
                        &timeout
                        );

                    if (WinStationSendMessageW(
                        NULL,
                        sessionId,
                        title->Buffer,
                        (ULONG)title->Length,
                        text->Buffer,
                        (ULONG)text->Length,
                        icon,
                        (ULONG)timeout,
                        &response,
                        TRUE
                        ))
                    {
                        EndDialog(hwndDlg, IDOK);
                    }
                    else
                    {
                        PhShowStatus(hwndDlg, PhGetApplicationUiString(IDS_PH_UNABLE_SEND_MESSAGE), 0, GetLastError());
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

VOID PhShowSessionSendMessageDialog(
    _In_ HWND ParentWindowHandle,
    _In_ ULONG SessionId
    )
{
    PhDialogBox(
        NtCurrentImageBase(),
        MAKEINTRESOURCE(IDD_EDITMESSAGE),
        ParentWindowHandle,
        PhpSessionSendMessageDlgProc,
        UlongToPtr(SessionId)
        );
}
