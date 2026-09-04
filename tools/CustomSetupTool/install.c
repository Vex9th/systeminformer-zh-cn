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
 * Installs System Informer.
 *
 * \param Context The setup context.
 * \return Successful or errant status.
 */
_Function_class_(USER_THREAD_START_ROUTINE)
NTSTATUS CALLBACK SetupProgressThread(
    _In_ PVOID Context
    )
{
    PPH_SETUP_CONTEXT context = (PPH_SETUP_CONTEXT)Context;
    NTSTATUS status;
    BOOLEAN updateDesktopShortcut = TRUE;
    BOOLEAN desktopShortcutExists = FALSE;
    BOOLEAN removeStartMenuFolder = FALSE;
    PPH_STRING previousInstallPath;
    PPH_STRING currentInstallPath;
    PPH_STRING desktopShortcutPath;

    context->SetupProgressActive = TRUE;

    previousInstallPath = GetApplicationInstallPath();
    currentInstallPath = SetupCreateFullPath(context->SetupInstallPath, L"");

    if (!PhIsNullOrEmptyString(previousInstallPath) &&
        !PhIsNullOrEmptyString(currentInstallPath) &&
        PhEqualStringRef(&previousInstallPath->sr, &currentInstallPath->sr, TRUE))
    {
        if (desktopShortcutPath = PhGetKnownFolderPathZ(&FOLDERID_PublicDesktop, L"\\System Informer.lnk"))
        {
            desktopShortcutExists = PhDoesFileExistWin32(PhGetString(desktopShortcutPath));
            PhDereferenceObject(desktopShortcutPath);
        }

        updateDesktopShortcut = context->SetupCreateDesktopShortcut != desktopShortcutExists;
    }

    PhClearReference(&previousInstallPath);
    PhClearReference(&currentInstallPath);

    if (!PhIsNullOrEmptyString(context->SetupPreviousStartMenuFolderName) && (!context->SetupCreateStartMenuShortcuts ||
        !PhEqualStringRef(&context->SetupPreviousStartMenuFolderName->sr, &context->SetupStartMenuFolderName->sr, TRUE)))
    {
        removeStartMenuFolder = TRUE;
    }

    //
    // Create the folder.
    //

    SetupSetProgressMarquee(context, TRUE);
    SetupSetProgressTextResource(context, IDS_SETUP_CREATING_INSTALL_DIRECTORY);

    if (!NT_SUCCESS(status = PhCreateDirectoryWin32(&context->SetupInstallPath->sr)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

#ifndef FORCE_TEST_UPDATE_LOCAL_INSTALL

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
    // Upgrade the settings file.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_UPDATING_SETTINGS);
    SetupUpgradeSettingsFile();

    //
    // Convert the settings file.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_CONVERTING_SETTINGS);
    SetupConvertSettingsFile();

    // Remove the previous installation.
    //if (Context->SetupResetSettings)
    //    PhDeleteDirectory(Context->SetupInstallPath);

    // Perform Windows Options cleanup (registry)
    SetupSetProgressTextResource(context, IDS_SETUP_REMOVING_WINDOWS_INTEGRATION);
    SetupDeleteWindowsOptions(Context);

    // Delete all shortcuts for cleanup

    SetupSetProgressTextResource(context, IDS_SETUP_REMOVING_SHORTCUTS);
    SetupDeleteShortcuts(Context, updateDesktopShortcut, removeStartMenuFolder);

    //
    // Create the uninstaller.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_CREATING_UNINSTALLER);

    if (!NT_SUCCESS(status = SetupCreateUninstallFile(context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    //
    // Create the ARP uninstall entries.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_CREATING_UNINSTALL_REGISTRATION);
    SetupCreateUninstallKey(Context);

    //
    // Create Windows Error Reporting LocalDumps key.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_CREATING_LOCALDUMPS);
    SetupCreateLocalDumpsKey();

    //
    // Create autorun.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_CREATING_WINDOWS_INTEGRATION);
    SetupCreateWindowsOptions(Context);

    //
    // Create shortcuts.
    //

    SetupSetProgressTextResource(context, IDS_SETUP_CREATING_SHORTCUTS);
    SetupCreateShortcuts(Context, updateDesktopShortcut);

    // Set the default image execution options.
    //
    //SetupCreateImageFileExecutionOptions();

#endif

    //
    // Extract the updated files.
    //
    SetupSetProgressTextResource(context, IDS_SETUP_EXTRACTING_FILES);

    if (!NT_SUCCESS(status = SetupExtractBuild(Context)))
    {
        context->LastStatus = status;
        goto CleanupExit;
    }

    SetupSetProgressTextResource(context, IDS_SETUP_INSTALLATION_COMPLETE);
    SetupSetProgressValue(context, 100);
    context->SetupProgressActive = FALSE;
    context->SetupCompleted = TRUE;
    PostMessage(context->DialogHandle, SETUP_SHOWFINAL, 0, 0);
    return STATUS_SUCCESS;

CleanupExit:
    SetupSetProgressTextResource(context, IDS_SETUP_INSTALLATION_FAILED);
    context->SetupProgressActive = FALSE;
    PostMessage(context->DialogHandle, SETUP_SHOWERROR, 0, 0);
    return STATUS_UNSUCCESSFUL;
}
