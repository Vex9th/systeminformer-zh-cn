/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     dmex    2020-2026
 *
 */

#include "exttools.h"
#include <secedit.h>
#include <kphuser.h>
#include <hndlinfo.h>

PCWSTR EtGetUiString(
    _In_ ULONG ResourceId,
    _In_ PCWSTR Fallback
    );

typedef struct _PIPE_ENUM_DIALOG_CONTEXT
{
    HWND WindowHandle;
    HWND ParentWindowHandle;
    HWND ListViewWndHandle;
    PH_LAYOUT_MANAGER LayoutManager;
    BOOLEAN UseKph;
} PIPE_ENUM_DIALOG_CONTEXT, *PPIPE_ENUM_DIALOG_CONTEXT;

_Function_class_(PH_ENUM_DIRECTORY_FILE)
BOOLEAN NTAPI EtNamedPipeDirectoryCallback(
    _In_ HANDLE RootDirectory,
    _In_ PFILE_DIRECTORY_INFORMATION Information,
    _In_ PVOID Context
    )
{
    PhAddItemList(Context, PhCreateStringEx(Information->FileName, Information->FileNameLength));
    return TRUE;
}

VOID EtEnumerateNamedPipeDirectory(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    static CONST PH_STRINGREF objectName = PH_STRINGREF_INIT(DEVICE_NAMED_PIPE);
    NTSTATUS status;
    HANDLE pipeDirectoryHandle;
    IO_STATUS_BLOCK isb;
    PPH_LIST pipeList;
    ULONG count = 0;

    ExtendedListView_SetRedraw(Context->ListViewWndHandle, FALSE);
    ListView_DeleteAllItems(Context->ListViewWndHandle);

    status = PhOpenFile(
        &pipeDirectoryHandle,
        &objectName,
        FILE_LIST_DIRECTORY | SYNCHRONIZE,
        NULL,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT,
        NULL
        );

    if (!NT_SUCCESS(status))
        return;

    pipeList = PhCreateList(1);
    PhEnumDirectoryFile(pipeDirectoryHandle, NULL, EtNamedPipeDirectoryCallback, pipeList);

    for (ULONG i = 0; i < pipeList->Count; i++)
    {
        PPH_STRING pipeName = pipeList->Items[i];
        WCHAR value[PH_PTR_STR_LEN_1];
        HANDLE pipeHandle;
        LONG lvItemIndex;
        UNICODE_STRING fileName;
        OBJECT_ATTRIBUTES objectAttributes;
        IO_STATUS_BLOCK ioStatusBlock;
        SECURITY_QUALITY_OF_SERVICE pipeSecurityQos =
        {
            sizeof(SECURITY_QUALITY_OF_SERVICE),
            SecurityAnonymous,
            SECURITY_STATIC_TRACKING,
            FALSE
        };

        if (!PhStringRefToUnicodeString(&pipeName->sr, &fileName))
            continue;

        InitializeObjectAttributes(
            &objectAttributes,
            &fileName,
            OBJ_CASE_INSENSITIVE,
            pipeDirectoryHandle,
            NULL
            );

        objectAttributes.SecurityQualityOfService = &pipeSecurityQos;

        status = NtOpenFile(
            &pipeHandle,
            FILE_READ_ATTRIBUTES | SYNCHRONIZE,
            &objectAttributes,
            &ioStatusBlock,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            FILE_NON_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT
            );

        PhPrintUInt32(value, ++count);
        lvItemIndex = PhAddListViewItem(Context->ListViewWndHandle, MAXINT, value, NULL);
        PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 1, pipeName->Buffer);

        if (NT_SUCCESS(status))
        {
            HANDLE processID;
            FILE_PIPE_INFORMATION pipeInfo;
            FILE_PIPE_LOCAL_INFORMATION pipeLocalInfo;

            if (NT_SUCCESS(PhGetNamedPipeServerProcessId(pipeHandle, &processID)))
            {
                CLIENT_ID clientId;

                clientId.UniqueProcess = processID;
                clientId.UniqueThread = 0;

                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 2, PH_AUTO_T(PH_STRING, PhStdGetClientIdName(&clientId))->Buffer);
            }

            if (NT_SUCCESS(NtQueryInformationFile(pipeHandle, &isb, &pipeLocalInfo, sizeof(pipeLocalInfo), FilePipeLocalInformation)))
            {
                // Will always be client, since we opened the pipe by name. NtCreateNamedPipeFile must be used to create/open the server end.
                assert(pipeLocalInfo.NamedPipeEnd == FILE_PIPE_CLIENT_END);

                switch (pipeLocalInfo.NamedPipeType & ~FILE_PIPE_REJECT_REMOTE_CLIENTS)
                {
                case FILE_PIPE_BYTE_STREAM_TYPE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 3,
                        EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                    break;
                case FILE_PIPE_MESSAGE_TYPE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 3,
                        EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                    break;
                }

                switch (pipeLocalInfo.NamedPipeConfiguration)
                {
                case FILE_PIPE_INBOUND:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 4,
                        EtGetUiString(IDS_ET_PIPE_INBOUND, L"Inbound"));
                    break;
                case FILE_PIPE_OUTBOUND:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 4,
                        EtGetUiString(IDS_ET_PIPE_OUTBOUND, L"Outbound"));
                    break;
                case FILE_PIPE_FULL_DUPLEX:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 4,
                        EtGetUiString(IDS_ET_PIPE_DUPLEX, L"Duplex"));
                    break;
                }

                if (pipeLocalInfo.MaximumInstances == FILE_PIPE_UNLIMITED_INSTANCES)
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 5,
                        EtGetUiString(IDS_ET_PIPE_UNLIMITED, L"Unlimited"));
                else
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 5, PhaFormatUInt64(pipeLocalInfo.MaximumInstances, FALSE)->Buffer);
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 6, PhaFormatUInt64(pipeLocalInfo.CurrentInstances, FALSE)->Buffer);
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 7, PhaFormatSize(pipeLocalInfo.ReadDataAvailable, FALSE)->Buffer);
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 8, PhaFormatSize(pipeLocalInfo.OutboundQuota, FALSE)->Buffer);

                switch (pipeLocalInfo.NamedPipeState)
                {
                case FILE_PIPE_DISCONNECTED_STATE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 9,
                        EtGetUiString(IDS_ET_SESSION_STATE_DISCONNECTED, L"Disconnected"));
                    break;
                case FILE_PIPE_LISTENING_STATE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 9,
                        EtGetUiString(IDS_ET_PIPE_LISTENING, L"Listening"));
                    break;
                case FILE_PIPE_CONNECTED_STATE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 9,
                        EtGetUiString(IDS_ET_SESSION_STATE_CONNECTED, L"Connected"));
                    break;
                case FILE_PIPE_CLOSING_STATE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 9,
                        EtGetUiString(IDS_ET_PIPE_CLOSING, L"Closing"));
                    break;
                }

                if (pipeLocalInfo.NamedPipeType & FILE_PIPE_REJECT_REMOTE_CLIENTS)
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 10,
                        EtGetUiString(IDS_ET_PIPE_REJECT, L"Reject"));
                else
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 10,
                        EtGetUiString(IDS_ET_PIPE_ACCEPT, L"Accept"));
            }

            if (NT_SUCCESS(NtQueryInformationFile(pipeHandle, &isb, &pipeInfo, sizeof(pipeInfo), FilePipeInformation)))
            {
                switch (pipeInfo.ReadMode)
                {
                case FILE_PIPE_BYTE_STREAM_MODE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 11,
                        EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                    break;
                case FILE_PIPE_MESSAGE_MODE:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 11,
                        EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                    break;
                }

                switch (pipeInfo.CompletionMode)
                {
                case FILE_PIPE_QUEUE_OPERATION:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 12,
                        EtGetUiString(IDS_ET_PIPE_QUEUE, L"Queue"));
                    break;
                case FILE_PIPE_COMPLETE_OPERATION:
                    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 12,
                        EtGetUiString(IDS_ET_PIPE_COMPLETE, L"Complete"));
                    break;
                }
            }

            NtClose(pipeHandle);
        }

        PhDereferenceObject(pipeName);
    }

    PhDereferenceObject(pipeList);
    NtClose(pipeDirectoryHandle);

    ExtendedListView_SetRedraw(Context->ListViewWndHandle, TRUE);
}

