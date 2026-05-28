"""
book_annotations.py — manages the "copy vs original" decision and annotation path
for each book. Stores a small sidecar JSON in ~/.sibyla/annot_prefs/<book_id>.json.
Annotation data lives inside the PDF itself via PyMuPDF.
"""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path

_PREFS_DIR  = Path.home() / ".sibyla" / "annot_prefs"
_COPIES_DIR = Path.home() / ".sibyla" / "annot_copies"


def _prefs_file(book_id: str) -> Path:
    _PREFS_DIR.mkdir(parents=True, exist_ok=True)
    return _PREFS_DIR / f"{book_id}.json"


def get_working_path(book_id: str) -> str | None:
    """Return the path we should annotate, or None if not set up yet."""
    p = _prefs_file(book_id)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        wp = data.get("working_path", "")
        return wp if wp and os.path.isfile(wp) else None
    except Exception:
        return None


def setup_annotation(book_id: str, original_path: str, make_copy: bool) -> str:
    """
    Configure annotation mode for a book.
    If make_copy=True, copies the PDF to ~/.sibyla/annot_copies/ (if not already done).
    Persists the preference and returns the working path.
    """
    if make_copy:
        _COPIES_DIR.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(original_path)[1]
        copy_path = str(_COPIES_DIR / f"{book_id}_annotated{ext}")
        if not os.path.isfile(copy_path):
            shutil.copy2(original_path, copy_path)
        working = copy_path
    else:
        working = original_path

    data = {
        "working_path": working,
        "original_path": original_path,
        "mode": "copy" if make_copy else "original",
    }
    _prefs_file(book_id).write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return working


def get_mode(book_id: str) -> str | None:
    """Returns 'copy', 'original', or None if not configured."""
    p = _prefs_file(book_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text()).get("mode")
    except Exception:
        return None
