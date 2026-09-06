/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2011
 *     dmex    2011-2026
 *
 */

#include "exttools.h"
#include <netfw.h>

_Function_class_(PH_PLUGIN_TREENEW_SORT_FUNCTION)
LONG EtpProcessTreeNewSortFunction(
    _In_ PVOID Node1,
    _In_ PVOID Node2,
    _In_ ULONG SubId,
    _In_ PH_SORT_ORDER SortOrder,
    _In_ PVOID Context
    );

_Function_class_(PH_PLUGIN_TREENEW_SORT_FUNCTION)
LONG EtpNetworkTreeNewSortFunction(
    _In_ PVOID Node1,
    _In_ PVOID Node2,
    _In_ ULONG SubId,
    _In_ PH_SORT_ORDER SortOrder,
    _In_ PVOID Context
    );

typedef struct _COLUMN_INFO
{
    ULONG SubId;
    ULONG TextResourceId;
    PCWSTR Text;
    ULONG Width;
    ULONG Alignment;
    ULONG TextFlags;
    BOOLEAN SortDescending;
} COLUMN_INFO, *PCOLUMN_INFO;

static ULONG ProcessTreeListSortColumn;
static PH_SORT_ORDER ProcessTreeListSortOrder;
static PPH_LIST EtGpuNodeColumnTextList;

VOID EtpAddTreeNewColumn(
    _In_ PPH_PLUGIN_TREENEW_INFORMATION TreeNewInfo,
    _In_ ULONG SubId,
    _In_ PCWSTR Text,
    _In_ ULONG Width,
    _In_ ULONG Alignment,
    _In_ ULONG TextFlags,
    _In_ BOOLEAN SortDescending,
    _In_ PPH_PLUGIN_TREENEW_SORT_FUNCTION SortFunction
    )
{
    PH_TREENEW_COLUMN column;

    memset(&column, 0, sizeof(PH_TREENEW_COLUMN));
    column.SortDescending = SortDescending;
    column.Text = (PWSTR)Text;
    column.Width = Width;
    column.Alignment = Alignment;
    column.TextFlags = TextFlags;

    PhPluginAddTreeNewColumn(
        PluginInstance,
        TreeNewInfo->CmData,
        &column,
        SubId,
        NULL,
        SortFunction
        );
}

