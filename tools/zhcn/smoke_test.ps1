# Windows x64 smoke gate for the zh-CN community edition. Each iteration
# starts an isolated sys_info.exe instance, verifies that its main window can
# process WM_NULL, checks the expected plugin module mappings, and requests a
# normal application Exit command. This is not a visual or interactive UI test.
param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,

    [ValidateRange(1, 100)]
    [int]$Iterations = 3,

    [string]$DumpDirectory
)

$ErrorActionPreference = 'Stop'

Add-Type -Namespace Native -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lp);
[DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr parent, EnumWindowsProc cb, IntPtr lp);
public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lp);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder sb, int max);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder sb, int max);
[DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr hWnd);
[DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wp, IntPtr lp, uint flags, uint timeout, out IntPtr result);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wp, IntPtr lp);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
'@

function Get-ProcessWindows([int]$Id) {
    $list = New-Object System.Collections.ArrayList
    $callback = {
        param($windowHandle, $parameter)

        $windowProcessId = 0
        [Native.Win]::GetWindowThreadProcessId($windowHandle, [ref]$windowProcessId) | Out-Null

        if ($windowProcessId -eq $Id -and [Native.Win]::IsWindowVisible($windowHandle)) {
            $title = New-Object System.Text.StringBuilder 512
            $className = New-Object System.Text.StringBuilder 256
            [Native.Win]::GetWindowText($windowHandle, $title, 512) | Out-Null
            [Native.Win]::GetClassName($windowHandle, $className, 256) | Out-Null
            [void]$list.Add(@{
                Handle = $windowHandle
                Title = $title.ToString()
                ClassName = $className.ToString()
            })
        }

        return $true
    }

    [Native.Win]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
    return ,$list
}

function Get-ChildWindowDescriptions([IntPtr]$ParentHandle) {
    $list = New-Object System.Collections.ArrayList
    $callback = {
        param($windowHandle, $parameter)

        $text = New-Object System.Text.StringBuilder 1024
        $className = New-Object System.Text.StringBuilder 256
        [Native.Win]::GetWindowText($windowHandle, $text, 1024) | Out-Null
        [Native.Win]::GetClassName($windowHandle, $className, 256) | Out-Null
        [void]$list.Add(@{
            ControlId = [Native.Win]::GetDlgCtrlID($windowHandle)
            ClassName = $className.ToString()
            Text = $text.ToString().Replace("`r", ' ').Replace("`n", ' ')
        })

        return $true
    }

    [Native.Win]::EnumChildWindows($ParentHandle, $callback, [IntPtr]::Zero) | Out-Null
    return ,$list
}

function Get-NewDumpFiles([string]$Directory, [string[]]$BaselinePaths) {
    if (-not $Directory) {
        return @()
    }

    return @(
        Get-ChildItem -LiteralPath $Directory -Filter '*.dmp' -File |
            Where-Object { $BaselinePaths -notcontains $_.FullName }
    )
}

$ExePath = (Resolve-Path -LiteralPath $ExePath).Path
$workingDirectory = Split-Path -Parent $ExePath
$exitCommandId = 10001 # ID_HACKER_EXIT in SystemInformer/resource.h
$isolatedSettings = [ordered]@{
    'Language' = 'zh-CN'
    'FirstRun' = 0
    # Plugin settings are unknown when the core first parses the file. The
    # ignored-settings bridge preserves them as strings, then converts them to
    # the plugin's declared integer type after plugin registration.
    'OnlineChecks.PartnerPromptShown' = '1'
    'OnlineChecks.EnableScanning' = '0'
    'OnlineChecks.HybridAnalysisEnableLookups' = '0'
    'OnlineChecks.HybridAnalysisEnableAutoSubmit' = '0'
    'OnlineChecks.VirusTotalEnableLookups' = '0'
}
$settingsJson = $isolatedSettings | ConvertTo-Json -Compress
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$expectedModuleMappings = @(
    'ToolStatus.dll',
    'ExtendedTools.dll',
    'ExtendedServices.dll',
    'DotNetTools.dll',
    'HardwareDevices.dll',
    'NetworkTools.dll',
    'OnlineChecks.dll',
    'UserNotes.dll',
    'WindowExplorer.dll',
    'ExtendedNotifications.dll'
)
$dumpRegistryKey = 'HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps\sys_info.exe'
$dumpParentKeys = @(
    'HKCU:\Software\Microsoft',
    'HKCU:\Software\Microsoft\Windows',
    'HKCU:\Software\Microsoft\Windows\Windows Error Reporting',
    'HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps'
)
$dumpKeyCreated = $false
$createdDumpParentKeys = @()
$baselineDumpPaths = @()

