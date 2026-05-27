# Gera SibylaTranslate.exe para Windows — basta dar dois cliques para abrir.
$ErrorActionPreference = "Stop"

$root       = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$uiDir      = Join-Path $root "ui"
$distDir    = Join-Path $root "dist"

Write-Host "=== [1/4] Preparando venvs ==="
foreach ($dir in @($backendDir, $uiDir)) {
    if (-not (Test-Path "$dir\.venv\Scripts\python.exe")) {
        python -m venv "$dir\.venv"
    }
    & "$dir\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip setuptools
    & "$dir\.venv\Scripts\pip.exe" install --quiet -e $dir
}
& "$uiDir\.venv\Scripts\pip.exe" install --quiet pyinstaller

Write-Host "=== [2/4] Construindo backend ==="
Set-Location $backendDir
& ".venv\Scripts\pip.exe" install --quiet pyinstaller
& ".venv\Scripts\pyinstaller.exe" app/main.py `
    --name sibyla-backend `
    --onefile `
    --noconfirm `
    --clean `
    --hidden-import=app.routers.pdf `
    --hidden-import=app.routers.translate `
    --hidden-import=app.routers.config `
    --hidden-import=app.routers.history `
    --hidden-import=app.routers.glossary `
    --collect-all langdetect `
    --collect-all pdfplumber `
    --collect-all fitz

$backendExe = Join-Path $backendDir "dist\sibyla-backend.exe"

Write-Host "=== [3/4] Construindo app da interface ==="
Set-Location $uiDir
& ".venv\Scripts\pyinstaller.exe" main.py `
    --name "SibylaTranslate" `
    --onefile `
    --windowed `
    --noconfirm `
    --add-binary "$backendExe;." `
    --collect-all sibyla_qt `
    --hidden-import=PySide6.QtSvg

Write-Host "=== [4/4] Copiando para dist/ ==="
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
Copy-Item "$uiDir\dist\SibylaTranslate.exe" "$distDir\SibylaTranslate.exe" -Force

Write-Host ""
Write-Host "Pronto! Arquivo: $distDir\SibylaTranslate.exe"
