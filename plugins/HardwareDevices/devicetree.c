/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     jxy-s   2022-2023
 *
 */

#include "devices.h"
#include <toolstatusintf.h>

#include <devguid.h>

#include <trace.h>

typedef struct _DEVICE_NODE
{
    PH_TREENEW_NODE Node;
    PH_SH_STATE ShState;
    PPH_DEVICE_ITEM DeviceItem;
    PPH_LIST Children;
    ULONG_PTR IconIndex;
    PH_STRINGREF TextCache[PhMaxDeviceProperty];
} DEVICE_NODE, *PDEVICE_NODE;

typedef struct _DEVICE_TREE
{
    PPH_DEVICE_TREE Tree;
    PPH_LIST Nodes;
    PPH_LIST Roots;
} DEVICE_TREE, *PDEVICE_TREE;

typedef struct _DEVICE_TREE_SORT_CONTEXT
{
    ULONG SortColumn;
    PH_SORT_ORDER SortOrder;
} DEVICE_TREE_SORT_CONTEXT, *PDEVICE_TREE_SORT_CONTEXT;

static BOOLEAN AutoRefreshDeviceTree = TRUE;
static BOOLEAN ShowDeviceRootNode = FALSE;
static BOOLEAN ShowDisconnected = TRUE;
static BOOLEAN ShowSoftwareComponents = TRUE;
static BOOLEAN ShowDeviceInterfaces = TRUE;
static BOOLEAN ShowDisabledDeviceInterfaces = TRUE;
static BOOLEAN SortNameDevices = FALSE;
static BOOLEAN SortChildDevices = FALSE;
static BOOLEAN SortRootDevices = FALSE;
static BOOLEAN HighlightUpperFiltered = TRUE;
static BOOLEAN HighlightLowerFiltered = TRUE;
static ULONG DeviceProblemColor = 0;
static ULONG DeviceDisabledColor = 0;
static ULONG DeviceDisconnectedColor = 0;
static ULONG DeviceHighlightColor = 0;
static ULONG DeviceInterfaceColor = 0;
static ULONG DeviceDisabledInterfaceColor = 0;
static ULONG DeviceArrivedColor = 0;
static ULONG DeviceHighlightingDuration = 0;

static CONST PH_STRINGREF DevicePageText = PH_STRINGREF_INIT(L"Devices");
static CONST PH_STRINGREF DeviceBannerText = PH_STRINGREF_INIT(L"Search Devices");
static PPH_OBJECT_TYPE DeviceTreeType = NULL;
static BOOLEAN DeviceTabCreated = FALSE;
static HWND DeviceTreeHandle = NULL;
static ULONG DeviceTreeVisibleColumns[PhMaxDeviceProperty] = { 0 };
static PH_CALLBACK_REGISTRATION DeviceNotifyRegistration = { 0 };
static PH_CALLBACK_REGISTRATION ProcessesUpdatedCallbackRegistration = { 0 };
static PH_CALLBACK_REGISTRATION SettingsUpdatedCallbackRegistration = { 0 };
static PH_CALLBACK_REGISTRATION DeviceTreeMenuItemCallbackRegistration = { 0 };
static PDEVICE_TREE DeviceTree = NULL;
static HIMAGELIST DeviceImageList = NULL;
static PH_INTEGER_PAIR DeviceIconSize = { 16, 16 };
static PH_LIST DeviceFilterList = { 0 };
static PPH_MAIN_TAB_PAGE DevicesAddedTabPage = NULL;
static PTOOLSTATUS_INTERFACE ToolStatusInterface = NULL;
static BOOLEAN DeviceTabSelected = FALSE;
static ULONG DeviceTreeSortColumn = 0;
static PH_SORT_ORDER DeviceTreeSortOrder = NoSortOrder;
static PH_TN_FILTER_SUPPORT DeviceTreeFilterSupport = { 0 };
static PPH_TN_FILTER_ENTRY DeviceTreeFilterEntry = NULL;
static PH_CALLBACK_REGISTRATION SearchChangedRegistration = { 0 };
static PPH_POINTER_LIST DeviceNodeStateList = NULL;

static int __cdecl DeviceListSortByNameFunction(
    const void* Left,
    const void* Right
    )
{
    PDEVICE_NODE lhsNode;
    PDEVICE_NODE rhsNode;
    PPH_DEVICE_PROPERTY lhs;
    PPH_DEVICE_PROPERTY rhs;

    lhsNode = *(PDEVICE_NODE*)Left;
    rhsNode = *(PDEVICE_NODE*)Right;
    lhs = PhGetDeviceProperty(lhsNode->DeviceItem, PhDevicePropertyName);
    rhs = PhGetDeviceProperty(rhsNode->DeviceItem, PhDevicePropertyName);

    return PhCompareStringWithNull(lhs->AsString, rhs->AsString, TRUE);
}

static int __cdecl DeviceNodeSortFunction(
    const void* Left,
    const void* Right
    )
{
    PDEVICE_NODE lhsItem;
    PDEVICE_NODE rhsItem;

    lhsItem = *(PDEVICE_NODE*)Left;
    rhsItem = *(PDEVICE_NODE*)Right;

    return uintcmp(lhsItem->DeviceItem->InstanceIdHash, rhsItem->DeviceItem->InstanceIdHash);
}

static int __cdecl DeviceNodeSearchFunction(
    const void* Hash,
    const void* Item
    )
{
    PDEVICE_NODE item;

    item = *(PDEVICE_NODE*)Item;

    return uintcmp(PtrToUlong(Hash), item->DeviceItem->InstanceIdHash);
}

_Success_(return != NULL)
_Must_inspect_result_
PDEVICE_NODE DeviceTreeLookupNode(
    _In_ PDEVICE_TREE Tree,
    _In_ ULONG InstanceIdHash
    )
{
    PDEVICE_NODE* deviceItem;

    deviceItem = bsearch(
        UlongToPtr(InstanceIdHash),
        Tree->Nodes->Items,
        Tree->Nodes->Count,
        sizeof(PVOID),
        DeviceNodeSearchFunction
        );

    return deviceItem ? *deviceItem : NULL;
}

BOOLEAN DeviceTreeShouldIncludeDeviceItem(
    _In_ PPH_DEVICE_ITEM DeviceItem
    )
{
    if (DeviceItem->DeviceInterface)
    {
        if (!ShowDeviceInterfaces)
            return FALSE;

        if (ShowDisabledDeviceInterfaces)
            return TRUE;

        return PhGetDeviceProperty(DeviceItem, PhDevicePropertyInterfaceEnabled)->Boolean;
    }
    else
    {
        if (ShowDisconnected)
            return TRUE;

        if (!ShowSoftwareComponents && IsEqualGUID(&DeviceItem->ClassGuid, &GUID_DEVCLASS_SOFTWARECOMPONENT))
            return FALSE;

        return PhGetDeviceProperty(DeviceItem, PhDevicePropertyIsPresent)->Boolean;
    }
}

BOOLEAN DeviceTreeIsJustArrivedDeviceItem(
    _In_ PPH_DEVICE_ITEM DeviceItem
    )
{
    LARGE_INTEGER lastArrival;
    LARGE_INTEGER systemTime;
    LARGE_INTEGER elapsed;

    lastArrival = PhGetDeviceProperty(DeviceItem, PhDevicePropertyLastArrivalDate)->TimeStamp;

    if (lastArrival.QuadPart <= 0)
        return FALSE;

    PhQuerySystemTime(&systemTime);

    elapsed.QuadPart = systemTime.QuadPart - lastArrival.QuadPart;

    // convert to milliseconds
    elapsed.QuadPart /= 10000;

    // consider devices that arrived in that last 10 seconds as "just arrived"
    if (elapsed.QuadPart < (10 * 1000))
    {
        return TRUE;
    }

    return FALSE;
}

PDEVICE_NODE DeviceTreeCreateNode(
    _In_ PPH_DEVICE_ITEM Item,
    _Inout_ PPH_LIST Nodes
    )
{
    PDEVICE_NODE node;
    HICON iconHandle;

    node = PhAllocateZero(sizeof(DEVICE_NODE));
    PhInitializeTreeNewNode(&node->Node);
    node->Node.TextCache = node->TextCache;
    node->Node.TextCacheSize = RTL_NUMBER_OF(node->TextCache);

    node->DeviceItem = Item;
    iconHandle = PhGetDeviceIcon(Item, &DeviceIconSize);
    if (iconHandle)
    {
        node->IconIndex = PhImageListAddIcon(DeviceImageList, iconHandle);
        DestroyIcon(iconHandle);
    }
    else
    {
        node->IconIndex = 0; // Must be set to zero (dmex)
    }

    if (DeviceTreeFilterSupport.NodeList)
        node->Node.Visible = PhApplyTreeNewFiltersToNode(&DeviceTreeFilterSupport, &node->Node);
    else
        node->Node.Visible = TRUE;

    node->Children = PhCreateList(Item->ChildrenCount);
    for (PPH_DEVICE_ITEM item = Item->Child; item; item = item->Sibling)
    {
        if (DeviceTreeShouldIncludeDeviceItem(item))
            PhAddItemList(node->Children, DeviceTreeCreateNode(item, Nodes));
    }

    if (SortNameDevices)
    {
        qsort(node->Children->Items, node->Children->Count, sizeof(PVOID), DeviceListSortByNameFunction);
    }

    PhAddItemList(Nodes, node);
    return node;
}

PDEVICE_TREE DeviceTreeCreate(
    _In_ PPH_DEVICE_TREE Tree
    )
{
    PDEVICE_TREE tree;

    PhTrace("Creating device tree...");

    tree = PhCreateObject(sizeof(DEVICE_TREE), DeviceTreeType);
    tree->Nodes = PhCreateList(Tree->DeviceList->AllocatedCount);

    if (ShowDeviceRootNode)
    {
        tree->Roots = PhCreateList(1);
        PhAddItemList(tree->Roots, DeviceTreeCreateNode(Tree->Root, tree->Nodes));
    }
    else
    {
        tree->Roots = PhCreateList(Tree->Root->ChildrenCount);
        for (PPH_DEVICE_ITEM item = Tree->Root->Child; item; item = item->Sibling)
        {
            if (DeviceTreeShouldIncludeDeviceItem(item))
                PhAddItemList(tree->Roots, DeviceTreeCreateNode(item, tree->Nodes));
        }

        if (SortNameDevices)
        {
            qsort(tree->Roots->Items, tree->Roots->Count, sizeof(PVOID), DeviceListSortByNameFunction);
        }
    }

    qsort(tree->Nodes->Items, tree->Nodes->Count, sizeof(PVOID), DeviceNodeSortFunction);

    tree->Tree = PhReferenceObject(Tree);

    PhTrace("Created device tree with %lu nodes", tree->Nodes->Count);

    return tree;
}

_Function_class_(PH_TYPE_DELETE_PROCEDURE)
VOID DeviceTreeDeleteProcedure(
    _In_ PVOID Object,
    _In_ ULONG Flags
    )
{
    PDEVICE_TREE tree = Object;

    for (ULONG i = 0; i < tree->Nodes->Count; i++)
    {
        PDEVICE_NODE node = tree->Nodes->Items[i];
        PhDereferenceObject(node->Children);
        PhFree(node);
    }

    PhDereferenceObject(tree->Nodes);
    PhDereferenceObject(tree->Roots);
    PhDereferenceObject(tree->Tree);
}

_Must_inspect_impl_
_Success_(return != NULL)
PDEVICE_TREE DeviceTreeCreateIfNecessary(
    _In_ BOOLEAN Force
    )
{
    PDEVICE_TREE deviceTree;
    PPH_DEVICE_TREE tree;

    tree = PhReferenceDeviceTreeEx(Force);
    if (Force || !DeviceTree || DeviceTree->Tree != tree)
    {
        deviceTree = DeviceTreeCreate(tree);
    }
    else
    {
        // the device tree hasn't changed, no need to create a new one
        deviceTree = NULL;
    }

    PhDereferenceObject(tree);

    return deviceTree;
}

