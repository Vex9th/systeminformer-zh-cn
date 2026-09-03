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
            if ($sb.Length -gt 0) { [void]$list.Add(@{ Handle = $hWnd; Title = $sb.ToString() }) }
        }
        return $true
    }
    [Native.Win]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
    return $list
}

function HasChinese([string]$s) {
    return $s -match '[\u4e00-\u9fff]'
}

$ExePath = (Resolve-Path $ExePath).Path
$workDir = Split-Path $ExePath
Write-Host "launching: $ExePath"
$p = Start-Process -FilePath $ExePath -WorkingDirectory $workDir -PassThru
$failed = $false

try {
    Start-Sleep -Seconds 20
    if ($p.HasExited) { throw "process exited during startup (code $($p.ExitCode))" }
    $p.Refresh()

    # 1. main window title must contain sys_info
    if ($p.MainWindowTitle -notmatch 'sys_info') {
        Write-Host "::error::main window title is '$($p.MainWindowTitle)', expected sys_info"
        $failed = $true
    } else {
        Write-Host "PASS main title: $($p.MainWindowTitle)"
    }

    # 2. main menu must contain Chinese entries
    $hWnd = $p.MainWindowHandle
    $hMenu = [Native.Win]::GetMenu($hWnd)
    $menuText = ''
    if ($hMenu -ne [IntPtr]::Zero) {
        $count = [Native.Win]::GetMenuItemCount($hMenu)
        for ($i = 0; $i -lt $count; $i++) {
            $sb = New-Object System.Text.StringBuilder 256
            [Native.Win]::GetMenuString($hMenu, $i, $sb, 256, 0x400) | Out-Null  # MF_BYPOSITION
            $menuText += $sb.ToString() + ' '
        }
    }
    if (-not (HasChinese $menuText)) {
        Write-Host "::error::main menu has no Chinese text: '$menuText'"
        $failed = $true
    } else {
        Write-Host "PASS main menu: $menuText"
    }

    # 3. open the Options dialog (ID_HACKER_OPTIONS = 10083) and verify Chinese
    [Native.Win]::PostMessage($hWnd, 0x0111, [IntPtr]10083, [IntPtr]::Zero) | Out-Null  # WM_COMMAND
    Start-Sleep -Seconds 8
    $windows = Get-ProcessWindows($p.Id)
    $optionsWin = $windows | Where-Object { $_.Title -match '设置|选项' } | Select-Object -First 1
    if (-not $optionsWin) {
        $titles = ($windows | ForEach-Object { $_.Title }) -join ' | '
        Write-Host "::error::options dialog not found or caption not Chinese; titles: $titles"
        $failed = $true
    } else {
        Write-Host "PASS options caption: $($optionsWin.Title)"
    }

    if ($failed) { exit 1 }
    Write-Host 'ALL RUNTIME SMOKE CHECKS PASSED'
}
finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
