
import os
import sys
import datetime
from typing import List

from PyQt5.QtCore import Qt, QTimer, QSize, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, QLabel,
    QTextEdit, QComboBox, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QSplitter, QStyle, QTabWidget, QDialog, QDialogButtonBox, QFormLayout,
    QSpinBox, QInputDialog
)

from app.storage import Storage
from app.models import ClipEntry, TemplateEntry
from app.language import Language
from app.theme import build_stylesheet, THEMES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "data.json")
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")
LANG_DIR = os.path.join(BASE_DIR, "languages")
os.makedirs(IMAGE_DIR, exist_ok=True)


def load_icon(theme: str) -> QIcon:
    if theme == "dark":
        path = os.path.join(BASE_DIR, "assets", "icons", "dark", "icon.ico")
    else:
        path = os.path.join(BASE_DIR, "assets", "icons", "light", "icon.ico")
    if os.path.exists(path):
        return QIcon(path)
    return QIcon()


class SettingsDialog(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle(Language.T("settings.title"))
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItem(Language.T("settings.language.zh"), "zh_TW")
        self.cmb_lang.addItem(Language.T("settings.language.en"), "en_US")
        idx = self.cmb_lang.findData(self.storage.language)
        if idx >= 0:
            self.cmb_lang.setCurrentIndex(idx)

        self.cmb_theme = QComboBox()
        theme_key = self.storage.theme
        for key in THEMES.keys():
            text_key = f"settings.theme.{key}"
            label = Language.T(text_key, THEMES[key]["name"])
            self.cmb_theme.addItem(label, key)
        idx = self.cmb_theme.findData(theme_key)
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)

        self.cmb_icon = QComboBox()
        self.cmb_icon.addItem(Language.T("settings.icon.light"), "light")
        self.cmb_icon.addItem(Language.T("settings.icon.dark"), "dark")
        idx = self.cmb_icon.findData(self.storage.icon_theme)
        if idx >= 0:
            self.cmb_icon.setCurrentIndex(idx)

        self.spin_max = QSpinBox()
        self.spin_max.setRange(10, 10000)
        self.spin_max.setValue(self.storage.max_entries)

        form.addRow(Language.T("settings.language"), self.cmb_lang)
        form.addRow(Language.T("settings.theme"), self.cmb_theme)
        form.addRow(Language.T("settings.icon_theme"), self.cmb_icon)
        form.addRow(Language.T("settings.max_entries"), self.spin_max)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText(Language.T("settings.ok"))
        btns.button(QDialogButtonBox.Cancel).setText(Language.T("settings.cancel"))
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def apply(self):
        lang = self.cmb_lang.currentData()
        theme_key = self.cmb_theme.currentData()
        icon_theme = self.cmb_icon.currentData()
        max_entries = self.spin_max.value()

        self.storage.language = lang
        self.storage.theme = theme_key
        self.storage.icon_theme = icon_theme
        self.storage.max_entries = max_entries


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.storage = Storage(DATA_FILE)

        Language.load(self.storage.language, LANG_DIR)

        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

        self._building_list = False

        self.init_ui()
        self.init_tray()
        self.init_global_hotkeys()
        self.refresh_clipboard_list()
        self.refresh_template_list()

    def init_ui(self):
        self.setWindowTitle(Language.T("app.title"))
        icon = load_icon(self.storage.icon_theme)
        if not icon.isNull():
            self.setWindowIcon(icon)

        self.apply_theme()

        menubar = self.menuBar()
        menu_settings = menubar.addMenu(Language.T("menu.settings"))
        menu_about = menubar.addMenu(Language.T("menu.about"))
        menu_help = menubar.addMenu(Language.T("menu.help"))

        act_settings = QAction(Language.T("menu.settings"), self)
        act_settings.triggered.connect(self.show_settings)
        menu_settings.addAction(act_settings)

        act_about = QAction(Language.T("menu.about"), self)
        act_about.triggered.connect(self.show_about)
        menu_about.addAction(act_about)

        act_report = QAction(Language.T("menu.help.report"), self)
        act_report.triggered.connect(self.open_report_email)
        menu_help.addAction(act_report)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        clip_tab = QWidget()
        clip_layout = QVBoxLayout()
        clip_tab.setLayout(clip_layout)

        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(Language.T("label.search") + " ...")
        self.search_edit.textChanged.connect(self.refresh_clipboard_list)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            Language.T("filter.all"),
            Language.T("filter.text"),
            Language.T("filter.image"),
            Language.T("filter.url"),
            Language.T("filter.file"),
            Language.T("filter.pinned"),
        ])
        self.filter_combo.currentIndexChanged.connect(self.refresh_clipboard_list)

        search_layout.addWidget(QLabel(Language.T("label.search")))
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(QLabel(Language.T("label.type")))
        search_layout.addWidget(self.filter_combo)
        clip_layout.addLayout(search_layout)

        splitter = QSplitter()
        clip_layout.addWidget(splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_clipboard_selection_changed)
        left_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_pin = QPushButton(Language.T("button.pin"))
        self.btn_delete = QPushButton(Language.T("button.delete"))
        self.btn_copy = QPushButton(Language.T("button.copy"))
        self.btn_clear = QPushButton(Language.T("button.clear"))

        self.btn_pin.clicked.connect(self.toggle_pin)
        self.btn_delete.clicked.connect(self.delete_selected_clipboard)
        self.btn_copy.clicked.connect(self.copy_selected_to_clipboard)
        self.btn_clear.clicked.connect(self.clear_history_keep_pinned)

        for b in (self.btn_pin, self.btn_delete, self.btn_copy, self.btn_clear):
            btn_layout.addWidget(b)
        left_layout.addLayout(btn_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        self.preview_title = QLabel(Language.T("preview.title"))
        self.preview_title.setStyleSheet("font-weight: bold;")
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setVisible(False)

        right_layout.addWidget(self.preview_title)
        right_layout.addWidget(self.preview_area)
        right_layout.addWidget(self.image_label)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])

        self.tabs.addTab(clip_tab, Language.T("tab.clipboard"))

        tpl_tab = QWidget()
        tpl_layout = QVBoxLayout()
        tpl_tab.setLayout(tpl_layout)

        self.tpl_list = QListWidget()
        tpl_layout.addWidget(self.tpl_list)

        tpl_btn_layout = QHBoxLayout()
        self.btn_tpl_add = QPushButton(Language.T("button.tpl.add"))
        self.btn_tpl_edit = QPushButton(Language.T("button.tpl.edit"))
        self.btn_tpl_delete = QPushButton(Language.T("button.tpl.delete"))
        self.btn_tpl_copy = QPushButton(Language.T("button.tpl.copy"))
        self.btn_tpl_hotkey = QPushButton(Language.T("button.tpl.hotkey"))

        self.btn_tpl_add.clicked.connect(self.add_template)
        self.btn_tpl_edit.clicked.connect(self.edit_template)
        self.btn_tpl_delete.clicked.connect(self.delete_template)
        self.btn_tpl_copy.clicked.connect(self.copy_template_to_clipboard)
        self.btn_tpl_hotkey.clicked.connect(self.set_template_hotkey)

        for b in (self.btn_tpl_add, self.btn_tpl_edit, self.btn_tpl_delete, self.btn_tpl_copy, self.btn_tpl_hotkey):
            tpl_btn_layout.addWidget(b)
        tpl_layout.addLayout(tpl_btn_layout)

        self.tabs.addTab(tpl_tab, Language.T("tab.templates"))

    def apply_theme(self):
        theme_key = self.storage.theme
        self.setStyleSheet(build_stylesheet(theme_key))

    def init_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = load_icon(self.storage.icon_theme)
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.SP_FileDialogInfoView)
        self.tray.setIcon(icon)
        self.tray.setToolTip(Language.T("tray.tooltip"))

        self.build_tray_menu()
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def build_tray_menu(self):
        menu = QMenu()
        act_show = QAction(Language.T("tray.menu.show"), self)
        act_quit = QAction(Language.T("tray.menu.quit"), self)

        act_show.triggered.connect(self.show_normal_from_tray)
        act_quit.triggered.connect(QApplication.instance().quit)

        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)

    def init_global_hotkeys(self):
        try:
            import keyboard
        except Exception:
            return

        keyboard.add_hotkey('ctrl+shift+c', lambda: QTimer.singleShot(0, self.show_normal_from_tray))

        for i in range(1, 10):
            keyboard.add_hotkey(f'ctrl+shift+{i}', lambda idx=i: QTimer.singleShot(0, lambda: self.apply_template_hotkey(idx)))

    def apply_template_hotkey(self, idx: int):
        tpl = self.storage.find_template_by_hotkey(idx)
        if not tpl:
            return
        self.clipboard.setText(tpl.content)

    def show_normal_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden() or self.isMinimized():
                self.show_normal_from_tray()
            else:
                self.hide()

    def closeEvent(self, event):
        if self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                Language.T("msg.title.app"),
                Language.T("msg.tray.hidden"),
                QSystemTrayIcon.Information,
                3000
            )
        else:
            super().closeEvent(event)

    def get_filtered_entries(self) -> List[ClipEntry]:
        keyword = self.search_edit.text().strip().lower()
        f = self.filter_combo.currentText()

        entries = self.storage.get_entries()

        def match_type(e: ClipEntry) -> bool:
            if f in (Language.T("filter.all"), ""):
                return True
            if f == Language.T("filter.pinned"):
                return e.pinned
            mapping = {
                Language.T("filter.text"): "text",
                Language.T("filter.image"): "image",
                Language.T("filter.url"): "url",
                Language.T("filter.file"): "file",
            }
            t = mapping.get(f)
            if not t:
                return True
            return e.type == t

        filtered = [e for e in entries if match_type(e)]

        if keyword:
            result = []
            for e in filtered:
                text = (e.content or "").lower()
                tags = " ".join(e.tags or []).lower()
                if keyword in text or keyword in tags or keyword in e.timestamp_local.lower():
                    result.append(e)
            filtered = result

        return filtered

    def refresh_clipboard_list(self):
        self._building_list = True
        self.list_widget.clear()

        entries = self.get_filtered_entries()
        for e in entries:
            ts = e.timestamp_local
            display = f"[{e.type}] {ts} - {e.content}"
            if len(display) > 60:
                display = display[:57] + "..."
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, e.id)
            if e.pinned:
                item.setText("📌 " + item.text())
            self.list_widget.addItem(item)

        self._building_list = False
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        else:
            self.preview_area.clear()
            self.image_label.clear()
            self.image_label.setVisible(False)

    def get_entry_by_id(self, entry_id: int) -> ClipEntry:
        for e in self.storage.get_entries():
            if e.id == entry_id:
                return e
        return None

    def current_clipboard_entry(self) -> ClipEntry:
        item = self.list_widget.currentItem()
        if not item:
            return None
        entry_id = item.data(Qt.UserRole)
        return self.get_entry_by_id(entry_id)

    def on_clipboard_selection_changed(self, current, previous):
        if self._building_list:
            return
        entry = self.current_clipboard_entry()
        if not entry:
            self.preview_area.clear()
            self.image_label.clear()
            self.image_label.setVisible(False)
            return

        self.preview_title.setText(f"{Language.T('preview.title')} - ID {entry.id} ({entry.type})")
        self.image_label.clear()
        self.image_label.setVisible(False)

        if entry.type in ("text", "url", "file"):
            self.preview_area.setPlainText(entry.content)
        elif entry.type == "image":
            self.preview_area.setPlainText(entry.content)
            img_path = entry.extra.get("image_path") if entry.extra else None
            if img_path and os.path.exists(img_path):
                pix = QPixmap(img_path)
                if not pix.isNull():
                    self.image_label.setPixmap(pix.scaled(QSize(360, 360), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.image_label.setVisible(True)
        else:
            self.preview_area.setPlainText(entry.content)

    def toggle_pin(self):
        entry = self.current_clipboard_entry()
        if not entry:
            return
        entry.pinned = not entry.pinned
        self.storage.update_entry(entry)
        self.refresh_clipboard_list()

    def delete_selected_clipboard(self):
        entry = self.current_clipboard_entry()
        if not entry:
            return
        reply = QMessageBox.question(
            self,
            Language.T("msg.title.delete"),
            Language.T("msg.delete.confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.storage.delete_entry(entry.id)
            self.refresh_clipboard_list()

    def copy_selected_to_clipboard(self):
        entry = self.current_clipboard_entry()
        if not entry:
            return
        if entry.type in ("text", "url", "file"):
            self.clipboard.setText(entry.content)
        elif entry.type == "image":
            img_path = entry.extra.get("image_path") if entry.extra else None
            if img_path and os.path.exists(img_path):
                pix = QPixmap(img_path)
                self.clipboard.setPixmap(pix)

    def clear_history_keep_pinned(self):
        reply = QMessageBox.question(
            self,
            Language.T("msg.title.clear"),
            Language.T("msg.clear.confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.storage.clear_history(keep_pinned=True)
            self.refresh_clipboard_list()

    def on_clipboard_changed(self):
        mime = self.clipboard.mimeData()
        if mime is None:
            return

        entry_type = None
        content = ""
        extra = {}

        if mime.hasImage():
            entry_type = "image"
            image = self.clipboard.image()
            if not image.isNull():
                now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                img_path = os.path.join(IMAGE_DIR, f"clip_{now_str}.png")
                image.save(img_path, "PNG")
                content = img_path
                extra["image_path"] = img_path
        elif mime.hasUrls():
            urls = mime.urls()
            if urls:
                if urls[0].isLocalFile():
                    entry_type = "file"
                    content = urls[0].toLocalFile()
                else:
                    entry_type = "url"
                    content = urls[0].toString()
        elif mime.hasText():
            entry_type = "text"
            content = mime.text()

        if not entry_type or not content:
            return

        now = datetime.datetime.now().astimezone()
        ts_local = now.strftime("%Y-%m-%d %H:%M:%S")
        ts_iso = now.isoformat(timespec="seconds")

        new_entry = ClipEntry(
            id=self.storage.next_entry_id(),
            type=entry_type,
            content=content,
            timestamp_local=ts_local,
            timestamp_iso=ts_iso,
            pinned=False,
            tags=[],
            extra=extra
        )
        self.storage.add_entry(new_entry)
        self.refresh_clipboard_list()

    def refresh_template_list(self):
        self.tpl_list.clear()
        templates = self.storage.get_templates()
        for t in templates:
            label = t.name
            if t.hotkey_index:
                label = f"[{t.hotkey_index}] " + label
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t.id)
            self.tpl_list.addItem(item)

    def current_template(self) -> TemplateEntry:
        item = self.tpl_list.currentItem()
        if not item:
            return None
        tpl_id = item.data(Qt.UserRole)
        for t in self.storage.get_templates():
            if t.id == tpl_id:
                return t
        return None

    def add_template(self):
        name, ok = QInputDialog.getText(self, Language.T("tab.templates"), Language.T("tpl.input.name"))
        if not ok or not name.strip():
            return
        content, ok = QInputDialog.getMultiLineText(self, Language.T("tab.templates"), Language.T("tpl.input.content"))
        if not ok:
            return
        tpl = TemplateEntry(id=self.storage.next_template_id(), name=name.strip(), content=content, hotkey_index=None)
        self.storage.add_template(tpl)
        self.refresh_template_list()

    def edit_template(self):
        tpl = self.current_template()
        if not tpl:
            return
        name, ok = QInputDialog.getText(self, Language.T("tab.templates"), Language.T("tpl.input.name"), text=tpl.name)
        if not ok or not name.strip():
            return
        content, ok = QInputDialog.getMultiLineText(self, Language.T("tab.templates"), Language.T("tpl.input.content"), text=tpl.content)
        if not ok:
            return
        tpl.name = name.strip()
        tpl.content = content
        self.storage.update_template(tpl)
        self.refresh_template_list()

    def delete_template(self):
        tpl = self.current_template()
        if not tpl:
            return
        reply = QMessageBox.question(
            self,
            Language.T("msg.title.delete"),
            Language.T("msg.delete.confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.storage.delete_template(tpl.id)
            self.refresh_template_list()

    def copy_template_to_clipboard(self):
        tpl = self.current_template()
        if not tpl:
            return
        self.clipboard.setText(tpl.content)

    def set_template_hotkey(self):
        tpl = self.current_template()
        if not tpl:
            return
        idx, ok = QInputDialog.getInt(self, Language.T("tab.templates"), Language.T("tpl.input.hotkey"), value=tpl.hotkey_index or 1, min=1, max=9)
        if not ok:
            tpl.hotkey_index = None
        else:
            tpl.hotkey_index = idx
        self.storage.update_template(tpl)
        self.refresh_template_list()

    def show_settings(self):
        dlg = SettingsDialog(self.storage, self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.apply()
            Language.load(self.storage.language, LANG_DIR)
            self.apply_theme()
            icon = load_icon(self.storage.icon_theme)
            if not icon.isNull():
                self.setWindowIcon(icon)
                self.tray.setIcon(icon)
            self.retranslate_ui()
            self.refresh_clipboard_list()
            self.refresh_template_list()
            self.build_tray_menu()

    def retranslate_ui(self):
        self.setWindowTitle(Language.T("app.title"))
        menubar = self.menuBar()
        menubar.clear()
        menu_settings = menubar.addMenu(Language.T("menu.settings"))
        menu_about = menubar.addMenu(Language.T("menu.about"))
        menu_help = menubar.addMenu(Language.T("menu.help"))

        act_settings = QAction(Language.T("menu.settings"), self)
        act_settings.triggered.connect(self.show_settings)
        menu_settings.addAction(act_settings)

        act_about = QAction(Language.T("menu.about"), self)
        act_about.triggered.connect(self.show_about)
        menu_about.addAction(act_about)

        act_report = QAction(Language.T("menu.help.report"), self)
        act_report.triggered.connect(self.open_report_email)
        menu_help.addAction(act_report)

        self.tabs.setTabText(0, Language.T("tab.clipboard"))
        self.tabs.setTabText(1, Language.T("tab.templates"))

        self.btn_pin.setText(Language.T("button.pin"))
        self.btn_delete.setText(Language.T("button.delete"))
        self.btn_copy.setText(Language.T("button.copy"))
        self.btn_clear.setText(Language.T("button.clear"))
        self.preview_title.setText(Language.T("preview.title"))

        self.btn_tpl_add.setText(Language.T("button.tpl.add"))
        self.btn_tpl_edit.setText(Language.T("button.tpl.edit"))
        self.btn_tpl_delete.setText(Language.T("button.tpl.delete"))
        self.btn_tpl_copy.setText(Language.T("button.tpl.copy"))
        self.btn_tpl_hotkey.setText(Language.T("button.tpl.hotkey"))

        self.search_edit.setPlaceholderText(Language.T("label.search") + " ...")

        current_index = self.filter_combo.currentIndex()
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItems([
            Language.T("filter.all"),
            Language.T("filter.text"),
            Language.T("filter.image"),
            Language.T("filter.url"),
            Language.T("filter.file"),
            Language.T("filter.pinned"),
        ])
        self.filter_combo.blockSignals(False)
        if 0 <= current_index < self.filter_combo.count():
            self.filter_combo.setCurrentIndex(current_index)

    def show_about(self):
        text = Language.T("about.text") + "\n\n" + Language.T("about.docs")
        QMessageBox.information(self, Language.T("about.title"), text)

    def open_report_email(self):
        QMessageBox.information(self, Language.T("menu.help.report"), Language.T("help.report.msg"))
        url = QUrl("mailto:trialscales0430@gmail.com?subject=LightClip%20v1.3%20問題回報")
        QDesktopServices.openUrl(url)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    win.resize(1000, 680)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
