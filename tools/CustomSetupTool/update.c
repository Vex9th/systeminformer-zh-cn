/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     dmex
 *
 */

#include "setup.h"

/**
 * Updates an existing System Informer installation.
 *
 * \param Context The setup context.
 * \return Successful or errant status.
 */
_Function_class_(USER_THREAD_START_ROUTINE)
NTSTATUS CALLBACK SetupUpdateBuild(
    _In_ PVOID Context
    )
{
    PPH_SETUP_CONTEXT context = (PPH_SETUP_CONTEXT)Context;
    NTSTATUS status;

    context->SetupProgressActive = TRUE;

#if !defined(PH_BUILD_API)
    SetupSetProgressTextResource(context, IDS_SETUP_DOWNLOADING_UPDATE);

    if (!NT_SUCCESS(status = SetupDownloadBuildZip(context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }
#endif

    //
    // Create the folder.
    //

    SetupSetProgressMarquee(context, TRUE);
    SetupSetProgressTextResource(context, IDS_SETUP_PREPARING_UPDATE_DIRECTORY);

    if (!NT_SUCCESS(status = PhCreateDirectoryWin32(&context->SetupInstallPath->sr)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    //
    // Stop the application.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_STOPPING_APPLICATION);

    if (!NT_SUCCESS(status = SetupShutdownApplication(context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    //
    // Stop the kernel driver.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_STOPPING_DRIVER);

    if (!NT_SUCCESS(status = SetupUninstallDriver(context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    //
    // Create the uninstaller.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_UPDATING_UNINSTALLER);

    if (!NT_SUCCESS(status = SetupCreateUninstallFile(context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    //
    // Extract the updated files.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_EXTRACTING_UPDATED_FILES);

    if (!NT_SUCCESS(status = SetupExtractBuild(context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    //
    // Upgrade the settings file.
    //
    SetupSetProgressTextResource(context, IDS_SETUP_UPDATING_SETTINGS);
    SetupUpgradeSettingsFile();

    //
    // Convert the settings file.
    //
    SetupSetProgressTextResource(context, IDS_SETUP_CONVERTING_SETTINGS);
    SetupConvertSettingsFile();

    //
    // Create the ARP uninstall config.
    //
    SetupSetProgressTextResource(context, IDS_SETUP_UPDATING_UNINSTALL_REGISTRATION);
    SetupCreateUninstallKey(Context);

    //
    // Create Windows Error Reporting config.
    //
    SetupSetProgressTextResource(context, IDS_SETUP_UPDATING_LOCALDUMPS);
    SetupCreateLocalDumpsKey();

    //
    // Create the application path config.
    //
    SetupSetProgressTextResource(context, IDS_SETUP_UPDATING_WINDOWS_INTEGRATION);
    SetupCreateWindowsOptions(Context);

    SetupSetProgressTextResource(context, IDS_SETUP_UPDATE_COMPLETE);
    SetupSetProgressValue(context, 100);
    context->SetupProgressActive = FALSE;
    SetupDeleteBuildZip(context);
    PostMessage(context->DialogHandle, SETUP_SHOWUPDATEFINAL, 0, 0);
    return STATUS_SUCCESS;

CleanupExit:

    SetupSetProgressTextResource(context, IDS_SETUP_UPDATE_FAILED);
    context->SetupProgressActive = FALSE;
    SetupDeleteBuildZip(context);
    PostMessage(context->DialogHandle, SETUP_SHOWUPDATEERROR, 0, 0);
    return STATUS_UNSUCCESSFUL;
}

/**
 * Callback for the update progress task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupUpdatingTaskDialogCallbackProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam,
    _In_ LONG_PTR dwRefData
    )
{
    PPH_SETUP_CONTEXT context = (PPH_SETUP_CONTEXT)dwRefData;

    switch (uMsg)
    {
    case TDN_NAVIGATED:
        {
            SetupApplyDarkModeToPage(hwndDlg);
            SetupSetProgressMarquee(context, TRUE);

            PhCreateThread2(SetupUpdateBuild, context);
        }
        break;
    }

    return S_OK;
}

/**
 * Callback for the update completed task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupCompletedTaskDialogCallbackProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam,
    _In_ LONG_PTR dwRefData
)
{
    PPH_SETUP_CONTEXT context = (PPH_SETUP_CONTEXT)dwRefData;

    switch (uMsg)
    {
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDCLOSE)
            {
                SetupExecuteApplication(context);
            }
        }
        break;
    }

    return S_OK;
}

/**
 * Callback for the update error task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupErrorTaskDialogCallbackProc(
    _In_ HWND hwndDlg,
    _In_ UINT uMsg,
    _In_ WPARAM wParam,
    _In_ LPARAM lParam,
    _In_ LONG_PTR dwRefData
    )
{
    PPH_SETUP_CONTEXT context = (PPH_SETUP_CONTEXT)dwRefData;

    switch (uMsg)
    {
    case TDN_NAVIGATED:
        SetupApplyDarkModeToPage(hwndDlg);
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDYES)
            {
                ShowUpdatePageDialog(context);
                return S_FALSE;
            }
        }
        break;
    }

    return S_OK;
}

/**
 * Shows the update progress page.
 *
 * \param Context The setup context.
 */
VOID ShowUpdatePageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_SHOW_MARQUEE_PROGRESS_BAR;
    config.dwCommonButtons = TDCBF_CANCEL_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pfCallback = SetupUpdatingTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;

    config.cxWidth = 200;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = PhaFormatString(
        SetupGetUiString(IDS_SETUP_UPDATING_VERSION_FORMAT),
        PHAPP_VERSION_MAJOR,
        PHAPP_VERSION_MINOR,
        PHAPP_VERSION_BUILD,
        PHAPP_VERSION_REVISION
        )->Buffer;
    config.pszContent = L" ";

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Shows the update completed page.
 *
 * \param Context The setup context.
 */
VOID ShowUpdateCompletedPageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pfCallback = SetupCompletedTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;

    config.cxWidth = 200;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = SetupGetUiString(IDS_SETUP_UPDATE_COMPLETE);
    config.pszContent = SetupGetUiString(IDS_SETUP_SELECT_CLOSE);

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Shows the update error page.
 *
 * \param Context The setup context.
 */
VOID ShowUpdateErrorPageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOG_BUTTON TaskDialogButtonArray[] =
    {
        { IDYES, SetupGetUiString(IDS_SETUP_BUTTON_RETRY) },
        { IDCLOSE, SetupGetUiString(IDS_SETUP_BUTTON_CLOSE) },
    };
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    //config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pfCallback = SetupErrorTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pButtons = TaskDialogButtonArray;
    config.cButtons = ARRAYSIZE(TaskDialogButtonArray);
    config.cxWidth = 200;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = SetupGetUiString(IDS_SETUP_UPDATE_ERROR);

    if (Context->LastStatus)
    {
        PPH_STRING errorString;

        if (errorString = PhGetStatusMessage(Context->LastStatus, 0))
            config.pszContent = PhGetString(errorString);
    }

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
