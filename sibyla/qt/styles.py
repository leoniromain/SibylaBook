def get_stylesheet(theme: str = "default") -> str:
    # "default" is treated as "dark" (legacy alias)
    return _LIGHT_STYLESHEET if theme == "light" else _DARK_STYLESHEET


# ── backwards compat alias ────────────────────────────────────────────────────
STYLESHEET = """
/* ── Global ── */
QWidget {
    font-family: -apple-system, "SF Pro Text", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1e293b;
    background-color: transparent;
}

QMainWindow, QDialog {
    background-color: #f1f5f9;
}

/* ── Top navigation bar ── */
QWidget#main_topbar {
    background-color: #0f172a;
    border: none;
}
QLabel#topbar_logo {
    background: transparent;
}
QFrame#topbar_vsep {
    color: #1e293b;
    background-color: #1e293b;
    max-width: 1px;
}
QFrame#topbar_hsep {
    color: #1e293b;
    background-color: #1e293b;
    max-height: 1px;
}
QPushButton#topnav_btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
}
QPushButton#topnav_btn:hover {
    background-color: #1e293b;
    color: #e2e8f0;
}
QPushButton#topnav_btn[active="true"] {
    background-color: #1d4ed8;
    color: #ffffff;
}
QLabel#version {
    color: #334155;
    font-size: 11px;
    padding: 4px 8px;
}
QPushButton#theme_toggle_btn {
    background: transparent;
    border: 1px solid #1e293b;
    border-radius: 10px;
    font-size: 17px;
    padding: 0;
    color: #e2e8f0;
}
QPushButton#theme_toggle_btn:hover {
    background: #1e293b;
    border-color: #334155;
}
QPushButton#theme_toggle_btn:pressed {
    background: #0f172a;
}

/* ── Persistent library side panel ── */
QWidget#lib_side_panel {
    background-color: #0f172a;
}
QWidget#lib_panel_header {
    background-color: #0f172a;
}
QLabel#lib_panel_title {
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}
QScrollArea#lib_panel_scroll {
    background-color: #0f172a;
}
QWidget#lib_panel_container {
    background-color: #0f172a;
}
/* Tag group rows */
QFrame#tag_group_row {
    background: transparent;
    border: none;
    border-radius: 6px;
    margin: 0 8px;
}
QFrame#tag_group_row:hover {
    background-color: #1e293b;
}
QFrame#tag_group_row[active="true"] {
    background-color: #1e3a5f;
}
QLabel#tag_group_label {
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}
QFrame#tag_group_row[active="true"] QLabel#tag_group_label {
    color: #f8fafc;
    font-weight: 600;
}
QLabel#tag_group_count {
    color: #475569;
    font-size: 11px;
    background: transparent;
}
QFrame#tag_group_row[active="true"] QLabel#tag_group_count {
    color: #93c5fd;
}
/* inner separator between groups */
QFrame#panel_inner_sep {
    color: #1e293b;
    background-color: #1e293b;
    max-height: 1px;
    margin: 4px 14px;
}
QFrame#panel_sep {
    color: #1e293b;
    background-color: #1e293b;
    max-width: 1px;
}
/* "+" add button in panel header */
QPushButton#lib_panel_add_btn {
    background: #1e293b;
    color: #94a3b8;
    border: none;
    border-radius: 5px;
    font-size: 16px;
    font-weight: 400;
    padding: 0;
}
QPushButton#lib_panel_add_btn:hover {
    background: #334155;
    color: #f8fafc;
}
/* Sidebar divider row */
QFrame#sidebar_divider_row {
    background: transparent;
    border: none;
    margin: 2px 8px;
}
QLabel#divider_label {
    color: #475569;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
}
QFrame#divider_line {
    color: #1e293b;
    background: #1e293b;
    max-height: 1px;
}
/* Group dialog */
QLabel#dialog_type_badge {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
QLabel#dialog_field_label {
    color: #334155;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}
QLabel#dialog_hint {
    color: #94a3b8;
    font-size: 11px;
    background: transparent;
}

/* ── Content area ── */
QFrame#content {
    background-color: #f1f5f9;
}

/* ── Cards (GroupBox) ── */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 10px;
    padding: 16px 16px 16px 16px;
    font-weight: 600;
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
    top: -1px;
    background-color: #ffffff;
}

/* ── Labels ── */
QLabel {
    color: #334155;
    background: transparent;
}
QLabel#page_title {
    font-size: 22px;
    font-weight: 700;
    color: #0f172a;
}

/* ── Inputs ── */
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1e293b;
    selection-background-color: #2563eb;
    font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1.5px solid #2563eb;
    outline: none;
}
QLineEdit:read-only {
    background-color: #f8fafc;
    color: #64748b;
}
QLineEdit:placeholder {
    color: #94a3b8;
}

QSpinBox::up-button, QSpinBox::down-button {
    width: 18px;
    border: none;
    background: transparent;
}

QComboBox {
    padding-right: 28px;
    color: #1e293b;
    background-color: #ffffff;
}
QComboBox:disabled {
    color: #94a3b8;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
    padding: 4px;
}

/* ── Buttons ── */
QPushButton {
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    border: none;
}

QPushButton#btn_primary {
    background-color: #2563eb;
    color: #ffffff;
}
QPushButton#btn_primary:hover {
    background-color: #1d4ed8;
}
QPushButton#btn_primary:pressed {
    background-color: #1e40af;
}
QPushButton#btn_primary:disabled {
    background-color: #93c5fd;
    color: #ffffff;
}

QPushButton#btn_secondary {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
}
QPushButton#btn_secondary:hover {
    background-color: #e2e8f0;
}

QPushButton#btn_danger {
    background-color: transparent;
    color: #dc2626;
    border: 1px solid #fecaca;
}
QPushButton#btn_danger:hover {
    background-color: #fef2f2;
}

/* ── Checkbox ── */
QCheckBox {
    color: #334155;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #cbd5e1;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

/* ── Progress bar ── */
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #e2e8f0;
    height: 8px;
    text-align: center;
    font-size: 11px;
    color: transparent;
}
QProgressBar::chunk {
    border-radius: 6px;
    background-color: #2563eb;
}

/* ── Log / TextEdit ── */
QTextEdit {
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    font-size: 12px;
    background-color: #0f172a;
    color: #94a3b8;
    border-radius: 8px;
    padding: 10px;
    border: none;
}

/* ── Table ── */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    gridline-color: #f1f5f9;
    font-size: 12px;
}
QTableWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #f1f5f9;
}
QTableWidget::item:selected {
    background-color: #eff6ff;
    color: #1e293b;
}
QHeaderView::section {
    background-color: #f8fafc;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

/* ── Bottom panel ── */
QWidget#bottom_panel {
    background-color: #f1f5f9;
    border-top: 1px solid #e2e8f0;
}

/* ── ScrollBar ── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 3px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #e2e8f0;
    width: 1px;
}

/* ── Context menu ── */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 6px 4px;
}
QMenu::item {
    padding: 8px 20px;
    border-radius: 6px;
    color: #1e293b;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}
QMenu::item:disabled {
    color: #94a3b8;
}
QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 8px;
}

/* ── List ── */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 4px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #334155;
}
QListWidget::item:hover {
    background-color: #f8fafc;
}
QListWidget::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}

/* ── ScrollArea ── */
QScrollArea {
    border: none;
    background: transparent;
}

/* ── Biblioteca ── */
QWidget#library_header {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
}

QWidget#search_container {
    background-color: #f8fafc;
    padding-top: 8px;
    border-bottom: 1px solid #e2e8f0;
}

QLineEdit#search_input {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    color: #334155;
}
QLineEdit#search_input:focus {
    border-color: #6366f1;
}

QPushButton#filter_btn {
    background-color: transparent;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 5px 14px;
    color: #64748b;
    font-size: 12px;
}
QPushButton#filter_btn:hover {
    background-color: #f1f5f9;
    color: #334155;
}
QPushButton#filter_btn[active="true"] {
    background-color: #6366f1;
    border-color: #6366f1;
    color: #ffffff;
}

QWidget#grid_container {
    background-color: #f1f5f9;
}

QLabel#library_count {
    color: #94a3b8;
    font-size: 12px;
}

QLabel#empty_label {
    color: #94a3b8;
    font-size: 15px;
    background: transparent;
}

/* ── Book Card ── */
QFrame#book_card {
    background-color: #ffffff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    padding: 0px;
}
QFrame#book_card:hover {
    border-color: #6366f1;
    background-color: #fafafa;
}

QLabel#book_cover {
    border-radius: 8px 8px 0 0;
    background-color: #f1f5f9;
}

QLabel#book_title {
    color: #1e293b;
    font-size: 12px;
    font-weight: 600;
    padding: 0 8px;
}

QLabel#book_author {
    color: #64748b;
    font-size: 11px;
    padding: 0 8px;
}

QLabel#badge_pdf {
    color: #dc2626;
    font-size: 10px;
    font-weight: 700;
    padding: 0 8px 4px 8px;
}
QLabel#badge_epub {
    color: #2563eb;
    font-size: 10px;
    font-weight: 700;
    padding: 0 8px 4px 8px;
}

/* ── Info icon ── */
QLabel#info_icon {
    background-color: #f59e0b;
    color: #ffffff;
    border-radius: 8px;
    font-size: 10px;
    font-weight: 700;
}

/* ── Queue badge (sidebar) ── */
QPushButton#queue_badge {
    background-color: #1e3a5f;
    color: #93c5fd;
    border: 1px solid #1d4ed8;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    text-align: left;
}
QPushButton#queue_badge:hover {
    background-color: #1d4ed8;
    color: #ffffff;
}

/* ── Import status bar ── */
QLabel#import_status {
    background-color: #eff6ff;
    color: #1d4ed8;
    font-size: 12px;
    font-weight: 500;
    border-bottom: 1px solid #bfdbfe;
}

/* ── Separador sidebar ── */
QFrame#sidebar_sep {
    color: #1e293b;
    background-color: #1e293b;
    max-height: 1px;
    margin: 0 4px;
}

/* ── Star rating ── */
QLabel#book_rating {
    color: #f59e0b;
    font-size: 10px;
}

/* ── Read status badges ── */
QLabel#status_read {
    color: #16a34a;
    font-size: 9px;
    font-weight: 700;
}
QLabel#status_reading {
    color: #2563eb;
    font-size: 9px;
    font-weight: 700;
}

/* ── Tag chips ── */
QWidget#tag_chips_container {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
}

QPushButton#tag_chip {
    background: #e2e8f0;
    color: #475569;
    border: none;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}
QPushButton#tag_chip:hover {
    background: #cbd5e1;
}
QPushButton#tag_chip[active="true"] {
    background: #2563eb;
    color: white;
}

/* ── Sort combobox ── */
QComboBox#sort_combo {
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 8px;
}

/* ── Main toolbar ── */
QWidget#main_toolbar {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    padding: 0 32px;
}
QPushButton#toolbar_btn {
    background: transparent;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    color: #475569;
}
QPushButton#toolbar_btn:hover {
    background: #f1f5f9;
}
QPushButton#toolbar_btn:disabled {
    color: #cbd5e1;
    border-color: #f1f5f9;
}
QPushButton#toolbar_btn_danger {
    background: transparent;
    border: 1px solid #fecaca;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    color: #dc2626;
}
QPushButton#toolbar_btn_danger:hover {
    background: #fef2f2;
}
QPushButton#toolbar_btn_danger:disabled {
    color: #fca5a5;
    border-color: #fee2e2;
}
QFrame#toolbar_sep {
    color: #e2e8f0;
}

/* ── Reader ── */
QWidget#reader_topbar {
    background: #1e293b;
    border-bottom: 1px solid #334155;
}
QLabel#reader_title {
    color: #f8fafc;
    font-size: 14px;
    font-weight: 600;
}
QLabel#reader_page_info {
    color: #94a3b8;
    font-size: 12px;
}
QPushButton#reader_close_btn {
    background: transparent;
    color: #94a3b8;
    border: none;
    font-size: 13px;
    padding: 6px 12px;
}
QPushButton#reader_close_btn:hover {
    color: #f8fafc;
}
QPushButton#reader_nav_btn {
    background: #334155;
    color: #e2e8f0;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
}
QPushButton#reader_nav_btn:hover {
    background: #475569;
}
QPushButton#reader_nav_btn:disabled {
    background: #1e293b;
    color: #475569;
}
QWidget#reader_content_area {
    background: #0f172a;
}
QTextEdit#epub_reader_text {
    background: #fafaf8;
    color: #1a1a1a;
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 16px;
    border: none;
    padding: 40px 80px;
}
QPushButton#reader_detach_btn {
    background: transparent;
    color: #64748b;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 14px;
    padding: 3px 8px;
}
QPushButton#reader_detach_btn:hover {
    color: #f8fafc;
    border-color: #475569;
}

/* ── Page jump input ── */
QWidget#reader_page_jump {
    background: transparent;
}
QLineEdit#reader_page_input {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-size: 13px;
    font-weight: 500;
    padding: 4px 6px;
}
QLineEdit#reader_page_input:focus {
    border-color: #3b82f6;
}

/* ── PDF page labels ── */
QLabel#pdf_page_label {
    background: #ffffff;
    border-radius: 4px;
}


/* ── Main Tabs ── */
QTabWidget#main_tabs {
    background: transparent;
}
QTabWidget#main_tabs::pane {
    border: none;
    background: #f1f5f9;
    border-top: 1px solid #e2e8f0;
}
QTabWidget#main_tabs QTabBar {
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
}
QTabWidget#main_tabs QTabBar::tab {
    background: transparent;
    color: #94a3b8;
    padding: 8px 18px 9px 14px;
    margin: 6px 2px 0 2px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 7px 7px 0 0;
    font-size: 12px;
    font-weight: 500;
    min-width: 90px;
    max-width: 210px;
}
QTabWidget#main_tabs QTabBar::tab:selected {
    background: #ffffff;
    color: #0f172a;
    border-color: #e2e8f0;
    border-bottom: 2px solid #ffffff;
    font-weight: 600;
}
QTabWidget#main_tabs QTabBar::tab:hover:!selected {
    background: #f1f5f9;
    color: #475569;
}
QTabWidget#main_tabs QTabBar::close-button {
    subcontrol-position: right;
    width: 14px;
    height: 14px;
    margin-right: 2px;
}

/* ── Reader Tabs (legacy — kept for FloatingReader) ── */
QTabWidget#reader_tabs {
    background: #f1f5f9;
}
QTabWidget#reader_tabs::pane {
    border: none;
    background: #f1f5f9;
}
QTabWidget#reader_tabs QTabBar::tab {
    background: #1e293b;
    color: #94a3b8;
    border: none;
    border-right: 1px solid #0f172a;
    padding: 8px 16px;
    font-size: 12px;
    min-width: 80px;
    max-width: 180px;
}
QTabWidget#reader_tabs QTabBar::tab:selected {
    background: #334155;
    color: #f8fafc;
}
QTabWidget#reader_tabs QTabBar::tab:hover:!selected {
    background: #253447;
    color: #e2e8f0;
}
QTabWidget#reader_tabs QTabBar::close-button {
    subcontrol-position: right;
}

/* ══════════════════════════════════════════════════════════════
   NOTE CARDS
   ══════════════════════════════════════════════════════════════ */
QFrame#note_card {
    background-color: #ffffff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
}
QFrame#note_card:hover {
    border-color: #6366f1;
    background-color: #fafafa;
}
QLabel#note_cover {
    border-radius: 8px 8px 0 0;
    background: transparent;
}
QLabel#note_title {
    color: #1e293b;
    font-size: 12px;
    font-weight: 600;
    padding: 0 8px;
}
QLabel#note_tags_preview {
    color: #6366f1;
    font-size: 10px;
    font-weight: 500;
    padding: 0 8px;
}
QLabel#note_date {
    color: #94a3b8;
    font-size: 10px;
    padding: 0 8px 4px 8px;
}

/* ══════════════════════════════════════════════════════════════
   NOTE EDITOR
   ══════════════════════════════════════════════════════════════ */
QWidget#note_editor_header {
    background-color: #ffffff;
    border-bottom: 1px solid #f1f5f9;
}
QLineEdit#note_title_input {
    background: transparent;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    border-radius: 0;
    font-size: 18px;
    font-weight: 600;
    color: #0f172a;
    padding: 4px 0;
}
QLineEdit#note_title_input:focus {
    border-bottom: 2px solid #6366f1;
}
/* Tag editor */
QPushButton#note_tag_chip {
    background: #ede9fe;
    color: #6366f1;
    border: none;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
}
QPushButton#note_tag_chip:hover {
    background: #ddd6fe;
}
QLineEdit#note_tag_input {
    background: transparent;
    border: none;
    border-bottom: 1px dashed #cbd5e1;
    border-radius: 0;
    font-size: 12px;
    color: #64748b;
    padding: 2px 2px;
}
QLineEdit#note_tag_input:focus {
    border-bottom-color: #6366f1;
}
/* Toolbar */
QWidget#note_toolbar {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
}
QToolButton#note_tool_btn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 12px;
    color: #475569;
    min-width: 26px;
    min-height: 26px;
}
QToolButton#note_tool_btn:hover {
    background: #e2e8f0;
    color: #0f172a;
}
QToolButton#note_tool_btn:checked {
    background: #ede9fe;
    color: #6366f1;
    border-color: #c4b5fd;
}
QFrame#note_toolbar_sep {
    color: #e2e8f0;
    background: #e2e8f0;
    max-width: 1px;
    margin: 0 4px;
}
QComboBox#note_para_combo {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
    color: #334155;
}
/* Editor body */
QTextEdit#note_editor_body {
    background: #ffffff;
    color: #1e293b;
    border: none;
    font-family: -apple-system, "SF Pro Text", "Segoe UI", sans-serif;
    font-size: 14px;
    padding: 28px 80px;
    line-height: 1.7;
}
QFrame#note_editor_sep {
    color: #e2e8f0;
    background: #e2e8f0;
    max-height: 1px;
}
/* Status bar */
QWidget#note_status_bar {
    background: #f8fafc;
    border-top: 1px solid #f1f5f9;
}
QLabel#note_status_lbl {
    color: #94a3b8;
    font-size: 11px;
    background: transparent;
}
/* Notes view header */
QWidget#notes_header {
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
}

/* ── Library side tree ── */
QTreeWidget#lib_side_tree {
    background: #0f172a;
    color: #cbd5e1;
    border: none;
    font-size: 12px;
    outline: 0;
}
QTreeWidget#lib_side_tree::item {
    padding: 5px 6px;
    border-radius: 6px;
    color: #cbd5e1;
}
QTreeWidget#lib_side_tree::item:hover {
    background: #1e293b;
}
QTreeWidget#lib_side_tree::item:selected {
    background: #1e3a5f;
    color: #f8fafc;
}
QTreeWidget#lib_side_tree::branch {
    background: #0f172a;
}
QTreeWidget#lib_side_tree::branch:has-children:!has-siblings:closed,
QTreeWidget#lib_side_tree::branch:closed:has-children:has-siblings {
    color: #475569;
}
QTreeWidget#lib_side_tree::branch:open:has-children:!has-siblings,
QTreeWidget#lib_side_tree::branch:open:has-children:has-siblings {
    color: #475569;
}

/* ── Color picker popup ── */
QFrame#color_picker_popup {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
}
QWidget#color_picker_panel {
    background: transparent;
}
QFrame#color_picker_div {
    color: #e2e8f0;
    background: #e2e8f0;
    max-width: 1px;
}
QPushButton#color_picker_custom_btn {
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px 8px;
    color: #475569;
    font-size: 12px;
}
QPushButton#color_picker_custom_btn:hover {
    background: #f1f5f9;
    color: #1e293b;
}
"""


