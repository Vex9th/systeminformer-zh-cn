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

typedef enum _ET_PIPE_TREE_COLUMN
{
    ET_PIPE_COLUMN_END,
    ET_PIPE_COLUMN_NAME,
    ET_PIPE_COLUMN_PROCESS,
    ET_PIPE_COLUMN_HANDLE,
    ET_PIPE_COLUMN_GRANTEDACCESS,
    ET_PIPE_COLUMN_TYPE,
    ET_PIPE_COLUMN_CONFIGURATION,
    ET_PIPE_COLUMN_MAXIMUMINSTANCES,
    ET_PIPE_COLUMN_CURRENTINSTANCES,
    ET_PIPE_COLUMN_READDATAAVAILABLE,
    ET_PIPE_COLUMN_OUTBOUNDQUOTA,
    ET_PIPE_COLUMN_STATE,
    ET_PIPE_COLUMN_REMOTECLIENTS,
    ET_PIPE_COLUMN_READMODE,
    ET_PIPE_COLUMN_COMPLETIONMODE,
    ET_PIPE_COLUMN_MAXIMUM
} ET_PIPE_TREE_COLUMN;

typedef struct _ET_PIPE_NODE
{
    PH_TREENEW_NODE Node;

    ULONG Index;
    PPH_STRING Columns[ET_PIPE_COLUMN_MAXIMUM];

    PH_STRINGREF TextCache[ET_PIPE_COLUMN_MAXIMUM];
} ET_PIPE_NODE, *PET_PIPE_NODE;

typedef struct _PIPE_ENUM_DIALOG_CONTEXT
{
    HWND WindowHandle;
    HWND ParentWindowHandle;
    HWND TreeNewHandle;
    HWND SearchBoxHandle;
    ULONG_PTR SearchMatchHandle;
    PPH_LIST NodeList;
    PH_TN_FILTER_SUPPORT FilterSupport;
    PH_LAYOUT_MANAGER LayoutManager;
    ULONG TreeNewSortColumn;
    PH_SORT_ORDER TreeNewSortOrder;
    BOOLEAN UseKph;
} PIPE_ENUM_DIALOG_CONTEXT, *PPIPE_ENUM_DIALOG_CONTEXT;

static PET_PIPE_NODE EtCreatePipeNode(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    PET_PIPE_NODE node;

    node = PhAllocateZero(sizeof(ET_PIPE_NODE));
    PhInitializeTreeNewNode(&node->Node);

    memset(node->TextCache, 0, sizeof(node->TextCache));
    node->Node.TextCache = node->TextCache;
    node->Node.TextCacheSize = ET_PIPE_COLUMN_MAXIMUM;

    node->Index = Context->NodeList->Count;
    PhAddItemList(Context->NodeList, node);

    return node;
}

static VOID EtSetPipeNodeColumn(
    _In_ PET_PIPE_NODE Node,
    _In_ ULONG Index,
    _In_opt_ PCWSTR Text
    )
{
    if (Index >= ET_PIPE_COLUMN_MAXIMUM)
        return;

    PhMoveReference(&Node->Columns[Index], Text ? PhCreateString(Text) : NULL);
}

static VOID EtClearPipeNodes(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    for (ULONG i = 0; i < Context->NodeList->Count; i++)
    {
        PET_PIPE_NODE node = Context->NodeList->Items[i];

        for (ULONG j = 0; j < ET_PIPE_COLUMN_MAXIMUM; j++)
            PhClearReference(&node->Columns[j]);

        PhFree(node);
    }

    PhClearList(Context->NodeList);
}

_Function_class_(PH_TN_FILTER_FUNCTION)
static BOOLEAN NTAPI EtPipeTreeFilterCallback(
    _In_ PPH_TREENEW_NODE Node,
    _In_opt_ PVOID Context
    )
{
    PPIPE_ENUM_DIALOG_CONTEXT context = Context;
    PET_PIPE_NODE node = (PET_PIPE_NODE)Node;

    assert(Context);

    if (!context->SearchMatchHandle)
        return TRUE;

    for (ULONG i = 0; i < ET_PIPE_COLUMN_MAXIMUM; i++)
    {
        if (node->Columns[i] && PhSearchControlMatch(context->SearchMatchHandle, &node->Columns[i]->sr))
            return TRUE;
    }

    return FALSE;
}

