param(
    [Alias('DshRoot')]
    [string]$DsBotRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.ds-bot'),
    [string]$McpExe
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if (-not $McpExe) {
    $installedMcp = Join-Path $env:LOCALAPPDATA 'NijikaDesktopPet\app\dist\虹夏MCP-v2\虹夏MCP-v2.exe'
    $McpExe = if (Test-Path -LiteralPath $installedMcp -PathType Leaf) {
        $installedMcp
    } else {
        Join-Path $projectRoot 'dist\虹夏MCP-v2\虹夏MCP-v2.exe'
    }
}
$McpExe = (Resolve-Path -LiteralPath $McpExe).Path
$mcpDirectory = Split-Path -Parent $McpExe
if (-not (Test-Path -LiteralPath (Join-Path $mcpDirectory '_internal') -PathType Container)) {
    throw "The MCP onedir runtime is incomplete beside: $McpExe"
}
if (-not (Test-Path -LiteralPath $DsBotRoot -PathType Container)) {
    throw "DS Bot home does not exist: $DsBotRoot"
}

$profileRoot = Join-Path $DsBotRoot 'profiles\ds-bot'
$profilePackage = Join-Path $profileRoot 'package.json'
$profileLock = Join-Path $profileRoot 'pnpm-lock.yaml'
foreach ($path in @($profilePackage, $profileLock)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "DS Bot profile file is missing: $path"
    }
}

$sourceRoot = Join-Path $PSScriptRoot 'nijika-mcp'
$targetRoot = Join-Path $DsBotRoot 'integrations\nijika-dsbot-mcp'
$skillSource = Join-Path $sourceRoot 'skill\SKILL.md'
$instructionsSource = Join-Path $sourceRoot 'global-instructions.txt'
foreach ($path in @(
    (Join-Path $sourceRoot 'cordis.patch.yml'),
    (Join-Path $sourceRoot 'package.json'),
    (Join-Path $sourceRoot 'README.md'),
    $skillSource,
    $instructionsSource
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "DS Bot integration source is missing: $path"
    }
}