try {
    if ($DumpDirectory) {
        $DumpDirectory = [System.IO.Path]::GetFullPath($DumpDirectory)
        [System.IO.Directory]::CreateDirectory($DumpDirectory) | Out-Null

        if (Test-Path -LiteralPath $dumpRegistryKey) {
            throw "LocalDumps key already exists; refusing to overwrite user settings: $dumpRegistryKey"
        }

        foreach ($dumpParentKey in $dumpParentKeys) {
            if (-not (Test-Path -LiteralPath $dumpParentKey)) {
                New-Item -Path $dumpParentKey | Out-Null
                $createdDumpParentKeys += $dumpParentKey
            }
        }

        New-Item -Path $dumpRegistryKey | Out-Null
        $dumpKeyCreated = $true
        New-ItemProperty -Path $dumpRegistryKey -Name DumpFolder -PropertyType ExpandString -Value $DumpDirectory | Out-Null
        New-ItemProperty -Path $dumpRegistryKey -Name DumpType -PropertyType DWord -Value 2 | Out-Null
        $baselineDumpPaths = @(
            Get-ChildItem -LiteralPath $DumpDirectory -Filter '*.dmp' -File |
                ForEach-Object { $_.FullName }
        )
    }

    for ($iteration = 1; $iteration -le $Iterations; $iteration++) {
        $process = $null
        $settingsFile = $null
        $iterationSucceeded = $false

        try {
            $settingsFile = Join-Path `
                ([System.IO.Path]::GetTempPath()) `
                ("sys_info-smoke-{0}.settings.json" -f [Guid]::NewGuid().ToString('N'))
            [System.IO.File]::WriteAllText($settingsFile, $settingsJson, $utf8NoBom)
            $launchArguments = "-settings `"$settingsFile`" -newinstance"

            Write-Host "iteration $iteration/${Iterations}: launching $ExePath"
            $process = Start-Process `
                -FilePath $ExePath `
                -ArgumentList $launchArguments `
                -WorkingDirectory $workingDirectory `
                -PassThru

            $mainWindow = $null
            $startupDeadline = (Get-Date).AddSeconds(90)

            while ((Get-Date) -lt $startupDeadline) {
                if ($process.HasExited) {
                    throw "iteration ${iteration}: process exited during startup with code $($process.ExitCode)"
                }

                $windows = Get-ProcessWindows $process.Id
                $mainWindow = @($windows | Where-Object { $_.ClassName -eq 'sys_infoMainWindow' }) |
                    Select-Object -First 1

                if ($mainWindow) {
                    break
                }

                Start-Sleep -Seconds 1
            }

            if (-not $mainWindow) {
                $observedWindows = @(
                    $windows | ForEach-Object {
                        $childWindows = @(
                            Get-ChildWindowDescriptions $_.Handle | ForEach-Object {
                                "id=$($_.ControlId) class='$($_.ClassName)' text='$($_.Text)'"
                            }
                        ) -join ', '
                        if (-not $childWindows) {
                            $childWindows = '<none>'
                        }
                        "class='$($_.ClassName)' title='$($_.Title)' children=[$childWindows]"
                    }
                ) -join '; '
                if (-not $observedWindows) {
                    $observedWindows = '<none>'
                }
                throw "iteration ${iteration}: main window was not found within 90 seconds; observed visible windows: $observedWindows"
            }

            $probeResult = [IntPtr]::Zero
            $probeOk = [Native.Win]::SendMessageTimeout($mainWindow.Handle, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero, 2, 5000, [ref]$probeResult)
            if (-not $probeOk) {
                throw "iteration ${iteration}: main window did not respond to WM_NULL"
            }

            Start-Sleep -Seconds 5
            $process.Refresh()
            if ($process.HasExited) {
                throw "iteration ${iteration}: process exited before module mapping check with code $($process.ExitCode)"
            }

            $mappedModules = @($process.Modules | ForEach-Object { $_.ModuleName })
            $missingMappings = @(
                $expectedModuleMappings | Where-Object { $mappedModules -notcontains $_ }
            )
            if ($missingMappings.Count -gt 0) {
                throw "iteration ${iteration}: missing plugin module mapping: $($missingMappings -join ', ')"
            }
            if ($mappedModules -contains 'Updater.dll') {
                throw "iteration ${iteration}: forbidden plugin module mapping: Updater.dll"
            }

            Write-Host "iteration ${iteration}: main window responsive; $($expectedModuleMappings.Count) plugin module mappings present"

            if (-not [Native.Win]::PostMessage($mainWindow.Handle, 0x0111, [IntPtr]$exitCommandId, [IntPtr]::Zero)) {
                throw "iteration ${iteration}: failed to post the application Exit command"
            }

            if (-not $process.WaitForExit(30000)) {
                throw "iteration ${iteration}: process did not exit within 30 seconds after the application Exit command"
            }

            $process.Refresh()
            if ($process.ExitCode -ne 0) {
                throw "iteration ${iteration}: process exited with code $($process.ExitCode)"
            }

            if ($DumpDirectory) {
                Start-Sleep -Seconds 2
                $newDumps = Get-NewDumpFiles $DumpDirectory $baselineDumpPaths
                if ($newDumps.Count -gt 0) {
                    throw "iteration ${iteration}: new crash dump detected: $($newDumps.FullName -join ', ')"
                }
            }

            $iterationSucceeded = $true
            Write-Host "iteration ${iteration}: clean exit confirmed"
        }
        finally {
            if ($process) {
                if (-not $iterationSucceeded -and -not $process.HasExited) {
                    Write-Warning "iteration $iteration failed; forcing cleanup of process $($process.Id)"

                    try {
                        Stop-Process -Id $process.Id -Force -ErrorAction Stop
                    }
                    catch {
                        Write-Warning "failed to force cleanup process $($process.Id): $($_.Exception.Message)"
                    }
                }

                $process.Dispose()
            }

            if ($settingsFile -and (Test-Path -LiteralPath $settingsFile)) {
                Remove-Item -LiteralPath $settingsFile -Force
            }
        }
    }

    Write-Host "PASS: $Iterations Windows x64 smoke iterations completed"
}
finally {
    if ($dumpKeyCreated) {
        Remove-Item -LiteralPath $dumpRegistryKey -Recurse -Force
    }

    for ($parentIndex = $createdDumpParentKeys.Count - 1; $parentIndex -ge 0; $parentIndex--) {
        $createdParentKey = $createdDumpParentKeys[$parentIndex]
        if (Test-Path -LiteralPath $createdParentKey) {
            Remove-Item -LiteralPath $createdParentKey
        }
    }
}