VOID EtProcessTreeNewInitializing(
    _In_ PVOID Parameter
    )
{
    const static COLUMN_INFO columns[] =
    {
        { ETPRTNC_DISKREADS, IDS_ET_PROCESS_COLUMN_DISK_READS, L"Disk reads", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKWRITES, IDS_ET_PROCESS_COLUMN_DISK_WRITES, L"Disk writes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKREADBYTES, IDS_ET_PROCESS_COLUMN_DISK_READ_BYTES, L"Disk read bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKWRITEBYTES, IDS_ET_PROCESS_COLUMN_DISK_WRITE_BYTES, L"Disk write bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKTOTALBYTES, IDS_ET_PROCESS_COLUMN_DISK_TOTAL_BYTES, L"Disk total bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKREADSDELTA, IDS_ET_PROCESS_COLUMN_DISK_READS_DELTA, L"Disk reads delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKWRITESDELTA, IDS_ET_PROCESS_COLUMN_DISK_WRITES_DELTA, L"Disk writes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKREADBYTESDELTA, IDS_ET_PROCESS_COLUMN_DISK_READ_BYTES_DELTA, L"Disk read bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKWRITEBYTESDELTA, IDS_ET_PROCESS_COLUMN_DISK_WRITE_BYTES_DELTA, L"Disk write bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKTOTALBYTESDELTA, IDS_ET_PROCESS_COLUMN_DISK_TOTAL_BYTES_DELTA, L"Disk total bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKRECEIVES, IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVES, L"Network receives", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKSENDS, IDS_ET_PROCESS_COLUMN_NETWORK_SENDS, L"Network sends", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKRECEIVEBYTES, IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_BYTES, L"Network receive bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKSENDBYTES, IDS_ET_PROCESS_COLUMN_NETWORK_SEND_BYTES, L"Network send bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKTOTALBYTES, IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_BYTES, L"Network total bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKRECEIVESDELTA, IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVES_DELTA, L"Network receives delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKSENDSDELTA, IDS_ET_PROCESS_COLUMN_NETWORK_SENDS_DELTA, L"Network sends delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKRECEIVEBYTESDELTA, IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_BYTES_DELTA, L"Network receive bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKSENDBYTESDELTA, IDS_ET_PROCESS_COLUMN_NETWORK_SEND_BYTES_DELTA, L"Network send bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKTOTALBYTESDELTA, IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_BYTES_DELTA, L"Network total bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_HARDFAULTS, IDS_ET_PROCESS_COLUMN_HARD_FAULTS, L"Hard faults", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_HARDFAULTSDELTA, IDS_ET_PROCESS_COLUMN_HARD_FAULTS_DELTA, L"Hard faults delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_PEAKTHREADS, IDS_ET_PROCESS_COLUMN_PEAK_THREADS, L"Peak threads", 45, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_GPUDEDICATEDBYTES, IDS_ET_PROCESS_COLUMN_GPU_DEDICATED_RESIDENT, L"GPU dedicated bytes (resident)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_GPUSHAREDBYTES, IDS_ET_PROCESS_COLUMN_GPU_SHARED_RESIDENT, L"GPU shared bytes (resident)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKREADRATE, IDS_ET_PROCESS_COLUMN_DISK_READ_RATE, L"Disk read rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKWRITERATE, IDS_ET_PROCESS_COLUMN_DISK_WRITE_RATE, L"Disk write rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_DISKTOTALRATE, IDS_ET_PROCESS_COLUMN_DISK_TOTAL_RATE, L"Disk total rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKRECEIVERATE, IDS_ET_PROCESS_COLUMN_NETWORK_RECEIVE_RATE, L"Network receive rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKSENDRATE, IDS_ET_PROCESS_COLUMN_NETWORK_SEND_RATE, L"Network send rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NETWORKTOTALRATE, IDS_ET_PROCESS_COLUMN_NETWORK_TOTAL_RATE, L"Network total rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_FPS, IDS_ET_PROCESS_COLUMN_FPS, L"FPS", 50, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NPU, IDS_ET_GROUP_NPU, L"NPU", 45, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NPUDEDICATEDBYTES, IDS_ET_PROCESS_COLUMN_NPU_DEDICATED_RESIDENT, L"NPU dedicated bytes (resident)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NPUSHAREDBYTES, IDS_ET_PROCESS_COLUMN_NPU_SHARED_RESIDENT, L"NPU shared bytes (resident)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES, IDS_ET_PROCESS_COLUMN_GPU_DEDICATED_COMMITTED, L"GPU dedicated bytes (committed)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_GPUSHAREDCOMMITTEDBYTES, IDS_ET_PROCESS_COLUMN_GPU_SHARED_COMMITTED, L"GPU shared bytes (committed)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES, IDS_ET_PROCESS_COLUMN_NPU_DEDICATED_COMMITTED, L"NPU dedicated bytes (committed)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_NPUSHAREDCOMMITTEDBYTES, IDS_ET_PROCESS_COLUMN_NPU_SHARED_COMMITTED, L"NPU shared bytes (committed)", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_FIREWALLALLOWS, IDS_ET_PROCESS_COLUMN_FIREWALL_ALLOWS, L"Firewall allows", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_FIREWALLBLOCKS, IDS_ET_PROCESS_COLUMN_FIREWALL_BLOCKS, L"Firewall blocks", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_FIREWALLALLOWSDELTA, IDS_ET_PROCESS_COLUMN_FIREWALL_ALLOWS_DELTA, L"Firewall allows delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETPRTNC_FIREWALLBLOCKSDELTA, IDS_ET_PROCESS_COLUMN_FIREWALL_BLOCKS_DELTA, L"Firewall blocks delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
    };

    PPH_PLUGIN_TREENEW_INFORMATION treeNewInfo = Parameter;
    ULONG i;

    for (i = 0; i < RTL_NUMBER_OF(columns); i++)
    {
        EtpAddTreeNewColumn(treeNewInfo, columns[i].SubId, EtGetUiString(columns[i].TextResourceId, columns[i].Text), columns[i].Width, columns[i].Alignment,
            columns[i].TextFlags, columns[i].SortDescending, EtpProcessTreeNewSortFunction);
    }

    if (EtGpuEnabled && EtGpuTotalNodeCount)
    {
        ULONG adapterCount = EtGetGpuAdapterCount();
        ULONG previousAdapterIndex = ULONG_MAX;
        ULONG adapterNodeIndex = 0;

        EtGpuNodeColumnTextList = PhCreateList(adapterCount + EtGpuTotalNodeCount);

        for (i = 0; i < adapterCount; i++)
        {
            PPH_STRING columnText;

            columnText = PhFormatString(EtGetUiString(IDS_ET_GPU_ADAPTER_COLUMN_FORMAT, L"GPU %lu"), i);
            PhAddItemList(EtGpuNodeColumnTextList, columnText);
            EtpAddTreeNewColumn(
                treeNewInfo,
                ETPRTNC_GPUADAPTER_FIRST + i,
                columnText->Buffer,
                55,
                PH_ALIGN_RIGHT,
                DT_RIGHT,
                TRUE,
                EtpProcessTreeNewSortFunction
                );
        }

        for (i = 0; i < EtGpuTotalNodeCount; i++)
        {
            ULONG adapterIndex;
            PPH_STRING nodeName;
            PPH_STRING columnText;

            adapterIndex = EtGetGpuAdapterIndexFromNodeIndex(i);
            nodeName = EtGetGpuAdapterNodeDescription(adapterIndex, i);

            if (adapterIndex == previousAdapterIndex)
                adapterNodeIndex++;
            else
                adapterNodeIndex = 0;

            previousAdapterIndex = adapterIndex;

            if (nodeName && nodeName->Length)
                columnText = PhFormatString(EtGetUiString(IDS_ET_GPU_NODE_COLUMN_NAMED_FORMAT, L"GPU %lu node %lu (%s)"), adapterIndex, adapterNodeIndex, nodeName->Buffer);
            else
                columnText = PhFormatString(EtGetUiString(IDS_ET_GPU_NODE_COLUMN_FORMAT, L"GPU %lu node %lu"), adapterIndex, adapterNodeIndex);

            PhAddItemList(EtGpuNodeColumnTextList, columnText);
            EtpAddTreeNewColumn(
                treeNewInfo,
                ETPRTNC_GPUNODE_FIRST + i,
                columnText->Buffer,
                75,
                PH_ALIGN_RIGHT,
                DT_RIGHT,
                TRUE,
                EtpProcessTreeNewSortFunction
                );
        }
    }

    PhPluginEnableTreeNewNotify(PluginInstance, treeNewInfo->CmData);
}

VOID EtUninitializeTreeNewColumns(
    VOID
    )
{
    if (EtGpuNodeColumnTextList)
    {
        PhDereferenceObjects(EtGpuNodeColumnTextList->Items, EtGpuNodeColumnTextList->Count);
        PhDereferenceObject(EtGpuNodeColumnTextList);
        EtGpuNodeColumnTextList = NULL;
    }
}

static VOID PhpAggregateFieldIfNeeded(
    _In_ PPH_PROCESS_NODE ProcessNode,
    _In_ PH_AGGREGATE_TYPE Type,
    _In_ PVOID BaseAddress,
    _In_ SIZE_T FieldOffset,
    _Inout_ PVOID AggregatedValue
    )
{
    PhAggregateProcessFieldIfNeeded(ProcessNode, Type, AggregateProcessItem, BaseAddress, FieldOffset, AggregatedValue);
}

static VOID EtpAggregateGpuNode(
    _In_ PPH_PROCESS_NODE ProcessNode,
    _In_ ULONG NodeIndex,
    _Inout_ PFLOAT Value
    )
{
    PET_PROCESS_BLOCK block;

    block = EtGetProcessBlock(ProcessNode->ProcessItem);

    if (block && block->GpuNodesUtilization)
        *Value += block->GpuNodesUtilization[NodeIndex];

    for (ULONG i = 0; i < ProcessNode->Children->Count; i++)
        EtpAggregateGpuNode(ProcessNode->Children->Items[i], NodeIndex, Value);
}

static FLOAT EtpGetGpuNodeValue(
    _In_ PPH_PROCESS_NODE ProcessNode,
    _In_ PET_PROCESS_BLOCK Block,
    _In_ ULONG NodeIndex
    )
{
    FLOAT value = 0;

    if (!EtPropagateCpuUsage || ProcessNode->Node.Expanded ||
        ProcessTreeListSortOrder != NoSortOrder)
    {
        if (Block->GpuNodesUtilization)
            value = Block->GpuNodesUtilization[NodeIndex];
    }
    else
    {
        EtpAggregateGpuNode(ProcessNode, NodeIndex, &value);
    }

    return min(value, 1.f);
}

static FLOAT EtpGetGpuAdapterOwnValue(
    _In_ PET_PROCESS_BLOCK Block,
    _In_ ULONG AdapterIndex
    )
{
    FLOAT value = 0;

    if (!Block->GpuNodesUtilization)
        return 0;

    for (ULONG i = 0; i < EtGpuTotalNodeCount; i++)
    {
        if (EtGetGpuAdapterIndexFromNodeIndex(i) == AdapterIndex)
            value += Block->GpuNodesUtilization[i];
    }

    return value;
}

static VOID EtpAggregateGpuAdapter(
    _In_ PPH_PROCESS_NODE ProcessNode,
    _In_ ULONG AdapterIndex,
    _Inout_ PFLOAT Value
    )
{
    PET_PROCESS_BLOCK block;

    block = EtGetProcessBlock(ProcessNode->ProcessItem);

    if (block)
        *Value += EtpGetGpuAdapterOwnValue(block, AdapterIndex);

    for (ULONG i = 0; i < ProcessNode->Children->Count; i++)
        EtpAggregateGpuAdapter(ProcessNode->Children->Items[i], AdapterIndex, Value);
}

static FLOAT EtpGetGpuAdapterValue(
    _In_ PPH_PROCESS_NODE ProcessNode,
    _In_ PET_PROCESS_BLOCK Block,
    _In_ ULONG AdapterIndex
    )
{
    FLOAT value = 0;

    if (!EtPropagateCpuUsage || ProcessNode->Node.Expanded ||
        ProcessTreeListSortOrder != NoSortOrder)
    {
        value = EtpGetGpuAdapterOwnValue(Block, AdapterIndex);
    }
    else
    {
        EtpAggregateGpuAdapter(ProcessNode, AdapterIndex, &value);
    }

    return value;
}

VOID EtProcessTreeNewMessage(
    _In_ PVOID Parameter
    )
{
    PPH_PLUGIN_TREENEW_MESSAGE message = Parameter;
    PPH_PROCESS_NODE processNode;
    PET_PROCESS_BLOCK block;

    if (message->Message == TreeNewGetCellText)
    {
        PPH_TREENEW_GET_CELL_TEXT getCellText = message->Parameter1;
        processNode = (PPH_PROCESS_NODE)getCellText->Node;
        block = EtGetProcessBlock(processNode->ProcessItem);

        if ((message->SubId >= ETPRTNC_GPUADAPTER_FIRST &&
            message->SubId < ETPRTNC_GPUADAPTER_FIRST + EtGetGpuAdapterCount()) ||
            (message->SubId >= ETPRTNC_GPUNODE_FIRST &&
            message->SubId < ETPRTNC_GPUNODE_FIRST + EtGpuTotalNodeCount))
        {
            ULONG cacheIndex;
            FLOAT gpuUsage;
            PWCHAR textBuffer;

            if (message->SubId >= ETPRTNC_GPUNODE_FIRST)
            {
                ULONG nodeIndex = message->SubId - ETPRTNC_GPUNODE_FIRST;

                cacheIndex = EtGetGpuAdapterCount() + nodeIndex;
                gpuUsage = EtpGetGpuNodeValue(processNode, block, nodeIndex) * 100;
            }
            else
            {
                ULONG adapterIndex = message->SubId - ETPRTNC_GPUADAPTER_FIRST;

                cacheIndex = adapterIndex;
                gpuUsage = EtpGetGpuAdapterValue(processNode, block, adapterIndex) * 100;
            }

            PhAcquireQueuedLockExclusive(&block->TextCacheLock);

            textBuffer = block->GpuNodesTextCache + cacheIndex * 64;

            if (!block->GpuNodesTextCacheValid[cacheIndex])
            {
                block->GpuNodesTextCacheLength[cacheIndex] = 0;

                if (gpuUsage >= 0.01f)
                {
                    PH_FORMAT format;
                    SIZE_T returnLength;

                    PhInitFormatF(&format, gpuUsage, 2);

                    if (PhFormatToBuffer(&format, 1, textBuffer, sizeof(WCHAR) * 64, &returnLength))
                        block->GpuNodesTextCacheLength[cacheIndex] = returnLength - sizeof(UNICODE_NULL);
                }

                block->GpuNodesTextCacheValid[cacheIndex] = TRUE;
            }

            if (block->GpuNodesTextCacheLength[cacheIndex])
            {
                getCellText->Text.Buffer = textBuffer;
                getCellText->Text.Length = block->GpuNodesTextCacheLength[cacheIndex];
            }

            PhReleaseQueuedLockExclusive(&block->TextCacheLock);
            return;
        }

        PhAcquireQueuedLockExclusive(&block->TextCacheLock);

        if (block->TextCacheValid[message->SubId])
        {
            if (block->TextCacheLength[message->SubId])
            {
                getCellText->Text.Length = block->TextCacheLength[message->SubId];
                getCellText->Text.Buffer = block->TextCache[message->SubId];
            }
        }
        else
        {
            switch (message->SubId)
            {
            case ETPRTNC_DISKREADS:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadCount), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_DISKWRITES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteCount), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_DISKREADBYTES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadRaw), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_DISKWRITEBYTES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteRaw), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_DISKTOTALBYTES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadRaw), &number);
                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteRaw), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_DISKREADSDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadDelta.Delta), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_DISKWRITESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteDelta.Delta), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_DISKREADBYTESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_DISKWRITEBYTESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_DISKTOTALBYTESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadRawDelta.Delta), &number);
                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKRECEIVES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveCount), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKSENDS:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendCount), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKRECEIVEBYTES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveRaw), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKSENDBYTES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendRaw), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKTOTALBYTES:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveRaw), &number);
                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendRaw), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKRECEIVESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKSENDSDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKRECEIVEBYTESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveRawDelta.Delta), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKSENDBYTESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendRawDelta.Delta), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKTOTALBYTESDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveRawDelta.Delta), &number);
                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendRawDelta.Delta), &number);

                    EtFormatSize(number, block, message);
                }
                break;
            case ETPRTNC_HARDFAULTS:
                EtFormatInt64(processNode->ProcessItem->HardFaultsDelta.Value, block, message);
                break;
            case ETPRTNC_HARDFAULTSDELTA:
                if (processNode->ProcessItem->HardFaultsDelta.Delta != 0)
                    EtFormatInt64(processNode->ProcessItem->HardFaultsDelta.Delta, block, message);
                break;
            case ETPRTNC_PEAKTHREADS:
                EtFormatInt64(block->ProcessItem->PeakNumberOfThreads, block, message);
                break;
            case ETPRTNC_GPU:
                {
                    FLOAT gpuUsage = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeFloat,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, GpuNodeUtilization),
                        &gpuUsage
                        );

                    gpuUsage *= 100;
                    EtFormatDouble(gpuUsage, block, message);
                }
                break;
            case ETPRTNC_GPUDEDICATEDBYTES:
                {
                    ULONG64 gpuDedicatedUsage = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, GpuDedicatedUsage),
                        &gpuDedicatedUsage
                        );

                    EtFormatSize(gpuDedicatedUsage, block, message);
                }
                break;
            case ETPRTNC_GPUSHAREDBYTES:
                {
                    ULONG64 gpuSharedUsage = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, GpuSharedUsage),
                        &gpuSharedUsage
                        );

                    EtFormatSize(gpuSharedUsage, block, message);
                }
                break;
            case ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES:
                {
                    ULONG64 gpuDedicatedCommitted = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, GpuDedicatedCommitted),
                        &gpuDedicatedCommitted
                        );

                    EtFormatSize(gpuDedicatedCommitted, block, message);
                }
                break;
            case ETPRTNC_GPUSHAREDCOMMITTEDBYTES:
                {
                    ULONG64 gpuSharedCommitted = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, GpuSharedCommitted),
                        &gpuSharedCommitted
                        );

                    EtFormatSize(gpuSharedCommitted, block, message);
                }
                break;
            case ETPRTNC_DISKREADRATE:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_DISKWRITERATE:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_DISKTOTALRATE:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskReadRawDelta.Delta), &number);
                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, DiskWriteRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKRECEIVERATE:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKSENDRATE:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_NETWORKTOTALRATE:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkReceiveRawDelta.Delta), &number);
                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, NetworkSendRawDelta.Delta), &number);

                    EtFormatRate(number, block, message);
                }
                break;
            case ETPRTNC_FPS:
                {
                    FLOAT frames = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeFloat,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, FramesPerSecond),
                        &frames
                        );

                    EtFormatDouble(frames, block, message);
                }
                break;
            case ETPRTNC_NPU:
                {
                    FLOAT npuUsage = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeFloat,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, NpuNodeUtilization),
                        &npuUsage
                        );

                    npuUsage *= 100;
                    EtFormatDouble(npuUsage, block, message);
                }
                break;
            case ETPRTNC_NPUDEDICATEDBYTES:
                {
                    ULONG64 npuDedicatedUsage = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, NpuDedicatedUsage),
                        &npuDedicatedUsage
                        );

                    EtFormatSize(npuDedicatedUsage, block, message);
                }
                break;
            case ETPRTNC_NPUSHAREDBYTES:
                {
                    ULONG64 npuSharedUsage = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, NpuSharedUsage),
                        &npuSharedUsage
                        );

                    EtFormatSize(npuSharedUsage, block, message);
                }
                break;
            case ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES:
                {
                    ULONG64 npuDedicatedCommitted = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, NpuDedicatedCommitted),
                        &npuDedicatedCommitted
                        );

                    EtFormatSize(npuDedicatedCommitted, block, message);
                }
                break;
            case ETPRTNC_NPUSHAREDCOMMITTEDBYTES:
                {
                    ULONG64 npuSharedCommitted = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, NpuSharedCommitted),
                        &npuSharedCommitted
                        );

                    EtFormatSize(npuSharedCommitted, block, message);
                }
                break;
            case ETPRTNC_FIREWALLALLOWS:
                {
                    ULONG64 firewallAllowCount = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, FirewallAllowCount),
                        &firewallAllowCount
                        );

                    EtFormatInt64(firewallAllowCount, block, message);
                }
                break;
            case ETPRTNC_FIREWALLBLOCKS:
                {
                    ULONG64 firewallBlockCount = 0;

                    PhpAggregateFieldIfNeeded(
                        processNode,
                        AggregateTypeInt64,
                        block,
                        FIELD_OFFSET(ET_PROCESS_BLOCK, FirewallBlockCount),
                        &firewallBlockCount
                        );

                    EtFormatInt64(firewallBlockCount, block, message);
                }
                break;
            case ETPRTNC_FIREWALLALLOWSDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, FirewallAllowDelta.Delta), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            case ETPRTNC_FIREWALLBLOCKSDELTA:
                {
                    ULONG64 number = 0;

                    PhpAggregateFieldIfNeeded(processNode, AggregateTypeInt64, block, FIELD_OFFSET(ET_PROCESS_BLOCK, FirewallBlockDelta.Delta), &number);

                    EtFormatInt64(number, block, message);
                }
                break;
            }

            if (block->TextCacheLength[message->SubId])
            {
                getCellText->Text.Length = block->TextCacheLength[message->SubId];
                getCellText->Text.Buffer = block->TextCache[message->SubId];
            }

            block->TextCacheValid[message->SubId] = TRUE;
        }

        PhReleaseQueuedLockExclusive(&block->TextCacheLock);
    }
    else if (message->Message == TreeNewSortChanged)
    {
        PPH_TREENEW_SORT_CHANGED_EVENT sorting = message->Parameter1;

        ProcessTreeListSortColumn = sorting->SortColumn;
        ProcessTreeListSortOrder = sorting->SortOrder;
    }
    else if (message->Message == TreeNewNodeExpanding)
    {
        processNode = message->Parameter1;
        block = EtGetProcessBlock(processNode->ProcessItem);

        if (EtPropagateCpuUsage)
        {
            if (block->GpuNodesTextCacheValid)
                memset(block->GpuNodesTextCacheValid, 0, sizeof(BOOLEAN) * (EtGetGpuAdapterCount() + EtGpuTotalNodeCount));

            block->TextCacheValid[ETPRTNC_DISKTOTALBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_NETWORKTOTALBYTES] = FALSE;

            block->TextCacheValid[ETPRTNC_DISKTOTALBYTESDELTA] = FALSE;
            block->TextCacheValid[ETPRTNC_NETWORKTOTALBYTESDELTA] = FALSE;

            block->TextCacheValid[ETPRTNC_GPU] = FALSE;
            block->TextCacheValid[ETPRTNC_GPUDEDICATEDBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_GPUSHAREDBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_GPUSHAREDCOMMITTEDBYTES] = FALSE;

            block->TextCacheValid[ETPRTNC_DISKTOTALRATE] = FALSE;
            block->TextCacheValid[ETPRTNC_NETWORKTOTALRATE] = FALSE;

            block->TextCacheValid[ETPRTNC_FPS] = FALSE;

            block->TextCacheValid[ETPRTNC_NPU] = FALSE;
            block->TextCacheValid[ETPRTNC_NPUDEDICATEDBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_NPUSHAREDBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES] = FALSE;
            block->TextCacheValid[ETPRTNC_NPUSHAREDCOMMITTEDBYTES] = FALSE;

            block->TextCacheValid[ETPRTNC_FIREWALLALLOWS] = FALSE;
            block->TextCacheValid[ETPRTNC_FIREWALLBLOCKS] = FALSE;
        }
    }
    else if (message->Message == TreeNewGetHeaderText)
    {
        PPH_TREENEW_GET_HEADER_TEXT getHeaderText = message->Parameter1;
        PPH_TREENEW_COLUMN column = getHeaderText->Column;
        PLIST_ENTRY listEntry;
        SIZE_T returnLength;
        FLOAT decimal = 0;
        ULONG64 number = 0;

        if ((message->SubId >= ETPRTNC_GPUADAPTER_FIRST &&
            message->SubId < ETPRTNC_GPUADAPTER_FIRST + EtGetGpuAdapterCount()) ||
            (message->SubId >= ETPRTNC_GPUNODE_FIRST &&
            message->SubId < ETPRTNC_GPUNODE_FIRST + EtGpuTotalNodeCount))
        {
            BOOLEAN nodeColumn = message->SubId >= ETPRTNC_GPUNODE_FIRST;
            ULONG valueIndex = nodeColumn ?
                message->SubId - ETPRTNC_GPUNODE_FIRST :
                message->SubId - ETPRTNC_GPUADAPTER_FIRST;

            listEntry = EtProcessBlockListHead.Flink;

            while (listEntry != &EtProcessBlockListHead)
            {
                block = CONTAINING_RECORD(listEntry, ET_PROCESS_BLOCK, ListEntry);

                if (!(block->ProcessItem->State & PH_PROCESS_ITEM_REMOVED) &&
                    block->ProcessNode && block->ProcessNode->Node.Visible &&
                    block->GpuNodesUtilization)
                {
                    if (nodeColumn)
                        decimal += block->GpuNodesUtilization[valueIndex];
                    else
                        decimal += EtpGetGpuAdapterOwnValue(block, valueIndex);
                }

                listEntry = listEntry->Flink;
            }

            if (decimal != 0.f)
            {
                PH_FORMAT format[2];

                if (nodeColumn)
                    decimal = min(decimal, 1.f);

                PhInitFormatF(&format[0], decimal * 100.f, 2);
                PhInitFormatC(&format[1], L'%');

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }

            return;
        }

        switch (message->SubId)
        {
        case ETPRTNC_DISKREADS:
        case ETPRTNC_DISKWRITES:
        case ETPRTNC_DISKREADBYTES:
        case ETPRTNC_DISKWRITEBYTES:
        case ETPRTNC_DISKTOTALBYTES:
        case ETPRTNC_DISKREADSDELTA:
        case ETPRTNC_DISKWRITESDELTA:
        case ETPRTNC_DISKREADBYTESDELTA:
        case ETPRTNC_DISKWRITEBYTESDELTA:
        case ETPRTNC_DISKTOTALBYTESDELTA:
        case ETPRTNC_NETWORKRECEIVES:
        case ETPRTNC_NETWORKSENDS:
        case ETPRTNC_NETWORKRECEIVEBYTES:
        case ETPRTNC_NETWORKSENDBYTES:
        case ETPRTNC_NETWORKTOTALBYTES:
        case ETPRTNC_NETWORKRECEIVESDELTA:
        case ETPRTNC_NETWORKSENDSDELTA:
        case ETPRTNC_NETWORKRECEIVEBYTESDELTA:
        case ETPRTNC_NETWORKSENDBYTESDELTA:
        case ETPRTNC_NETWORKTOTALBYTESDELTA:
        case ETPRTNC_HARDFAULTS:
        case ETPRTNC_HARDFAULTSDELTA:
        case ETPRTNC_PEAKTHREADS:
        case ETPRTNC_GPU:
        case ETPRTNC_GPUDEDICATEDBYTES:
        case ETPRTNC_GPUSHAREDBYTES:
        case ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES:
        case ETPRTNC_GPUSHAREDCOMMITTEDBYTES:
        case ETPRTNC_DISKREADRATE:
        case ETPRTNC_DISKWRITERATE:
        case ETPRTNC_DISKTOTALRATE:
        case ETPRTNC_NETWORKRECEIVERATE:
        case ETPRTNC_NETWORKSENDRATE:
        case ETPRTNC_NETWORKTOTALRATE:
        case ETPRTNC_FPS:
        case ETPRTNC_NPU:
        case ETPRTNC_NPUDEDICATEDBYTES:
        case ETPRTNC_NPUSHAREDBYTES:
        case ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES:
        case ETPRTNC_NPUSHAREDCOMMITTEDBYTES:
        case ETPRTNC_FIREWALLALLOWS:
        case ETPRTNC_FIREWALLBLOCKS:
        case ETPRTNC_FIREWALLALLOWSDELTA:
        case ETPRTNC_FIREWALLBLOCKSDELTA:
            break;
        default:
            return;
        }

        listEntry = EtProcessBlockListHead.Flink;

        while (listEntry != &EtProcessBlockListHead)
        {
            block = CONTAINING_RECORD(listEntry, ET_PROCESS_BLOCK, ListEntry);

            if (block->ProcessItem->State & PH_PROCESS_ITEM_REMOVED)
            {
                listEntry = listEntry->Flink;
                continue; // Skip terminated.
            }

            if (block->ProcessNode)
            {
                if (!block->ProcessNode->Node.Visible)
                {
                    listEntry = listEntry->Flink;
                    continue; // Skip filtered nodes.
                }
            }
            else
            {
                listEntry = listEntry->Flink;
                continue; // Skip filtered nodes.
            }

            switch (message->SubId)
            {
            case ETPRTNC_DISKREADS:
                number += block->DiskReadCount;
                break;
            case ETPRTNC_DISKWRITES:
                number += block->DiskWriteCount;
                break;
            case ETPRTNC_DISKREADBYTES:
                number += block->DiskReadRaw;
                break;
            case ETPRTNC_DISKWRITEBYTES:
                number += block->DiskWriteRaw;
                break;
            case ETPRTNC_DISKTOTALBYTES:
                number += block->DiskReadRaw + block->DiskWriteRaw;
                break;
            case ETPRTNC_DISKREADSDELTA:
                number += block->DiskReadDelta.Delta;
                break;
            case ETPRTNC_DISKWRITESDELTA:
                number += block->DiskWriteDelta.Delta;
                break;
            case ETPRTNC_DISKREADBYTESDELTA:
                number += block->DiskReadRawDelta.Delta;
                break;
            case ETPRTNC_DISKWRITEBYTESDELTA:
                number += block->DiskWriteRawDelta.Delta;
                break;
            case ETPRTNC_DISKTOTALBYTESDELTA:
                number += block->DiskReadRawDelta.Delta + block->DiskWriteRawDelta.Delta;
                break;
            case ETPRTNC_NETWORKRECEIVES:
                number += block->NetworkReceiveCount;
                break;
            case ETPRTNC_NETWORKSENDS:
                number += block->NetworkSendCount;
                break;
            case ETPRTNC_NETWORKRECEIVEBYTES:
                number += block->NetworkReceiveRaw;
                break;
            case ETPRTNC_NETWORKSENDBYTES:
                number += block->NetworkSendRaw;
                break;
            case ETPRTNC_NETWORKTOTALBYTES:
                number += block->NetworkReceiveRaw + block->NetworkSendRaw;
                break;
            case ETPRTNC_NETWORKRECEIVESDELTA:
                number += block->NetworkReceiveDelta.Delta;
                break;
            case ETPRTNC_NETWORKSENDSDELTA:
                number += block->NetworkSendDelta.Delta;
                break;
            case ETPRTNC_NETWORKRECEIVEBYTESDELTA:
                number += block->NetworkReceiveRawDelta.Delta;
                break;
            case ETPRTNC_NETWORKSENDBYTESDELTA:
                number += block->NetworkSendRawDelta.Delta;
                break;
            case ETPRTNC_NETWORKTOTALBYTESDELTA:
                number += block->NetworkReceiveRawDelta.Delta + block->NetworkSendRawDelta.Delta;
                break;
            case ETPRTNC_HARDFAULTS:
                number += block->ProcessItem->HardFaultsDelta.Value;
                break;
            case ETPRTNC_HARDFAULTSDELTA:
                number += block->ProcessItem->HardFaultsDelta.Delta;
                break;
            case ETPRTNC_PEAKTHREADS:
                number += block->ProcessItem->PeakNumberOfThreads;
                break;
            case ETPRTNC_GPU:
                decimal += block->GpuNodeUtilization;
                break;
            case ETPRTNC_GPUDEDICATEDBYTES:
                number += block->GpuDedicatedUsage;
                break;
            case ETPRTNC_GPUSHAREDBYTES:
                number += block->GpuSharedUsage;
                break;
            case ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES:
                number += block->GpuDedicatedCommitted;
                break;
            case ETPRTNC_GPUSHAREDCOMMITTEDBYTES:
                number += block->GpuSharedCommitted;
                break;
            case ETPRTNC_DISKREADRATE:
                number += block->DiskReadRawDelta.Delta;
                break;
            case ETPRTNC_DISKWRITERATE:
                number += block->DiskWriteRawDelta.Delta;
                break;
            case ETPRTNC_DISKTOTALRATE:
                number += block->DiskReadRawDelta.Delta + block->DiskWriteRawDelta.Delta;
                break;
            case ETPRTNC_NETWORKRECEIVERATE:
                number += block->NetworkReceiveRawDelta.Delta;
                break;
            case ETPRTNC_NETWORKSENDRATE:
                number += block->NetworkSendRawDelta.Delta;
                break;
            case ETPRTNC_NETWORKTOTALRATE:
                number += block->NetworkReceiveRawDelta.Delta + block->NetworkSendRawDelta.Delta;
                break;
            case ETPRTNC_FPS:
                decimal += block->FramesPerSecond;
                break;
            case ETPRTNC_NPU:
                decimal += block->NpuNodeUtilization;
                break;
            case ETPRTNC_NPUDEDICATEDBYTES:
                number += block->NpuDedicatedUsage;
                break;
            case ETPRTNC_NPUSHAREDBYTES:
                number += block->NpuSharedUsage;
                break;
            case ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES:
                number += block->NpuDedicatedCommitted;
                break;
            case ETPRTNC_NPUSHAREDCOMMITTEDBYTES:
                number += block->NpuSharedCommitted;
                break;
            case ETPRTNC_FIREWALLALLOWS:
                number += block->FirewallAllowCount;
                break;
            case ETPRTNC_FIREWALLBLOCKS:
                number += block->FirewallBlockCount;
                break;
            case ETPRTNC_FIREWALLALLOWSDELTA:
                number += block->FirewallAllowDelta.Delta;
                break;
            case ETPRTNC_FIREWALLBLOCKSDELTA:
                number += block->FirewallBlockDelta.Delta;
                break;
            }

            listEntry = listEntry->Flink;
        }

        switch (message->SubId)
        {
        case ETPRTNC_DISKREADS:
        case ETPRTNC_DISKREADSDELTA:
        case ETPRTNC_DISKWRITES:
        case ETPRTNC_DISKWRITESDELTA:
        case ETPRTNC_HARDFAULTS:
        case ETPRTNC_HARDFAULTSDELTA:
        case ETPRTNC_NETWORKRECEIVES:
        case ETPRTNC_NETWORKRECEIVESDELTA:
        case ETPRTNC_NETWORKSENDS:
        case ETPRTNC_NETWORKSENDSDELTA:
        case ETPRTNC_PEAKTHREADS:
        case ETPRTNC_FIREWALLALLOWS:
        case ETPRTNC_FIREWALLBLOCKS:
            {
                PH_FORMAT format[1];

                if (number == 0)
                    break;

                PhInitFormatI64UGroupDigits(&format[0], number);

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }
            break;
        case ETPRTNC_DISKREADBYTES:
        case ETPRTNC_DISKWRITEBYTES:
        case ETPRTNC_DISKTOTALBYTES:
        case ETPRTNC_DISKREADBYTESDELTA:
        case ETPRTNC_DISKWRITEBYTESDELTA:
        case ETPRTNC_DISKTOTALBYTESDELTA:
        case ETPRTNC_NETWORKRECEIVEBYTES:
        case ETPRTNC_NETWORKSENDBYTES:
        case ETPRTNC_NETWORKTOTALBYTES:
        case ETPRTNC_NETWORKRECEIVEBYTESDELTA:
        case ETPRTNC_NETWORKSENDBYTESDELTA:
        case ETPRTNC_NETWORKTOTALBYTESDELTA:
        case ETPRTNC_GPUDEDICATEDBYTES:
        case ETPRTNC_GPUSHAREDBYTES:
        case ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES:
        case ETPRTNC_GPUSHAREDCOMMITTEDBYTES:
        case ETPRTNC_NPUDEDICATEDBYTES:
        case ETPRTNC_NPUSHAREDBYTES:
        case ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES:
        case ETPRTNC_NPUSHAREDCOMMITTEDBYTES:
            {
                PH_FORMAT format[1];

                if (number == 0)
                    break;

                PhInitFormatSize(&format[0], number);

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }
            break;
        case ETPRTNC_DISKREADRATE:
        case ETPRTNC_DISKWRITERATE:
        case ETPRTNC_DISKTOTALRATE:
        case ETPRTNC_NETWORKRECEIVERATE:
        case ETPRTNC_NETWORKSENDRATE:
        case ETPRTNC_NETWORKTOTALRATE:
            {
                PH_FORMAT format[2];
                ULONG64 value;

                if (number == 0)
                    break;

                value = number;
                value *= 1000;
                value /= EtUpdateInterval;

                PhInitFormatSize(&format[0], value);
                PhInitFormatS(&format[1], L"/s");

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }
            break;
        case ETPRTNC_GPU:
            {
                PH_FORMAT format[2];

                if (decimal == 0.f)
                    break;

                decimal *= 100.f;
                PhInitFormatF(&format[0], decimal, 2);
                PhInitFormatC(&format[1], L'%');

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }
            break;
        case ETPRTNC_FPS:
            {
                PH_FORMAT format[1];

                if (decimal == 0.f)
                    break;

                PhInitFormatF(&format[0], decimal, 2);

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }
            break;
        case ETPRTNC_NPU:
            {
                PH_FORMAT format[2];

                if (decimal == 0.f)
                    break;

                decimal *= 100.f;
                PhInitFormatF(&format[0], decimal, 2);
                PhInitFormatC(&format[1], L'%');

                if (PhFormatToBuffer(format, RTL_NUMBER_OF(format), getHeaderText->TextCache, getHeaderText->TextCacheSize, &returnLength))
                {
                    getHeaderText->Text.Buffer = getHeaderText->TextCache;
                    getHeaderText->Text.Length = returnLength - sizeof(UNICODE_NULL);
                }
            }
            break;
        }
    }
}

