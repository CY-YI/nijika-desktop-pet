$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.pyinstaller-cache'
$sprites = Join-Path $root 'assets\sprites'
python -m PyInstaller --noconfirm --clean --onefile --windowed --name '虹夏桌宠' --distpath 'dist' --workpath 'build' --specpath 'build' --add-data "$sprites;assets\sprites" 'pet.py'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Output (Join-Path $root 'dist\虹夏桌宠.exe')
