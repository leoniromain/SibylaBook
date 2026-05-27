from __future__ import annotations
import os
import urllib.parse


def normalize_path(path: str) -> str:
    path = urllib.parse.unquote(path)
    if path.startswith("file:///"):
        path = path[8:]
    elif path.startswith("file://"):
        path = path[7:]
    return os.path.normpath(path)


def get_pdf_info(path: str) -> dict:
    """Returns {pages, size_mb, detected_lang}. Raises FileNotFoundError / RuntimeError."""
    import pdfplumber
    path = normalize_path(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    size_mb = round(os.path.getsize(path) / 1_048_576, 2)
    try:
        from langdetect import detect
    except ImportError:
        detect = None
    try:
        with pdfplumber.open(path) as pdf:
            pages = len(pdf.pages)
            first_text = pdf.pages[0].extract_text() or "" if pages > 0 else ""
        detected_lang = None
        if detect and first_text.strip():
            try:
                detected_lang = detect(first_text[:2000])
            except Exception:
                pass
        return {"pages": pages, "size_mb": size_mb, "detected_lang": detected_lang}
    except Exception as e:
        raise RuntimeError(str(e))
