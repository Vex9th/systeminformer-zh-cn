/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2011-2015
 *     dmex    2020-2023
 *
 */

#include "extsrv.h"
#include <hndlinfo.h>

typedef struct _ES_TRIGGER_DATA
{
    ULONG Type;
    union
    {
        PPH_STRING String;
        struct
        {
            PVOID Binary;
            ULONG BinaryLength;
        };
        UCHAR Byte;
        ULONG64 UInt64;
    };
} ES_TRIGGER_DATA, *PES_TRIGGER_DATA;

typedef struct _TYPE_ENTRY
{
    ULONG ResourceId;
    ULONG Type;
} TYPE_ENTRY, PTYPE_ENTRY;

typedef struct _SUBTYPE_ENTRY
{
    ULONG ResourceId;
    ULONG Type;
    PCGUID Guid;
} SUBTYPE_ENTRY, PSUBTYPE_ENTRY;

typedef struct _ACTION_ENTRY
{
    ULONG ResourceId;
    ULONG Action;
} ACTION_ENTRY, PACTION_ENTRY;

typedef struct _ETW_PUBLISHER_ENTRY
{
    PPH_STRING PublisherName;
    GUID Guid;
} ETW_PUBLISHER_ENTRY, *PETW_PUBLISHER_ENTRY;

INT_PTR CALLBACK EspServiceTriggerDlgProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    );

INT_PTR CALLBACK ValueDlgProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    );

DEFINE_GUID(NetworkManagerFirstIpAddressArrivalGuid, 0x4f27f2de, 0x14e2, 0x430b, 0xa5, 0x49, 0x7c, 0xd4, 0x8c, 0xbc, 0x82, 0x45);
DEFINE_GUID(NetworkManagerLastIpAddressRemovalGuid, 0xcc4ba62a, 0x162e, 0x4648, 0x84, 0x7a, 0xb6, 0xbd, 0xf9, 0x93, 0xe3, 0x35);
DEFINE_GUID(DomainJoinGuid, 0x1ce20aba, 0x9851, 0x4421, 0x94, 0x30, 0x1d, 0xde, 0xb7, 0x66, 0xe8, 0x09);
DEFINE_GUID(DomainLeaveGuid, 0xddaf516e, 0x58c2, 0x4866, 0x95, 0x74, 0xc3, 0xb6, 0x15, 0xd4, 0x2e, 0xa1);
DEFINE_GUID(FirewallPortOpenGuid, 0xb7569e07, 0x8421, 0x4ee0, 0xad, 0x10, 0x86, 0x91, 0x5a, 0xfd, 0xad, 0x09);
DEFINE_GUID(FirewallPortCloseGuid, 0xa144ed38, 0x8e12, 0x4de4, 0x9d, 0x96, 0xe6, 0x47, 0x40, 0xb1, 0xa5, 0x24);
DEFINE_GUID(MachinePolicyPresentGuid, 0x659fcae6, 0x5bdb, 0x4da9, 0xb1, 0xff, 0xca, 0x2a, 0x17, 0x8d, 0x46, 0xe0);
DEFINE_GUID(UserPolicyPresentGuid, 0x54fb46c8, 0xf089, 0x464c, 0xb1, 0xfd, 0x59, 0xd1, 0xb6, 0x2c, 0x3b, 0x50);
DEFINE_GUID(RpcInterfaceEventGuid, 0xbc90d167, 0x9470, 0x4139, 0xa9, 0xba, 0xbe, 0x0b, 0xbb, 0xf5, 0xb7, 0x4d);
DEFINE_GUID(NamedPipeEventGuid, 0x1f81d131, 0x3fac, 0x4537, 0x9e, 0x0c, 0x7e, 0x7b, 0x0c, 0x2f, 0x4b, 0x55);
DEFINE_GUID(SubTypeUnknownGuid, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);

static CONST TYPE_ENTRY TypeEntries[] =
{
    { IDS_ES_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL, SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL },
    { IDS_ES_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY, SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY },
    { IDS_ES_TRIGGER_TYPE_DOMAIN_JOIN, SERVICE_TRIGGER_TYPE_DOMAIN_JOIN },
    { IDS_ES_TRIGGER_TYPE_FIREWALL_PORT_EVENT, SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT },
    { IDS_ES_TRIGGER_TYPE_GROUP_POLICY, SERVICE_TRIGGER_TYPE_GROUP_POLICY },
    { IDS_ES_TRIGGER_TYPE_NETWORK_ENDPOINT, SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT },
    { IDS_ES_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE, SERVICE_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE },
    { IDS_ES_TRIGGER_CUSTOM, SERVICE_TRIGGER_TYPE_CUSTOM }
};

static CONST SUBTYPE_ENTRY SubTypeEntries[] =
{
    { IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS, SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY, NULL },
    { IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS_FIRST_ARRIVAL, SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY, &NetworkManagerFirstIpAddressArrivalGuid },
    { IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS_LAST_REMOVAL, SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY, &NetworkManagerLastIpAddressRemovalGuid },
    { IDS_ES_TRIGGER_SUBTYPE_IP_ADDRESS_UNKNOWN, SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY, &SubTypeUnknownGuid },
    { IDS_ES_TRIGGER_SUBTYPE_DOMAIN, SERVICE_TRIGGER_TYPE_DOMAIN_JOIN, NULL },
    { IDS_ES_TRIGGER_SUBTYPE_DOMAIN_JOIN, SERVICE_TRIGGER_TYPE_DOMAIN_JOIN, &DomainJoinGuid },
    { IDS_ES_TRIGGER_SUBTYPE_DOMAIN_LEAVE, SERVICE_TRIGGER_TYPE_DOMAIN_JOIN, &DomainLeaveGuid },
    { IDS_ES_TRIGGER_SUBTYPE_DOMAIN_UNKNOWN, SERVICE_TRIGGER_TYPE_DOMAIN_JOIN, &SubTypeUnknownGuid },
    { IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT, SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT, NULL },
    { IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT_OPEN, SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT, &FirewallPortOpenGuid },
    { IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT_CLOSE, SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT, &FirewallPortCloseGuid },
    { IDS_ES_TRIGGER_SUBTYPE_FIREWALL_PORT_UNKNOWN, SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT, &SubTypeUnknownGuid },
    { IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_CHANGE, SERVICE_TRIGGER_TYPE_GROUP_POLICY, NULL },
    { IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_MACHINE, SERVICE_TRIGGER_TYPE_GROUP_POLICY, &MachinePolicyPresentGuid },
    { IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_USER, SERVICE_TRIGGER_TYPE_GROUP_POLICY, &UserPolicyPresentGuid },
    { IDS_ES_TRIGGER_SUBTYPE_GROUP_POLICY_UNKNOWN, SERVICE_TRIGGER_TYPE_GROUP_POLICY, &SubTypeUnknownGuid },
    { IDS_ES_TRIGGER_TYPE_NETWORK_ENDPOINT, SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT, NULL },
    { IDS_ES_TRIGGER_SUBTYPE_NETWORK_ENDPOINT_RPC, SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT, &RpcInterfaceEventGuid },
    { IDS_ES_TRIGGER_SUBTYPE_NETWORK_ENDPOINT_NAMED_PIPE, SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT, &NamedPipeEventGuid },
    { IDS_ES_TRIGGER_SUBTYPE_NETWORK_ENDPOINT_UNKNOWN, SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT, &SubTypeUnknownGuid }
};

static CONST ACTION_ENTRY ActionEntries[] =
{
    { IDS_ES_TRIGGER_ACTION_START_SERVICE, SERVICE_TRIGGER_ACTION_SERVICE_START },
    { IDS_ES_TRIGGER_ACTION_STOP_SERVICE, SERVICE_TRIGGER_ACTION_SERVICE_STOP }
};

