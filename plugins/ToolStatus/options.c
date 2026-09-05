/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2010-2013
 *     dmex    2011-2026
 *
 */

#include "toolstatus.h"

typedef struct _GRAPH_TYPE_ITEM
{
    PH_TASKBAR_ICON Type;
    ULONG ResourceId;
    PCWSTR Fallback;
} GRAPH_TYPE_ITEM;

static CONST GRAPH_TYPE_ITEM GraphTypeItems[] =
{
    { TASKBAR_ICON_NONE, IDS_TS_GRAPH_NONE, L"None" },
    { TASKBAR_ICON_CPU_USAGE, IDS_TS_STATUS_LABEL_CPU_USAGE, L"CPU usage" },
    { TASKBAR_ICON_CPU_HISTORY, IDS_TS_GRAPH_CPU_HISTORY, L"CPU history" },
    { TASKBAR_ICON_IO_HISTORY, IDS_TS_GRAPH_IO_HISTORY, L"I/O history" },
    { TASKBAR_ICON_COMMIT_HISTORY, IDS_TS_GRAPH_COMMIT_CHARGE_HISTORY, L"Commit charge history" },
    { TASKBAR_ICON_PHYSICAL_HISTORY, IDS_TS_GRAPH_PHYSICAL_MEMORY_HISTORY, L"Physical memory history" },
};

INT_PTR CALLBACK OptionsDlgProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    )
{
    switch (WindowMessage)
    {
    case WM_INITDIALOG:
        {
            HWND graphTypeHandle;
            ULONG graphType;
            INT selectedIndex = CB_ERR;

            Button_SetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_TOOLBAR), ToolStatusConfig.ToolBarEnabled ? BST_CHECKED : BST_UNCHECKED);
            Button_SetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_STATUSBAR), ToolStatusConfig.StatusBarEnabled ? BST_CHECKED : BST_UNCHECKED);
            Button_SetCheck(GetDlgItem(WindowHandle, IDC_RESOLVEGHOSTWINDOWS), ToolStatusConfig.ResolveGhostWindows ? BST_CHECKED : BST_UNCHECKED);
            Button_SetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_AUTOHIDE_MENU), ToolStatusConfig.AutoHideMenu ? BST_CHECKED : BST_UNCHECKED);
#if TOOLSTATUS_ENABLE_MENUBAR
            Button_SetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_MENUBAR), ToolStatusConfig.EnableMenuBar ? BST_CHECKED : BST_UNCHECKED);
#endif
            Button_SetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_AUTOFOCUS_SEARCH), ToolStatusConfig.SearchAutoFocus ? BST_CHECKED : BST_UNCHECKED);
            Button_SetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_LARGETOOLBARICON), ToolStatusConfig.ToolBarLargeIcons ? BST_CHECKED : BST_UNCHECKED);

            graphTypeHandle = GetDlgItem(WindowHandle, IDC_CURRENT);
            graphType = PhGetIntegerSetting(SETTING_NAME_TASKBARDISPLAYSTYLE);

            for (ULONG i = 0; i < RTL_NUMBER_OF(GraphTypeItems); i++)
            {
                INT itemIndex;

                itemIndex = ComboBox_AddString(
                    graphTypeHandle,
                    ToolStatusGetUiString(
                        GraphTypeItems[i].ResourceId,
                        GraphTypeItems[i].Fallback
                        )
                    );

                if (itemIndex == CB_ERR || itemIndex == CB_ERRSPACE)
                    continue;

                if (ComboBox_SetItemData(
                    graphTypeHandle,
                    itemIndex,
                    UlongToPtr(GraphTypeItems[i].Type)
                    ) == CB_ERR)
                {
                    ComboBox_DeleteString(graphTypeHandle, itemIndex);
                    continue;
                }

                if (GraphTypeItems[i].Type == graphType ||
                    (selectedIndex == CB_ERR && GraphTypeItems[i].Type == TASKBAR_ICON_NONE))
                {
                    selectedIndex = itemIndex;
                }
            }

            if (selectedIndex != CB_ERR)
                ComboBox_SetCurSel(graphTypeHandle, selectedIndex);
        }
        break;
    case WM_DESTROY:
        {
            HWND graphTypeHandle;
            INT selectedIndex;
            PH_TASKBAR_ICON graphType = TASKBAR_ICON_NONE;

            ReBarSaveLayoutSettings();

            ToolStatusConfig.ToolBarEnabled = Button_GetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_TOOLBAR)) == BST_CHECKED;
            ToolStatusConfig.StatusBarEnabled = Button_GetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_STATUSBAR)) == BST_CHECKED;
            ToolStatusConfig.ResolveGhostWindows = Button_GetCheck(GetDlgItem(WindowHandle, IDC_RESOLVEGHOSTWINDOWS)) == BST_CHECKED;
            ToolStatusConfig.AutoHideMenu = Button_GetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_AUTOHIDE_MENU)) == BST_CHECKED;
#if TOOLSTATUS_ENABLE_MENUBAR
            ToolStatusConfig.EnableMenuBar = Button_GetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_MENUBAR)) == BST_CHECKED;
#endif
            ToolStatusConfig.SearchAutoFocus = Button_GetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_AUTOFOCUS_SEARCH)) == BST_CHECKED;
            ToolStatusConfig.ToolBarLargeIcons = Button_GetCheck(GetDlgItem(WindowHandle, IDC_ENABLE_LARGETOOLBARICON)) == BST_CHECKED;

            PhSetIntegerSetting(SETTING_NAME_TOOLSTATUS_CONFIG, ToolStatusConfig.Flags);

            {
                ULONG bandStyle;

                if (RebarGetBandIndexStyle(0, &bandStyle))
                {
                    ClearFlag(bandStyle, RBBS_BREAK);
                    RebarSetBandIndexStyle(0, bandStyle);
                }
            }

            ToolbarDestroyControls();
            ToolbarCreateControls();
            ReBarSaveLayoutSettings();

            graphTypeHandle = GetDlgItem(WindowHandle, IDC_CURRENT);
            selectedIndex = ComboBox_GetCurSel(graphTypeHandle);

            if (selectedIndex != CB_ERR)
            {
                LRESULT itemData = ComboBox_GetItemData(graphTypeHandle, selectedIndex);

                if (itemData != CB_ERR)
                    graphType = PtrToUlong((PVOID)itemData);
            }

            PhSetIntegerSetting(SETTING_NAME_TASKBARDISPLAYSTYLE, graphType);
            TaskbarListIconType = graphType;
            TaskbarIsDirty = TRUE;

            TaskbarInitialize();

            SendMessage(MainWindowHandle, WM_DPICHANGED, 0, 0);
        }
        break;
    case WM_CTLCOLORBTN:
        return HANDLE_WM_CTLCOLORBTN(WindowHandle, wParam, lParam, PhWindowThemeControlColor);
    case WM_CTLCOLORDLG:
        return HANDLE_WM_CTLCOLORDLG(WindowHandle, wParam, lParam, PhWindowThemeControlColor);
    case WM_CTLCOLORSTATIC:
        return HANDLE_WM_CTLCOLORSTATIC(WindowHandle, wParam, lParam, PhWindowThemeControlColor);
    }

    return FALSE;
}