FORCEINLINE LONG EtpSortAggregateIfNeeded(
    _In_ PPH_PROCESS_NODE ProcessNode1,
    _In_ PET_PROCESS_BLOCK Block1,
    _In_ PPH_PROCESS_NODE ProcessNode2,
    _In_ PET_PROCESS_BLOCK Block2,
    _In_ SIZE_T FieldOffset
    )
{
    ULONG64 number1 = 0;
    ULONG64 number2 = 0;

    PhpAggregateFieldIfNeeded(ProcessNode1, AggregateTypeInt64, Block1, FieldOffset, &number1);
    PhpAggregateFieldIfNeeded(ProcessNode2, AggregateTypeInt64, Block2, FieldOffset, &number2);

    return uint64cmp(number1, number2);
}

#define ET_SORT_AGGREGATE_IF_NEEDED(Field)                                     \
    EtpSortAggregateIfNeeded(                                                  \
        node1,                                                                 \
        block1,                                                                \
        node2,                                                                 \
        block2,                                                                \
        FIELD_OFFSET(ET_PROCESS_BLOCK, Field)                                  \
        )

FORCEINLINE LONG EtpSortAggregateIfNeeded2(
    _In_ PPH_PROCESS_NODE ProcessNode1,
    _In_ PET_PROCESS_BLOCK Block1,
    _In_ PPH_PROCESS_NODE ProcessNode2,
    _In_ PET_PROCESS_BLOCK Block2,
    _In_ SIZE_T FieldOffset1,
    _In_ SIZE_T FieldOffset2
    )
{
    ULONG64 number1 = 0;
    ULONG64 number2 = 0;

    PhpAggregateFieldIfNeeded(ProcessNode1, AggregateTypeInt64, Block1, FieldOffset1, &number1);
    PhpAggregateFieldIfNeeded(ProcessNode1, AggregateTypeInt64, Block1, FieldOffset2, &number1);

    PhpAggregateFieldIfNeeded(ProcessNode2, AggregateTypeInt64, Block2, FieldOffset1, &number2);
    PhpAggregateFieldIfNeeded(ProcessNode2, AggregateTypeInt64, Block2, FieldOffset2, &number2);

    return uint64cmp(number1, number2);
}