_Function_class_(PH_SEARCHCONTROL_CALLBACK)
static VOID NTAPI EtPipeSearchControlCallback(
    _In_ ULONG_PTR MatchHandle,
    _In_opt_ PVOID Context
    )
{
    PPIPE_ENUM_DIALOG_CONTEXT context = Context;

    if (!context)
        return;

    context->SearchMatchHandle = MatchHandle;

    PhApplyTreeNewFilters(&context->FilterSupport);
}

static int __cdecl EtPipeNodeCompareFunction(
    _In_ void* _context,
    _In_ const void* _elem1,
    _In_ const void* _elem2
    )
{
    PET_PIPE_NODE node1 = *(PET_PIPE_NODE*)_elem1;
    PET_PIPE_NODE node2 = *(PET_PIPE_NODE*)_elem2;
    PPIPE_ENUM_DIALOG_CONTEXT context = _context;
    ULONG column = context->TreeNewSortColumn;
    int sortResult;

    if (column >= ET_PIPE_COLUMN_MAXIMUM)
        column = ET_PIPE_COLUMN_NAME;

    sortResult = PhCompareStringWithNull(node1->Columns[column], node2->Columns[column], TRUE);

    return PhModifySort(sortResult, context->TreeNewSortOrder);
}

static int __cdecl EtPipeNodeCompareIndexFunction(
    _In_ void* _context,
    _In_ const void* _elem1,
    _In_ const void* _elem2
    )
{
    PET_PIPE_NODE node1 = *(PET_PIPE_NODE*)_elem1;
    PET_PIPE_NODE node2 = *(PET_PIPE_NODE*)_elem2;

    return uintcmp(node1->Index, node2->Index);
}

