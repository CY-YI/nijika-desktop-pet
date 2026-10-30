param(
    [switch]$Apply,
    [string]$UserProfile = $env:USERPROFILE,
    [string]$CodexHome,
    [string]$NijikaDataRoot,
    [string]$SourceRoot,
    [string]$BackupDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($UserProfile)) {
    throw 'UserProfile is required.'
}
if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    $SourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
}
if ([string]::IsNullOrWhiteSpace($CodexHome)) {
    $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $UserProfile '.codex' }
}
if ([string]::IsNullOrWhiteSpace($NijikaDataRoot)) {
    $NijikaDataRoot = Join-Path $UserProfile '.nijika-desktop-pet'
}

$SourceRoot = [IO.Path]::GetFullPath($SourceRoot).TrimEnd('\')
$UserProfile = [IO.Path]::GetFullPath($UserProfile).TrimEnd('\')
$CodexHome = [IO.Path]::GetFullPath($CodexHome).TrimEnd('\')
$NijikaDataRoot = [IO.Path]::GetFullPath($NijikaDataRoot).TrimEnd('\')

$sourceSkill = Join-Path $SourceRoot 'skills\nijika-desktop-dialog\SKILL.md'
$authoritativeSkill = Join-Path $CodexHome 'skills\nijika-desktop-dialog\SKILL.md'
$legacySkillDirectory = Join-Path $UserProfile '.agents\skills\nijika-desktop-dialog'
$legacyBackup = Join-Path $CodexHome 'skills\nijika-desktop-dialog\SKILL.md.bak-nijika-20261009-195053-238'
$approvalProbe = Join-Path $NijikaDataRoot 'codex-approval-probe-20261017-f9137c62.txt'

function Get-Sha256 {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '')
    } finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
}

foreach ($required in @($sourceSkill, $authoritativeSkill)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required authoritative skill file is missing: $required"
    }
}
$sourceHash = Get-Sha256 $sourceSkill
$authoritativeHash = Get-Sha256 $authoritativeSkill
if ($sourceHash -ne $authoritativeHash) {
    throw 'The active Codex skill does not match the source skill. Refusing cleanup.'
}
if (-not $CodexHome.StartsWith($UserProfile + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'CodexHome must be inside UserProfile for this narrow cleanup tool.'
}
if (-not $NijikaDataRoot.StartsWith($UserProfile + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'NijikaDataRoot must be inside UserProfile for this narrow cleanup tool.'
}

$targets = @(
    [pscustomobject]@{
        kind = 'directory'
        path = $legacySkillDirectory
        name = 'legacy duplicate Codex skill directory'
    },
    [pscustomobject]@{
        kind = 'file'
        path = $legacyBackup
        name = 'obsolete Codex skill backup'
    },
    [pscustomobject]@{
        kind = 'file'
        path = $approvalProbe
        name = 'empty legacy approval probe'
    }
)

$existing = @($targets | Where-Object {
    if ($_.kind -eq 'directory') {
        Test-Path -LiteralPath $_.path -PathType Container
    } else {
        Test-Path -LiteralPath $_.path -PathType Leaf
    }
})

function Get-ManifestFiles {
    param(
        [string]$TargetPath,
        [string]$TargetKind
    )

    $files = if ($TargetKind -eq 'directory') {
        @(Get-ChildItem -LiteralPath $TargetPath -File -Recurse -Force)
    } else {
        @(Get-Item -LiteralPath $TargetPath -Force)
    }
    foreach ($item in $files) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to traverse or copy a reparse-point file: $($item.FullName)"
        }
        $relative = if ($TargetKind -eq 'directory') {
            $item.FullName.Substring($TargetPath.Length).TrimStart('\')
        } else {
            $item.Name
        }
        [pscustomobject]@{
            relative_path = $relative
            bytes = $item.Length
            sha256 = Get-Sha256 $item.FullName
        }
    }
}

foreach ($target in $existing) {
    $item = Get-Item -LiteralPath $target.path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing to remove a reparse point: $($target.path)"
    }
    if ($target.kind -eq 'directory') {
        Get-ChildItem -LiteralPath $target.path -Force -Recurse | ForEach-Object {
            if (($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Refusing to remove a directory containing a reparse point: $($_.FullName)"
            }
        }
    }
}

if (-not $Apply) {
    $result = [ordered]@{
        status = if ($existing.Count) { 'plan' } else { 'clean' }
        apply = $false
        authoritative_skill = $authoritativeSkill
        authoritative_sha256 = $authoritativeHash
        targets = @($existing | ForEach-Object {
            [ordered]@{ kind = $_.kind; path = $_.path; name = $_.name }
        })
    }
    Write-Output (($result | ConvertTo-Json -Depth 8))
    exit 0
}

if (-not $existing.Count) {
    $result = [ordered]@{
        status = 'clean'
        apply = $true
        authoritative_skill = $authoritativeSkill
        targets = @()
    }
    Write-Output (($result | ConvertTo-Json -Depth 8))
    exit 0
}

if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
    $BackupDirectory = Join-Path $SourceRoot (
        'backups\legacy-integration-cleanup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$BackupDirectory = [IO.Path]::GetFullPath($BackupDirectory).TrimEnd('\')
New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null

$manifestTargets = @()
$snapshots = @()
for ($index = 0; $index -lt $existing.Count; $index++) {
    $target = $existing[$index]
    $destination = Join-Path $BackupDirectory ('{0:D2}-{1}' -f ($index + 1), (Split-Path -Leaf $target.path))
    if (Test-Path -LiteralPath $destination) {
        throw "Backup destination already exists: $destination"
    }
    if ($target.kind -eq 'directory') {
        Copy-Item -LiteralPath $target.path -Destination $destination -Recurse
    } else {
        Copy-Item -LiteralPath $target.path -Destination $destination
    }
    $files = @(Get-ManifestFiles -TargetPath $target.path -TargetKind $target.kind)
    foreach ($file in $files) {
        $backupFile = if ($target.kind -eq 'directory') {
            Join-Path $destination $file.relative_path
        } else {
            $destination
        }
        if (-not (Test-Path -LiteralPath $backupFile -PathType Leaf)) {
            throw "Backup verification failed; missing file: $backupFile"
        }
        $backupHash = Get-Sha256 $backupFile
        if ($backupHash -ne $file.sha256) {
            throw "Backup verification failed; hash mismatch: $backupFile"
        }
    }
    $manifestTargets += [ordered]@{
        source = $target.path
        backup = $destination
        kind = $target.kind
        files = @($files)
    }
    $snapshots += [pscustomobject]@{
        target = $target
        files = @($files)
    }
}

$manifest = [ordered]@{
    created_at = (Get-Date).ToString('o')
    source_skill = $sourceSkill
    authoritative_skill = $authoritativeSkill
    authoritative_sha256 = $authoritativeHash
    targets = @($manifestTargets)
}
[IO.File]::WriteAllText(
    (Join-Path $BackupDirectory 'manifest.json'),
    (($manifest | ConvertTo-Json -Depth 12) + [Environment]::NewLine),
    [Text.UTF8Encoding]::new($false))

foreach ($snapshot in $snapshots) {
    $target = $snapshot.target
    if ((Get-Sha256 $authoritativeSkill) -ne $sourceHash) {
        throw 'The authoritative Codex skill changed before deletion. Stop and inspect the backup.'
    }
    if (-not (Test-Path -LiteralPath $target.path)) {
        throw "Target disappeared after backup: $($target.path)"
    }
    $current = @(Get-ManifestFiles -TargetPath $target.path -TargetKind $target.kind)
    $expected = @($snapshot.files)
    if ($current.Count -ne $expected.Count) {
        throw "Target files changed after backup: $($target.path)"
    }
    foreach ($file in $expected) {
        $now = $current | Where-Object { $_.relative_path -ceq $file.relative_path }
        if (-not $now -or $now.bytes -ne $file.bytes -or
            $now.sha256 -ne $file.sha256) {
            throw "Target content changed after backup: $($target.path)"
        }
    }
    if ($target.kind -eq 'directory') {
        Remove-Item -LiteralPath $target.path -Recurse -Force
    } else {
        Remove-Item -LiteralPath $target.path -Force
    }
}

$postHash = Get-Sha256 $authoritativeSkill
if ($postHash -ne $sourceHash) {
    throw 'The authoritative Codex skill changed during cleanup. Stop and inspect the backup.'
}
foreach ($target in $existing) {
    if (Test-Path -LiteralPath $target.path) {
        throw "Cleanup verification failed: $($target.path)"
    }
}

$result = [ordered]@{
    status = 'applied'
    apply = $true
    backup_directory = $BackupDirectory
    removed = @($existing | ForEach-Object {
        [ordered]@{ kind = $_.kind; path = $_.path; name = $_.name }
    })
    authoritative_skill = $authoritativeSkill
    authoritative_sha256 = $postHash
}
Write-Output (($result | ConvertTo-Json -Depth 8))
