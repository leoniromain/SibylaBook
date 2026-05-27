from __future__ import annotations
import os
import urllib.request
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QComboBox, QFileDialog, QGroupBox,
    QGridLayout, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal

from sibyla.core.config import AppConfig
from sibyla.qt.core.queue_manager import QueueManager

LANGUAGES = [
    ("Detectar automaticamente", "auto"),
    ("Inglês", "en"), ("Português", "pt"), ("Espanhol", "es"),
    ("Francês", "fr"), ("Alemão", "de"), ("Italiano", "it"),
    ("Japonês", "ja"), ("Chinês (Simplificado)", "zh-cn"), ("Russo", "ru"),
]

FORMATS_PDF  = [("Word (.docx)", "docx"), ("PDF (.pdf)", "pdf"), ("Texto (.txt)", "txt"), ("Markdown (.md)", "md"), ("EPUB (.epub)", "epub")]
FORMATS_EPUB = [("EPUB (.epub)", "epub"), ("Word (.docx)", "docx"), ("PDF (.pdf)", "pdf"), ("Texto (.txt)", "txt"), ("Markdown (.md)", "md")]

ALIGNMENTS = [
    ("Original (do PDF)", "original"),
    ("Justificado", "justify"),
    ("Esquerda", "left"),
    ("Centralizado", "center"),
    ("Direita", "right"),
]

FONTS = [
    ("Padrão (do PDF)", ""),
    ("Arial / Helvetica", "Arial"),
    ("Times New Roman", "Times New Roman"),
    ("Georgia", "Georgia"),
    ("Verdana", "Verdana"),
    ("Calibri (Windows)", "Calibri"),
    ("Garamond", "Garamond"),
    ("Courier New", "Courier New"),
]

FONT_SIZES = [
    ("Original (do PDF)", 0),
    ("8 pt", 8), ("9 pt", 9), ("10 pt", 10), ("11 pt", 11),
    ("12 pt", 12), ("13 pt", 13), ("14 pt", 14), ("16 pt", 16),
    ("18 pt", 18), ("20 pt", 20), ("24 pt", 24),
]

ENGINES = [
    ("Google Translate  (gratuito)", "google"),
    ("DeepL  (requer API key)", "deepl"),
    ("LibreTranslate  (requer URL/key)", "libretranslate"),
]


