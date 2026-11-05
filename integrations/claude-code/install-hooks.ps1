param(
    [string]$UserSettings = (Join-Path $env:USERPROFILE '.claude\settings.json'),
    [string]$ApprovalExe = (Join-Path $PSScriptRoot '..\..\dist\虹夏审批提醒.exe')
)
$ErrorActionPreference = 'Stop'
$exe = (Resolve-Path -LiteralPath $ApprovalExe).Path
$target = $UserSettings
$config = if (Test-Path -LiteralPath $target) {
    Get-Content -LiteralPath $target -Raw -Encoding UTF8 | ConvertFrom-Json
} else { [pscustomobject]@{} }
if (-not $config.PSObject.Properties['hooks']) {
    $config | Add-Member hooks ([pscustomobject]@{}) -Force
}
foreach ($eventName in @('PermissionRequest', 'PostToolUse')) {
    # Replace earlier Nijika entries (packaged exe or source form); keep all others.
    $existing = @($config.hooks.PSObject.Properties[$eventName] | ForEach-Object { $_.Value })
    $others = @($existing | Where-Object {
        $_ -and -not (@($_.hooks | Where-Object {
            $_.command -like '*虹夏审批提醒*' -or
            ((@($_.args) -join ' ') -like '*approval_hook.py*')
        }).Count)
    })
    $hook = [ordered]@{
        type = 'command'
        command = $exe
        args = @('--source', 'claude-code')
        timeout = 10
    }
    if ($eventName -eq 'PostToolUse') { $hook['async'] = $true }
    $entry = [pscustomobject]@{ matcher = '.*'; hooks = @([pscustomobject]$hook) }
    $config.hooks | Add-Member $eventName (@($others) + @($entry)) -Force
}
New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
if (Test-Path -LiteralPath $target) {
    $backupDirectory = Join-Path (Split-Path -Parent $target) 'backups'
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    Copy-Item -LiteralPath $target -Destination (Join-Path $backupDirectory `
        ("settings.json.backup.nijika-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')))
}
[IO.File]::WriteAllText($target, ($config | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
Write-Output "Hook definitions installed: $target"
Write-Output 'Claude Code hot-reloads settings. Clicking the bubble records only; it never grants permission.'
