#!/usr/bin/env bash
# Build the Python backend as a standalone executable (macOS / Linux)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
DIST_DIR="$SCRIPT_DIR/../dist"

cd "$BACKEND_DIR"

echo "=== Setting up venv ==="
python3.11 -m venv .venv
source .venv/bin/activate

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -e .
pip install pyinstaller

echo "=== Building backend executable ==="
pyinstaller app/main.py \
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

mkdir -p "$DIST_DIR"
cp dist/sibyla-backend "$DIST_DIR/sibyla-backend"
chmod +x "$DIST_DIR/sibyla-backend"

echo "=== Done: $DIST_DIR/sibyla-backend ==="
