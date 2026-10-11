param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex'),
    [string]$ApprovalExe = (Join-Path $PSScriptRoot '..\..\dist\虹夏审批提醒.exe')
)
$ErrorActionPreference = 'Stop'
$exe = (Resolve-Path -LiteralPath $ApprovalExe).Path
$target = Join-Path $CodexHome 'hooks.json'
$config = if (Test-Path -LiteralPath $target) {
    Get-Content -LiteralPath $target -Raw -Encoding UTF8 | ConvertFrom-Json
} else { [pscustomobject]@{ hooks = [pscustomobject]@{} } }
if (-not $config.hooks) { $config | Add-Member hooks ([pscustomobject]@{}) -Force }
$template = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'hooks.example.json') -Raw -Encoding UTF8 | ConvertFrom-Json
# A fixed executable invocation only. Event data arrives over stdin, never interpolation.
$command = 'powershell.exe -NoLogo -NoProfile -NonInteractive -Command "& ''' + $exe.Replace("'", "''") + '''"'
foreach ($eventName in @('PermissionRequest', 'PostToolUse')) {
    $others = @($config.hooks.$eventName | Where-Object {
        $_ -and -not (@($_.hooks | Where-Object { $_.command -like '*虹夏审批提醒.exe*' }).Count)
    })
    $entry = $template.hooks.$eventName[0]
    $entry.hooks[0].command = $command
    $config.hooks | Add-Member $eventName (@($others) + @($entry)) -Force
}
New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null
if (Test-Path -LiteralPath $target) {
    Copy-Item -LiteralPath $target -Destination "$target.bak-nijika-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
}
[IO.File]::WriteAllText($target, ($config | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
Write-Output "Hook definitions installed: $target"
Write-Output 'Review and trust both Nijika hooks in /hooks, then start a new task. No trust or permission setting was changed.'