static CONST SUBTYPE_ENTRY EspCustomSubTypeEntry =
{
    IDS_ES_TRIGGER_CUSTOM,
    0,
    NULL
};

static CONST PH_STRINGREF PublishersKeyName = PH_STRINGREF_INIT(L"Software\\Microsoft\\Windows\\CurrentVersion\\WINEVT\\Publishers\\");

static INT EspAddTriggerComboBoxItem(
    _In_ HWND ComboBoxHandle,
    _In_ PCWSTR Text,
    _In_opt_ PVOID ItemData
    )
{
    INT itemIndex;

    itemIndex = ComboBox_AddString(ComboBoxHandle, Text);

    if (itemIndex >= 0)
    {
        if (ComboBox_SetItemData(ComboBoxHandle, itemIndex, ItemData) != CB_ERR)
            return itemIndex;

        ComboBox_DeleteString(ComboBoxHandle, itemIndex);
    }

    return CB_ERR;
}

static INT EspAddTriggerComboBoxResourceItem(
    _In_ HWND ComboBoxHandle,
    _In_ ULONG ResourceId,
    _In_opt_ PVOID ItemData
    )
{
    PPH_STRING text;
    INT itemIndex;

    text = PhLoadUiString(PluginInstance->DllBase, ResourceId, NULL);
    itemIndex = EspAddTriggerComboBoxItem(ComboBoxHandle, PhGetString(text), ItemData);
    PhDereferenceObject(text);

    return itemIndex;
}

static BOOLEAN EspGetSelectedTriggerComboBoxItemData(
    _In_ HWND ComboBoxHandle,
    _Out_ PVOID *ItemData
    )
{
    INT selectedIndex;
    LRESULT selectedData;

    selectedIndex = ComboBox_GetCurSel(ComboBoxHandle);

    if (selectedIndex == CB_ERR)
        return FALSE;

    selectedData = ComboBox_GetItemData(ComboBoxHandle, selectedIndex);

    if (selectedData == CB_ERR)
        return FALSE;

    *ItemData = (PVOID)selectedData;
    return TRUE;
}

static BOOLEAN EspSelectTriggerComboBoxItemData(
    _In_ HWND ComboBoxHandle,
    _In_opt_ PVOID ItemData
    )
{
    INT numberOfItems;

    numberOfItems = ComboBox_GetCount(ComboBoxHandle);

    for (INT i = 0; i < numberOfItems; i++)
    {
        LRESULT currentItemData;

        currentItemData = ComboBox_GetItemData(ComboBoxHandle, i);

        if (currentItemData != CB_ERR && (PVOID)currentItemData == ItemData)
        {
            ComboBox_SetCurSel(ComboBoxHandle, i);
            return TRUE;
        }
    }

    return FALSE;
}

static CONST TYPE_ENTRY* EspFindTriggerTypeEntry(
    _In_ ULONG Type
    )
{
    for (ULONG i = 0; i < ARRAYSIZE(TypeEntries); i++)
    {
        if (TypeEntries[i].Type == Type)
            return &TypeEntries[i];
    }

    return NULL;
}

static CONST ACTION_ENTRY* EspFindTriggerActionEntry(
    _In_ ULONG Action
    )
{
    for (ULONG i = 0; i < ARRAYSIZE(ActionEntries); i++)
    {
        if (ActionEntries[i].Action == Action)
            return &ActionEntries[i];
    }

    return NULL;
}

PES_TRIGGER_DATA EspCreateTriggerData(
    _In_opt_ PSERVICE_TRIGGER_SPECIFIC_DATA_ITEM DataItem
    )
{
    PES_TRIGGER_DATA data;

    data = PhAllocate(sizeof(ES_TRIGGER_DATA));
    memset(data, 0, sizeof(ES_TRIGGER_DATA));

    if (DataItem)
    {
        data->Type = DataItem->dwDataType;

        if (data->Type == SERVICE_TRIGGER_DATA_TYPE_STRING)
        {
            if (DataItem->pData && DataItem->cbData >= 2)
                data->String = PhCreateStringEx((PWSTR)DataItem->pData, DataItem->cbData - 2); // exclude final null terminator
            else
                data->String = PhReferenceEmptyString();
        }
        else if (data->Type == SERVICE_TRIGGER_DATA_TYPE_BINARY)
        {
            data->BinaryLength = DataItem->cbData;
            data->Binary = PhAllocateCopy(DataItem->pData, DataItem->cbData);
        }
        else if (data->Type == SERVICE_TRIGGER_DATA_TYPE_LEVEL)
        {
            if (DataItem->cbData == sizeof(UCHAR))
                data->Byte = *(PUCHAR)DataItem->pData;
        }
        else if (data->Type == SERVICE_TRIGGER_DATA_TYPE_KEYWORD_ANY || data->Type == SERVICE_TRIGGER_DATA_TYPE_KEYWORD_ALL)
        {
            if (DataItem->cbData == sizeof(ULONG64))
                data->UInt64 = *(PULONG64)DataItem->pData;
        }
    }

    return data;
}

PES_TRIGGER_DATA EspCloneTriggerData(
    _In_ PES_TRIGGER_DATA Data
    )
{
    PES_TRIGGER_DATA newData;

    newData = PhAllocateCopy(Data, sizeof(ES_TRIGGER_DATA));

    if (newData->Type == SERVICE_TRIGGER_DATA_TYPE_STRING)
    {
        if (newData->String)
            newData->String = PhDuplicateString(newData->String);
    }
    else if (newData->Type == SERVICE_TRIGGER_DATA_TYPE_BINARY)
    {
        if (newData->Binary)
            newData->Binary = PhAllocateCopy(newData->Binary, newData->BinaryLength);
    }

    return newData;
}

VOID EspDestroyTriggerData(
    _In_ PES_TRIGGER_DATA Data
    )
{
    if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_STRING)
    {
        if (Data->String)
            PhDereferenceObject(Data->String);
    }
    else if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_BINARY)
    {
        if (Data->Binary)
            PhFree(Data->Binary);
    }

    PhFree(Data);
}

PES_TRIGGER_INFO EspCreateTriggerInfo(
    _In_opt_ PSERVICE_TRIGGER Trigger
    )
{
    PES_TRIGGER_INFO info;

    info = PhAllocate(sizeof(ES_TRIGGER_INFO));
    memset(info, 0, sizeof(ES_TRIGGER_INFO));

    if (Trigger)
    {
        info->Type = Trigger->dwTriggerType;

        if (Trigger->pTriggerSubtype)
        {
            info->SubtypeBuffer = *Trigger->pTriggerSubtype;
            info->Subtype = &info->SubtypeBuffer;
        }

        info->Action = Trigger->dwAction;

        if (
            info->Type == SERVICE_TRIGGER_TYPE_CUSTOM ||
            info->Type == SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL ||
            info->Type == SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT ||
            info->Type == SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT
            )
        {
            ULONG i;

            info->DataList = PhCreateList(Trigger->cDataItems);

            for (i = 0; i < Trigger->cDataItems; i++)
            {
                PhAddItemList(info->DataList, EspCreateTriggerData(&Trigger->pDataItems[i]));
            }
        }
    }

    return info;
}

PES_TRIGGER_INFO EspCloneTriggerInfo(
    _In_ PES_TRIGGER_INFO Info
    )
{
    PES_TRIGGER_INFO newInfo;

    newInfo = PhAllocateCopy(Info, sizeof(ES_TRIGGER_INFO));

    if (newInfo->Subtype == &Info->SubtypeBuffer)
        newInfo->Subtype = &newInfo->SubtypeBuffer;

    if (newInfo->DataList)
    {
        ULONG i;

        newInfo->DataList = PhCreateList(Info->DataList->AllocatedCount);
        newInfo->DataList->Count = Info->DataList->Count;

        for (i = 0; i < Info->DataList->Count; i++)
            newInfo->DataList->Items[i] = EspCloneTriggerData(Info->DataList->Items[i]);
    }

    return newInfo;
}

