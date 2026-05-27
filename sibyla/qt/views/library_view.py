from __future__ import annotations
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QFileDialog, QMenu,
    QMessageBox, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox,
    QComboBox, QStackedWidget,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCursor

from sibyla.core.config import AppConfig
from sibyla.core import library as lib_svc
from sibyla.qt.core import sidebar_groups as sg
from sibyla.qt.core.queue_manager import QueueManager
from sibyla.qt.widgets.book_card import BookCard
from sibyla.qt.widgets.search_bar import SearchBar

SUPPORTED = "PDF e EPUB (*.pdf *.epub)"

_SORT_OPTIONS = [
    ("Ordenar: Título A-Z",   "title_asc"),
    ("Título Z-A",             "title_desc"),
    ("Autor A-Z",              "author_asc"),
    ("Data (+ recente)",       "date_desc"),
    ("Data (+ antiga)",        "date_asc"),
    ("Avaliação",              "rating_desc"),
]


def _library_path() -> str:
    return AppConfig.load().get("library_path", str(Path.home() / "Sibyla Library"))


class _ImportThread(QThread):
    done = Signal(object)
    error = Signal(str)

    def __init__(self, path: str, copy_to_library: bool = False) -> None:
        super().__init__()
        self._path = path
        self._copy = copy_to_library

    def run(self) -> None:
        try:
            book = lib_svc.import_book(_library_path(), self._path, self._copy)
            self.done.emit(book)
        except Exception as e:
            self.error.emit(str(e))


