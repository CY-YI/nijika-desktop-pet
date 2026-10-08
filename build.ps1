$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.pyinstaller-cache'
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$sprites = Join-Path $root 'assets\sprites'
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name '虹夏桌宠' --distpath 'dist' --workpath 'build' --specpath 'build' --add-data "$sprites;assets\sprites" 'pet.py'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root 'dist\虹夏桌宠.exe')
& $python -m PyInstaller --noconfirm --clean --onefile --console --name '虹夏MCP-v2' --distpath 'dist' --workpath 'build' --specpath 'build' 'mcp_server.py'
if ($LASTEXITCODE -ne 0) { throw "MCP server build failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root 'dist\虹夏MCP-v2.exe')
