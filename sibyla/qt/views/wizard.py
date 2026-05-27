from __future__ import annotations
import os
import json
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QComboBox, QApplication,
    QStackedWidget, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPainterPath, QPen

# Same language list as translate_view.py (excluding "auto" for dest)
LANGUAGES = [
    ("Detectar automaticamente", "auto"),
    ("Inglês", "en"),
    ("Português", "pt"),
    ("Espanhol", "es"),
    ("Francês", "fr"),
    ("Alemão", "de"),
    ("Italiano", "it"),
    ("Japonês", "ja"),
    ("Chinês (Simplificado)", "zh-cn"),
    ("Russo", "ru"),
]

LANGUAGES_DST = [l for l in LANGUAGES if l[1] != "auto"]

_DIALOG_STYLE = """
QDialog {
    background-color: #f8fafc;
    border-radius: 16px;
}
QWidget {
    font-family: -apple-system, "SF Pro Text", "Segoe UI", sans-serif;
    color: #1e293b;
    background-color: transparent;
}
QLabel {
    background: transparent;
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 14px;
    color: #1e293b;
    font-size: 14px;
    min-height: 20px;
}
QLineEdit:focus {
    border: 1.5px solid #2563eb;
}
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 14px;
    color: #1e293b;
    font-size: 14px;
    min-height: 20px;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
}
QPushButton#wizard_primary {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 28px;
    font-size: 15px;
    font-weight: 600;
    min-width: 140px;
}
QPushButton#wizard_primary:hover {
    background-color: #1d4ed8;
}
QPushButton#wizard_primary:pressed {
    background-color: #1e40af;
}
QPushButton#wizard_primary:disabled {
    background-color: #93c5fd;
}
QPushButton#wizard_back {
    background: transparent;
    color: #64748b;
    border: none;
    font-size: 13px;
    padding: 4px 8px;
    text-decoration: underline;
}
QPushButton#wizard_back:hover {
    color: #2563eb;
}
QPushButton#wizard_browse {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#wizard_browse:hover {
    background-color: #e2e8f0;
}
"""


class _DotsWidget(QWidget):
    """Small row of progress dots."""

    def __init__(self, count: int, parent=None) -> None:
        super().__init__(parent)
        self._count = count
        self._active = 0
        self.setFixedHeight(18)

    def set_active(self, index: int) -> None:
        self._active = index
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        dot_r = 6
        gap = 16
        total_w = self._count * (dot_r * 2) + (self._count - 1) * gap
        x0 = (self.width() - total_w) // 2
        y = self.height() // 2
        for i in range(self._count):
            cx = x0 + i * (dot_r * 2 + gap) + dot_r
            if i == self._active:
                p.setBrush(QColor("#2563eb"))
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - dot_r, y - dot_r, dot_r * 2, dot_r * 2)
            elif i < self._active:
                p.setBrush(QColor("#93c5fd"))
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - dot_r, y - dot_r, dot_r * 2, dot_r * 2)
            else:
                p.setBrush(QColor("#e2e8f0"))
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - dot_r, y - dot_r, dot_r * 2, dot_r * 2)
        p.end()


