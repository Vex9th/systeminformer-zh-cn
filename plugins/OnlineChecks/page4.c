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

HRESULT CALLBACK TaskDialogErrorProc(
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
            //    PhTaskbarListSetProgressValue(context->TaskbarListClass, context->DialogHandle, 1, 1);
            //    PhTaskbarListSetProgressState(context->TaskbarListClass, context->DialogHandle, PH_TBLF_ERROR);
            //}
        }
        break;
    }

    return S_OK;
}

VOID VirusTotalShowErrorDialog(
    _In_ PUPLOAD_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;
    PPH_STRING uploadingFormat;
    PPH_STRING uploadingText;
    PPH_STRING uploadErrorFormat;
    PPH_STRING uploadErrorText;

    uploadingFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_UPLOADING_FORMAT, NULL));
    uploadingText = PhaFormatString(
        PhGetStringOrEmpty(uploadingFormat),
        PhGetStringOrEmpty(Context->BaseFileName)
        );
    uploadErrorFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_OC_UPLOAD_ERROR_FORMAT, NULL));
    uploadErrorText = PhaFormatString(
        PhGetStringOrEmpty(uploadErrorFormat),
        PhGetStringOrEmpty(Context->BaseFileName)
        );

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_ENABLE_HYPERLINKS;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, PhGetWindowDpi(Context->DialogHandle));
    config.pszWindowTitle = uploadingText->Buffer;
    config.pszMainInstruction = uploadErrorText->Buffer;
    config.pszContent = PhGetStringOrEmpty(Context->ErrorString);

    config.cxWidth = 200;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pfCallback = TaskDialogErrorProc;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
