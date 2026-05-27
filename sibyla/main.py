from __future__ import annotations
import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QIcon, QPixmap

from sibyla.qt.main_window import MainWindow
from sibyla.qt.styles import get_stylesheet

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Sibyla Translate")
    app.setOrganizationName("Sibyla")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    saved_theme = QSettings("Sibyla", "SibylaTranslate").value("theme", "dark")
    app.setStyleSheet(get_stylesheet(saved_theme))

    icon_path = os.path.join(_ASSETS, "logo_square.png")
    if not os.path.isfile(icon_path):
        icon_path = os.path.join(_ASSETS, "logo.png")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from sibyla.qt.views.wizard import WelcomeWizard, should_show_wizard
    if should_show_wizard():
        wiz = WelcomeWizard(app)
        wiz.exec()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
