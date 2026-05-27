from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QSizePolicy, QLineEdit,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPixmap, QImage, QKeyEvent

from sibyla.core import library as lib_svc


# ── PDF: render all pages in a single background pass ───────────────────────

class _PdfAllPagesThread(QThread):
    total_known = Signal(int)               # emitted first with page count
    page_ready  = Signal(QPixmap, int, int) # pixmap, 0-based index, total
    error       = Signal(str)

    def __init__(self, book_path: str) -> None:
        super().__init__()
        self._book_path = book_path
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            import fitz
            doc = fitz.open(self._book_path)
            total = len(doc)
            self.total_known.emit(total)
            mat = fitz.Matrix(1.8, 1.8)
            for i in range(total):
                if self._cancelled:
                    break
                pix = doc[i].get_pixmap(matrix=mat)
                png = pix.tobytes("png")
                img = QImage.fromData(png, "PNG")
                self.page_ready.emit(QPixmap.fromImage(img), i, total)
            doc.close()
        except Exception as e:
            self.error.emit(str(e))


# ── EPUB: render one chapter at a time ──────────────────────────────────────

class _EpubLoadThread(QThread):
    chapter_ready = Signal(int, int, str, str)
    error = Signal(str)

    def __init__(self, book_path: str, chapter_num: int) -> None:
        super().__init__()
        self._book_path = book_path
        self._chapter_num = chapter_num

    def run(self) -> None:
        try:
            data = lib_svc.render_epub_chapter(self._book_path, self._chapter_num)
            self.chapter_ready.emit(
                data["chapter"], data["total"], data["title"], data["text"]
            )
        except Exception as e:
            self.error.emit(str(e))


# ── Reader widget ────────────────────────────────────────────────────────────