_Function_class_(PH_TREENEW_CALLBACK)
static BOOLEAN NTAPI EtPipeTreeNewCallback(
    _In_ HWND WindowHandle,
    _In_ PH_TREENEW_MESSAGE Message,
    _In_ PVOID Parameter1,
    _In_ PVOID Parameter2,
    _In_ PVOID Context
    )
{
    PPIPE_ENUM_DIALOG_CONTEXT context = Context;
    PET_PIPE_NODE node;

    switch (Message)
    {
    case TreeNewGetChildren:
        {
            PPH_TREENEW_GET_CHILDREN getChildren = Parameter1;

            if (!getChildren->Node)
            {
                // The node list is sorted in place, so the enumeration order has to be restored
                // from the node index when the sort is reset.
                qsort_s(
                    context->NodeList->Items,
                    context->NodeList->Count,
                    sizeof(PVOID),
                    context->TreeNewSortOrder != NoSortOrder ? EtPipeNodeCompareFunction : EtPipeNodeCompareIndexFunction,
                    context
                    );

                getChildren->Children = (PPH_TREENEW_NODE*)context->NodeList->Items;
                getChildren->NumberOfChildren = context->NodeList->Count;
            }
        }
        return TRUE;
    case TreeNewIsLeaf:
        {
            PPH_TREENEW_IS_LEAF isLeaf = Parameter1;

            isLeaf->IsLeaf = TRUE;
        }
        return TRUE;
    case TreeNewGetCellText:
        {
            PPH_TREENEW_GET_CELL_TEXT getCellText = Parameter1;

            node = (PET_PIPE_NODE)getCellText->Node;

            if (getCellText->Id < ET_PIPE_COLUMN_MAXIMUM)
                getCellText->Text = PhGetStringRef(node->Columns[getCellText->Id]);
        }
        return TRUE;
    case TreeNewSortChanged:
        {
            PPH_TREENEW_SORT_CHANGED_EVENT sorting = Parameter1;

            context->TreeNewSortColumn = sorting->SortColumn;
            context->TreeNewSortOrder = sorting->SortOrder;

            TreeNew_NodesStructured(WindowHandle);
        }
        return TRUE;
    case TreeNewKeyDown:
        {
            PPH_TREENEW_KEY_EVENT keyEvent = Parameter1;

            switch (keyEvent->VirtualKey)
            {
            case 'C':
                {
                    if (GetKeyState(VK_CONTROL) < 0)
                    {
                        PPH_STRING text;

                        text = PhGetTreeNewText(WindowHandle, 0);
                        PhSetClipboardString(WindowHandle, &text->sr);
                        PhDereferenceObject(text);
                    }
                }
                break;
            case 'A':
                {
                    if (GetKeyState(VK_CONTROL) < 0)
                        TreeNew_SelectRange(WindowHandle, 0, -1);
                }
                break;
            }
        }
        return TRUE;
    case TreeNewContextMenu:
        {
            PPH_TREENEW_CONTEXT_MENU contextMenu = Parameter1;
            PPH_EMENU menu;
            PPH_EMENU_ITEM selectedItem;

            menu = PhCreateEMenu();
            PhInsertEMenuItem(menu, PhCreateEMenuItem(0, USHRT_MAX, EtGetUiString(IDS_ET_MENU_COPY, L"&Copy"), NULL, NULL), ULONG_MAX);
            PhInsertCopyCellEMenuItem(menu, USHRT_MAX, WindowHandle, contextMenu->Column);

            selectedItem = PhShowEMenu(
                menu,
                WindowHandle,
                PH_EMENU_SHOW_LEFTRIGHT,
                PH_ALIGN_LEFT | PH_ALIGN_TOP,
                contextMenu->Location.x,
                contextMenu->Location.y
                );

            if (selectedItem && selectedItem->Id != ULONG_MAX)
            {
                if (!PhHandleCopyCellEMenuItem(selectedItem))
                {
                    if (selectedItem->Id == USHRT_MAX)
                    {
                        PPH_STRING text;

                        text = PhGetTreeNewText(WindowHandle, 0);
                        PhSetClipboardString(WindowHandle, &text->sr);
                        PhDereferenceObject(text);
                    }
                }
            }

            PhDestroyEMenu(menu);
        }
        return TRUE;
    case TreeNewHeaderRightClick:
        {
            PH_TN_COLUMN_MENU_DATA data;

            data.TreeNewHandle = WindowHandle;
            data.MouseEvent = Parameter1;
            data.DefaultSortColumn = ET_PIPE_COLUMN_NAME;
            data.DefaultSortOrder = NoSortOrder;
            PhInitializeTreeNewColumnMenuEx(&data, PH_TN_COLUMN_MENU_SHOW_RESET_SORT);

            data.Selection = PhShowEMenu(
                data.Menu,
                WindowHandle,
                PH_EMENU_SHOW_LEFTRIGHT,
                PH_ALIGN_LEFT | PH_ALIGN_TOP,
                data.MouseEvent->ScreenLocation.x,
                data.MouseEvent->ScreenLocation.y
                );

            PhHandleTreeNewColumnMenu(&data);
            PhDeleteTreeNewColumnMenu(&data);
        }
        return TRUE;
    }

    return FALSE;
}

