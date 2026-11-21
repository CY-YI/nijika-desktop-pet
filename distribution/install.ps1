param(
    [switch]$Codex,
    [switch]$Work,
    [switch]$CodexHooks,
    [switch]$ClaudeHooks,
    [switch]$Dsh,
    [switch]$DsBot,
    [switch]$AutoStart,
    [switch]$NoLaunch,
    [switch]$NoShortcuts,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'NijikaDesktopPet\app'),
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex'),
    [string]$DshRoot = (Join-Path $env:USERPROFILE '.dsh'),
    [string]$DsBotRoot = (Join-Path $env:USERPROFILE '.ds-bot')
)

$ErrorActionPreference = 'Stop'
if ($Codex -or $Work -or $Dsh -or $DsBot) {
    throw 'Direct Agent installation was retired. Open Nijika settings > Agent setup and distribute through MAGPIE Library.'
}
$sourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\')
$targetRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
$CodexHome = [IO.Path]::GetFullPath($CodexHome).TrimEnd('\')
$DshRoot = [IO.Path]::GetFullPath($DshRoot).TrimEnd('\')
$DsBotRoot = [IO.Path]::GetFullPath($DsBotRoot).TrimEnd('\')
if ($targetRoot.Equals($sourceRoot, [StringComparison]::OrdinalIgnoreCase) -or
    $targetRoot.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'InstallRoot must be outside the extracted package.'
}
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }

foreach ($relative in @('dist\虹夏桌宠.exe', 'dist\虹夏MCP-v2\虹夏MCP-v2.exe', 'dist\虹夏审批提醒.exe',
        'dist\_nijika_pet_runtime\base_library.zip', 'dist\_nijika_pet_runtime\python312.dll',
        'dist\_nijika_hook_runtime\base_library.zip', 'dist\_nijika_hook_runtime\python312.dll',
        'dist\虹夏MCP-v2\_internal\python312.dll',
        'assets\icons\nijika-shortcut.ico', 'skills\nijika-agent-dialog\SKILL.md',
        'skills\nijika-magpie-setup\SKILL.md',
        'plugins\nijika-work-local\mcp.json', 'integrations\claude-code\install-hooks.ps1',
        'integrations\dsh\install.ps1', 'integrations\dsh\lifecycle-bridge.mjs',
        'AGENT_SETUP.md', 'NOTIFICATION_PROTOCOL.md')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $relative) -PathType Leaf)) {
        throw "Incomplete package: $relative"
    }
}
New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart('\')
    $destination = Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
}
$petExe = Join-Path $targetRoot 'dist\虹夏桌宠.exe'
$mcpExe = Join-Path $targetRoot 'dist\虹夏MCP-v2\虹夏MCP-v2.exe'
$icon = Join-Path $targetRoot 'assets\icons\nijika-shortcut.ico'
$manifestPath = Join-Path $targetRoot 'plugins\nijika-work-local\mcp.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$manifest.mcpServers.'nijika-work-pet'.args[-1] = $mcpExe
[IO.File]::WriteAllText($manifestPath,
    ($manifest | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))

if (-not $NoShortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $shortcut = $shell.CreateShortcut((Join-Path $desktop '虹夏桌宠.lnk'))
    $shortcut.TargetPath = $petExe
    $shortcut.Arguments = '--control-panel'
    $shortcut.WorkingDirectory = Split-Path -Parent $petExe
    $shortcut.IconLocation = $icon
    $shortcut.Save()
    if ($AutoStart) {
        $startup = [Environment]::GetFolderPath('Startup')
        $shortcut = $shell.CreateShortcut((Join-Path $startup '虹夏桌宠.lnk'))
        $shortcut.TargetPath = $petExe
        $shortcut.Arguments = ''
        $shortcut.WorkingDirectory = Split-Path -Parent $petExe
        $shortcut.IconLocation = $icon
        $shortcut.Save()
    }
}

if ($CodexHooks) {
    & (Join-Path $targetRoot 'integrations\codex\install-hooks.ps1') -CodexHome $CodexHome `
        -ApprovalExe (Join-Path $targetRoot 'dist\虹夏审批提醒.exe')
}

if ($ClaudeHooks) {
    & (Join-Path $targetRoot 'integrations\claude-code\install-hooks.ps1') `
        -ApprovalExe (Join-Path $targetRoot 'dist\虹夏审批提醒.exe')
    Write-Output 'Claude Code approval hooks installed. Restart or reload Claude Code settings to apply.'
}

if (-not $NoLaunch) { Start-Process -FilePath $petExe -WorkingDirectory (Split-Path -Parent $petExe) }
Write-Output "Nijika installed at: $targetRoot"
Write-Output "Connect Agents through the MAGPIE guide in Nijika settings."
