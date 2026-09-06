/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     dmex    2016-2026
 *
 */

#include "onlnchk.h"

HRESULT CALLBACK TaskDialogResultFoundProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam,
    _In_ LONG_PTR dwRefData
    )
{
    PUPLOAD_CONTEXT context = (PUPLOAD_CONTEXT)dwRefData;

    switch (WindowMessage)
    {
    case TDN_NAVIGATED:
        {
            //if (context->TaskbarListClass)
            //{
            //    PhTaskbarListSetProgressState(context->TaskbarListClass, context->DialogHandle, PH_TBLF_NOPROGRESS);
            //}
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            INT buttonID = (INT)wParam;

            if (buttonID == IDOK)
            {
                ShowFileUploadProgressDialog(context);
                return S_FALSE;
            }
            else if (buttonID == IDRETRY)
            {
//#ifdef PH_BUILD_API
                ShowVirusTotalReScanProgressDialog(context);
                return S_FALSE;
//#else
//                if (!PhIsNullOrEmptyString(context->ReAnalyseUrl))
//                {
//                    PhShellExecute(WindowHandle, PhGetString(context->ReAnalyseUrl), NULL);
//                }
//#endif
            }
            else if (buttonID == IDYES)
            {
//#ifdef PH_BUILD_API
                ShowVirusTotalViewReportProgressDialog(context);
                return S_FALSE;
//#else
//                if (!PhIsNullOrEmptyString(context->LaunchCommand))
//                {
//                    PhShellExecute(WindowHandle, PhGetString(context->LaunchCommand), NULL);
//                }
//#endif
            }
        }
        break;
    case TDN_VERIFICATION_CLICKED:
        {
            BOOL verification = (BOOL)wParam;
        }
        break;
    }

    return S_OK;
}

VOID ShowFileFoundDialog(
    _In_ PUPLOAD_CONTEXT Context
    )
{
    PPH_STRING viewLastAnalysisText;
    PPH_STRING uploadFileText;
    PPH_STRING lastAnalyzedFormat;
    PPH_STRING detectionsLabel;
    PPH_STRING firstAnalyzedLabel;
    PPH_STRING lastAnalyzedLabel;
    PPH_STRING uploadSizeLabel;
    PPH_STRING analysisActionPrompt;
    TASKDIALOG_BUTTON TaskDialogButtonArray[] =
    {
        { IDYES, NULL },
        //{ IDRETRY, L"Reanalyze file\nRescan the existing sample on VirusTotal" },
        { IDOK, NULL },
    };
    TASKDIALOGCONFIG config;

    viewLastAnalysisText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_BUTTON_VIEW_LAST_ANALYSIS, NULL));
    uploadFileText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_BUTTON_UPLOAD_FILE, NULL));
    lastAnalyzedFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_LAST_ANALYZED_FORMAT, NULL));
    detectionsLabel = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_DETECTIONS_LABEL, NULL));
    firstAnalyzedLabel = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_FIRST_ANALYZED_LABEL, NULL));
    lastAnalyzedLabel = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_LAST_ANALYZED_LABEL, NULL));
    uploadSizeLabel = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_UPLOAD_SIZE_LABEL, NULL));
    analysisActionPrompt = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_ANALYSIS_ACTION_PROMPT, NULL));
    TaskDialogButtonArray[0].pszButtonText = PhGetStringOrEmpty(viewLastAnalysisText);
    TaskDialogButtonArray[1].pszButtonText = PhGetStringOrEmpty(uploadFileText);

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_ENABLE_HYPERLINKS | TDF_USE_COMMAND_LINKS;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, PhGetWindowDpi(Context->DialogHandle));
    config.pszMainInstruction = PhaFormatString(
        PhGetStringOrEmpty(lastAnalyzedFormat),
        PhGetStringOrEmpty(Context->BaseFileName),
        PhGetStringOrEmpty(Context->LastAnalysisDate)
        )->Buffer;

    if (Context->Service == MENUITEM_VIRUSTOTAL_UPLOAD || Context->Service == MENUITEM_VIRUSTOTAL_UPLOAD_SERVICE)
    {
        // was last analyzed by VirusTotal on 2016-12-28 05:26:50 UTC (1 hour ago) it was first analyzed by VirusTotal on 2016-12-12 17:08:19 UTC.
        config.pszContent = PhaFormatString(
            L"%s %s\r\n%s %s\r\n%s %s\r\n%s %s\r\n\r\n%s",
            PhGetStringOrEmpty(detectionsLabel),
            PhGetStringOrEmpty(Context->Detected),
            PhGetStringOrEmpty(firstAnalyzedLabel),
            PhGetStringOrEmpty(Context->FirstAnalysisDate),
            PhGetStringOrEmpty(lastAnalyzedLabel),
            PhGetStringOrEmpty(Context->LastAnalysisDate),
            PhGetStringOrEmpty(uploadSizeLabel),
            PhGetStringOrEmpty(Context->FileSize),
            PhGetStringOrEmpty(analysisActionPrompt)
            )->Buffer;
    }
    else
    {
        config.pszContent = PhaFormatString(
            L"%s %s\r\n%s %s\r\n\r\n%s",
            PhGetStringOrEmpty(detectionsLabel),
            PhGetStringOrEmpty(Context->Detected),
            //L"Last analyzed:",
            //PhGetStringOrEmpty(Context->LastAnalysisDate),
            PhGetStringOrEmpty(uploadSizeLabel),
            PhGetStringOrEmpty(Context->FileSize),
            PhGetStringOrEmpty(analysisActionPrompt)
            )->Buffer;
    }

    //config.pszVerificationText = L"Remember this selection...";
    config.pButtons = TaskDialogButtonArray;
    config.cButtons = ARRAYSIZE(TaskDialogButtonArray);
    config.lpCallbackData = (LONG_PTR)Context;
    config.pfCallback = TaskDialogResultFoundProc;
    config.cxWidth = 250;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