VOID EtAddNamedPipeHandleToListView(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context,
    _In_ HANDLE ProcessId,
    _In_ HANDLE ProcessHandle,
    _In_ PKPH_PROCESS_HANDLE HandleInfo,
    _In_ PPH_STRING PipeName
    )
{
    CLIENT_ID clientId;
    FILE_PIPE_INFORMATION pipeInfo;
    FILE_PIPE_LOCAL_INFORMATION pipeLocalInfo;
    LONG lvItemIndex;
    WCHAR handle[PH_PTR_STR_LEN_1];
    PPH_ACCESS_ENTRY accessEntries;
    ULONG numberOfAccessEntries;
    PPH_STRING accessString;
    PH_FORMAT format[4];
    WCHAR access[MAX_PATH];

    if (!NT_SUCCESS(PhCallKphQueryFileInformationWithTimeout(
        ProcessHandle,
        HandleInfo->Handle,
        FilePipeLocalInformation,
        &pipeLocalInfo,
        sizeof(pipeLocalInfo),
        NULL
        )))
    {
        pipeLocalInfo.NamedPipeEnd = ULONG_MAX;
    }

    if (pipeLocalInfo.NamedPipeEnd == FILE_PIPE_CLIENT_END)
        lvItemIndex = PhAddListViewItem(Context->ListViewWndHandle, MAXINT, EtGetUiString(IDS_ET_PIPE_CLIENT, L"Client"), NULL);
    else if (pipeLocalInfo.NamedPipeEnd == FILE_PIPE_SERVER_END)
        lvItemIndex = PhAddListViewItem(Context->ListViewWndHandle, MAXINT, EtGetUiString(IDS_ET_PIPE_SERVER, L"Server"), NULL);
    else
        lvItemIndex = PhAddListViewItem(Context->ListViewWndHandle, MAXINT, L"", NULL);

    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 1, PhGetString(PipeName));

    clientId.UniqueProcess = ProcessId;
    clientId.UniqueThread = 0;
    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 2, PH_AUTO_T(PH_STRING, PhStdGetClientIdName(&clientId))->Buffer);

    PhPrintPointer(handle, HandleInfo->Handle);
    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 3, handle);

    if (PhGetAccessEntries(L"FileObject", &accessEntries, &numberOfAccessEntries))
        accessString = PhGetAccessString(HandleInfo->GrantedAccess, accessEntries, numberOfAccessEntries);
    else
        accessString = NULL;

    if (accessString)
    {
        PhInitFormatSR(&format[0], accessString->sr);
        PhInitFormatS(&format[1], L" (0x");
        PhInitFormatX(&format[2], HandleInfo->GrantedAccess);
        PhInitFormatS(&format[3], L" )");
        if (!PhFormatToBuffer(format, 4, access, sizeof(access), NULL))
            access[0] = UNICODE_NULL;
        PhDereferenceObject(accessString);
    }
    else
    {
        PhInitFormatS(&format[0], L"0x");
        PhInitFormatX(&format[1], HandleInfo->GrantedAccess);
        if (!PhFormatToBuffer(format, 2, access, sizeof(access), NULL))
            access[0] = UNICODE_NULL;
    }

    PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 4, access);

    if (pipeLocalInfo.NamedPipeEnd != ULONG_MAX)
    {
        switch (pipeLocalInfo.NamedPipeType & ~FILE_PIPE_REJECT_REMOTE_CLIENTS)
        {
            case FILE_PIPE_BYTE_STREAM_TYPE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 5,
                    EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                break;
            case FILE_PIPE_MESSAGE_TYPE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 5,
                    EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                break;
        }

        switch (pipeLocalInfo.NamedPipeConfiguration)
        {
            case FILE_PIPE_INBOUND:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 6,
                    EtGetUiString(IDS_ET_PIPE_INBOUND, L"Inbound"));
                break;
            case FILE_PIPE_OUTBOUND:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 6,
                    EtGetUiString(IDS_ET_PIPE_OUTBOUND, L"Outbound"));
                break;
            case FILE_PIPE_FULL_DUPLEX:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 6,
                    EtGetUiString(IDS_ET_PIPE_DUPLEX, L"Duplex"));
                break;
        }

        if (pipeLocalInfo.MaximumInstances == FILE_PIPE_UNLIMITED_INSTANCES)
            PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 7,
                EtGetUiString(IDS_ET_PIPE_UNLIMITED, L"Unlimited"));
        else
            PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 7, PhaFormatUInt64(pipeLocalInfo.MaximumInstances, FALSE)->Buffer);

        PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 8, PhaFormatUInt64(pipeLocalInfo.CurrentInstances, FALSE)->Buffer);
        PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 9, PhaFormatSize(pipeLocalInfo.ReadDataAvailable, FALSE)->Buffer);
        PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 10, PhaFormatSize(pipeLocalInfo.OutboundQuota, FALSE)->Buffer);

        switch (pipeLocalInfo.NamedPipeState)
        {
            case FILE_PIPE_DISCONNECTED_STATE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 11,
                    EtGetUiString(IDS_ET_SESSION_STATE_DISCONNECTED, L"Disconnected"));
                break;
            case FILE_PIPE_LISTENING_STATE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 11,
                    EtGetUiString(IDS_ET_PIPE_LISTENING, L"Listening"));
                break;
            case FILE_PIPE_CONNECTED_STATE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 11,
                    EtGetUiString(IDS_ET_SESSION_STATE_CONNECTED, L"Connected"));
                break;
            case FILE_PIPE_CLOSING_STATE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 11,
                    EtGetUiString(IDS_ET_PIPE_CLOSING, L"Closing"));
                break;
        }

        if (pipeLocalInfo.NamedPipeType & FILE_PIPE_REJECT_REMOTE_CLIENTS)
            PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 12,
                EtGetUiString(IDS_ET_PIPE_REJECT, L"Reject"));
        else
            PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 12,
                EtGetUiString(IDS_ET_PIPE_ACCEPT, L"Accept"));
    }

    if (NT_SUCCESS(PhCallKphQueryFileInformationWithTimeout(
        ProcessHandle,
        HandleInfo->Handle,
        FilePipeInformation,
        &pipeInfo,
        sizeof(pipeInfo),
        NULL
        )))
    {
        switch (pipeInfo.ReadMode)
        {
            case FILE_PIPE_BYTE_STREAM_MODE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 13,
                    EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                break;
            case FILE_PIPE_MESSAGE_MODE:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 13,
                    EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                break;
        }

        switch (pipeInfo.CompletionMode)
        {
            case FILE_PIPE_QUEUE_OPERATION:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 14,
                    EtGetUiString(IDS_ET_PIPE_QUEUE, L"Queue"));
                break;
            case FILE_PIPE_COMPLETE_OPERATION:
                PhSetListViewSubItem(Context->ListViewWndHandle, lvItemIndex, 14,
                    EtGetUiString(IDS_ET_PIPE_COMPLETE, L"Complete"));
                break;
        }
    }
}

