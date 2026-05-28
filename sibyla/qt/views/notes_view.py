from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QGridLayout, QLabel, QPushButton, QLineEdit, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from sibyla.core import notes as notes_svc
from sibyla.qt.widgets.note_card import NoteCard, NOTE_COLORS


class NotesView(QWidget):
    open_note     = Signal(dict)   # note dict → open editor tab
    notes_changed = Signal()       # after create/delete

    def __init__(self) -> None:
        super().__init__()
        self._all_notes: list[dict] = []
        self._active_tag: str = ""
        self._search_text: str = ""
        self._build_ui()
        self._load()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ───────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("notes_header")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(12)

        title = QLabel("Anotações")
        title.setObjectName("page_title")
        hl.addWidget(title)

        hl.addStretch()

        self._search = QLineEdit()
        self._search.setObjectName("search_input")
        self._search.setPlaceholderText("Buscar notas…")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._on_search)
        hl.addWidget(self._search)

        new_btn = QPushButton("+ Nova nota")
        new_btn.setObjectName("btn_primary")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._create_note)
        hl.addWidget(new_btn)

        root.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("topbar_hsep")
        root.addWidget(sep)

        # ── Tag chips bar ────────────────────────────────────────────────────
        self._chips_widget = QWidget()
        self._chips_widget.setObjectName("tag_chips_container")
        self._chips_layout = QHBoxLayout(self._chips_widget)
        self._chips_layout.setContentsMargins(20, 8, 20, 8)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch()
        self._chips_widget.setFixedHeight(46)
        root.addWidget(self._chips_widget)

        # ── Grid scroll area ─────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setObjectName("notes_scroll")

        self._grid_container = QWidget()
        self._grid_container.setObjectName("grid_container")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(24, 20, 24, 24)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._scroll.setWidget(self._grid_container)
        root.addWidget(self._scroll, 1)

        # ── Empty state ──────────────────────────────────────────────────────
        self._empty_lbl = QLabel("Nenhuma nota ainda.\nClique em '+ Nova nota' para começar.")
        self._empty_lbl.setObjectName("empty_label")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        root.addWidget(self._empty_lbl)
        self._empty_lbl.hide()

    # ── Data ─────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        self._all_notes = [n.model_dump() for n in notes_svc.load_all()]
        self._refresh_chips()
        self._render_grid()

    def reload(self) -> None:
        self._load()

    # ── Tag chips ────────────────────────────────────────────────────────────

    def _refresh_chips(self) -> None:
        # Remove all chips except the trailing stretch
        while self._chips_layout.count() > 1:
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # "Todas" chip
        all_btn = QPushButton("Todas")
        all_btn.setObjectName("tag_chip")
        all_btn.setProperty("active", self._active_tag == "")
        all_btn.setCheckable(False)
        all_btn.setCursor(Qt.PointingHandCursor)
        all_btn.clicked.connect(lambda: self._set_tag(""))
        self._chips_layout.insertWidget(0, all_btn)

        tags = sorted({t for n in self._all_notes for t in (n.get("tags") or [])})
        for i, tag in enumerate(tags):
            btn = QPushButton(f"#{tag}")
            btn.setObjectName("tag_chip")
            btn.setProperty("active", self._active_tag == tag)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, t=tag: self._set_tag(t))
            self._chips_layout.insertWidget(i + 1, btn)

        self._chips_widget.setVisible(bool(tags))

    def _set_tag(self, tag: str) -> None:
        self._active_tag = tag
        self._refresh_chips()
        self._render_grid()

    # ── Search ───────────────────────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        self._search_text = text.strip().lower()
        self._render_grid()

    # ── Grid rendering ───────────────────────────────────────────────────────

    def _filtered_notes(self) -> list[dict]:
        notes = self._all_notes
        if self._active_tag:
            notes = [n for n in notes if self._active_tag in (n.get("tags") or [])]
        if self._search_text:
            notes = [
                n for n in notes
                if self._search_text in n.get("title", "").lower()
                or self._search_text in " ".join(n.get("tags") or []).lower()
            ]
        return notes

    def _render_grid(self) -> None:
        # Clear existing cards
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notes = self._filtered_notes()

        if not notes:
            self._scroll.hide()
            self._empty_lbl.show()
            return

        self._empty_lbl.hide()
        self._scroll.show()

        cols = max(1, (self._scroll.viewport().width() - 48) // (160 + 16))
        for idx, note in enumerate(notes):
            card = NoteCard(note)
            card.clicked.connect(self.open_note)
            card.right_clicked.connect(self._on_card_right_click)
            self._grid.addWidget(card, idx // cols, idx % cols)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_grid()

    # ── Actions ──────────────────────────────────────────────────────────────

    def _create_note(self) -> None:
        import random
        color = random.choice(NOTE_COLORS)
        note = notes_svc.create(cover_color=color)
        self.open_note.emit(note.model_dump())
        self._load()
        self.notes_changed.emit()

    def _on_card_right_click(self, note: dict, pos) -> None:
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        menu = QMenu(self)
        menu.addAction("Abrir", lambda: self.open_note.emit(note))
        menu.addSeparator()
        act_del = menu.addAction("Excluir nota", lambda: self._delete_note(note))
        act_del.setData("danger")
        menu.exec(QCursor.pos())

    def _delete_note(self, note: dict) -> None:
        from PySide6.QtWidgets import QMessageBox
        res = QMessageBox.question(
            self,
            "Excluir nota",
            f"Excluir \"{note.get('title', 'nota')}\"? Essa ação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            notes_svc.delete(note["id"])
            self._load()
            self.notes_changed.emit()
