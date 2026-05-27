from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPixmap, QImage, QKeyEvent

from sibyla.core import library as lib_svc


class _LoadThread(QThread):
    """Render a PDF page directly (no HTTP)."""
    page_ready = Signal(QPixmap, int, int)  # pixmap, current, total
    error = Signal(str)

    def __init__(self, book_path: str, page_num: int) -> None:
        super().__init__()
        self._book_path = book_path
        self._page_num = page_num

    def run(self) -> None:
        try:
            png_bytes, page_num, total = lib_svc.render_pdf_page(self._book_path, self._page_num)
            img = QImage.fromData(png_bytes, "PNG")
            self.page_ready.emit(QPixmap.fromImage(img), page_num, total)
        except Exception as e:
            self.error.emit(str(e))


class _EpubLoadThread(QThread):
    """Render an EPUB chapter directly (no HTTP)."""
    chapter_ready = Signal(int, int, str, str)  # chapter, total, title, text
    error = Signal(str)

    def __init__(self, book_path: str, chapter_num: int) -> None:
        super().__init__()
        self._book_path = book_path
        self._chapter_num = chapter_num

    def run(self) -> None:
        try:
            data = lib_svc.render_epub_chapter(self._book_path, self._chapter_num)
            self.chapter_ready.emit(data["chapter"], data["total"], data["title"], data["text"])
        except Exception as e:
            self.error.emit(str(e))


