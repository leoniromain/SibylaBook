from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QApplication,
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
from sibyla.qt.views.reading_layout import ReadingLayout, LibrarySidePanel
from sibyla.qt.styles import get_stylesheet

_ASSETS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets"
)
_LOGO = os.path.join(_ASSETS, "logo.png")

NAV_ITEMS = [
    ("library",   "📚  Biblioteca"),
    ("translate", "🌐  Traduzir"),
    ("queue",     "⏳  Fila"),
    ("history",   "🕘  Histórico"),
    ("config",    "⚙️   Config"),
]

_IDX_LIBRARY   = 0
_IDX_TRANSLATE = 1
_IDX_QUEUE     = 2
_IDX_HISTORY   = 3
_IDX_CONFIG    = 4
_IDX_READER    = 5


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
        self._q.jobs_changed.connect(self._update_queue_nav)
        self._selected_book: dict | None = None
        self._build_ui()
        self._select(_IDX_LIBRARY)

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

        self._nav_buttons: list[QPushButton] = []
        for i, (key, label) in enumerate(NAV_ITEMS):
            btn = QPushButton(label)
            btn.setObjectName("topnav_btn")
            btn.setProperty("active", False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._select(idx))
            tl.addWidget(btn)
            self._nav_buttons.append(btn)

        tl.addStretch()

        # ── Theme toggle button ───────────────────────────────────────────────
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

        # ── Body: persistent library panel + content ──────────────────────────
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        # Persistent library panel (always visible)
        self._lib_panel = LibrarySidePanel()
        self._lib_panel.setFixedWidth(240)
        self._lib_panel.tag_selected.connect(self._on_tag_selected)
        self._lib_panel.book_tagged.connect(self._on_book_tagged_from_panel)
        bl.addWidget(self._lib_panel)

        panel_sep = QFrame()
        panel_sep.setFrameShape(QFrame.VLine)
        panel_sep.setObjectName("panel_sep")
        bl.addWidget(panel_sep)

        # Content area
        content = QFrame()
        content.setObjectName("content")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._library_view   = LibraryView()
        self._library_view.open_book.connect(self._on_open_book)
        self._library_view.book_selected.connect(self._on_book_selected)
        self._library_view.books_changed.connect(self._lib_panel.load)

        self._translate_view = TranslateView()
        self._translate_view.go_to_queue.connect(lambda: self._select(_IDX_QUEUE))

        self._queue_view     = QueueView()
        self._history_view   = HistoryView()
        self._config_view    = ConfigView()

        self._reading_layout = ReadingLayout()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._library_view)    # 0
        self._stack.addWidget(self._translate_view)  # 1
        self._stack.addWidget(self._queue_view)      # 2
        self._stack.addWidget(self._history_view)    # 3
        self._stack.addWidget(self._config_view)     # 4
        self._stack.addWidget(self._reading_layout)  # 5

        cl.addWidget(self._stack, 1)
        bl.addWidget(content, 1)
        root.addWidget(body, 1)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _update_queue_nav(self) -> None:
        n = self._q.active_count()
        btn = self._nav_buttons[_IDX_QUEUE]
        btn.setText(f"⏳  Fila  ({n})" if n > 0 else "⏳  Fila")

    def _select(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

        nav_idx = index if index < len(self._nav_buttons) else -1
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", i == nav_idx)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if index == _IDX_LIBRARY:
            self._library_view._load_books()
            self._lib_panel.load()
        elif index == _IDX_TRANSLATE:
            self._translate_view._load_config()

    # ── Book / tag actions ────────────────────────────────────────────────────

    def _on_tag_selected(self, tag: str) -> None:
        self._select(_IDX_LIBRARY)
        self._library_view.set_tag_filter(tag)

    def _on_book_selected(self, book: dict) -> None:
        self._selected_book = book

    def _on_book_tagged_from_panel(self, book_id: str, tag: str) -> None:
        """Refresh library grid after a book is drag-dropped into a folder."""
        self._library_view._load_books()

    def _on_open_book(self, book: dict) -> None:
        self._selected_book = book
        self._reading_layout.open_book(book)
        self._stack.setCurrentIndex(_IDX_READER)
        for btn in self._nav_buttons:
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Theme toggle ──────────────────────────────────────────────────────────

    _THEME_CYCLE = ["dark", "light"]

    def _cycle_theme(self) -> None:
        idx = self._THEME_CYCLE.index(self._current_theme) if self._current_theme in self._THEME_CYCLE else 0
        self._current_theme = self._THEME_CYCLE[(idx + 1) % len(self._THEME_CYCLE)]
        QSettings("Sibyla", "SibylaTranslate").setValue("theme", self._current_theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(self._current_theme))
        self._update_theme_btn()

    def _update_theme_btn(self) -> None:
        # Normalize legacy "default" to "dark"
        if self._current_theme not in self._THEME_CYCLE:
            self._current_theme = "dark"
        icons = {"dark": "🌙", "light": "☀️"}
        tips  = {"dark": "Modo escuro — clique para Claro", "light": "Modo claro — clique para Escuro"}
        self._theme_btn.setText(icons[self._current_theme])
        self._theme_btn.setToolTip(tips[self._current_theme])
