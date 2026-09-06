# Windows x64 smoke gate for the zh-CN community edition. Each iteration
# starts an isolated sys_info.exe instance, verifies that its main window can
# process WM_NULL, checks the expected plugin module mappings, and requests a
# normal WM_CLOSE shutdown. This is not a visual or interactive UI test.
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
public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lp);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder sb, int max);
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
            [Native.Win]::GetWindowText($windowHandle, $title, 512) | Out-Null
            [void]$list.Add(@{ Handle = $windowHandle; Title = $title.ToString() })
        }

        return $true
    }

    [Native.Win]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
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
$launchArguments = @('-nosettings', '-newinstance')
$expectedModuleMappings = @(
    'ToolStatus.dll',
    'ExtendedTools.dll',
    'ExtendedServices.dll',
    'DotNetTools.dll',
    'HardwareDevices.dll',
    'NetworkTools.dll',
    'OnlineChecks.dll',
    'Updater.dll',
    'UserNotes.dll',
    'WindowExplorer.dll',
    'ExtendedNotifications.dll'
)
$dumpRegistryKey = 'HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps\sys_info.exe'
$dumpKeyCreated = $false
$baselineDumpPaths = @()

try {
    if ($DumpDirectory) {
        $DumpDirectory = [System.IO.Path]::GetFullPath($DumpDirectory)
        [System.IO.Directory]::CreateDirectory($DumpDirectory) | Out-Null

        if (Test-Path -LiteralPath $dumpRegistryKey) {
            throw "LocalDumps key already exists; refusing to overwrite user settings: $dumpRegistryKey"
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
        $iterationSucceeded = $false

        try {
            Write-Host "iteration $iteration/$Iterations: launching $ExePath"
            $process = Start-Process `
                -FilePath $ExePath `
                -ArgumentList $launchArguments `
                -WorkingDirectory $workingDirectory `
                -PassThru

            $mainWindow = $null
            $startupDeadline = (Get-Date).AddSeconds(90)

            while ((Get-Date) -lt $startupDeadline) {
                if ($process.HasExited) {
                    throw "iteration $iteration: process exited during startup with code $($process.ExitCode)"
                }

                $windows = Get-ProcessWindows $process.Id
                $mainWindow = @($windows | Where-Object { $_.Title -match 'sys_info' }) |
                    Select-Object -First 1

                if ($mainWindow) {
                    break
                }

                Start-Sleep -Seconds 1
            }

            if (-not $mainWindow) {
                throw "iteration $iteration: main window was not found within 90 seconds"
            }

            $probeResult = [IntPtr]::Zero
            $probeOk = [Native.Win]::SendMessageTimeout($mainWindow.Handle, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero, 2, 5000, [ref]$probeResult)
            if (-not $probeOk) {
                throw "iteration $iteration: main window did not respond to WM_NULL"
            }

            Start-Sleep -Seconds 5
            $process.Refresh()
            if ($process.HasExited) {
                throw "iteration $iteration: process exited before module mapping check with code $($process.ExitCode)"
            }

            $mappedModules = @($process.Modules | ForEach-Object { $_.ModuleName })
            $missingMappings = @(
                $expectedModuleMappings | Where-Object { $mappedModules -notcontains $_ }
            )
            if ($missingMappings.Count -gt 0) {
                throw "iteration $iteration: missing plugin module mapping: $($missingMappings -join ', ')"
            }

            Write-Host "iteration $iteration: main window responsive; 11 plugin module mappings present"

            if (-not [Native.Win]::PostMessage($mainWindow.Handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
                throw "iteration $iteration: failed to post WM_CLOSE"
            }

            if (-not $process.WaitForExit(30000)) {
                throw "iteration $iteration: process did not exit within 30 seconds after WM_CLOSE"
            }

            $process.Refresh()
            if ($process.ExitCode -ne 0) {
                throw "iteration $iteration: process exited with code $($process.ExitCode)"
            }

            if ($DumpDirectory) {
                Start-Sleep -Seconds 2
                $newDumps = Get-NewDumpFiles $DumpDirectory $baselineDumpPaths
                if ($newDumps.Count -gt 0) {
                    throw "iteration $iteration: new crash dump detected: $($newDumps.FullName -join ', ')"
                }
            }

            $iterationSucceeded = $true
            Write-Host "iteration $iteration: clean exit confirmed"
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
        }
    }

    Write-Host "PASS: $Iterations Windows x64 smoke iterations completed"
}
finally {
    if ($dumpKeyCreated) {
        Remove-Item -LiteralPath $dumpRegistryKey -Recurse -Force
    }
}
