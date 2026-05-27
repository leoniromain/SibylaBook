#!/usr/bin/env bash
# Build the PySide6 desktop UI as a standalone app (macOS / Linux)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI_DIR="$SCRIPT_DIR/../ui"
DIST_DIR="$SCRIPT_DIR/../dist"

cd "$UI_DIR"

echo "=== Setting up venv ==="
python3.11 -m venv .venv
source .venv/bin/activate

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -e .
pip install pyinstaller

echo "=== Building UI executable ==="
pyinstaller main.py \
  --name "Sibyla Translate" \
  --onedir \
  --noconfirm \
  --windowed \
  --collect-all sibyla_qt \
  --collect-all PySide6

mkdir -p "$DIST_DIR"

if [[ "$OSTYPE" == "darwin"* ]]; then
  cp -r "dist/Sibyla Translate.app" "$DIST_DIR/"
  echo "=== Done: $DIST_DIR/Sibyla Translate.app ==="
else
  cp -r "dist/Sibyla Translate" "$DIST_DIR/"
  echo "=== Done: $DIST_DIR/Sibyla Translate ==="
fi
