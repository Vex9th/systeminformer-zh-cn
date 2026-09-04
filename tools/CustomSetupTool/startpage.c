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
 * Shows the installation directory browse dialog.
 *
 * \param Context The setup context.
 */
VOID SetupShowBrowseDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    PVOID fileDialog;

    if (fileDialog = PhCreateOpenFileDialog())
    {
        PhSetFileDialogOptions(fileDialog, PH_FILEDIALOG_PICKFOLDERS);

        if (PhShowFileDialog(Context->DialogHandle, fileDialog))
        {
            PPH_STRING fileDialogFolderPath;

            fileDialogFolderPath = PhGetFileDialogFileName(fileDialog);
            PhTrimToNullTerminatorString(fileDialogFolderPath);
            PhSwapReference(&Context->SetupInstallPath, fileDialogFolderPath);
        }

        PhFreeFileDialog(fileDialog);
    }

    if (PhIsNullOrEmptyString(Context->SetupInstallPath))
    {
        Context->SetupInstallPath = SetupFindInstallDirectory();
    }

    if (!PhIsNullOrEmptyString(Context->SetupInstallPath))
    {
        if (!PhEndsWithStringRef(&Context->SetupInstallPath->sr, &PhNtPathSeparatorString, TRUE))
        {
            PhSwapReference(&Context->SetupInstallPath, PhConcatStringRef2(&Context->SetupInstallPath->sr, &PhNtPathSeparatorString));
        }
    }
}

/**
 * Callback for checking whether a directory contains files.
 *
 * \param RootDirectory The root directory handle.
 * \param Information The file directory information.
 * \param Context The file count.
 * \return TRUE to continue enumeration, FALSE to stop.
 */
_Function_class_(PH_ENUM_DIRECTORY_FILE)
static BOOLEAN CALLBACK SetupCheckDirectoryCallback(
    _In_ HANDLE RootDirectory,
    _In_ PFILE_DIRECTORY_INFORMATION Information,
    _In_ PVOID Context
    )
{
    PH_STRINGREF baseName;

    baseName.Buffer = Information->FileName;
    baseName.Length = Information->FileNameLength;

    if (PhEqualStringRef2(&baseName, L".", TRUE) || PhEqualStringRef2(&baseName, L"..", TRUE))
        return TRUE;

    (*(PULONG)Context) += 1;
    return FALSE;
}

/**
 * Shows a warning prompt for a non-empty installation directory.
 *
 * \param Context The setup context.
 * \return TRUE if the directory warning should be shown, otherwise FALSE.
 */
BOOLEAN SetupShowDirectoryWarningPrompt(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    if (PhDoesFileExistWin32(PhGetString(Context->SetupInstallPath)))
    {
        HANDLE directoryHandle;
        ULONG count = 0;

        if (NT_SUCCESS(PhCreateFileWin32(
            &directoryHandle,
            PhGetString(Context->SetupInstallPath),
            FILE_LIST_DIRECTORY | SYNCHRONIZE,
            FILE_ATTRIBUTE_DIRECTORY,
            FILE_SHARE_READ,
            FILE_OPEN,
            FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT
            )))
        {
            PhEnumDirectoryFile(directoryHandle, NULL, SetupCheckDirectoryCallback, &count);
            NtClose(directoryHandle);
        }

        if (count != 0)
        {
            return TRUE;
        }
    }

    return FALSE;
}

/**
 * Shows the setup error page.
 *
 * \param Context The setup context.
 */