VOID EspDestroyTriggerInfo(
    _In_ PES_TRIGGER_INFO Info
    )
{
    if (Info->DataList)
    {
        ULONG i;

        for (i = 0; i < Info->DataList->Count; i++)
        {
            EspDestroyTriggerData(Info->DataList->Items[i]);
        }

        PhDereferenceObject(Info->DataList);
    }

    PhFree(Info);
}

VOID EspClearTriggerInfoList(
    _In_ PPH_LIST List
    )
{
    ULONG i;

    for (i = 0; i < List->Count; i++)
    {
        EspDestroyTriggerInfo(List->Items[i]);
    }

    PhClearList(List);
}

PES_TRIGGER_CONTEXT EsCreateServiceTriggerContext(
    _In_ PPH_SERVICE_ITEM ServiceItem,
    _In_ HWND WindowHandle,
    _In_ HWND TriggersLv
    )
{
    PES_TRIGGER_CONTEXT context;

    context = PhAllocateZero(sizeof(ES_TRIGGER_CONTEXT));
    context->ServiceItem = ServiceItem;
    context->WindowHandle = WindowHandle;
    context->TriggersLv = TriggersLv;
    context->InfoList = PhCreateList(4);

    PhSetListViewStyle(TriggersLv, FALSE, TRUE);
    PhSetControlTheme(TriggersLv, L"explorer");
    PhAddListViewColumn(
        TriggersLv,
        0,
        0,
        0,
        LVCFMT_LEFT,
        300,
        PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_COLUMN_TRIGGER, NULL)))
        );
    PhAddListViewColumn(
        TriggersLv,
        1,
        1,
        1,
        LVCFMT_LEFT,
        60,
        PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_COLUMN_ACTION, NULL)))
        );
    PhSetExtendedListView(TriggersLv);

    EnableWindow(GetDlgItem(WindowHandle, IDC_EDIT), FALSE);
    EnableWindow(GetDlgItem(WindowHandle, IDC_DELETE), FALSE);

    return context;
}

VOID EsDestroyServiceTriggerContext(
    _In_ PES_TRIGGER_CONTEXT Context
    )
{
    ULONG i;

    for (i = 0; i < Context->InfoList->Count; i++)
    {
        EspDestroyTriggerInfo(Context->InfoList->Items[i]);
    }

    PhDereferenceObject(Context->InfoList);
    PhFree(Context);
}

_Function_class_(PH_ENUM_KEY_CALLBACK)
BOOLEAN NTAPI EspEtwPublishersEnumerateKeyCallback(
    _In_ HANDLE RootDirectory,
    _In_ PKEY_BASIC_INFORMATION Information,
    _In_ PVOID Context
    )
{
    PH_STRINGREF keyName;
    HANDLE keyHandle;
    GUID guid;
    PPH_STRING publisherName;

    keyName.Buffer = Information->Name;
    keyName.Length = Information->NameLength;

    // Make sure this is a valid publisher key. (wj32)
    if (NT_SUCCESS(PhStringToGuid(&keyName, &guid)))
    {
        if (NT_SUCCESS(PhOpenKey(
            &keyHandle,
            KEY_READ,
            RootDirectory,
            &keyName,
            0
            )))
        {
            publisherName = PhQueryRegistryString(keyHandle, NULL);

            if (publisherName)
            {
                if (publisherName->Length != 0)
                {
                    ETW_PUBLISHER_ENTRY entry;

                    memset(&entry, 0, sizeof(ETW_PUBLISHER_ENTRY));
                    PhMoveReference(&entry.PublisherName, publisherName);
                    memcpy_s(&entry.Guid, sizeof(entry.Guid), &guid, sizeof(GUID));

                    PhAddItemArray(Context, &entry);
                }
                else
                {
                    PhDereferenceObject(publisherName);
                }
            }

            NtClose(keyHandle);
        }
    }

    return TRUE;
}

NTSTATUS EspEnumerateEtwPublishers(
    _Out_ PETW_PUBLISHER_ENTRY *Entries,
    _Out_ PULONG NumberOfEntries
    )
{
    NTSTATUS status;
    HANDLE publishersKeyHandle;
    PH_ARRAY publishersArrayList;

    status = PhOpenKey(
        &publishersKeyHandle,
        KEY_READ,
        PH_KEY_LOCAL_MACHINE,
        &PublishersKeyName,
        0
        );

    if (!NT_SUCCESS(status))
        return status;

    PhInitializeArray(&publishersArrayList, sizeof(ETW_PUBLISHER_ENTRY), 100);
    PhEnumerateKey(
        publishersKeyHandle,
        KeyBasicInformation,
        EspEtwPublishersEnumerateKeyCallback,
        &publishersArrayList
        );
    NtClose(publishersKeyHandle);

    *Entries = PhFinalArrayItems(&publishersArrayList);
    *NumberOfEntries = (ULONG)publishersArrayList.Count;

    return STATUS_SUCCESS;
}

_Success_(return)
BOOLEAN EspLookupEtwPublisherGuid(
    _In_ PCPH_STRINGREF PublisherName,
    _Out_ PGUID Guid
    )
{
    BOOLEAN result;
    PETW_PUBLISHER_ENTRY entries;
    ULONG numberOfEntries;
    ULONG i;

    if (!NT_SUCCESS(EspEnumerateEtwPublishers(&entries, &numberOfEntries)))
        return FALSE;

    result = FALSE;

    for (i = 0; i < numberOfEntries; i++)
    {
        if (!result && PhEqualStringRef(&entries[i].PublisherName->sr, PublisherName, TRUE))
        {
            *Guid = entries[i].Guid;
            result = TRUE;
        }

        PhDereferenceObject(entries[i].PublisherName);
    }

    PhFree(entries);

    return result;
}

VOID EspFormatTriggerInfo(
    _In_ PES_TRIGGER_INFO Info,
    _Out_ PPH_STRING *TriggerString,
    _Out_ PPH_STRING *ActionString
    )
{
    PPH_STRING triggerString = NULL;
    PPH_STRING actionString;
    CONST ACTION_ENTRY* actionEntry;
    ULONG i;

    switch (Info->Type)
    {
    case SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL:
        {
            PPH_STRING typeString;
            PPH_STRING guidString;

            typeString = PhLoadUiString(
                PluginInstance->DllBase,
                IDS_ES_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL,
                NULL
                );

            if (!Info->Subtype)
            {
                triggerString = typeString;
            }
            else
            {
                guidString = PhFormatGuid(Info->Subtype);
                triggerString = PhFormatString(
                    L"%s: %s",
                    PhGetString(typeString),
                    PhGetString(guidString)
                    );
                PhDereferenceObject(typeString);
                PhDereferenceObject(guidString);
            }
        }
        break;
    case SERVICE_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE:
        {
            PPH_STRING typeString;
            PPH_STRING guidString;

            typeString = PhLoadUiString(
                PluginInstance->DllBase,
                IDS_ES_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE,
                NULL
                );

            if (!Info->Subtype)
            {
                triggerString = typeString;
            }
            else
            {
                guidString = PhFormatGuid(Info->Subtype);
                triggerString = PhFormatString(
                    L"%s: %s",
                    PhGetString(typeString),
                    PhGetString(guidString)
                    );
                PhDereferenceObject(typeString);
                PhDereferenceObject(guidString);
            }
        }
        break;
    case SERVICE_TRIGGER_TYPE_CUSTOM:
        {
            PPH_STRING typeString;

            typeString = PhLoadUiString(
                PluginInstance->DllBase,
                IDS_ES_TRIGGER_CUSTOM,
                NULL
                );

            if (Info->Subtype)
            {
                PPH_STRING publisherName;

                // Try to lookup the publisher name from the GUID. (wj32)
                publisherName = PhGetEtwPublisherName(Info->Subtype);
                triggerString = PhFormatString(
                    L"%s: %s",
                    PhGetString(typeString),
                    PhGetString(publisherName)
                    );
                PhDereferenceObject(typeString);
                PhDereferenceObject(publisherName);
            }
            else
            {
                triggerString = typeString;
            }
        }
        break;
    default:
        {
            CONST SUBTYPE_ENTRY* subTypeEntry = NULL;

            for (i = 0; i < ARRAYSIZE(SubTypeEntries); i++)
            {
                if (SubTypeEntries[i].Type == Info->Type)
                {
                    if (!Info->Subtype && !SubTypeEntries[i].Guid)
                    {
                        subTypeEntry = &SubTypeEntries[i];
                        break;
                    }
                    else if (Info->Subtype && SubTypeEntries[i].Guid && IsEqualGUID(Info->Subtype, SubTypeEntries[i].Guid))
                    {
                        subTypeEntry = &SubTypeEntries[i];
                        break;
                    }
                    else if (!subTypeEntry && SubTypeEntries[i].Guid == &SubTypeUnknownGuid)
                    {
                        subTypeEntry = &SubTypeEntries[i];
                    }
                }
            }

            triggerString = PhLoadUiString(
                PluginInstance->DllBase,
                subTypeEntry ? subTypeEntry->ResourceId : IDS_ES_TRIGGER_UNKNOWN,
                NULL
                );
        }
        break;
    }

    actionEntry = EspFindTriggerActionEntry(Info->Action);
    actionString = PhLoadUiString(
        PluginInstance->DllBase,
        actionEntry ? actionEntry->ResourceId : IDS_ES_TRIGGER_UNKNOWN,
        NULL
        );

    *TriggerString = triggerString;
    *ActionString = actionString;
}

