param(
    [switch]$Codex,
    [switch]$Work,
    [switch]$CodexHooks,
    [switch]$ClaudeHooks,
    [switch]$Dsh,
    [switch]$AutoStart,
    [switch]$NoLaunch,
    [switch]$NoShortcuts,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'NijikaDesktopPet\app'),
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex'),
    [string]$DshRoot = (Join-Path $env:USERPROFILE '.dsh')
)

$ErrorActionPreference = 'Stop'
$sourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\')
$targetRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
$CodexHome = [IO.Path]::GetFullPath($CodexHome).TrimEnd('\')
$DshRoot = [IO.Path]::GetFullPath($DshRoot).TrimEnd('\')
if ($targetRoot.Equals($sourceRoot, [StringComparison]::OrdinalIgnoreCase) -or
    $targetRoot.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'InstallRoot must be outside the extracted package.'
}
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }

foreach ($relative in @('dist\虹夏桌宠.exe', 'dist\虹夏MCP-v2.exe', 'dist\虹夏审批提醒.exe',
        'assets\icons\nijika-shortcut.ico', 'skills\nijika-desktop-dialog\SKILL.md',
        'plugins\nijika-work-local\mcp.json', 'integrations\claude-code\install-hooks.ps1',
        'integrations\dsh\install.ps1', 'integrations\dsh\lifecycle-bridge.mjs',
        'AGENT_SETUP.md', 'NOTIFICATION_PROTOCOL.md')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $relative) -PathType Leaf)) {
        throw "Incomplete package: $relative"
    }
}
if (($Codex -or $Work) -and -not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw 'Codex CLI is not on PATH. Run without -Codex/-Work to install the pet, then connect an Agent later.'
}
if ($Codex -or $Work) {
    New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null
    # codex.exe/codex.cmd resolves its MCP, plugin and hook state from
    # CODEX_HOME. Keep a recipient-supplied -CodexHome authoritative.
    $env:CODEX_HOME = $CodexHome
}
if ($Work -and -not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    throw 'The current Work plugin launcher requires python.exe on PATH. Install Python, or run without -Work.'
}
if ($Dsh -and -not (Test-Path -LiteralPath $DshRoot -PathType Container)) {
    throw "DSH home does not exist: $DshRoot"
}

New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart('\')
    $destination = Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
}
$petExe = Join-Path $targetRoot 'dist\虹夏桌宠.exe'
$mcpExe = Join-Path $targetRoot 'dist\虹夏MCP-v2.exe'
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
    $shortcut.WorkingDirectory = Split-Path -Parent $petExe
    $shortcut.IconLocation = $icon
    $shortcut.Save()
    $controlShortcut = $shell.CreateShortcut((Join-Path $desktop '虹夏桌宠设置.lnk'))
    $controlShortcut.TargetPath = $petExe
    $controlShortcut.Arguments = '--control-panel'
    $controlShortcut.WorkingDirectory = Split-Path -Parent $petExe
    $controlShortcut.IconLocation = $icon
    $controlShortcut.Save()
    if ($AutoStart) {
        $startup = [Environment]::GetFolderPath('Startup')
        $shortcut = $shell.CreateShortcut((Join-Path $startup '虹夏桌宠.lnk'))
        $shortcut.TargetPath = $petExe
        $shortcut.WorkingDirectory = Split-Path -Parent $petExe
        $shortcut.IconLocation = $icon
        $shortcut.Save()
    }
}

function Update-MarkedBlock {
    param([string]$Path, [string]$Block)
    $start = '# BEGIN NIJIKA-CODEX-DIALOG'
    $end = '# END NIJIKA-CODEX-DIALOG'
    $current = if (Test-Path -LiteralPath $Path) { [IO.File]::ReadAllText($Path) } else { '' }
    $startAt = $current.IndexOf($start, [StringComparison]::Ordinal)
    $endAt = $current.IndexOf($end, [StringComparison]::Ordinal)
    if (($startAt -ge 0) -ne ($endAt -ge 0)) { throw "Incomplete Nijika block in $Path" }
    if ($startAt -ge 0) {
        if ($endAt -lt $startAt) { throw "Invalid Nijika block in $Path" }
        $updated = $current.Substring(0, $startAt) + $Block.TrimEnd() +
            $current.Substring($endAt + $end.Length)
    } else {
        $updated = $current.TrimEnd("`r", "`n") + "`n`n" + $Block.TrimEnd() + "`n"
    }
    if ($updated -eq $current) { return }
    if (Test-Path -LiteralPath $Path) {
        Copy-Item -LiteralPath $Path -Destination "$Path.bak-nijika-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
    }
    [IO.File]::WriteAllText($Path, $updated, [Text.UTF8Encoding]::new($false))
}

if ($Codex) {
    $skillTarget = Join-Path $CodexHome 'skills\nijika-desktop-dialog\SKILL.md'
    New-Item -ItemType Directory -Path (Split-Path -Parent $skillTarget) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $targetRoot 'skills\nijika-desktop-dialog\SKILL.md') `
        -Destination $skillTarget -Force
    $block = [IO.File]::ReadAllText((Join-Path $targetRoot 'distribution\codex-global-instructions.txt'))
    New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null
    Update-MarkedBlock -Path (Join-Path $CodexHome 'AGENTS.md') -Block $block
    & codex mcp get nijika-pet *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Warning 'nijika-pet already exists in Codex. Check its executable path; this installer did not overwrite it.'
    } else {
        & codex mcp add nijika-pet -- $mcpExe
        if ($LASTEXITCODE -ne 0) { throw 'Codex MCP registration failed.' }
    }
    Write-Output 'Codex skill and global trigger rule installed.'
}

if ($Work) {
    & codex plugin marketplace add $targetRoot --json
    if ($LASTEXITCODE -ne 0) { throw 'Work plugin marketplace registration failed.' }
    & codex plugin add nijika-work-local@nijika-local --json
    if ($LASTEXITCODE -ne 0) { throw 'Work plugin installation failed.' }
    Write-Output 'Work plugin installed. Restart the ChatGPT desktop app and use a new local Work task.'
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

if ($Dsh) {
    & (Join-Path $targetRoot 'integrations\dsh\install.ps1') -DshRoot $DshRoot
    Write-Output 'DSH integration installed. Restart DSH and use a new conversation.'
}

if (-not $NoLaunch) { Start-Process -FilePath $petExe -WorkingDirectory (Split-Path -Parent $petExe) }
Write-Output "Nijika installed at: $targetRoot"
