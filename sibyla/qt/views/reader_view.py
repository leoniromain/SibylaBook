from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QSizePolicy, QLineEdit,
    QApplication, QRubberBand, QInputDialog, QMessageBox,
    QToolButton,
)
from PySide6.QtCore import Qt, Signal, QThread, QRect, QSize, QPoint
from PySide6.QtGui import QPixmap, QImage, QKeyEvent, QPainter, QColor

from sibyla.core import library as lib_svc

# zoom factor used when rendering PDF pages
_RENDER_SCALE = 1.8

# Annotation highlight-colour presets shown in the toolbar
_ANNOT_COLORS = [
    ("#fef08a", "Amarelo"),
    ("#86efac", "Verde"),
    ("#93c5fd", "Azul"),
    ("#f9a8d4", "Rosa"),
    ("#fca5a5", "Vermelho"),
]


# ── PDF: render all pages in a background thread ────────────────────────────

class _PdfAllPagesThread(QThread):
    total_known = Signal(int)               # page count
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
            mat = fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE)
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


# ── PDF: re-render a single page (after annotation) ─────────────────────────

class _PdfSinglePageThread(QThread):
    page_ready = Signal(QPixmap, int)  # pixmap, page_idx

    def __init__(self, book_path: str, page_idx: int) -> None:
        super().__init__()
        self._book_path = book_path
        self._page_idx = page_idx

    def run(self) -> None:
        try:
            import fitz
            doc = fitz.open(self._book_path)
            mat = fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE)
            pix = doc[self._page_idx].get_pixmap(matrix=mat)
            png = pix.tobytes("png")
            img = QImage.fromData(png, "PNG")
            self.page_ready.emit(QPixmap.fromImage(img), self._page_idx)
            doc.close()
        except Exception:
            pass


# ── EPUB: load one chapter ───────────────────────────────────────────────────

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


# ── Page widget: renders one PDF page + handles annotation gestures ──────────

