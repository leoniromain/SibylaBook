from __future__ import annotations
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QToolButton, QComboBox,
    QColorDialog, QSizePolicy, QScrollArea, QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import (
    QTextCursor, QTextCharFormat, QTextBlockFormat, QTextListFormat,
    QFont, QColor, QKeySequence, QAction, QTextDocument,
)

from sibyla.core import notes as notes_svc
from sibyla.models.note import Note
from sibyla.qt.widgets.note_card import NOTE_COLORS


# ── Toolbar helpers ───────────────────────────────────────────────────────────

def _tool_btn(text: str, tooltip: str, checkable: bool = False) -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setObjectName("note_tool_btn")
    btn.setCursor(Qt.PointingHandCursor)
    return btn


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setObjectName("note_toolbar_sep")
    f.setFixedHeight(20)
    return f


# ── Color picker popup ────────────────────────────────────────────────────────

_VIVID_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#3b82f6", "#8b5cf6", "#ec4899", "#f43f5e", "#06b6d4",
    "#84cc16", "#a855f7", "#6366f1", "#0ea5e9", "#10b981",
]

_NEUTRAL_COLORS = [
    "#ffffff", "#f1f5f9", "#e2e8f0", "#cbd5e1", "#94a3b8",
    "#64748b", "#475569", "#334155", "#1e293b", "#0f172a",
    "#fef9c3", "#fde68a", "#fed7aa", "#fecaca", "#ddd6fe",
]