static VOID EtInitializePipeTree(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    ULONG index = 0;

    PhSetControlTheme(Context->TreeNewHandle, L"explorer");

    TreeNew_SetCallback(Context->TreeNewHandle, EtPipeTreeNewCallback, Context);
    TreeNew_SetExtendedFlags(Context->TreeNewHandle, TN_FLAG_ITEM_DRAG_SELECT, TN_FLAG_ITEM_DRAG_SELECT);
    TreeNew_SetTriState(Context->TreeNewHandle, TRUE);

    TreeNew_SetRedraw(Context->TreeNewHandle, FALSE);

    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_END, Context->UseKph, EtGetUiString(IDS_ET_PIPE_COLUMN_END, L"End"), 50, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_NAME, TRUE, EtGetUiString(IDS_ET_WCT_COLUMN_NAME, L"Name"), 200, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_PROCESS, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_PROCESS, L"Process"), 200, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_HANDLE, Context->UseKph, EtGetUiString(IDS_ET_PIPE_COLUMN_HANDLE, L"Handle"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_GRANTEDACCESS, Context->UseKph, EtGetUiString(IDS_ET_PIPE_COLUMN_GRANTED_ACCESS, L"Granted access"), 140, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_TYPE, TRUE, EtGetUiString(IDS_ET_TYPE, L"Type"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_CONFIGURATION, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_CONFIGURATION, L"Configuration"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_MAXIMUMINSTANCES, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_MAX_INSTANCES, L"Max instances"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_CURRENTINSTANCES, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_CURRENT_INSTANCES, L"Current instances"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_READDATAAVAILABLE, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_READ_DATA_AVAILABLE, L"Read data available"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_OUTBOUNDQUOTA, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_OUTBOUND_QUOTA, L"Outbound quota"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_STATE, TRUE, EtGetUiString(IDS_ET_STATE, L"State"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_REMOTECLIENTS, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_REMOTE_CLIENTS, L"Remote clients"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_READMODE, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_READ_MODE, L"Read mode"), 80, PH_ALIGN_LEFT, index++, 0);
    PhAddTreeNewColumn(Context->TreeNewHandle, ET_PIPE_COLUMN_COMPLETIONMODE, TRUE, EtGetUiString(IDS_ET_PIPE_COLUMN_COMPLETION_MODE, L"Completion mode"), 80, PH_ALIGN_LEFT, index++, 0);

    TreeNew_SetRedraw(Context->TreeNewHandle, TRUE);

    PhInitializeTreeNewFilterSupport(&Context->FilterSupport, Context->TreeNewHandle, Context->NodeList);
    PhAddTreeNewFilter(&Context->FilterSupport, EtPipeTreeFilterCallback, Context);
}

static VOID EtLoadSettingsPipeTree(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    PPH_STRING settings;
    PH_INTEGER_PAIR sortSettings;

    settings = PhGetStringSetting(SETTING_NAME_PIPE_ENUM_TREE_LIST_COLUMNS);
    PhCmLoadSettings(Context->TreeNewHandle, &settings->sr);
    PhDereferenceObject(settings);

    sortSettings = PhGetIntegerPairSetting(SETTING_NAME_PIPE_ENUM_TREE_LIST_SORT);
    TreeNew_SetSort(Context->TreeNewHandle, (ULONG)sortSettings.X, (PH_SORT_ORDER)sortSettings.Y);
}

static VOID EtSaveSettingsPipeTree(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    PPH_STRING settings;
    PH_INTEGER_PAIR sortSettings;
    ULONG sortColumn;
    PH_SORT_ORDER sortOrder;

    settings = PhCmSaveSettings(Context->TreeNewHandle);
    PhSetStringSetting2(SETTING_NAME_PIPE_ENUM_TREE_LIST_COLUMNS, &settings->sr);
    PhDereferenceObject(settings);

    TreeNew_GetSort(Context->TreeNewHandle, &sortColumn, &sortOrder);
    sortSettings.X = sortColumn;
    sortSettings.Y = sortOrder;
    PhSetIntegerPairSetting(SETTING_NAME_PIPE_ENUM_TREE_LIST_SORT, sortSettings);
}