#define ET_SORT_AGGREGATE_IF_NEEDED_2(Field1, Field2)                          \
    EtpSortAggregateIfNeeded2(                                                 \
        node1,                                                                 \
        block1,                                                                \
        node2,                                                                 \
        block2,                                                                \
        FIELD_OFFSET(ET_PROCESS_BLOCK, Field1),                                \
        FIELD_OFFSET(ET_PROCESS_BLOCK, Field2)                                 \
        )

_Function_class_(PH_PLUGIN_TREENEW_SORT_FUNCTION)
LONG EtpProcessTreeNewSortFunction(
    _In_ PVOID Node1,
    _In_ PVOID Node2,
    _In_ ULONG SubId,
    _In_ PH_SORT_ORDER SortOrder,
    _In_ PVOID Context
    )
{
    LONG result;
    PPH_PROCESS_NODE node1 = Node1;
    PPH_PROCESS_NODE node2 = Node2;
    PET_PROCESS_BLOCK block1;
    PET_PROCESS_BLOCK block2;

    block1 = EtGetProcessBlock(node1->ProcessItem);
    block2 = EtGetProcessBlock(node2->ProcessItem);

    result = 0;

    if (SubId >= ETPRTNC_GPUADAPTER_FIRST &&
        SubId < ETPRTNC_GPUADAPTER_FIRST + EtGetGpuAdapterCount())
    {
        ULONG adapterIndex = SubId - ETPRTNC_GPUADAPTER_FIRST;
        FLOAT value1 = EtpGetGpuAdapterValue(node1, block1, adapterIndex);
        FLOAT value2 = EtpGetGpuAdapterValue(node2, block2, adapterIndex);

        return singlecmp(value1, value2);
    }

    if (SubId >= ETPRTNC_GPUNODE_FIRST &&
        SubId < ETPRTNC_GPUNODE_FIRST + EtGpuTotalNodeCount)
    {
        ULONG nodeIndex = SubId - ETPRTNC_GPUNODE_FIRST;
        FLOAT value1 = EtpGetGpuNodeValue(node1, block1, nodeIndex);
        FLOAT value2 = EtpGetGpuNodeValue(node2, block2, nodeIndex);

        return singlecmp(value1, value2);
    }

    switch (SubId)
    {
    case ETPRTNC_DISKREADS:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskReadCount);
        break;
    case ETPRTNC_DISKWRITES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskWriteCount);
        break;
    case ETPRTNC_DISKREADBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskReadRaw);
        break;
    case ETPRTNC_DISKWRITEBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskWriteRaw);
        break;
    case ETPRTNC_DISKTOTALBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED_2(DiskReadRaw, DiskWriteRaw);
        break;
    case ETPRTNC_DISKREADSDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskReadDelta.Delta);
        break;
    case ETPRTNC_DISKWRITESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskWriteDelta.Delta);
        break;
    case ETPRTNC_DISKREADBYTESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskReadRawDelta.Delta);
        break;
    case ETPRTNC_DISKWRITEBYTESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskWriteRawDelta.Delta);
        break;
    case ETPRTNC_DISKTOTALBYTESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED_2(DiskReadRawDelta.Delta, DiskWriteRawDelta.Delta);
        break;
    case ETPRTNC_NETWORKRECEIVES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkReceiveCount);
        break;
    case ETPRTNC_NETWORKSENDS:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkSendCount);
        break;
    case ETPRTNC_NETWORKRECEIVEBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkReceiveRaw);
        break;
    case ETPRTNC_NETWORKSENDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkSendRaw);
        break;
    case ETPRTNC_NETWORKTOTALBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED_2(NetworkReceiveRaw, NetworkSendRaw);
        break;
    case ETPRTNC_NETWORKRECEIVESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkReceiveDelta.Delta);
        break;
    case ETPRTNC_NETWORKSENDSDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkSendDelta.Delta);
        break;
    case ETPRTNC_NETWORKRECEIVEBYTESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkReceiveRawDelta.Delta);
        break;
    case ETPRTNC_NETWORKSENDBYTESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkSendRawDelta.Delta);
        break;
    case ETPRTNC_NETWORKTOTALBYTESDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED_2(NetworkReceiveRawDelta.Delta, NetworkSendRawDelta.Delta);
        break;
    case ETPRTNC_HARDFAULTS:
        result = uintcmp(block1->ProcessItem->HardFaultsDelta.Value, block2->ProcessItem->HardFaultsDelta.Value);
        break;
    case ETPRTNC_HARDFAULTSDELTA:
        result = uintcmp(block1->ProcessItem->HardFaultsDelta.Delta, block2->ProcessItem->HardFaultsDelta.Delta);
        break;
    case ETPRTNC_PEAKTHREADS:
        result = uintcmp(block1->ProcessItem->PeakNumberOfThreads, block2->ProcessItem->PeakNumberOfThreads);
        break;
    case ETPRTNC_GPU:
        result = ET_SORT_AGGREGATE_IF_NEEDED(GpuNodeUtilization);
        break;
    case ETPRTNC_GPUDEDICATEDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(GpuDedicatedUsage);
        break;
    case ETPRTNC_GPUSHAREDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(GpuSharedUsage);
        break;
    case ETPRTNC_GPUDEDICATEDCOMMITTEDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(GpuDedicatedCommitted);
        break;
    case ETPRTNC_GPUSHAREDCOMMITTEDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(GpuSharedCommitted);
        break;
    case ETPRTNC_DISKREADRATE:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskReadRawDelta.Delta);
        break;
    case ETPRTNC_DISKWRITERATE:
        result = ET_SORT_AGGREGATE_IF_NEEDED(DiskWriteRawDelta.Delta);
        break;
    case ETPRTNC_DISKTOTALRATE:
        result = ET_SORT_AGGREGATE_IF_NEEDED_2(DiskReadRawDelta.Delta, DiskWriteRawDelta.Delta);
        break;
    case ETPRTNC_NETWORKRECEIVERATE:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkReceiveRawDelta.Delta);
        break;
    case ETPRTNC_NETWORKSENDRATE:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NetworkSendRawDelta.Delta);
        break;
    case ETPRTNC_NETWORKTOTALRATE:
        result = ET_SORT_AGGREGATE_IF_NEEDED_2(NetworkReceiveRawDelta.Delta, NetworkSendRawDelta.Delta);
        break;
    case ETPRTNC_FPS:
        result = ET_SORT_AGGREGATE_IF_NEEDED(FramesPerSecond);
        break;
    case ETPRTNC_NPU:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NpuNodeUtilization);
        break;
    case ETPRTNC_NPUDEDICATEDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NpuDedicatedUsage);
        break;
    case ETPRTNC_NPUSHAREDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NpuSharedUsage);
        break;
    case ETPRTNC_NPUDEDICATEDCOMMITTEDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NpuDedicatedCommitted);
        break;
    case ETPRTNC_NPUSHAREDCOMMITTEDBYTES:
        result = ET_SORT_AGGREGATE_IF_NEEDED(NpuSharedCommitted);
        break;
    case ETPRTNC_FIREWALLALLOWS:
        result = ET_SORT_AGGREGATE_IF_NEEDED(FirewallAllowCount);
        break;
    case ETPRTNC_FIREWALLBLOCKS:
        result = ET_SORT_AGGREGATE_IF_NEEDED(FirewallBlockCount);
        break;
    case ETPRTNC_FIREWALLALLOWSDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(FirewallAllowDelta.Delta);
        break;
    case ETPRTNC_FIREWALLBLOCKSDELTA:
        result = ET_SORT_AGGREGATE_IF_NEEDED(FirewallBlockDelta.Delta);
        break;
    }

    return result;
}

