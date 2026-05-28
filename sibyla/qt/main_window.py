from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QApplication, QTabWidget, QTabBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSettings

from sibyla.qt.core.queue_manager import QueueManager
from sibyla.qt.views.library_view import LibraryView
from sibyla.qt.views.translate_view import PdfView as TranslateView
from sibyla.qt.views.queue_view import QueueView
from sibyla.qt.views.history_view import HistoryView
from sibyla.qt.views.config_view import ConfigView
from sibyla.qt.views.notes_view import NotesView
from sibyla.qt.views.note_editor import NoteEditor
from sibyla.qt.views.reader_view import ReaderView
from sibyla.qt.views.reading_layout import LibrarySidePanel, FloatingReader
from sibyla.qt.styles import get_stylesheet

_ASSETS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets"
)
_LOGO = os.path.join(_ASSETS, "logo.png")

# Top nav items (Biblioteca is now a permanent tab, not a nav button)
NAV_ITEMS = [
    ("translate", "🌐  Traduzir"),
    ("queue",     "⏳  Fila"),
    ("history",   "🕘  Histórico"),
    ("config",    "⚙️   Config"),
]

# Tab IDs
_TAB_LIVROS    = "livros"
_TAB_ANOTACOES = "anotacoes"
_TAB_TRADUZIR  = "traduzir"
_TAB_QUEUE     = "queue"
_TAB_HISTORY   = "history"
_TAB_CONFIG    = "config"

