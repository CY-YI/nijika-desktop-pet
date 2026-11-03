[CmdletBinding()]
param(
    [string]$Version = '0.1.9',
    [string]$OutputDirectory = 'dist-release\installer',
    [string]$Compiler = '',
    [switch]$BuildApplications,
    [string]$ApplicationDirectory = '',
    [string]$SupportBundle = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($Version -notmatch '^\d+\.\d+\.\d+(\.\d+)?$') {
    throw 'Version must contain three or four numeric components.'
}
if ($BuildApplications) {
    if ($ApplicationDirectory) {
        & (Join-Path $root 'build.ps1') -OutputDirectory $ApplicationDirectory
    } else {
        & (Join-Path $root 'build.ps1')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
}
if (-not $Compiler) {
    $candidates = @(
        (Join-Path $root 'build\installer-tools\InnoSetup\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
    )
    $Compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $Compiler -or -not (Test-Path -LiteralPath $Compiler -PathType Leaf)) {
    throw 'Inno Setup 6 is required. Install it or pass -Compiler <ISCC.exe path>.'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$stageName = $Version
if (Test-Path -LiteralPath (Join-Path $root ('build\installer-staging\' + $Version))) {
    $stageName += '-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
}
$stage = Join-Path $root ('build\installer-staging\' + $stageName)
if (Test-Path -LiteralPath $stage) {
    throw "Staging directory already exists; choose a new version or remove this generated directory after review: $stage"
}
$packageArguments = @((Join-Path $root 'tools\package_release.py'), '--stage', $stage)
if ($ApplicationDirectory) {
    $reviewedApplications = (Resolve-Path -LiteralPath $ApplicationDirectory).Path
    $packageArguments += @(
        '--app-exe', (Join-Path $reviewedApplications '虹夏桌宠.exe'),
        '--mcp-exe', (Join-Path $reviewedApplications '虹夏MCP-v2\虹夏MCP-v2.exe'),
        '--approval-exe', (Join-Path $reviewedApplications '虹夏审批提醒.exe')
    )
}
if ($SupportBundle) { $packageArguments += @('--support-bundle', (Resolve-Path -LiteralPath $SupportBundle).Path) }
& $python @packageArguments
if ($LASTEXITCODE -ne 0) { throw 'Installer staging failed.' }
$language = Join-Path $root 'build\installer-tools\ChineseSimplified.isl'
if (-not (Test-Path -LiteralPath $language -PathType Leaf)) {
    $language = Join-Path $root 'installer\ChineseSimplified.isl'
}
if (-not (Test-Path -LiteralPath $language -PathType Leaf)) {
    throw 'Missing the reviewed Simplified Chinese Inno Setup language file.'
}
$output = Join-Path $root $OutputDirectory
New-Item -ItemType Directory -Path $output -Force | Out-Null
& $Compiler ('/DSourceDir=' + $stage) ('/DOutputDir=' + $output) ('/DAppVersion=' + $Version) ('/DLanguageFile=' + $language) (Join-Path $root 'installer\nijika.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
$installers = @(Get-ChildItem -LiteralPath $output -Filter ('*Setup-' + $Version + '.exe') -File)
if ($installers.Count -ne 1) {
    throw "Expected exactly one Setup EXE for version $Version in $output; found $($installers.Count)."
}
$installer = $installers[0].FullName
$hash = Get-FileHash -LiteralPath $installer -Algorithm SHA256
$manifest = [ordered]@{
    file = Split-Path -Leaf $installer
    version = $Version
    bytes = (Get-Item -LiteralPath $installer).Length
    sha256 = $hash.Hash.ToLowerInvariant()
    signed = $false
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'installer-manifest.json') -Encoding UTF8
Write-Output $installer
Write-Output ('SHA256: ' + $manifest.sha256)