VOID EtNetworkTreeNewInitializing(
    _In_ PVOID Parameter
    )
{
    const static COLUMN_INFO columns[] =
    {
        { ETNETNC_RECEIVES, IDS_ET_RECEIVES, L"Receives", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_SENDS, IDS_ET_SENDS, L"Sends", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_RECEIVEBYTES, IDS_ET_RECEIVE_BYTES, L"Receive bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_SENDBYTES, IDS_ET_SEND_BYTES, L"Send bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_TOTALBYTES, IDS_ET_TOTAL_BYTES, L"Total bytes", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_RECEIVESDELTA, IDS_ET_NETWORK_COLUMN_RECEIVES_DELTA, L"Receives delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_SENDSDELTA, IDS_ET_NETWORK_COLUMN_SENDS_DELTA, L"Sends delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_RECEIVEBYTESDELTA, IDS_ET_RECEIVE_BYTES_DELTA, L"Receive bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_SENDBYTESDELTA, IDS_ET_SEND_BYTES_DELTA, L"Send bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_TOTALBYTESDELTA, IDS_ET_TOTAL_BYTES_DELTA, L"Total bytes delta", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_FIREWALLSTATUS, IDS_ET_NETWORK_COLUMN_FIREWALL_STATUS, L"Firewall status", 170, PH_ALIGN_LEFT, 0, FALSE },
        { ETNETNC_RECEIVERATE, IDS_ET_NETWORK_COLUMN_RECEIVE_RATE, L"Receive rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_SENDRATE, IDS_ET_NETWORK_COLUMN_SEND_RATE, L"Send rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE },
        { ETNETNC_TOTALRATE, IDS_ET_DISK_COLUMN_TOTAL_RATE, L"Total rate", 70, PH_ALIGN_RIGHT, DT_RIGHT, TRUE }
    };

    PPH_PLUGIN_TREENEW_INFORMATION treeNewInfo = Parameter;
    ULONG i;

    for (i = 0; i < sizeof(columns) / sizeof(COLUMN_INFO); i++)
    {
        EtpAddTreeNewColumn(treeNewInfo, columns[i].SubId, EtGetUiString(columns[i].TextResourceId, columns[i].Text), columns[i].Width, columns[i].Alignment,
            columns[i].TextFlags, columns[i].SortDescending, EtpNetworkTreeNewSortFunction);
    }
}