# ── Dark theme ────────────────────────────────────────────────────────────────

_DARK_STYLESHEET = STYLESHEET + """
/* ── Dark overrides ── */
QMainWindow, QDialog {
    background-color: #0f172a;
}

/* Dark main tabs */
QTabWidget#main_tabs::pane {
    background: #0f172a;
    border-top: 1px solid #1e293b;
}
QTabWidget#main_tabs QTabBar {
    background: #070d14;
    border-bottom: 1px solid #1e293b;
}
QTabWidget#main_tabs QTabBar::tab {
    background: transparent;
    color: #475569;
}
QTabWidget#main_tabs QTabBar::tab:selected {
    background: #0f172a;
    color: #f1f5f9;
    border-color: #1e293b;
    border-bottom: 2px solid #0f172a;
}
QTabWidget#main_tabs QTabBar::tab:hover:!selected {
    background: #111a28;
    color: #64748b;
}

QFrame#content {
    background-color: #0f172a;
}
QWidget#grid_container {
    background-color: #0f172a;
}
QWidget#library_header, QWidget#search_container, QWidget#tag_chips_container {
    background-color: #0f172a;
    border-color: #1e293b;
}
QFrame#book_card {
    background-color: #1e293b;
    border-color: #334155;
}
QFrame#book_card:hover {
    background-color: #253347;
    border-color: #3b82f6;
}
QLabel#book_title { color: #e2e8f0; }
QLabel#book_author { color: #64748b; }
QLabel#page_title { color: #f8fafc; }
QLabel#empty_label { color: #475569; }
QLabel#library_count { color: #475569; }
QGroupBox {
    background-color: #1e293b;
    border-color: #334155;
    color: #94a3b8;
}
QGroupBox::title { background-color: #1e293b; }
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #1e293b;
    border-color: #334155;
    color: #e2e8f0;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #3b82f6;
}
QLineEdit:read-only { background-color: #152032; color: #64748b; }
QComboBox QAbstractItemView {
    background-color: #1e293b;
    border-color: #334155;
    selection-background-color: #1d4ed8;
    color: #e2e8f0;
}
QPushButton#btn_secondary {
    background-color: #1e293b;
    color: #94a3b8;
    border-color: #334155;
}
QPushButton#btn_secondary:hover { background-color: #253347; }
QWidget#main_toolbar { background-color: #0a0f1a; border-color: #1e293b; }
QPushButton#toolbar_btn { color: #64748b; border-color: #1e293b; }
QPushButton#toolbar_btn:hover { background: #1e293b; }
QScrollArea { background: #0f172a; }
QWidget#bottom_panel { background-color: #0f172a; border-color: #1e293b; }
QTableWidget {
    background-color: #1e293b;
    border-color: #334155;
    gridline-color: #0f172a;
}
QTableWidget::item { border-color: #0f172a; }
QTableWidget::item:selected { background-color: #1d4ed8; color: #f8fafc; }
QHeaderView::section {
    background-color: #152032;
    border-color: #334155;
    color: #64748b;
}
QListWidget {
    background-color: #1e293b;
    border-color: #334155;
}
QListWidget::item { color: #cbd5e1; }
QListWidget::item:hover { background: #253347; }
QListWidget::item:selected { background: #1d4ed8; color: #f8fafc; }
QWidget#main_topbar { background-color: #070d14; }

/* Dark note cards */
QFrame#note_card {
    background-color: #1e293b;
    border-color: #334155;
}
QFrame#note_card:hover {
    background-color: #253347;
    border-color: #6366f1;
}
QLabel#note_title { color: #e2e8f0; }
QLabel#note_date  { color: #475569; }

/* Dark note editor */
QWidget#note_editor_header { background: #0f172a; border-color: #1e293b; }
QLineEdit#note_title_input  { color: #f1f5f9; border-bottom-color: #334155; }
QLineEdit#note_title_input:focus { border-bottom-color: #6366f1; }
QPushButton#note_tag_chip   { background: #312e81; color: #a5b4fc; }
QPushButton#note_tag_chip:hover { background: #3730a3; }
QLineEdit#note_tag_input    { color: #94a3b8; border-bottom-color: #334155; }
QWidget#note_toolbar        { background: #0a1628; border-color: #1e293b; }
QToolButton#note_tool_btn   { color: #64748b; }
QToolButton#note_tool_btn:hover  { background: #1e293b; color: #e2e8f0; }
QToolButton#note_tool_btn:checked { background: #312e81; color: #a5b4fc; border-color: #4338ca; }
QFrame#note_toolbar_sep     { color: #1e293b; background: #1e293b; }
QComboBox#note_para_combo   { background: #1e293b; border-color: #334155; color: #e2e8f0; }
QTextEdit#note_editor_body  { background: #0f172a; color: #e2e8f0; }
QFrame#note_editor_sep      { color: #1e293b; background: #1e293b; }
QWidget#note_status_bar     { background: #0a1628; border-color: #1e293b; }
QLabel#note_status_lbl      { color: #475569; }
QWidget#notes_header        { background: #0a1628; border-color: #1e293b; }
QFrame#color_picker_popup   { background: #1e293b; border-color: #334155; }
QFrame#color_picker_div     { color: #334155; background: #334155; }
QPushButton#color_picker_custom_btn { border-color: #334155; color: #94a3b8; }
QPushButton#color_picker_custom_btn:hover { background: #0f172a; color: #e2e8f0; }
"""