VOID EsLoadServiceTriggerInfo(
    _In_ PES_TRIGGER_CONTEXT Context,
    _In_ SC_HANDLE ServiceHandle
    )
{
    PSERVICE_TRIGGER_INFO triggerInfo;
    ULONG i;

    EspClearTriggerInfoList(Context->InfoList);

    if (NT_SUCCESS(PhQueryServiceVariableSize(ServiceHandle, SERVICE_CONFIG_TRIGGER_INFO, &triggerInfo)))
    {
        for (i = 0; i < triggerInfo->cTriggers; i++)
        {
            PSERVICE_TRIGGER trigger = &triggerInfo->pTriggers[i];
            PES_TRIGGER_INFO info;
            PPH_STRING triggerString;
            PPH_STRING actionString;
            INT lvItemIndex;

            info = EspCreateTriggerInfo(trigger);
            PhAddItemList(Context->InfoList, info);

            EspFormatTriggerInfo(info, &triggerString, &actionString);

            lvItemIndex = PhAddListViewItem(Context->TriggersLv, MAXINT, PhGetString(triggerString), info);
            PhSetListViewSubItem(Context->TriggersLv, lvItemIndex, 1, PhGetString(actionString));

            PhDereferenceObject(triggerString);
            PhDereferenceObject(actionString);
        }

        Context->InitialNumberOfTriggers = triggerInfo->cTriggers;

        ExtendedListView_SortItems(Context->TriggersLv);

        PhFree(triggerInfo);
    }
}

_Success_(return)
BOOLEAN EsSaveServiceTriggerInfo(
    _In_ PES_TRIGGER_CONTEXT Context,
    _Out_opt_ PNTSTATUS NtResult
    )
{
    BOOLEAN result = TRUE;
    NTSTATUS status;
    PH_AUTO_POOL autoPool;
    SC_HANDLE serviceHandle;
    SERVICE_TRIGGER_INFO triggerInfo;
    ULONG i;
    ULONG j;

    if (!Context->Dirty)
        return TRUE;

    // Do not try to change trigger information if we didn't have any triggers before and we don't
    // have any now. ChangeServiceConfig2 returns an error in this situation.
    if (Context->InitialNumberOfTriggers == 0 && Context->InfoList->Count == 0)
        return TRUE;

    PhInitializeAutoPool(&autoPool);

    memset(&triggerInfo, 0, sizeof(SERVICE_TRIGGER_INFO));
    triggerInfo.cTriggers = Context->InfoList->Count;

    // pTriggers needs to be NULL when there are no triggers.
    if (Context->InfoList->Count != 0)
    {
        triggerInfo.pTriggers = PH_AUTO(PhCreateAlloc(Context->InfoList->Count * sizeof(SERVICE_TRIGGER)));
        memset(triggerInfo.pTriggers, 0, Context->InfoList->Count * sizeof(SERVICE_TRIGGER));

        for (i = 0; i < Context->InfoList->Count; i++)
        {
            PSERVICE_TRIGGER trigger = &triggerInfo.pTriggers[i];
            PES_TRIGGER_INFO info = Context->InfoList->Items[i];

            trigger->dwTriggerType = info->Type;
            trigger->dwAction = info->Action;
            trigger->pTriggerSubtype = info->Subtype;

            if (info->DataList && info->DataList->Count != 0)
            {
                trigger->cDataItems = info->DataList->Count;
                trigger->pDataItems = PH_AUTO(PhCreateAlloc(info->DataList->Count * sizeof(SERVICE_TRIGGER_SPECIFIC_DATA_ITEM)));

                for (j = 0; j < info->DataList->Count; j++)
                {
                    PSERVICE_TRIGGER_SPECIFIC_DATA_ITEM dataItem = &trigger->pDataItems[j];
                    PES_TRIGGER_DATA data = info->DataList->Items[j];

                    dataItem->dwDataType = data->Type;

                    if (data->Type == SERVICE_TRIGGER_DATA_TYPE_STRING)
                    {
                        dataItem->cbData = (ULONG)data->String->Length + sizeof(UNICODE_NULL); // include null terminator
                        dataItem->pData = (PBYTE)data->String->Buffer;
                    }
                    else if (data->Type == SERVICE_TRIGGER_DATA_TYPE_BINARY)
                    {
                        dataItem->cbData = data->BinaryLength;
                        dataItem->pData = data->Binary;
                    }
                    else if (data->Type == SERVICE_TRIGGER_DATA_TYPE_LEVEL)
                    {
                        dataItem->cbData = sizeof(UCHAR);
                        dataItem->pData = (PBYTE)&data->Byte;
                    }
                    else if (data->Type == SERVICE_TRIGGER_DATA_TYPE_KEYWORD_ANY || data->Type == SERVICE_TRIGGER_DATA_TYPE_KEYWORD_ALL)
                    {
                        dataItem->cbData = sizeof(ULONG64);
                        dataItem->pData = (PBYTE)&data->UInt64;
                    }
                }
            }
        }
    }

    status = PhOpenService(&serviceHandle, SERVICE_CHANGE_CONFIG, PhGetString(Context->ServiceItem->Name));

    if (NT_SUCCESS(status))
    {
        status = PhChangeServiceConfig2(serviceHandle, SERVICE_CONFIG_TRIGGER_INFO, &triggerInfo);

        if (!NT_SUCCESS(status))
        {
            result = FALSE;
        }

        PhCloseServiceHandle(serviceHandle);
    }
    else
    {
        result = FALSE;

        if (status == STATUS_ACCESS_DENIED && !PhGetOwnTokenAttributes().Elevated)
        {
            // Elevate using phsvc.
            if (PhUiConnectToPhSvc(Context->WindowHandle, FALSE))
            {
                result = TRUE;

                if (!NT_SUCCESS(status = PhSvcCallChangeServiceConfig2(
                    PhGetString(Context->ServiceItem->Name),
                    SERVICE_CONFIG_TRIGGER_INFO,
                    &triggerInfo
                    )))
                {
                    result = FALSE;
                }

                PhUiDisconnectFromPhSvc();
            }
            else
            {
                // User cancelled elevation.
                status = STATUS_CANCELLED;
            }
        }
    }

    PhDeleteAutoPool(&autoPool);

    if (NtResult)
        *NtResult = status;

    return result;
}

