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

function Remove-LegacyNijika {
    param([string]$Text)
    if (-not $Text.Contains('magpie-mcp-nijika-pet')) { return $Text }
    # Only the old manager's simple block-list layout is supported.
    # Refuse complex YAML rather than expanding a deletion to sibling services.
    $lines = [regex]::Matches($Text, '[^\r\n]*(?:\r\n|\n|\r|\z)') |
        Where-Object { $_.Length -gt 0 } | ForEach-Object { $_.Value }
    foreach ($value in $lines) {
        if ($value.TrimStart().StartsWith('#')) { continue }
        if ($value -match ':\s*[|>]') { throw 'Multiline DSH block; manual review required.' }
        if ($value.TrimEnd("`r", "`n") -match ':\s*([''"])(.*)$') {
            $quote = $Matches[1]; $tail = $Matches[2]
            if ($tail -notmatch ('.*' + $quote + '\s*(?:#.*)?$')) {
                throw 'Multiline DSH string; manual review required.'
            }
        }
    }
    $remove = [Collections.Generic.HashSet[int]]::new()
    $found = 0
    for ($start = 0; $start -lt $lines.Count; $start++) {
        if ($lines[$start].TrimEnd("`r", "`n") -notmatch '^- insert:\s*(?:#.*)?$') { continue }
        $end = $start + 1
        while ($end -lt $lines.Count) {
            $line = $lines[$end].TrimEnd("`r", "`n")
            if ($line -and $line -match '^[^\s#]') { break }
            $end++
        }
        $block = ($lines[($start + 1)..($end - 1)] -join '')
        if (-not $block.Contains('magpie-mcp-nijika-pet')) { continue }
        $entries = [Collections.Generic.List[int]]::new()
        for ($i = $start + 1; $i -lt $end; $i++) {
            $line = $lines[$i].TrimEnd("`r", "`n")
            if (-not $line.Trim() -or $line.TrimStart().StartsWith('#')) { continue }
            if ($line.Contains("`t") -or -not $line.StartsWith('    ') -or
                $line -match ':\s*(?:[|>&*!]|[{[](?![}\]]\s*(?:#.*)?$))') { throw 'Unsupported legacy DSH YAML; no automatic cleanup.' }
            if ($line -match ':\s*([''"])(.*)$') {
                $quote = $Matches[1]
                $tail = $Matches[2]
                if ($tail -notmatch ('.*' + $quote + '\s*(?:#.*)?$')) {
                    throw 'Multiline legacy DSH scalar; no automatic cleanup.'
                }
            }
            if ($line.StartsWith('    - ')) { $entries.Add($i) }
            elseif ($entries.Count -eq 0) { throw 'Unsupported legacy DSH list; no automatic cleanup.' }
        }
        $kept = 0
        for ($p = 0; $p -lt $entries.Count; $p++) {
            $first = $entries[$p]
            $last = if ($p + 1 -lt $entries.Count) { $entries[$p + 1] } else { $end }
            if ($lines[$first].TrimEnd("`r", "`n") -notmatch '^    - id: [''"]?magpie-mcp-nijika-pet[''"]?\s*(?:#.*)?$') {
                $kept++; continue
            }
            $item = $lines[$first..($last - 1)] -join ''
            if ($item -notmatch '(?m)^        serverName: [''"]?nijika[-_]pet[''"]?\s*(?:#.*)?$') {
                throw 'Cannot verify legacy DSH service; no automatic cleanup.'
            }
            $found++
            for ($i = $first; $i -lt $last; $i++) { [void]$remove.Add($i) }
        }
        if ($kept -eq 0) {
            for ($i = $start; $i -lt $end; $i++) { [void]$remove.Add($i) }
        }
    }
    if ($found -eq 0) { throw 'Unsupported legacy DSH entry layout; no automatic cleanup.' }
    $output = for ($i = 0; $i -lt $lines.Count; $i++) {
        if (-not $remove.Contains($i) -or $lines[$i].TrimStart().StartsWith('#')) { $lines[$i] }
    }
    return ($output -join '')
}

function Remove-OrphanNijikaMarker {
    param([string]$Text)
    $begin = [regex]::Matches($Text, '(?m)^[ \t]*# BEGIN NIJIKA-DSH-MCP[ \t]*\r?$')
    $end = [regex]::Matches($Text, '(?m)^[ \t]*# END NIJIKA-DSH-MCP[ \t]*\r?$')
    if ($begin.Count -ne 1 -or $end.Count -ne 0 -or
        $Text -match '(?m)^\s*-?\s*id:\s*mcp-nijika-pet\s*(?:#.*)?$') {
        return $Text
    }
    $match = $begin[0]
    $length = $match.Length
    if ($Text.Substring($match.Index + $match.Length) -match '^(\r\n|\n|\r)') {
        $length += $Matches[1].Length
    }
    return $Text.Remove($match.Index, $length)
}

function Update-MarkedBlock {
    param([string]$Path, [string]$Block, [string]$Start, [string]$End)

    $current = if (Test-Path -LiteralPath $Path) {
        [IO.File]::ReadAllText($Path)
    } else {
        ''
    }
    $original = $current
    if ($Start -eq '# BEGIN NIJIKA-DSH-MCP') { $current = Remove-LegacyNijika $current }
    if ($Start -eq '# BEGIN NIJIKA-DSH-MCP') { $current = Remove-OrphanNijikaMarker $current }
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
    if ($updated -eq $original) { return }
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
          NIJIKA_AGENT_NAME: Agent
          NIJIKA_HOST_NAME: DSH
# END NIJIKA-DSH-MCP
"@

foreach ($profile in $Profiles) {
    $patch = Join-Path $DshRoot "profiles\$profile\cordis.patch.yml"
    if (-not (Test-Path -LiteralPath $patch -PathType Leaf)) { throw "DSH profile patch is missing: $patch" }
    [void](Remove-LegacyNijika ([IO.File]::ReadAllText($patch)))
}
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
    [Convert]::ToBase64String([IO.File]::ReadAllBytes($skillTarget)) -ne
    [Convert]::ToBase64String([IO.File]::ReadAllBytes($skillSource))) {
    Copy-Item -LiteralPath $skillTarget -Destination "$skillTarget.bak-nijika-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
}
Copy-Item -LiteralPath $skillSource -Destination $skillTarget -Force

$instructions = [IO.File]::ReadAllText($instructionsSource)
Update-MarkedBlock -Path (Join-Path $DshRoot 'AGENTS.md') -Block $instructions `
    -Start '# BEGIN NIJIKA-DSH-DIALOG' -End '# END NIJIKA-DSH-DIALOG'

Write-Output "Installed DSH skill: $skillTarget"
Write-Output "DSH tools: mcp__nijika_pet__request_decision / show_completion / get_reply / wait_for_reply"
