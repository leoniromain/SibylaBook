from __future__ import annotations
import re
from datetime import datetime

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPainterPath,
    QTextDocument, QTextOption,
)

CARD_W  = 160
CARD_H  = 220
COVER_H = 148

# Palette of accent colors users can choose from (exposed in editor)
NOTE_COLORS = [
    "#6366f1",  # indigo
    "#3b82f6",  # blue
    "#06b6d4",  # cyan
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#ef4444",  # red
    "#ec4899",  # pink
    "#8b5cf6",  # violet
    "#64748b",  # slate
    "#0f172a",  # dark
]


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d %b %Y")
    except Exception:
        return ""


def _render_cover(note: dict, w: int = CARD_W, h: int = COVER_H) -> QPixmap:
    """Render note HTML content as a miniature page on top of cover_color."""
    color = QColor(note.get("cover_color", "#6366f1"))
    bg = color.lighter(175)
    bg.setAlpha(255)

    pix = QPixmap(w, h)
    pix.fill(bg)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    # Colored top accent bar
    accent_h = 5
    painter.fillRect(0, 0, w, accent_h, color)

    # Mini-page white card
    margin = 10
    page_rect_x = margin
    page_rect_y = accent_h + 8
    page_rect_w = w - margin * 2
    page_rect_h = h - page_rect_y - margin

    # White page shadow
    shadow_color = QColor(0, 0, 0, 20)
    painter.fillRect(page_rect_x + 2, page_rect_y + 2, page_rect_w, page_rect_h, shadow_color)

    # White page
    page_path = QPainterPath()
    page_path.addRoundedRect(page_rect_x, page_rect_y, page_rect_w, page_rect_h, 3, 3)
    painter.fillPath(page_path, QColor("#ffffff"))

    # Render HTML content inside the page
    content = note.get("content", "")
    if content.strip():
        doc = QTextDocument()
        doc.setDefaultFont(QFont("SF Pro Text, Segoe UI, sans-serif", 5))
        doc.setTextWidth(page_rect_w - 8)

        opt = QTextOption()
        opt.setWrapMode(QTextOption.WordWrap)
        doc.setDefaultTextOption(opt)

        # Trim content to avoid rendering thousands of chars
        doc.setHtml(content[:2000])

        painter.save()
        painter.translate(page_rect_x + 4, page_rect_y + 4)
        # Clip to page bounds
        painter.setClipRect(0, 0, page_rect_w - 8, page_rect_h - 8)
        doc.drawContents(painter)
        painter.restore()
    else:
        # Empty note — show faint lines
        line_color = QColor(color)
        line_color.setAlpha(40)
        painter.setPen(line_color)
        for y_off in range(14, page_rect_h - 8, 10):
            lx = page_rect_x + 6
            lw = page_rect_w - 12 if y_off < 24 else page_rect_w - 30
            painter.drawLine(lx, page_rect_y + y_off, lx + lw, page_rect_y + y_off)

    painter.end()
    return pix


class NoteCard(QFrame):
    clicked       = Signal(dict)
    right_clicked = Signal(dict, object)

    def __init__(self, note: dict, parent=None) -> None:
        super().__init__(parent)
        self._note = note
        self.setFixedSize(CARD_W, CARD_H + 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("note_card")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(5)

        # Cover preview
        self._cover_lbl = QLabel()
        self._cover_lbl.setFixedSize(CARD_W, COVER_H)
        self._cover_lbl.setAlignment(Qt.AlignCenter)
        self._cover_lbl.setObjectName("note_cover")
        self._cover_lbl.setPixmap(_render_cover(self._note))
        layout.addWidget(self._cover_lbl)

        # Title
        title_lbl = QLabel()
        title_lbl.setObjectName("note_title")
        fm = title_lbl.fontMetrics()
        title_lbl.setText(
            fm.elidedText(self._note.get("title", "Sem título"), Qt.ElideRight, CARD_W - 8)
        )
        layout.addWidget(title_lbl)

        # Tags row
        tags = self._note.get("tags") or []
        if tags:
            tags_lbl = QLabel("  ".join(f"#{t}" for t in tags[:3]))
            tags_lbl.setObjectName("note_tags_preview")
            fm2 = tags_lbl.fontMetrics()
            tags_lbl.setText(
                fm2.elidedText(tags_lbl.text(), Qt.ElideRight, CARD_W - 8)
            )
            layout.addWidget(tags_lbl)

        # Date
        date_str = _fmt_date(self._note.get("updated_at", ""))
        if date_str:
            date_lbl = QLabel(date_str)
            date_lbl.setObjectName("note_date")
            layout.addWidget(date_lbl)

    def refresh(self, note: dict) -> None:
        self._note = note
        self._cover_lbl.setPixmap(_render_cover(note))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._note)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self._note, event.globalPosition().toPoint())
        super().mousePressEvent(event)
