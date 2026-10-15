param([string]$OutputDirectory = 'dist')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.pyinstaller-cache'
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$sprites = Join-Path $root 'assets\sprites'
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name '虹夏桌宠' --distpath $OutputDirectory --workpath 'build' --specpath 'build' --add-data "$sprites;assets\sprites" 'pet.py'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root "$OutputDirectory\虹夏桌宠.exe")
& $python -m PyInstaller --noconfirm --clean --onefile --console --name '虹夏MCP-v2' --distpath $OutputDirectory --workpath 'build' --specpath 'build' 'mcp_server.py'
if ($LASTEXITCODE -ne 0) { throw "MCP server build failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root "$OutputDirectory\虹夏MCP-v2.exe")
& $python -m PyInstaller --noconfirm --clean --onefile --console --name '虹夏审批提醒' --distpath $OutputDirectory --workpath 'build' --specpath 'build' 'approval_hook.py'
if ($LASTEXITCODE -ne 0) { throw "Approval hook build failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root "$OutputDirectory\虹夏审批提醒.exe")
$controlUi = Join-Path $root 'control-ui'
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name '虹夏控制中心' --icon (Join-Path $root 'assets\icons\nijika-shortcut.ico') --distpath $OutputDirectory --workpath 'build' --specpath 'build' --collect-data webview --add-data "$controlUi;control-ui" --add-data "$sprites;assets\sprites" 'control_panel.py'
if ($LASTEXITCODE -ne 0) { throw "Control panel build failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root "$OutputDirectory\虹夏控制中心.exe")