class _CheckmarkWidget(QWidget):
    """Animated green checkmark drawn with QPainter."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self._progress = 0.0

    def set_progress(self, v: float) -> None:
        self._progress = v
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy, r = self.width() // 2, self.height() // 2, 34

        # Circle
        p.setBrush(QColor("#dcfce7"))
        p.setPen(QPen(QColor("#16a34a"), 3))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Checkmark (two segments totaling progress)
        if self._progress > 0:
            pen = QPen(QColor("#16a34a"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)

            # Checkmark points: left tick then up-right
            p1 = (cx - 14, cy)
            p2 = (cx - 3, cy + 11)
            p3 = (cx + 16, cy - 10)

            # Segment 1: p1 -> p2, length fraction
            seg1_frac = min(1.0, self._progress * 2)
            if seg1_frac > 0:
                ex = p1[0] + (p2[0] - p1[0]) * seg1_frac
                ey = p1[1] + (p2[1] - p1[1]) * seg1_frac
                p.drawLine(p1[0], p1[1], int(ex), int(ey))

            # Segment 2: p2 -> p3
            if self._progress > 0.5:
                seg2_frac = min(1.0, (self._progress - 0.5) * 2)
                ex2 = p2[0] + (p3[0] - p2[0]) * seg2_frac
                ey2 = p2[1] + (p3[1] - p2[1]) * seg2_frac
                p.drawLine(p2[0], p2[1], int(ex2), int(ey2))

        p.end()


def _make_label(text: str, size: int = 13, bold: bool = False,
                color: str = "#1e293b", wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(size)
    if bold:
        f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    if wrap:
        lbl.setWordWrap(True)
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


class WelcomeWizard(QDialog):
    def __init__(self, app: "QApplication", parent=None) -> None:
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self._app = app
        self._current_step = 0
        self._library_path = ""
        self._lang_src = "auto"
        self._lang_dst = "pt"

        self.setStyleSheet(_DIALOG_STYLE)
        self.setMinimumSize(560, 480)
        self.setModal(True)

        self._build_ui()
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 36)
        root.setSpacing(0)

        # Dots
        self._dots = _DotsWidget(4)
        root.addWidget(self._dots)
        root.addSpacing(28)

        # Stack of steps
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step_welcome())
        self._stack.addWidget(self._build_step_library())
        self._stack.addWidget(self._build_step_languages())
        self._stack.addWidget(self._build_step_done())
        root.addWidget(self._stack, 1)

        root.addSpacing(24)

        # Bottom nav row
        nav = QHBoxLayout()
        nav.setSpacing(16)

        self._back_btn = QPushButton("← Voltar")
        self._back_btn.setObjectName("wizard_back")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.hide()
        nav.addWidget(self._back_btn, 0, Qt.AlignLeft | Qt.AlignVCenter)

        nav.addStretch()

        self._next_btn = QPushButton("Começar →")
        self._next_btn.setObjectName("wizard_primary")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._next_btn, 0, Qt.AlignRight | Qt.AlignVCenter)

        root.addLayout(nav)

        self._goto_step(0)

    # ── Step builders ─────────────────────────────────────────────────────────

    def _build_step_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # Logo placeholder (large emoji / text)
        logo_lbl = QLabel("📚")
        logo_lbl.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(52)
        logo_lbl.setFont(f)
        logo_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(logo_lbl)

        title = _make_label("Sibyla", 30, bold=True, color="#0f172a")
        layout.addWidget(title)

        tagline = _make_label(
            "Sua biblioteca pessoal com tradução integrada.",
            14, color="#64748b", wrap=True,
        )
        layout.addWidget(tagline)

        return w

    def _build_step_library(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(16)

        title = _make_label("Onde guardar seus livros?", 20, bold=True, color="#0f172a")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = _make_label(
            "Escolha uma pasta onde o Sibyla armazenará\nsua biblioteca e os metadados dos livros.",
            13, color="#64748b", wrap=True,
        )
        layout.addWidget(desc)

        layout.addSpacing(12)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        self._lib_path_edit = QLineEdit()
        self._lib_path_edit.setPlaceholderText("Selecione uma pasta…")
        default_lib = os.path.join(os.path.expanduser("~"), "Sibyla Library")
        self._lib_path_edit.setText(default_lib)
        self._library_path = default_lib
        self._lib_path_edit.textChanged.connect(self._on_lib_path_changed)
        path_row.addWidget(self._lib_path_edit, 1)

        browse_btn = QPushButton("Procurar…")
        browse_btn.setObjectName("wizard_browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_library)
        path_row.addWidget(browse_btn)

        layout.addLayout(path_row)

        hint = _make_label(
            "A pasta será criada automaticamente caso não exista.",
            11, color="#94a3b8", wrap=True,
        )
        hint.setAlignment(Qt.AlignLeft)
        layout.addWidget(hint)

        return w

    def _build_step_languages(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(16)

        title = _make_label("Quais idiomas você usa mais?", 20, bold=True, color="#0f172a")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = _make_label(
            "Esses idiomas serão pré-selecionados ao traduzir.\nVocê pode mudar a qualquer momento.",
            13, color="#64748b", wrap=True,
        )
        layout.addWidget(desc)

        layout.addSpacing(12)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Source language
        src_row = QHBoxLayout()
        src_lbl = QLabel("Idioma de origem:")
        src_lbl.setStyleSheet("color: #475569; font-size: 13px; background: transparent;")
        src_lbl.setFixedWidth(160)
        src_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        src_row.addWidget(src_lbl)

        self._wiz_lang_src = QComboBox()
        for label, code in LANGUAGES:
            self._wiz_lang_src.addItem(label, code)
        # Default: auto
        self._wiz_lang_src.setCurrentIndex(0)
        self._wiz_lang_src.currentIndexChanged.connect(
            lambda: setattr(self, "_lang_src", self._wiz_lang_src.currentData())
        )
        src_row.addWidget(self._wiz_lang_src, 1)
        form_layout.addLayout(src_row)

        # Dest language
        dst_row = QHBoxLayout()
        dst_lbl = QLabel("Idioma de destino:")
        dst_lbl.setStyleSheet("color: #475569; font-size: 13px; background: transparent;")
        dst_lbl.setFixedWidth(160)
        dst_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dst_row.addWidget(dst_lbl)

        self._wiz_lang_dst = QComboBox()
        for label, code in LANGUAGES_DST:
            self._wiz_lang_dst.addItem(label, code)
        # Default: pt
        for i in range(self._wiz_lang_dst.count()):
            if self._wiz_lang_dst.itemData(i) == "pt":
                self._wiz_lang_dst.setCurrentIndex(i)
                break
        self._wiz_lang_dst.currentIndexChanged.connect(
            lambda: setattr(self, "_lang_dst", self._wiz_lang_dst.currentData())
        )
        dst_row.addWidget(self._wiz_lang_dst, 1)
        form_layout.addLayout(dst_row)

        layout.addWidget(form_widget)
        return w

    def _build_step_done(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self._checkmark = _CheckmarkWidget()
        layout.addWidget(self._checkmark, 0, Qt.AlignCenter)

        title = _make_label("Tudo configurado!", 22, bold=True, color="#0f172a")
        layout.addWidget(title)

        desc = _make_label(
            "Sua biblioteca está pronta.\nComece a importar seus livros e traduzir.",
            14, color="#64748b", wrap=True,
        )
        layout.addWidget(desc)

        return w

    # ── Navigation ────────────────────────────────────────────────────────────

    def _goto_step(self, step: int) -> None:
        self._current_step = step
        self._stack.setCurrentIndex(step)
        self._dots.set_active(step)

        # Back button
        self._back_btn.setVisible(step > 0)

        # Next button text
        texts = ["Começar →", "Continuar →", "Continuar →", "Abrir Sibyla"]
        self._next_btn.setText(texts[step])

        # On entering step 3, animate checkmark
        if step == 3:
            self._save_config()
            self._animate_checkmark()

    def _go_next(self) -> None:
        if self._current_step < 3:
            self._goto_step(self._current_step + 1)
        else:
            self.accept()

    def _go_back(self) -> None:
        if self._current_step > 0:
            self._goto_step(self._current_step - 1)

    # ── Library path ──────────────────────────────────────────────────────────

    def _on_lib_path_changed(self, text: str) -> None:
        self._library_path = text

    def _browse_library(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Escolher pasta da biblioteca",
            self._lib_path_edit.text() or os.path.expanduser("~"),
        )
        if path:
            self._lib_path_edit.setText(path)
            self._library_path = path

    # ── Config save ───────────────────────────────────────────────────────────

    def _save_config(self) -> None:
        # Save translation config
        try:
            from sibyla.core.config import AppConfig
            cfg = AppConfig.load()
            cfg.set_many({"lang_src": self._lang_src, "lang_dst": self._lang_dst})
            lib_path = self._library_path.strip()
            if lib_path:
                os.makedirs(lib_path, exist_ok=True)
                cfg.set("library_path", lib_path)
        except Exception:
            pass

    # ── Checkmark animation ───────────────────────────────────────────────────

    def _animate_checkmark(self) -> None:
        from PySide6.QtCore import QTimer

        self._check_progress = 0.0
        self._check_timer = QTimer(self)
        self._check_timer.setInterval(16)  # ~60fps

        def _tick() -> None:
            self._check_progress = min(1.0, self._check_progress + 0.04)
            self._checkmark.set_progress(self._check_progress)
            if self._check_progress >= 1.0:
                self._check_timer.stop()

        self._check_timer.timeout.connect(_tick)
        self._check_timer.start()

    # ── Drop shadow via paintEvent ────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        p.fillPath(path, QColor("#f8fafc"))
        p.end()


# ── Detection logic ──────────────────────────────────────────────────────────

def should_show_wizard() -> bool:
    from sibyla.core.config import AppConfig
    try:
        path = AppConfig.load().get("library_path", "")
        return not path or not os.path.isdir(path)
    except Exception:
        return False