class _ColorPickerPopup(QFrame):
    """Two-panel color swatch popup. Emits color_chosen(str) then closes."""
    color_chosen = Signal(str)

    def __init__(self, current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("color_picker_popup")
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._current = current
        self._build()

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        # LEFT: vivid colors
        left = QWidget()
        left.setObjectName("color_picker_panel")
        lg = QGridLayout(left)
        lg.setContentsMargins(4, 4, 4, 4)
        lg.setSpacing(4)
        for i, c in enumerate(_VIVID_COLORS):
            btn = self._swatch(c)
            lg.addWidget(btn, i // 5, i % 5)

        # divider
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setObjectName("color_picker_div")

        # RIGHT: neutral/pastel colors + custom button
        right = QWidget()
        right.setObjectName("color_picker_panel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)
        rg = QGridLayout()
        rg.setSpacing(4)
        for i, c in enumerate(_NEUTRAL_COLORS):
            btn = self._swatch(c)
            rg.addWidget(btn, i // 5, i % 5)
        rl.addLayout(rg)

        custom_btn = QPushButton("Cor personalizada…")
        custom_btn.setObjectName("color_picker_custom_btn")
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.clicked.connect(self._open_custom)
        rl.addWidget(custom_btn)

        outer.addWidget(left)
        outer.addWidget(div)
        outer.addWidget(right)

    def _swatch(self, color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(22, 22)
        btn.setCursor(Qt.PointingHandCursor)
        border = "2px solid #ffffff" if color.lower() == self._current.lower() else "1px solid rgba(0,0,0,0.15)"
        btn.setStyleSheet(
            f"QPushButton {{ background:{color}; border-radius:3px; border:{border}; }}"
            f"QPushButton:hover {{ border:2px solid #ffffff; }}"
        )
        btn.setToolTip(color)
        btn.clicked.connect(lambda _, c=color: self._choose(c))
        return btn

    def _choose(self, color: str) -> None:
        self.color_chosen.emit(color)
        self.close()

    def _open_custom(self) -> None:
        self.close()
        # Small delay so popup is fully gone before dialog opens
        QTimer.singleShot(50, self._show_dialog)

    def _show_dialog(self) -> None:
        c = QColorDialog.getColor(QColor(self._current), None, "Cor personalizada")
        if c.isValid():
            self.color_chosen.emit(c.name())


# ── Color picker button ───────────────────────────────────────────────────────

class _ColorBtn(QToolButton):
    """Toolbar button that shows a custom color swatch popup.
    Emits `about_to_pick` BEFORE the popup opens so the caller can
    snapshot the text cursor (which loses focus during interaction).
    """
    about_to_pick = Signal()
    color_chosen  = Signal(str)  # hex color

    def __init__(self, icon: str, tooltip: str, default: str = "#000000") -> None:
        super().__init__()
        self.setText(icon)
        self.setToolTip(tooltip)
        self.setObjectName("note_tool_btn")
        self.setCursor(Qt.PointingHandCursor)
        self._color = default
        self._update_underline()
        self.clicked.connect(self._pick)

    def _pick(self) -> None:
        self.about_to_pick.emit()          # caller saves cursor NOW
        popup = _ColorPickerPopup(self._color)
        popup.color_chosen.connect(self._on_color_chosen)
        # Position below button
        pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.move(pos)
        popup.show()

    def _on_color_chosen(self, color: str) -> None:
        self._color = color
        self._update_underline()
        self.color_chosen.emit(self._color)

    def _update_underline(self) -> None:
        self.setStyleSheet(
            f"QToolButton {{ border-bottom: 3px solid {self._color}; }}"
        )


# ── Tag editor ────────────────────────────────────────────────────────────────

class _TagEditor(QWidget):
    tags_changed = Signal(list)

    def __init__(self, tags: list[str]) -> None:
        super().__init__()
        self._tags: list[str] = list(tags)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._input = QLineEdit()
        self._input.setObjectName("note_tag_input")
        self._input.setPlaceholderText("+ tag  (Enter)")
        self._input.setFixedWidth(130)
        self._input.returnPressed.connect(self._add_tag)
        self._rebuild()

    def _rebuild(self) -> None:
        # Remove all except input
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for tag in self._tags:
            chip = QPushButton(f"#{tag}  ✕")
            chip.setObjectName("note_tag_chip")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _, t=tag: self._remove_tag(t))
            self._layout.addWidget(chip)

        self._layout.addWidget(self._input)
        self._layout.addStretch()

    def _add_tag(self) -> None:
        tag = self._input.text().strip().lower().replace(" ", "_")
        if tag and tag not in self._tags:
            self._tags.append(tag)
            self.tags_changed.emit(self._tags)
        self._input.clear()
        self._rebuild()

    def _remove_tag(self, tag: str) -> None:
        self._tags = [t for t in self._tags if t != tag]
        self._rebuild()
        self.tags_changed.emit(self._tags)

    def set_tags(self, tags: list[str]) -> None:
        self._tags = list(tags)
        self._rebuild()

    @property
    def tags(self) -> list[str]:
        return list(self._tags)


# ── Note editor ───────────────────────────────────────────────────────────────

class NoteEditor(QWidget):
    note_saved = Signal(dict)   # emitted after each auto-save

    def __init__(self, note: dict) -> None:
        super().__init__()
        self._note = dict(note)
        self._dirty = False
        self._saved_cursor: QTextCursor | None = None   # snapshot before color dialog
        self._color_dots: list[tuple[QPushButton, str]] = []
        self._build_ui()
        self._load_note()

        # Auto-save debounce
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(900)
        self._save_timer.timeout.connect(self._auto_save)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header row (title + tags + color) ────────────────────────────────
        header = QWidget()
        header.setObjectName("note_editor_header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 12, 24, 12)
        hl.setSpacing(12)

        self._title_input = QLineEdit()
        self._title_input.setObjectName("note_title_input")
        self._title_input.setPlaceholderText("Título da nota…")
        self._title_input.textChanged.connect(self._on_title_changed)
        hl.addWidget(self._title_input, 1)

        self._tag_editor = _TagEditor([])
        self._tag_editor.tags_changed.connect(self._on_tags_changed)
        hl.addWidget(self._tag_editor)

        # Cover color picker dots — shows which is active
        color_row = QHBoxLayout()
        color_row.setSpacing(5)
        self._color_dots = []
        for color in NOTE_COLORS[:8]:
            dot = QPushButton()
            dot.setFixedSize(18, 18)
            dot.setCursor(Qt.PointingHandCursor)
            dot.setObjectName("note_color_dot")
            dot.clicked.connect(lambda _, c=color: self._set_cover_color(c))
            color_row.addWidget(dot)
            self._color_dots.append((dot, color))
        hl.addLayout(color_row)

        root.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("note_editor_sep")
        root.addWidget(sep)

        # ── Toolbar ──────────────────────────────────────────────────────────
        self._toolbar = QWidget()
        self._toolbar.setObjectName("note_toolbar")
        tl = QHBoxLayout(self._toolbar)
        tl.setContentsMargins(16, 4, 16, 4)
        tl.setSpacing(2)

        # Paragraph style
        self._para_combo = QComboBox()
        self._para_combo.setObjectName("note_para_combo")
        self._para_combo.addItems(["Normal", "H1", "H2", "H3", "Código", "Citação"])
        self._para_combo.setFixedWidth(100)
        self._para_combo.currentTextChanged.connect(self._apply_paragraph_style)
        tl.addWidget(self._para_combo)

        tl.addWidget(_sep())

        # Bold / Italic / Underline / Strikethrough
        self._bold_btn = _tool_btn("B", "Negrito (Ctrl+B)", checkable=True)
        self._bold_btn.setFont(QFont("", -1, QFont.Bold))
        self._bold_btn.clicked.connect(self._toggle_bold)
        tl.addWidget(self._bold_btn)

        self._italic_btn = _tool_btn("I", "Itálico (Ctrl+I)", checkable=True)
        self._italic_btn.setFont(QFont("", -1, -1, True))
        self._italic_btn.clicked.connect(self._toggle_italic)
        tl.addWidget(self._italic_btn)

        self._under_btn = _tool_btn("U̲", "Sublinhado (Ctrl+U)", checkable=True)
        self._under_btn.clicked.connect(self._toggle_underline)
        tl.addWidget(self._under_btn)

        self._strike_btn = _tool_btn("S̶", "Riscado", checkable=True)
        self._strike_btn.clicked.connect(self._toggle_strike)
        tl.addWidget(self._strike_btn)

        tl.addWidget(_sep())

        # Text color / highlight — save cursor BEFORE dialog steals focus
        self._fg_btn = _ColorBtn("A", "Cor do texto", "#1e293b")
        self._fg_btn.about_to_pick.connect(self._snapshot_cursor)
        self._fg_btn.color_chosen.connect(self._apply_fg_color)
        tl.addWidget(self._fg_btn)

        self._hl_btn = _ColorBtn("◼", "Realce", "#fef08a")
        self._hl_btn.about_to_pick.connect(self._snapshot_cursor)
        self._hl_btn.color_chosen.connect(self._apply_highlight)
        tl.addWidget(self._hl_btn)

        tl.addWidget(_sep())

        # Lists
        self._bullet_btn = _tool_btn("•≡", "Lista de marcadores", checkable=True)
        self._bullet_btn.clicked.connect(self._toggle_bullet_list)
        tl.addWidget(self._bullet_btn)

        self._num_btn = _tool_btn("1≡", "Lista numerada", checkable=True)
        self._num_btn.clicked.connect(self._toggle_num_list)
        tl.addWidget(self._num_btn)

        indent_in = _tool_btn("→|", "Aumentar recuo")
        indent_in.clicked.connect(self._indent_more)
        tl.addWidget(indent_in)

        indent_out = _tool_btn("|←", "Diminuir recuo")
        indent_out.clicked.connect(self._indent_less)
        tl.addWidget(indent_out)

        tl.addWidget(_sep())

        # Alignment
        for icon, tip, align in [
            ("⬅", "Alinhar à esquerda", Qt.AlignLeft),
            ("↔", "Centralizar", Qt.AlignHCenter),
            ("➡", "Alinhar à direita", Qt.AlignRight),
        ]:
            btn = _tool_btn(icon, tip)
            btn.clicked.connect(lambda _, a=align: self._set_alignment(a))
            tl.addWidget(btn)

        tl.addWidget(_sep())

        # Insert
        hr_btn = _tool_btn("―", "Inserir divisor horizontal")
        hr_btn.clicked.connect(self._insert_hr)
        tl.addWidget(hr_btn)

        tl.addStretch()

        # Undo / Redo
        undo_btn = _tool_btn("↩", "Desfazer (Ctrl+Z)")
        undo_btn.clicked.connect(lambda: self._editor.undo())
        tl.addWidget(undo_btn)

        redo_btn = _tool_btn("↪", "Refazer (Ctrl+Y)")
        redo_btn.clicked.connect(lambda: self._editor.redo())
        tl.addWidget(redo_btn)

        root.addWidget(self._toolbar)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("note_editor_sep")
        root.addWidget(sep2)

        # ── Editor body ──────────────────────────────────────────────────────
        self._editor = QTextEdit()
        self._editor.setObjectName("note_editor_body")
        self._editor.setAcceptRichText(True)
        self._editor.document().setDefaultStyleSheet("""
            h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
            h2 { font-size: 19px; font-weight: 700; margin-bottom: 4px; }
            h3 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
            p  { margin: 0; line-height: 1.6; }
            blockquote {
                border-left: 3px solid #6366f1;
                padding-left: 12px;
                color: #64748b;
                font-style: italic;
            }
            code, pre {
                font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
                background: #f1f5f9;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 13px;
            }
        """)
        self._editor.textChanged.connect(self._on_content_changed)
        self._editor.cursorPositionChanged.connect(self._update_toolbar_state)
        root.addWidget(self._editor, 1)

        # ── Status bar ───────────────────────────────────────────────────────
        status = QWidget()
        status.setObjectName("note_status_bar")
        sl = QHBoxLayout(status)
        sl.setContentsMargins(20, 4, 20, 4)
        sl.setSpacing(8)
        self._status_lbl = QLabel("Auto-salvo ativo")
        self._status_lbl.setObjectName("note_status_lbl")
        sl.addStretch()
        sl.addWidget(self._status_lbl)
        root.addWidget(status)

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        for keys, fn in [
            (QKeySequence.Bold,      self._toggle_bold),
            (QKeySequence.Italic,    self._toggle_italic),
            (QKeySequence.Underline, self._toggle_underline),
            (QKeySequence.Save,      self._force_save),
        ]:
            act = QAction(self)
            act.setShortcut(keys)
            act.triggered.connect(fn)
            self._editor.addAction(act)

    # ── Load / save ───────────────────────────────────────────────────────────

    def _load_note(self) -> None:
        self._title_input.blockSignals(True)
        self._title_input.setText(self._note.get("title", ""))
        self._title_input.blockSignals(False)

        self._tag_editor.set_tags(self._note.get("tags") or [])

        self._editor.blockSignals(True)
        content = self._note.get("content", "")
        if content.strip():
            self._editor.setHtml(content)
        else:
            self._editor.clear()
        self._editor.blockSignals(False)

        self._editor.setFocus()
        self._dirty = False
        self._refresh_color_dots()

    def _auto_save(self) -> None:
        if not self._dirty:
            return
        self._save()
        now = datetime.now().strftime("%H:%M")
        self._status_lbl.setText(f"Auto-salvo · {now}")

    def _force_save(self) -> None:
        self._save()
        now = datetime.now().strftime("%H:%M")
        self._status_lbl.setText(f"Salvo · {now}")

    def _save(self) -> None:
        note_obj = notes_svc.load_one(self._note["id"])
        if note_obj is None:
            return
        note_obj.title   = self._note.get("title", "Nova nota")
        note_obj.content = self._editor.toHtml()
        note_obj.tags    = self._tag_editor.tags
        note_obj.cover_color = self._note.get("cover_color", "#6366f1")
        notes_svc.save(note_obj)
        self._note.update(note_obj.model_dump())
        self._dirty = False
        self.note_saved.emit(self._note)

    def _schedule_save(self) -> None:
        self._dirty = True
        self._save_timer.start()

    # ── Change handlers ───────────────────────────────────────────────────────

    def _on_title_changed(self, text: str) -> None:
        self._note["title"] = text
        self._schedule_save()

    def _on_tags_changed(self, tags: list[str]) -> None:
        self._note["tags"] = tags
        self._schedule_save()

    def _on_content_changed(self) -> None:
        self._schedule_save()

    def _set_cover_color(self, color: str) -> None:
        self._note["cover_color"] = color
        self._refresh_color_dots()
        self._schedule_save()

    def _refresh_color_dots(self) -> None:
        active = self._note.get("cover_color", "#6366f1")
        for dot, color in self._color_dots:
            is_active = color == active
            border = "#ffffff" if is_active else "transparent"
            outline = "2px solid rgba(0,0,0,0.25)" if is_active else "none"
            dot.setStyleSheet(
                f"QPushButton {{"
                f"  background:{color}; border-radius:9px;"
                f"  border: 2px solid {border};"
                f"  outline: {outline};"
                f"}}"
                f"QPushButton:hover {{ border-color: #ffffff; }}"
            )

    # ── Cursor snapshot (for color dialog focus loss) ─────────────────────────

    def _snapshot_cursor(self) -> None:
        """Save cursor selection right before QColorDialog opens."""
        self._saved_cursor = QTextCursor(self._editor.textCursor())

    # ── Paragraph styles ──────────────────────────────────────────────────────

    def _apply_paragraph_style(self, style: str) -> None:
        cursor = self._editor.textCursor()
        cursor.beginEditBlock()
        fmt = QTextCharFormat()
        block_fmt = QTextBlockFormat()

        if style == "H1":
            fmt.setFontPointSize(24)
            fmt.setFontWeight(QFont.Bold)
        elif style == "H2":
            fmt.setFontPointSize(19)
            fmt.setFontWeight(QFont.Bold)
        elif style == "H3":
            fmt.setFontPointSize(15)
            fmt.setFontWeight(QFont.DemiBold)
        elif style == "Código":
            fmt.setFontFamily("SF Mono, Menlo, Consolas, monospace")
            fmt.setFontPointSize(13)
            block_fmt.setBackground(QColor("#f1f5f9"))
        elif style == "Citação":
            block_fmt.setLeftMargin(16)
            block_fmt.setTopMargin(4)
            block_fmt.setBottomMargin(4)
            fmt.setForeground(QColor("#64748b"))
            fmt.setFontItalic(True)
        else:  # Normal
            fmt.setFontPointSize(13)
            fmt.setFontWeight(QFont.Normal)
            fmt.setFontFamily("")
            fmt.setFontItalic(False)
            block_fmt.setLeftMargin(0)
            block_fmt.setBackground(QColor(Qt.transparent))

        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.mergeCharFormat(fmt)

        cursor.mergeBlockFormat(block_fmt)
        cursor.endEditBlock()

    # ── Inline formatting ─────────────────────────────────────────────────────

    def _merge_char_fmt(self, fmt: QTextCharFormat, use_snapshot: bool = False) -> None:
        """Apply fmt to selection. If use_snapshot=True, use the pre-dialog saved cursor."""
        if use_snapshot and self._saved_cursor is not None:
            cursor = QTextCursor(self._saved_cursor)
            self._saved_cursor = None
        else:
            cursor = self._editor.textCursor()

        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)

        cursor.mergeCharFormat(fmt)
        self._editor.setTextCursor(cursor)
        self._editor.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        is_bold = self._editor.fontWeight() == QFont.Bold
        fmt.setFontWeight(QFont.Normal if is_bold else QFont.Bold)
        self._merge_char_fmt(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self._editor.fontItalic())
        self._merge_char_fmt(fmt)

    def _toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self._editor.fontUnderline())
        self._merge_char_fmt(fmt)

    def _toggle_strike(self) -> None:
        cursor = self._editor.textCursor()
        fmt = cursor.charFormat()
        new_fmt = QTextCharFormat()
        new_fmt.setFontStrikeOut(not fmt.fontStrikeOut())
        self._merge_char_fmt(new_fmt)

    def _apply_fg_color(self, color: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        self._merge_char_fmt(fmt, use_snapshot=True)

    def _apply_highlight(self, color: str) -> None:
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(color))
        self._merge_char_fmt(fmt, use_snapshot=True)

    # ── Lists ─────────────────────────────────────────────────────────────────

    def _toggle_bullet_list(self) -> None:
        self._toggle_list(QTextListFormat.ListDisc)

    def _toggle_num_list(self) -> None:
        self._toggle_list(QTextListFormat.ListDecimal)

    def _toggle_list(self, style: QTextListFormat.Style) -> None:
        cursor = self._editor.textCursor()
        current_list = cursor.currentList()
        if current_list and current_list.format().style() == style:
            # Remove list
            fmt = QTextBlockFormat()
            fmt.setIndent(0)
            cursor.setBlockFormat(fmt)
        else:
            fmt = QTextListFormat()
            fmt.setStyle(style)
            fmt.setIndent(1)
            cursor.createList(fmt)

    def _indent_more(self) -> None:
        cursor = self._editor.textCursor()
        lst = cursor.currentList()
        if lst:
            fmt = lst.format()
            fmt.setIndent(fmt.indent() + 1)
            lst.setFormat(fmt)
        else:
            fmt = QTextBlockFormat()
            fmt.setIndent(cursor.blockFormat().indent() + 1)
            cursor.mergeBlockFormat(fmt)

    def _indent_less(self) -> None:
        cursor = self._editor.textCursor()
        lst = cursor.currentList()
        if lst:
            fmt = lst.format()
            fmt.setIndent(max(1, fmt.indent() - 1))
            lst.setFormat(fmt)
        else:
            fmt = QTextBlockFormat()
            fmt.setIndent(max(0, cursor.blockFormat().indent() - 1))
            cursor.mergeBlockFormat(fmt)

    # ── Alignment ────────────────────────────────────────────────────────────

    def _set_alignment(self, align: Qt.AlignmentFlag) -> None:
        self._editor.setAlignment(align)

    # ── Insert ───────────────────────────────────────────────────────────────

    def _insert_hr(self) -> None:
        cursor = self._editor.textCursor()
        cursor.insertHtml("<hr/>")

    # ── Toolbar state sync ────────────────────────────────────────────────────

    def _update_toolbar_state(self) -> None:
        self._bold_btn.setChecked(self._editor.fontWeight() == QFont.Bold)
        self._italic_btn.setChecked(self._editor.fontItalic())
        self._under_btn.setChecked(self._editor.fontUnderline())
        fmt = self._editor.textCursor().charFormat()
        self._strike_btn.setChecked(fmt.fontStrikeOut())
        cursor = self._editor.textCursor()
        in_list = cursor.currentList() is not None
        if in_list:
            style = cursor.currentList().format().style()
            self._bullet_btn.setChecked(style == QTextListFormat.ListDisc)
            self._num_btn.setChecked(style == QTextListFormat.ListDecimal)
        else:
            self._bullet_btn.setChecked(False)
            self._num_btn.setChecked(False)

    # ── Public ────────────────────────────────────────────────────────────────

    def flush_save(self) -> None:
        """Call before closing the tab to ensure latest content is persisted."""
        if self._dirty:
            self._save_timer.stop()
            self._save()