VOID ShowErrorPageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;
    PPH_STRING string;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = SetupGetUiString(IDS_SETUP_FAILED);
    config.cxWidth = 200;

    if (string = PhGetStatusMessage(Context->LastStatus, 0))
        config.pszContent = PhaFormatString(SetupGetUiString(IDS_SETUP_ERROR_STATUS_FORMAT), PhGetString(string))->Buffer;
    else
        config.pszContent = SetupGetUiString(IDS_SETUP_CLOSE_EXIT);

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Callback for the welcome task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupWelcomePageCallbackProc(
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
            PhCenterWindow(hwndDlg, NULL);

            if (!PhGetOwnTokenAttributes().Elevated)
            {
                SendMessage(hwndDlg, TDM_SET_BUTTON_ELEVATION_REQUIRED_STATE, IDCONTINUE, TRUE);
            }
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDCONTINUE)
            {
#ifndef FORCE_TEST_UPDATE_LOCAL_INSTALL
                if (PhGetOwnTokenAttributes().Elevated)
                {
                    if (!context->SetupIsLegacyUpdate && NT_SUCCESS(SetupLegacySetupInstalled()))
                    {
                        SetupShowMessagePromptForLegacyVersion();
                    }

                    ShowConfigPageDialog(context);
                    return S_FALSE;
                }
                else
                {
                    NTSTATUS status;
                    PPH_STRING applicationFileName;
                    PPH_STRING applicationCommandLine;
                    PH_STRINGREF applicationCommandLineStringRef;

                    if (!NT_SUCCESS(status = PhGetProcessCommandLineStringRef(&applicationCommandLineStringRef)))
                    {
                        context->LastStatus = status;
                        return S_FALSE;
                    }
                    if (!(applicationFileName = PhGetApplicationFileNameWin32()))
                    {
                        context->LastStatus = STATUS_NO_MEMORY;
                        return S_FALSE;
                    }
                    applicationCommandLine = PhCreateString2(&applicationCommandLineStringRef);

                    status = PhShellExecuteEx(
                        hwndDlg,
                        PhGetString(applicationFileName),
                        PhGetString(applicationCommandLine),
                        NULL,
                        SW_SHOW,
                        PH_SHELL_EXECUTE_ADMIN,
                        0,
                        &context->SubProcessHandle
                        );

                    PhDereferenceObject(applicationCommandLine);
                    PhDereferenceObject(applicationFileName);

                    if (NT_SUCCESS(status))
                    {
                        ShowWindow(hwndDlg, SW_HIDE);
                    }
                    else
                    {
                        context->LastStatus = status;
                        return S_FALSE;
                    }
                }
#else
                ShowConfigPageDialog(context);
                return S_FALSE;
#endif
            }
        }
        break;
    }

    return S_OK;
}

/**
 * Shows the welcome page.
 *
 * \param Context The setup context.
 */
VOID ShowWelcomePageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOG_BUTTON buttonArray[] =
    {
        { IDCONTINUE, SetupGetUiString(IDS_SETUP_BUTTON_INSTALL) }
    };
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pButtons = buttonArray;
    config.cButtons = ARRAYSIZE(buttonArray);
    config.pfCallback = SetupWelcomePageCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = PhApplicationName;
    config.pszContent = SetupGetUiString(IDS_SETUP_PRODUCT_DESCRIPTION);
    config.cxWidth = 200;

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Callback for the completed task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupCompletePageCallbackProc(
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
        break;
    }

    return S_OK;
}

/**
 * Shows the completed page.
 *
 * \param Context The setup context.
 */
VOID ShowCompletedPageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_VERIFICATION_FLAG_CHECKED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pfCallback = SetupCompletePageCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = PhaFormatString(SetupGetUiString(IDS_SETUP_COMPLETE_FORMAT), PhApplicationName)->Buffer;
    config.pszContent = SetupGetUiString(IDS_SETUP_CLOSE_EXIT);
    config.pszVerificationText = SetupGetUiString(IDS_SETUP_START_PROGRAM_ON_EXIT);
    config.cxWidth = 200;

#ifdef FORCE_TEST_UPDATE_LOCAL_INSTALL
    ClearFlag(config.dwFlags, TDF_VERIFICATION_FLAG_CHECKED);
#endif

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Callback for the configuration task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupConfigPageCallbackProc(
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
            PPH_STRING status;

            status = PhFormatString(
                SetupGetUiString(IDS_SETUP_INSTALLATION_FOLDER_FORMAT),
                PhGetStringOrEmpty(context->SetupInstallPath)
                );
            SendMessage(hwndDlg, TDM_UPDATE_ELEMENT_TEXT, TDE_CONTENT, (LPARAM)status->Buffer);
            PhDereferenceObject(status);
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            if ((INT)wParam == IDYES)
            {
                PPH_STRING status;

                SetupShowBrowseDialog(context);

                status = PhFormatString(
                    SetupGetUiString(IDS_SETUP_INSTALLATION_FOLDER_FORMAT),
                    PhGetStringOrEmpty(context->SetupInstallPath)
                    );
                SendMessage(hwndDlg, TDM_UPDATE_ELEMENT_TEXT, TDE_CONTENT, (LPARAM)status->Buffer);
                PhDereferenceObject(status);

                return S_FALSE;
            }

            if ((INT)wParam == IDOK)
            {
                if (PhIsNullOrEmptyString(context->SetupInstallPath))
                    return S_FALSE;

                //if (SetupShowDirectoryWarningPrompt(context))
                //    return S_FALSE;

                if (SetupShowDirectoryWarningPrompt(context))
                {
                    ShowConfigDirectoryNonEmptyDialog(context);
                    return S_FALSE;
                }

                ShowInstallPageDialog(context);
                return S_FALSE;
            }
        }
        break;
    }

    return S_OK;
}