VOID EtpUpdateFirewallStatus(
    _Inout_ PET_NETWORK_BLOCK Block
    )
{
    if (!Block->FirewallStatusValid)
    {
        Block->FirewallStatus = EtQueryFirewallStatus(Block->NetworkItem);
        Block->FirewallStatusValid = TRUE;
    }
}

VOID EtNetworkTreeNewMessage(
    _In_ PVOID Parameter
    )
{
    PPH_PLUGIN_TREENEW_MESSAGE message = Parameter;

    if (message->Message == TreeNewGetCellText)
    {
        PPH_TREENEW_GET_CELL_TEXT getCellText = message->Parameter1;
        PPH_NETWORK_NODE networkNode = (PPH_NETWORK_NODE)getCellText->Node;
        PET_NETWORK_BLOCK block = EtGetNetworkBlock(networkNode->NetworkItem);

        PhAcquireQueuedLockExclusive(&block->TextCacheLock);

        if (block->TextCacheValid[message->SubId])
        {
            if (block->TextCacheLength[message->SubId])
            {
                getCellText->Text.Length = block->TextCacheLength[message->SubId];
                getCellText->Text.Buffer = block->TextCache[message->SubId];
            }
        }
        else
        {
            switch (message->SubId)
            {
            case ETNETNC_RECEIVES:
                EtFormatNetworkInt64(block->ReceiveCount, block, message);
                break;
            case ETNETNC_SENDS:
                EtFormatNetworkInt64(block->SendCount, block, message);
                break;
            case ETNETNC_RECEIVEBYTES:
                EtFormatNetworkSize(block->ReceiveRaw, block, message);
                break;
            case ETNETNC_SENDBYTES:
                EtFormatNetworkSize(block->SendRaw, block, message);
                break;
            case ETNETNC_TOTALBYTES:
                EtFormatNetworkSize(block->ReceiveRaw + block->SendRaw, block, message);
                break;
            case ETNETNC_RECEIVESDELTA:
                EtFormatNetworkInt64(block->ReceiveDelta.Delta, block, message);
                break;
            case ETNETNC_SENDSDELTA:
                EtFormatNetworkInt64(block->SendDelta.Delta, block, message);
                break;
            case ETNETNC_RECEIVEBYTESDELTA:
                EtFormatNetworkSize(block->ReceiveRawDelta.Delta, block, message);
                break;
            case ETNETNC_SENDBYTESDELTA:
                EtFormatNetworkSize(block->SendRawDelta.Delta, block, message);
                break;
            case ETNETNC_TOTALBYTESDELTA:
                EtFormatNetworkSize(block->ReceiveRawDelta.Delta + block->SendRawDelta.Delta, block, message);
                break;
            case ETNETNC_FIREWALLSTATUS:
                {
                    EtpUpdateFirewallStatus(block);

                    if (block->FirewallStatus >= FirewallUnknownStatus && block->FirewallStatus < FirewallMaximumStatus)
                    {
                        static CONST PH_STRINGREF strings[FirewallMaximumStatus] =
                        {
                            PH_STRINGREF_INIT(L"Unknown"),
                            PH_STRINGREF_INIT(L"Allowed, not restricted"),
                            PH_STRINGREF_INIT(L"Allowed, restricted"),
                            PH_STRINGREF_INIT(L"Not allowed, not restricted"),
                            PH_STRINGREF_INIT(L"Not allowed, restricted"),
                        };

                        block->TextCacheLength[message->SubId] = strings[block->FirewallStatus].Length;
                        memcpy_s(
                            block->TextCache[message->SubId],
                            sizeof(block->TextCache[message->SubId]),
                            strings[block->FirewallStatus].Buffer,
                            strings[block->FirewallStatus].Length
                            );
                    }
                }
                break;
            case ETNETNC_RECEIVERATE:
                EtFormatNetworkRate(block->ReceiveRawDelta.Delta, block, message);
                break;
            case ETNETNC_SENDRATE:
                EtFormatNetworkRate(block->SendRawDelta.Delta, block, message);
                break;
            case ETNETNC_TOTALRATE:
                EtFormatNetworkRate(block->ReceiveRawDelta.Delta + block->SendRawDelta.Delta, block, message);
                break;
            }

            if (block->TextCacheLength[message->SubId])
            {
                getCellText->Text.Length = block->TextCacheLength[message->SubId];
                getCellText->Text.Buffer = block->TextCache[message->SubId];
            }

            block->TextCacheValid[message->SubId] = TRUE;
        }

        PhReleaseQueuedLockExclusive(&block->TextCacheLock);
    }
}

