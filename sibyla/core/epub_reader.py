from __future__ import annotations
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString, Tag

TRANSLATABLE_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "caption", "blockquote", "dt", "dd"}


def _spine_documents(book: epub.EpubBook) -> list[epub.EpubHtml]:
    spine_ids = {item_id for item_id, _ in book.spine}
    docs = [item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
            if item.id in spine_ids]
    if not docs:
        docs = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    return docs


def parse_chapter(item: epub.EpubHtml) -> BeautifulSoup:
    return BeautifulSoup(item.get_content(), "lxml")


def _collect_text_nodes(element: Tag) -> list[NavigableString]:
    nodes = []
    for child in element.descendants:
        if isinstance(child, NavigableString) and child.parent.name not in ("script", "style") and child.strip():
            nodes.append(child)
    return nodes


def extrair_blocos_capitulo(soup: BeautifulSoup) -> list[dict]:
    blocos = []
    for tag in soup.find_all(TRANSLATABLE_TAGS):
        if tag.find_parent(TRANSLATABLE_TAGS):
            continue
        text = tag.get_text(strip=True)
        if text:
            blocos.append({"tag": tag, "texto": text})
    return blocos


def chapter_count(epub_path: str) -> int:
    book = epub.read_epub(epub_path, options={"ignore_ncx": True})
    return len(_spine_documents(book))