# ── Light theme ───────────────────────────────────────────────────────────────

_LIGHT_STYLESHEET = STYLESHEET + """
/* ── Light topbar ── */
QWidget#main_topbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QFrame#topbar_vsep {
    color: #e2e8f0;
    background-color: #e2e8f0;
}
QFrame#topbar_hsep {
    color: #e2e8f0;
    background-color: #e2e8f0;
}
QPushButton#topnav_btn {
    color: #64748b;
    background: transparent;
}
QPushButton#topnav_btn:hover {
    background-color: #f1f5f9;
    color: #1e293b;
}
QPushButton#topnav_btn[active="true"] {
    background-color: #2563eb;
    color: #ffffff;
}
QLabel#version { color: #94a3b8; }
QPushButton#theme_toggle_btn {
    border-color: #e2e8f0;
    color: #1e293b;
}
QPushButton#theme_toggle_btn:hover {
    background: #f1f5f9;
    border-color: #cbd5e1;
}

/* ── Light sidebar ── */
QWidget#lib_side_panel,
QWidget#lib_panel_header {
    background-color: #f8fafc;
    border-right: 1px solid #e2e8f0;
}
QScrollArea#lib_panel_scroll,
QWidget#lib_panel_container {
    background-color: #f8fafc;
}
QTreeWidget#lib_side_tree {
    background: #f8fafc;
    color: #1e293b;
}
QTreeWidget#lib_side_tree::item { color: #334155; }
QTreeWidget#lib_side_tree::item:hover { background: #f1f5f9; }
QTreeWidget#lib_side_tree::item:selected {
    background: #eff6ff;
    color: #1d4ed8;
}
QTreeWidget#lib_side_tree::branch { background: #f8fafc; }
QLabel#lib_panel_title { color: #94a3b8; }
QFrame#tag_group_row { background: transparent; }
QFrame#tag_group_row:hover { background: #f1f5f9; }
QFrame#tag_group_row[active="true"] { background: #eff6ff; }
QLabel#tag_group_label { color: #334155; }
QFrame#tag_group_row[active="true"] QLabel#tag_group_label { color: #1d4ed8; }
QLabel#tag_group_count { color: #94a3b8; }
QFrame#panel_sep, QFrame#panel_inner_sep {
    color: #e2e8f0;
    background-color: #e2e8f0;
}
QPushButton#lib_panel_add_btn {
    background: #e2e8f0;
    color: #475569;
}
QPushButton#lib_panel_add_btn:hover {
    background: #cbd5e1;
    color: #0f172a;
}
"""