VOID EtEnumerateNamedPipeHandles(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    PVOID processes;
    PSYSTEM_PROCESS_INFORMATION process;

    ExtendedListView_SetRedraw(Context->ListViewWndHandle, FALSE);
    ListView_DeleteAllItems(Context->ListViewWndHandle);

    if (!NT_SUCCESS(PhEnumProcesses(&processes)))
    {
        return;
    }

    process = PH_FIRST_PROCESS(processes);
    do
    {
        HANDLE processHandle;
        PKPH_PROCESS_HANDLE_INFORMATION handles;

        if (!NT_SUCCESS(PhOpenProcess(
            &processHandle,
            PROCESS_QUERY_LIMITED_INFORMATION,
            process->UniqueProcessId
            )))
        {
            continue;
        }

        if (NT_SUCCESS(KsiEnumerateProcessHandles(processHandle, &handles)))
        {
            for (ULONG i = 0; i < handles->HandleCount; i++)
            {
                PKPH_PROCESS_HANDLE handle = &handles->Handles[i];
                DEVICE_TYPE deviceType;

                if (!NT_SUCCESS(PhGetDeviceType(processHandle, handle->Handle, &deviceType)))
                    continue;

                if (deviceType == FILE_DEVICE_NAMED_PIPE)
                {
                    PPH_STRING objectName;

                    if (!NT_SUCCESS(PhGetHandleInformation(
                        processHandle,
                        handle->Handle,
                        handle->ObjectTypeIndex,
                        NULL,
                        NULL,
                        NULL,
                        &objectName
                        )))
                    {
                        continue;
                    }

                    EtAddNamedPipeHandleToListView(
                        Context,
                        process->UniqueProcessId,
                        processHandle,
                        handle,
                        objectName
                        );
                }
            }

            PhFree(handles);
        }

        NtClose(processHandle);

    } while (process = PH_NEXT_PROCESS(process));

    ExtendedListView_SetRedraw(Context->ListViewWndHandle, TRUE);
}