static VOID EtRefreshPipeTree(
    _In_ PPIPE_ENUM_DIALOG_CONTEXT Context
    )
{
    PhApplyTreeNewFilters(&Context->FilterSupport);

    TreeNew_NodesStructured(Context->TreeNewHandle);
    TreeNew_SetRedraw(Context->TreeNewHandle, TRUE);
}

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

    TreeNew_SetRedraw(Context->TreeNewHandle, FALSE);
    EtClearPipeNodes(Context);

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
    {
        EtRefreshPipeTree(Context);
        return;
    }

    pipeList = PhCreateList(1);
    PhEnumDirectoryFile(pipeDirectoryHandle, NULL, EtNamedPipeDirectoryCallback, pipeList);

    for (ULONG i = 0; i < pipeList->Count; i++)
    {
        PPH_STRING pipeName = pipeList->Items[i];
        HANDLE pipeHandle;
        PET_PIPE_NODE node;
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

        node = EtCreatePipeNode(Context);
        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_NAME, pipeName->Buffer);

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

                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_PROCESS, PH_AUTO_T(PH_STRING, PhStdGetClientIdName(&clientId))->Buffer);
            }

            if (NT_SUCCESS(NtQueryInformationFile(pipeHandle, &isb, &pipeLocalInfo, sizeof(pipeLocalInfo), FilePipeLocalInformation)))
            {
                // Will always be client, since we opened the pipe by name. NtCreateNamedPipeFile must be used to create/open the server end.
                assert(pipeLocalInfo.NamedPipeEnd == FILE_PIPE_CLIENT_END);

                switch (pipeLocalInfo.NamedPipeType & ~FILE_PIPE_REJECT_REMOTE_CLIENTS)
                {
                case FILE_PIPE_BYTE_STREAM_TYPE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_TYPE, EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                    break;
                case FILE_PIPE_MESSAGE_TYPE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_TYPE, EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                    break;
                }

                switch (pipeLocalInfo.NamedPipeConfiguration)
                {
                case FILE_PIPE_INBOUND:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CONFIGURATION, EtGetUiString(IDS_ET_PIPE_INBOUND, L"Inbound"));
                    break;
                case FILE_PIPE_OUTBOUND:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CONFIGURATION, EtGetUiString(IDS_ET_PIPE_OUTBOUND, L"Outbound"));
                    break;
                case FILE_PIPE_FULL_DUPLEX:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CONFIGURATION, EtGetUiString(IDS_ET_PIPE_DUPLEX, L"Duplex"));
                    break;
                }

                if (pipeLocalInfo.MaximumInstances == FILE_PIPE_UNLIMITED_INSTANCES)
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_MAXIMUMINSTANCES, EtGetUiString(IDS_ET_PIPE_UNLIMITED, L"Unlimited"));
                else
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_MAXIMUMINSTANCES, PhaFormatUInt64(pipeLocalInfo.MaximumInstances, FALSE)->Buffer);
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CURRENTINSTANCES, PhaFormatUInt64(pipeLocalInfo.CurrentInstances, FALSE)->Buffer);
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_READDATAAVAILABLE, PhaFormatSize(pipeLocalInfo.ReadDataAvailable, FALSE)->Buffer);
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_OUTBOUNDQUOTA, PhaFormatSize(pipeLocalInfo.OutboundQuota, FALSE)->Buffer);

                switch (pipeLocalInfo.NamedPipeState)
                {
                case FILE_PIPE_DISCONNECTED_STATE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_SESSION_STATE_DISCONNECTED, L"Disconnected"));
                    break;
                case FILE_PIPE_LISTENING_STATE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_PIPE_LISTENING, L"Listening"));
                    break;
                case FILE_PIPE_CONNECTED_STATE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_SESSION_STATE_CONNECTED, L"Connected"));
                    break;
                case FILE_PIPE_CLOSING_STATE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_PIPE_CLOSING, L"Closing"));
                    break;
                }

                if (pipeLocalInfo.NamedPipeType & FILE_PIPE_REJECT_REMOTE_CLIENTS)
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_REMOTECLIENTS, EtGetUiString(IDS_ET_PIPE_REJECT, L"Reject"));
                else
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_REMOTECLIENTS, EtGetUiString(IDS_ET_PIPE_ACCEPT, L"Accept"));
            }

            if (NT_SUCCESS(NtQueryInformationFile(pipeHandle, &isb, &pipeInfo, sizeof(pipeInfo), FilePipeInformation)))
            {
                switch (pipeInfo.ReadMode)
                {
                case FILE_PIPE_BYTE_STREAM_MODE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_READMODE, EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                    break;
                case FILE_PIPE_MESSAGE_MODE:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_READMODE, EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                    break;
                }

                switch (pipeInfo.CompletionMode)
                {
                case FILE_PIPE_QUEUE_OPERATION:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_COMPLETIONMODE, EtGetUiString(IDS_ET_PIPE_QUEUE, L"Queue"));
                    break;
                case FILE_PIPE_COMPLETE_OPERATION:
                    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_COMPLETIONMODE, EtGetUiString(IDS_ET_PIPE_COMPLETE, L"Complete"));
                    break;
                }
            }

            NtClose(pipeHandle);
        }

        PhDereferenceObject(pipeName);
    }

    PhDereferenceObject(pipeList);
    NtClose(pipeDirectoryHandle);

    EtRefreshPipeTree(Context);
}

