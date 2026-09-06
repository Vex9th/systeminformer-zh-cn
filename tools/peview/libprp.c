/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2010
 *
 */

#include <peview.h>
#include <mapimg.h>

INT_PTR CALLBACK PvpLibExportsDlgProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    );

PH_MAPPED_ARCHIVE PvMappedArchive;

VOID PvLibProperties(
    VOID
    )
{
    NTSTATUS status;
    PPV_PROPCONTEXT propContext;

    status = PhLoadMappedArchive(PvFileName->Buffer, NULL, &PvMappedArchive);

    if (!NT_SUCCESS(status))
    {
        PhShowStatus(NULL, PvpLoadUiString(IDS_PV_UNABLE_LOAD_ARCHIVE), status, 0);
        return;
    }

    if (propContext = PvCreatePropContext(PvFileName))
    {
        PPV_PROPPAGECONTEXT newPage;

        // Lib page
        newPage = PvCreatePropPageContext(
            MAKEINTRESOURCE(IDD_LIBEXPORTS),
            PvpLibExportsDlgProc,
            NULL
            );
        PvAddPropPage(propContext, newPage);

        PhModalPropertySheet(&propContext->PropSheetHeader);

        PhDereferenceObject(propContext);
    }

    PhUnloadMappedArchive(&PvMappedArchive);
}

INT_PTR CALLBACK PvpLibExportsDlgProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    )
{
    LPPROPSHEETPAGE propSheetPage;
    PPV_PROPPAGECONTEXT propPageContext;

    if (!PvPropPageDlgProcHeader(hwndDlg, uMsg, lParam, &propSheetPage, &propPageContext))
        return FALSE;

    switch (uMsg)
    {
    case WM_INITDIALOG:
        {
            ULONG fallbackColumns[] = { 0, 1, 2, 3 };
            HWND lvHandle;
            PH_MAPPED_ARCHIVE_MEMBER member;
            PH_MAPPED_ARCHIVE_IMPORT_ENTRY importEntry;

            lvHandle = GetDlgItem(hwndDlg, IDC_LIST);
            PhSetListViewStyle(lvHandle, TRUE, TRUE);
            PhSetControlTheme(lvHandle, L"explorer");
            PhAddListViewColumn(lvHandle, 0, 0, 0, LVCFMT_LEFT, 60, PvpLoadUiString(IDS_PV_COLUMN_DLL));
            PhAddListViewColumn(lvHandle, 1, 1, 1, LVCFMT_LEFT, 200, PvpLoadUiString(IDS_PV_COLUMN_NAME));
            PhAddListViewColumn(lvHandle, 2, 2, 2, LVCFMT_LEFT, 40, PvpLoadUiString(IDS_PV_COLUMN_ORDINAL_HINT));
            PhAddListViewColumn(lvHandle, 3, 3, 3, LVCFMT_LEFT, 40, PvpLoadUiString(IDS_PV_COLUMN_TYPE));
            PhAddListViewColumn(lvHandle, 4, 4, 4, LVCFMT_LEFT, 60, PvpLoadUiString(IDS_PV_COLUMN_NAME_TYPE));
            PhSetExtendedListView(lvHandle);
            ExtendedListView_AddFallbackColumns(lvHandle, 4, fallbackColumns);
            PhLoadListViewColumnsFromSetting(L"LibListViewColumns", lvHandle);

            member = *PvMappedArchive.LastStandardMember;

            while (NT_SUCCESS(PhGetNextMappedArchiveMember(&member, &member)))
            {
                if (NT_SUCCESS(PhGetMappedArchiveImportEntry(&member, &importEntry)))
                {
                    INT lvItemIndex;
                    PPH_STRING name;
                    WCHAR number[PH_INT32_STR_LEN_1];
                    PCWSTR type;

                    name = PhZeroExtendToUtf16(importEntry.DllName);
                    lvItemIndex = PhAddListViewItem(lvHandle, MAXINT, name->Buffer, NULL);
                    PhDereferenceObject(name);

                    name = PhZeroExtendToUtf16(importEntry.Name);
                    PhSetListViewSubItem(lvHandle, lvItemIndex, 1, name->Buffer);
                    PhDereferenceObject(name);

                    // Ordinal is unioned with NameHint, so this works both ways.
                    PhPrintUInt32(number, importEntry.Ordinal);
                    PhSetListViewSubItem(lvHandle, lvItemIndex, 2, number);

                    switch (importEntry.Type)
                    {
                    case IMPORT_OBJECT_CODE:
                        type = PvpLoadUiString(IDS_PV_IMPORT_OBJECT_CODE);
                        break;
                    case IMPORT_OBJECT_DATA:
                        type = PvpLoadUiString(IDS_PV_COLUMN_DATA);
                        break;
                    case IMPORT_OBJECT_CONST:
                        type = PvpLoadUiString(IDS_PV_IMPORT_OBJECT_CONST);
                        break;
                    default:
                        type = PvpLoadUiString(IDS_PV_MAPPING_UNKNOWN);
                        break;
                    }

                    PhSetListViewSubItem(lvHandle, lvItemIndex, 3, type);

                    switch (importEntry.NameType)
                    {
                    case IMPORT_OBJECT_ORDINAL:
                        type = PvpLoadUiString(IDS_PV_COLUMN_ORDINAL);
                        break;
                    case IMPORT_OBJECT_NAME:
                        type = PvpLoadUiString(IDS_PV_COLUMN_NAME);
                        break;
                    case IMPORT_OBJECT_NAME_NO_PREFIX:
                        type = PvpLoadUiString(IDS_PV_IMPORT_NAME_NO_PREFIX);
                        break;
                    case IMPORT_OBJECT_NAME_UNDECORATE:
                        type = PvpLoadUiString(IDS_PV_IMPORT_NAME_UNDECORATE);
                        break;
                    default:
                        type = PvpLoadUiString(IDS_PV_MAPPING_UNKNOWN);
                        break;
                    }

                    PhSetListViewSubItem(lvHandle, lvItemIndex, 4, type);
                }
            }

            ExtendedListView_SortItems(lvHandle);

            PhInitializeWindowTheme(hwndDlg, PhEnableThemeSupport);
        }
        break;
    case WM_DESTROY:
        {
            PhSaveListViewColumnsToSetting(L"LibListViewColumns", GetDlgItem(hwndDlg, IDC_LIST));
        }
        break;
    case WM_SHOWWINDOW:
        {
            if (!propPageContext->LayoutInitialized)
            {
                PPH_LAYOUT_ITEM dialogItem;

                dialogItem = PvAddPropPageLayoutItem(hwndDlg, hwndDlg, PH_PROP_PAGE_TAB_CONTROL_PARENT, PH_ANCHOR_ALL);
                PvAddPropPageLayoutItem(hwndDlg, GetDlgItem(hwndDlg, IDC_LIST), dialogItem, PH_ANCHOR_ALL);
                PvDoPropPageLayout(hwndDlg);

                propPageContext->LayoutInitialized = TRUE;
            }
        }
        break;
    case WM_NOTIFY:
        {
            PvHandleListViewNotifyForCopy(lParam, GetDlgItem(hwndDlg, IDC_LIST));
        }
        break;
    case WM_CONTEXTMENU:
        {
            PvHandleListViewCommandCopy(hwndDlg, lParam, wParam, GetDlgItem(hwndDlg, IDC_LIST));
        }
        break;
    }

    return FALSE;
}
