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
 * \brief Callback procedure for the final state task dialog pages (Install, Latest, Error).
 * \param WindowHandle Handle to the dialog window.
 * \param WindowMessage The window message.
 * \param wParam Additional message-specific information.
 * \param lParam Additional message-specific information.
 * \param dwRefData The updater context.
 * \return HRESULT Successful or errant status.
 */
HRESULT CALLBACK FinalTaskDialogCallbackProc(
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
#ifndef FORCE_NO_STATUS_TIMER
            if (context->ProgressTimer)
            {
                PhKillTimer(WindowHandle, 9000);
                context->ProgressTimer = FALSE;
            }
#endif
            context->ElevationRequired = !!UpdateCheckDirectoryElevationRequired();

#ifdef FORCE_ELEVATION_CHECK
            context->ElevationRequired = TRUE;
#endif

            if (context->ElevationRequired)
            {
                SendMessage(WindowHandle, TDM_SET_BUTTON_ELEVATION_REQUIRED_STATE, IDYES, TRUE);
            }
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            INT buttonId = (INT)wParam;

            if (buttonId == IDRETRY)
            {
                if (context->CryptoBackend == UpdaterCryptoBackendSymCrypt)
                    context->CryptoBackend = UpdaterCryptoBackendBCrypt;
                ShowCheckForUpdatesDialog(context);
                return S_FALSE;
            }
            else if (buttonId == IDYES)
            {
#if defined(PH_BUILD_MSIX)
                // MSIX: the platform already downloaded and installed the update.
                // Nothing to ShellExecute; let the dialog close.
#else
                if (!NT_SUCCESS(UpdateShellExecute(context, WindowHandle)))
                {
                    return S_FALSE;
                }
#endif
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
 * \brief Shows the Ready to Install dialog page.
 * \param Context The updater context.
 */
VOID ShowUpdateInstallDialog(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING installButtonText;
    PPH_STRING windowTitle;
    PPH_STRING releaseReadyText;
    PPH_STRING canaryReadyText;
    PPH_STRING channelReadyText;
    PPH_STRING updateInstalledText;
    PPH_STRING installReadyText;
    PPH_STRING channelVerifiedText;
    PPH_STRING updateInstalledRestartText;
    PPH_STRING updateVerifiedText;
    TASKDIALOG_BUTTON taskDialogButtonArray[1];
    TASKDIALOGCONFIG config;

    installButtonText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_BUTTON_INSTALL, NULL));
    windowTitle = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DIALOG_TITLE, NULL));
    releaseReadyText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_SWITCH_RELEASE_READY, NULL));
    canaryReadyText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_SWITCH_CANARY_READY, NULL));
    channelReadyText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_SWITCH_CHANNEL_READY, NULL));
    updateInstalledText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_UPDATE_INSTALLED, NULL));
    installReadyText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_INSTALL_UPDATE_READY, NULL));
    channelVerifiedText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_CHANNEL_VERIFIED_INSTALL, NULL));
    updateInstalledRestartText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_UPDATE_INSTALLED_RESTART, NULL));
    updateVerifiedText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_UPDATE_VERIFIED_INSTALL, NULL));

    taskDialogButtonArray[0].nButtonID = IDYES;
    taskDialogButtonArray[0].pszButtonText = PhGetStringOrEmpty(installButtonText);

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);
    config.cxWidth = 200;
    config.pfCallback = FinalTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pButtons = taskDialogButtonArray;
    config.cButtons = RTL_NUMBER_OF(taskDialogButtonArray);

    config.pszWindowTitle = PhGetStringOrEmpty(windowTitle);
    if (Context->SwitchingChannel)
    {
        switch (Context->Channel)
        {
        case PhReleaseChannel:
            config.pszMainInstruction = PhGetStringOrEmpty(releaseReadyText);
            break;
        //case PhPreviewChannel:
        //    config.pszMainInstruction = L"Ready to switch to the preview channel?";
        //    break;
        case PhCanaryChannel:
            config.pszMainInstruction = PhGetStringOrEmpty(canaryReadyText);
            break;
        //case PhDeveloperChannel:
        //    config.pszMainInstruction = L"Ready to switch to the developer channel?";
        //    break;
        default:
            config.pszMainInstruction = PhGetStringOrEmpty(channelReadyText);
            break;
        }

        config.pszContent = PhGetStringOrEmpty(channelVerifiedText);
    }
    else
    {
#if defined(PH_BUILD_MSIX)
        config.pszMainInstruction = PhGetStringOrEmpty(updateInstalledText);
        config.pszContent = PhGetStringOrEmpty(updateInstalledRestartText);
#else
        config.pszMainInstruction = PhGetStringOrEmpty(installReadyText);
        config.pszContent = PhGetStringOrEmpty(updateVerifiedText);
#endif
    }

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * \brief Generates the text describing the current latest version.
 * \param Context The updater context.
 * \return A string containing the formatted version text.
 */