VOID NTAPI DeviceTreePublish(
    _In_opt_ PDEVICE_TREE Tree
    )
{
    PDEVICE_TREE oldTree;

    if (!Tree)
        return;

    TreeNew_SetRedraw(DeviceTreeHandle, FALSE);

    oldTree = DeviceTree;
    DeviceTree = Tree;
    DeviceFilterList.AllocatedCount = DeviceTree->Nodes->AllocatedCount;
    DeviceFilterList.Count = DeviceTree->Nodes->Count;
    DeviceFilterList.Items = DeviceTree->Nodes->Items;

    if (oldTree)
    {
        // TODO PhClearPointerList
        PhMoveReference(&DeviceNodeStateList, NULL);

        for (ULONG i = 0; i < DeviceTree->Nodes->Count; i++)
        {
            PDEVICE_NODE node = DeviceTree->Nodes->Items[i];
            PDEVICE_NODE old = DeviceTreeLookupNode(oldTree, node->DeviceItem->InstanceIdHash);

            if (old)
            {
                node->Node.Selected = old->Node.Selected;
            }

            if (DeviceTreeIsJustArrivedDeviceItem(node->DeviceItem))
            {
                PhChangeShStateTn(
                    &node->Node,
                    &node->ShState,
                    &DeviceNodeStateList,
                    NewItemState,
                    DeviceArrivedColor,
                    NULL
                    );
            }
        }
    }

    TreeNew_SetRedraw(DeviceTreeHandle, TRUE);

    if (DeviceTreeFilterSupport.FilterList)
        PhApplyTreeNewFilters(&DeviceTreeFilterSupport);
    else
        TreeNew_NodesStructured(DeviceTreeHandle);

    PhClearReference(&oldTree);
}

_Function_class_(USER_THREAD_START_ROUTINE)
NTSTATUS NTAPI DeviceTreePublishThread(
    _In_ PVOID Parameter
    )
{
    BOOLEAN force = PtrToUlong(Parameter) ? TRUE : FALSE;

    SystemInformer_Invoke(DeviceTreePublish, DeviceTreeCreateIfNecessary(force));

    return STATUS_SUCCESS;
}

VOID DeviceTreePublishAsync(
    _In_ BOOLEAN Force
    )
{
    PhCreateThread2(DeviceTreePublishThread, ULongToPtr(Force ? 1ul : 0ul));
}

VOID InvalidateDeviceNodes(
    VOID
    )
{
    if (!DeviceTree)
        return;

    for (ULONG i = 0; i < DeviceTree->Nodes->Count; i++)
    {
        PDEVICE_NODE node;

        node = DeviceTree->Nodes->Items[i];

        PhInvalidateTreeNewNode(&node->Node, TN_CACHE_COLOR);
        TreeNew_InvalidateNode(DeviceTreeHandle, &node->Node);
    }
}

_Function_class_(PH_TN_FILTER_FUNCTION)
BOOLEAN NTAPI DeviceTreeFilterCallback(
    _In_ PPH_TREENEW_NODE Node,
    _In_opt_ PVOID Context
    )
{
    PDEVICE_NODE node = (PDEVICE_NODE)Node;

    if (!ToolStatusInterface->GetSearchMatchHandle())
        return TRUE;

    for (ULONG i = 0; i < ARRAYSIZE(node->DeviceItem->Properties); i++)
    {
        PPH_DEVICE_PROPERTY prop;

        if (!DeviceTreeVisibleColumns[i])
            continue;

        prop = PhGetDeviceProperty(node->DeviceItem, i);

        if (PhIsNullOrEmptyString(prop->AsString))
            continue;

        if (ToolStatusInterface->WordMatch(&prop->AsString->sr))
            return TRUE;
    }

    return FALSE;
}

_Function_class_(PH_CALLBACK_FUNCTION)
VOID NTAPI DeviceTreeSearchChangedHandler(
    _In_opt_ PVOID Parameter,
    _In_opt_ PVOID Context
    )
{
    if (DeviceTabSelected)
        PhApplyTreeNewFilters(&DeviceTreeFilterSupport);
}

static int __cdecl DeviceTreeSortFunction(
    void* Context,
    const void* Left,
    const void* Right
    )
{
    PDEVICE_TREE_SORT_CONTEXT context = Context;
    int sortResult;
    PDEVICE_NODE lhsNode;
    PDEVICE_NODE rhsNode;
    PPH_DEVICE_PROPERTY lhs;
    PPH_DEVICE_PROPERTY rhs;
    PH_STRINGREF srl;
    PH_STRINGREF srr;

    sortResult = 0;
    lhsNode = *(PDEVICE_NODE*)Left;
    rhsNode = *(PDEVICE_NODE*)Right;
    lhs = PhGetDeviceProperty(lhsNode->DeviceItem, context->SortColumn);
    rhs = PhGetDeviceProperty(rhsNode->DeviceItem, context->SortColumn);

    assert(lhs->Type == rhs->Type);

    if (!lhs->Valid && !rhs->Valid)
    {
        sortResult = 0;
    }
    else if (lhs->Valid && !rhs->Valid)
    {
        sortResult = 1;
    }
    else if (!lhs->Valid && rhs->Valid)
    {
        sortResult = -1;
    }
    else
    {
        switch (lhs->Type)
        {
        case PhDevicePropertyTypeString:
            sortResult = PhCompareString(lhs->String, rhs->String, TRUE);
            break;
        case PhDevicePropertyTypeUInt64:
            sortResult = uint64cmp(lhs->UInt64, rhs->UInt64);
            break;
        case PhDevicePropertyTypeInt64:
            sortResult = int64cmp(lhs->Int64, rhs->Int64);
            break;
        case PhDevicePropertyTypeUInt32:
            sortResult = uint64cmp(lhs->UInt32, rhs->UInt32);
            break;
        case PhDevicePropertyTypeInt32:
        case PhDevicePropertyTypeNTSTATUS:
            sortResult = int64cmp(lhs->Int32, rhs->Int32);
            break;
        case PhDevicePropertyTypeGUID:
            sortResult = memcmp(&lhs->Guid, &rhs->Guid, sizeof(GUID));
            break;
        case PhDevicePropertyTypeBoolean:
            {
                if (lhs->Boolean && !rhs->Boolean)
                    sortResult = 1;
                else if (!lhs->Boolean && rhs->Boolean)
                    sortResult = -1;
                else
                    sortResult = 0;
            }
            break;
        case PhDevicePropertyTypeTimeStamp:
            sortResult = int64cmp(lhs->TimeStamp.QuadPart, rhs->TimeStamp.QuadPart);
            break;
        case PhDevicePropertyTypeStringList:
            {
                srl = PhGetStringRef(lhs->AsString);
                srr = PhGetStringRef(rhs->AsString);
                sortResult = PhCompareStringRef(&srl, &srr, TRUE);
            }
            break;
        case PhDevicePropertyTypeBinary:
            {
                sortResult = memcmp(lhs->Binary.Buffer, rhs->Binary.Buffer, min(lhs->Binary.Size, rhs->Binary.Size));
                if (sortResult == 0)
                    sortResult = uint64cmp(lhs->Binary.Size, rhs->Binary.Size);
            }
            break;
        default:
            assert(FALSE);
        }
    }

    if (sortResult == 0)
    {
        srl = PhGetStringRef(lhsNode->DeviceItem->Properties[PhDevicePropertyName].AsString);
        srr = PhGetStringRef(rhsNode->DeviceItem->Properties[PhDevicePropertyName].AsString);
        sortResult = PhCompareStringRef(&srl, &srr, TRUE);
    }

    return PhModifySort(sortResult, context->SortOrder);
}

VOID DeviceNodeShowProperties(
    _In_ HWND ParentWindowHandle,
    _In_ PDEVICE_NODE DeviceNode
    )
{
    PPH_DEVICE_ITEM deviceItem;

    if (DeviceNode->DeviceItem->DeviceInterface)
        deviceItem = DeviceNode->DeviceItem->Parent;
    else
        deviceItem = DeviceNode->DeviceItem;

    if (deviceItem->InstanceId)
        DeviceShowProperties(ParentWindowHandle, deviceItem);
}

VOID DeviceTreeGetSelectedDeviceItems(
    _Out_ PPH_DEVICE_ITEM** Devices,
    _Out_ PULONG NumberOfDevices
    )
{
    PH_ARRAY array;

    PhInitializeArray(&array, sizeof(PVOID), 2);

    for (ULONG i = 0; i < DeviceTree->Nodes->Count; i++)
    {
        PDEVICE_NODE node = DeviceTree->Nodes->Items[i];

        if (node->Node.Visible && node->Node.Selected)
            PhAddItemArray(&array, &node->DeviceItem);
    }

    *NumberOfDevices = (ULONG)array.Count;
    *Devices = PhFinalArrayItems(&array);
}

VOID DevicesExpandAllNodes(
    _In_ BOOLEAN Expand
    )
{
    BOOLEAN needsRestructure = FALSE;

    if (!DeviceTree)
        return;

    for (ULONG i = 0; i < DeviceTree->Nodes->Count; i++)
    {
        PDEVICE_NODE node = DeviceTree->Nodes->Items[i];

        if (node->Children->Count != 0 && node->Node.Expanded != Expand)
        {
            node->Node.Expanded = Expand;
            needsRestructure = TRUE;
        }
    }

    if (needsRestructure)
        TreeNew_NodesStructured(DeviceTreeHandle);
}

VOID DeviceTreeUpdateVisibleColumns(
    VOID
    )
{
    for (ULONG i = 0; i < PhMaxDeviceProperty; i++)
        DeviceTreeVisibleColumns[i] = i;

    TreeNew_GetVisibleColumnArray(
        DeviceTreeHandle,
        PhMaxDeviceProperty,
        DeviceTreeVisibleColumns
        );
}