LOGICAL EspSetListViewItemParam(
    _In_ HWND ListViewHandle,
    _In_ INT Index,
    _In_ PVOID Param
    )
{
    LVITEM item;

    item.mask = LVIF_PARAM;
    item.iItem = Index;
    item.iSubItem = 0;
    item.lParam = (LPARAM)Param;

    return ListView_SetItem(ListViewHandle, &item);
}

VOID EsHandleEventServiceTrigger(
    _In_ PES_TRIGGER_CONTEXT Context,
    _In_ ULONG Event
    )
{
    switch (Event)
    {
    case ES_TRIGGER_EVENT_NEW:
        {
            Context->EditingInfo = EspCreateTriggerInfo(NULL);
            Context->EditingInfo->Type = SERVICE_TRIGGER_TYPE_IP_ADDRESS_AVAILABILITY;
            Context->EditingInfo->SubtypeBuffer = NetworkManagerFirstIpAddressArrivalGuid;
            Context->EditingInfo->Subtype = &Context->EditingInfo->SubtypeBuffer;
            Context->EditingInfo->Action = SERVICE_TRIGGER_ACTION_SERVICE_START;

            if (PhDialogBox(
                NtCurrentImageBase(),
                MAKEINTRESOURCE(IDD_SRVTRIGGER),
                Context->WindowHandle,
                EspServiceTriggerDlgProc,
                Context
                ) == IDOK)
            {
                PPH_STRING triggerString;
                PPH_STRING actionString;
                INT lvItemIndex;

                Context->Dirty = TRUE;
                PhAddItemList(Context->InfoList, Context->EditingInfo);

                EspFormatTriggerInfo(Context->EditingInfo, &triggerString, &actionString);

                lvItemIndex = PhAddListViewItem(Context->TriggersLv, MAXINT, PhGetString(triggerString), Context->EditingInfo);
                PhSetListViewSubItem(Context->TriggersLv, lvItemIndex, 1, PhGetString(actionString));

                PhDereferenceObject(triggerString);
                PhDereferenceObject(actionString);
            }
            else
            {
                EspDestroyTriggerInfo(Context->EditingInfo);
            }

            Context->EditingInfo = NULL;
        }
        break;
    case ES_TRIGGER_EVENT_EDIT:
        {
            INT lvItemIndex;
            PES_TRIGGER_INFO info;
            ULONG index;

            lvItemIndex = PhFindListViewItemByFlags(Context->TriggersLv, INT_ERROR, LVNI_SELECTED);

            if (lvItemIndex != INT_ERROR && PhGetListViewItemParam(Context->TriggersLv, lvItemIndex, (PVOID *)&info))
            {
                index = PhFindItemList(Context->InfoList, info);

                if (index != ULONG_MAX)
                {
                    Context->EditingInfo = EspCloneTriggerInfo(info);

                    if (PhDialogBox(
                        NtCurrentImageBase(),
                        MAKEINTRESOURCE(IDD_SRVTRIGGER),
                        Context->WindowHandle,
                        EspServiceTriggerDlgProc,
                        Context
                        ) == IDOK)
                    {
                        PPH_STRING triggerString;
                        PPH_STRING actionString;

                        Context->Dirty = TRUE;
                        EspDestroyTriggerInfo(Context->InfoList->Items[index]);
                        Context->InfoList->Items[index] = Context->EditingInfo;

                        EspFormatTriggerInfo(Context->EditingInfo, &triggerString, &actionString);
                        PhSetListViewSubItem(Context->TriggersLv, lvItemIndex, 0, PhGetString(triggerString));
                        PhSetListViewSubItem(Context->TriggersLv, lvItemIndex, 1, PhGetString(actionString));

                        PhDereferenceObject(triggerString);
                        PhDereferenceObject(actionString);

                        EspSetListViewItemParam(Context->TriggersLv, lvItemIndex, Context->EditingInfo);
                    }
                    else
                    {
                        EspDestroyTriggerInfo(Context->EditingInfo);
                    }

                    Context->EditingInfo = NULL;
                }
            }
        }
        break;
    case ES_TRIGGER_EVENT_DELETE:
        {
            INT lvItemIndex;
            PES_TRIGGER_INFO info;
            ULONG index;

            lvItemIndex = PhFindListViewItemByFlags(Context->TriggersLv, INT_ERROR, LVNI_SELECTED);

            if (lvItemIndex != INT_ERROR && PhGetListViewItemParam(Context->TriggersLv, lvItemIndex, (PVOID *)&info))
            {
                index = PhFindItemList(Context->InfoList, info);

                if (index != ULONG_MAX)
                {
                    EspDestroyTriggerInfo(info);
                    PhRemoveItemList(Context->InfoList, index);
                    PhRemoveListViewItem(Context->TriggersLv, lvItemIndex);
                }
            }

            Context->Dirty = TRUE;
        }
        break;
    case ES_TRIGGER_EVENT_SELECTIONCHANGED:
        {
            ULONG selectedCount;

            selectedCount = ListView_GetSelectedCount(Context->TriggersLv);

            EnableWindow(GetDlgItem(Context->WindowHandle, IDC_EDIT), selectedCount == 1);
            EnableWindow(GetDlgItem(Context->WindowHandle, IDC_DELETE), selectedCount == 1);
        }
        break;
    }
}

static int __cdecl EtwPublisherByNameCompareFunction(
    _In_ const void *elem1,
    _In_ const void *elem2
    )
{
    PETW_PUBLISHER_ENTRY entry1 = (PETW_PUBLISHER_ENTRY)elem1;
    PETW_PUBLISHER_ENTRY entry2 = (PETW_PUBLISHER_ENTRY)elem2;

    return PhCompareString(entry1->PublisherName, entry2->PublisherName, TRUE);
}

VOID EspFixServiceTriggerControls(
    _In_ HWND WindowHandle,
    _In_ PES_TRIGGER_CONTEXT Context
    )
{
    HWND typeComboBox;
    HWND subTypeComboBox;
    ULONG i;
    PVOID selectedTypeData;
    ULONG type;
    PVOID selectedSubTypeData;

    typeComboBox = GetDlgItem(WindowHandle, IDC_TYPE);
    subTypeComboBox = GetDlgItem(WindowHandle, IDC_SUBTYPE);

    if (!EspGetSelectedTriggerComboBoxItemData(typeComboBox, &selectedTypeData))
        return;

    type = PtrToUlong(selectedTypeData);

    if (Context->LastSelectedType != type)
    {
        // Change the contents of the subtype combo box based on the type.

        ComboBox_ResetContent(subTypeComboBox);

        switch (type)
        {
        case SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL:
            {
                EspAddTriggerComboBoxResourceItem(
                    subTypeComboBox,
                    EspCustomSubTypeEntry.ResourceId,
                    (PVOID)&EspCustomSubTypeEntry
                    );
            }
            break;
        case SERVICE_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE:
            {
                EspAddTriggerComboBoxResourceItem(
                    subTypeComboBox,
                    EspCustomSubTypeEntry.ResourceId,
                    (PVOID)&EspCustomSubTypeEntry
                    );
            }
            break;
        case SERVICE_TRIGGER_TYPE_CUSTOM:
            {
                PETW_PUBLISHER_ENTRY entries;
                ULONG numberOfEntries;

                EspAddTriggerComboBoxResourceItem(
                    subTypeComboBox,
                    EspCustomSubTypeEntry.ResourceId,
                    (PVOID)&EspCustomSubTypeEntry
                    );

                // Display a list of publishers.
                if (NT_SUCCESS(EspEnumerateEtwPublishers(&entries, &numberOfEntries)))
                {
                    // Sort the list by name.
                    qsort(entries, numberOfEntries, sizeof(ETW_PUBLISHER_ENTRY), EtwPublisherByNameCompareFunction);

                    for (i = 0; i < numberOfEntries; i++)
                    {
                        EspAddTriggerComboBoxItem(
                            subTypeComboBox,
                            entries[i].PublisherName->Buffer,
                            NULL
                            );
                        PhDereferenceObject(entries[i].PublisherName);
                    }

                    PhFree(entries);
                }
            }
            break;
        default:
            for (i = 0; i < ARRAYSIZE(SubTypeEntries); i++)
            {
                if (SubTypeEntries[i].Type == type && SubTypeEntries[i].Guid && SubTypeEntries[i].Guid != &SubTypeUnknownGuid)
                {
                    EspAddTriggerComboBoxResourceItem(
                        subTypeComboBox,
                        SubTypeEntries[i].ResourceId,
                        (PVOID)&SubTypeEntries[i]
                        );
                }
            }
            break;
        }

        ComboBox_SetCurSel(subTypeComboBox, 0);

        Context->LastSelectedType = type;
    }

    if (!EspGetSelectedTriggerComboBoxItemData(subTypeComboBox, &selectedSubTypeData))
        return;

    if (selectedSubTypeData == &EspCustomSubTypeEntry)
    {
        EnableWindow(GetDlgItem(WindowHandle, IDC_SUBTYPECUSTOM), TRUE);
        PhSetDialogItemText(WindowHandle, IDC_SUBTYPECUSTOM, Context->LastCustomSubType->Buffer);
    }
    else
    {
        if (IsWindowEnabled(GetDlgItem(WindowHandle, IDC_SUBTYPECUSTOM)))
        {
            EnableWindow(GetDlgItem(WindowHandle, IDC_SUBTYPECUSTOM), FALSE);
            PhMoveReference(&Context->LastCustomSubType, PhGetWindowText(GetDlgItem(WindowHandle, IDC_SUBTYPECUSTOM)));
            PhSetDialogItemText(WindowHandle, IDC_SUBTYPECUSTOM, L"");
        }
    }
}

