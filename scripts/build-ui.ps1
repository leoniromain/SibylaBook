# Build the PySide6 desktop UI as a standalone executable (Windows)
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uiDir     = Join-Path $scriptDir "..\ui"
$distDir   = Join-Path $scriptDir "..\dist"

Set-Location $uiDir

Write-Host "=== Setting up venv ==="
python -m venv .venv
.\.venv\Scripts\Activate.ps1

Write-Host "=== Installing dependencies ==="
pip install --upgrade pip
pip install -e .
pip install pyinstaller

Write-Host "=== Building UI executable ==="
pyinstaller main.py `
  --name "Sibyla Translate" `
  --onedir `
  --noconfirm `
  --windowed `
  --collect-all sibyla_qt `
  --collect-all PySide6

New-Item -ItemType Directory -Force -Path $distDir | Out-Null
Copy-Item "dist\Sibyla Translate" "$distDir\Sibyla Translate" -Recurse -Force

Write-Host "=== Done: $distDir\Sibyla Translate ==="
