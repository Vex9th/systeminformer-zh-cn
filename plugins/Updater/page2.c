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
 * \brief Callback procedure for the Checking for Updates task dialog page.
 * \param WindowHandle Handle to the dialog window.
 * \param WindowMessage The window message.
 * \param wParam Additional message-specific information.
 * \param lParam Additional message-specific information.
 * \param dwRefData The updater context.
 * \return HRESULT Successful or errant status.
 */
HRESULT CALLBACK CheckingForUpdatesCallbackProc(
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
        {
            PhSetEvent(&InitializedEvent);

            SendMessage(WindowHandle, TDM_SET_MARQUEE_PROGRESS_BAR, TRUE, 0);
            SendMessage(WindowHandle, TDM_SET_PROGRESS_BAR_MARQUEE, TRUE, 1);
            context->ProgressMarquee = TRUE;

#ifndef FORCE_NO_STATUS_TIMER
            if (!context->ProgressTimer)
            {
                PhSetTimer(WindowHandle, 9000, SETTING_NAME_STATUS_TIMER_INTERVAL, NULL);
                context->ProgressTimer = TRUE;
            }
#endif
            PhReferenceObject(context);
            PhCreateThread2(UpdateCheckThread, context);
        }
        break;
    }

    return S_OK;
}

/**
 * \brief Shows the Checking for Updates dialog page.
 * \param Context The updater context.
 */
VOID ShowCheckingForUpdatesDialog(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING windowTitle;
    PPH_STRING releaseChannelText;
    PPH_STRING canaryChannelText;
    PPH_STRING channelText;
    PPH_STRING checkingReleaseText;
    TASKDIALOGCONFIG config;

    windowTitle = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DIALOG_TITLE, NULL));
    releaseChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHECKING_RELEASE_CHANNEL, NULL));
    canaryChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHECKING_CANARY_CHANNEL, NULL));
    channelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHECKING_CHANNEL, NULL));
    checkingReleaseText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHECKING_UPDATED_RELEASE, NULL));

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_SHOW_MARQUEE_PROGRESS_BAR;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);
    config.cxWidth = 200;
    config.pfCallback = CheckingForUpdatesCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;

    config.pszWindowTitle = PhGetStringOrEmpty(windowTitle);

    if (Context->SwitchingChannel)
    {
        switch (Context->Channel)
        {
        case PhReleaseChannel:
            config.pszMainInstruction = PhGetStringOrEmpty(releaseChannelText);
            break;
        //case PhPreviewChannel:
        //    config.pszMainInstruction = L"Checking the preview channel...";
        //    break;
        case PhCanaryChannel:
            config.pszMainInstruction = PhGetStringOrEmpty(canaryChannelText);
            break;
        //case PhDeveloperChannel:
        //    config.pszMainInstruction = L"Checking the developer channel...";
        //    break;
        default:
            config.pszMainInstruction = PhGetStringOrEmpty(channelText);
            break;
        }
    }
    else
    {
        config.pszMainInstruction = PhGetStringOrEmpty(checkingReleaseText);
    }

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
