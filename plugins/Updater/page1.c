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
 * Callback procedure for the Check for Updates task dialog page.
 *
 * \param WindowHandle Handle to the dialog window.
 * \param WindowMessage The window message.
 * \param wParam Additional message-specific information.
 * \param lParam Additional message-specific information.
 * \param dwRefData The updater context.
 * \return HRESULT Successful or errant status.
 */
HRESULT CALLBACK CheckForUpdatesCallbackProc(
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
                ShowCheckingForUpdatesDialog(context);
                return S_FALSE;
            }
        }
        break;
    case TDN_RADIO_BUTTON_CLICKED:
        {
            PH_RELEASE_CHANNEL channel;

            switch ((INT)wParam)
            {
            default:
            case IDOK:
                channel = PhReleaseChannel;
                break;
            case IDRETRY:
                channel = PhCanaryChannel;
                break;
            }

            if (PhGetBuildReleaseChannel() != channel)
            {
                context->Channel = channel;
                context->SwitchingChannel = TRUE;
                PhSetIntegerSetting(SETTING_RELEASE_CHANNEL, channel);
            }
        }
        break;
    }

    return S_OK;
}

/**
 * Shows the initial Check for Updates dialog page.
 *
 * \param Context The updater context.
 */
VOID ShowCheckForUpdatesDialog(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING checkButtonText;
    PPH_STRING stableChannelText;
    PPH_STRING canaryChannelText;
    TASKDIALOG_BUTTON updateTaskDialogButtonArray[1];
    //static TASKDIALOG_BUTTON SwitchTaskDialogButtonArray[] =
    //{
    //    { IDOK, L"Yes" }
    //};
    TASKDIALOG_BUTTON checkForUpdatesRadioButtons[2];
    TASKDIALOGCONFIG config;

    checkButtonText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_BUTTON_CHECK, NULL));
    stableChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHANNEL_STABLE_RECOMMENDED, NULL));
    canaryChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHANNEL_CANARY_PREVIEW, NULL));

    updateTaskDialogButtonArray[0].nButtonID = IDOK;
    updateTaskDialogButtonArray[0].pszButtonText = PhGetStringOrEmpty(checkButtonText);
    checkForUpdatesRadioButtons[0].nButtonID = IDOK;
    checkForUpdatesRadioButtons[0].pszButtonText = PhGetStringOrEmpty(stableChannelText);
    checkForUpdatesRadioButtons[1].nButtonID = IDRETRY;
    checkForUpdatesRadioButtons[1].pszButtonText = PhGetStringOrEmpty(canaryChannelText);

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_ENABLE_HYPERLINKS | TDF_EXPAND_FOOTER_AREA;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);
    config.pRadioButtons = checkForUpdatesRadioButtons;
    config.cRadioButtons = RTL_NUMBER_OF(checkForUpdatesRadioButtons);
    config.pfCallback = CheckForUpdatesCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.cxWidth = 200;

    config.pszWindowTitle = L"System Informer - Updater";

    switch (Context->Channel)
    {
    default:
    case PhReleaseChannel:
        config.nDefaultRadioButton = IDOK;
        break;
    case PhCanaryChannel:
        config.nDefaultRadioButton = IDRETRY;
        break;
    }

    //if (Context->SwitchingChannel)
    //{
    //    config.pButtons = SwitchTaskDialogButtonArray;
    //    config.cButtons = RTL_NUMBER_OF(SwitchTaskDialogButtonArray);
    //
    //    switch (Context->Channel)
    //    {
    //    case PhReleaseChannel:
    //        config.pszMainInstruction = L"Switch to the System Informer release channel?";
    //        break;
    //    //case PhPreviewChannel:
    //    //    config.pszMainInstruction = L"Switch to the System Informer preview channel?";
    //    //    break;
    //    case PhCanaryChannel:
    //        config.pszMainInstruction = L"Switch to the System Informer canary channel?";
    //        break;
    //    //case PhDeveloperChannel:
    //    //    config.pszMainInstruction = L"Switch to the System Informer developer channel?";
    //    //    break;
    //    default:
    //        config.pszMainInstruction = L"Switch the System Informer update channel?";
    //        break;
    //    }
    //
    //    //if (Context->Channel < PhGetBuildhReleaseChannel())
    //    //{
    //    //    config.pszContent = L"Downgrading the channel might cause instability.\r\n\r\nClick Yes to continue.\r\n";
    //    //}
    //    //else
    //    {
    //        config.pszContent = L"Click Yes to continue.";
    //    }
    //}
    //else
    {
        config.pButtons = updateTaskDialogButtonArray;
        config.cButtons = RTL_NUMBER_OF(updateTaskDialogButtonArray);
        config.pszMainInstruction = L"Check for an updated System Informer release?";
        config.pszContent = L"Click Check to continue.";
    }

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
