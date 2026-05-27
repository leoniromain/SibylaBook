#!/usr/bin/env bash
# Inicia o Sibyla Translate.
# Uso: ./dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Garante que o venv existe e tem as dependências
if [ ! -f "$ROOT/.venv/bin/python" ]; then
    echo ">>> Criando venv …"
    python3.11 -m venv "$ROOT/.venv"
    "$ROOT/.venv/bin/pip" install --quiet --upgrade pip
    "$ROOT/.venv/bin/pip" install --quiet -e "$ROOT"
fi

echo ">>> Iniciando Sibyla Translate …"
"$ROOT/.venv/bin/python" "$ROOT/run.py"