class _PageWidget(QWidget):
    """A QWidget that paints one PDF page and captures annotation mouse events."""
    highlight_rect  = Signal(int, object)  # page_idx, fitz.Rect
    note_requested  = Signal(int, object)  # page_idx, fitz.Point

    def __init__(self, page_idx: int, pixmap: QPixmap, display_scale: float) -> None:
        super().__init__()
        self._page_idx = page_idx
        self._pixmap = pixmap
        self._display_scale = display_scale   # displayed pixels per PDF point
        self._annot_active = False
        self._annot_tool = "highlight"
        self._origin: QPoint | None = None
        self._rubber_band: QRubberBand | None = None
        self.setFixedSize(pixmap.size())

    # ── public ───────────────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.setFixedSize(pixmap.size())
        self.update()

    def set_annotation_mode(self, active: bool, tool: str) -> None:
        self._annot_active = active
        self._annot_tool = tool
        if active and tool == "note":
            self.setCursor(Qt.CrossCursor)
        elif active:
            self.setCursor(Qt.IBeamCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        if not active and self._rubber_band:
            self._rubber_band.hide()

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pixmap)

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QKeyEvent) -> None:
        if not self._annot_active or event.button() != Qt.LeftButton:
            return
        self._origin = event.pos()
        if self._annot_tool in ("highlight", "underline", "strikeout"):
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._origin, QSize(0, 0)))
            self._rubber_band.show()

    def mouseMoveEvent(self, event) -> None:
        if self._rubber_band and self._origin:
            self._rubber_band.setGeometry(
                QRect(self._origin, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event) -> None:
        if not self._annot_active or event.button() != Qt.LeftButton:
            return

        if self._annot_tool == "note":
            if self._origin is not None:
                try:
                    import fitz
                    pt = event.pos()
                    s = self._display_scale
                    self.note_requested.emit(
                        self._page_idx, fitz.Point(pt.x() / s, pt.y() / s)
                    )
                except ImportError:
                    pass
            self._origin = None
            return

        if self._rubber_band and self._origin is not None:
            rect = QRect(self._origin, event.pos()).normalized()
            self._rubber_band.hide()
            self._origin = None
            if rect.width() > 5 and rect.height() > 5:
                try:
                    import fitz
                    s = self._display_scale
                    fitz_rect = fitz.Rect(
                        rect.x() / s,
                        rect.y() / s,
                        (rect.x() + rect.width()) / s,
                        (rect.y() + rect.height()) / s,
                    )
                    self.highlight_rect.emit(self._page_idx, fitz_rect)
                except ImportError:
                    pass


# ── Reader widget ────────────────────────────────────────────────────────────

class ReaderView(QWidget):
    close_reader     = Signal()
    detach_requested = Signal()

    def __init__(self, show_detach: bool = False) -> None:
        super().__init__()
        self._show_detach = show_detach
        self._book: dict = {}
        self._path: str = ""
        self._format: str = ""
        # PDF state
        self._pdf_total: int = 0
        self._page_widgets: list[_PageWidget] = []
        self._pdf_thread: _PdfAllPagesThread | None = None
        self._pdf_display_scale: float = _RENDER_SCALE
        # Annotation state
        self._annot_mode = False
        self._annot_tool = "highlight"
        self._annot_color = _ANNOT_COLORS[0][0]   # yellow
        self._annot_path: str = ""
        self._rerender_threads: list[_PdfSinglePageThread] = []
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
        tb.setSpacing(10)

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

        # ── Annotation toggle ────────────────────────────────────────────────
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setObjectName("topbar_vsep")
        sep_v.setFixedHeight(22)
        tb.addWidget(sep_v)

        self._annot_toggle = QPushButton("✏️  Anotar")
        self._annot_toggle.setObjectName("reader_annot_toggle")
        self._annot_toggle.setCheckable(True)
        self._annot_toggle.setCursor(Qt.PointingHandCursor)
        self._annot_toggle.setToolTip("Ativar modo de anotação")
        self._annot_toggle.toggled.connect(self._on_annot_toggle)
        tb.addWidget(self._annot_toggle)
        self._annot_toggle.hide()  # shown only for PDF

        # ── Annotation sub-toolbar (visible only when mode active) ────────────
        self._annot_sub = QWidget()
        self._annot_sub.setObjectName("reader_annot_sub")
        asl = QHBoxLayout(self._annot_sub)
        asl.setContentsMargins(6, 0, 6, 0)
        asl.setSpacing(3)

        self._tool_btns: dict[str, QPushButton] = {}
        for key, label, tip in [
            ("highlight",  "🖊",  "Grifar"),
            ("underline",  "_A",  "Sublinhar"),
            ("strikeout",  "S̶",   "Tachado"),
            ("note",       "💬",  "Nota em balão"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("reader_annot_tool_btn")
            btn.setProperty("active", key == self._annot_tool)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(key == self._annot_tool)
            btn.clicked.connect(lambda _, k=key: self._select_tool(k))
            asl.addWidget(btn)
            self._tool_btns[key] = btn

        sep_c = QFrame()
        sep_c.setFrameShape(QFrame.VLine)
        sep_c.setObjectName("topbar_vsep")
        sep_c.setFixedHeight(20)
        asl.addWidget(sep_c)

        # colour swatches
        self._color_btns: list[QPushButton] = []
        for color, name in _ANNOT_COLORS:
            cb = QPushButton()
            cb.setFixedSize(20, 20)
            cb.setToolTip(name)
            cb.setCursor(Qt.PointingHandCursor)
            cb.setObjectName("reader_annot_color_btn")
            cb.clicked.connect(lambda _, c=color: self._select_color(c))
            self._color_btns.append(cb)
            asl.addWidget(cb)
        self._refresh_color_swatches()

        tb.addWidget(self._annot_sub)
        self._annot_sub.hide()

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

        self._pdf_scroll = QScrollArea()
        self._pdf_scroll.setWidgetResizable(True)
        self._pdf_scroll.setFrameShape(QFrame.NoFrame)
        self._pdf_scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._pdf_scroll.setObjectName("reader_content_area")
        self._pdf_scroll.verticalScrollBar().valueChanged.connect(self._on_pdf_scroll)

        self._pdf_container = QWidget()
        self._pdf_container.setObjectName("reader_content_area")
        self._pdf_vbox = QVBoxLayout(self._pdf_container)
        self._pdf_vbox.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._pdf_vbox.setContentsMargins(24, 24, 24, 24)
        self._pdf_vbox.setSpacing(16)
        self._pdf_scroll.setWidget(self._pdf_container)

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
        self._annot_path = ""  # will be resolved in _open_pdf from saved prefs

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
        self._annot_toggle.show()

        if self._pdf_thread and self._pdf_thread.isRunning():
            self._pdf_thread.cancel()
            self._pdf_thread.quit()
            self._pdf_thread.wait(2000)

        for w in self._page_widgets:
            self._pdf_vbox.removeWidget(w)
            w.deleteLater()
        self._page_widgets.clear()
        self._pdf_total = 0
        self._page_input.setText("1")
        self._total_lbl.setText("…")

        # Resolve annotation path BEFORE rendering so we show annotations
        book_id = self._book.get("id", "")
        if book_id:
            from sibyla.core.book_annotations import get_working_path
            wp = get_working_path(book_id)
            if wp:
                self._annot_path = wp

        # Render from annotated copy when available, else from original
        render_path = self._annot_path if self._annot_path else self._path

        self._pdf_thread = _PdfAllPagesThread(render_path)
        self._pdf_thread.total_known.connect(self._on_pdf_total_known)
        self._pdf_thread.page_ready.connect(self._on_pdf_page_ready)
        self._pdf_thread.error.connect(self._on_pdf_error)
        self._pdf_thread.start()

    def _on_pdf_total_known(self, total: int) -> None:
        self._pdf_total = total
        self._total_lbl.setText(str(total))

    def _on_pdf_page_ready(self, pix: QPixmap, index: int, total: int) -> None:
        avail_w = max(500, self._pdf_scroll.viewport().width() - 48)
        original_w = pix.width()           # rendered at _RENDER_SCALE
        if original_w > avail_w:
            pix = pix.scaledToWidth(avail_w, Qt.SmoothTransformation)

        # pixels per PDF point for this rendered size
        display_scale = pix.width() * _RENDER_SCALE / original_w

        if index == 0:
            self._pdf_display_scale = display_scale
            self._page_input.setText("1")

        widget = _PageWidget(index, pix, display_scale)
        widget.highlight_rect.connect(self._on_highlight_rect)
        widget.note_requested.connect(self._on_note_requested)
        widget.set_annotation_mode(self._annot_mode, self._annot_tool)
        self._pdf_vbox.addWidget(widget)
        self._page_widgets.append(widget)

    def _on_pdf_error(self, msg: str) -> None:
        err = QLabel(f"Erro ao carregar PDF:\n{msg}")
        err.setStyleSheet("color: #dc2626; background: transparent; padding: 20px;")
        self._pdf_vbox.addWidget(err)

    def _on_pdf_scroll(self, value: int) -> None:
        if not self._page_widgets:
            return
        vp_h = self._pdf_scroll.viewport().height()
        center = value + vp_h // 2
        best, best_d = 0, float("inf")
        for i, w in enumerate(self._page_widgets):
            lbl_c = w.y() + w.height() // 2
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
        if 0 <= idx < len(self._page_widgets):
            self._pdf_scroll.ensureWidgetVisible(self._page_widgets[idx])

    # ── Annotation mode ───────────────────────────────────────────────────────

    def _on_annot_toggle(self, active: bool) -> None:
        if active and not self._ensure_annot_path():
            self._annot_toggle.blockSignals(True)
            self._annot_toggle.setChecked(False)
            self._annot_toggle.blockSignals(False)
            return
        self._annot_mode = active
        self._annot_sub.setVisible(active)
        for w in self._page_widgets:
            w.set_annotation_mode(active, self._annot_tool)

    def _ensure_annot_path(self) -> bool:
        """Ask user copy/original if not decided yet. Returns False on cancel."""
        if self._annot_path and os.path.isfile(self._annot_path):
            return True

        book_id = self._book.get("id", "")
        if not book_id:
            return False

        from sibyla.core.book_annotations import get_working_path, setup_annotation
        wp = get_working_path(book_id)
        if wp:
            self._annot_path = wp
            return True

        # First time — ask
        msg = QMessageBox(self)
        msg.setWindowTitle("Anotar este livro")
        msg.setText(
            "<b>Como você quer anotar este livro?</b><br><br>"
            "Você pode criar uma <b>cópia</b> do arquivo e anotar nela "
            "(o original fica intacto), ou anotar diretamente no <b>arquivo original</b>."
        )
        msg.setTextFormat(Qt.RichText)
        copy_btn = msg.addButton("📋  Usar cópia  (recomendado)", QMessageBox.AcceptRole)
        orig_btn = msg.addButton("✏️  Editar arquivo original", QMessageBox.DestructiveRole)
        msg.addButton("Cancelar", QMessageBox.RejectRole)
        msg.setDefaultButton(copy_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is None or (clicked is not copy_btn and clicked is not orig_btn):
            return False

        self._annot_path = setup_annotation(
            book_id, self._path, make_copy=(clicked is copy_btn)
        )
        return True

    def _select_tool(self, tool: str) -> None:
        self._annot_tool = tool
        for k, btn in self._tool_btns.items():
            btn.setChecked(k == tool)
            btn.setProperty("active", k == tool)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        for w in self._page_widgets:
            w.set_annotation_mode(self._annot_mode, tool)

    def _select_color(self, color: str) -> None:
        self._annot_color = color
        self._refresh_color_swatches()

    def _refresh_color_swatches(self) -> None:
        for i, (color, _) in enumerate(_ANNOT_COLORS):
            btn = self._color_btns[i]
            is_active = color == self._annot_color
            border = "2px solid #ffffff" if is_active else "1px solid rgba(0,0,0,0.2)"
            outline = "2px solid #6366f1" if is_active else "none"
            btn.setStyleSheet(
                f"QPushButton {{ background:{color}; border-radius:10px; border:{border}; }}"
                f"QPushButton:hover {{ border:2px solid #ffffff; }}"
            )

    # ── Applying annotations ─────────────────────────────────────────────────

    def _on_highlight_rect(self, page_idx: int, fitz_rect) -> None:
        self._apply_annot(page_idx, self._annot_tool, fitz_rect)

    def _on_note_requested(self, page_idx: int, fitz_pt) -> None:
        text, ok = QInputDialog.getMultiLineText(
            self, "Nova anotação",
            "Digite o texto da anotação:",
            ""
        )
        if ok and text.strip():
            try:
                import fitz
                # treat click point as a small rect for consistency
                rect = fitz.Rect(
                    fitz_pt.x, fitz_pt.y,
                    fitz_pt.x + 20, fitz_pt.y + 20
                )
                self._apply_annot(page_idx, "note", rect, note_text=text.strip())
            except ImportError:
                pass

    def _apply_annot(
        self,
        page_idx: int,
        tool: str,
        fitz_rect,
        note_text: str = "",
    ) -> None:
        if not self._annot_path:
            return
        try:
            import fitz
            doc = fitz.open(self._annot_path)
            page = doc[page_idx]
            c = QColor(self._annot_color)
            rgb = [c.redF(), c.greenF(), c.blueF()]

            if tool == "highlight":
                annot = page.add_highlight_annot(fitz_rect)
                annot.set_colors(stroke=rgb)
                annot.update()
            elif tool == "underline":
                annot = page.add_underline_annot(fitz_rect)
                annot.set_colors(stroke=rgb)
                annot.update()
            elif tool == "strikeout":
                annot = page.add_strikeout_annot(fitz_rect)
                annot.set_colors(stroke=rgb)
                annot.update()
            elif tool == "note":
                annot = page.add_text_annot(
                    fitz.Point(fitz_rect.x0, fitz_rect.y0),
                    note_text,
                )
                annot.set_colors(stroke=rgb)
                annot.update()

            doc.save(self._annot_path, incremental=True,
                     encryption=fitz.PDF_ENCRYPT_KEEP)
            doc.close()
        except Exception as e:
            print(f"[ReaderView] annotation error: {e}")
            return

        self._rerender_page(page_idx)

    def _rerender_page(self, page_idx: int) -> None:
        t = _PdfSinglePageThread(self._annot_path, page_idx)
        t.page_ready.connect(self._on_page_rerendered)
        self._rerender_threads.append(t)
        t.finished.connect(
            lambda: self._rerender_threads.remove(t)
            if t in self._rerender_threads else None
        )
        t.start()

    def _on_page_rerendered(self, pix: QPixmap, page_idx: int) -> None:
        if page_idx >= len(self._page_widgets):
            return
        avail_w = max(500, self._pdf_scroll.viewport().width() - 48)
        if pix.width() > avail_w:
            pix = pix.scaledToWidth(avail_w, Qt.SmoothTransformation)
        self._page_widgets[page_idx].set_pixmap(pix)

    # ── EPUB ──────────────────────────────────────────────────────────────────

    def _open_epub(self) -> None:
        self._pdf_scroll.hide()
        self._page_jump.hide()
        self._annot_toggle.hide()
        self._annot_sub.hide()
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
        t.finished.connect(
            lambda: self._threads.remove(t) if t in self._threads else None
        )
        t.start()

    def _on_epub_chapter_ready(
        self, chapter: int, total: int, title: str, text: str
    ) -> None:
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
