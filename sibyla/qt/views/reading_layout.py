from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QFrame, QMainWindow,
    QDialog, QLineEdit, QGridLayout, QPushButton, QMenu,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QCursor, QIcon, QPixmap, QPainter, QColor, QFont, QPainterPath

from sibyla.core import library as lib_svc
from sibyla.core.config import AppConfig
from sibyla.qt.views.reader_view import ReaderView
from sibyla.qt.core import sidebar_groups as sg


# ── Color palette ─────────────────────────────────────────────────────────────

_PALETTE = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
    "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e",
    "#a78bfa", "#fb923c", "#84cc16", "#0ea5e9", "#6366f1",
]


_ICON_SIZE = 16   # single source of truth — all sidebar icons use this


def _dot_icon(color: str, size: int = _ICON_SIZE) -> QIcon:
    """Create a filled circle QIcon in the given color."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.end()
    return QIcon(pix)



# ── Color picker ──────────────────────────────────────────────────────────────

class _ColorPicker(QWidget):
    color_picked = Signal(str)

    def __init__(self, current: str = "") -> None:
        super().__init__()
        self._current = current if current in _PALETTE else _PALETTE[0]
        layout = QGridLayout(self)
        layout.setSpacing(7)
        layout.setContentsMargins(0, 0, 0, 0)
        self._btns: list[tuple[QPushButton, str]] = []
        for i, c in enumerate(_PALETTE):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            self._style(btn, c, c == self._current)
            btn.clicked.connect(lambda _, col=c: self._pick(col))
            layout.addWidget(btn, i // 5, i % 5)
            self._btns.append((btn, c))

    def _style(self, btn: QPushButton, color: str, active: bool) -> None:
        if active:
            # White ring + checkmark via text
            btn.setText("✓")
            btn.setStyleSheet(
                f"background:{color}; border-radius:14px;"
                f"border:3px solid #ffffff; color:white;"
                f"font-size:14px; font-weight:700;"
            )
        else:
            btn.setText("")
            btn.setStyleSheet(
                f"background:{color}; border-radius:14px;"
                f"border:2px solid transparent;"
            )

    def _pick(self, color: str) -> None:
        self._current = color
        for btn, c in self._btns:
            self._style(btn, c, c == color)
        self.color_picked.emit(color)

    @property
    def color(self) -> str:
        return self._current


# ── Group dialog ──────────────────────────────────────────────────────────────

class _GroupDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        group_type: str = "folder",
        existing: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self._type = existing["type"] if existing else group_type
        init_color = existing.get("color", _PALETTE[0]) if existing else _PALETTE[0]
        is_edit = existing is not None
        label = "Pasta" if self._type == "folder" else "Divisor"
        self.setWindowTitle(f"Editar {label}" if is_edit else f"Novo {label}")
        self.setModal(True)
        self.setFixedWidth(330)

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        badge_text = "Pasta" if self._type == "folder" else "Divisor"
        badge = QLabel(badge_text)
        badge.setObjectName("dialog_type_badge")
        root.addWidget(badge)

        name_lbl = QLabel("Nome:")
        name_lbl.setObjectName("dialog_field_label")
        root.addWidget(name_lbl)

        self._name_input = QLineEdit(existing.get("name", "") if existing else "")
        self._name_input.setPlaceholderText("Ex: Favoritos")
        root.addWidget(self._name_input)

        if self._type == "folder":
            hint = QLabel("Livros com essa tag aparecerão nesta pasta.")
            hint.setObjectName("dialog_hint")
            hint.setWordWrap(True)
            root.addWidget(hint)

        color_lbl = QLabel("Cor:")
        color_lbl.setObjectName("dialog_field_label")
        root.addWidget(color_lbl)

        self._picker = _ColorPicker(init_color)
        root.addWidget(self._picker)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Salvar" if is_edit else "Criar")
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self._name_input.setFocus()

    def _on_ok(self) -> None:
        if not self._name_input.text().strip():
            self._name_input.setStyleSheet("border: 1.5px solid #dc2626;")
            return
        self.accept()

    def result_data(self) -> tuple[str, str]:
        return self._name_input.text().strip(), self._picker.color


# ── Group tree widget ─────────────────────────────────────────────────────────

_ROLE_GROUP = Qt.UserRole       # stores group dict
_ROLE_TYPE  = Qt.UserRole + 1   # "folder" | "divider"

_BOOK_MIME = "application/x-sibyla-book-id"


class _GroupTree(QTreeWidget):
    """Draggable tree of user folders/dividers. Emits tag_selected on click."""
    tag_selected      = Signal(str)        # tag name or __folder_id__
    structure_changed = Signal()           # after drag-reorder
    book_tagged       = Signal(str, str)   # (book_id, tag) when book dropped on folder

    def __init__(self, books_getter) -> None:
        super().__init__()
        self._books_getter = books_getter  # callable → list[dict]
        self._active_id: str | None = None

        self.setHeaderHidden(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("lib_side_tree")
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self.setIndentation(14)
        self.setAnimated(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setColumnCount(2)
        self.header().setStretchLastSection(False)
        self.setColumnWidth(0, 168)
        self.setColumnWidth(1, 28)
        self.customContextMenuRequested.connect(self._ctx_menu)
        self.itemClicked.connect(self._on_click)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.model().rowsMoved.connect(self._on_rows_moved)

    # ── Drag-drop for book cards ───────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(_BOOK_MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(_BOOK_MIME):
            item = self.itemAt(event.position().toPoint())
            if item and item.data(0, _ROLE_TYPE) == "folder":
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(_BOOK_MIME):
            book_id = bytes(event.mimeData().data(_BOOK_MIME)).decode("utf-8")
            item = self.itemAt(event.position().toPoint())
            if item:
                g = item.data(0, _ROLE_GROUP)
                if g and g["type"] == "folder":
                    tag = g.get("tag", g["name"])
                    self.book_tagged.emit(book_id, tag)
                    event.acceptProposedAction()
                    return
            event.ignore()
        else:
            super().dropEvent(event)
            sg.save(self._dump_tree())
            self.structure_changed.emit()

    # ── Build ─────────────────────────────────────────────────────────────────

    def populate(self, groups: list[dict]) -> None:
        self.blockSignals(True)
        self.clear()
        books = self._books_getter()
        for g in groups:
            item = self._make_item(g, books)
            self.addTopLevelItem(item)
            item.setExpanded(True)
        self.blockSignals(False)

    def _make_item(self, group: dict, books: list[dict]) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        self._apply_group(item, group, books)
        for child in group.get("children", []):
            ci = self._make_item(child, books)
            item.addChild(ci)
        return item

    def _apply_group(self, item: QTreeWidgetItem, group: dict, books: list[dict]) -> None:
        item.setData(0, _ROLE_GROUP, group)
        item.setData(0, _ROLE_TYPE, group["type"])
        color = group["color"]
        count = sum(1 for b in books if group.get("tag", group["name"]) in (b.get("tags") or []))
        item.setIcon(0, _dot_icon(color))
        item.setText(1, str(count))
        item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)

        if group["type"] == "folder":
            item.setText(0, group["name"])
            f = item.font(0)
            f.setPointSize(12)
            item.setFont(0, f)
        else:
            item.setText(0, group["name"] if group.get("name") else "─────")
            f = item.font(0)
            f.setPointSize(11)
            f.setItalic(True)
            item.setFont(0, f)
            item.setForeground(0, QColor("#475569"))

        item.setFlags(
            Qt.ItemIsEnabled | Qt.ItemIsSelectable |
            Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        )

    def set_active(self, group_id: str | None) -> None:
        self._active_id = group_id
        self._refresh_highlight()

    def _refresh_highlight(self) -> None:
        def walk(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                g = item.data(0, _ROLE_GROUP)
                is_active = g and g["id"] == self._active_id
                item.setSelected(is_active)
                walk(item)
        walk(self.invisibleRootItem())

    # ── Events ────────────────────────────────────────────────────────────────

    def _on_click(self, item: QTreeWidgetItem, _col: int) -> None:
        g = item.data(0, _ROLE_GROUP)
        if not g:
            return
        self._active_id = g["id"]
        self.tag_selected.emit(g.get("tag", g["name"]))

    def _on_double_click(self, item: QTreeWidgetItem, _col: int) -> None:
        g = item.data(0, _ROLE_GROUP)
        if g:
            self._open_edit(item, g)

    def _on_rows_moved(self) -> None:
        # Only save after internal reorders (not book drops, handled in dropEvent)
        sg.save(self._dump_tree())
        self.structure_changed.emit()


    def _ctx_menu(self, pos: QPoint) -> None:
        item = self.itemAt(pos)
        if not item:
            return
        g = item.data(0, _ROLE_GROUP)
        if not g:
            return

        menu = QMenu(self)
        menu.addAction("Editar", lambda: self._open_edit(item, g))

        if g["type"] == "folder":
            menu.addSeparator()
            sub = menu.addMenu("Adicionar dentro")
            sub.addAction("Sub-pasta",   lambda: self._add_child(item, "folder"))
            sub.addAction("Sub-divisor", lambda: self._add_child(item, "divider"))

        menu.addSeparator()
        act_del = menu.addAction("Excluir", lambda: self._delete_item(item, g))
        act_del.setData("danger")

        menu.exec(QCursor.pos())

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _open_edit(self, item: QTreeWidgetItem, g: dict) -> None:
        dlg = _GroupDialog(self, existing=g)
        if dlg.exec() != QDialog.Accepted:
            return
        name, color = dlg.result_data()
        g["name"] = name
        g["color"] = color
        if g["type"] == "folder":
            g["tag"] = name
        item.setData(0, _ROLE_GROUP, g)
        self._apply_group(item, g, self._books_getter())
        sg.save(self._dump_tree())

    def _add_child(self, parent_item: QTreeWidgetItem, group_type: str) -> None:
        dlg = _GroupDialog(self, group_type=group_type)
        if dlg.exec() != QDialog.Accepted:
            return
        name, color = dlg.result_data()
        group = sg.new_folder(name, color) if group_type == "folder" else sg.new_divider(name, color)
        child = self._make_item(group, self._books_getter())
        parent_item.addChild(child)
        parent_item.setExpanded(True)
        sg.save(self._dump_tree())

    def _delete_item(self, item: QTreeWidgetItem, g: dict) -> None:
        if self._active_id == g["id"]:
            self._active_id = None
            self.tag_selected.emit("")
        parent = item.parent() or self.invisibleRootItem()
        parent.removeChild(item)
        sg.save(self._dump_tree())

    # ── Add at root level ─────────────────────────────────────────────────────

    def add_root_group(self, group_type: str) -> None:
        dlg = _GroupDialog(self, group_type=group_type)
        if dlg.exec() != QDialog.Accepted:
            return
        name, color = dlg.result_data()
        group = sg.new_folder(name, color) if group_type == "folder" else sg.new_divider(name, color)
        item = self._make_item(group, self._books_getter())
        self.addTopLevelItem(item)
        sg.save(self._dump_tree())

    # ── Tree serialization ────────────────────────────────────────────────────

    def _dump_tree(self) -> list[dict]:
        def walk(parent) -> list[dict]:
            result = []
            for i in range(parent.childCount()):
                item = parent.child(i)
                g = dict(item.data(0, _ROLE_GROUP) or {})
                if not g:
                    continue
                g["children"] = walk(item)
                result.append(g)
            return result
        return walk(self.invisibleRootItem())


# ── Fixed row (Todos / Avulsos) ───────────────────────────────────────────────

class _DotWidget(QWidget):
    """A painted circle dot, always crisp at any DPI."""
    def __init__(self, color: str, diameter: int = _ICON_SIZE) -> None:
        super().__init__()
        self._color = QColor(color)
        self._d = diameter
        self.setFixedSize(diameter, diameter)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, self._d, self._d)
        p.end()


class _FixedRow(QFrame):
    clicked = Signal()

    def __init__(self, label: str, count: int, color: str) -> None:
        super().__init__()
        self.setObjectName("tag_group_row")
        self.setCursor(Qt.PointingHandCursor)
        self._count_lbl: QLabel
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        dot = _DotWidget(color, diameter=14)
        layout.addWidget(dot)
        lbl = QLabel(label)
        lbl.setObjectName("tag_group_label")
        layout.addWidget(lbl, 1)
        self._count_lbl = QLabel(str(count))
        self._count_lbl.setObjectName("tag_group_count")
        layout.addWidget(self._count_lbl)

    def set_count(self, n: int) -> None:
        self._count_lbl.setText(str(n))

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ── Persistent library side panel ─────────────────────────────────────────────

class LibrarySidePanel(QWidget):
    tag_selected       = Signal(str)
    book_tagged        = Signal(str, str)   # (book_id, tag) — forwarded to MainWindow
    open_livros_tab    = Signal()           # request focus/open Livros tab
    open_anotacoes_tab = Signal()           # request focus/open Anotações tab

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("lib_side_panel")
        self._books: list[dict] = []
        self._active_key: str = ""   # "" | "__avulsos__" | "__anotacoes__" | folder-id
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("lib_panel_header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 12, 10, 10)
        hl.setSpacing(6)
        title = QLabel("BIBLIOTECA")
        title.setObjectName("lib_panel_title")
        hl.addWidget(title, 1)
        self._add_btn = QPushButton("+")
        self._add_btn.setObjectName("lib_panel_add_btn")
        self._add_btn.setFixedSize(22, 22)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setToolTip("Nova pasta ou divisor")
        self._add_btn.clicked.connect(self._show_add_menu)
        hl.addWidget(self._add_btn)
        layout.addWidget(header)

        layout.addWidget(self._hsep())

        # "Anotações" row — fixed shortcut to Notes tab (pinned above Todos)
        self._anotacoes_row = _FixedRow("Anotações", 0, "#8b5cf6")
        self._anotacoes_row.clicked.connect(self._on_anotacoes_clicked)
        layout.addWidget(self._anotacoes_row)

        layout.addWidget(self._inner_sep())

        # "Todos" row — also focuses the Livros tab
        self._todos_row = _FixedRow("Todos", 0, "#94a3b8")
        self._todos_row.set_active(True)
        self._todos_row.clicked.connect(self._on_todos_clicked)
        layout.addWidget(self._todos_row)

        layout.addWidget(self._inner_sep())

        # Draggable tree for user groups
        self._tree = _GroupTree(lambda: self._books)
        self._tree.tag_selected.connect(self._on_tree_selected)
        self._tree.structure_changed.connect(self._rebuild_counts)
        self._tree.book_tagged.connect(self._on_book_tagged)
        layout.addWidget(self._tree, 1)

        layout.addWidget(self._inner_sep())

        # "Avulsos" row
        self._avulsos_row = _FixedRow("Avulsos", 0, "#475569")
        self._avulsos_row.clicked.connect(lambda: self._select_fixed("__avulsos__"))
        layout.addWidget(self._avulsos_row)

    def _hsep(self) -> QFrame:
        f = QFrame(); f.setFrameShape(QFrame.HLine); f.setObjectName("panel_sep")
        return f

    def _inner_sep(self) -> QFrame:
        f = QFrame(); f.setFrameShape(QFrame.HLine); f.setObjectName("panel_inner_sep")
        return f

    # ── Public ────────────────────────────────────────────────────────────────

    def load(self) -> None:
        try:
            from pathlib import Path
            lib_path = AppConfig.load().get("library_path", str(Path.home() / "Sibyla Library"))
            self._books = [b.model_dump() for b in lib_svc.load_books(lib_path)]
        except Exception:
            self._books = []
        self._todos_row.set_count(len(self._books))
        avulsos = sum(1 for b in self._books if not (b.get("tags") or []))
        self._avulsos_row.set_count(avulsos)
        self._tree.populate(sg.load())
        # Restore active highlight after reload
        self._todos_row.set_active(self._active_key == "")
        self._avulsos_row.set_active(self._active_key == "__avulsos__")
        self._anotacoes_row.set_active(self._active_key == "__anotacoes__")

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_todos_clicked(self) -> None:
        self._select_fixed("")
        self.open_livros_tab.emit()

    def _on_anotacoes_clicked(self) -> None:
        self._active_key = "__anotacoes__"
        self._todos_row.set_active(False)
        self._avulsos_row.set_active(False)
        self._anotacoes_row.set_active(True)
        self._tree.set_active(None)
        self.open_anotacoes_tab.emit()

    def _select_fixed(self, key: str) -> None:
        self._active_key = key
        self._todos_row.set_active(key == "")
        self._avulsos_row.set_active(key == "__avulsos__")
        self._anotacoes_row.set_active(False)
        self._tree.set_active(None)
        self.tag_selected.emit(key)

    def _on_tree_selected(self, tag: str) -> None:
        self._active_key = tag
        self._todos_row.set_active(False)
        self._avulsos_row.set_active(False)
        self._anotacoes_row.set_active(False)
        self.tag_selected.emit(tag)

    # ── Book → folder drop ────────────────────────────────────────────────────

    def _on_book_tagged(self, book_id: str, tag: str) -> None:
        """Called when a BookCard is dropped onto a folder in the tree."""
        from pathlib import Path
        book = next((b for b in self._books if b["id"] == book_id), None)
        if not book:
            return
        lib_path = AppConfig.load().get("library_path", str(Path.home() / "Sibyla Library"))
        tags = list(book.get("tags") or [])
        if tag not in tags:
            tags.append(tag)
            try:
                lib_svc.update_book(lib_path, book_id, tags=tags)
                book["tags"] = tags          # update local cache
                self._rebuild_counts()       # refresh folder counts
                self.book_tagged.emit(book_id, tag)   # notify main window
            except Exception as e:
                print(f"[LibrarySidePanel] Error tagging book: {e}")

    # ── Counts after drag ─────────────────────────────────────────────────────

    def _rebuild_counts(self) -> None:
        self._tree.populate(sg.load())

    # ── Add at root level ─────────────────────────────────────────────────────

    def _show_add_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("Nova Pasta",   lambda: self._tree.add_root_group("folder"))
        menu.addAction("Novo Divisor", lambda: self._tree.add_root_group("divider"))
        menu.exec(self._add_btn.mapToGlobal(self._add_btn.rect().bottomLeft()))


# ── Floating reader window ────────────────────────────────────────────────────

class FloatingReader(QMainWindow):
    def __init__(self, book: dict) -> None:
        super().__init__()
        self.setWindowTitle(book.get("title") or "Leitor")
        self.setMinimumSize(820, 640)
        self._reader = ReaderView()
        self._reader.close_reader.connect(self.close)
        self.setCentralWidget(self._reader)
        self._reader.open_book(book)


# ── Reading layout (tab container) ───────────────────────────────────────────

class ReadingLayout(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._floating: list[FloatingReader] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._tabs = QTabWidget()
        self._tabs.setObjectName("reader_tabs")
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.tabCloseRequested.connect(self._tabs.removeTab)
        layout.addWidget(self._tabs)

    def open_book(self, book: dict) -> None:
        book_id = book.get("id", "")
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if getattr(w, "_book", {}).get("id") == book_id:
                self._tabs.setCurrentIndex(i)
                return
        reader = ReaderView(show_detach=True)
        reader.close_reader.connect(
            lambda: self._tabs.removeTab(self._tabs.indexOf(reader))
        )
        reader.detach_requested.connect(lambda: self._detach(reader))
        reader.open_book(book)
        title = book.get("title") or "Livro"
        short = (title[:16] + "…") if len(title) > 16 else title
        idx = self._tabs.addTab(reader, short)
        self._tabs.setCurrentIndex(idx)

    def _detach(self, reader: ReaderView) -> None:
        book = reader._book
        idx = self._tabs.indexOf(reader)
        if idx >= 0:
            self._tabs.removeTab(idx)
        win = FloatingReader(book)
        win.show()
        self._floating.append(win)