class ReaderView(QWidget):
    close_reader = Signal()
    detach_requested = Signal()

    def __init__(self, show_detach: bool = False) -> None:
        super().__init__()
        self._show_detach = show_detach
        self._book: dict = {}
        self._path: str = ""
        self._format: str = ""
        self._pdf_page: int = 0
        self._pdf_total: int = 0
        self._epub_chapter: int = 0
        self._epub_total: int = 0
        self._threads: list[QThread] = []
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setObjectName("reader_topbar")
        topbar.setFixedHeight(52)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(20, 0, 20, 0)
        tb_layout.setSpacing(16)

        self._close_btn = QPushButton("← Fechar")
        self._close_btn.setObjectName("reader_close_btn")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self.close_reader)
        tb_layout.addWidget(self._close_btn)

        if self._show_detach:
            self._detach_btn = QPushButton("⤢")
            self._detach_btn.setObjectName("reader_detach_btn")
            self._detach_btn.setCursor(Qt.PointingHandCursor)
            self._detach_btn.setToolTip("Abrir em janela flutuante")
            self._detach_btn.clicked.connect(self.detach_requested)
            tb_layout.addWidget(self._detach_btn)

        tb_layout.addStretch()

        self._page_info_lbl = QLabel("")
        self._page_info_lbl.setObjectName("reader_page_info")
        self._page_info_lbl.setAlignment(Qt.AlignCenter)
        tb_layout.addWidget(self._page_info_lbl)

        tb_layout.addStretch()

        self._title_lbl = QLabel("")
        self._title_lbl.setObjectName("reader_title")
        self._title_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._title_lbl.setMaximumWidth(300)
        tb_layout.addWidget(self._title_lbl)

        root.addWidget(topbar)

        # ── Content area ─────────────────────────────────────────────────────
        content_area = QWidget()
        content_area.setObjectName("reader_content_area")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # PDF view
        self._pdf_scroll = QScrollArea()
        self._pdf_scroll.setWidgetResizable(True)
        self._pdf_scroll.setFrameShape(QFrame.NoFrame)
        self._pdf_scroll.setAlignment(Qt.AlignCenter)
        self._pdf_scroll.setObjectName("reader_content_area")

        pdf_container = QWidget()
        pdf_container.setObjectName("reader_content_area")
        pdf_vbox = QVBoxLayout(pdf_container)
        pdf_vbox.setAlignment(Qt.AlignCenter)
        pdf_vbox.setContentsMargins(20, 20, 20, 20)

        self._pdf_label = QLabel()
        self._pdf_label.setAlignment(Qt.AlignCenter)
        self._pdf_label.setObjectName("reader_content_area")
        self._pdf_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pdf_vbox.addWidget(self._pdf_label)

        self._pdf_loading_lbl = QLabel("Carregando…")
        self._pdf_loading_lbl.setAlignment(Qt.AlignCenter)
        self._pdf_loading_lbl.setStyleSheet("color: #94a3b8; font-size: 14px; background: transparent;")
        self._pdf_loading_lbl.hide()
        pdf_vbox.addWidget(self._pdf_loading_lbl)

        self._pdf_scroll.setWidget(pdf_container)

        # EPUB view
        self._epub_text = QTextEdit()
        self._epub_text.setObjectName("epub_reader_text")
        self._epub_text.setReadOnly(True)
        self._epub_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Stack both in content_area, show/hide as needed
        content_layout.addWidget(self._pdf_scroll, 1)
        content_layout.addWidget(self._epub_text, 1)
        self._pdf_scroll.hide()
        self._epub_text.hide()

        root.addWidget(content_area, 1)

        # ── Bottom bar ───────────────────────────────────────────────────────
        botbar = QWidget()
        botbar.setObjectName("reader_topbar")
        botbar.setFixedHeight(56)
        bot_layout = QHBoxLayout(botbar)
        bot_layout.setContentsMargins(32, 0, 32, 0)
        bot_layout.setSpacing(16)

        self._prev_btn = QPushButton("← Anterior")
        self._prev_btn.setObjectName("reader_nav_btn")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._go_prev)
        bot_layout.addWidget(self._prev_btn)

        bot_layout.addStretch()

        self._bot_page_lbl = QLabel("")
        self._bot_page_lbl.setObjectName("reader_page_info")
        self._bot_page_lbl.setAlignment(Qt.AlignCenter)
        bot_layout.addWidget(self._bot_page_lbl)

        bot_layout.addStretch()

        self._next_btn = QPushButton("Próxima →")
        self._next_btn.setObjectName("reader_nav_btn")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._go_next)
        bot_layout.addWidget(self._next_btn)

        root.addWidget(botbar)

        self.setFocusPolicy(Qt.StrongFocus)

    # ── Public API ────────────────────────────────────────────────────────────

    def open_book(self, book: dict) -> None:
        self._book = book
        self._path = book.get("path", "")
        self._format = book.get("format", "").lower()
        title = book.get("title") or os.path.basename(self._path)

        # Elide title to fit
        fm = self._title_lbl.fontMetrics()
        self._title_lbl.setText(
            fm.elidedText(title, Qt.ElideRight, 280)
        )

        if self._format == "pdf":
            self._open_pdf()
        elif self._format == "epub":
            self._open_epub()
        else:
            # Guess from extension
            ext = os.path.splitext(self._path)[1].lower()
            if ext == ".pdf":
                self._format = "pdf"
                self._open_pdf()
            elif ext == ".epub":
                self._format = "epub"
                self._open_epub()
            else:
                self._title_lbl.setText("Formato não suportado")

    # ── PDF ───────────────────────────────────────────────────────────────────

    def _open_pdf(self) -> None:
        self._epub_text.hide()
        self._pdf_scroll.show()
        self._pdf_page = 0
        self._pdf_total = 0
        self._load_pdf_page(0)

    def _load_pdf_page(self, num: int) -> None:
        self._pdf_loading_lbl.show()
        self._pdf_label.clear()
        book_path = self._book.get("path", "")
        t = _LoadThread(book_path, num)
        t.page_ready.connect(self._on_pdf_page_ready)
        t.error.connect(self._on_pdf_error)
        self._threads.append(t)
        t.finished.connect(lambda: self._threads.remove(t) if t in self._threads else None)
        t.start()

    def _on_pdf_page_ready(self, pix: QPixmap, page: int, total: int) -> None:
        self._pdf_loading_lbl.hide()
        self._pdf_page = page
        self._pdf_total = total

        # Scale to fit available width
        available_w = max(400, self._pdf_scroll.viewport().width() - 40)
        if pix.width() > available_w:
            pix = pix.scaledToWidth(available_w, Qt.SmoothTransformation)

        self._pdf_label.setPixmap(pix)
        self._update_nav()

    def _on_pdf_error(self, msg: str) -> None:
        self._pdf_loading_lbl.hide()
        self._pdf_label.setText(f"Erro ao carregar página:\n{msg}")
        self._pdf_label.setStyleSheet("color: #dc2626; background: transparent;")

    # ── EPUB ──────────────────────────────────────────────────────────────────

    def _open_epub(self) -> None:
        self._pdf_scroll.hide()
        self._epub_text.show()
        self._epub_chapter = 0
        self._epub_total = 0
        self._epub_text.setPlainText("Carregando…")
        self._load_epub_chapter(0)

    def _load_epub_chapter(self, num: int) -> None:
        book_path = self._book.get("path", "")
        t = _EpubLoadThread(book_path, num)
        t.chapter_ready.connect(self._on_epub_chapter_ready)
        t.error.connect(self._on_epub_error)
        self._threads.append(t)
        t.finished.connect(lambda: self._threads.remove(t) if t in self._threads else None)
        t.start()

    def _on_epub_chapter_ready(self, chapter: int, total: int, title: str, text: str) -> None:
        self._epub_chapter = chapter
        self._epub_total = total
        self._epub_text.setPlainText(f"{title}\n\n{text}")
        self._epub_text.verticalScrollBar().setValue(0)
        self._update_nav()

    def _on_epub_error(self, msg: str) -> None:
        self._epub_text.setPlainText(f"Erro ao carregar capítulo:\n{msg}")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_prev(self) -> None:
        if self._format == "pdf":
            if self._pdf_page > 0:
                self._pdf_scroll.verticalScrollBar().setValue(0)
                self._load_pdf_page(self._pdf_page - 1)
        elif self._format == "epub":
            if self._epub_chapter > 0:
                self._load_epub_chapter(self._epub_chapter - 1)

    def _go_next(self) -> None:
        if self._format == "pdf":
            if self._pdf_page < self._pdf_total - 1:
                self._pdf_scroll.verticalScrollBar().setValue(0)
                self._load_pdf_page(self._pdf_page + 1)
        elif self._format == "epub":
            if self._epub_chapter < self._epub_total - 1:
                self._load_epub_chapter(self._epub_chapter + 1)

    def _update_nav(self) -> None:
        if self._format == "pdf":
            total = self._pdf_total
            cur = self._pdf_page + 1 if total > 0 else 0
            info = f"Página {cur} de {total}" if total > 0 else ""
            self._prev_btn.setEnabled(self._pdf_page > 0)
            self._next_btn.setEnabled(self._pdf_page < self._pdf_total - 1)
        elif self._format == "epub":
            total = self._epub_total
            cur = self._epub_chapter + 1 if total > 0 else 0
            info = f"Capítulo {cur} de {total}" if total > 0 else ""
            self._prev_btn.setEnabled(self._epub_chapter > 0)
            self._next_btn.setEnabled(self._epub_chapter < total - 1)
        else:
            info = ""
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)

        self._page_info_lbl.setText(info)
        self._bot_page_lbl.setText(info)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_PageUp):
            self._go_prev()
        elif key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_PageDown):
            self._go_next()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Re-scale current PDF page on resize
        if self._format == "pdf" and self._pdf_label.pixmap() and not self._pdf_label.pixmap().isNull():
            pix = self._pdf_label.pixmap()
            available_w = max(400, self._pdf_scroll.viewport().width() - 40)
            if pix.width() != available_w:
                pix = pix.scaledToWidth(available_w, Qt.SmoothTransformation)
                self._pdf_label.setPixmap(pix)