function Copy-FileWithBackup {
    param([string]$Source, [string]$Destination)
    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $sourceBytes = [IO.File]::ReadAllBytes($Source)
        $destinationBytes = [IO.File]::ReadAllBytes($Destination)
        if ([Convert]::ToBase64String($sourceBytes) -eq [Convert]::ToBase64String($destinationBytes)) {
            return
        }
        Copy-Item -LiteralPath $Destination -Destination (Join-Path $backupRoot ([IO.Path]::GetFileName($Destination))) -Force
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backupRoot = Join-Path $DsBotRoot "backups\nijika-dsbot-$timestamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

$package = [IO.File]::ReadAllText($profilePackage, [Text.Encoding]::UTF8) | ConvertFrom-Json
if (-not $package.dependencies) {
    throw 'DS Bot profile package.json has no dependencies block.'
}
$expectedLink = 'link:' + ($targetRoot -replace '\\', '/')
$existingLink = [string]$package.dependencies.'@cy/nijika-dsbot-mcp'
$allowedLinks = @(
    $expectedLink,
    ('link:' + ((Join-Path $sourceRoot '') -replace '\\', '/')),
    ('link:' + ((Join-Path $sourceRoot '') -replace '\\', '/').TrimEnd('/'))
)
if ($existingLink -and $existingLink -notin $allowedLinks) {
    throw "An unmanaged @cy/nijika-dsbot-mcp dependency already exists: $existingLink"
}
if (-not $package.dsh -or -not $package.dsh.profile) {
    throw 'DS Bot profile package.json has no dsh.profile block.'
}
$bundles = @($package.dsh.profile.bundles)
if ('@cy/nijika-dsbot-mcp' -notin $bundles) {
    $bundles += '@cy/nijika-dsbot-mcp'
    $package.dsh.profile | Add-Member -NotePropertyName 'bundles' `
        -NotePropertyValue @($bundles) -Force
}

New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $targetRoot 'locale') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $targetRoot 'skill') -Force | Out-Null
foreach ($name in @('package.json', 'README.md', 'global-instructions.txt')) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination (Join-Path $targetRoot $name) -Force
}
foreach ($locale in Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'locale') -File) {
    Copy-Item -LiteralPath $locale.FullName -Destination (Join-Path $targetRoot "locale\$($locale.Name)") -Force
}
Copy-Item -LiteralPath $skillSource -Destination (Join-Path $targetRoot 'skill\SKILL.md') -Force

$yaml = [IO.File]::ReadAllText((Join-Path $sourceRoot 'cordis.patch.yml'))
if (([regex]::Matches($yaml, [regex]::Escape('__NIJIKA_MCP_EXE__'))).Count -ne 1) {
    throw 'The DS Bot YAML template must contain exactly one MCP path placeholder.'
}
$yaml = $yaml.Replace('__NIJIKA_MCP_EXE__', $McpExe.Replace("'", "''"))
[IO.File]::WriteAllText((Join-Path $targetRoot 'cordis.patch.yml'), $yaml, [Text.UTF8Encoding]::new($false))

Copy-Item -LiteralPath $profilePackage -Destination (Join-Path $backupRoot 'package.json') -Force
Copy-Item -LiteralPath $profileLock -Destination (Join-Path $backupRoot 'pnpm-lock.yaml') -Force
if ($existingLink -ne $expectedLink) {
    $package.dependencies | Add-Member -NotePropertyName '@cy/nijika-dsbot-mcp' `
        -NotePropertyValue $expectedLink -Force
    $updatedPackage = $package | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($profilePackage, $updatedPackage + "`n", [Text.UTF8Encoding]::new($false))
}

$pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if (-not $pnpm) {
    throw 'pnpm.cmd is required to refresh the DS Bot profile link.'
}
& $pnpm.Source install --offline --ignore-scripts --dir $profileRoot
if ($LASTEXITCODE -ne 0) {
    throw "pnpm failed while refreshing the DS Bot profile (exit $LASTEXITCODE)."
}

$linked = Join-Path $profileRoot 'node_modules\@cy\nijika-dsbot-mcp'
if (-not (Test-Path -LiteralPath $linked)) {
    throw "DS Bot package link was not created: $linked"
}
$linkedItem = Get-Item -LiteralPath $linked -Force
$resolvedLink = if ($linkedItem.LinkTarget) {
    $linkedItem.LinkTarget
} else {
    $linkedItem.Target
}
if (-not $resolvedLink -or
    ([IO.Path]::GetFullPath([string]$resolvedLink) -ne [IO.Path]::GetFullPath($targetRoot))) {
    throw "DS Bot resolved the Nijika package from an unexpected location: $resolvedLink"
}

$skillTarget = Join-Path $DsBotRoot 'skills\nijika-dsbot-dialog\SKILL.md'
New-Item -ItemType Directory -Path (Split-Path -Parent $skillTarget) -Force | Out-Null
Copy-FileWithBackup -Source $skillSource -Destination $skillTarget

$agentsPath = Join-Path $DsBotRoot 'AGENTS.md'
$currentAgents = if (Test-Path -LiteralPath $agentsPath) {
    [IO.File]::ReadAllText($agentsPath)
} else {
    ''
}
$block = [IO.File]::ReadAllText($instructionsSource).TrimEnd()
$start = '# BEGIN NIJIKA-DSBOT-DIALOG'
$end = '# END NIJIKA-DSBOT-DIALOG'
$startCount = ([regex]::Matches($currentAgents, [regex]::Escape($start))).Count
$endCount = ([regex]::Matches($currentAgents, [regex]::Escape($end))).Count
if ($startCount -ne $endCount -or $startCount -gt 1) {
    throw "Malformed Nijika markers in $agentsPath"
}
if ($startCount -eq 1) {
    $startIndex = $currentAgents.IndexOf($start, [StringComparison]::Ordinal)
    $endIndex = $currentAgents.IndexOf($end, [StringComparison]::Ordinal)
    if ($startIndex -lt 0 -or $endIndex -lt $startIndex) {
        throw "Nijika markers are out of order in $agentsPath"
    }
    $updatedAgents = $currentAgents.Substring(0, $startIndex) + $block +
        $currentAgents.Substring($endIndex + $end.Length)
} else {
    $updatedAgents = $currentAgents.TrimEnd("`r", "`n")
    if ($updatedAgents) { $updatedAgents += "`n`n" }
    $updatedAgents += $block + "`n"
}
if ($updatedAgents -ne $currentAgents) {
    if (Test-Path -LiteralPath $agentsPath) {
        Copy-Item -LiteralPath $agentsPath -Destination (Join-Path $backupRoot 'AGENTS.md') -Force
    }
    [IO.File]::WriteAllText($agentsPath, $updatedAgents, [Text.UTF8Encoding]::new($false))
}

Write-Output "Configured DS Bot MCP: $McpExe"
Write-Output "Installed local bundle: $targetRoot"
Write-Output "Installed skill: $skillTarget"
Write-Output "Profile backup: $backupRoot"
