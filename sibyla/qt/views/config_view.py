from __future__ import annotations
from pathlib import Path
from sibyla.core.config import AppConfig
from sibyla.core import library as lib_svc
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QComboBox, QHBoxLayout,
    QFileDialog, QScrollArea, QFrame, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from sibyla.qt.styles import get_stylesheet

LANGUAGES = [
    ("Inglês", "en"), ("Português", "pt"), ("Espanhol", "es"),
    ("Francês", "fr"), ("Alemão", "de"), ("Italiano", "it"),
    ("Japonês", "ja"), ("Chinês (Simplificado)", "zh-cn"), ("Russo", "ru"),
]

FORMATS = [("Word (.docx)", "docx"), ("PDF (.pdf)", "pdf"), ("Texto (.txt)", "txt")]

ALIGNMENTS = [
    ("Original (do PDF)", "original"),
    ("Justificado", "justify"),
    ("Esquerda", "left"),
    ("Centralizado", "center"),
    ("Direita", "right"),
]

ENGINES = [
    ("Google Translate  (gratuito)", "google"),
    ("DeepL  (requer API key)", "deepl"),
    ("LibreTranslate  (requer URL/key)", "libretranslate"),
]

_LABEL_W = 220
_FIELD_W = 280


def _lbl(text: str) -> QLabel:
    l = QLabel(text)
    l.setFixedWidth(_LABEL_W)
    l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return l


def _row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    row.addWidget(_lbl(label))
    row.addWidget(widget)
    row.addStretch()
    return row


def _combo(items: list, width: int = _FIELD_W) -> QComboBox:
    c = QComboBox()
    c.setFixedWidth(width)
    for label, data in items:
        c.addItem(label, data)
    return c