PPH_STRING UpdaterGetLatestVersionText(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING version;
    PPH_STRING commit;
    ULONG majorVersion;
    ULONG minorVersion;
    ULONG buildVersion;
    ULONG revisionVersion;

    PhGetBuildVersionNumbers(&majorVersion, &minorVersion, &buildVersion, &revisionVersion);
    commit = PhGetBuildCommit();

    if (commit && commit->Length > 4)
    {
        version = PhFormatString(
            L"%lu.%lu.%lu.%lu (%s)",
            majorVersion,
            minorVersion,
            buildVersion,
            revisionVersion,
            PhGetString(commit)
            );
        PhMoveReference(&version, PhFormatString(
            L"%s\r\n\r\n<A HREF=\"changelog.txt\">View changelog</A>",
            PhGetStringOrEmpty(version)
            ));
    }
    else
    {
        version = PhFormatString(
            L"System Informer %lu.%lu.%lu.%lu",
            majorVersion,
            minorVersion,
            buildVersion,
            revisionVersion
            );
        PhMoveReference(&version, PhFormatString(
            L"%s\r\n\r\n<A HREF=\"changelog.txt\">View changelog</A>",
            PhGetStringOrEmpty(version)
            ));
    }

    if (commit)
    {
        PhDereferenceObject(commit);
    }

    return version;
}

/**
 * \brief Shows the Latest Version dialog page.
 * \param Context The updater context.
 */
VOID ShowLatestVersionDialog(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING windowTitle;
    PPH_STRING latestVersionText;
    TASKDIALOGCONFIG config;

    windowTitle = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DIALOG_TITLE, NULL));
    latestVersionText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_LATEST_VERSION, NULL));

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_ENABLE_HYPERLINKS;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);
    config.cxWidth = 200;
    config.pfCallback = FinalTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;

    config.pszWindowTitle = PhGetStringOrEmpty(windowTitle);
    config.pszMainInstruction = PhGetStringOrEmpty(latestVersionText);
    config.pszContent = PH_AUTO_T(PH_STRING, UpdaterGetLatestVersionText(Context))->Buffer;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * \brief Shows the Newer Version dialog page (e.g., when running a pre-release).
 * \param Context The updater context.
 */
VOID ShowNewerVersionDialog(
    _In_ PPH_UPDATER_CONTEXT Context
    )
{
    PPH_STRING windowTitle;
    PPH_STRING preReleaseText;
    TASKDIALOGCONFIG config;

    windowTitle = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DIALOG_TITLE, NULL));
    preReleaseText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_PRE_RELEASE_BUILD, NULL));

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_ENABLE_HYPERLINKS;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);
    config.cxWidth = 200;
    config.pfCallback = FinalTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;

    config.pszWindowTitle = PhGetStringOrEmpty(windowTitle);
    config.pszMainInstruction = PhGetStringOrEmpty(preReleaseText);
    config.pszContent = PH_AUTO_T(PH_STRING, UpdaterGetLatestVersionText(Context))->Buffer;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * \brief Shows the Update Failed dialog page.
 * \param Context The updater context.
 * \param HashFailed TRUE if the hash verification failed.
 * \param SignatureFailed TRUE if the signature verification failed.
 */
