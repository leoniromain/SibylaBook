# Build the Python backend as a standalone executable (Windows)
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "..\backend"
$distDir    = Join-Path $scriptDir "..\dist"

Set-Location $backendDir

Write-Host "=== Setting up venv ==="
python -m venv .venv
.\.venv\Scripts\Activate.ps1

Write-Host "=== Installing dependencies ==="
pip install --upgrade pip
pip install -e .
pip install pyinstaller

Write-Host "=== Building backend executable ==="
pyinstaller app/main.py `
  --name sibyla-backend `
  --onefile `
  --noconfirm `
  --hidden-import=app.routers.pdf `
  --hidden-import=app.routers.translate `
  --hidden-import=app.routers.config `
  --hidden-import=app.routers.history `
  --hidden-import=app.routers.glossary `
  --collect-all langdetect `
  --collect-all pdfplumber `
  --collect-all fitz

New-Item -ItemType Directory -Force -Path $distDir | Out-Null
Copy-Item "dist\sibyla-backend.exe" "$distDir\sibyla-backend.exe" -Force

Write-Host "=== Done: $distDir\sibyla-backend.exe ==="