_Function_class_(PH_PLUGIN_TREENEW_SORT_FUNCTION)
LONG EtpNetworkTreeNewSortFunction(
    _In_ PVOID Node1,
    _In_ PVOID Node2,
    _In_ ULONG SubId,
    _In_ PH_SORT_ORDER SortOrder,
    _In_ PVOID Context
    )
{
    LONG result;
    PPH_NETWORK_NODE node1 = Node1;
    PPH_NETWORK_NODE node2 = Node2;
    PET_NETWORK_BLOCK block1;
    PET_NETWORK_BLOCK block2;

    block1 = EtGetNetworkBlock(node1->NetworkItem);
    block2 = EtGetNetworkBlock(node2->NetworkItem);

    result = 0;

    switch (SubId)
    {
    case ETNETNC_RECEIVES:
        result = uint64cmp(block1->ReceiveCount, block2->ReceiveCount);
        break;
    case ETNETNC_SENDS:
        result = uint64cmp(block1->SendCount, block2->SendCount);
        break;
    case ETNETNC_RECEIVEBYTES:
        result = uint64cmp(block1->ReceiveRaw, block2->ReceiveRaw);
        break;
    case ETNETNC_SENDBYTES:
        result = uint64cmp(block1->SendRaw, block2->SendRaw);
        break;
    case ETNETNC_TOTALBYTES:
        result = uint64cmp(block1->ReceiveRaw + block1->SendRaw, block2->ReceiveRaw + block2->SendRaw);
        break;
    case ETNETNC_RECEIVESDELTA:
        result = uint64cmp(block1->ReceiveDelta.Delta, block2->ReceiveDelta.Delta);
        break;
    case ETNETNC_SENDSDELTA:
        result = uint64cmp(block1->SendDelta.Delta, block2->SendDelta.Delta);
        break;
    case ETNETNC_RECEIVEBYTESDELTA:
        result = uint64cmp(block1->ReceiveRawDelta.Delta, block2->ReceiveRawDelta.Delta);
        break;
    case ETNETNC_SENDBYTESDELTA:
        result = uint64cmp(block1->SendRawDelta.Delta, block2->SendRawDelta.Delta);
        break;
    case ETNETNC_TOTALBYTESDELTA:
        result = uint64cmp(block1->ReceiveRawDelta.Delta + block1->SendRawDelta.Delta, block2->ReceiveRawDelta.Delta + block2->SendRawDelta.Delta);
        break;
    case ETNETNC_FIREWALLSTATUS:
        EtpUpdateFirewallStatus(block1);
        EtpUpdateFirewallStatus(block2);
        result = intcmp(block1->FirewallStatus, block2->FirewallStatus);
        break;
    case ETNETNC_RECEIVERATE:
        result = uint64cmp(block1->ReceiveRawDelta.Delta, block2->ReceiveRawDelta.Delta);
        break;
    case ETNETNC_SENDRATE:
        result = uint64cmp(block1->SendRawDelta.Delta, block2->SendRawDelta.Delta);
        break;
    case ETNETNC_TOTALRATE:
        result = uint64cmp(block1->ReceiveRawDelta.Delta + block1->SendRawDelta.Delta, block2->ReceiveRawDelta.Delta + block2->SendRawDelta.Delta);
        break;
    }

    return result;
}