PPH_STRING EspConvertNullsToNewLines(
    _In_ PPH_STRING String
    )
{
    PH_STRING_BUILDER sb;
    ULONG i;

    PhInitializeStringBuilder(&sb, String->Length);

    for (i = 0; i < (ULONG)String->Length / 2; i++)
    {
        if (String->Buffer[i] == 0)
        {
            PhAppendStringBuilderEx(&sb, L"\r\n", 4);
            continue;
        }

        PhAppendCharStringBuilder(&sb, String->Buffer[i]);
    }

    return PhFinalStringBuilderString(&sb);
}

PPH_STRING EspConvertNewLinesToNulls(
    _In_ PPH_STRING String
    )
{
    PPH_STRING text;
    SIZE_T count;
    SIZE_T i;

    text = PhCreateStringEx(NULL, String->Length + sizeof(UNICODE_NULL)); // plus one character for an extra null terminator (see below)
    text->Length = 0;
    count = 0;

    for (i = 0; i < String->Length / 2; i++)
    {
        // Lines are terminated by "\r\n".
        if (String->Buffer[i] == '\r')
        {
            continue;
        }

        if (String->Buffer[i] == '\n')
        {
            text->Buffer[count++] = UNICODE_NULL;
            continue;
        }

        text->Buffer[count++] = String->Buffer[i];
    }

    if (count != 0)
    {
        // Make sure we have an extra null terminator at the end, as required of multistrings.
        if (text->Buffer[count - 1] != UNICODE_NULL)
            text->Buffer[count++] = UNICODE_NULL;
    }

    text->Length = count * sizeof(WCHAR);

    return text;
}

PPH_STRING EspConvertNullsToSpaces(
    _In_ PPH_STRING String
    )
{
    PPH_STRING text;
    SIZE_T j;

    text = PhDuplicateString(String);

    for (j = 0; j < text->Length / sizeof(WCHAR); j++)
    {
        if (text->Buffer[j] == UNICODE_NULL)
            text->Buffer[j] = ' ';
    }

    return text;
}

VOID EspFormatTriggerData(
    _In_ PES_TRIGGER_DATA Data,
    _Out_ PPH_STRING *Text
    )
{
    if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_STRING)
    {
        // This check works for both normal strings and multistrings.
        if (Data->String->Length != 0)
        {
            // Prepare the text for display by replacing null characters with spaces.
            *Text = EspConvertNullsToSpaces(Data->String);
        }
        else
        {
            *Text = PhCreateString(L"(empty string)");
        }
    }
    else if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_BINARY)
    {
        *Text = PhCreateString(L"(binary data)");
    }
    else if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_LEVEL)
    {
        *Text = PhFormatString(L"(level) %u", Data->Byte);
    }
    else if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_KEYWORD_ANY)
    {
        *Text = PhFormatString(L"(keyword any) 0x%I64x", Data->UInt64);
    }
    else if (Data->Type == SERVICE_TRIGGER_DATA_TYPE_KEYWORD_ALL)
    {
        *Text = PhFormatString(L"(keyword all) 0x%I64x", Data->UInt64);
    }
    else
    {
        *Text = PhCreateString(L"(unknown type)");
    }
}

