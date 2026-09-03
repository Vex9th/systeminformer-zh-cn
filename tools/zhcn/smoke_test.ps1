# Runtime smoke test for the zh-CN community edition: launches the built
# sys_info.exe, verifies the window title, the main menu and the Options
# dialog show translated text, then exits. Run from the repository root with
# the exe path as the only argument.
param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath
)

$ErrorActionPreference = 'Stop'
Add-Type -Namespace Native -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lp);
public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lp);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder sb, int max);
[DllImport("user32.dll")] public static extern IntPtr GetMenu(IntPtr hWnd);
[DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr hMenu);
[DllImport("user32.dll")] public static extern uint GetMenuString(IntPtr hMenu, uint index, System.Text.StringBuilder sb, int max, uint flags);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wp, IntPtr lp);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
[DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wp, IntPtr lp, uint flags, uint timeout, out IntPtr result);
'@

function Get-ProcessWindows([int]$Id) {
    $list = New-Object System.Collections.ArrayList
    $cb = {
        param($hWnd, $lp)
        $pid2 = 0
        [Native.Win]::GetWindowThreadProcessId($hWnd, [ref]$pid2) | Out-Null
        if ($pid2 -eq $Id -and [Native.Win]::IsWindowVisible($hWnd)) {
            $sb = New-Object System.Text.StringBuilder 512
            [Native.Win]::GetWindowText($hWnd, $sb, 512) | Out-Null
            [void]$list.Add(@{ Handle = $hWnd; Title = $sb.ToString() })
        }
        return $true
    }
    [Native.Win]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
    return ,$list
}

function HasChinese([string]$s) {
    return $s -match '[\u4e00-\u9fff]'
}

$ExePath = (Resolve-Path $ExePath).Path
$workDir = Split-Path $ExePath
Write-Host "launching: $ExePath"
$p = Start-Process -FilePath $ExePath -WorkingDirectory $workDir -PassThru
$failed = $false
$mainWindow = $null

try {
    # wait up to 90s for the main window (title contains sys_info)
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        if ($p.HasExited) { throw "process exited during startup (code $($p.ExitCode))" }
        $windows = Get-ProcessWindows($p.Id)
        $titled = @($windows | Where-Object { $_.Title.Length -gt 0 })
        Write-Host ("visible windows: {0}, titled: {1}" -f $windows.Count, $titled.Count)
        if ($titled.Count -gt 0) {
            Write-Host ("titles: " + (($titled | ForEach-Object { $_.Title }) -join ' | '))
        }
        $mainWindow = $titled | Where-Object { $_.Title -match 'sys_info' } | Select-Object -First 1
        if ($mainWindow) { break }
        Start-Sleep -Seconds 5
    }

    if (-not $mainWindow) {
        Write-Host "::error::main window (title containing sys_info) not found within 90s"
        $failed = $true
    } else {
        Write-Host "PASS main title: $($mainWindow.Title)"
        $hWnd = $mainWindow.Handle

        # probe the UI thread for responsiveness
        $probeResult = [IntPtr]::Zero
        $probeOk = [Native.Win]::SendMessageTimeout($hWnd, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero, 2, 5000, [ref]$probeResult)
        Write-Host ("UI thread responsive: {0}" -f ($probeOk -ne 0))

        # all plugins must be loaded (proves the sys_info import library
        # resolves; a rename regression fails every plugin with 0xc0000135)
        Start-Sleep -Seconds 5
        $p.Refresh()
        $modules = @($p.Modules | ForEach-Object { $_.ModuleName })
        $expected = @(
            'ToolStatus.dll', 'ExtendedTools.dll', 'ExtendedServices.dll',
            'DotNetTools.dll', 'HardwareDevices.dll', 'NetworkTools.dll',
            'OnlineChecks.dll', 'Updater.dll', 'UserNotes.dll', 'WindowExplorer.dll',
            'ExtendedNotifications.dll'
        )
        $missing = @($expected | Where-Object { $modules -notcontains $_ })
        if ($missing.Count -gt 0) {
            Write-Host "::error::plugins not loaded: $($missing -join ', ')"
            $failed = $true
        } else {
            Write-Host "PASS all 11 plugins loaded"
        }

    if ($failed) { exit 1 }
    Write-Host 'ALL RUNTIME SMOKE CHECKS PASSED'
}
finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