ET_FIREWALL_STATUS EtQueryFirewallStatus(
    _In_ PPH_NETWORK_ITEM NetworkItem
    )
{
    static INetFwMgr* manager = NULL;
    ET_FIREWALL_STATUS result;
    PPH_PROCESS_ITEM processItem;
    PPH_STRING imageFileName;
    BSTR imageFileNameBStr;
    BSTR localAddressBStr;
    VARIANT allowed;
    VARIANT restricted;

    if (!manager)
    {
        if (!SUCCEEDED(PhGetClassObject(L"firewallapi.dll", &CLSID_NetFwMgr, &IID_INetFwMgr, &manager)))
            return FirewallUnknownStatus;

        if (!manager)
            return FirewallUnknownStatus;
    }

    processItem = PhReferenceProcessItem(NetworkItem->ProcessId);

    if (!processItem)
        return FirewallUnknownStatus;

    if (PhIsNullOrEmptyString(processItem->FileName))
    {
        PhDereferenceObject(processItem);
        return FirewallUnknownStatus;
    }

    result = FirewallUnknownStatus;
    imageFileName = PhGetFileName(processItem->FileName);

    if (imageFileNameBStr = SysAllocStringLen(imageFileName->Buffer, (ULONG)imageFileName->Length / sizeof(WCHAR)))
    {
        localAddressBStr = NULL;

        if (!PhIsNullIpAddress(&NetworkItem->LocalEndpoint.Address) && !PhIsNullOrEmptyString(NetworkItem->LocalAddressString))
            localAddressBStr = SysAllocStringLen(NetworkItem->LocalAddressString->Buffer, (UINT)(NetworkItem->LocalAddressString->Length / sizeof(WCHAR)));

        memset(&allowed, 0, sizeof(VARIANT)); // VariantInit
        memset(&restricted, 0, sizeof(VARIANT)); // VariantInit

        if (SUCCEEDED(INetFwMgr_IsPortAllowed(
            manager,
            imageFileNameBStr,
            (NetworkItem->ProtocolType & PH_NETWORK_TYPE_IPV6) ? NET_FW_IP_VERSION_V6 : NET_FW_IP_VERSION_V4,
            NetworkItem->LocalEndpoint.Port,
            localAddressBStr,
            (NetworkItem->ProtocolType & PH_PROTOCOL_TYPE_UDP) ? NET_FW_IP_PROTOCOL_UDP : NET_FW_IP_PROTOCOL_TCP,
            &allowed,
            &restricted
            )))
        {
            if (V_BOOL(&allowed))
            {
                if (V_BOOL(&restricted))
                    result = FirewallAllowedRestricted;
                else
                    result = FirewallAllowedNotRestricted;
            }
            else
            {
                if (V_BOOL(&restricted))
                    result = FirewallNotAllowedRestricted;
                else
                    result = FirewallNotAllowedNotRestricted;
            }
        }

        if (localAddressBStr)
            SysFreeString(localAddressBStr);

        SysFreeString(imageFileNameBStr);
    }

    PhDereferenceObject(imageFileName);
    PhDereferenceObject(processItem);

    return result;
}