/**
 * Shows the configuration page.
 *
 * \param Context The setup context.
 */
VOID ShowConfigPageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOG_BUTTON buttonConfig[] =
    {
        { IDYES, SetupGetUiString(IDS_SETUP_BUTTON_BROWSE) },
        { IDOK, SetupGetUiString(IDS_SETUP_BUTTON_NEXT_PLAIN) },
    };
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pButtons = buttonConfig;
    config.cButtons = ARRAYSIZE(buttonConfig);
    config.pfCallback = SetupConfigPageCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.cxWidth = 200;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = SetupGetUiString(IDS_SETUP_OPTIONS_TITLE);
    config.pszContent = SetupGetUiString(IDS_SETUP_INSTALLATION_FOLDER);

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Callback for the non-empty directory task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupDirectoryNonEmptyTaskDialogCallbackProc(
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
            if ((INT)wParam == IDNO)
            {
                ShowInstallPageDialog(context);
                return S_FALSE;
            }

            if ((INT)wParam == IDYES)
            {
                ShowConfigPageDialog(context);
                return S_FALSE;
            }
        }
        break;
    }

    return S_OK;
}

/**
 * Shows the non-empty directory warning page.
 *
 * \param Context The setup context.
 */
VOID ShowConfigDirectoryNonEmptyDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOG_BUTTON buttonConfig[] =
    {
        { IDYES, SetupGetUiString(IDS_SETUP_BUTTON_CHANGE_DIRECTORY) },
        { IDNO, SetupGetUiString(IDS_SETUP_BUTTON_CONTINUE) },
    };
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.pszMainIcon = TD_WARNING_ICON;
    config.pButtons = buttonConfig;
    config.cButtons = ARRAYSIZE(buttonConfig);
    config.pfCallback = SetupDirectoryNonEmptyTaskDialogCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.cxWidth = 200;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = SetupGetUiString(IDS_SETUP_WARNING);
    config.pszContent = SetupGetUiString(IDS_SETUP_DIRECTORY_NOT_EMPTY);

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}

/**
 * Callback for the installation task dialog.
 *
 * \param hwndDlg The task dialog window handle.
 * \param uMsg The notification message.
 * \param wParam Additional message information.
 * \param lParam Additional message information.
 * \param dwRefData The setup context.
 * \return S_OK to continue, otherwise an HRESULT value.
 */
HRESULT CALLBACK SetupInstallPageCallbackProc(
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
            SendMessage(hwndDlg, TDM_SET_MARQUEE_PROGRESS_BAR, TRUE, 0);
            SendMessage(hwndDlg, TDM_SET_PROGRESS_BAR_MARQUEE, TRUE, 1);

            PhCreateThread2(SetupProgressThread, context);
        }
        break;
    case TDN_BUTTON_CLICKED:
        {
            return S_FALSE;
        }
        break;
    }

    return S_OK;
}

/**
 * Shows the installation progress page.
 *
 * \param Context The setup context.
 */
VOID ShowInstallPageDialog(
    _In_ PPH_SETUP_CONTEXT Context
    )
{
    TASKDIALOGCONFIG config;

    memset(&config, 0, sizeof(TASKDIALOGCONFIG));
    config.cbSize = sizeof(TASKDIALOGCONFIG);
    config.dwFlags = TDF_USE_HICON_MAIN | TDF_ALLOW_DIALOG_CANCELLATION | TDF_CAN_BE_MINIMIZED | TDF_SHOW_MARQUEE_PROGRESS_BAR;
    config.dwCommonButtons = TDCBF_CLOSE_BUTTON;
    config.hMainIcon = Context->IconLargeHandle;
    config.pfCallback = SetupInstallPageCallbackProc;
    config.lpCallbackData = (LONG_PTR)Context;
    config.cxWidth = 200;
    config.pszWindowTitle = PhApplicationName;
    config.pszMainInstruction = SetupGetUiString(IDS_SETUP_PREPARING_INSTALL);
    config.pszContent = L" ";

    PhTaskDialogNavigatePage(Context->DialogHandle, &config);
}