class PdfView(QWidget):
    go_to_queue = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._current_book_id: str | None = None
        self._q = QueueManager.instance()
        self._q.jobs_changed.connect(self._update_queue_btn)
        self._build_ui()
        self._load_config()

    def set_book(self, book: dict) -> None:
        path = book.get("path", "")
        self._path_edit.setText(path)
        self._current_book_id = book.get("id")
        self._update_fmt_for_file(path)
        self._update_output_ext()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Topbar ──────────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setObjectName("library_header")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(32, 20, 24, 16)
        topbar_layout.setSpacing(16)

        page_title = QLabel("Nova tradução")
        page_title.setObjectName("page_title")
        topbar_layout.addWidget(page_title)
        topbar_layout.addStretch()

        self._queue_btn = QPushButton("Ver fila")
        self._queue_btn.setObjectName("btn_secondary")
        self._queue_btn.setFixedHeight(34)
        self._queue_btn.setMinimumWidth(110)
        self._queue_btn.setCursor(Qt.PointingHandCursor)
        self._queue_btn.clicked.connect(self.go_to_queue)
        topbar_layout.addWidget(self._queue_btn)
        root.addWidget(topbar)

        # ── Formulário ───────────────────────────────────────────────────────
        form_widget = QWidget()
        form_outer = QVBoxLayout(form_widget)
        form_outer.setContentsMargins(0, 0, 0, 0)
        form_outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(32, 24, 32, 24)
        form_layout.setSpacing(20)

        # arquivo
        file_group = QGroupBox("Arquivo de origem")
        file_layout = QHBoxLayout(file_group)
        file_layout.setSpacing(10)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Selecione um PDF ou EPUB…")
        self._path_edit.setReadOnly(True)
        browse_btn = QPushButton("Abrir arquivo")
        browse_btn.setObjectName("btn_secondary")
        browse_btn.setFixedWidth(120)
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self._path_edit)
        file_layout.addWidget(browse_btn)
        form_layout.addWidget(file_group)

        # opções
        opts_group = QGroupBox("Opções de tradução")
        grid = QGridLayout(opts_group)
        grid.setSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnMinimumWidth(2, 24)

        self._lang_src = QComboBox()
        self._lang_dst = QComboBox()
        for label, code in LANGUAGES:
            self._lang_src.addItem(label, code)
            self._lang_dst.addItem(label, code)

        self._fmt = QComboBox()
        for label, code in FORMATS_PDF:
            self._fmt.addItem(label, code)
        self._fmt.currentIndexChanged.connect(self._update_output_ext)

        self._alinhamento = QComboBox()
        for label, code in ALIGNMENTS:
            self._alinhamento.addItem(label, code)

        self._tamanho_fonte = QComboBox()
        for label, val in FONT_SIZES:
            self._tamanho_fonte.addItem(label, val)

        self._fonte = QComboBox()
        for label, val in FONTS:
            self._fonte.addItem(label, val)

        self._modo_traducao = QComboBox()
        self._modo_traducao.addItem("Bloco a bloco  (mais compatível)", "bloco")
        self._modo_traducao.addItem("Página inteira  (~10× mais rápido)", "pagina")

        self._engine = QComboBox()
        for label, code in ENGINES:
            self._engine.addItem(label, code)
        self._engine.currentIndexChanged.connect(self._on_engine_changed)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setPlaceholderText("API key…")
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.hide()
        self._api_key_label_idx = None

        self._pag_ini = QSpinBox()
        self._pag_ini.setMinimum(1)
        self._pag_ini.setMaximum(9999)
        self._pag_fim = QSpinBox()
        self._pag_fim.setMinimum(1)
        self._pag_fim.setMaximum(9999)
        self._pag_fim.setValue(9999)
        page_row = QHBoxLayout()
        page_row.setSpacing(8)
        page_row.addWidget(self._pag_ini)
        page_row.addWidget(QLabel("até"))
        page_row.addWidget(self._pag_fim)
        page_row.addStretch()
        page_widget = QWidget()
        page_widget.setLayout(page_row)

        def lbl(text):
            l = QLabel(text)
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return l

        grid.addWidget(lbl("Idioma de origem:"),  0, 0)
        grid.addWidget(self._lang_src,             0, 1)
        grid.addWidget(lbl("Idioma de destino:"), 0, 3)
        grid.addWidget(self._lang_dst,             0, 4)
        grid.addWidget(lbl("Formato de saída:"),  1, 0)
        grid.addWidget(self._fmt,                  1, 1)
        grid.addWidget(lbl("Alinhamento:"),        1, 3)
        grid.addWidget(self._alinhamento,           1, 4)
        grid.addWidget(lbl("Tamanho da fonte:"),  2, 0)
        grid.addWidget(self._tamanho_fonte,         2, 1)
        grid.addWidget(lbl("Fonte:"),              2, 3)
        grid.addWidget(self._fonte,                 2, 4)
        grid.addWidget(lbl("Método:"),             3, 0)
        grid.addWidget(self._modo_traducao,         3, 1)
        self._page_label = lbl("Páginas:")
        self._page_info_icon = QLabel("!")
        self._page_info_icon.setObjectName("info_icon")
        self._page_info_icon.setFixedSize(16, 16)
        self._page_info_icon.setAlignment(Qt.AlignCenter)
        self._page_info_icon.hide()
        page_label_container = QWidget()
        page_label_row = QHBoxLayout(page_label_container)
        page_label_row.setContentsMargins(0, 0, 0, 0)
        page_label_row.setSpacing(4)
        page_label_row.addStretch()
        page_label_row.addWidget(self._page_label)
        page_label_row.addWidget(self._page_info_icon)
        grid.addWidget(page_label_container,        3, 3)
        grid.addWidget(page_widget,                 3, 4)
        grid.addWidget(lbl("Engine:"),             4, 0)
        grid.addWidget(self._engine,                4, 1)
        self._api_key_label = lbl("API key:")
        self._api_key_label.hide()
        grid.addWidget(self._api_key_label,         4, 3)
        grid.addWidget(self._api_key_edit,          4, 4)
        form_layout.addWidget(opts_group)

        # saída
        out_group = QGroupBox("Arquivo de saída")
        out_layout = QHBoxLayout(out_group)
        out_layout.setSpacing(10)
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Caminho do arquivo traduzido…")
        out_browse = QPushButton("Escolher destino")
        out_browse.setObjectName("btn_secondary")
        out_browse.setFixedWidth(130)
        out_browse.clicked.connect(self._browse_output)
        out_layout.addWidget(self._out_edit)
        out_layout.addWidget(out_browse)
        form_layout.addWidget(out_group)

        form_layout.addStretch()
        scroll.setWidget(form_container)
        form_outer.addWidget(scroll, 1)

        # Botão adicionar
        btn_bar = QWidget()
        btn_bar.setObjectName("bottom_panel")
        btn_bar_layout = QHBoxLayout(btn_bar)
        btn_bar_layout.setContentsMargins(32, 16, 32, 24)
        btn_bar_layout.addStretch()
        self._add_btn = QPushButton("  Adicionar à fila  ")
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.clicked.connect(self._add_to_queue)
        btn_bar_layout.addWidget(self._add_btn)
        form_outer.addWidget(btn_bar)

        root.addWidget(form_widget, 1)

    def _on_engine_changed(self) -> None:
        needs_key = self._engine.currentData() in ("deepl", "libretranslate")
        self._api_key_label.setVisible(needs_key)
        self._api_key_edit.setVisible(needs_key)

    def _update_queue_btn(self) -> None:
        n = self._q.active_count()
        total = len(self._q.jobs())
        if n > 0:
            self._queue_btn.setText(f"⏳ Fila ({n})")
            self._queue_btn.setObjectName("btn_primary")
        elif total > 0:
            self._queue_btn.setText(f"Ver fila ({total})")
            self._queue_btn.setObjectName("btn_secondary")
        else:
            self._queue_btn.setText("Ver fila")
            self._queue_btn.setObjectName("btn_secondary")
        self._queue_btn.style().unpolish(self._queue_btn)
        self._queue_btn.style().polish(self._queue_btn)

    # ── Config ───────────────────────────────────────────────────────────────
    def _load_config(self) -> None:
        cfg = AppConfig.load().all()
        self._set_combo(self._lang_src, cfg.get("lang_src", "auto"))
        self._set_combo(self._lang_dst, cfg.get("lang_dst", "pt"))
        self._set_combo(self._fmt, cfg.get("fmt", "docx"))
        self._set_combo(self._alinhamento, cfg.get("alinhamento", "original"))
        self._set_combo(self._tamanho_fonte, cfg.get("tamanho_fonte", 0))
        self._set_combo(self._fonte, cfg.get("fonte", ""))
        self._set_combo(self._modo_traducao, cfg.get("modo_traducao", "pagina"))
        self._set_combo(self._engine, cfg.get("engine", "google"))
        self._api_key_edit.setText(cfg.get("engine_api_key", ""))
        self._on_engine_changed()

    def _set_combo(self, combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    # ── Arquivos ─────────────────────────────────────────────────────────────
    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo", "", "PDF e EPUB (*.pdf *.epub)"
        )
        if path:
            self._path_edit.setText(path)
            self._current_book_id = None
            self._update_fmt_for_file(path)
            self._update_output_ext()

    def _update_fmt_for_file(self, path: str) -> None:
        is_epub = path.lower().endswith(".epub")
        current_data = self._fmt.currentData()
        self._fmt.blockSignals(True)
        self._fmt.clear()
        formats = FORMATS_EPUB if is_epub else FORMATS_PDF
        for label, code in formats:
            self._fmt.addItem(label, code)
        self._set_combo(self._fmt, current_data)
        self._fmt.blockSignals(False)

        if is_epub:
            self._page_label.setText("Capítulos:")
            tooltip = (
                "EPUBs são divididos em capítulos, não páginas físicas.\n"
                "Selecione o intervalo de capítulos a traduzir.\n"
                "O número de páginas do arquivo final pode ser diferente."
            )
            self._page_info_icon.setToolTip(tooltip)
            self._page_info_icon.show()
        else:
            self._page_label.setText("Páginas:")
            self._page_info_icon.hide()

    def _update_output_ext(self) -> None:
        pdf = self._path_edit.text().strip()
        if not pdf:
            return
        base = os.path.splitext(pdf)[0]
        if base.endswith("_traduzido"):
            base = base[:-len("_traduzido")]
        fmt = self._fmt.currentData() or "docx"
        self._out_edit.setText(f"{base}_traduzido.{fmt}")

    def _browse_output(self) -> None:
        fmt = self._fmt.currentData()
        filters = {
            "docx": "Word (*.docx)", "pdf": "PDF (*.pdf)",
            "txt": "Texto (*.txt)", "md": "Markdown (*.md)",
            "epub": "EPUB (*.epub)",
        }
        path, _ = QFileDialog.getSaveFileName(self, "Salvar como", "", filters.get(fmt, ""))
        if path:
            self._out_edit.setText(path)

    # ── Fila ─────────────────────────────────────────────────────────────────
    def _add_to_queue(self) -> None:
        file_path = self._path_edit.text().strip()
        output_path = self._out_edit.text().strip()
        if not file_path or not output_path:
            return

        settings = {
            "pag_ini": self._pag_ini.value(),
            "pag_fim": self._pag_fim.value(),
            "modo": "novo",
            "lang_src": self._lang_src.currentData(),
            "lang_dst": self._lang_dst.currentData(),
            "fmt": self._fmt.currentData(),
            "alinhamento": self._alinhamento.currentData(),
            "tamanho_fonte": self._tamanho_fonte.currentData() or None,
            "fonte": self._fonte.currentData() or None,
            "modo_traducao": self._modo_traducao.currentData(),
            "glossario": [],
            "engine": self._engine.currentData(),
            "engine_api_key": self._api_key_edit.text().strip() or None,
        }

        self._q.add(
            file_path=file_path,
            output_path=output_path,
            settings=settings,
            book_id=self._current_book_id,
            file_name=os.path.basename(file_path),
        )

        self._path_edit.clear()
        self._out_edit.clear()
        self._current_book_id = None
        self.go_to_queue.emit()
