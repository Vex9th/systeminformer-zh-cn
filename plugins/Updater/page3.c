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

#include "updater.h"

/**
 * \brief Callback procedure for the Update Available task dialog page.
 * \param WindowHandle Handle to the dialog window.
 * \param WindowMessage The window message.
 * \param wParam Additional message-specific information.
 * \param lParam Additional message-specific information.
 * \param dwRefData The updater context.
 * \return HRESULT Successful or errant status.
 */
HRESULT CALLBACK ShowAvailableCallbackProc(
    _In_ HWND WindowHandle,
    _In_ UINT WindowMessage,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam,
    _In_ LONG_PTR dwRefData
    )
{
    PPH_UPDATER_CONTEXT context = (PPH_UPDATER_CONTEXT)dwRefData;

    switch (WindowMessage)
    {
    case TDN_NAVIGATED:
        PhSetEvent(&InitializedEvent);
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDOK)
            {
                ShowProgressDialog(context);
                return S_FALSE;
            }
        }
        break;
    case TDN_HYPERLINK_CLICKED:
        {
            TaskDialogLinkClicked(context);
            return S_FALSE;
        }
        break;
    }

    return S_OK;
}

/**
 * \brief Shows the Update Available dialog page.
 * \param Context The updater context.
 */
VOID ShowAvailableDialog(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING downloadButtonText;
    PPH_STRING availableDetailsFormat;
    PPH_STRING windowTitle;
    PPH_STRING releaseDownloadText;
    PPH_STRING canaryDownloadText;
    PPH_STRING updateDownloadText;
    PPH_STRING newerBuildText;
    TASKDIALOG_BUTTON taskDialogButtonArray[1];
    TASKDIALOGCONFIG config;

    downloadButtonText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_BUTTON_DOWNLOAD, NULL));
    availableDetailsFormat = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_AVAILABLE_DETAILS_FORMAT, NULL));
    windowTitle = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DIALOG_TITLE, NULL));
    releaseDownloadText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DOWNLOAD_RELEASE_PROMPT, NULL));
    canaryDownloadText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DOWNLOAD_CANARY_PROMPT, NULL));
    updateDownloadText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DOWNLOAD_UPDATE_PROMPT, NULL));
    newerBuildText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_NEWER_BUILD_AVAILABLE, NULL));

    taskDialogButtonArray[0].nButtonID = IDOK;
    taskDialogButtonArray[0].pszButtonText = PhGetStringOrEmpty(downloadButtonText);

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_ENABLE_HYPERLINKS;
    config.dwCommonButtons = TDCBF_CANCEL_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);
    config.cxWidth = 200;
    config.pButtons = taskDialogButtonArray;
    config.cButtons = RTL_NUMBER_OF(taskDialogButtonArray);
    config.lpCallbackData = (LONG_PTR)Context;
    config.pfCallback = ShowAvailableCallbackProc;

    config.pszWindowTitle = PhGetStringOrEmpty(windowTitle);
    if (Context->SwitchingChannel)
    {
        switch (Context->Channel)
        {
        case PhReleaseChannel:
            config.pszMainInstruction = PhGetStringOrEmpty(releaseDownloadText);
            break;
        //case PhPreviewChannel:
        //    config.pszMainInstruction = L"Would you like to download the Preview build?";
        //    break;
        case PhCanaryChannel:
            config.pszMainInstruction = PhGetStringOrEmpty(canaryDownloadText);
            break;
        //case PhDeveloperChannel:
        //    config.pszMainInstruction = L"Would you like to download the Developer build?";
        //    break;
        default:
            config.pszMainInstruction = PhGetStringOrEmpty(updateDownloadText);
            break;
        }
    }
    else
    {
        config.pszMainInstruction = PhGetStringOrEmpty(newerBuildText);
    }

    config.pszContent = PhaFormatString(
        PhGetStringOrEmpty(availableDetailsFormat),
        PhGetStringOrEmpty(Context->Version),
        PhGetStringOrEmpty(Context->SetupFileLength)
        )->Buffer;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