_NAV_TAB_MAP: dict[str, tuple[str, str]] = {
    "translate": (_TAB_TRADUZIR, "🌐  Traduzir"),
    "queue":     (_TAB_QUEUE,    "⏳  Fila"),
    "history":   (_TAB_HISTORY,  "🕘  Histórico"),
    "config":    (_TAB_CONFIG,   "⚙️  Config"),
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sibyla")
        self.setMinimumSize(1180, 720)
        icon = os.path.join(_ASSETS, "logo_square.png")
        if not os.path.isfile(icon):
            icon = _LOGO
        if os.path.isfile(icon):
            self.setWindowIcon(QIcon(icon))
        self._q = QueueManager.instance()
        self._q.jobs_changed.connect(self._update_queue_badge)
        self._selected_book: dict | None = None
        self._floating: list[FloatingReader] = []
        self._build_ui()
        # Open default tabs on startup
        self._open_livros()
        self._open_anotacoes()
        self._focus_tab(_TAB_LIVROS)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top navigation bar ────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setObjectName("main_topbar")
        topbar.setFixedHeight(52)
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(16, 0, 20, 0)
        tl.setSpacing(2)

        if os.path.isfile(_LOGO):
            logo_lbl = QLabel()
            pix = QPixmap(_LOGO).scaledToHeight(30, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl = QLabel("Sibyla")
        logo_lbl.setObjectName("topbar_logo")
        logo_lbl.setContentsMargins(0, 0, 10, 0)
        tl.addWidget(logo_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setObjectName("topbar_vsep")
        sep.setFixedHeight(24)
        tl.addWidget(sep)
        tl.addSpacing(6)

        self._nav_buttons: dict[str, QPushButton] = {}
        for key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setObjectName("topnav_btn")
            btn.setProperty("active", False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_click(k))
            tl.addWidget(btn)
            self._nav_buttons[key] = btn

        tl.addStretch()

        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("theme_toggle_btn")
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.setToolTip("Alternar tema")
        self._theme_btn.clicked.connect(self._cycle_theme)
        self._current_theme = QSettings("Sibyla", "SibylaTranslate").value("theme", "default")
        self._update_theme_btn()
        tl.addWidget(self._theme_btn)

        tl.addSpacing(8)
        version_lbl = QLabel("v0.1.0")
        version_lbl.setObjectName("version")
        tl.addWidget(version_lbl)

        root.addWidget(topbar)

        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.HLine)
        sep_h.setObjectName("topbar_hsep")
        root.addWidget(sep_h)

        # ── Body: sidebar + tab content area ─────────────────────────────────
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self._lib_panel = LibrarySidePanel()
        self._lib_panel.setFixedWidth(240)
        self._lib_panel.tag_selected.connect(self._on_tag_selected)
        self._lib_panel.book_tagged.connect(self._on_book_tagged_from_panel)
        self._lib_panel.open_livros_tab.connect(self._open_livros)
        self._lib_panel.open_anotacoes_tab.connect(self._open_anotacoes)
        bl.addWidget(self._lib_panel)

        panel_sep = QFrame()
        panel_sep.setFrameShape(QFrame.VLine)
        panel_sep.setObjectName("panel_sep")
        bl.addWidget(panel_sep)

        # Main tab widget
        self._tabs = QTabWidget()
        self._tabs.setObjectName("main_tabs")
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        bl.addWidget(self._tabs, 1)

        root.addWidget(body, 1)

    # ── Tab utilities ─────────────────────────────────────────────────────────

    def _find_tab(self, tab_id: str) -> int:
        for i in range(self._tabs.count()):
            if getattr(self._tabs.widget(i), "_tab_id", None) == tab_id:
                return i
        return -1

    def _focus_tab(self, tab_id: str) -> bool:
        idx = self._find_tab(tab_id)
        if idx >= 0:
            self._tabs.setCurrentIndex(idx)
            return True
        return False

    def _add_tab(
        self,
        widget: QWidget,
        tab_id: str,
        label: str,
        closeable: bool = True,
    ) -> int:
        widget._tab_id = tab_id  # type: ignore[attr-defined]
        idx = self._tabs.addTab(widget, label)
        if not closeable:
            self._tabs.tabBar().setTabButton(idx, QTabBar.RightSide, None)
            self._tabs.tabBar().setTabButton(idx, QTabBar.LeftSide, None)
        return idx

    # ── Permanent tabs ────────────────────────────────────────────────────────

    def _open_livros(self) -> None:
        if self._focus_tab(_TAB_LIVROS):
            return
        view = LibraryView()
        view.open_book.connect(self._on_open_book)
        view.book_selected.connect(self._on_book_selected)
        view.books_changed.connect(self._lib_panel.load)
        self._library_view = view
        idx = self._add_tab(view, _TAB_LIVROS, "📚  Livros", closeable=True)
        self._tabs.setCurrentIndex(idx)
        view._load_books()
        self._lib_panel.load()

    def _open_anotacoes(self) -> None:
        if self._focus_tab(_TAB_ANOTACOES):
            return
        view = NotesView()
        view.open_note.connect(self._on_open_note)
        self._notes_view = view
        self._add_tab(view, _TAB_ANOTACOES, "📝  Anotações", closeable=True)

    # ── Tab events ────────────────────────────────────────────────────────────

    def _on_tab_close_requested(self, idx: int) -> None:
        widget = self._tabs.widget(idx)
        if isinstance(widget, NoteEditor):
            widget.flush_save()
        self._tabs.removeTab(idx)

    def _on_tab_changed(self, idx: int) -> None:
        w = self._tabs.widget(idx)
        tab_id = getattr(w, "_tab_id", None) if w else None
        nav_key_for_tab = {v[0]: k for k, v in _NAV_TAB_MAP.items()}
        active_nav_key = nav_key_for_tab.get(tab_id)
        for key, btn in self._nav_buttons.items():
            btn.setProperty("active", key == active_nav_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # Keep translate view in sync with config
        if tab_id == _TAB_TRADUZIR and isinstance(w, TranslateView):
            w._load_config()

    # ── Nav buttons open/focus utility tabs ───────────────────────────────────

    def _on_nav_click(self, key: str) -> None:
        tab_id, label = _NAV_TAB_MAP[key]
        if self._focus_tab(tab_id):
            return
        view = self._make_nav_view(key)
        self._add_tab(view, tab_id, label, closeable=True)
        self._focus_tab(tab_id)

    def _make_nav_view(self, key: str) -> QWidget:
        if key == "translate":
            v = TranslateView()
            v.go_to_queue.connect(lambda: self._on_nav_click("queue"))
            return v
        if key == "queue":
            return QueueView()
        if key == "history":
            return HistoryView()
        if key == "config":
            return ConfigView()
        return QWidget()

    def _update_queue_badge(self) -> None:
        n = self._q.active_count()
        btn = self._nav_buttons.get("queue")
        if btn:
            btn.setText(f"⏳  Fila  ({n})" if n > 0 else "⏳  Fila")

    # ── Book opening ──────────────────────────────────────────────────────────

    def _on_book_selected(self, book: dict) -> None:
        self._selected_book = book

    def _on_open_book(self, book: dict) -> None:
        book_id = book.get("id", "")
        tab_id = f"book:{book_id}"
        if self._focus_tab(tab_id):
            return
        reader = ReaderView(show_detach=True)
        reader.close_reader.connect(
            lambda: self._close_book_tab(tab_id)
        )
        reader.detach_requested.connect(lambda: self._detach_book(reader, book))
        reader.open_book(book)
        title = book.get("title") or "Livro"
        short = (title[:18] + "…") if len(title) > 18 else title
        idx = self._add_tab(reader, tab_id, f"📖  {short}", closeable=True)
        self._tabs.setCurrentIndex(idx)

    def _on_open_note(self, note: dict) -> None:
        note_id = note.get("id", "")
        tab_id = f"note:{note_id}"
        if self._focus_tab(tab_id):
            return
        editor = NoteEditor(note)
        editor.note_saved.connect(self._on_note_saved)
        title = note.get("title") or "Nova nota"
        short = (title[:18] + "…") if len(title) > 18 else title
        idx = self._add_tab(editor, tab_id, f"📝  {short}", closeable=True)
        self._tabs.setCurrentIndex(idx)

    def _on_note_saved(self, note: dict) -> None:
        # Update tab title if it changed
        tab_id = f"note:{note.get('id', '')}"
        idx = self._find_tab(tab_id)
        if idx >= 0:
            title = note.get("title") or "Nova nota"
            short = (title[:18] + "…") if len(title) > 18 else title
            self._tabs.setTabText(idx, f"📝  {short}")
        # Refresh notes grid if open
        if hasattr(self, "_notes_view"):
            self._notes_view.reload()

    def _close_book_tab(self, tab_id: str) -> None:
        idx = self._find_tab(tab_id)
        if idx >= 0:
            self._tabs.removeTab(idx)

    def _detach_book(self, reader: ReaderView, book: dict) -> None:
        book_id = book.get("id", "")
        self._close_book_tab(f"book:{book_id}")
        win = FloatingReader(book)
        win.show()
        self._floating.append(win)

    # ── Tag / sidebar actions ─────────────────────────────────────────────────

    def _on_tag_selected(self, tag: str) -> None:
        self._open_livros()
        if hasattr(self, "_library_view"):
            self._library_view.set_tag_filter(tag)

    def _on_book_tagged_from_panel(self, book_id: str, tag: str) -> None:
        if hasattr(self, "_library_view"):
            self._library_view._load_books()

    # ── Theme ─────────────────────────────────────────────────────────────────

    _THEME_CYCLE = ["dark", "light"]

    def _cycle_theme(self) -> None:
        idx = (
            self._THEME_CYCLE.index(self._current_theme)
            if self._current_theme in self._THEME_CYCLE
            else 0
        )
        self._current_theme = self._THEME_CYCLE[(idx + 1) % len(self._THEME_CYCLE)]
        QSettings("Sibyla", "SibylaTranslate").setValue("theme", self._current_theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(self._current_theme))
        self._update_theme_btn()

    def _update_theme_btn(self) -> None:
        if self._current_theme not in self._THEME_CYCLE:
            self._current_theme = "dark"
        icons = {"dark": "🌙", "light": "☀️"}
        tips = {
            "dark": "Modo escuro — clique para Claro",
            "light": "Modo claro — clique para Escuro",
        }
        self._theme_btn.setText(icons[self._current_theme])
        self._theme_btn.setToolTip(tips[self._current_theme])
