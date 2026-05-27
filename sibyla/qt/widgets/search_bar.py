from __future__ import annotations
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon


class SearchBar(QWidget):
    search_changed = Signal(str)
    filter_changed = Signal(str)  # "all" | "pdf" | "epub" | "translated"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_filter = "all"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setObjectName("search_input")
        self._search.setPlaceholderText("Buscar por título ou autor…")
        self._search.textChanged.connect(self.search_changed)
        layout.addWidget(self._search, 1)

        for label, key in [("Todos", "all"), ("PDF", "pdf"), ("EPUB", "epub"), ("Traduzidos", "translated")]:
            btn = QPushButton(label)
            btn.setProperty("filter_key", key)
            btn.setObjectName("filter_btn")
            btn.setProperty("active", key == "all")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(False)
            btn.clicked.connect(lambda _, k=key: self._set_filter(k))
            layout.addWidget(btn)
            setattr(self, f"_btn_{key}", btn)

    def _set_filter(self, key: str) -> None:
        self._active_filter = key
        for k in ["all", "pdf", "epub", "translated"]:
            btn = getattr(self, f"_btn_{k}", None)
            if btn:
                btn.setProperty("active", k == key)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        self.filter_changed.emit(key)

    def text(self) -> str:
        return self._search.text()