class ConfigView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(20)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Configurações")
        title.setObjectName("page_title")
        root.addWidget(title)

        # ── Tradução ──
        trans_group = QGroupBox("Padrões de tradução")
        trans_layout = QVBoxLayout(trans_group)
        trans_layout.setSpacing(10)
        trans_layout.setContentsMargins(16, 20, 16, 16)

        self._default_src = _combo(LANGUAGES)
        self._default_dst = _combo(LANGUAGES)
        self._default_fmt = _combo(FORMATS, 200)
        self._default_alinhamento = _combo(ALIGNMENTS, 200)
        self._default_modo_traducao = QComboBox()
        self._default_modo_traducao.setFixedWidth(_FIELD_W)
        self._default_modo_traducao.addItem("Bloco a bloco  (mais compatível)", "bloco")
        self._default_modo_traducao.addItem("Página inteira  (~10× mais rápido)", "pagina")

        trans_layout.addLayout(_row("Idioma de origem padrão:", self._default_src))
        trans_layout.addLayout(_row("Idioma de destino padrão:", self._default_dst))
        trans_layout.addLayout(_row("Formato de saída padrão:", self._default_fmt))
        trans_layout.addLayout(_row("Alinhamento padrão:", self._default_alinhamento))
        trans_layout.addLayout(_row("Método de tradução:", self._default_modo_traducao))
        root.addWidget(trans_group)

        # ── Engine ──
        engine_group = QGroupBox("Motor de tradução")
        engine_layout = QVBoxLayout(engine_group)
        engine_layout.setSpacing(10)
        engine_layout.setContentsMargins(16, 20, 16, 16)

        self._default_engine = _combo(ENGINES)
        self._default_engine.currentIndexChanged.connect(self._on_engine_changed)

        self._engine_api_key = QLineEdit()
        self._engine_api_key.setFixedWidth(_FIELD_W)
        self._engine_api_key.setEchoMode(QLineEdit.Password)
        self._engine_api_key.setPlaceholderText("Chave de API…")

        self._engine_api_key_row = QHBoxLayout()
        self._engine_api_key_row.setSpacing(12)
        self._engine_api_key_row.addWidget(_lbl("API key:"))
        self._engine_api_key_row.addWidget(self._engine_api_key)
        self._engine_api_key_row.addStretch()
        self._engine_api_key_widget = QWidget()
        self._engine_api_key_widget.setLayout(self._engine_api_key_row)

        engine_layout.addLayout(_row("Engine padrão:", self._default_engine))
        engine_layout.addWidget(self._engine_api_key_widget)
        root.addWidget(engine_group)

        # ── Glossário ──
        glossary_group = QGroupBox("Glossário de termos protegidos")
        glossary_layout = QVBoxLayout(glossary_group)
        glossary_layout.setSpacing(10)
        glossary_layout.setContentsMargins(16, 20, 16, 16)

        self._glossary_list = QListWidget()
        self._glossary_list.setFixedHeight(160)
        self._glossary_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background: #f8fafc;
                font-size: 13px;
            }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background: #dbeafe; color: #1e40af; }
        """)
        glossary_layout.addWidget(self._glossary_list)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._term_edit = QLineEdit()
        self._term_edit.setPlaceholderText("Novo termo (ex: Harry Potter)…")
        self._term_edit.returnPressed.connect(self._add_term)
        add_btn = QPushButton("Adicionar")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedWidth(100)
        add_btn.clicked.connect(self._add_term)
        remove_btn = QPushButton("Remover")
        remove_btn.setObjectName("btn_secondary")
        remove_btn.setFixedWidth(90)
        remove_btn.clicked.connect(self._remove_term)
        add_row.addWidget(self._term_edit)
        add_row.addWidget(add_btn)
        add_row.addWidget(remove_btn)
        glossary_layout.addLayout(add_row)

        self._glossary_status = QLabel("")
        self._glossary_status.setStyleSheet("color: #64748b; font-size: 11px;")
        glossary_layout.addWidget(self._glossary_status)
        root.addWidget(glossary_group)

        # ── Biblioteca ──
        lib_group = QGroupBox("Biblioteca")
        lib_layout = QVBoxLayout(lib_group)
        lib_layout.setSpacing(10)
        lib_layout.setContentsMargins(16, 20, 16, 16)

        self._library_path = QLineEdit()
        self._library_path.setFixedWidth(_FIELD_W)
        self._library_path.setPlaceholderText("~/Sibyla Library")

        browse_lib = QPushButton("Escolher…")
        browse_lib.setObjectName("btn_secondary")
        browse_lib.setFixedWidth(90)
        browse_lib.clicked.connect(self._browse_library)

        lib_row = QHBoxLayout()
        lib_row.setSpacing(8)
        lib_row.addWidget(_lbl("Pasta da biblioteca:"))
        lib_row.addWidget(self._library_path)
        lib_row.addWidget(browse_lib)
        lib_row.addStretch()
        lib_layout.addLayout(lib_row)
        root.addWidget(lib_group)

        # ── Aparência ──
        appear_group = QGroupBox("Aparência")
        appear_layout = QVBoxLayout(appear_group)
        appear_layout.setSpacing(10)
        appear_layout.setContentsMargins(16, 20, 16, 16)

        self._theme_combo = QComboBox()
        self._theme_combo.setFixedWidth(200)
        self._theme_combo.addItem("Escuro", "dark")
        self._theme_combo.addItem("Claro", "light")
        saved_theme = QSettings("Sibyla", "SibylaTranslate").value("theme", "dark")
        idx = self._theme_combo.findData(saved_theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        appear_layout.addLayout(_row("Tema:", self._theme_combo))
        root.addWidget(appear_group)

        # ── Salvar ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("  Salvar configurações  ")
        save_btn.setObjectName("btn_primary")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #64748b; font-size: 12px;")
        root.addWidget(self._status)

    def _on_theme_changed(self) -> None:
        theme = self._theme_combo.currentData()
        QSettings("Sibyla", "SibylaTranslate").setValue("theme", theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(theme))

    def _on_engine_changed(self) -> None:
        needs_key = self._default_engine.currentData() in ("deepl", "libretranslate")
        self._engine_api_key_widget.setVisible(needs_key)

    def _load(self) -> None:
        cfg = AppConfig.load().all()
        self._set_combo(self._default_src, cfg.get("lang_src", "en"))
        self._set_combo(self._default_dst, cfg.get("lang_dst", "pt"))
        self._set_combo(self._default_fmt, cfg.get("fmt", "docx"))
        self._set_combo(self._default_alinhamento, cfg.get("alinhamento", "original"))
        self._set_combo(self._default_modo_traducao, cfg.get("modo_traducao", "pagina"))
        self._set_combo(self._default_engine, cfg.get("engine", "google"))
        self._engine_api_key.setText(cfg.get("engine_api_key", "") or "")
        self._on_engine_changed()
        self._library_path.setText(cfg.get("library_path", ""))
        self._load_glossary()

    def _load_glossary(self) -> None:
        terms = AppConfig.load().get("glossario", [])
        self._glossary_list.clear()
        for t in terms:
            self._glossary_list.addItem(QListWidgetItem(t))

    def _add_term(self) -> None:
        term = self._term_edit.text().strip()
        if not term:
            return
        cfg = AppConfig.load()
        terms: list = cfg.get("glossario", [])
        if term not in terms:
            terms.append(term)
            cfg.set("glossario", terms)
        self._glossary_list.clear()
        for t in terms:
            self._glossary_list.addItem(QListWidgetItem(t))
        self._term_edit.clear()
        self._glossary_status.setText(f'✓ "{term}" adicionado.')

    def _remove_term(self) -> None:
        item = self._glossary_list.currentItem()
        if not item:
            return
        term = item.text()
        cfg = AppConfig.load()
        terms: list = [t for t in cfg.get("glossario", []) if t != term]
        cfg.set("glossario", terms)
        self._glossary_list.clear()
        for t in terms:
            self._glossary_list.addItem(QListWidgetItem(t))
        self._glossary_status.setText(f'✓ "{term}" removido.')

    def _set_combo(self, combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _browse_library(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Escolher pasta da biblioteca", self._library_path.text() or ""
        )
        if path:
            self._library_path.setText(path)

    def _save(self) -> None:
        payload = {
            "lang_src": self._default_src.currentData(),
            "lang_dst": self._default_dst.currentData(),
            "fmt": self._default_fmt.currentData(),
            "alinhamento": self._default_alinhamento.currentData(),
            "modo_traducao": self._default_modo_traducao.currentData(),
            "engine": self._default_engine.currentData(),
            "engine_api_key": self._engine_api_key.text().strip() or None,
        }
        lib_path = self._library_path.text().strip()
        if lib_path:
            payload["library_path"] = lib_path
        try:
            AppConfig.load().set_many(payload)
        except Exception as e:
            self._status.setText(f"✗ Erro ao salvar: {e}")
            return
        self._status.setText("✓ Configurações salvas.")
