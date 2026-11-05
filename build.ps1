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
# 桌宠与设置中心共用同一个 EXE：右键菜单或 `--control-panel` 打开设置窗口。
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name '虹夏桌宠' --icon $icon --distpath $OutputDirectory --workpath 'build' --specpath 'build' --collect-data webview --hidden-import webview --add-data "$sprites;assets\sprites" --add-data "$controlUi;control-ui" 'pet.py'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root "$OutputDirectory\虹夏桌宠.exe")
& $python -m PyInstaller --noconfirm --clean --onedir --console --name '虹夏MCP-v2' --distpath $OutputDirectory --workpath 'build' --specpath 'build' 'mcp_server.py'
if ($LASTEXITCODE -ne 0) { throw "MCP server build failed with exit code $LASTEXITCODE" }
$mcpExe = Join-Path $root "$OutputDirectory\虹夏MCP-v2\虹夏MCP-v2.exe"
if (-not (Test-Path -LiteralPath $mcpExe -PathType Leaf)) {
    throw "MCP server build did not produce the expected onedir executable: $mcpExe"
}
Write-Output $mcpExe
& $python -m PyInstaller --noconfirm --clean --onefile --console --name '虹夏审批提醒' --distpath $OutputDirectory --workpath 'build' --specpath 'build' 'approval_hook.py'
if ($LASTEXITCODE -ne 0) { throw "Approval hook build failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root "$OutputDirectory\虹夏审批提醒.exe")