INT_PTR CALLBACK EspServiceTriggerDlgProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    )
{
    PES_TRIGGER_CONTEXT context;

    if (WindowMessage == WM_INITDIALOG)
    {
        context = (PES_TRIGGER_CONTEXT)lParam;
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
            HWND typeComboBox;
            HWND actionComboBox;
            HWND lvHandle;
            ULONG i;

            context->LastSelectedType = 0;

            if (context->EditingInfo->Subtype)
                context->LastCustomSubType = PhFormatGuid(context->EditingInfo->Subtype);
            else
                context->LastCustomSubType = PhReferenceEmptyString();

            typeComboBox = GetDlgItem(WindowHandle, IDC_TYPE);
            actionComboBox = GetDlgItem(WindowHandle, IDC_ACTION);

            for (i = 0; i < ARRAYSIZE(TypeEntries); i++)
            {
                INT itemIndex;

                itemIndex = EspAddTriggerComboBoxResourceItem(
                    typeComboBox,
                    TypeEntries[i].ResourceId,
                    UlongToPtr(TypeEntries[i].Type)
                    );

                if (itemIndex != CB_ERR && TypeEntries[i].Type == context->EditingInfo->Type)
                    ComboBox_SetCurSel(typeComboBox, itemIndex);
            }

            for (i = 0; i < ARRAYSIZE(ActionEntries); i++)
            {
                INT itemIndex;

                itemIndex = EspAddTriggerComboBoxResourceItem(
                    actionComboBox,
                    ActionEntries[i].ResourceId,
                    UlongToPtr(ActionEntries[i].Action)
                    );

                if (itemIndex != CB_ERR && ActionEntries[i].Action == context->EditingInfo->Action)
                    ComboBox_SetCurSel(actionComboBox, itemIndex);
            }

            EspFixServiceTriggerControls(WindowHandle, context);

            if (context->EditingInfo->Type != SERVICE_TRIGGER_TYPE_CUSTOM)
            {
                for (i = 0; i < ARRAYSIZE(SubTypeEntries); i++)
                {
                    if (
                        SubTypeEntries[i].Type == context->EditingInfo->Type &&
                        SubTypeEntries[i].Guid &&
                        context->EditingInfo->Subtype &&
                        IsEqualGUID(SubTypeEntries[i].Guid, context->EditingInfo->Subtype)
                        )
                    {
                        if (!EspSelectTriggerComboBoxItemData(
                            GetDlgItem(WindowHandle, IDC_SUBTYPE),
                            (PVOID)&SubTypeEntries[i]
                            ))
                        {
                            ComboBox_SetCurSel(GetDlgItem(WindowHandle, IDC_SUBTYPE), -1);
                        }
                        break;
                    }
                }
            }
            else
            {
                if (context->EditingInfo->Subtype)
                {
                    PPH_STRING publisherName;

                    // Try to select the publisher name in the subtype list. (wj32)
                    publisherName = PhGetEtwPublisherName(context->EditingInfo->Subtype);
                    PhSelectComboBoxString(GetDlgItem(WindowHandle, IDC_SUBTYPE), publisherName->Buffer, FALSE);
                    PhDereferenceObject(publisherName);
                }
            }

            // Call a second time since the state of the custom subtype text box may have changed.
            EspFixServiceTriggerControls(WindowHandle, context);

            lvHandle = GetDlgItem(WindowHandle, IDC_LIST);
            PhSetListViewStyle(lvHandle, FALSE, TRUE);
            PhSetControlTheme(lvHandle, L"explorer");
            PhAddListViewColumn(
                lvHandle,
                0,
                0,
                0,
                LVCFMT_LEFT,
                280,
                PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_COLUMN_DATA, NULL)))
                );

            if (context->EditingInfo->DataList)
            {
                for (i = 0; i < context->EditingInfo->DataList->Count; i++)
                {
                    PES_TRIGGER_DATA data;
                    PPH_STRING text;
                    INT lvItemIndex;

                    data = context->EditingInfo->DataList->Items[i];

                    EspFormatTriggerData(data, &text);
                    lvItemIndex = PhAddListViewItem(lvHandle, MAXINT, text->Buffer, data);
                    PhDereferenceObject(text);
                }
            }

            EnableWindow(GetDlgItem(WindowHandle, IDC_EDIT), FALSE);
            EnableWindow(GetDlgItem(WindowHandle, IDC_DELETE), FALSE);

            PhInitializeWindowTheme(WindowHandle, !!PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT));
        }
        break;
    case WM_DESTROY:
        {
            PhRemoveWindowContext(WindowHandle, PH_WINDOW_CONTEXT_DEFAULT);
            PhClearReference(&context->LastCustomSubType);
        }
        break;
    case WM_COMMAND:
        {
            switch (GET_WM_COMMAND_ID(wParam, lParam))
            {
            case IDC_TYPE:
                if (GET_WM_COMMAND_CMD(wParam, lParam) == CBN_SELCHANGE)
                {
                    EspFixServiceTriggerControls(WindowHandle, context);
                }
                break;
            case IDC_SUBTYPE:
                if (GET_WM_COMMAND_CMD(wParam, lParam) == CBN_SELCHANGE)
                {
                    EspFixServiceTriggerControls(WindowHandle, context);
                }
                break;
            case IDC_NEW:
                {
                    HWND lvHandle;

                    lvHandle = GetDlgItem(WindowHandle, IDC_LIST);
                    context->EditingValue = PhReferenceEmptyString();

                    if (PhDialogBox(
                        NtCurrentImageBase(),
                        MAKEINTRESOURCE(IDD_VALUE),
                        WindowHandle,
                        ValueDlgProc,
                        context
                        ) == IDOK)
                    {
                        PES_TRIGGER_DATA data;
                        PPH_STRING text;
                        INT lvItemIndex;

                        data = EspCreateTriggerData(NULL);
                        data->Type = SERVICE_TRIGGER_DATA_TYPE_STRING;
                        data->String = EspConvertNewLinesToNulls(context->EditingValue);

                        if (!context->EditingInfo->DataList)
                            context->EditingInfo->DataList = PhCreateList(4);

                        PhAddItemList(context->EditingInfo->DataList, data);

                        EspFormatTriggerData(data, &text);
                        lvItemIndex = PhAddListViewItem(lvHandle, MAXINT, text->Buffer, data);
                        PhDereferenceObject(text);
                    }

                    PhClearReference(&context->EditingValue);
                }
                break;
            case IDC_EDIT:
                {
                    HWND lvHandle;
                    INT lvItemIndex;
                    PES_TRIGGER_DATA data;
                    ULONG index;

                    lvHandle = GetDlgItem(WindowHandle, IDC_LIST);
                    lvItemIndex = PhFindListViewItemByFlags(lvHandle, INT_ERROR, LVNI_SELECTED);

                    if (
                        lvItemIndex != INT_ERROR && PhGetListViewItemParam(lvHandle, lvItemIndex, (PVOID *)&data) &&
                        data->Type == SERVICE_TRIGGER_DATA_TYPE_STRING // editing binary values is not supported
                        )
                    {
                        index = PhFindItemList(context->EditingInfo->DataList, data);

                        if (index != ULONG_MAX)
                        {
                            context->EditingValue = EspConvertNullsToNewLines(data->String);

                            if (PhDialogBox(
                                NtCurrentImageBase(),
                                MAKEINTRESOURCE(IDD_VALUE),
                                WindowHandle,
                                ValueDlgProc,
                                context
                                ) == IDOK)
                            {
                                PPH_STRING text;

                                PhMoveReference(&data->String, EspConvertNewLinesToNulls(context->EditingValue));

                                EspFormatTriggerData(data, &text);
                                PhSetListViewSubItem(lvHandle, lvItemIndex, 0, text->Buffer);
                                PhDereferenceObject(text);
                            }

                            PhClearReference(&context->EditingValue);
                        }
                    }
                }
                break;
            case IDC_DELETE:
                {
                    HWND lvHandle;
                    INT lvItemIndex;
                    PES_TRIGGER_DATA data;
                    ULONG index;

                    lvHandle = GetDlgItem(WindowHandle, IDC_LIST);
                    lvItemIndex = PhFindListViewItemByFlags(lvHandle, INT_ERROR, LVNI_SELECTED);

                    if (lvItemIndex != INT_ERROR && PhGetListViewItemParam(lvHandle, lvItemIndex, (PVOID *)&data))
                    {
                        index = PhFindItemList(context->EditingInfo->DataList, data);

                        if (index != ULONG_MAX)
                        {
                            EspDestroyTriggerData(data);
                            PhRemoveItemList(context->EditingInfo->DataList, index);
                            PhRemoveListViewItem(lvHandle, lvItemIndex);
                        }
                    }
                }
                break;
            case IDCANCEL:
                EndDialog(WindowHandle, IDCANCEL);
                break;
            case IDOK:
                {
                    PH_AUTO_POOL autoPool;
                    PVOID selectedTypeData;
                    PVOID selectedSubTypeData;
                    PVOID selectedActionData;
                    CONST TYPE_ENTRY* typeEntry;
                    CONST ACTION_ENTRY* actionEntry;
                    CONST SUBTYPE_ENTRY* subTypeEntry;
                    PPH_STRING typeString;
                    PPH_STRING customSubTypeString;
                    GUID subTypeBuffer;
                    ULONG type;
                    ULONG action;
                    ULONG i;

                    PhInitializeAutoPool(&autoPool);

                    if (!EspGetSelectedTriggerComboBoxItemData(
                        GetDlgItem(WindowHandle, IDC_TYPE),
                        &selectedTypeData
                        ))
                    {
                        goto DoNotClose;
                    }

                    if (!EspGetSelectedTriggerComboBoxItemData(
                        GetDlgItem(WindowHandle, IDC_SUBTYPE),
                        &selectedSubTypeData
                        ))
                    {
                        goto DoNotClose;
                    }

                    if (!EspGetSelectedTriggerComboBoxItemData(
                        GetDlgItem(WindowHandle, IDC_ACTION),
                        &selectedActionData
                        ))
                    {
                        goto DoNotClose;
                    }

                    type = PtrToUlong(selectedTypeData);
                    action = PtrToUlong(selectedActionData);
                    typeEntry = EspFindTriggerTypeEntry(type);
                    actionEntry = EspFindTriggerActionEntry(action);

                    if (!typeEntry || !actionEntry)
                        goto DoNotClose;

                    if (
                        action != SERVICE_TRIGGER_ACTION_SERVICE_START &&
                        action != SERVICE_TRIGGER_ACTION_SERVICE_STOP
                        )
                    {
                        goto DoNotClose;
                    }

                    if (selectedSubTypeData == &EspCustomSubTypeEntry)
                    {
                        PH_STRINGREF guidString;

                        if (
                            type != SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL &&
                            type != SERVICE_TRIGGER_TYPE_CUSTOM_SYSTEM_STATE_CHANGE &&
                            type != SERVICE_TRIGGER_TYPE_CUSTOM
                            )
                        {
                            goto DoNotClose;
                        }

                        customSubTypeString = PhaGetDlgItemText(WindowHandle, IDC_SUBTYPECUSTOM);
                        guidString = customSubTypeString->sr;

                        // Trim whitespace.

                        while (guidString.Length != 0 && *guidString.Buffer == L' ')
                        {
                            guidString.Buffer++;
                            guidString.Length -= sizeof(WCHAR);
                        }

                        while (guidString.Length != 0 && guidString.Buffer[guidString.Length / sizeof(WCHAR) - 1] == L' ')
                        {
                            guidString.Length -= sizeof(WCHAR);
                        }

                        if (!NT_SUCCESS(PhStringToGuid(&guidString, &subTypeBuffer)))
                        {
                            PhShowError2(
                                WindowHandle,
                                PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_CUSTOM_SUBTYPE_INVALID, NULL))),
                                L"%s",
                                PhGetStringOrEmpty(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_INVALID_GUID_HINT, NULL)))
                                );
                            goto DoNotClose;
                        }
                    }
                    else if (selectedSubTypeData)
                    {
                        subTypeEntry = NULL;

                        for (i = 0; i < ARRAYSIZE(SubTypeEntries); i++)
                        {
                            if (selectedSubTypeData == &SubTypeEntries[i])
                            {
                                subTypeEntry = &SubTypeEntries[i];
                                break;
                            }
                        }

                        if (
                            !subTypeEntry ||
                            subTypeEntry->Type != type ||
                            !subTypeEntry->Guid ||
                            subTypeEntry->Guid == &SubTypeUnknownGuid
                            )
                        {
                            goto DoNotClose;
                        }

                        subTypeBuffer = *subTypeEntry->Guid;
                    }
                    else
                    {
                        PPH_STRING subTypeString;

                        if (type != SERVICE_TRIGGER_TYPE_CUSTOM)
                            goto DoNotClose;

                        subTypeString = PhaGetDlgItemText(WindowHandle, IDC_SUBTYPE);

                        if (!EspLookupEtwPublisherGuid(&subTypeString->sr, &subTypeBuffer))
                        {
                            PhShowError2(WindowHandle, PhGetString(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_UNABLE_FIND_ETW_PUBLISHER_GUID, NULL))), L"%s", L"");
                            goto DoNotClose;
                        }
                    }

                    typeString = PH_AUTO(PhLoadUiString(
                        PluginInstance->DllBase,
                        typeEntry->ResourceId,
                        NULL
                        ));

                    if (
                        context->EditingInfo->DataList &&
                        context->EditingInfo->DataList->Count != 0 &&
                        type != SERVICE_TRIGGER_TYPE_DEVICE_INTERFACE_ARRIVAL &&
                        type != SERVICE_TRIGGER_TYPE_FIREWALL_PORT_EVENT &&
                        type != SERVICE_TRIGGER_TYPE_NETWORK_ENDPOINT &&
                        type != SERVICE_TRIGGER_TYPE_CUSTOM
                        )
                    {
                        PPH_STRING warningFormat;
                        PCWSTR warningFormatText;
                        INT warningResult;

                        // This trigger has data items, but the trigger type doesn't allow them.
                        warningFormat = PhLoadUiString(
                            PluginInstance->DllBase,
                            IDS_ES_TRIGGER_DATA_NOT_ALLOWED_FORMAT,
                            NULL
                            );
                        warningFormatText = PhGetStringOrDefault(warningFormat, L"The trigger type \"%s\" does not allow data items to be configured.");
                        warningResult = PhShowMessage2(
                            WindowHandle,
                            TD_OK_BUTTON | TD_CANCEL_BUTTON,
                            TD_WARNING_ICON,
                            PhaFormatString(
                                warningFormatText,
                                PhGetString(typeString)
                                )->Buffer,
                            L"%s",
                            PhGetString(PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_ES_TRIGGER_DATA_REMOVAL_WARNING, NULL)))
                            );
                        PhClearReference(&warningFormat);

                        if (warningResult != IDOK)
                        {
                            goto DoNotClose;
                        }

                        for (i = 0; i < context->EditingInfo->DataList->Count; i++)
                        {
                            EspDestroyTriggerData(context->EditingInfo->DataList->Items[i]);
                        }

                        PhClearReference(&context->EditingInfo->DataList);
                    }

                    context->EditingInfo->Type = type;
                    context->EditingInfo->SubtypeBuffer = subTypeBuffer;
                    context->EditingInfo->Subtype = &context->EditingInfo->SubtypeBuffer;
                    context->EditingInfo->Action = action;

                    EndDialog(WindowHandle, IDOK);