VOID EtAddNamedPipeHandleNode(
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
    PET_PIPE_NODE node;
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

    node = EtCreatePipeNode(Context);

    if (pipeLocalInfo.NamedPipeEnd == FILE_PIPE_CLIENT_END)
        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_END, EtGetUiString(IDS_ET_PIPE_CLIENT, L"Client"));
    else if (pipeLocalInfo.NamedPipeEnd == FILE_PIPE_SERVER_END)
        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_END, EtGetUiString(IDS_ET_PIPE_SERVER, L"Server"));
    else
        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_END, L"");

    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_NAME, PhGetString(PipeName));

    clientId.UniqueProcess = ProcessId;
    clientId.UniqueThread = 0;
    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_PROCESS, PH_AUTO_T(PH_STRING, PhStdGetClientIdName(&clientId))->Buffer);

    PhPrintPointer(handle, HandleInfo->Handle);
    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_HANDLE, handle);

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

    EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_GRANTEDACCESS, access);

    if (pipeLocalInfo.NamedPipeEnd != ULONG_MAX)
    {
        switch (pipeLocalInfo.NamedPipeType & ~FILE_PIPE_REJECT_REMOTE_CLIENTS)
        {
            case FILE_PIPE_BYTE_STREAM_TYPE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_TYPE, EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                break;
            case FILE_PIPE_MESSAGE_TYPE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_TYPE, EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                break;
        }

        switch (pipeLocalInfo.NamedPipeConfiguration)
        {
            case FILE_PIPE_INBOUND:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CONFIGURATION, EtGetUiString(IDS_ET_PIPE_INBOUND, L"Inbound"));
                break;
            case FILE_PIPE_OUTBOUND:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CONFIGURATION, EtGetUiString(IDS_ET_PIPE_OUTBOUND, L"Outbound"));
                break;
            case FILE_PIPE_FULL_DUPLEX:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CONFIGURATION, EtGetUiString(IDS_ET_PIPE_DUPLEX, L"Duplex"));
                break;
        }

        if (pipeLocalInfo.MaximumInstances == FILE_PIPE_UNLIMITED_INSTANCES)
            EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_MAXIMUMINSTANCES, EtGetUiString(IDS_ET_PIPE_UNLIMITED, L"Unlimited"));
        else
            EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_MAXIMUMINSTANCES, PhaFormatUInt64(pipeLocalInfo.MaximumInstances, FALSE)->Buffer);

        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_CURRENTINSTANCES, PhaFormatUInt64(pipeLocalInfo.CurrentInstances, FALSE)->Buffer);
        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_READDATAAVAILABLE, PhaFormatSize(pipeLocalInfo.ReadDataAvailable, FALSE)->Buffer);
        EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_OUTBOUNDQUOTA, PhaFormatSize(pipeLocalInfo.OutboundQuota, FALSE)->Buffer);

        switch (pipeLocalInfo.NamedPipeState)
        {
            case FILE_PIPE_DISCONNECTED_STATE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_SESSION_STATE_DISCONNECTED, L"Disconnected"));
                break;
            case FILE_PIPE_LISTENING_STATE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_PIPE_LISTENING, L"Listening"));
                break;
            case FILE_PIPE_CONNECTED_STATE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_SESSION_STATE_CONNECTED, L"Connected"));
                break;
            case FILE_PIPE_CLOSING_STATE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_STATE, EtGetUiString(IDS_ET_PIPE_CLOSING, L"Closing"));
                break;
        }

        if (pipeLocalInfo.NamedPipeType & FILE_PIPE_REJECT_REMOTE_CLIENTS)
            EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_REMOTECLIENTS, EtGetUiString(IDS_ET_PIPE_REJECT, L"Reject"));
        else
            EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_REMOTECLIENTS, EtGetUiString(IDS_ET_PIPE_ACCEPT, L"Accept"));
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
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_READMODE, EtGetUiString(IDS_ET_PIPE_STREAM, L"Stream"));
                break;
            case FILE_PIPE_MESSAGE_MODE:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_READMODE, EtGetUiString(IDS_ET_PIPE_MESSAGE, L"Message"));
                break;
        }

        switch (pipeInfo.CompletionMode)
        {
            case FILE_PIPE_QUEUE_OPERATION:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_COMPLETIONMODE, EtGetUiString(IDS_ET_PIPE_QUEUE, L"Queue"));
                break;
            case FILE_PIPE_COMPLETE_OPERATION:
                EtSetPipeNodeColumn(node, ET_PIPE_COLUMN_COMPLETIONMODE, EtGetUiString(IDS_ET_PIPE_COMPLETE, L"Complete"));
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

    TreeNew_SetRedraw(Context->TreeNewHandle, FALSE);
    EtClearPipeNodes(Context);

    if (!NT_SUCCESS(PhEnumProcesses(&processes)))
    {
        EtRefreshPipeTree(Context);
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

                    EtAddNamedPipeHandleNode(
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

    EtRefreshPipeTree(Context);
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
            context->TreeNewHandle = GetDlgItem(WindowHandle, IDC_PIPELIST);
            context->SearchBoxHandle = GetDlgItem(WindowHandle, IDC_PIPESEARCH);
            context->NodeList = PhCreateList(100);

            PhSetApplicationWindowIcon(WindowHandle);

            PhCreateSearchControl(
                WindowHandle,
                context->SearchBoxHandle,
                EtGetUiString(IDS_ET_SEARCH_NAMED_PIPES, L"Search Named Pipes (Ctrl+K)"),
                EtPipeSearchControlCallback,
                context
                );

            EtInitializePipeTree(context);
            EtLoadSettingsPipeTree(context);

            PhInitializeLayoutManager(&context->LayoutManager, WindowHandle);
            PhAddLayoutItem(&context->LayoutManager, context->SearchBoxHandle, NULL, PH_ANCHOR_TOP | PH_ANCHOR_LEFT | PH_ANCHOR_RIGHT);
            PhAddLayoutItem(&context->LayoutManager, GetDlgItem(WindowHandle, IDRETRY), NULL, PH_ANCHOR_TOP | PH_ANCHOR_RIGHT);
            PhAddLayoutItem(&context->LayoutManager, context->TreeNewHandle, NULL, PH_ANCHOR_ALL);

            if (PhValidWindowPlacementFromSetting(SETTING_NAME_PIPE_ENUM_WINDOW_POSITION))
                PhLoadWindowPlacementFromSetting(SETTING_NAME_PIPE_ENUM_WINDOW_POSITION, SETTING_NAME_PIPE_ENUM_WINDOW_SIZE, WindowHandle);
            else
                PhCenterWindow(WindowHandle, context->ParentWindowHandle);

            PhInitializeWindowTheme(WindowHandle, !!PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT));

            if (context->UseKph)
                EtEnumerateNamedPipeHandles(context);
            else
                EtEnumerateNamedPipeDirectory(context);
        }
        break;
    case WM_DESTROY:
        {
            PhRemoveWindowContext(WindowHandle, PH_WINDOW_CONTEXT_DEFAULT);

            PhSaveWindowPlacementToSetting(SETTING_NAME_PIPE_ENUM_WINDOW_POSITION, SETTING_NAME_PIPE_ENUM_WINDOW_SIZE, WindowHandle);
            EtSaveSettingsPipeTree(context);

            PhDeleteLayoutManager(&context->LayoutManager);
            PhDeleteTreeNewFilterSupport(&context->FilterSupport);

            EtClearPipeNodes(context);
            PhDereferenceObject(context->NodeList);

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
    case WM_KEYDOWN:
        {
            if (LOWORD(wParam) == 'K')
            {
                if (GetKeyState(VK_CONTROL) < 0)
                {
                    SetFocus(context->SearchBoxHandle);
                    return TRUE;
                }
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