BOOLEAN NTAPI DeviceTreeCallback(
    _In_ HWND hwnd,
    _In_ PH_TREENEW_MESSAGE Message,
    _In_ PVOID Parameter1,
    _In_ PVOID Parameter2,
    _In_ PVOID Context
    )
{
    PDEVICE_NODE node;

    switch (Message)
    {
    case TreeNewGetChildren:
        {
            PPH_TREENEW_GET_CHILDREN getChildren = Parameter1;

            if (!DeviceTree)
            {
                getChildren->Children = NULL;
                getChildren->NumberOfChildren = 0;
            }
            else
            {
                PPH_LIST sortList;
                DEVICE_TREE_SORT_CONTEXT sortContext;

                node = (PDEVICE_NODE)getChildren->Node;
                sortList = NULL;
                sortContext.SortColumn = DeviceTreeSortColumn;
                sortContext.SortOrder = DeviceTreeSortOrder;

                if (SortChildDevices)
                {
                    if (!node)
                    {
                        getChildren->Children = (PPH_TREENEW_NODE*)DeviceTree->Roots->Items;
                        getChildren->NumberOfChildren = DeviceTree->Roots->Count;
                        if (SortRootDevices)
                            sortList = DeviceTree->Roots;
                    }
                    else if (sortContext.SortOrder == NoSortOrder)
                    {
                        getChildren->Children = (PPH_TREENEW_NODE*)node->Children->Items;
                        getChildren->NumberOfChildren = node->Children->Count;
                        sortList = node->Children;
                        sortContext.SortColumn = PhDevicePropertyName;
                        sortContext.SortOrder = AscendingSortOrder;
                    }
                    else
                    {
                        getChildren->Children = (PPH_TREENEW_NODE*)node->Children->Items;
                        getChildren->NumberOfChildren = node->Children->Count;
                        sortList = node->Children;
                    }
                }
                else
                {
                    if (DeviceTreeSortOrder == NoSortOrder)
                    {
                        if (!node)
                        {
                            getChildren->Children = (PPH_TREENEW_NODE*)DeviceTree->Roots->Items;
                            getChildren->NumberOfChildren = DeviceTree->Roots->Count;
                            if (SortRootDevices)
                                sortList = DeviceTree->Roots;
                        }
                        else
                        {
                            getChildren->Children = (PPH_TREENEW_NODE*)node->Children->Items;
                            getChildren->NumberOfChildren = node->Children->Count;
                        }
                    }
                    else
                    {
                        getChildren->Children = (PPH_TREENEW_NODE*)DeviceTree->Nodes->Items;
                        getChildren->NumberOfChildren = DeviceTree->Nodes->Count;
                        sortList = DeviceTree->Nodes;
                    }
                }

                if (sortList)
                {
                    if (sortContext.SortColumn < PhMaxDeviceProperty)
                    {
                        qsort_s(
                            sortList->Items,
                            sortList->Count,
                            sizeof(PVOID),
                            DeviceTreeSortFunction,
                            &sortContext
                            );
                    }
                }
            }
        }
        return TRUE;
    case TreeNewIsLeaf:
        {
            PPH_TREENEW_IS_LEAF isLeaf = Parameter1;
            node = (PDEVICE_NODE)isLeaf->Node;

            if (SortChildDevices || DeviceTreeSortOrder == NoSortOrder)
                isLeaf->IsLeaf = node->Children->Count == 0;
            else
                isLeaf->IsLeaf = TRUE;
        }
        return TRUE;
    case TreeNewGetCellText:
        {
            PPH_TREENEW_GET_CELL_TEXT getCellText = Parameter1;
            node = (PDEVICE_NODE)getCellText->Node;

            PPH_STRING text = PhGetDeviceProperty(node->DeviceItem, getCellText->Id)->AsString;

            getCellText->Text = PhGetStringRef(text);
            getCellText->Flags = TN_CACHE;
        }
        return TRUE;
    case TreeNewGetNodeColor:
        {
            PPH_TREENEW_GET_NODE_COLOR getNodeColor = Parameter1;
            node = (PDEVICE_NODE)getNodeColor->Node;

            getNodeColor->Flags = TN_CACHE | TN_AUTO_FORECOLOR;

            if (node->DeviceItem->DeviceInterface)
            {
                if (PhGetDeviceProperty(node->DeviceItem, PhDevicePropertyInterfaceEnabled)->Boolean)
                    getNodeColor->BackColor = DeviceInterfaceColor;
                else
                    getNodeColor->BackColor = DeviceDisabledInterfaceColor;
            }
            else if (node->DeviceItem->DevNodeStatus & DN_HAS_PROBLEM && (node->DeviceItem->ProblemCode != CM_PROB_DISABLED))
            {
                getNodeColor->BackColor = DeviceProblemColor;
            }
            else if (!PhGetDeviceProperty(node->DeviceItem, PhDevicePropertyIsPresent)->Boolean)
            {
                getNodeColor->BackColor = DeviceDisconnectedColor;
            }
            else if ((node->DeviceItem->Capabilities & CM_DEVCAP_HARDWAREDISABLED) || (node->DeviceItem->ProblemCode == CM_PROB_DISABLED))
            {
                getNodeColor->BackColor = DeviceDisabledColor;
            }
            else if ((HighlightUpperFiltered && node->DeviceItem->HasUpperFilters) || (HighlightLowerFiltered && node->DeviceItem->HasLowerFilters))
            {
                getNodeColor->BackColor = DeviceHighlightColor;
            }
        }
        return TRUE;
    case TreeNewGetNodeIcon:
        {
            PPH_TREENEW_GET_NODE_ICON getNodeIcon = Parameter1;

            node = (PDEVICE_NODE)getNodeIcon->Node;
            getNodeIcon->Icon = (HICON)(ULONG_PTR)node->IconIndex;
        }
        return TRUE;
    case TreeNewSortChanged:
        {
            PPH_TREENEW_SORT_CHANGED_EVENT sorting = Parameter1;

            DeviceTreeSortColumn = sorting->SortColumn;
            DeviceTreeSortOrder = sorting->SortOrder;

            if (DeviceTreeFilterSupport.FilterList)
                PhApplyTreeNewFilters(&DeviceTreeFilterSupport);
            else
                TreeNew_NodesStructured(hwnd);
        }
        return TRUE;
    case TreeNewContextMenu:
        {
            PDEVICE_TREE activeTree;
            PPH_DEVICE_ITEM* devices;
            ULONG numberOfDevices;
            PPH_TREENEW_CONTEXT_MENU contextMenuEvent = Parameter1;
            PPH_EMENU menu;
            PPH_EMENU subMenu;
            PPH_EMENU_ITEM selectedItem;
            PPH_EMENU_ITEM gotoServiceItem;
            PPH_EMENU_ITEM enable;
            PPH_EMENU_ITEM disable;
            PPH_EMENU_ITEM restart;
            PPH_EMENU_ITEM uninstall;
            PPH_EMENU_ITEM properties;
            BOOLEAN republish;

            // We muse reference the active tree here since a new tree could be
            // published on the UI thread after we show the context menu.
            activeTree = PhReferenceObject(DeviceTree);

            DeviceTreeGetSelectedDeviceItems(&devices, &numberOfDevices);

            node = (PDEVICE_NODE)contextMenuEvent->Node;

            menu = PhCreateEMenu();
            PhInsertEMenuItem(menu, gotoServiceItem = PhCreateEMenuItem(0, 108, HardwareDevicesGetUiString(IDS_HD_MENU_GO_TO_SERVICE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuItem(0, ID_DEVICE_SEARCH_ONLINE, HardwareDevicesGetUiString(IDS_HD_MENU_SEARCH_ONLINE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuItem(0, ID_DEVICE_SEARCH_DRIVER_UPDATE, HardwareDevicesGetUiString(IDS_HD_MENU_SEARCH_DRIVER_UPDATE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            PhInsertEMenuItem(menu, enable = PhCreateEMenuItem(0, 0, HardwareDevicesGetUiString(IDS_HD_MENU_ENABLE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, disable = PhCreateEMenuItem(0, 1, HardwareDevicesGetUiString(IDS_HD_MENU_DISABLE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, restart = PhCreateEMenuItem(0, 2, HardwareDevicesGetUiString(IDS_HD_MENU_RESTART), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, uninstall = PhCreateEMenuItem(0, 3, HardwareDevicesGetUiString(IDS_HD_MENU_UNINSTALL), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            subMenu = PhCreateEMenuItem(0, 0, HardwareDevicesGetUiString(IDS_HD_MENU_OPEN_KEY), NULL, NULL);
            PhInsertEMenuItem(subMenu, PhCreateEMenuItem(0, HW_KEY_INDEX_HARDWARE, HardwareDevicesGetUiString(IDS_HD_MENU_HARDWARE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(subMenu, PhCreateEMenuItem(0, HW_KEY_INDEX_SOFTWARE, HardwareDevicesGetUiString(IDS_HD_MENU_SOFTWARE), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(subMenu, PhCreateEMenuItem(0, HW_KEY_INDEX_USER, HardwareDevicesGetUiString(IDS_HD_MENU_USER), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(subMenu, PhCreateEMenuItem(0, HW_KEY_INDEX_CONFIG, HardwareDevicesGetUiString(IDS_HD_MENU_CONFIG), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, subMenu, ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            PhInsertEMenuItem(menu, properties = PhCreateEMenuItem(0, 10, HardwareDevicesGetUiString(IDS_HD_MENU_PROPERTIES), NULL, NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuItem(0, 11, HardwareDevicesGetUiString(IDS_HD_MENU_COPY), NULL, NULL), ULONG_MAX);
            PhInsertCopyCellEMenuItem(menu, 11, DeviceTreeHandle, contextMenuEvent->Column);
            PhSetFlagsEMenuItem(menu, 10, PH_EMENU_DEFAULT, PH_EMENU_DEFAULT);

            if (!node || numberOfDevices != 1)
            {
                PhSetDisabledEMenuItem(gotoServiceItem);
                PhSetDisabledEMenuItem(subMenu);
                PhSetDisabledEMenuItem(properties);
            }
            else
            {
                PPH_STRING serviceName = PhGetDeviceProperty(node->DeviceItem, PhDevicePropertyService)->AsString;
                if (PhIsNullOrEmptyString(serviceName))
                    PhSetDisabledEMenuItem(gotoServiceItem);
            }

            if (!PhGetOwnTokenAttributes().Elevated)
            {
                PhSetDisabledEMenuItem(enable);
                PhSetDisabledEMenuItem(disable);
                PhSetDisabledEMenuItem(restart);
                PhSetDisabledEMenuItem(uninstall);
            }

            selectedItem = PhShowEMenu(
                menu,
                SystemInformer_GetWindowHandle(),
                PH_EMENU_SHOW_LEFTRIGHT,
                PH_ALIGN_LEFT | PH_ALIGN_TOP,
                contextMenuEvent->Location.x,
                contextMenuEvent->Location.y
                );

            republish = FALSE;

            if (selectedItem && selectedItem->Id != ULONG_MAX)
            {
                if (!PhHandleCopyCellEMenuItem(selectedItem))
                {
                    switch (selectedItem->Id)
                    {
                    case 0:
                    case 1:
                        {
                            for (ULONG i = 0; i < numberOfDevices; i++)
                            {
                                if (devices[i]->InstanceId)
                                    republish |= HardwareDeviceEnableDisable(hwnd, devices[i]->InstanceId, selectedItem->Id == 0);
                            }
                        }
                        break;
                    case 2:
                        {
                            for (ULONG i = 0; i < numberOfDevices; i++)
                            {
                                if (devices[i]->InstanceId)
                                    republish |= HardwareDeviceRestart(hwnd, devices[i]->InstanceId);
                            }
                        }
                        break;
                    case 3:
                        {
                            for (ULONG i = 0; i < numberOfDevices; i++)
                            {
                                if (devices[i]->InstanceId)
                                    republish |= HardwareDeviceUninstall(hwnd, devices[i]->InstanceId);
                            }
                        }
                        break;
                    case ID_DEVICE_SEARCH_ONLINE:
                    case ID_DEVICE_SEARCH_DRIVER_UPDATE:
                        {
                            PPH_DEVICE_ITEM deviceItem;

                            if (node->DeviceItem->DeviceInterface)
                                deviceItem = node->DeviceItem->Parent;
                            else
                                deviceItem = node->DeviceItem;

                            if (deviceItem)
                            {
                                PPH_DEVICE_PROPERTY deviceId = PhGetDeviceProperty(deviceItem, PhDevicePropertyMatchingDeviceId);
                                PPH_STRING searchId = NULL;
                                if (deviceId->Valid && !PhIsNullOrEmptyString(deviceId->String))
                                    searchId = deviceId->String;
                                else
                                    searchId = deviceItem->InstanceId;

                                if (searchId)
                                {
                                    if (selectedItem->Id == ID_DEVICE_SEARCH_ONLINE)
                                    {
                                        PhSearchOnlineString(hwnd, PhGetString(searchId));
                                    }
                                    else
                                    {
                                        PPH_STRING encodedId = PhpEncodeDeviceQuery(searchId);
                                        PPH_STRING url = PhFormatString(L"https://www.catalog.update.microsoft.com/search.aspx?q=%s", PhGetString(encodedId));
                                        PhShellExecute(hwnd, PhGetString(url), NULL);
                                        PhDereferenceObject(url);
                                        PhDereferenceObject(encodedId);
                                    }
                                }
                            }
                        }
                        break;
                    case HW_KEY_INDEX_HARDWARE:
                    case HW_KEY_INDEX_SOFTWARE:
                    case HW_KEY_INDEX_USER:
                    case HW_KEY_INDEX_CONFIG:
                        if (node->DeviceItem->InstanceId)
                            HardwareDeviceOpenKey(hwnd, node->DeviceItem->InstanceId, selectedItem->Id);
                        break;
                    case 10:
                        DeviceNodeShowProperties(hwnd, node);
                        break;
                    case 11:
                        {
                            PPH_STRING text;

                            text = PhGetTreeNewText(DeviceTreeHandle, 0);
                            PhSetClipboardString(DeviceTreeHandle, &text->sr);
                            PhDereferenceObject(text);
                        }
                        break;
                    case 108:
                        {
                            PPH_STRING serviceName = PhGetDeviceProperty(node->DeviceItem, PhDevicePropertyService)->AsString;
                            PPH_SERVICE_ITEM serviceItem;

                            if (!PhIsNullOrEmptyString(serviceName))
                            {
                                if (serviceItem = PhReferenceServiceItem(&serviceName->sr))
                                {
                                    SystemInformer_SelectTabPage(1);
                                    SystemInformer_SelectServiceItem(serviceItem);
                                    PhDereferenceObject(serviceItem);
                                }
                            }
                        }
                        break;
                    }
                }
            }

            PhDestroyEMenu(menu);

            if (republish)
                DeviceTreePublishAsync(TRUE);

            PhFree(devices);
            PhDereferenceObject(activeTree);
        }
        return TRUE;
    case TreeNewLeftDoubleClick:
        {
            PPH_TREENEW_MOUSE_EVENT mouseEvent = Parameter1;
            node = (PDEVICE_NODE)mouseEvent->Node;

            if (node)
                DeviceNodeShowProperties(hwnd, node);
        }
        return TRUE;
    case TreeNewHeaderRightClick:
        {
            PH_TN_COLUMN_MENU_DATA data;

            data.TreeNewHandle = hwnd;
            data.MouseEvent = Parameter1;
            data.DefaultSortColumn = 0;
            data.DefaultSortOrder = NoSortOrder;
            PhInitializeTreeNewColumnMenuEx(&data, PH_TN_COLUMN_MENU_SHOW_RESET_SORT);

            data.Selection = PhShowEMenu(
                data.Menu,
                hwnd,
                PH_EMENU_SHOW_LEFTRIGHT,
                PH_ALIGN_LEFT | PH_ALIGN_TOP,
                data.MouseEvent->ScreenLocation.x,
                data.MouseEvent->ScreenLocation.y
                );
            PhHandleTreeNewColumnMenu(&data);
            PhDeleteTreeNewColumnMenu(&data);
            DeviceTreeUpdateVisibleColumns();
        }
        return TRUE;
    }

    return FALSE;
}

VOID DevicesTreeLoadSettings(
    _In_ HWND TreeNewHandle
    )
{
    PPH_STRING settings;
    PH_INTEGER_PAIR sortSettings;

    settings = PhGetStringSetting(SETTING_NAME_DEVICE_TREE_COLUMNS);
    sortSettings = PhGetIntegerPairSetting(SETTING_NAME_DEVICE_TREE_SORT);
    PhCmLoadSettings(TreeNewHandle, &settings->sr);
    TreeNew_SetSort(TreeNewHandle, (ULONG)sortSettings.X, (ULONG)sortSettings.Y);
    PhDereferenceObject(settings);
}

VOID DevicesTreeSaveSettings(
    VOID
    )
{
    PPH_STRING settings;
    PH_INTEGER_PAIR sortSettings;
    ULONG sortColumn;
    ULONG sortOrder;

    if (!DeviceTabCreated)
        return;

    settings = PhCmSaveSettings(DeviceTreeHandle);
    TreeNew_GetSort(DeviceTreeHandle, &sortColumn, &sortOrder);
    sortSettings.X = sortColumn;
    sortSettings.Y = sortOrder;
    PhSetStringSetting2(SETTING_NAME_DEVICE_TREE_COLUMNS, &settings->sr);
    PhSetIntegerPairSetting(SETTING_NAME_DEVICE_TREE_SORT, sortSettings);
    PhDereferenceObject(settings);
}

VOID DevicesTreeImageListInitialize(
    _In_ HWND TreeNewHandle
    )
{
    LONG dpi;

    dpi = PhGetWindowDpi(TreeNewHandle);
    DeviceIconSize.X = PhGetSystemMetrics(SM_CXSMICON, dpi);
    DeviceIconSize.Y = PhGetSystemMetrics(SM_CYSMICON, dpi);

    if (DeviceImageList)
    {
        PhImageListSetIconSize(DeviceImageList, DeviceIconSize.X, DeviceIconSize.Y);
    }
    else
    {
        DeviceImageList = PhImageListCreate(
            DeviceIconSize.X,
            DeviceIconSize.Y,
            ILC_MASK | ILC_COLOR32,
            200,
            100
            );
    }

    if (DeviceImageList)
    {
        PhImageListAddIcon(DeviceImageList, PhGetApplicationIcon(TRUE, dpi));

        TreeNew_SetImageList(DeviceTreeHandle, DeviceImageList);
    }
}

const DEVICE_PROPERTY_TABLE_ENTRY DeviceItemPropertyTable[] =
{
    { PhDevicePropertyName, IDS_HD_NAME, L"Name", TRUE, 400, 0 },
    { PhDevicePropertyManufacturer, IDS_HD_DEVICE_PROPERTY_MANUFACTURER, L"Manufacturer", TRUE, 180, 0 },
    { PhDevicePropertyService, IDS_HD_SERVICE, L"Service", TRUE, 120, 0 },
    { PhDevicePropertyClass, IDS_HD_GROUP_CLASS, L"Class", TRUE, 120, 0 },
    { PhDevicePropertyEnumeratorName, IDS_HD_ENUMERATOR, L"Enumerator", TRUE, 80, 0 },
    { PhDevicePropertyInstallDate, IDS_HD_INSTALLED, L"Installed", TRUE, 160, 0 },

    { PhDevicePropertyFirstInstallDate, IDS_HD_FIRST_INSTALLED, L"First installed", FALSE, 160, 0 },
    { PhDevicePropertyLastArrivalDate, IDS_HD_LAST_ARRIVAL, L"Last arrival", FALSE, 160, 0 },
    { PhDevicePropertyLastRemovalDate, IDS_HD_LAST_REMOVAL, L"Last removal", FALSE, 160, 0 },
    { PhDevicePropertyDeviceDesc, IDS_HD_DESCRIPTION, L"Description", FALSE, 280, 0 },
    { PhDevicePropertyFriendlyName, IDS_HD_DEVICE_PROPERTY_FRIENDLY_NAME, L"Friendly name", FALSE, 220, 0 },
    { PhDevicePropertyInstanceId, IDS_HD_INSTANCE_ID, L"Instance ID", FALSE, 240, DT_PATH_ELLIPSIS },
    { PhDevicePropertyParentInstanceId, IDS_HD_PARENT_INSTANCE_ID, L"Parent instance ID", FALSE, 240, DT_PATH_ELLIPSIS },
    { PhDevicePropertyPDOName, IDS_HD_PDO_NAME, L"PDO name", FALSE, 180, DT_PATH_ELLIPSIS },
    { PhDevicePropertyLocationInfo, IDS_HD_LOCATION_INFO, L"Location info", FALSE, 180, DT_PATH_ELLIPSIS },
    { PhDevicePropertyClassGuid, IDS_HD_DEVICE_PROPERTY_CLASS_GUID, L"Class GUID", FALSE, 80, 0 },
    { PhDevicePropertyDriver, IDS_HD_DRIVER, L"Driver", FALSE, 180, DT_PATH_ELLIPSIS },
    { PhDevicePropertyDriverVersion, IDS_HD_DRIVER_VERSION, L"Driver version", FALSE, 80, 0 },
    { PhDevicePropertyDriverDate, IDS_HD_DRIVER_DATE, L"Driver date", FALSE, 80, 0 },
    { PhDevicePropertyFirmwareDate, IDS_HD_DEVICE_PROPERTY_FIRMWARE_DATE, L"Firmware date", FALSE, 80, 0 },
    { PhDevicePropertyFirmwareVersion, IDS_HD_DEVICE_PROPERTY_FIRMWARE_VERSION, L"Firmware version", FALSE, 80, 0 },
    { PhDevicePropertyFirmwareRevision, IDS_HD_DEVICE_PROPERTY_FIRMWARE_REVISION, L"Firmware revision", FALSE, 80, 0 },
    { PhDevicePropertyHasProblem, IDS_HD_DEVICE_PROPERTY_HAS_PROBLEM, L"Has problem", FALSE, 80, 0 },
    { PhDevicePropertyProblemCode, IDS_HD_PROBLEM_CODE, L"Problem code", FALSE, 80, 0 },
    { PhDevicePropertyProblemStatus, IDS_HD_PROBLEM_STATUS, L"Problem status", FALSE, 80, 0 },
    { PhDevicePropertyDevNodeStatus, IDS_HD_DEVICE_PROPERTY_DEV_NODE_STATUS, L"Node status flags", FALSE, 80, 0 },
    { PhDevicePropertyDevCapabilities, IDS_HD_DEVICE_PROPERTY_DEV_CAPABILITIES, L"Capabilities", FALSE, 80, 0 },
    { PhDevicePropertyUpperFilters, IDS_HD_DEVICE_PROPERTY_UPPER_FILTERS, L"Upper filters", FALSE, 80, 0 },
    { PhDevicePropertyLowerFilters, IDS_HD_DEVICE_PROPERTY_LOWER_FILTERS, L"Lower filters", FALSE, 80, 0 },
    { PhDevicePropertyHardwareIds, IDS_HD_HARDWARE_IDS, L"Hardware IDs", FALSE, 80, 0 },
    { PhDevicePropertyCompatibleIds, IDS_HD_DEVICE_PROPERTY_COMPATIBLE_IDS, L"Compatible IDs", FALSE, 80, 0 },
    { PhDevicePropertyConfigFlags, IDS_HD_DEVICE_PROPERTY_CONFIG_FLAGS, L"Configuration flags", FALSE, 80, 0 },
    { PhDevicePropertyUINumber, IDS_HD_DEVICE_PROPERTY_UI_NUMBER, L"Number", FALSE, 80, 0 },
    { PhDevicePropertyBusTypeGuid, IDS_HD_DEVICE_PROPERTY_BUS_TYPE_GUID, L"Bus type GUID", FALSE, 80, 0 },
    { PhDevicePropertyLegacyBusType, IDS_HD_DEVICE_PROPERTY_LEGACY_BUS_TYPE, L"Legacy bus type", FALSE, 80, 0 },
    { PhDevicePropertyBusNumber, IDS_HD_DEVICE_PROPERTY_BUS_NUMBER, L"Bus number", FALSE, 80, 0 },
    { PhDevicePropertySecurity, IDS_HD_DEVICE_PROPERTY_SECURITY, L"Security descriptor (binary)", FALSE, 80, 0 },
    { PhDevicePropertySecuritySDS, IDS_HD_SECURITY_DESCRIPTOR, L"Security descriptor", FALSE, 80, 0 },
    { PhDevicePropertyDevType, IDS_HD_DEVICE_PROPERTY_DEV_TYPE, L"Type", FALSE, 80, 0 },
    { PhDevicePropertyExclusive, IDS_HD_DEVICE_PROPERTY_EXCLUSIVE, L"Exclusive", FALSE, 80, 0 },
    { PhDevicePropertyCharacteristics, IDS_HD_DEVICE_PROPERTY_CHARACTERISTICS, L"Characteristics", FALSE, 80, 0 },
    { PhDevicePropertyAddress, IDS_HD_DEVICE_PROPERTY_ADDRESS, L"Address", FALSE, 80, 0 },
    { PhDevicePropertyPowerData, IDS_HD_DEVICE_PROPERTY_POWER_DATA, L"Power data", FALSE, 80, 0 },
    { PhDevicePropertyRemovalPolicy, IDS_HD_DEVICE_PROPERTY_REMOVAL_POLICY, L"Removal policy", FALSE, 80, 0 },
    { PhDevicePropertyRemovalPolicyDefault, IDS_HD_DEVICE_PROPERTY_REMOVAL_POLICY_DEFAULT, L"Removal policy default", FALSE, 80, 0 },
    { PhDevicePropertyRemovalPolicyOverride, IDS_HD_DEVICE_PROPERTY_REMOVAL_POLICY_OVERRIDE, L"Removal policy override", FALSE, 80, 0 },
    { PhDevicePropertyInstallState, IDS_HD_DEVICE_PROPERTY_INSTALL_STATE, L"Install state", FALSE, 80, 0 },
    { PhDevicePropertyLocationPaths, IDS_HD_LOCATION_PATHS, L"Location paths", FALSE, 80, 0 },
    { PhDevicePropertyBaseContainerId, IDS_HD_DEVICE_PROPERTY_BASE_CONTAINER_ID, L"Base container ID", FALSE, 80, 0 },
    { PhDevicePropertyEjectionRelations, IDS_HD_DEVICE_PROPERTY_EJECTION_RELATIONS, L"Ejection relations", FALSE, 80, 0 },
    { PhDevicePropertyRemovalRelations, IDS_HD_DEVICE_PROPERTY_REMOVAL_RELATIONS, L"Removal relations", FALSE, 80, 0 },
    { PhDevicePropertyPowerRelations, IDS_HD_DEVICE_PROPERTY_POWER_RELATIONS, L"Power relations", FALSE, 80, 0 },
    { PhDevicePropertyBusRelations, IDS_HD_DEVICE_PROPERTY_BUS_RELATIONS, L"Bus relations", FALSE, 80, 0 },
    { PhDevicePropertyChildren, IDS_HD_DEVICE_PROPERTY_CHILDREN, L"Children", FALSE, 80, 0 },
    { PhDevicePropertySiblings, IDS_HD_DEVICE_PROPERTY_SIBLINGS, L"Siblings", FALSE, 80, 0 },
    { PhDevicePropertyTransportRelations, IDS_HD_DEVICE_PROPERTY_TRANSPORT_RELATIONS, L"Transport relations", FALSE, 80, 0 },
    { PhDevicePropertyReported, IDS_HD_DEVICE_PROPERTY_REPORTED, L"Reported", FALSE, 80, 0 },
    { PhDevicePropertyLegacy, IDS_HD_DEVICE_PROPERTY_LEGACY, L"Legacy", FALSE, 80, 0 },
    { PhDevicePropertyContainerId, IDS_HD_DEVICE_PROPERTY_CONTAINER_ID, L"Container ID", FALSE, 80, 0 },
    { PhDevicePropertyInLocalMachineContainer, IDS_HD_DEVICE_PROPERTY_IN_LOCAL_MACHINE_CONTAINER, L"Local machine container", FALSE, 80, 0 },
    { PhDevicePropertyModel, IDS_HD_DEVICE_PROPERTY_MODEL, L"Model", FALSE, 80, 0 },
    { PhDevicePropertyModelId, IDS_HD_DEVICE_PROPERTY_MODEL_ID, L"Model ID", FALSE, 80, 0 },
    { PhDevicePropertyFriendlyNameAttributes, IDS_HD_DEVICE_PROPERTY_FRIENDLY_NAME_ATTRIBUTES, L"Friendly name attributes", FALSE, 80, 0 },
    { PhDevicePropertyManufacturerAttributes, IDS_HD_DEVICE_PROPERTY_MANUFACTURER_ATTRIBUTES, L"Manufacturer attributes", FALSE, 80, 0 },
    { PhDevicePropertyPresenceNotForDevice, IDS_HD_DEVICE_PROPERTY_PRESENCE_NOT_FOR_DEVICE, L"Presence not for device", FALSE, 80, 0 },
    { PhDevicePropertySignalStrength, IDS_HD_DEVICE_PROPERTY_SIGNAL_STRENGTH, L"Signal strength", FALSE, 80, 0 },
    { PhDevicePropertyIsAssociateableByUserAction, IDS_HD_DEVICE_PROPERTY_IS_ASSOCIATEABLE_BY_USER_ACTION, L"Associateable by user action", FALSE, 80, 0 },
    { PhDevicePropertyShowInUninstallUI, IDS_HD_DEVICE_PROPERTY_SHOW_IN_UNINSTALL_UI, L"Show uninstall UI", FALSE, 80, 0 },
    { PhDevicePropertyNumaProximityDomain, IDS_HD_DEVICE_PROPERTY_NUMA_PROXIMITY_DOMAIN, L"NUMA proximity domain", FALSE, 80, 0 },
    { PhDevicePropertyDHPRebalancePolicy, IDS_HD_DEVICE_PROPERTY_DHP_REBALANCE_POLICY, L"DHP rebalance policy", FALSE, 80, 0 },
    { PhDevicePropertyNumaNode, IDS_HD_DEVICE_PROPERTY_NUMA_NODE, L"NUMA node", FALSE, 80, 0 },
    { PhDevicePropertyBusReportedDeviceDesc, IDS_HD_DEVICE_PROPERTY_BUS_REPORTED_DEVICE_DESC, L"Bus reported description", FALSE, 80, 0 },
    { PhDevicePropertyIsPresent, IDS_HD_DEVICE_PROPERTY_IS_PRESENT, L"Present", FALSE, 80, 0 },
    { PhDevicePropertyConfigurationId, IDS_HD_DEVICE_PROPERTY_CONFIGURATION_ID, L"Configuration ID", FALSE, 80, 0 },
    { PhDevicePropertyReportedDeviceIdsHash, IDS_HD_DEVICE_PROPERTY_REPORTED_DEVICE_IDS_HASH, L"Reported IDs hash", FALSE, 80, 0 },
    { PhDevicePropertyPhysicalDeviceLocation, IDS_HD_DEVICE_PROPERTY_PHYSICAL_DEVICE_LOCATION, L"Physical location", FALSE, 80, 0 },
    { PhDevicePropertyBiosDeviceName, IDS_HD_DEVICE_PROPERTY_BIOS_DEVICE_NAME, L"BIOS name", FALSE, 80, 0 },
    { PhDevicePropertyDriverProblemDesc, IDS_HD_PROBLEM_DESCRIPTION, L"Problem description", FALSE, 80, 0 },
    { PhDevicePropertyDebuggerSafe, IDS_HD_DEVICE_PROPERTY_DEBUGGER_SAFE, L"Debugger safe", FALSE, 80, 0 },
    { PhDevicePropertyPostInstallInProgress, IDS_HD_DEVICE_PROPERTY_POST_INSTALL_IN_PROGRESS, L"Post install in progress", FALSE, 80, 0 },
    { PhDevicePropertyStack, IDS_HD_DEVICE_PROPERTY_STACK, L"Stack", FALSE, 80, 0 },
    { PhDevicePropertyExtendedConfigurationIds, IDS_HD_DEVICE_PROPERTY_EXTENDED_CONFIGURATION_IDS, L"Extended configuration IDs", FALSE, 80, 0 },
    { PhDevicePropertyIsRebootRequired, IDS_HD_DEVICE_PROPERTY_IS_REBOOT_REQUIRED, L"Reboot required", FALSE, 80, 0 },
    { PhDevicePropertyDependencyProviders, IDS_HD_DEVICE_PROPERTY_DEPENDENCY_PROVIDERS, L"Dependency providers", FALSE, 80, 0 },
    { PhDevicePropertyDependencyDependents, IDS_HD_DEVICE_PROPERTY_DEPENDENCY_DEPENDENTS, L"Dependency dependents", FALSE, 80, 0 },
    { PhDevicePropertySoftRestartSupported, IDS_HD_DEVICE_PROPERTY_SOFT_RESTART_SUPPORTED, L"Soft restart supported", FALSE, 80, 0 },
    { PhDevicePropertyExtendedAddress, IDS_HD_DEVICE_PROPERTY_EXTENDED_ADDRESS, L"Extended address", FALSE, 80, 0 },
    { PhDevicePropertyAssignedToGuest, IDS_HD_DEVICE_PROPERTY_ASSIGNED_TO_GUEST, L"Assigned to guest", FALSE, 80, 0 },
    { PhDevicePropertyCreatorProcessId, IDS_HD_DEVICE_PROPERTY_CREATOR_PROCESS_ID, L"Creator process ID", FALSE, 80, 0 },
    { PhDevicePropertyFirmwareVendor, IDS_HD_DEVICE_PROPERTY_FIRMWARE_VENDOR, L"Firmware vendor", FALSE, 80, 0 },
    { PhDevicePropertySessionId, IDS_HD_DEVICE_PROPERTY_SESSION_ID, L"Session ID", FALSE, 80, 0 },
    { PhDevicePropertyDriverDesc, IDS_HD_DRIVER_DESCRIPTION, L"Driver description", FALSE, 80, 0 },
    { PhDevicePropertyDriverInfPath, IDS_HD_DEVICE_PROPERTY_DRIVER_INF_PATH, L"Driver INF path", FALSE, 80, 0 },
    { PhDevicePropertyDriverInfSection, IDS_HD_DRIVER_INF_SECTION, L"Driver INF section", FALSE, 80, 0 },
    { PhDevicePropertyDriverInfSectionExt, IDS_HD_DEVICE_PROPERTY_DRIVER_INF_SECTION_EXT, L"Driver INF section extension", FALSE, 80, 0 },
    { PhDevicePropertyMatchingDeviceId, IDS_HD_MATCHING_ID, L"Matching ID", FALSE, 80, 0 },
    { PhDevicePropertyDriverProvider, IDS_HD_DRIVER_PROVIDER, L"Driver provider", FALSE, 80, 0 },
    { PhDevicePropertyDriverPropPageProvider, IDS_HD_DEVICE_PROPERTY_DRIVER_PROP_PAGE_PROVIDER, L"Driver property page provider", FALSE, 80, 0 },
    { PhDevicePropertyDriverCoInstallers, IDS_HD_DEVICE_PROPERTY_DRIVER_CO_INSTALLERS, L"Driver co-installers", FALSE, 80, 0 },
    { PhDevicePropertyResourcePickerTags, IDS_HD_DEVICE_PROPERTY_RESOURCE_PICKER_TAGS, L"Resource picker tags", FALSE, 80, 0 },
    { PhDevicePropertyResourcePickerExceptions, IDS_HD_DEVICE_PROPERTY_RESOURCE_PICKER_EXCEPTIONS, L"Resource picker exceptions", FALSE, 80, 0 },
    { PhDevicePropertyDriverRank, IDS_HD_DEVICE_PROPERTY_DRIVER_RANK, L"Driver rank", FALSE, 80, 0 },
    { PhDevicePropertyDriverLogoLevel, IDS_HD_DEVICE_PROPERTY_DRIVER_LOGO_LEVEL, L"Driver LOGO level", FALSE, 80, 0 },
    { PhDevicePropertyNoConnectSound, IDS_HD_DEVICE_PROPERTY_NO_CONNECT_SOUND, L"No connect sound", FALSE, 80, 0 },
    { PhDevicePropertyGenericDriverInstalled, IDS_HD_DEVICE_PROPERTY_GENERIC_DRIVER_INSTALLED, L"Generic driver installed", FALSE, 80, 0 },
    { PhDevicePropertyAdditionalSoftwareRequested, IDS_HD_DEVICE_PROPERTY_ADDITIONAL_SOFTWARE_REQUESTED, L"Additional software requested", FALSE, 80, 0 },
    { PhDevicePropertySafeRemovalRequired, IDS_HD_DEVICE_PROPERTY_SAFE_REMOVAL_REQUIRED, L"Safe removal required", FALSE, 80, 0 },
    { PhDevicePropertySafeRemovalRequiredOverride, IDS_HD_DEVICE_PROPERTY_SAFE_REMOVAL_REQUIRED_OVERRIDE, L"Safe removal required override", FALSE, 80, 0 },

    { PhDevicePropertyPkgModel, IDS_HD_DEVICE_PROPERTY_PKG_MODEL, L"Package model", FALSE, 80, 0 },
    { PhDevicePropertyPkgVendorWebSite, IDS_HD_DEVICE_PROPERTY_PKG_VENDOR_WEB_SITE, L"Package vendor website", FALSE, 80, 0 },
    { PhDevicePropertyPkgDetailedDescription, IDS_HD_DEVICE_PROPERTY_PKG_DETAILED_DESCRIPTION, L"Package description", FALSE, 80, 0 },
    { PhDevicePropertyPkgDocumentationLink, IDS_HD_DEVICE_PROPERTY_PKG_DOCUMENTATION_LINK, L"Package documentation", FALSE, 80, 0 },
    { PhDevicePropertyPkgIcon, IDS_HD_DEVICE_PROPERTY_PKG_ICON, L"Package icon", FALSE, 80, 0 },
    { PhDevicePropertyPkgBrandingIcon, IDS_HD_DEVICE_PROPERTY_PKG_BRANDING_ICON, L"Package branding icon", FALSE, 80, 0 },

    { PhDevicePropertyClassUpperFilters, IDS_HD_DEVICE_PROPERTY_CLASS_UPPER_FILTERS, L"Class upper filters", FALSE, 80, 0 },
    { PhDevicePropertyClassLowerFilters, IDS_HD_DEVICE_PROPERTY_CLASS_LOWER_FILTERS, L"Class lower filters", FALSE, 80, 0 },
    { PhDevicePropertyClassSecurity, IDS_HD_DEVICE_PROPERTY_CLASS_SECURITY, L"Class security descriptor (binary)", FALSE, 80, 0 },
    { PhDevicePropertyClassSecuritySDS, IDS_HD_DEVICE_PROPERTY_CLASS_SECURITY_SDS, L"Class security descriptor", FALSE, 80, 0 },
    { PhDevicePropertyClassDevType, IDS_HD_DEVICE_PROPERTY_CLASS_DEV_TYPE, L"Class type", FALSE, 80, 0 },
    { PhDevicePropertyClassExclusive, IDS_HD_DEVICE_PROPERTY_CLASS_EXCLUSIVE, L"Class exclusive", FALSE, 80, 0 },
    { PhDevicePropertyClassCharacteristics, IDS_HD_DEVICE_PROPERTY_CLASS_CHARACTERISTICS, L"Class characteristics", FALSE, 80, 0 },
    { PhDevicePropertyClassName, IDS_HD_DEVICE_PROPERTY_CLASS_NAME, L"Class device name", FALSE, 80, 0 },
    { PhDevicePropertyClassClassName, IDS_HD_CLASS_NAME, L"Class name", FALSE, 80, 0 },
    { PhDevicePropertyClassIcon, IDS_HD_DEVICE_PROPERTY_CLASS_ICON, L"Class icon", FALSE, 80, 0 },
    { PhDevicePropertyClassClassInstaller, IDS_HD_DEVICE_PROPERTY_CLASS_CLASS_INSTALLER, L"Class installer", FALSE, 80, 0 },
    { PhDevicePropertyClassPropPageProvider, IDS_HD_DEVICE_PROPERTY_CLASS_PROP_PAGE_PROVIDER, L"Class property page provider", FALSE, 80, 0 },
    { PhDevicePropertyClassNoInstallClass, IDS_HD_DEVICE_PROPERTY_CLASS_NO_INSTALL_CLASS, L"Class no install", FALSE, 80, 0 },
    { PhDevicePropertyClassNoDisplayClass, IDS_HD_DEVICE_PROPERTY_CLASS_NO_DISPLAY_CLASS, L"Class no display", FALSE, 80, 0 },
    { PhDevicePropertyClassSilentInstall, IDS_HD_DEVICE_PROPERTY_CLASS_SILENT_INSTALL, L"Class silent install", FALSE, 80, 0 },
    { PhDevicePropertyClassNoUseClass, IDS_HD_DEVICE_PROPERTY_CLASS_NO_USE_CLASS, L"Class no use class", FALSE, 80, 0 },
    { PhDevicePropertyClassDefaultService, IDS_HD_DEVICE_PROPERTY_CLASS_DEFAULT_SERVICE, L"Class default service", FALSE, 80, 0 },
    { PhDevicePropertyClassIconPath, IDS_HD_DEVICE_PROPERTY_CLASS_ICON_PATH, L"Class icon path", FALSE, 80, 0 },
    { PhDevicePropertyClassDHPRebalanceOptOut, IDS_HD_DEVICE_PROPERTY_CLASS_DHP_REBALANCE_OPT_OUT, L"Class DHP rebalance opt-out", FALSE, 80, 0 },
    { PhDevicePropertyClassClassCoInstallers, IDS_HD_DEVICE_PROPERTY_CLASS_CLASS_CO_INSTALLERS, L"Class co-installers", FALSE, 80, 0 },

    { PhDevicePropertyInterfaceFriendlyName, IDS_HD_DEVICE_PROPERTY_INTERFACE_FRIENDLY_NAME, L"Interface friendly name", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceEnabled, IDS_HD_DEVICE_PROPERTY_INTERFACE_ENABLED, L"Interface enabled", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceClassGuid, IDS_HD_DEVICE_PROPERTY_INTERFACE_CLASS_GUID, L"Interface class GUID", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceReferenceString, IDS_HD_DEVICE_PROPERTY_INTERFACE_REFERENCE_STRING, L"Interface reference", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceRestricted, IDS_HD_DEVICE_PROPERTY_INTERFACE_RESTRICTED, L"Interface restricted", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceUnrestrictedAppCapabilities, IDS_HD_DEVICE_PROPERTY_INTERFACE_UNRESTRICTED_APP_CAPABILITIES, L"Interface unrestricted application capabilities", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceSchematicName, IDS_HD_DEVICE_PROPERTY_INTERFACE_SCHEMATIC_NAME, L"Interface schematic name", FALSE, 80, 0 },

    { PhDevicePropertyInterfaceClassDefaultInterface, IDS_HD_DEVICE_PROPERTY_INTERFACE_CLASS_DEFAULT_INTERFACE, L"Interface class default interface", FALSE, 80, 0 },
    { PhDevicePropertyInterfaceClassName, IDS_HD_DEVICE_PROPERTY_INTERFACE_CLASS_NAME, L"Interface class name", FALSE, 80, 0 },

    { PhDevicePropertyContainerAddress, IDS_HD_DEVICE_PROPERTY_CONTAINER_ADDRESS, L"Container address", FALSE, 80, 0 },
    { PhDevicePropertyContainerDiscoveryMethod, IDS_HD_DEVICE_PROPERTY_CONTAINER_DISCOVERY_METHOD, L"Container discovery method", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsEncrypted, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_ENCRYPTED, L"Container encrypted", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsAuthenticated, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_AUTHENTICATED, L"Container authenticated", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsConnected, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_CONNECTED, L"Container connected", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsPaired, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_PAIRED, L"Container paired", FALSE, 80, 0 },
    { PhDevicePropertyContainerIcon, IDS_HD_DEVICE_PROPERTY_CONTAINER_ICON, L"Container icon", FALSE, 80, 0 },
    { PhDevicePropertyContainerVersion, IDS_HD_DEVICE_PROPERTY_CONTAINER_VERSION, L"Container version", FALSE, 80, 0 },
    { PhDevicePropertyContainerLastSeen, IDS_HD_DEVICE_PROPERTY_CONTAINER_LAST_SEEN, L"Container last seen", FALSE, 80, 0 },
    { PhDevicePropertyContainerLastConnected, IDS_HD_DEVICE_PROPERTY_CONTAINER_LAST_CONNECTED, L"Container last connected", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsShowInDisconnectedState, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_SHOW_IN_DISCONNECTED_STATE, L"Container show in disconnected state", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsLocalMachine, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_LOCAL_MACHINE, L"Container local machine", FALSE, 80, 0 },
    { PhDevicePropertyContainerMetadataPath, IDS_HD_DEVICE_PROPERTY_CONTAINER_METADATA_PATH, L"Container metadata path", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsMetadataSearchInProgress, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_METADATA_SEARCH_IN_PROGRESS, L"Container metadata search in progress", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsMetadataChecksum, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_METADATA_CHECKSUM, L"Metadata checksum", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsNotInterestingForDisplay, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_NOT_INTERESTING_FOR_DISPLAY, L"Container not interesting for display", FALSE, 80, 0 },
    { PhDevicePropertyContainerLaunchDeviceStageOnDeviceConnect, IDS_HD_DEVICE_PROPERTY_CONTAINER_LAUNCH_DEVICE_STAGE_ON_DEVICE_CONNECT, L"Container launch on connect", FALSE, 80, 0 },
    { PhDevicePropertyContainerLaunchDeviceStageFromExplorer, IDS_HD_DEVICE_PROPERTY_CONTAINER_LAUNCH_DEVICE_STAGE_FROM_EXPLORER, L"Container launch from explorer", FALSE, 80, 0 },
    { PhDevicePropertyContainerBaselineExperienceId, IDS_HD_DEVICE_PROPERTY_CONTAINER_BASELINE_EXPERIENCE_ID, L"Container baseline experience ID", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsDeviceUniquelyIdentifiable, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_DEVICE_UNIQUELY_IDENTIFIABLE, L"Container uniquely identifiable", FALSE, 80, 0 },
    { PhDevicePropertyContainerAssociationArray, IDS_HD_DEVICE_PROPERTY_CONTAINER_ASSOCIATION_ARRAY, L"Container association", FALSE, 80, 0 },
    { PhDevicePropertyContainerDeviceDescription1, IDS_HD_DEVICE_PROPERTY_CONTAINER_DEVICE_DESCRIPTION1, L"Container description", FALSE, 80, 0 },
    { PhDevicePropertyContainerDeviceDescription2, IDS_HD_DEVICE_PROPERTY_CONTAINER_DEVICE_DESCRIPTION2, L"Container description other", FALSE, 80, 0 },
    { PhDevicePropertyContainerHasProblem, IDS_HD_DEVICE_PROPERTY_CONTAINER_HAS_PROBLEM, L"Container has problem", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsSharedDevice, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_SHARED_DEVICE, L"Container shared device", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsNetworkDevice, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_NETWORK_DEVICE, L"Container network device", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsDefaultDevice, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_DEFAULT_DEVICE, L"Container default device", FALSE, 80, 0 },
    { PhDevicePropertyContainerMetadataCabinet, IDS_HD_DEVICE_PROPERTY_CONTAINER_METADATA_CABINET, L"Container metadata cabinet", FALSE, 80, 0 },
    { PhDevicePropertyContainerRequiresPairingElevation, IDS_HD_DEVICE_PROPERTY_CONTAINER_REQUIRES_PAIRING_ELEVATION, L"Container requires pairing elevation", FALSE, 80, 0 },
    { PhDevicePropertyContainerExperienceId, IDS_HD_DEVICE_PROPERTY_CONTAINER_EXPERIENCE_ID, L"Container experience ID", FALSE, 80, 0 },
    { PhDevicePropertyContainerCategory, IDS_HD_DEVICE_PROPERTY_CONTAINER_CATEGORY, L"Container category", FALSE, 80, 0 },
    { PhDevicePropertyContainerCategoryDescSingular, IDS_HD_DEVICE_PROPERTY_CONTAINER_CATEGORY_DESC_SINGULAR, L"Container category description", FALSE, 80, 0 },
    { PhDevicePropertyContainerCategoryDescPlural, IDS_HD_DEVICE_PROPERTY_CONTAINER_CATEGORY_DESC_PLURAL, L"Container category description plural", FALSE, 80, 0 },
    { PhDevicePropertyContainerCategoryIcon, IDS_HD_DEVICE_PROPERTY_CONTAINER_CATEGORY_ICON, L"Container category icon", FALSE, 80, 0 },
    { PhDevicePropertyContainerCategoryGroupDesc, IDS_HD_DEVICE_PROPERTY_CONTAINER_CATEGORY_GROUP_DESC, L"Container category group description", FALSE, 80, 0 },
    { PhDevicePropertyContainerCategoryGroupIcon, IDS_HD_DEVICE_PROPERTY_CONTAINER_CATEGORY_GROUP_ICON, L"Container category group icon", FALSE, 80, 0 },
    { PhDevicePropertyContainerPrimaryCategory, IDS_HD_DEVICE_PROPERTY_CONTAINER_PRIMARY_CATEGORY, L"Container primary category", FALSE, 80, 0 },
    { PhDevicePropertyContainerUnpairUninstall, IDS_HD_DEVICE_PROPERTY_CONTAINER_UNPAIR_UNINSTALL, L"Container unpair uninstall", FALSE, 80, 0 },
    { PhDevicePropertyContainerRequiresUninstallElevation, IDS_HD_DEVICE_PROPERTY_CONTAINER_REQUIRES_UNINSTALL_ELEVATION, L"Container requires uninstall elevation", FALSE, 80, 0 },
    { PhDevicePropertyContainerDeviceFunctionSubRank, IDS_HD_DEVICE_PROPERTY_CONTAINER_DEVICE_FUNCTION_SUB_RANK, L"Container function sub-rank", FALSE, 80, 0 },
    { PhDevicePropertyContainerAlwaysShowDeviceAsConnected, IDS_HD_DEVICE_PROPERTY_CONTAINER_ALWAYS_SHOW_DEVICE_AS_CONNECTED, L"Container always show connected", FALSE, 80, 0 },
    { PhDevicePropertyContainerConfigFlags, IDS_HD_DEVICE_PROPERTY_CONTAINER_CONFIG_FLAGS, L"Container configuration flags", FALSE, 80, 0 },
    { PhDevicePropertyContainerPrivilegedPackageFamilyNames, IDS_HD_DEVICE_PROPERTY_CONTAINER_PRIVILEGED_PACKAGE_FAMILY_NAMES, L"Container privileged package family names", FALSE, 80, 0 },
    { PhDevicePropertyContainerCustomPrivilegedPackageFamilyNames, IDS_HD_DEVICE_PROPERTY_CONTAINER_CUSTOM_PRIVILEGED_PACKAGE_FAMILY_NAMES, L"Container custom privileged package family names", FALSE, 80, 0 },
    { PhDevicePropertyContainerIsRebootRequired, IDS_HD_DEVICE_PROPERTY_CONTAINER_IS_REBOOT_REQUIRED, L"Container reboot required", FALSE, 80, 0 },
    { PhDevicePropertyContainerFriendlyName, IDS_HD_DEVICE_PROPERTY_CONTAINER_FRIENDLY_NAME, L"Container friendly name", FALSE, 80, 0 },
    { PhDevicePropertyContainerManufacturer, IDS_HD_DEVICE_PROPERTY_CONTAINER_MANUFACTURER, L"Container manufacturer", FALSE, 80, 0 },
    { PhDevicePropertyContainerModelName, IDS_HD_DEVICE_PROPERTY_CONTAINER_MODEL_NAME, L"Container model name", FALSE, 80, 0 },
    { PhDevicePropertyContainerModelNumber, IDS_HD_DEVICE_PROPERTY_CONTAINER_MODEL_NUMBER, L"Container model number", FALSE, 80, 0 },
    { PhDevicePropertyContainerInstallInProgress, IDS_HD_DEVICE_PROPERTY_CONTAINER_INSTALL_IN_PROGRESS, L"Container install in progress", FALSE, 80, 0 },

    { PhDevicePropertyObjectType, IDS_HD_DEVICE_PROPERTY_OBJECT_TYPE, L"Object type", FALSE, 80, 0 },

    { PhDevicePropertyPciDeviceType, IDS_HD_DEVICE_PROPERTY_PCI_DEVICE_TYPE, L"PCI device type", FALSE, 80, 0 },
    { PhDevicePropertyPciCurrentSpeedAndMode, IDS_HD_DEVICE_PROPERTY_PCI_CURRENT_SPEED_AND_MODE, L"PCI current speed and mode", FALSE, 80, 0 },
    { PhDevicePropertyPciBaseClass, IDS_HD_DEVICE_PROPERTY_PCI_BASE_CLASS, L"PCI base class", FALSE, 80, 0 },
    { PhDevicePropertyPciSubClass, IDS_HD_DEVICE_PROPERTY_PCI_SUB_CLASS, L"PCI subclass", FALSE, 80, 0 },
    { PhDevicePropertyPciProgIf, IDS_HD_DEVICE_PROPERTY_PCI_PROG_IF, L"PCI programming interface", FALSE, 80, 0 },
    { PhDevicePropertyPciCurrentPayloadSize, IDS_HD_DEVICE_PROPERTY_PCI_CURRENT_PAYLOAD_SIZE, L"PCI current payload size", FALSE, 80, 0 },
    { PhDevicePropertyPciMaxPayloadSize, IDS_HD_DEVICE_PROPERTY_PCI_MAX_PAYLOAD_SIZE, L"PCI max payload size", FALSE, 80, 0 },
    { PhDevicePropertyPciMaxReadRequestSize, IDS_HD_DEVICE_PROPERTY_PCI_MAX_READ_REQUEST_SIZE, L"PCI max read request size", FALSE, 80, 0 },
    { PhDevicePropertyPciCurrentLinkSpeed, IDS_HD_DEVICE_PROPERTY_PCI_CURRENT_LINK_SPEED, L"PCI current link speed", FALSE, 80, 0 },
    { PhDevicePropertyPciCurrentLinkWidth, IDS_HD_DEVICE_PROPERTY_PCI_CURRENT_LINK_WIDTH, L"PCI current link width", FALSE, 80, 0 },
    { PhDevicePropertyPciMaxLinkSpeed, IDS_HD_DEVICE_PROPERTY_PCI_MAX_LINK_SPEED, L"PCI max link speed", FALSE, 80, 0 },
    { PhDevicePropertyPciMaxLinkWidth, IDS_HD_DEVICE_PROPERTY_PCI_MAX_LINK_WIDTH, L"PCI max link width", FALSE, 80, 0 },
    { PhDevicePropertyPciExpressSpecVersion, IDS_HD_DEVICE_PROPERTY_PCI_EXPRESS_SPEC_VERSION, L"PCI Express specification version", FALSE, 80, 0 },
    { PhDevicePropertyPciInterruptSupport, IDS_HD_DEVICE_PROPERTY_PCI_INTERRUPT_SUPPORT, L"PCI interrupt support", FALSE, 80, 0 },
    { PhDevicePropertyPciInterruptMessageMaximum, IDS_HD_DEVICE_PROPERTY_PCI_INTERRUPT_MESSAGE_MAXIMUM, L"PCI interrupt message maximum", FALSE, 80, 0 },
    { PhDevicePropertyPciBarTypes, IDS_HD_DEVICE_PROPERTY_PCI_BAR_TYPES, L"PCI BAR types", FALSE, 80, 0 },
    { PhDevicePropertyPciSriovSupport, IDS_HD_DEVICE_PROPERTY_PCI_SRIOV_SUPPORT, L"PCI SR-IOV support", FALSE, 80, 0 },
    { PhDevicePropertyPciLabel_Id, IDS_HD_DEVICE_PROPERTY_PCI_LABEL_ID, L"PCI label ID", FALSE, 80, 0 },
    { PhDevicePropertyPciLabel_String, IDS_HD_DEVICE_PROPERTY_PCI_LABEL_STRING, L"PCI label string", FALSE, 80, 0 },
    { PhDevicePropertyPciSerialNumber, IDS_HD_DEVICE_PROPERTY_PCI_SERIAL_NUMBER, L"PCI serial number", FALSE, 80, 0 },

    { PhDevicePropertyPciExpressCapabilityControl, IDS_HD_DEVICE_PROPERTY_PCI_EXPRESS_CAPABILITY_CONTROL, L"PCI express capability control", FALSE, 80, 0 },
    { PhDevicePropertyPciNativeExpressControl, IDS_HD_DEVICE_PROPERTY_PCI_NATIVE_EXPRESS_CONTROL, L"PCI native express control", FALSE, 80, 0 },
    { PhDevicePropertyPciSystemMsiSupport, IDS_HD_DEVICE_PROPERTY_PCI_SYSTEM_MSI_SUPPORT, L"PCI system MSI support", FALSE, 80, 0 },

    { PhDevicePropertyStoragePortable, IDS_HD_DEVICE_PROPERTY_STORAGE_PORTABLE, L"Storage portable", FALSE, 80, 0 },
    { PhDevicePropertyStorageRemovableMedia, IDS_HD_DEVICE_PROPERTY_STORAGE_REMOVABLE_MEDIA, L"Storage removable media", FALSE, 80, 0 },
    { PhDevicePropertyStorageSystemCritical, IDS_HD_DEVICE_PROPERTY_STORAGE_SYSTEM_CRITICAL, L"Storage system critical", FALSE, 80, 0 },
    { PhDevicePropertyStorageDiskNumber, IDS_HD_DEVICE_PROPERTY_STORAGE_DISK_NUMBER, L"Storage disk number", FALSE, 80, 0 },
    { PhDevicePropertyStoragePartitionNumber, IDS_HD_DEVICE_PROPERTY_STORAGE_PARTITION_NUMBER, L"Storage partition number", FALSE, 80, 0 },

    { PhDevicePropertyGpuLuid, IDS_HD_DEVICE_PROPERTY_GPU_LUID, L"GPU LUID", FALSE, 80, 0 },
    { PhDevicePropertyGpuPhysicalAdapterIndex, IDS_HD_DEVICE_PROPERTY_GPU_PHYSICAL_ADAPTER_INDEX, L"GPU physical adapter index", FALSE, 80, 0 },
};
C_ASSERT(RTL_NUMBER_OF(DeviceItemPropertyTable) == PhMaxDeviceProperty);
const ULONG DeviceItemPropertyTableCount = RTL_NUMBER_OF(DeviceItemPropertyTable);

VOID DevicesTreeInitialize(
    _In_ HWND TreeNewHandle
    )
{
    ULONG count = 0;

    DeviceTreeHandle = TreeNewHandle;

    PhSetControlTheme(DeviceTreeHandle, L"explorer");
    TreeNew_SetRedraw(DeviceTreeHandle, FALSE);
    TreeNew_SetCallback(DeviceTreeHandle, DeviceTreeCallback, NULL);
    TreeNew_SetExtendedFlags(DeviceTreeHandle, TN_FLAG_ITEM_DRAG_SELECT, TN_FLAG_ITEM_DRAG_SELECT);
    SendMessage(TreeNew_GetTooltips(DeviceTreeHandle), TTM_SETDELAYTIME, TTDT_AUTOPOP, MAXSHORT);
    DevicesTreeImageListInitialize(DeviceTreeHandle);

    for (ULONG i = 0; i < DeviceItemPropertyTableCount; i++)
    {
        ULONG displayIndex;
        const DEVICE_PROPERTY_TABLE_ENTRY* entry;

        entry = &DeviceItemPropertyTable[i];

        assert(i == entry->PropClass);

        if (entry->PropClass == PhDevicePropertyName)
        {
            assert(i == 0);
            displayIndex = -2;
        }
        else
        {
            assert(i > 0);
            displayIndex = i - 1;
        }

        PhAddTreeNewColumn(
            DeviceTreeHandle,
            entry->PropClass,
            entry->ColumnVisible,
            DevicePropertyTableEntryGetColumnName(entry),
            entry->ColumnWidth,
            PH_ALIGN_LEFT,
            displayIndex,
            entry->ColumnTextFlags
            );
    }

    PhInitializeTreeNewFilterSupport(&DeviceTreeFilterSupport, DeviceTreeHandle, &DeviceFilterList);
    if (ToolStatusInterface)
    {
        PhRegisterCallback(
            ToolStatusInterface->SearchChangedEvent,
            DeviceTreeSearchChangedHandler,
            NULL,
            &SearchChangedRegistration);
        PhAddTreeNewFilter(&DeviceTreeFilterSupport, DeviceTreeFilterCallback, NULL);
    }

    if (PhGetIntegerSetting(SETTING_TREE_LIST_CUSTOM_ROW_SIZE))
    {
        ULONG treelistCustomRowSize = PhGetIntegerSetting(SETTING_TREE_LIST_CUSTOM_ROW_SIZE);

        if (treelistCustomRowSize < 15)
            treelistCustomRowSize = 15;

        TreeNew_SetRowHeight(DeviceTreeHandle, treelistCustomRowSize);
    }

    if (PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT))
    {
        PhInitializeWindowTheme(DeviceTreeHandle, TRUE);
        PhSetControlTheme(DeviceTreeHandle, L"DarkMode_Explorer");
        TreeNew_ThemeSupport(DeviceTreeHandle, TRUE);
    }

    TreeNew_SetTriState(DeviceTreeHandle, TRUE);
    TreeNew_SetRedraw(DeviceTreeHandle, TRUE);

    DevicesTreeLoadSettings(DeviceTreeHandle);

    DeviceTreeUpdateVisibleColumns();
}

_Function_class_(PH_MAIN_TAB_PAGE_CALLBACK)
BOOLEAN DevicesTabPageCallback(
    _In_ struct _PH_MAIN_TAB_PAGE* Page,
    _In_ PH_MAIN_TAB_PAGE_MESSAGE Message,
    _In_opt_ PVOID Parameter1,
    _In_opt_ PVOID Parameter2
    )
{
    switch (Message)
    {
    case MainTabPageCreateWindow:
        {
            HWND hwnd;
            ULONG thinRows;
            ULONG treelistBorder;
            ULONG treelistCustomColors;
            PH_TREENEW_CREATEPARAMS treelistCreateParams = { 0 };

            thinRows = PhGetIntegerSetting(SETTING_THIN_ROWS) ? TN_STYLE_THIN_ROWS : 0;
            treelistBorder = (PhGetIntegerSetting(SETTING_TREE_LIST_BORDER_ENABLE) && !PhGetIntegerSetting(SETTING_ENABLE_THEME_SUPPORT)) ? WS_BORDER : 0;
            treelistCustomColors = PhGetIntegerSetting(SETTING_TREE_LIST_CUSTOM_COLORS_ENABLE) ? TN_STYLE_CUSTOM_COLORS : 0;

            if (treelistCustomColors)
            {
                treelistCreateParams.TextColor = PhGetIntegerSetting(SETTING_TREE_LIST_CUSTOM_COLOR_TEXT);
                treelistCreateParams.FocusColor = PhGetIntegerSetting(SETTING_TREE_LIST_CUSTOM_COLOR_FOCUS);
                treelistCreateParams.SelectionColor = PhGetIntegerSetting(SETTING_TREE_LIST_CUSTOM_COLOR_SELECTION);
            }

            hwnd = CreateWindow(
                PH_TREENEW_CLASSNAME,
                NULL,
                WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS | TN_STYLE_ICONS | TN_STYLE_DOUBLE_BUFFERED | TN_STYLE_ANIMATE_DIVIDER | thinRows | treelistBorder | treelistCustomColors,
                0,
                0,
                0,
                0,
                Parameter2,
                NULL,
                PluginInstance->DllBase,
                &treelistCreateParams
                );

            if (!hwnd)
                return FALSE;

            DeviceTabCreated = TRUE;

            DevicesTreeInitialize(hwnd);

            if (Parameter1)
            {
                *(HWND*)Parameter1 = hwnd;
            }
        }
        return TRUE;
    case MainTabPageLoadSettings:
        {
            NOTHING;
        }
        return TRUE;
    case MainTabPageSaveSettings:
        {
            DevicesTreeSaveSettings();
        }
        return TRUE;
    case MainTabPageSelected:
        {
            DeviceTabSelected = (BOOLEAN)PtrToUlong(Parameter1);
            if (DeviceTabSelected)
            {
                DeviceTreePublishAsync(FALSE);

                if (DeviceTreeHandle)
                {
                    TreeNew_NodesStructured(DeviceTreeHandle);

                    if (DeviceTreeFilterSupport.FilterList)
                        PhApplyTreeNewFilters(&DeviceTreeFilterSupport);
                }
            }
        }
        break;
    case MainTabPageFontChanged:
        {
            HFONT font = (HFONT)Parameter1;

            if (DeviceTreeHandle)
                SetWindowFont(DeviceTreeHandle, Parameter1, TRUE);
        }
        break;
    case MainTabPageDpiChanged:
        {
            if (DeviceImageList)
            {
                DevicesTreeImageListInitialize(DeviceTreeHandle);

                if (DeviceTree)
                {
                    for (ULONG i = 0; i < DeviceTree->Nodes->Count; i++)
                    {
                        PDEVICE_NODE node = DeviceTree->Nodes->Items[i];
                        HICON iconHandle = PhGetDeviceIcon(node->DeviceItem, &DeviceIconSize);
                        if (iconHandle)
                        {
                            node->IconIndex = PhImageListAddIcon(DeviceImageList, iconHandle);
                            DestroyIcon(iconHandle);
                        }
                        else
                        {
                            node->IconIndex = 0; // Must be reset (dmex)
                        }
                    }
                }
            }
        }
        break;
    case MainTabPageInitializeSectionMenuItems:
        {
            PPH_MAIN_TAB_PAGE_MENU_INFORMATION menuInfo = Parameter1;
            PPH_EMENU menu;
            PPH_EMENU_ITEM autoRefresh;
            PPH_EMENU_ITEM showDisconnectedDevices;
            PPH_EMENU_ITEM showSoftwareDevices;
            PPH_EMENU_ITEM showDeviceInterfaces;
            PPH_EMENU_ITEM showDisabledDeviceInterfaces;
            PPH_EMENU_ITEM sortChildDevices;
            PPH_EMENU_ITEM sortRootDevices;
            PPH_EMENU_ITEM highlightUpperFiltered;
            PPH_EMENU_ITEM highlightLowerFiltered;

            assert(menuInfo);

            menu = PhCreateEMenuItem(0, 0, HardwareDevicesGetUiString(IDS_HD_MENU_DEVICES), NULL, NULL);
            PhInsertEMenuItem(menuInfo->Menu, menu, menuInfo->StartIndex);

            PhInsertEMenuItem(menu, PhPluginCreateEMenuItem(PluginInstance, 0, 98, L"Collapse all", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhPluginCreateEMenuItem(PluginInstance, 0, 99, L"Expand all", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            PhInsertEMenuItem(menu, PhPluginCreateEMenuItem(PluginInstance, 0, 100, L"Refresh", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, autoRefresh = PhPluginCreateEMenuItem(PluginInstance, 0, 101, L"Refresh automatically", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, PhCreateEMenuSeparator(), ULONG_MAX);
            PhInsertEMenuItem(menu, showDisconnectedDevices = PhPluginCreateEMenuItem(PluginInstance, 0, 102, L"Show disconnected devices", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, showSoftwareDevices = PhPluginCreateEMenuItem(PluginInstance, 0, 103, L"Show software components", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, showDeviceInterfaces = PhPluginCreateEMenuItem(PluginInstance, 0, 104, L"Show device interfaces", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, showDisabledDeviceInterfaces = PhPluginCreateEMenuItem(PluginInstance, 0, 105, L"Show disabled device interfaces", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, sortChildDevices = PhPluginCreateEMenuItem(PluginInstance, 0, 106, L"Sort child devices", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, sortRootDevices = PhPluginCreateEMenuItem(PluginInstance, 0, 107, L"Sort root devices", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, highlightUpperFiltered = PhPluginCreateEMenuItem(PluginInstance, 0, 108, L"Highlight upper filtered", NULL), ULONG_MAX);
            PhInsertEMenuItem(menu, highlightLowerFiltered = PhPluginCreateEMenuItem(PluginInstance, 0, 109, L"Highlight lower filtered", NULL), ULONG_MAX);

            if (AutoRefreshDeviceTree)
                autoRefresh->Flags |= PH_EMENU_CHECKED;
            if (ShowDisconnected)
                showDisconnectedDevices->Flags |= PH_EMENU_CHECKED;
            if (ShowSoftwareComponents)
                showSoftwareDevices->Flags |= PH_EMENU_CHECKED;
            if (ShowDeviceInterfaces)
                showDeviceInterfaces->Flags |= PH_EMENU_CHECKED;
            if (ShowDisabledDeviceInterfaces)
                showDisabledDeviceInterfaces->Flags |= PH_EMENU_CHECKED;
            if (SortChildDevices)
                sortChildDevices->Flags |= PH_EMENU_CHECKED;
            if (SortRootDevices)
                sortRootDevices->Flags |= PH_EMENU_CHECKED;
            if (HighlightUpperFiltered)
                highlightUpperFiltered->Flags |= PH_EMENU_CHECKED;
            if (HighlightLowerFiltered)
                highlightLowerFiltered->Flags |= PH_EMENU_CHECKED;
        }
        return TRUE;
    }

    return FALSE;
}

_Function_class_(PH_CALLBACK_FUNCTION)
VOID NTAPI DeviceTreeMenuItemCallback(
    _In_opt_ PVOID Parameter,
    _In_opt_ PVOID Context
    )
{
    BOOLEAN republish = FALSE;
    BOOLEAN invalidate = FALSE;
    PPH_PLUGIN_MENU_ITEM menuItem = Parameter;

    assert(menuItem);

    switch (menuItem->Id)
    {
    case 98:
        DevicesExpandAllNodes(FALSE);
        break;
    case 99:
        DevicesExpandAllNodes(TRUE);
        break;
    case 100:
        republish = TRUE;
        break;
    case 101:
        AutoRefreshDeviceTree = !AutoRefreshDeviceTree;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_TREE_AUTO_REFRESH, AutoRefreshDeviceTree);
        break;
    case 102:
        ShowDisconnected = !ShowDisconnected;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_TREE_SHOW_DISCONNECTED, ShowDisconnected);
        republish = TRUE;
        break;
    case 103:
        ShowSoftwareComponents = !ShowSoftwareComponents;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_SHOW_SOFTWARE_COMPONENTS, ShowSoftwareComponents);
        republish = TRUE;
        break;
    case 104:
        ShowDeviceInterfaces = !ShowDeviceInterfaces;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_SHOW_DEVICE_INTERFACES, ShowDeviceInterfaces);
        republish = TRUE;
        break;
    case 105:
        ShowDisabledDeviceInterfaces = !ShowDisabledDeviceInterfaces;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_SHOW_DISABLED_DEVICE_INTERFACES, ShowDisabledDeviceInterfaces);
        republish = TRUE;
        break;
    case 106:
        SortChildDevices = !SortChildDevices;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_SORT_CHILD_DEVICES, SortChildDevices);
        republish = TRUE;
        break;
    case 107:
        SortRootDevices = !SortRootDevices;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_SORT_ROOT_DEVICES, SortRootDevices);
        republish = TRUE;
        break;
    case 108:
        HighlightUpperFiltered = !HighlightUpperFiltered;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_TREE_HIGHLIGHT_UPPER_FILTERED, HighlightUpperFiltered);
        invalidate = TRUE;
        break;
    case 109:
        HighlightLowerFiltered = !HighlightLowerFiltered;
        PhSetIntegerSetting(SETTING_NAME_DEVICE_TREE_HIGHLIGHT_LOWER_FILTERED, HighlightLowerFiltered);
        invalidate = TRUE;
        break;
    }

    if (DeviceTabCreated)
    {
        if (republish)
        {
            DeviceTreePublishAsync(TRUE);
        }
        else if (invalidate)
        {
            InvalidateDeviceNodes();
            if (DeviceTreeFilterSupport.FilterList)
                PhApplyTreeNewFilters(&DeviceTreeFilterSupport);
        }
    }
}

_Function_class_(TOOLSTATUS_TAB_ACTIVATE_CONTENT)
VOID NTAPI ToolStatusActivateContent(
    _In_ BOOLEAN Select
    )
{
    SetFocus(DeviceTreeHandle);

    if (Select)
    {
        if (TreeNew_GetFlatNodeCount(DeviceTreeHandle) > 0)
        {
            PDEVICE_NODE node;

            node = (PDEVICE_NODE)TreeNew_GetFlatNode(DeviceTreeHandle, 0);

            if (!node->Node.Visible)
            {
                TreeNew_FocusMarkSelectNode(DeviceTreeHandle, &node->Node);
            }
        }
    }
}

_Function_class_(TOOLSTATUS_GET_TREENEW_HANDLE)
HWND NTAPI ToolStatusGetTreeNewHandle(
    VOID
    )
{
    return DeviceTreeHandle;
}

_Function_class_(PH_CALLBACK_FUNCTION)
VOID NTAPI DeviceProviderCallbackHandler(
    _In_opt_ PVOID Parameter,
    _In_opt_ PVOID Context
    )
{
    if (DeviceTabCreated && DeviceTabSelected && AutoRefreshDeviceTree)
    {
        SystemInformer_Invoke(DeviceTreePublish, DeviceTreeCreateIfNecessary(FALSE));
    }
}

VOID DeviceTreeRemoveDeviceNode(
    _In_ PDEVICE_NODE Node,
    _In_opt_ PVOID Context
    )
{
    NOTHING;
}

_Function_class_(PH_CALLBACK_FUNCTION)
VOID NTAPI DeviceTreeProcessesUpdatedCallback(
    _In_opt_ PVOID Parameter,
    _In_opt_ PVOID Context
    )
{
    BOOLEAN fullyInvalidated = FALSE;

    if (PtrToUlong(Parameter) < 2)
        return;

    if (!DeviceTreeHandle)
        return;

    // piggy back off the processes update callback to handle state changes
    PH_TICK_SH_STATE_TN(
        DEVICE_NODE,
        ShState,
        DeviceNodeStateList,
        DeviceTreeRemoveDeviceNode,
        DeviceHighlightingDuration,
        DeviceTreeHandle,
        TRUE,
        &fullyInvalidated,
        Context
        );
}

VOID DeviceTreeUpdateCachedSettings(
    _In_ BOOLEAN UpdateColors
    )
{
    ShowDeviceRootNode = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_SHOW_ROOT);
    AutoRefreshDeviceTree = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_TREE_AUTO_REFRESH);
    ShowDisconnected = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_TREE_SHOW_DISCONNECTED);
    ShowSoftwareComponents = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_SHOW_SOFTWARE_COMPONENTS);
    ShowDeviceInterfaces = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_SHOW_DEVICE_INTERFACES);
    ShowDisabledDeviceInterfaces = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_SHOW_DISABLED_DEVICE_INTERFACES);
    HighlightUpperFiltered = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_TREE_HIGHLIGHT_UPPER_FILTERED);
    HighlightLowerFiltered = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_TREE_HIGHLIGHT_LOWER_FILTERED);
    DeviceHighlightingDuration = PhGetIntegerSetting(SETTING_NAME_DEVICE_HIGHLIGHTING_DURATION);
    SortNameDevices = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_SORT_CHILDREN_BY_NAME);
    SortChildDevices = !!PhGetIntegerSetting(SETTING_NAME_DEVICE_SORT_CHILD_DEVICES);

    if (UpdateColors)
    {
        DeviceProblemColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_PROBLEM_COLOR);
        DeviceDisabledColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_DISABLED_COLOR);
        DeviceDisconnectedColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_DISCONNECTED_COLOR);
        DeviceHighlightColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_HIGHLIGHT_COLOR);
        DeviceInterfaceColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_INTERFACE_COLOR);
        DeviceDisabledInterfaceColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_DISABLED_INTERFACE_COLOR);
        DeviceArrivedColor = PhGetIntegerSetting(SETTING_NAME_DEVICE_ARRIVED_COLOR);
    }
}

_Function_class_(PH_CALLBACK_FUNCTION)
VOID NTAPI DeviceTreeSettingsUpdatedCallback(
    _In_opt_ PVOID Parameter,
    _In_opt_ PVOID Context
    )
{
    DeviceTreeUpdateCachedSettings(FALSE);
}

VOID InitializeDevicesTab(
    VOID
    )
{
    PH_MAIN_TAB_PAGE page;

    DeviceTreeType = PhCreateObjectType(L"DevicesTree", 0, DeviceTreeDeleteProcedure);

    PhRegisterCallback(
        PhGetGeneralCallback(GeneralCallbackDeviceNotificationEvent),
        DeviceProviderCallbackHandler,
        NULL,
        &DeviceNotifyRegistration
        );
    PhRegisterCallback(
        PhGetGeneralCallback(GeneralCallbackProcessesUpdated),
        DeviceTreeProcessesUpdatedCallback,
        NULL,
        &ProcessesUpdatedCallbackRegistration
        );
    PhRegisterCallback(
        PhGetGeneralCallback(GeneralCallbackSettingsUpdated),
        DeviceTreeSettingsUpdatedCallback,
        NULL,
        &SettingsUpdatedCallbackRegistration
        );
    PhRegisterCallback(
        PhGetPluginCallback(PluginInstance, PluginCallbackMenuItem),
        DeviceTreeMenuItemCallback,
        NULL,
        &DeviceTreeMenuItemCallbackRegistration
        );

    DeviceTreeUpdateCachedSettings(TRUE);

    RtlZeroMemory(&page, sizeof(PH_MAIN_TAB_PAGE));
    page.Name = DevicePageText;
    page.Callback = DevicesTabPageCallback;
    DevicesAddedTabPage = PhPluginCreateTabPage(&page);

    if (ToolStatusInterface = PhGetPluginInterfaceZ(TOOLSTATUS_INTERFACE_NAME, TOOLSTATUS_INTERFACE_VERSION))
    {
        PTOOLSTATUS_TAB_INFO tabInfo;

        tabInfo = ToolStatusInterface->RegisterTabInfo(DevicesAddedTabPage->Index, &DeviceBannerText);
        tabInfo->ActivateContent = ToolStatusActivateContent;
        tabInfo->GetTreeNewHandle = ToolStatusGetTreeNewHandle;
    }
}
