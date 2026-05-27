from __future__ import annotations
import json
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from sibyla.models.book import Book


def _default_library_path() -> str:
    return str(Path.home() / "Sibyla Library")


def _meta_file(library_path: str) -> str:
    return os.path.join(library_path, ".sibyla", "metadata.json")


def _covers_dir(library_path: str) -> str:
    return os.path.join(library_path, ".sibyla", "covers")


def _ensure_dirs(library_path: str) -> None:
    os.makedirs(os.path.join(library_path, ".sibyla", "covers"), exist_ok=True)


def load_books(library_path: str) -> list[Book]:
    meta = _meta_file(library_path)
    if not os.path.isfile(meta):
        return []
    try:
        with open(meta, encoding="utf-8") as f:
            data = json.load(f)
        return [Book(**b) for b in data]
    except Exception:
        return []


def save_books(library_path: str, books: list[Book]) -> None:
    _ensure_dirs(library_path)
    meta = _meta_file(library_path)
    with open(meta, "w", encoding="utf-8") as f:
        json.dump([b.model_dump() for b in books], f, ensure_ascii=False, indent=2)


def _extract_cover_pdf(path: str, cover_out: str) -> bool:
    try:
        doc = fitz.open(path)
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(cover_out)
        doc.close()
        return True
    except Exception:
        return False


def _extract_cover_epub(path: str, cover_out: str) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            # Procura imagem de capa pelos nomes comuns
            candidates = [
                n for n in names
                if "cover" in n.lower() and n.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            if not candidates:
                # Tenta OPF para achar referência de capa
                opf = next((n for n in names if n.endswith(".opf")), None)
                if opf:
                    content = z.read(opf).decode("utf-8", errors="replace")
                    import re
                    m = re.search(r'content=["\']([^"\']*cover[^"\']*\.(?:jpg|jpeg|png))["\']',
                                  content, re.IGNORECASE)
                    if m:
                        opf_dir = os.path.dirname(opf)
                        candidates = [os.path.join(opf_dir, m.group(1)).replace("\\", "/")]
            if candidates:
                img_data = z.read(candidates[0])
                with open(cover_out, "wb") as f:
                    f.write(img_data)
                return True
    except Exception:
        pass
    return False


def _extract_metadata_epub(path: str) -> dict:
    meta = {"title": "", "author": "", "language": ""}
    try:
        import re
        with zipfile.ZipFile(path) as z:
            opf = next((n for n in z.namelist() if n.endswith(".opf")), None)
            if opf:
                content = z.read(opf).decode("utf-8", errors="replace")
                t = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", content)
                a = re.search(r"<dc:creator[^>]*>([^<]+)</dc:creator>", content)
                l = re.search(r"<dc:language[^>]*>([^<]+)</dc:language>", content)
                if t:
                    meta["title"] = t.group(1).strip()
                if a:
                    meta["author"] = a.group(1).strip()
                if l:
                    meta["language"] = l.group(1).strip()
    except Exception:
        pass
    return meta


def import_book(library_path: str, file_path: str, copy_to_library: bool = False) -> Book:
    _ensure_dirs(library_path)
    books = load_books(library_path)

    fmt = os.path.splitext(file_path)[1].lower().lstrip(".")
    book_id = str(uuid.uuid4())

    # Copia o arquivo para a biblioteca se solicitado
    if copy_to_library:
        dest_dir = os.path.join(library_path, "books")
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(file_path))
        # Evita sobrescrever arquivo existente com mesmo nome
        if os.path.exists(dest_path) and dest_path != file_path:
            base, ext = os.path.splitext(os.path.basename(file_path))
            dest_path = os.path.join(dest_dir, f"{base}_{book_id[:8]}{ext}")
        if dest_path != file_path:
            shutil.copy2(file_path, dest_path)
        file_path = dest_path

    # Evita duplicatas pelo caminho final
    existing = next((b for b in books if b.path == file_path), None)
    if existing:
        return existing

    size_mb = round(os.path.getsize(file_path) / 1_048_576, 2)

    title = os.path.splitext(os.path.basename(file_path))[0]
    author = ""
    language = ""
    pages = None

    if fmt == "epub":
        meta = _extract_metadata_epub(file_path)
        if meta["title"]:
            title = meta["title"]
        author = meta["author"]
        language = meta["language"]
    elif fmt == "pdf":
        try:
            doc = fitz.open(file_path)
            pages = len(doc)
            pdf_meta = doc.metadata
            if pdf_meta.get("title"):
                title = pdf_meta["title"]
            if pdf_meta.get("author"):
                author = pdf_meta["author"]
            doc.close()
        except Exception:
            pass

    # Extrai capa
    cover_path = ""
    cover_out = os.path.join(_covers_dir(library_path), f"{book_id}.jpg")
    if fmt == "pdf":
        if _extract_cover_pdf(file_path, cover_out):
            cover_path = cover_out
    elif fmt == "epub":
        ext = ".jpg"
        cover_out_png = cover_out.replace(".jpg", ".png")
        if _extract_cover_epub(file_path, cover_out):
            cover_path = cover_out
        elif _extract_cover_epub(file_path, cover_out_png):
            cover_path = cover_out_png

    book = Book(
        id=book_id,
        title=title,
        author=author,
        format=fmt,
        path=file_path,
        cover_path=cover_path,
        language=language,
        added_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        pages=pages,
        size_mb=size_mb,
    )

    books.insert(0, book)
    save_books(library_path, books)
    return book


