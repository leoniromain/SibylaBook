from __future__ import annotations
import os
import subprocess
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from sibyla.qt.core.queue_manager import QueueManager, TranslationJob


def _reveal_in_folder(path: str) -> None:
    """Abre o gerenciador de arquivos mostrando o arquivo."""
    if not os.path.exists(path):
        path = os.path.dirname(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])
    except Exception:
        pass

_DOT_COLOR = {
    "queued":  "#94a3b8",
    "running": "#2563eb",
    "paused":  "#f59e0b",
    "done":    "#16a34a",
    "error":   "#dc2626",
}


class _JobCard(QFrame):
    pause_requested  = Signal(str)
    resume_requested = Signal(str)
    cancel_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, job: TranslationJob, parent=None) -> None:
        super().__init__(parent)
        self._job_id = job.id
        self._expanded = job.status == "running"
        self.setObjectName("job_card_queue")
        self._build(job)

    def _build(self, job: TranslationJob) -> None:
        self.setStyleSheet("""
            QFrame#job_card_queue {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(8)

        # ── Top row ──────────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(10)

        dot = QLabel("●")
        dot.setFixedWidth(14)
        dot.setStyleSheet(f"color: {_DOT_COLOR.get(job.status, '#64748b')}; font-size: 11px;")
        top.addWidget(dot)

        name = QLabel(job.file_name)
        name.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")
        name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top.addWidget(name, 1)

        status_lbl = QLabel(job.status_label())
        status_lbl.setStyleSheet(
            f"font-size: 11px; color: {_DOT_COLOR.get(job.status, '#64748b')}; "
            "font-weight: 500;"
        )
        top.addWidget(status_lbl)

        # Botões de ação
        if job.status == "running":
            pause_btn = QPushButton("Pausar")
            pause_btn.setObjectName("btn_secondary")
            pause_btn.setFixedHeight(28)
            pause_btn.clicked.connect(lambda: self.pause_requested.emit(self._job_id))
            top.addWidget(pause_btn)

            cancel_btn = QPushButton("Cancelar")
            cancel_btn.setObjectName("btn_danger")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self._job_id))
            top.addWidget(cancel_btn)

        elif job.status == "paused":
            folder_btn = QPushButton("Ver na pasta")
            folder_btn.setObjectName("btn_secondary")
            folder_btn.setFixedHeight(28)
            _path = job.output_path
            folder_btn.clicked.connect(lambda: _reveal_in_folder(_path))
            top.addWidget(folder_btn)

            resume_btn = QPushButton("Retomar")
            resume_btn.setObjectName("btn_primary")
            resume_btn.setFixedHeight(28)
            resume_btn.clicked.connect(lambda: self.resume_requested.emit(self._job_id))
            top.addWidget(resume_btn)

            cancel_btn = QPushButton("Cancelar")
            cancel_btn.setObjectName("btn_danger")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self._job_id))
            top.addWidget(cancel_btn)

        elif job.status == "queued":
            cancel_btn = QPushButton("Remover")
            cancel_btn.setObjectName("btn_secondary")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self._job_id))
            top.addWidget(cancel_btn)

        elif job.status == "done":
            folder_btn = QPushButton("Ver na pasta")
            folder_btn.setObjectName("btn_secondary")
            folder_btn.setFixedHeight(28)
            _path = job.output_path
            folder_btn.clicked.connect(lambda: _reveal_in_folder(_path))
            top.addWidget(folder_btn)

            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("btn_secondary")
            remove_btn.setFixedSize(28, 28)
            remove_btn.setToolTip("Remover da lista")
            remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._job_id))
            top.addWidget(remove_btn)

        else:  # error
            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("btn_secondary")
            remove_btn.setFixedSize(28, 28)
            remove_btn.setToolTip("Remover da lista")
            remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._job_id))
            top.addWidget(remove_btn)

        outer.addLayout(top)

        # ── Progress bar ─────────────────────────────────────────────────────
        if job.status == "running" and job.total > 0:
            bar = QProgressBar()
            bar.setRange(0, job.total)
            bar.setValue(job.page)
            bar.setFixedHeight(5)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { border:none; border-radius:2px; background:#e2e8f0; }
                QProgressBar::chunk { border-radius:2px; background:#2563eb; }
            """)
            outer.addWidget(bar)
        elif job.status == "paused":
            bar = QProgressBar()
            bar.setRange(0, max(job.total, 1))
            bar.setValue(job.last_page)
            bar.setFixedHeight(5)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { border:none; border-radius:2px; background:#e2e8f0; }
                QProgressBar::chunk { border-radius:2px; background:#f59e0b; }
            """)
            outer.addWidget(bar)
        elif job.status == "done":
            bar = QProgressBar()
            bar.setRange(0, 1)
            bar.setValue(1)
            bar.setFixedHeight(5)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { border:none; border-radius:2px; background:#e2e8f0; }
                QProgressBar::chunk { border-radius:2px; background:#16a34a; }
            """)
            outer.addWidget(bar)

        # ── Log (expansível) ─────────────────────────────────────────────────
        if job.log_lines or job.status in ("running", "paused"):
            toggle_row = QHBoxLayout()
            self._log_toggle = QPushButton(
                "▼ Ocultar log" if self._expanded else "▶ Ver log"
            )
            self._log_toggle.setFlat(True)
            self._log_toggle.setStyleSheet(
                "color: #64748b; font-size: 11px; text-align: left; border: none; padding: 0;"
            )
            self._log_toggle.clicked.connect(self._toggle_log)
            toggle_row.addWidget(self._log_toggle)
            toggle_row.addStretch()

            if job.status == "done" and job.output_path if hasattr(job, 'output_path') else False:
                pass
            outer.addLayout(toggle_row)

            self._log_box = QTextEdit()
            self._log_box.setReadOnly(True)
            self._log_box.setFixedHeight(140)
            self._log_box.setStyleSheet("""
                QTextEdit {
                    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
                    font-size: 11px;
                    background: #0f172a;
                    color: #94a3b8;
                    border-radius: 6px;
                    padding: 8px;
                    border: none;
                }
            """)
            if job.log_lines:
                self._log_box.setPlainText("\n".join(job.log_lines))
                # scroll to bottom
                sb = self._log_box.verticalScrollBar()
                sb.setValue(sb.maximum())

            if job.status == "error" and job.message:
                self._log_box.append(f"\n✗ {job.message}")

            self._log_box.setVisible(self._expanded)
            outer.addWidget(self._log_box)
        else:
            self._log_box = None
            self._log_toggle = None

    def _toggle_log(self) -> None:
        if self._log_box is None:
            return
        self._expanded = not self._expanded
        self._log_box.setVisible(self._expanded)
        self._log_toggle.setText("▼ Ocultar log" if self._expanded else "▶ Ver log")


class QueueView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._q = QueueManager.instance()
        self._q.jobs_changed.connect(self._refresh)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("library_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 24, 32, 16)
        header_layout.setSpacing(16)

        title = QLabel("Fila de Tradução")
        title.setObjectName("page_title")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._count_label = QLabel("")
        self._count_label.setObjectName("library_count")
        header_layout.addWidget(self._count_label)

        clear_btn = QPushButton("Limpar concluídos")
        clear_btn.setObjectName("btn_secondary")
        clear_btn.clicked.connect(self._q.clear_finished)
        header_layout.addWidget(clear_btn)

        root.addWidget(header)

        # Lista de jobs
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(32, 24, 32, 32)
        self._list_layout.setSpacing(12)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll, 1)

        # Estado vazio
        self._empty = QLabel("Nenhuma tradução na fila.\nUse a tela 'Traduzir' para adicionar arquivos.")
        self._empty.setObjectName("empty_label")
        self._empty.setAlignment(Qt.AlignCenter)
        root.addWidget(self._empty)
        self._empty.hide()

    def _refresh(self) -> None:
        jobs = self._q.jobs()

        # Recria os cards
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not jobs:
            self._scroll.hide()
            self._empty.show()
            self._count_label.setText("")
            return

        self._empty.hide()
        self._scroll.show()

        active = sum(1 for j in jobs if j.status in ("queued", "running"))
        total = len(jobs)
        parts = []
        if active:
            parts.append(f"{active} em andamento")
        done = sum(1 for j in jobs if j.status == "done")
        if done:
            parts.append(f"{done} concluído{'s' if done > 1 else ''}")
        self._count_label.setText("  ·  ".join(parts) if parts else f"{total} job{'s' if total > 1 else ''}")

        for job in jobs:
            card = _JobCard(job)
            card.pause_requested.connect(self._q.pause)
            card.resume_requested.connect(self._q.resume)
            card.cancel_requested.connect(self._q.cancel)
            card.remove_requested.connect(self._q.remove_job)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
