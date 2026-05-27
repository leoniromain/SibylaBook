from __future__ import annotations
from sibyla.core import history as hist_svc
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt


COLUMNS = ["Data", "PDF", "Saída", "De", "Para", "Formato", "Páginas", "Duração"]


class HistoryView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(20)

        header_row = QHBoxLayout()
        title = QLabel("Histórico de Traduções")
        title.setObjectName("page_title")
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = QPushButton("Atualizar")
        refresh_btn.setObjectName("btn_secondary")
        refresh_btn.clicked.connect(self._load)
        clear_btn = QPushButton("Limpar histórico")
        clear_btn.setObjectName("btn_danger")
        clear_btn.clicked.connect(self._clear)
        header_row.addWidget(refresh_btn)
        header_row.addWidget(clear_btn)
        root.addLayout(header_row)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        root.addWidget(self._table)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        root.addWidget(self._status)

    def _load(self) -> None:
        try:
            entries = hist_svc.load()
        except Exception as e:
            self._status.setText(f"Erro ao carregar histórico: {e}")
            return

        self._table.setRowCount(0)
        for entry in entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            duracao = f"{entry.get('duracao_s', 0)}s" if entry.get("duracao_s") else "—"
            pages = f"{entry.get('pag_ini', 1)}–{entry.get('pag_fim', '?')}"
            values = [
                entry.get("data_iso", ""),
                entry.get("pdf", ""),
                entry.get("saida", ""),
                entry.get("lang_src", ""),
                entry.get("lang_dst", ""),
                entry.get("fmt", ""),
                pages,
                duracao,
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self._table.setItem(row, col, item)

        count = len(entries)
        self._status.setText(f"{count} entrada(s) no histórico")

    def _clear(self) -> None:
        reply = QMessageBox.question(
            self, "Limpar histórico",
            "Deseja apagar todo o histórico de traduções?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            hist_svc.clear()
            self._load()
        except Exception as e:
            self._status.setText(f"Erro ao limpar: {e}")