DoNotClose:
                    PhDeleteAutoPool(&autoPool);
                }
                break;
            }
        }
        break;
    case WM_NOTIFY:
        {
            LPNMHDR header = (LPNMHDR)lParam;
            HWND lvHandle;

            lvHandle = GetDlgItem(WindowHandle, IDC_LIST);

            switch (header->code)
            {
            case LVN_ITEMCHANGED:
                {
                    if (header->hwndFrom == lvHandle)
                    {
                        if (ListView_GetSelectedCount(lvHandle) == 1)
                        {
                            PES_TRIGGER_DATA data = PhGetSelectedListViewItemParam(GetDlgItem(WindowHandle, IDC_LIST));

                            // Editing binary data is not supported.
                            EnableWindow(GetDlgItem(WindowHandle, IDC_EDIT), data && data->Type == SERVICE_TRIGGER_DATA_TYPE_STRING);
                            EnableWindow(GetDlgItem(WindowHandle, IDC_DELETE), TRUE);
                        }
                        else
                        {
                            EnableWindow(GetDlgItem(WindowHandle, IDC_EDIT), FALSE);
                            EnableWindow(GetDlgItem(WindowHandle, IDC_DELETE), FALSE);
                        }
                    }
                }
                break;
            case NM_DBLCLK:
                {
                    if (header->hwndFrom == lvHandle)
                    {
                        SendMessage(WindowHandle, WM_COMMAND, IDC_EDIT, 0);
                    }
                }
                break;
            }
        }
        break;
    }

    return FALSE;
}

INT_PTR CALLBACK ValueDlgProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam
    )
{
    PES_TRIGGER_CONTEXT context;

    if (WindowMessage == WM_INITDIALOG)
    {
        context = (PES_TRIGGER_CONTEXT)lParam;
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
            PhSetDialogItemText(WindowHandle, IDC_VALUES, context->EditingValue->Buffer);
            PhSetDialogFocus(WindowHandle, GetDlgItem(WindowHandle, IDC_VALUES));
            Edit_SetSel(GetDlgItem(WindowHandle, IDC_VALUES), 0, -1);

            PhInitializeWindowTheme(WindowHandle, !!PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT));
        }
        break;
    case WM_DESTROY:
        {
            PhRemoveWindowContext(WindowHandle, PH_WINDOW_CONTEXT_DEFAULT);
        }
        break;
    case WM_COMMAND:
        {
            switch (GET_WM_COMMAND_ID(wParam, lParam))
            {
            case IDCANCEL:
                EndDialog(WindowHandle, IDCANCEL);
                break;
            case IDOK:
                PhMoveReference(&context->EditingValue, PhGetWindowText(GetDlgItem(WindowHandle, IDC_VALUES)));
                EndDialog(WindowHandle, IDOK);
                break;
            }
        }
        break;
    }

    return FALSE;
}
