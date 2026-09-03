# Runtime smoke test for the zh-CN community edition: launches the built
# sys_info.exe, verifies the main window title and that every plugin is
# loaded (plugin imports resolve against the renamed module), then exits.
# Menu and dialog text are validated separately at the byte level by
# validate_templates.py, because an interactive desktop is not available in
# this environment. Run from the repository root with the exe path argument.
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
[DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wp, IntPtr lp, uint flags, uint timeout, out IntPtr result);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
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

$ExePath = (Resolve-Path $ExePath).Path
$workDir = Split-Path $ExePath
Write-Host "launching: $ExePath"
$p = Start-Process -FilePath $ExePath -WorkingDirectory $workDir -PassThru
$failed = $false

try {
    # wait up to 90s for the main window (title contains sys_info)
    $mainWindow = $null
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

        # the UI thread must be responsive
        $probeResult = [IntPtr]::Zero
        $probeOk = [Native.Win]::SendMessageTimeout($mainWindow.Handle, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero, 2, 5000, [ref]$probeResult)
        if (-not $probeOk) {
            Write-Host "::error::UI thread not responsive"
            $failed = $true
        } else {
            Write-Host "PASS UI thread responsive"
        }
    }

    # all plugins must be loaded; a rename regression makes every plugin fail
    # with 0xc0000135, so this directly guards the sys_info import contract
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