def remove_book(library_path: str, book_id: str) -> bool:
    books = load_books(library_path)
    book = next((b for b in books if b.id == book_id), None)
    if not book:
        return False
    if book.cover_path and os.path.isfile(book.cover_path):
        os.remove(book.cover_path)
    books = [b for b in books if b.id != book_id]
    save_books(library_path, books)
    return True


def update_book(library_path: str, book_id: str, **fields) -> Optional[Book]:
    books = load_books(library_path)
    for i, b in enumerate(books):
        if b.id == book_id:
            # Derive `translated` from `translation_status` when provided
            if "translation_status" in fields and fields["translation_status"] is not None:
                fields["translated"] = fields["translation_status"] == "done"
            updated = b.model_copy(update={k: v for k, v in fields.items() if v is not None})
            books[i] = updated
            save_books(library_path, books)
            return updated
    return None


# ── Render helpers (chamados diretamente pela UI, sem HTTP) ────────────────────

def render_pdf_page(book_path: str, page_num: int) -> tuple[bytes, int, int]:
    """Returns (png_bytes, actual_page_num, total_pages)."""
    import fitz
    doc = fitz.open(book_path)
    total = len(doc)
    page_num = max(0, min(page_num, total - 1))
    mat = fitz.Matrix(1.8, 1.8)
    pix = doc[page_num].get_pixmap(matrix=mat)
    png = pix.tobytes("png")
    doc.close()
    return png, page_num, total


def render_epub_chapter(book_path: str, chapter_num: int) -> dict:
    """Returns {chapter, total, title, text}."""
    import re
    import ebooklib
    from ebooklib import epub as _epub
    ebook = _epub.read_epub(book_path, options={"ignore_ncx": True})
    docs = [item for item in ebook.get_items_of_type(ebooklib.ITEM_DOCUMENT)
            if item.get_content() and item.get_content().strip()]
    total = len(docs)
    chapter_num = max(0, min(chapter_num, total - 1))
    item = docs[chapter_num]
    raw = item.get_content().decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r" {2,}", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    h = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw, re.IGNORECASE | re.DOTALL)
    title = re.sub(r"<[^>]+>", "", h.group(1)).strip() if h else f"Capítulo {chapter_num + 1}"
    return {"chapter": chapter_num, "total": total, "title": title, "text": text}