VOID ShowUpdateFailedDialog(
    _In_ PPH_UPDATER_CONTEXT Context,
    _In_ BOOLEAN HashFailed,
    _In_ BOOLEAN SignatureFailed
    )
{
    PPH_STRING windowTitle;
    PPH_STRING errorChannelText;
    PPH_STRING errorUpdateText;
    PPH_STRING signatureChannelText;
    PPH_STRING signatureUpdateText;
    PPH_STRING hashChannelText;
    PPH_STRING hashUpdateText;
    PPH_STRING retryChannelText;
    PPH_STRING retryUpdateText;
    TASKDIALOGCONFIG config;

    windowTitle = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_DIALOG_TITLE, NULL));
    errorChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_ERROR_DOWNLOADING_CHANNEL, NULL));
    errorUpdateText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_ERROR_DOWNLOADING_UPDATE, NULL));
    signatureChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_SIGNATURE_FAILED_CHANNEL, NULL));
    signatureUpdateText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_SIGNATURE_FAILED_UPDATE, NULL));
    hashChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_HASH_FAILED_CHANNEL, NULL));
    hashUpdateText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_HASH_FAILED_UPDATE, NULL));
    retryChannelText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_RETRY_DOWNLOAD_CHANNEL, NULL));
    retryUpdateText = PH_AUTO(PhLoadUiString(PluginInstance->DllBase, IDS_UP_RETRY_DOWNLOAD_UPDATE, NULL));

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    //config.pszMainIcon = MAKEINTRESOURCE(65529);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON | TDCBF_RETRY_BUTTON;
    config.hMainIcon = PhGetApplicationIcon(FALSE, Context->WindowDpi);

    config.pszWindowTitle = PhGetStringOrEmpty(windowTitle);
    if (Context->SwitchingChannel)
        config.pszMainInstruction = PhGetStringOrEmpty(errorChannelText);
    else
        config.pszMainInstruction = PhGetStringOrEmpty(errorUpdateText);

    if (SignatureFailed)
    {
        if (Context->SwitchingChannel)
            config.pszContent = PhGetStringOrEmpty(signatureChannelText);
        else
            config.pszContent = PhGetStringOrEmpty(signatureUpdateText);
    }
    else if (HashFailed)
    {
        if (Context->SwitchingChannel)
            config.pszContent = PhGetStringOrEmpty(hashChannelText);
        else
            config.pszContent = PhGetStringOrEmpty(hashUpdateText);
    }
    else
    {
        if (Context->UpdateStatus)
        {
            PPH_STRING errorMessage;

            if (errorMessage = PhHttpGetErrorMessage(Context->UpdateStatus))
            {
                config.pszContent = PhaFormatString(L"[%lu] %s", Context->UpdateStatus, errorMessage->Buffer)->Buffer;
                PhDereferenceObject(errorMessage);
            }
            else if (errorMessage = PhGetStatusMessage(Context->UpdateStatus, 0))
            {
                config.pszContent = PhaFormatString(L"[%lu] %s", Context->UpdateStatus, errorMessage->Buffer)->Buffer;
                PhDereferenceObject(errorMessage);
            }
            else
            {
                if (Context->SwitchingChannel)
                    config.pszContent = PhGetStringOrEmpty(retryChannelText);
                else
                    config.pszContent = PhGetStringOrEmpty(retryUpdateText);
            }
        }
        else
        {
            if (Context->SwitchingChannel)
                config.pszContent = PhGetStringOrEmpty(retryChannelText);
            else
                config.pszContent = PhGetStringOrEmpty(retryUpdateText);
        }
    }

    config.cxWidth = 200;
    config.pfCallback = FinalTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
