param(
    [ValidateSet('desktop', 'web')]
    [string[]]$Profiles = @('desktop', 'web'),
    [string]$DshRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.dsh')
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$mcpExe = Join-Path $projectRoot 'dist\虹夏MCP-v2.exe'
$skillSource = Join-Path $PSScriptRoot 'nijika-dsh-dialog\SKILL.md'
$instructionsSource = Join-Path $PSScriptRoot 'global-instructions.txt'
foreach ($path in @($mcpExe, $skillSource, $instructionsSource)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required file is missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $DshRoot -PathType Container)) {
    throw "DSH home does not exist: $DshRoot"
}

function Update-MarkedBlock {
    param([string]$Path, [string]$Block, [string]$Start, [string]$End)

    $current = if (Test-Path -LiteralPath $Path) {
        [IO.File]::ReadAllText($Path)
    } else {
        ''
    }
    $startIndex = $current.IndexOf($Start, [StringComparison]::Ordinal)
    $endIndex = $current.IndexOf($End, [StringComparison]::Ordinal)
    if (($startIndex -ge 0) -ne ($endIndex -ge 0)) {
        throw "Only one Nijika marker is present in $Path"
    }
    if ($startIndex -ge 0) {
        if ($endIndex -lt $startIndex) { throw "Nijika markers are out of order in $Path" }
        $afterIndex = $endIndex + $End.Length
        $updated = $current.Substring(0, $startIndex) + $Block.TrimEnd() +
            $current.Substring($afterIndex)
    } else {
        $updated = $current.TrimEnd("`r", "`n") + "`n`n" + $Block.TrimEnd() + "`n"
    }
    if ($updated -eq $current) { return }
    if (Test-Path -LiteralPath $Path) {
        $backup = "$Path.bak-nijika-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
        Copy-Item -LiteralPath $Path -Destination $backup
    }
    [IO.File]::WriteAllText($Path, $updated, [Text.UTF8Encoding]::new($false))
}

$quotedExe = $mcpExe.Replace("'", "''")
$profileBlock = @"
# BEGIN NIJIKA-DSH-MCP
- insert:
    - id: mcp-nijika-pet
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: nijika_pet
        transport: stdio
        command: '$quotedExe'
        env:
          NIJIKA_AGENT_NAME: DSH
# END NIJIKA-DSH-MCP
"@

foreach ($profile in $Profiles) {
    $patch = Join-Path $DshRoot "profiles\$profile\cordis.patch.yml"
    if (-not (Test-Path -LiteralPath $patch -PathType Leaf)) {
        throw "DSH profile patch is missing: $patch"
    }
    $existing = [IO.File]::ReadAllText($patch)
    if ($existing.Contains('id: mcp-nijika-pet') -and
        -not $existing.Contains('# BEGIN NIJIKA-DSH-MCP')) {
        throw "Existing unmanaged Nijika MCP entry in $patch"
    }
    Update-MarkedBlock -Path $patch -Block $profileBlock `
        -Start '# BEGIN NIJIKA-DSH-MCP' -End '# END NIJIKA-DSH-MCP'
    Write-Output "Configured DSH profile: $profile"
}

$skillTarget = Join-Path $DshRoot 'skills\nijika-dsh-dialog\SKILL.md'
$skillDirectory = Split-Path -Parent $skillTarget
New-Item -ItemType Directory -Path $skillDirectory -Force | Out-Null
if ((Test-Path -LiteralPath $skillTarget) -and
    (Get-FileHash -LiteralPath $skillTarget).Hash -ne
    (Get-FileHash -LiteralPath $skillSource).Hash) {
    Copy-Item -LiteralPath $skillTarget -Destination
        "$skillTarget.bak-nijika-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
}
Copy-Item -LiteralPath $skillSource -Destination $skillTarget -Force

$instructions = [IO.File]::ReadAllText($instructionsSource)
Update-MarkedBlock -Path (Join-Path $DshRoot 'AGENTS.md') -Block $instructions `
    -Start '# BEGIN NIJIKA-DSH-DIALOG' -End '# END NIJIKA-DSH-DIALOG'

Write-Output "Installed DSH skill: $skillTarget"
Write-Output "DSH tools: mcp__nijika_pet__request_decision / show_completion / get_reply / wait_for_reply"
