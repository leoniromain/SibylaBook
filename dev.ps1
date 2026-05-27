# dev.ps1 — Inicia o Sibyla Translate no Windows.
# Uso: .\dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

# Garante venv e dependências
if (-not (Test-Path $venvPy)) {
    Write-Host ">>> Criando venv ..."
    python -m venv "$root\.venv"
    & "$root\.venv\Scripts\pip.exe" install --quiet --upgrade pip
    & "$root\.venv\Scripts\pip.exe" install --quiet -e $root
}

Write-Host ">>> Iniciando Sibyla Translate ..."
& $venvPy (Join-Path $root "run.py")
