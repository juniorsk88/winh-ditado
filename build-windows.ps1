# Build do Winh Ditado para Windows (PyInstaller)
#
# Uso:  powershell -ExecutionPolicy Bypass -File build-windows.ps1
#
# Precisa de um Python 3.11/3.12 com as dependencias:
#   pip install faster-whisper sounddevice numpy pyinstaller

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller --noconfirm --clean winh.spec

$exe = Join-Path $PSScriptRoot "dist\WinhDitado.exe"
if (-not (Test-Path $exe)) { throw "build falhou: $exe nao existe" }

$size = [math]::Round((Get-Item $exe).Length / 1MB, 0)
Write-Host "OK: $exe ($size MB)"
Write-Host ""
Write-Host "Antes de distribuir, teste:"
Write-Host "  1. apague %LOCALAPPDATA%\WinhDitado"
Write-Host "  2. rode o exe e escolha o modo"
Write-Host "  3. aperte Win+H e fale"
