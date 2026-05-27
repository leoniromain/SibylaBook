#!/usr/bin/env bash
# Gera SibylaTranslate.app para macOS — basta dar dois cliques para abrir.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
UI="$ROOT/ui"
DIST="$ROOT/dist"

echo "=== [1/4] Preparando venvs ==="
for dir in "$BACKEND" "$UI"; do
    if [ ! -f "$dir/.venv/bin/python" ]; then
        python3.11 -m venv "$dir/.venv"
    fi
    "$dir/.venv/bin/pip" install --quiet --upgrade pip
    "$dir/.venv/bin/pip" install --quiet -e "$dir"
done
"$UI/.venv/bin/pip" install --quiet pyinstaller

echo "=== [2/4] Construindo backend ==="
cd "$BACKEND"
.venv/bin/pip install --quiet pyinstaller
.venv/bin/pyinstaller app/main.py \
    --name sibyla-backend \
    --onefile \
    --noconfirm \
    --hidden-import=app.routers.pdf \
    --hidden-import=app.routers.translate \
    --hidden-import=app.routers.config \
    --hidden-import=app.routers.history \
    --hidden-import=app.routers.glossary \
    --collect-all langdetect \
    --collect-all pdfplumber \
    --collect-all fitz

BACKEND_BIN="$BACKEND/dist/sibyla-backend"

echo "=== [3/4] Construindo app da interface ==="
cd "$UI"
.venv/bin/pyinstaller main.py \
    --name "SibylaTranslate" \
    --onefile \
    --windowed \
    --noconfirm \
    --add-binary "$BACKEND_BIN:." \
    --collect-all sibyla_qt \
    --hidden-import=PySide6.QtSvg

echo "=== [4/4] Copiando para dist/ ==="
mkdir -p "$DIST"
cp -r "$UI/dist/SibylaTranslate.app" "$DIST/SibylaTranslate.app" 2>/dev/null || \
cp "$UI/dist/SibylaTranslate" "$DIST/SibylaTranslate"

echo ""
echo "✓ Pronto! Abra: $DIST/SibylaTranslate.app"
