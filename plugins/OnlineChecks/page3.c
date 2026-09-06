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

HRESULT CALLBACK TaskDialogProgressCallbackProc(
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
            SendMessage(WindowHandle, TDM_SET_MARQUEE_PROGRESS_BAR, TRUE, 0);
            SendMessage(WindowHandle, TDM_SET_PROGRESS_BAR_MARQUEE, TRUE, 1);
            context->ProgressMarquee = TRUE;

            //if (context->TaskbarListClass)
            //{
            //    PhTaskbarListSetProgressState(context->TaskbarListClass, context->DialogHandle, PH_TBLF_INDETERMINATE);
            //}

#ifndef FORCE_NO_STATUS_TIMER
            if (!context->ProgressTimer)
            {
                PhSetTimer(WindowHandle, 9000, SETTING_NAME_STATUS_TIMER_INTERVAL, NULL);
                context->ProgressTimer = TRUE;
            }
#endif
            PhReferenceObject(context);
            PhQueueItemWorkQueue(PhGetGlobalWorkQueue(), UploadFileThreadStart, context);
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDCANCEL)
            {
                context->Cancel = TRUE;
                return S_FALSE;
            }
        }
        break;
    }

    return S_OK;
}

HRESULT CALLBACK TaskDialogReScanProgressCallbackProc(
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
            SendMessage(WindowHandle, TDM_SET_MARQUEE_PROGRESS_BAR, TRUE, 0);
            SendMessage(WindowHandle, TDM_SET_PROGRESS_BAR_MARQUEE, TRUE, 1);
            context->ProgressMarquee = TRUE;

            //if (context->TaskbarListClass)
            //{
            //    PhTaskbarListSetProgressState(context->TaskbarListClass, context->DialogHandle, PH_TBLF_INDETERMINATE);
            //}

#ifndef FORCE_NO_STATUS_TIMER
            if (!context->ProgressTimer)
            {
                PhSetTimer(WindowHandle, 9000, SETTING_NAME_STATUS_TIMER_INTERVAL, NULL);
                context->ProgressTimer = TRUE;
            }
#endif
            PhReferenceObject(context);
            PhQueueItemWorkQueue(PhGetGlobalWorkQueue(), UploadRecheckThreadStart, context);
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDCANCEL)
            {
                context->Cancel = TRUE;
                return S_FALSE;
            }
        }
        break;
    }

    return S_OK;
}

HRESULT CALLBACK TaskDialogViewReportProgressCallbackProc(
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
            SendMessage(WindowHandle, TDM_SET_MARQUEE_PROGRESS_BAR, TRUE, 0);
            SendMessage(WindowHandle, TDM_SET_PROGRESS_BAR_MARQUEE, TRUE, 1);
            //context->ProgressMarquee = TRUE;

            //if (context->TaskbarListClass)
            //{
            //    PhTaskbarListSetProgressState(context->TaskbarListClass, context->DialogHandle, PH_TBLF_INDETERMINATE);
            //}

#ifndef FORCE_NO_STATUS_TIMER
            if (!context->ProgressTimer)
            {
                PhSetTimer(WindowHandle, 9000, SETTING_NAME_STATUS_TIMER_INTERVAL, NULL);
                context->ProgressTimer = TRUE;
            }
#endif
            PhReferenceObject(context);
            PhQueueItemWorkQueue(PhGetGlobalWorkQueue(), ViewReportThreadStart, context);
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDCANCEL)
            {
                context->Cancel = TRUE;
                return S_FALSE;
            }
        }
        break;
    }

    return S_OK;
}

VOID ShowFileUploadProgressDialog(
    _In_ PUPLOAD_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;
    PPH_STRING uploadingFormat;
    PPH_STRING uploadingText;

    uploadingFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_UPLOADING_FORMAT, NULL));
    uploadingText = PhaFormatString(
        PhGetStringOrEmpty(uploadingFormat),
        PhGetStringOrEmpty(Context->BaseFileName)
        );

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_EXPAND_FOOTER_AREA | TDF_ENABLE_HYPERLINKS | TDF_SHOW_PROGRESS_BAR | TDF_CALLBACK_TIMER;
    config.dwCommonButtons = TDCBF_CANCEL_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, PhGetWindowDpi(Context->DialogHandle));
    config.pszWindowTitle = uploadingText->Buffer;
    config.pszMainInstruction = uploadingText->Buffer;
    config.pszContent = L"Uploaded: ~ of ~ (0%)\r\nSpeed: ~ KB/s";

    config.cxWidth = 200;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pfCallback = TaskDialogProgressCallbackProc;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

VOID ShowVirusTotalReScanProgressDialog(
    _In_ PUPLOAD_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;
    PPH_STRING rescanningFormat;
    PPH_STRING rescanningText;

    rescanningFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_RESCANNING_FORMAT, NULL));
    rescanningText = PhaFormatString(
        PhGetStringOrEmpty(rescanningFormat),
        PhGetStringOrEmpty(Context->BaseFileName)
        );

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_EXPAND_FOOTER_AREA | TDF_ENABLE_HYPERLINKS | TDF_SHOW_PROGRESS_BAR;
    config.dwCommonButtons = TDCBF_CANCEL_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, PhGetWindowDpi(Context->DialogHandle));
    config.pszWindowTitle = rescanningText->Buffer;
    config.pszMainInstruction = rescanningText->Buffer;

    config.cxWidth = 200;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pfCallback = TaskDialogReScanProgressCallbackProc;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

VOID ShowVirusTotalViewReportProgressDialog(
    _In_ PUPLOAD_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;
    PPH_STRING locatingAnalysisFormat;
    PPH_STRING locatingAnalysisText;

    locatingAnalysisFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_LOCATING_ANALYSIS_FORMAT, NULL));
    locatingAnalysisText = PhaFormatString(
        PhGetStringOrEmpty(locatingAnalysisFormat),
        PhGetStringOrEmpty(Context->BaseFileName)
        );

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_EXPAND_FOOTER_AREA | TDF_ENABLE_HYPERLINKS | TDF_SHOW_PROGRESS_BAR;
    config.dwCommonButtons = TDCBF_CANCEL_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, PhGetWindowDpi(Context->DialogHandle));
    config.pszWindowTitle = locatingAnalysisText->Buffer;
    config.pszMainInstruction = locatingAnalysisText->Buffer;

    config.cxWidth = 200;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pfCallback = TaskDialogViewReportProgressCallbackProc;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