class LibraryView(QWidget):
    open_book = Signal(dict)
    book_selected = Signal(dict)
    books_changed = Signal()   # emitted after any add/remove/move

    def __init__(self) -> None:
        super().__init__()
        self._books: list = []
        self._filter = "all"
        self._query = ""
        self._sort_key = "title_asc"
        self._active_tag: str | None = None
        self._threads: list[QThread] = []
        self._importing = 0
        self._select_mode = False
        self._selected_ids: set[str] = set()
        self._cards: list = []
        self._tag_chip_btns: list[QPushButton] = []
        self._build_ui()
        self._load_books()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("library_header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(32, 24, 32, 16)
        hl.setSpacing(16)
        title = QLabel("Minha Biblioteca")
        title.setObjectName("page_title")
        hl.addWidget(title)
        hl.addStretch()
        self._count_label = QLabel("")
        self._count_label.setObjectName("library_count")
        hl.addWidget(self._count_label)
        self._sort_combo = QComboBox()
        self._sort_combo.setObjectName("sort_combo")
        for label, key in _SORT_OPTIONS:
            self._sort_combo.addItem(label, key)
        self._sort_combo.setFixedWidth(200)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        hl.addWidget(self._sort_combo)
        self._select_btn = QPushButton("Selecionar")
        self._select_btn.setObjectName("btn_secondary")
        self._select_btn.setCursor(Qt.PointingHandCursor)
        self._select_btn.clicked.connect(self._toggle_select_mode)
        hl.addWidget(self._select_btn)
        import_btn = QPushButton("+ Importar")
        import_btn.setObjectName("btn_primary")
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._import_dialog)
        hl.addWidget(import_btn)
        root.addWidget(header)

        self._bulk_bar = QWidget()
        self._bulk_bar.setObjectName("bulk_action_bar")
        bl = QHBoxLayout(self._bulk_bar)
        bl.setContentsMargins(32, 10, 32, 10)
        bl.setSpacing(12)
        self._bulk_label = QLabel("0 livros selecionados")
        self._bulk_label.setStyleSheet("color:#1e293b;font-size:13px;font-weight:500;")
        bl.addWidget(self._bulk_label)
        bl.addStretch()
        self._bulk_queue_btn = QPushButton("Adicionar à fila (0)")
        self._bulk_queue_btn.setObjectName("btn_primary")
        self._bulk_queue_btn.setEnabled(False)
        self._bulk_queue_btn.clicked.connect(self._queue_selected)
        bl.addWidget(self._bulk_queue_btn)
        cancel_sel_btn = QPushButton("Cancelar seleção")
        cancel_sel_btn.setObjectName("btn_secondary")
        cancel_sel_btn.clicked.connect(self._toggle_select_mode)
        bl.addWidget(cancel_sel_btn)
        self._bulk_bar.setStyleSheet(
            "QWidget#bulk_action_bar{background:#eff6ff;border-bottom:1px solid #bfdbfe;}"
        )
        self._bulk_bar.hide()
        root.addWidget(self._bulk_bar)

        self._import_bar = QLabel("")
        self._import_bar.setObjectName("import_status")
        self._import_bar.setAlignment(Qt.AlignCenter)
        self._import_bar.setFixedHeight(32)
        self._import_bar.hide()
        root.addWidget(self._import_bar)

        bar_container = QWidget()
        bar_container.setObjectName("search_container")
        bar_layout = QHBoxLayout(bar_container)
        bar_layout.setContentsMargins(32, 0, 32, 16)
        self._search_bar = SearchBar()
        self._search_bar.search_changed.connect(self._on_search)
        self._search_bar.filter_changed.connect(self._on_filter)
        bar_layout.addWidget(self._search_bar)
        root.addWidget(bar_container)

        self._tag_row_container = QWidget()
        self._tag_row_container.setObjectName("tag_chips_container")
        tro = QHBoxLayout(self._tag_row_container)
        tro.setContentsMargins(32, 0, 32, 12)
        tro.setSpacing(0)
        self._tag_scroll = QScrollArea()
        self._tag_scroll.setWidgetResizable(True)
        self._tag_scroll.setFrameShape(QFrame.NoFrame)
        self._tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tag_scroll.setFixedHeight(36)
        self._tag_chips_widget = QWidget()
        self._tag_chips_layout = QHBoxLayout(self._tag_chips_widget)
        self._tag_chips_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_chips_layout.setSpacing(8)
        self._tag_chips_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._tag_scroll.setWidget(self._tag_chips_widget)
        tro.addWidget(self._tag_scroll)
        self._tag_row_container.hide()
        root.addWidget(self._tag_row_container)

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("content_stack")

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._grid_container = QWidget()
        self._grid_container.setObjectName("grid_container")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(32, 8, 32, 32)
        self._grid.setSpacing(20)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._scroll.setWidget(self._grid_container)
        self._content_stack.addWidget(self._scroll)

        empty_page = QWidget()
        empty_page.setObjectName("grid_container")
        el = QVBoxLayout(empty_page)
        el.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        el.setContentsMargins(32, 40, 32, 32)
        self._empty_label = QLabel(
            "Nenhum livro na biblioteca.\nClique em '+ Importar' para adicionar."
        )
        self._empty_label.setObjectName("empty_label")
        self._empty_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        el.addWidget(self._empty_label)
        el.addStretch()
        self._content_stack.addWidget(empty_page)
        root.addWidget(self._content_stack, 1)

    def _load_books(self) -> None:
        try:
            self._books = [b.model_dump() for b in lib_svc.load_books(_library_path())]
        except Exception:
            self._books = []
        self._render_grid()

    def _render_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self._update_tag_chips()
        visible = self._filtered_books()
        self._count_label.setText(f"{len(visible)} livro{'s' if len(visible) != 1 else ''}")
        if not visible:
            self._content_stack.setCurrentIndex(1)
            return
        self._content_stack.setCurrentIndex(0)
        cols = max(1, (self.width() - 64) // (160 + 20))
        for i, book in enumerate(visible):
            card = BookCard(book)
            card.set_select_mode(self._select_mode)
            if self._select_mode and book["id"] in self._selected_ids:
                card.set_selected(True)
            card.clicked.connect(self._on_book_clicked)
            card.right_clicked.connect(self._on_book_right_clicked)
            card.selection_changed.connect(self._on_selection_changed)
            self._cards.append(card)
            self._grid.addWidget(card, i // cols, i % cols)

    def _filtered_books(self) -> list[dict]:
        q = self._query.lower()
        result = []
        for b in self._books:
            if self._filter == "pdf" and b.get("format") != "pdf":
                continue
            if self._filter == "epub" and b.get("format") != "epub":
                continue
            if self._filter == "translated" and not b.get("translated"):
                continue
            if self._active_tag is not None:
                if self._active_tag == "__avulsos__":
                    if b.get("tags"):
                        continue
                elif self._active_tag not in b.get("tags", []):
                    continue
            if q:
                tags_text = " ".join(b.get("tags", [])).lower()
                if (q not in b.get("title", "").lower()
                        and q not in b.get("author", "").lower()
                        and q not in tags_text):
                    continue
            result.append(b)
        key = self._sort_key
        if key == "title_asc":   result.sort(key=lambda b: b.get("title","").lower())
        elif key == "title_desc": result.sort(key=lambda b: b.get("title","").lower(), reverse=True)
        elif key == "author_asc": result.sort(key=lambda b: b.get("author","").lower())
        elif key == "date_desc":  result.sort(key=lambda b: b.get("added_at",""), reverse=True)
        elif key == "date_asc":   result.sort(key=lambda b: b.get("added_at",""))
        elif key == "rating_desc":result.sort(key=lambda b: b.get("rating",0), reverse=True)
        return result

    def _update_tag_chips(self) -> None:
        self._tag_row_container.hide()

    def _on_tag_chip_clicked(self, tag: str) -> None:
        self._active_tag = None if self._active_tag == tag else tag
        for btn in self._tag_chip_btns:
            btn.setProperty("active", "true" if btn.text() == self._active_tag else "false")
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._render_grid()

    def set_tag_filter(self, tag: str) -> None:
        self._active_tag = None if tag == "" else tag
        for btn in self._tag_chip_btns:
            btn.setProperty("active", "true" if btn.text() == self._active_tag else "false")
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._render_grid()

    def _on_sort_changed(self, index: int) -> None:
        self._sort_key = self._sort_combo.itemData(index); self._render_grid()

    def _on_search(self, text: str) -> None:
        self._query = text; self._render_grid()

    def _on_filter(self, key: str) -> None:
        self._filter = key; self._render_grid()

    def _import_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar livros", "", SUPPORTED)
        if not paths: return
        dlg = QDialog(self)
        dlg.setWindowTitle("Importar livros")
        dlg.setMinimumWidth(360)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(QLabel(f"{len(paths)} arquivo(s) selecionado(s)."))
        chk = QCheckBox("Copiar para ~/Sibyla Library")
        chk.setChecked(False)
        layout.addWidget(chk)
        hint = QLabel("Por padrão, o arquivo permanece no local original.")
        hint.setStyleSheet("color:#94a3b8;font-size:11px;")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted: return
        copy = chk.isChecked()
        self._importing += len(paths)
        self._update_import_bar()
        for path in paths:
            t = _ImportThread(path, copy_to_library=copy)
            t.done.connect(self._on_imported)
            t.error.connect(self._on_import_error)
            self._threads.append(t)
            t.start()

    def _on_imported(self, book) -> None:
        bd = book.model_dump() if hasattr(book, "model_dump") else book
        ids = {b["id"] for b in self._books}
        if bd["id"] not in ids: self._books.insert(0, bd)
        else: self._books = [bd if b["id"] == bd["id"] else b for b in self._books]
        self._importing = max(0, self._importing - 1)
        self._update_import_bar(); self._render_grid()

    def _on_import_error(self, msg: str) -> None:
        self._importing = max(0, self._importing - 1)
        self._update_import_bar()
        QMessageBox.warning(self, "Erro ao importar", msg)

    def _update_import_bar(self) -> None:
        if self._importing > 0:
            self._import_bar.setText(f"⏳  Importando {self._importing} arquivo{'s' if self._importing != 1 else ''}…")
            self._import_bar.show()
        else:
            self._import_bar.hide()

    def _toggle_select_mode(self) -> None:
        self._select_mode = not self._select_mode
        self._selected_ids.clear()
        self._bulk_bar.setVisible(self._select_mode)
        self._select_btn.setVisible(not self._select_mode)
        self._update_bulk_bar()
        for card in self._cards: card.set_select_mode(self._select_mode)

    def _on_selection_changed(self, book: dict, selected: bool) -> None:
        if selected: self._selected_ids.add(book["id"])
        else: self._selected_ids.discard(book["id"])
        self._update_bulk_bar()

    def _update_bulk_bar(self) -> None:
        n = len(self._selected_ids)
        self._bulk_label.setText(f"{n} livro{'s' if n != 1 else ''} selecionado{'s' if n != 1 else ''}")
        self._bulk_queue_btn.setText(f"Adicionar à fila ({n})")
        self._bulk_queue_btn.setEnabled(n > 0)

    def _queue_selected(self) -> None:
        for book in [b for b in self._books if b["id"] in self._selected_ids]:
            self._queue_book(book)
        self._toggle_select_mode()

    def _on_book_clicked(self, book: dict) -> None:
        self.book_selected.emit(book); self.open_book.emit(book)

    def _on_book_right_clicked(self, book: dict, pos) -> None:
        menu = QMenu(self)
        menu.addAction("Abrir para tradução", lambda: self.open_book.emit(book))
        menu.addAction("Adicionar à fila de tradução", lambda: self._queue_book(book))
        menu.addSeparator()

        # ── Mover para ────────────────────────────────────────────────────────
        move_menu = menu.addMenu("Mover para…")
        groups = sg.load()
        all_group_tags = self._collect_group_tags(groups)
        current_tags = set(book.get("tags") or [])
        current_group_tags = current_tags & all_group_tags

        move_menu.addAction("Sem pasta", lambda: self._move_book_to(book, None, all_group_tags))
        if groups:
            move_menu.addSeparator()
            self._build_move_menu(move_menu, groups, book, all_group_tags, current_group_tags, indent=0)

        menu.addSeparator()
        menu.addAction("Editar metadados", lambda: self._edit_metadata(book))
        menu.addSeparator()
        menu.addAction("Remover da biblioteca", lambda: self._remove_book(book))
        menu.exec(pos)

    def _collect_group_tags(self, groups: list[dict]) -> set[str]:
        """Recursively collect all tags used by groups/dividers."""
        tags: set[str] = set()
        for g in groups:
            tags.add(g.get("tag", g["name"]))
            tags |= self._collect_group_tags(g.get("children", []))
        return tags

    def _build_move_menu(
        self, menu: QMenu, groups: list[dict],
        book: dict, all_group_tags: set[str],
        current_group_tags: set[str], indent: int,
    ) -> None:
        for g in groups:
            tag = g.get("tag", g["name"])
            prefix = "    " * indent
            label = f"{prefix}{g['name']}"
            is_current = tag in current_group_tags
            if is_current:
                label += "  ✓"
            action = menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, t=tag: self._move_book_to(book, t, all_group_tags)
            )
            children = g.get("children", [])
            if children:
                self._build_move_menu(menu, children, book, all_group_tags, current_group_tags, indent + 1)

    def _move_book_to(self, book: dict, target_tag: str | None, all_group_tags: set[str]) -> None:
        """Remove all group tags from book, then add target_tag if given."""
        current_tags = list(book.get("tags") or [])
        new_tags = [t for t in current_tags if t not in all_group_tags]
        if target_tag:
            new_tags.append(target_tag)
        try:
            updated = lib_svc.update_book(_library_path(), book["id"], tags=new_tags)
            if updated:
                ud = updated.model_dump()
                self._books = [ud if b["id"] == ud["id"] else b for b in self._books]
                self._render_grid()
                self.books_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    def _queue_book(self, book: dict) -> None:
        file_path = book.get("path", "")
        if not file_path: return
        cfg = AppConfig.load().all()
        fmt = cfg.get("fmt", "docx")
        base = os.path.splitext(file_path)[0]
        output_path = f"{base}_traduzido.{fmt}"
        if file_path.lower().endswith(".epub") and fmt not in ("epub","docx","pdf","txt","md"):
            fmt = "epub"; output_path = f"{base}_traduzido.epub"
        settings = {
            "pag_ini": 1, "pag_fim": 9999, "modo": "novo",
            "lang_src": cfg.get("lang_src","auto"), "lang_dst": cfg.get("lang_dst","pt"),
            "fmt": fmt, "alinhamento": cfg.get("alinhamento","original"),
            "tamanho_fonte": None, "fonte": None,
            "modo_traducao": cfg.get("modo_traducao","pagina"),
            "engine": cfg.get("engine","google"), "engine_api_key": cfg.get("engine_api_key"),
            "glossario": [],
        }
        QueueManager.instance().add(
            file_path=file_path, output_path=output_path, settings=settings,
            book_id=book.get("id"), file_name=book.get("title") or os.path.basename(file_path),
        )

    def _edit_metadata(self, book: dict) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar metadados")
        dialog.setMinimumWidth(420)
        form = QFormLayout(dialog)
        form.setSpacing(12); form.setContentsMargins(20,20,20,20)
        title_edit = QLineEdit(book.get("title",""))
        author_edit = QLineEdit(book.get("author",""))
        lang_edit = QLineEdit(book.get("language",""))
        tags_edit = QLineEdit(", ".join(book.get("tags",[])))
        series_edit = QLineEdit(book.get("series",""))
        rating_combo = QComboBox()
        for lbl in ["Sem avaliação","★","★★","★★★","★★★★","★★★★★"]:
            rating_combo.addItem(lbl)
        rating_combo.setCurrentIndex(book.get("rating",0))
        read_combo = QComboBox()
        read_opts = [("Não lido","unread"),("Lendo","reading"),("Lido","read")]
        for lbl, val in read_opts: read_combo.addItem(lbl, val)
        cur = book.get("read_status","unread")
        read_combo.setCurrentIndex(next((i for i,(_, v) in enumerate(read_opts) if v==cur), 0))
        trans_combo = QComboBox()
        trans_opts = [("Não traduzido","none"),("Em tradução","in_progress"),("Traduzido","done")]
        for lbl, val in trans_opts: trans_combo.addItem(lbl, val)
        ct = book.get("translation_status","none")
        trans_combo.setCurrentIndex(next((i for i,(_, v) in enumerate(trans_opts) if v==ct), 0))
        form.addRow("Título:", title_edit)
        form.addRow("Autor:", author_edit)
        form.addRow("Idioma:", lang_edit)
        form.addRow("Tags (vírgula):", tags_edit)
        form.addRow("Avaliação:", rating_combo)
        form.addRow("Status de leitura:", read_combo)
        form.addRow("Status de tradução:", trans_combo)
        form.addRow("Série:", series_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            raw_tags = [t.strip() for t in tags_edit.text().split(",") if t.strip()]
            try:
                updated = lib_svc.update_book(
                    _library_path(), book["id"],
                    title=title_edit.text(), author=author_edit.text(),
                    language=lang_edit.text(), tags=raw_tags,
                    rating=rating_combo.currentIndex(),
                    read_status=read_combo.currentData(),
                    translation_status=trans_combo.currentData(),
                    series=series_edit.text(),
                )
                if updated:
                    ud = updated.model_dump()
                    self._books = [ud if b["id"]==ud["id"] else b for b in self._books]
                    self._render_grid()
            except Exception as e:
                QMessageBox.warning(self, "Erro", str(e))

    def _remove_book(self, book: dict) -> None:
        reply = QMessageBox.question(
            self, "Remover livro", f"Remover '{book.get('title')}' da biblioteca?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                lib_svc.remove_book(_library_path(), book["id"])
                self._books = [b for b in self._books if b["id"] != book["id"]]
                self._render_grid()
                self.books_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Erro", str(e))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event); self._render_grid()
