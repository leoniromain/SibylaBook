from __future__ import annotations
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QMimeData
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QFont, QPen, QDrag

CARD_W  = 160
CARD_H  = 240
COVER_H = 180

_BLUE       = QColor("#2563eb")
_BLUE_ALPHA = QColor(37, 99, 235, 70)


class _SelectionOverlay(QFrame):
    """Widget transparente que cobre todo o card e desenha a seleção por cima dos filhos."""

    def __init__(self, parent: "BookCard") -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._selected = False
        self._select_mode = False
        self.setGeometry(0, 0, CARD_W, CARD_H + 20)
        self.raise_()

    def update_state(self, select_mode: bool, selected: bool) -> None:
        self._select_mode = select_mode
        self._selected = selected
        self.update()

    def paintEvent(self, _) -> None:
        if not self._select_mode:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        if self._selected:
            # overlay azul sobre a capa
            cover_path = QPainterPath()
            cover_path.addRoundedRect(0, 0, w, COVER_H, 10, 10)
            p.fillPath(cover_path, _BLUE_ALPHA)

            # borda azul grossa em volta do card inteiro
            pen = QPen(_BLUE, 4)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(2, 2, w - 4, h - 4, 10, 10)

            # badge ✓ no canto superior direito
            bx, by, br = w - 18, 18, 13
            p.setBrush(_BLUE)
            p.setPen(Qt.NoPen)
            p.drawEllipse(bx - br, by - br, br * 2, br * 2)
            p.setPen(QPen(QColor("white"), 2.5))
            p.drawLine(bx - 5, by, bx - 1, by + 4)
            p.drawLine(bx - 1, by + 4, bx + 6, by - 5)

        else:
            # círculo vazio no canto superior direito
            cx, cy, cr = w - 18, 18, 11
            p.setBrush(QColor(255, 255, 255, 200))
            p.setPen(QPen(QColor(160, 160, 160, 220), 1.5))
            p.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)

        p.end()


class BookCard(QFrame):
    clicked = Signal(dict)
    right_clicked = Signal(dict, object)
    selection_changed = Signal(dict, bool)

    def __init__(self, book: dict, parent=None) -> None:
        super().__init__(parent)
        self._book = book
        self._select_mode = False
        self._selected = False
        self.setFixedSize(CARD_W, CARD_H + 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("book_card")
        self._build_ui()
        self._overlay = _SelectionOverlay(self)

    # ── Public API ───────────────────────────────────────────────────────────

    def set_select_mode(self, enabled: bool) -> None:
        self._select_mode = enabled
        if not enabled:
            self._selected = False
        self._overlay.update_state(self._select_mode, self._selected)

    @property
    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._overlay.update_state(self._select_mode, self._selected)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)

        self._cover = QLabel()
        self._cover.setFixedSize(CARD_W, COVER_H)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setObjectName("book_cover")
        self._load_cover()
        layout.addWidget(self._cover)

        title = QLabel(self._book.get("title", "Sem título"))
        title.setObjectName("book_title")
        title.setWordWrap(False)
        title.setAlignment(Qt.AlignLeft)
        title.setMaximumWidth(CARD_W - 8)
        fm = title.fontMetrics()
        title.setText(fm.elidedText(self._book.get("title", ""), Qt.ElideRight, CARD_W - 8))
        layout.addWidget(title)

        author = QLabel(self._book.get("author", "") or "Autor desconhecido")
        author.setObjectName("book_author")
        author.setAlignment(Qt.AlignLeft)
        fm2 = author.fontMetrics()
        author.setText(fm2.elidedText(author.text(), Qt.ElideRight, CARD_W - 8))
        layout.addWidget(author)

        fmt = self._book.get("format", "").upper()
        badge = QLabel(fmt)
        badge.setObjectName(f"badge_{fmt.lower()}")
        badge.setAlignment(Qt.AlignLeft)
        layout.addWidget(badge)

        # ── Stars + read-status row ──────────────────────────────────────────
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(8, 0, 8, 0)
        meta_row.setSpacing(4)

        rating = self._book.get("rating", 0)
        if rating and 1 <= rating <= 5:
            stars_lbl = QLabel("★" * rating)
            stars_lbl.setObjectName("book_rating")
            meta_row.addWidget(stars_lbl)

        meta_row.addStretch()

        read_status = self._book.get("read_status", "unread")
        if read_status == "read":
            status_lbl = QLabel("Lido")
            status_lbl.setObjectName("status_read")
            meta_row.addWidget(status_lbl)
        elif read_status == "reading":
            status_lbl = QLabel("Lendo")
            status_lbl.setObjectName("status_reading")
            meta_row.addWidget(status_lbl)

        layout.addLayout(meta_row)

    def _load_cover(self) -> None:
        cover_path = self._book.get("cover_path", "")
        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                pix = pix.scaled(CARD_W, COVER_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = (pix.width() - CARD_W) // 2
                y = (pix.height() - COVER_H) // 2
                pix = pix.copy(x, y, CARD_W, COVER_H)
                self._cover.setPixmap(pix)
                return
        self._draw_placeholder()

    def _draw_placeholder(self) -> None:
        pix = QPixmap(CARD_W, COVER_H)
        pix.fill(QColor("#2a2a3e"))
        painter = QPainter(pix)
        painter.setPen(QColor("#4a4a6a"))
        font = QFont()
        font.setPointSize(32)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignCenter, "📖")
        painter.end()
        self._cover.setPixmap(pix)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            if self._select_mode:
                self._selected = not self._selected
                self._overlay.update_state(self._select_mode, self._selected)
                self.selection_changed.emit(self._book, self._selected)
            else:
                self.clicked.emit(self._book)
        elif event.button() == Qt.RightButton:
            if not self._select_mode:
                self.right_clicked.emit(self._book, event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.LeftButton):
            return
        if self._select_mode:
            return
        if not hasattr(self, "_drag_start_pos"):
            return
        dist = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
        if dist < QApplication.startDragDistance():
            return

        # Build drag with book id as mime data
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(
            "application/x-sibyla-book-id",
            self._book["id"].encode("utf-8"),
        )
        drag.setMimeData(mime)

        # Drag thumbnail from cover
        cover_pix = self._cover.pixmap()
        if cover_pix and not cover_pix.isNull():
            thumb = cover_pix.scaledToWidth(80, Qt.SmoothTransformation)
            drag.setPixmap(thumb)
            drag.setHotSpot(QPoint(thumb.width() // 2, thumb.height() // 2))

        drag.exec(Qt.CopyAction)
