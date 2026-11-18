param([string]$OutputDirectory = 'dist')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.pyinstaller-cache'
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$sprites = Join-Path $root 'assets\sprites'
$controlUi = Join-Path $root 'control-ui'
$icon = Join-Path $root 'assets\icons\nijika-shortcut.ico'
$outputRoot = if ([IO.Path]::IsPathRooted($OutputDirectory)) {
    [IO.Path]::GetFullPath($OutputDirectory)
} else {
    [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
}
$components = Join-Path $root 'build\onedir-components'
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

function Copy-Component([string]$Name, [string]$RuntimeDirectory) {
    $component = Join-Path $components $Name
    $runtime = Join-Path $component $RuntimeDirectory
    $executable = Join-Path $component ($Name + '.exe')
    if (-not (Test-Path -LiteralPath $runtime -PathType Container) -or
        -not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Incomplete onedir build: $component"
    }
    $existingRuntime = Get-Item -LiteralPath (Join-Path $outputRoot $RuntimeDirectory) -Force -ErrorAction SilentlyContinue
    if ($existingRuntime -and ($existingRuntime.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Cannot copy a runtime to a reparse point: $existingRuntime"
    }
    Copy-Item -LiteralPath $runtime -Destination $outputRoot -Recurse -Force
    Copy-Item -LiteralPath $executable -Destination $outputRoot -Force
    Write-Output (Join-Path $outputRoot ($Name + '.exe'))
}

# 桌宠与设置中心共用同一个 EXE：右键菜单或 `--control-panel` 打开设置窗口。
& $python -m PyInstaller --noconfirm --clean --onedir --contents-directory '_nijika_pet_runtime' --windowed --name '虹夏桌宠' --icon $icon --distpath $components --workpath 'build' --specpath 'build' --collect-data webview --hidden-import webview --add-data "$sprites;assets\sprites" --add-data "$controlUi;control-ui" 'pet.py'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Copy-Component '虹夏桌宠' '_nijika_pet_runtime'
& $python -m PyInstaller --noconfirm --clean --onedir --console --name '虹夏MCP-v2' --distpath $outputRoot --workpath 'build' --specpath 'build' 'mcp_server.py'
if ($LASTEXITCODE -ne 0) { throw "MCP server build failed with exit code $LASTEXITCODE" }
$mcpExe = Join-Path $outputRoot '虹夏MCP-v2\虹夏MCP-v2.exe'
if (-not (Test-Path -LiteralPath $mcpExe -PathType Leaf)) {
    throw "MCP server build did not produce the expected onedir executable: $mcpExe"
}
Write-Output $mcpExe
& $python -m PyInstaller --noconfirm --clean --onedir --contents-directory '_nijika_hook_runtime' --console --name '虹夏审批提醒' --distpath $components --workpath 'build' --specpath 'build' 'approval_hook.py'
if ($LASTEXITCODE -ne 0) { throw "Approval hook build failed with exit code $LASTEXITCODE" }
Copy-Component '虹夏审批提醒' '_nijika_hook_runtime'