class ReaderView(QWidget):
    close_reader    = Signal()
    detach_requested = Signal()

    def __init__(self, show_detach: bool = False) -> None:
        super().__init__()
        self._show_detach = show_detach
        self._book: dict = {}
        self._path: str = ""
        self._format: str = ""
        # PDF state
        self._pdf_total: int = 0
        self._page_labels: list[QLabel] = []
        self._pdf_thread: _PdfAllPagesThread | None = None
        # EPUB state
        self._epub_chapter: int = 0
        self._epub_total: int = 0
        self._threads: list[QThread] = []
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setObjectName("reader_topbar")
        topbar.setFixedHeight(52)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(20, 0, 20, 0)
        tb.setSpacing(14)

        self._close_btn = QPushButton("← Fechar")
        self._close_btn.setObjectName("reader_close_btn")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self.close_reader)
        tb.addWidget(self._close_btn)

        if self._show_detach:
            det_btn = QPushButton("⤢")
            det_btn.setObjectName("reader_detach_btn")
            det_btn.setCursor(Qt.PointingHandCursor)
            det_btn.setToolTip("Abrir em janela flutuante")
            det_btn.clicked.connect(self.detach_requested)
            tb.addWidget(det_btn)

        tb.addStretch()

        # PDF page-jump widget (hidden for EPUB)
        self._page_jump = QWidget()
        self._page_jump.setObjectName("reader_page_jump")
        pjl = QHBoxLayout(self._page_jump)
        pjl.setContentsMargins(0, 0, 0, 0)
        pjl.setSpacing(6)

        self._page_input = QLineEdit()
        self._page_input.setObjectName("reader_page_input")
        self._page_input.setFixedWidth(52)
        self._page_input.setAlignment(Qt.AlignCenter)
        self._page_input.setToolTip("Digite uma página e pressione Enter")
        self._page_input.returnPressed.connect(self._on_page_jump)
        pjl.addWidget(self._page_input)

        pjl.addWidget(self._sep_label("/"))

        self._total_lbl = QLabel("0")
        self._total_lbl.setObjectName("reader_page_info")
        pjl.addWidget(self._total_lbl)

        tb.addWidget(self._page_jump)
        self._page_jump.hide()

        # EPUB info (hidden for PDF)
        self._epub_info_lbl = QLabel("")
        self._epub_info_lbl.setObjectName("reader_page_info")
        self._epub_info_lbl.setAlignment(Qt.AlignCenter)
        tb.addWidget(self._epub_info_lbl)
        self._epub_info_lbl.hide()

        tb.addStretch()

        self._title_lbl = QLabel("")
        self._title_lbl.setObjectName("reader_title")
        self._title_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._title_lbl.setMaximumWidth(320)
        tb.addWidget(self._title_lbl)

        root.addWidget(topbar)

        # ── Content area ─────────────────────────────────────────────────────
        content = QWidget()
        content.setObjectName("reader_content_area")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # PDF scroll area — holds all page labels stacked vertically
        self._pdf_scroll = QScrollArea()
        self._pdf_scroll.setWidgetResizable(True)
        self._pdf_scroll.setFrameShape(QFrame.NoFrame)
        self._pdf_scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._pdf_scroll.setObjectName("reader_content_area")
        self._pdf_scroll.verticalScrollBar().valueChanged.connect(
            self._on_pdf_scroll
        )

        self._pdf_container = QWidget()
        self._pdf_container.setObjectName("reader_content_area")
        self._pdf_vbox = QVBoxLayout(self._pdf_container)
        self._pdf_vbox.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._pdf_vbox.setContentsMargins(24, 24, 24, 24)
        self._pdf_vbox.setSpacing(16)

        self._pdf_scroll.setWidget(self._pdf_container)

        # EPUB text view
        self._epub_text = QTextEdit()
        self._epub_text.setObjectName("epub_reader_text")
        self._epub_text.setReadOnly(True)

        cl.addWidget(self._pdf_scroll, 1)
        cl.addWidget(self._epub_text, 1)
        self._pdf_scroll.hide()
        self._epub_text.hide()

        root.addWidget(content, 1)

        # ── EPUB bottom bar (chapter navigation) ─────────────────────────────
        self._epub_botbar = QWidget()
        self._epub_botbar.setObjectName("reader_topbar")
        self._epub_botbar.setFixedHeight(56)
        bbl = QHBoxLayout(self._epub_botbar)
        bbl.setContentsMargins(32, 0, 32, 0)
        bbl.setSpacing(16)

        self._prev_btn = QPushButton("← Anterior")
        self._prev_btn.setObjectName("reader_nav_btn")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._go_prev)
        bbl.addWidget(self._prev_btn)

        bbl.addStretch()

        self._bot_chapter_lbl = QLabel("")
        self._bot_chapter_lbl.setObjectName("reader_page_info")
        self._bot_chapter_lbl.setAlignment(Qt.AlignCenter)
        bbl.addWidget(self._bot_chapter_lbl)

        bbl.addStretch()

        self._next_btn = QPushButton("Próxima →")
        self._next_btn.setObjectName("reader_nav_btn")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._go_next)
        bbl.addWidget(self._next_btn)

        root.addWidget(self._epub_botbar)
        self._epub_botbar.hide()

        self.setFocusPolicy(Qt.StrongFocus)

    def _sep_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("reader_page_info")
        return lbl

    # ── Public API ────────────────────────────────────────────────────────────

    def open_book(self, book: dict) -> None:
        self._book = book
        self._path = book.get("path", "")
        self._format = book.get("format", "").lower()

        if not self._format:
            ext = os.path.splitext(self._path)[1].lower()
            self._format = "pdf" if ext == ".pdf" else ("epub" if ext == ".epub" else "")

        fm = self._title_lbl.fontMetrics()
        title = book.get("title") or os.path.basename(self._path)
        self._title_lbl.setText(fm.elidedText(title, Qt.ElideRight, 300))

        if self._format == "pdf":
            self._open_pdf()
        elif self._format == "epub":
            self._open_epub()
        else:
            self._title_lbl.setText("Formato não suportado")

    # ── PDF ───────────────────────────────────────────────────────────────────

    def _open_pdf(self) -> None:
        self._epub_text.hide()
        self._epub_botbar.hide()
        self._epub_info_lbl.hide()
        self._pdf_scroll.show()
        self._page_jump.show()

        # Cancel any previous render
        if self._pdf_thread and self._pdf_thread.isRunning():
            self._pdf_thread.cancel()
            self._pdf_thread.quit()
            self._pdf_thread.wait(2000)

        # Clear previous pages
        for lbl in self._page_labels:
            self._pdf_vbox.removeWidget(lbl)
            lbl.deleteLater()
        self._page_labels.clear()
        self._pdf_total = 0
        self._page_input.setText("1")
        self._total_lbl.setText("…")

        self._pdf_thread = _PdfAllPagesThread(self._path)
        self._pdf_thread.total_known.connect(self._on_pdf_total_known)
        self._pdf_thread.page_ready.connect(self._on_pdf_page_ready)
        self._pdf_thread.error.connect(self._on_pdf_error)
        self._pdf_thread.start()

    def _on_pdf_total_known(self, total: int) -> None:
        self._pdf_total = total
        self._total_lbl.setText(str(total))

    def _on_pdf_page_ready(self, pix: QPixmap, index: int, total: int) -> None:
        # Scale to viewport width
        avail_w = max(500, self._pdf_scroll.viewport().width() - 48)
        if pix.width() > avail_w:
            pix = pix.scaledToWidth(avail_w, Qt.SmoothTransformation)

        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setPixmap(pix)
        lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lbl.setObjectName("pdf_page_label")
        self._pdf_vbox.addWidget(lbl)
        self._page_labels.append(lbl)

        if index == 0:
            self._page_input.setText("1")

    def _on_pdf_error(self, msg: str) -> None:
        err = QLabel(f"Erro ao carregar PDF:\n{msg}")
        err.setStyleSheet("color: #dc2626; background: transparent; padding: 20px;")
        self._pdf_vbox.addWidget(err)

    def _on_pdf_scroll(self, value: int) -> None:
        if not self._page_labels:
            return
        vp_h = self._pdf_scroll.viewport().height()
        center = value + vp_h // 2
        best, best_d = 0, float("inf")
        for i, lbl in enumerate(self._page_labels):
            lbl_c = lbl.y() + lbl.height() // 2
            d = abs(lbl_c - center)
            if d < best_d:
                best_d, best = d, i
        self._page_input.setText(str(best + 1))

    def _on_page_jump(self) -> None:
        try:
            target = int(self._page_input.text())
        except ValueError:
            return
        target = max(1, min(target, self._pdf_total))
        self._page_input.setText(str(target))
        idx = target - 1
        if 0 <= idx < len(self._page_labels):
            self._pdf_scroll.ensureWidgetVisible(self._page_labels[idx])

    # ── EPUB ──────────────────────────────────────────────────────────────────

    def _open_epub(self) -> None:
        self._pdf_scroll.hide()
        self._page_jump.hide()
        self._epub_text.show()
        self._epub_botbar.show()
        self._epub_info_lbl.show()
        self._epub_chapter = 0
        self._epub_total = 0
        self._epub_text.setPlainText("Carregando…")
        self._load_epub_chapter(0)

    def _load_epub_chapter(self, num: int) -> None:
        t = _EpubLoadThread(self._path, num)
        t.chapter_ready.connect(self._on_epub_chapter_ready)
        t.error.connect(lambda msg: self._epub_text.setPlainText(f"Erro:\n{msg}"))
        self._threads.append(t)
        t.finished.connect(lambda: self._threads.remove(t) if t in self._threads else None)
        t.start()

    def _on_epub_chapter_ready(self, chapter: int, total: int, title: str, text: str) -> None:
        self._epub_chapter = chapter
        self._epub_total = total
        self._epub_text.setPlainText(f"{title}\n\n{text}")
        self._epub_text.verticalScrollBar().setValue(0)
        info = f"Capítulo {chapter + 1} de {total}" if total > 0 else ""
        self._epub_info_lbl.setText(info)
        self._bot_chapter_lbl.setText(info)
        self._prev_btn.setEnabled(chapter > 0)
        self._next_btn.setEnabled(chapter < total - 1)

    def _go_prev(self) -> None:
        if self._epub_chapter > 0:
            self._load_epub_chapter(self._epub_chapter - 1)

    def _go_next(self) -> None:
        if self._epub_chapter < self._epub_total - 1:
            self._load_epub_chapter(self._epub_chapter + 1)

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._format == "epub":
            if event.key() in (Qt.Key_Left, Qt.Key_PageUp):
                self._go_prev()
            elif event.key() in (Qt.Key_Right, Qt.Key_PageDown):
                self._go_next()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