INT_PTR CALLBACK EtPipeEnumDlgProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    )
{
    PPIPE_ENUM_DIALOG_CONTEXT context;

    if (WindowMessage == WM_INITDIALOG)
    {
        context = PhAllocateZero(sizeof(PIPE_ENUM_DIALOG_CONTEXT));
        context->ParentWindowHandle = (HWND)lParam;

        PhSetWindowContext(WindowHandle, PH_WINDOW_CONTEXT_DEFAULT, context);
    }
    else
    {
        context = PhGetWindowContext(WindowHandle, PH_WINDOW_CONTEXT_DEFAULT);
    }

    if (!context)
        return FALSE;

    switch (WindowMessage)
    {
    case WM_INITDIALOG:
        {
            context->UseKph = KsiLevel() >= KphLevelMed;
            context->ListViewWndHandle = GetDlgItem(WindowHandle, IDC_PIPELIST);

            PhSetApplicationWindowIcon(WindowHandle);

            PhInitializeLayoutManager(&context->LayoutManager, WindowHandle);
            PhAddLayoutItem(&context->LayoutManager, context->ListViewWndHandle, NULL, PH_ANCHOR_ALL);
            PhAddLayoutItem(&context->LayoutManager, GetDlgItem(WindowHandle, IDRETRY), NULL, PH_ANCHOR_BOTTOM | PH_ANCHOR_LEFT);
            PhAddLayoutItem(&context->LayoutManager, GetDlgItem(WindowHandle, IDOK), NULL, PH_ANCHOR_BOTTOM | PH_ANCHOR_RIGHT);

            if (PhValidWindowPlacementFromSetting(SETTING_NAME_PIPE_ENUM_WINDOW_POSITION))
                PhLoadWindowPlacementFromSetting(SETTING_NAME_PIPE_ENUM_WINDOW_POSITION, SETTING_NAME_PIPE_ENUM_WINDOW_SIZE, WindowHandle);
            else
                PhCenterWindow(WindowHandle, context->ParentWindowHandle);

            PhSetListViewStyle(context->ListViewWndHandle, TRUE, TRUE);
            PhSetControlTheme(context->ListViewWndHandle, L"explorer");

            if (context->UseKph)
            {
                PhAddListViewColumn(context->ListViewWndHandle, 0, 0, 0, LVCFMT_LEFT, 40, EtGetUiString(IDS_ET_PIPE_COLUMN_END, L"End"));
                PhAddListViewColumn(context->ListViewWndHandle, 1, 1, 1, LVCFMT_LEFT, 200, EtGetUiString(IDS_ET_WCT_COLUMN_NAME, L"Name"));
                PhAddListViewColumn(context->ListViewWndHandle, 2, 2, 2, LVCFMT_LEFT, 200, EtGetUiString(IDS_ET_PIPE_COLUMN_PROCESS, L"Process"));
                PhAddListViewColumn(context->ListViewWndHandle, 3, 3, 3, LVCFMT_LEFT, 200, EtGetUiString(IDS_ET_PIPE_COLUMN_HANDLE, L"Handle"));
                PhAddListViewColumn(context->ListViewWndHandle, 4, 4, 4, LVCFMT_LEFT, 50, EtGetUiString(IDS_ET_PIPE_COLUMN_GRANTED_ACCESS, L"Granted access"));
                PhAddListViewColumn(context->ListViewWndHandle, 5, 5, 5, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_TYPE, L"Type"));
                PhAddListViewColumn(context->ListViewWndHandle, 6, 6, 6, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_CONFIGURATION, L"Configuration"));
                PhAddListViewColumn(context->ListViewWndHandle, 7, 7, 7, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_MAX_INSTANCES, L"Max instances"));
                PhAddListViewColumn(context->ListViewWndHandle, 8, 8, 8, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_CURRENT_INSTANCES, L"Current instances"));
                PhAddListViewColumn(context->ListViewWndHandle, 9, 9, 9, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_READ_DATA_AVAILABLE, L"Read data available"));
                PhAddListViewColumn(context->ListViewWndHandle, 10, 10, 10, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_OUTBOUND_QUOTA, L"Outbound quota"));
                PhAddListViewColumn(context->ListViewWndHandle, 11, 11, 11, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_STATE, L"State"));
                PhAddListViewColumn(context->ListViewWndHandle, 12, 12, 12, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_REMOTE_CLIENTS, L"Remote clients"));
                PhAddListViewColumn(context->ListViewWndHandle, 13, 13, 13, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_READ_MODE, L"Read mode"));
                PhAddListViewColumn(context->ListViewWndHandle, 14, 14, 14, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_COMPLETION_MODE, L"Completion mode"));
                PhSetExtendedListView(context->ListViewWndHandle);
                PhLoadListViewColumnsFromSetting(SETTING_NAME_PIPE_ENUM_LISTVIEW_COLUMNS_WITH_KSI, context->ListViewWndHandle);

                PhInitializeWindowTheme(WindowHandle, !!PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT));

                EtEnumerateNamedPipeHandles(context);
            }
            else
            {
                PhAddListViewColumn(context->ListViewWndHandle, 0, 0, 0, LVCFMT_LEFT, 40, L"#");
                PhAddListViewColumn(context->ListViewWndHandle, 1, 1, 1, LVCFMT_LEFT, 200, EtGetUiString(IDS_ET_WCT_COLUMN_NAME, L"Name"));
                PhAddListViewColumn(context->ListViewWndHandle, 2, 2, 2, LVCFMT_LEFT, 50, EtGetUiString(IDS_ET_PIPE_SERVER, L"Server"));
                PhAddListViewColumn(context->ListViewWndHandle, 3, 3, 3, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_TYPE, L"Type"));
                PhAddListViewColumn(context->ListViewWndHandle, 4, 4, 4, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_CONFIGURATION, L"Configuration"));
                PhAddListViewColumn(context->ListViewWndHandle, 5, 5, 5, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_MAX_INSTANCES, L"Max instances"));
                PhAddListViewColumn(context->ListViewWndHandle, 6, 6, 6, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_CURRENT_INSTANCES, L"Current instances"));
                PhAddListViewColumn(context->ListViewWndHandle, 7, 7, 7, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_READ_DATA_AVAILABLE, L"Read data available"));
                PhAddListViewColumn(context->ListViewWndHandle, 8, 8, 8, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_OUTBOUND_QUOTA, L"Outbound quota"));
                PhAddListViewColumn(context->ListViewWndHandle, 9, 9, 9, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_STATE, L"State"));
                PhAddListViewColumn(context->ListViewWndHandle, 10, 10, 10, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_REMOTE_CLIENTS, L"Remote clients"));
                PhAddListViewColumn(context->ListViewWndHandle, 11, 11, 11, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_READ_MODE, L"Read mode"));
                PhAddListViewColumn(context->ListViewWndHandle, 12, 12, 12, LVCFMT_LEFT, 80, EtGetUiString(IDS_ET_PIPE_COLUMN_COMPLETION_MODE, L"Completion mode"));
                PhSetExtendedListView(context->ListViewWndHandle);
                PhLoadListViewColumnsFromSetting(SETTING_NAME_PIPE_ENUM_LISTVIEW_COLUMNS, context->ListViewWndHandle);

                PhInitializeWindowTheme(WindowHandle, !!PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT));

                EtEnumerateNamedPipeDirectory(context);
            }
        }
        break;
    case WM_DESTROY:
        {
            PhRemoveWindowContext(WindowHandle, PH_WINDOW_CONTEXT_DEFAULT);

            PhSaveWindowPlacementToSetting(SETTING_NAME_PIPE_ENUM_WINDOW_POSITION, SETTING_NAME_PIPE_ENUM_WINDOW_SIZE, WindowHandle);
            if (context->UseKph)
                PhSaveListViewColumnsToSetting(SETTING_NAME_PIPE_ENUM_LISTVIEW_COLUMNS_WITH_KSI, context->ListViewWndHandle);
            else
                PhSaveListViewColumnsToSetting(SETTING_NAME_PIPE_ENUM_LISTVIEW_COLUMNS, context->ListViewWndHandle);

            PhDeleteLayoutManager(&context->LayoutManager);
            PhFree(context);
        }
        break;
    case WM_SIZE:
        {
            PhLayoutManagerLayout(&context->LayoutManager);
        }
        break;
    case WM_DPICHANGED:
        {
            PhLayoutManagerUpdate(&context->LayoutManager, LOWORD(wParam));
            PhLayoutManagerLayout(&context->LayoutManager);
        }
        break;
    case WM_COMMAND:
        {
            switch (GET_WM_COMMAND_ID(wParam, lParam))
            {
            case IDCANCEL:
            case IDOK:
                EndDialog(WindowHandle, IDOK);
                break;
            case IDRETRY:
                {
                    if (context->UseKph)
                        EtEnumerateNamedPipeHandles(context);
                    else
                        EtEnumerateNamedPipeDirectory(context);
                }
                break;
            }
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

VOID EtShowPipeEnumDialog(
    _In_ HWND ParentWindowHandle
    )
{
    PhDialogBox(
        PluginInstance->DllBase,
        MAKEINTRESOURCE(IDD_PIPEDIALOG),
        NULL,
        EtPipeEnumDlgProc,
        ParentWindowHandle
        );
}
