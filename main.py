
import sys
import os
import webbrowser
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidget, QListWidgetItem, QPushButton, QLabel,
    QTextEdit, QLineEdit, QDialog, QFormLayout, QSpinBox, QComboBox,
    QMessageBox, QFileDialog, QSystemTrayIcon, QMenu, QStyle, QFrame,
    QScrollArea, QSizePolicy
)

from app.storage import StorageManager
from app.language import LanguageManager, _, init_language_manager
from app.theme import ThemeManager
from app.cloud_sync import CloudSync

APP_VERSION = "1.6.1a"


class TextViewerDialog(QDialog):
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(text)
        layout.addWidget(self.text_edit)


class TemplateEditorDialog(QDialog):
    def __init__(self, template: dict | None, parent=None):
        super().__init__(parent)
        self.template = template or {"name": "", "content": ""}
        self.setWindowTitle(_("template.editor.title"))
        self.resize(600, 500)

        main_layout = QVBoxLayout(self)

        # 第一行：名稱 + 右側複製
        name_row = QHBoxLayout()
        name_label = QLabel(_("template.name"), self)
        self.name_edit = QLineEdit(self)
        self.name_edit.setText(self.template["name"])
        self.copy_btn = QPushButton(_("template.copy_now"), self)
        self.copy_btn.clicked.connect(self.copy_template_content)
        name_row.addWidget(name_label)
        name_row.addWidget(self.name_edit)
        name_row.addWidget(self.copy_btn)
        main_layout.addLayout(name_row)

        # 第二塊：內容
        content_label = QLabel(_("template.content"), self)
        self.content_edit = QTextEdit(self)
        self.content_edit.setPlainText(self.template["content"])
        self.content_edit.textChanged.connect(self.update_preview)
        main_layout.addWidget(content_label)
        main_layout.addWidget(self.content_edit)

        # 第三塊：下方檢視（至少 3 行、13px）
        preview_label = QLabel(_("template.preview"), self)
        self.preview_edit = QTextEdit(self)
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setFixedHeight(100)
        font = self.preview_edit.font()
        font.setPointSize(13)
        self.preview_edit.setFont(font)

        main_layout.addWidget(preview_label)
        main_layout.addWidget(self.preview_edit)

        # 底部按鈕列
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.ok_btn = QPushButton(_("common.ok"), self)
        self.cancel_btn = QPushButton(_("common.cancel"), self)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.ok_btn)
        btn_row.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_row)

        self.update_preview()

    def update_preview(self):
        self.preview_edit.setPlainText(self.content_edit.toPlainText())

    def copy_template_content(self):
        # 將目前內容直接複製到剪貼簿
        clipboard = QApplication.clipboard()
        clipboard.setText(self.content_edit.toPlainText())
        QMessageBox.information(self, "LightClip", _("template.copied_to_clipboard"))

    def get_result(self):
        return {
            "name": self.name_edit.text().strip(),
            "content": self.content_edit.toPlainText()
        }


class SettingsDialog(QDialog):
    def __init__(self, storage: StorageManager, lang_mgr: LanguageManager, theme_mgr: ThemeManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.lang_mgr = lang_mgr
        self.theme_mgr = theme_mgr
        self.setWindowTitle(_("settings.title"))
        self.resize(400, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(7)  # 上下間距 7PX

        self.spin_history = QSpinBox(self)
        self.spin_history.setRange(10, 500)
        self.spin_history.setValue(self.storage.settings.get("max_history", 100))
        form.addRow(_("settings.max_history"), self.spin_history)

        self.combo_lang = QComboBox(self)
        self.combo_lang.addItem("繁體中文", "zh_TW")
        self.combo_lang.addItem("English", "en_US")
        current_lang = self.lang_mgr.current_language
        idx = self.combo_lang.findData(current_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        form.addRow(_("settings.language"), self.combo_lang)

        self.combo_theme = QComboBox(self)
        for key, meta in self.theme_mgr.themes.items():
            self.combo_theme.addItem(meta["name"], key)
        cur_theme = self.theme_mgr.current_theme_key
        tidx = self.combo_theme.findData(cur_theme)
        if tidx >= 0:
            self.combo_theme.setCurrentIndex(tidx)
        form.addRow(_("settings.theme"), self.combo_theme)

        layout.addLayout(form)

        # hotkey 簡化：僅顯示說明文字
        note = QLabel(_("settings.hotkey_hint"), self)
        note.setWordWrap(True)
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton(_("common.ok"), self)
        cancel_btn = QPushButton(_("common.cancel"), self)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def apply(self):
        self.storage.settings["max_history"] = self.spin_history.value()
        lang_code = self.combo_lang.currentData()
        theme_key = self.combo_theme.currentData()
        self.storage.settings["language"] = lang_code
        self.storage.settings["theme"] = theme_key
        self.lang_mgr.set_language(lang_code)
        self.theme_mgr.set_theme(theme_key)
        self.storage.save_all()


class LightClipWindow(QMainWindow):
    def __init__(self, storage: StorageManager, lang_mgr: LanguageManager, theme_mgr: ThemeManager):
        super().__init__()
        self.storage = storage
        self.lang_mgr = lang_mgr
        self.theme_mgr = theme_mgr
        self.cloud = CloudSync(storage)

        self.setWindowTitle(f"LightClip v{APP_VERSION} - " + _("app.subtitle"))
        self.setMinimumSize(900, 600)

        # 設定圖示
        icon_path = Path(__file__).resolve().parent / "assets" / "icons" / "lightclip_logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # 建立主版面
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Tab
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)

        # 剪貼簿 Tab
        self.clipboard_tab = QWidget(self)
        self.tabs.addTab(self.clipboard_tab, _("tab.clipboard"))
        self._init_clipboard_tab()

        # 模板 Tab
        self.template_tab = QWidget(self)
        self.tabs.addTab(self.template_tab, _("tab.templates"))
        self._init_template_tab()

        # 狀態列
        self.status = self.statusBar()
        self.update_status(_("status.ready"))

        # Menu bar
        self._init_menu_bar()

        # System tray
        self._init_tray(icon_path)

        # 監聽剪貼簿
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

        # 載入資料
        self.refresh_clipboard_list()
        self.refresh_template_list()

        # Shortcut (app 內)
        self.shortcut_show = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        self.shortcut_show.activated.connect(self.bring_to_front)

        self.apply_theme()

    # --- UI 初始化 ---

    def _init_menu_bar(self):
        menubar = self.menuBar()
        menubar.clear()

        # 依照需求：操作說明｜更新日誌｜問題回報｜雲端同步｜設定｜關於｜說明
        act_guide = QAction(_("menu.user_guide"), self)
        act_guide.triggered.connect(self.show_user_guide)
        menubar.addAction(act_guide)

        act_changelog = QAction(_("menu.changelog"), self)
        act_changelog.triggered.connect(self.show_changelog)
        menubar.addAction(act_changelog)

        act_report = QAction(_("menu.report_issue"), self)
        act_report.triggered.connect(self.open_report_email)
        menubar.addAction(act_report)

        act_cloud = QAction(_("menu.cloud_sync"), self)
        act_cloud.triggered.connect(self.do_cloud_sync)
        menubar.addAction(act_cloud)

        menubar.addSeparator()

        act_settings = QAction(_("menu.settings"), self)
        act_settings.triggered.connect(self.open_settings)
        menubar.addAction(act_settings)

        act_about = QAction(_("menu.about"), self)
        act_about.triggered.connect(self.show_about)
        menubar.addAction(act_about)

        act_help = QAction(_("menu.help"), self)
        act_help.triggered.connect(self.show_user_guide)
        menubar.addAction(act_help)

    def _init_tray(self, icon_path: Path):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.tray.setToolTip("LightClip")
        menu = QMenu()
        show_act = QAction(_("tray.show"), self)
        quit_act = QAction(_("tray.quit"), self)
        show_act.triggered.connect(self.bring_to_front)
        quit_act.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_act)
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.activated.connect(self._tray_activated)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.bring_to_front()

    def bring_to_front(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _init_clipboard_tab(self):
        layout = QVBoxLayout(self.clipboard_tab)

        # 搜尋列
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText(_("clipboard.search_placeholder"))
        self.search_edit.textChanged.connect(self.refresh_clipboard_list)
        search_row.addWidget(QLabel(_("clipboard.search_label"), self))
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        # 列表 (自動換列)
        self.clip_list = QListWidget(self)
        self.clip_list.itemDoubleClicked.connect(self.copy_selected_clip)
        self.clip_list.setWordWrap(True)
        layout.addWidget(self.clip_list)

        # 操作列
        btn_row = QHBoxLayout()
        self.btn_copy_clip = QPushButton(_("clipboard.btn_copy"), self)
        self.btn_copy_clip.clicked.connect(self.copy_selected_clip)
        self.btn_delete_clip = QPushButton(_("clipboard.btn_delete"), self)
        self.btn_delete_clip.clicked.connect(self.delete_selected_clip)
        self.btn_pin_clip = QPushButton(_("clipboard.btn_pin_toggle"), self)
        self.btn_pin_clip.clicked.connect(self.toggle_pin_selected_clip)
        btn_row.addWidget(self.btn_copy_clip)
        btn_row.addWidget(self.btn_delete_clip)
        btn_row.addWidget(self.btn_pin_clip)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 預覽區（支援文字與圖片）
        self.clip_preview_text = QTextEdit(self)
        self.clip_preview_text.setReadOnly(True)
        self.clip_preview_text.setPlaceholderText(_("clipboard.preview_placeholder"))

        self.clip_preview_image = QLabel(self)
        self.clip_preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clip_preview_image.setVisible(False)
        self.clip_preview_image.setMinimumHeight(180)

        layout.addWidget(self.clip_preview_text)
        layout.addWidget(self.clip_preview_image)

        self.clip_list.currentItemChanged.connect(self.update_clip_preview)

    def _init_template_tab(self):
        layout = QVBoxLayout(self.template_tab)

        # 模板列表
        self.tpl_list = QListWidget(self)
        self.tpl_list.itemDoubleClicked.connect(self.edit_selected_template)
        self.tpl_list.itemActivated.connect(self.edit_selected_template)
        layout.addWidget(self.tpl_list)

        # 操作列
        btn_row = QHBoxLayout()
        self.btn_tpl_add = QPushButton(_("template.btn_add"), self)
        self.btn_tpl_edit = QPushButton(_("template.btn_edit"), self)
        self.btn_tpl_delete = QPushButton(_("template.btn_delete"), self)
        self.btn_tpl_copy = QPushButton(_("template.btn_copy"), self)

        self.btn_tpl_add.clicked.connect(self.add_template)
        self.btn_tpl_edit.clicked.connect(self.edit_selected_template)
        self.btn_tpl_delete.clicked.connect(self.delete_selected_template)
        self.btn_tpl_copy.clicked.connect(self.copy_selected_template)

        btn_row.addWidget(self.btn_tpl_add)
        btn_row.addWidget(self.btn_tpl_edit)
        btn_row.addWidget(self.btn_tpl_delete)
        btn_row.addWidget(self.btn_tpl_copy)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 預覽
        self.tpl_preview = QTextEdit(self)
        self.tpl_preview.setReadOnly(True)
        font = self.tpl_preview.font()
        font.setPointSize(13)
        self.tpl_preview.setFont(font)
        layout.addWidget(self.tpl_preview)

        self.tpl_list.currentItemChanged.connect(self.update_template_preview)

    # --- 剪貼簿邏輯 ---

    def on_clipboard_changed(self):
        mime = self.clipboard.mimeData()
        self.storage.handle_new_clipboard(mime)
        self.refresh_clipboard_list()

    def refresh_clipboard_list(self):
        self.clip_list.clear()
        keyword = self.search_edit.text().strip().lower()
        for item in self.storage.iter_clipboard_items():
            text = item.get("preview", "")
            if keyword and keyword not in text.lower():
                continue
            label = text if len(text) < 200 else text[:200] + "..."
            if item.get("pinned"):
                label = "★ " + label
            lw_item = QListWidgetItem(label)
            lw_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.clip_list.addItem(lw_item)

    def get_selected_clip_id(self):
        item = self.clip_list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def copy_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        clip = self.storage.get_clipboard_item(cid)
        if not clip:
            return
        self.storage.copy_clip_to_clipboard(clip)
        self.update_status(_("clipboard.copied_status"))

    def delete_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        self.storage.delete_clipboard_item(cid)
        self.refresh_clipboard_list()
        self.clip_preview.clear()

    def toggle_pin_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        self.storage.toggle_pin(cid)
        self.refresh_clipboard_list()

    def update_clip_preview(self):
        cid = self.get_selected_clip_id()
        if not cid:
            self.clip_preview_text.clear()
            self.clip_preview_image.clear()
            self.clip_preview_image.setVisible(False)
            return
        clip = self.storage.get_clipboard_item(cid)
        if not clip:
            self.clip_preview_text.clear()
            self.clip_preview_image.clear()
            self.clip_preview_image.setVisible(False)
            return
        ctype = clip.get("type")
        if ctype == "image":
            from PyQt6.QtGui import QPixmap
            from pathlib import Path as _Path
            path = _Path(clip.get("image_path", ""))
            if path.exists():
                pix = QPixmap(str(path))
                self.clip_preview_image.setPixmap(pix.scaledToHeight(260, Qt.TransformationMode.SmoothTransformation))
                self.clip_preview_image.setVisible(True)
            else:
                self.clip_preview_image.clear()
                self.clip_preview_image.setVisible(False)
            self.clip_preview_text.setPlainText(clip.get("full_text", clip.get("preview", "")))
        else:
            self.clip_preview_image.clear()
            self.clip_preview_image.setVisible(False)
            self.clip_preview_text.setPlainText(clip.get("full_text", clip.get("preview", "")))

    # --- 模板邏輯 ---

    def refresh_template_list(self):
        self.tpl_list.clear()
        for tpl in self.storage.templates:
            item = QListWidgetItem(tpl["name"])
            item.setData(Qt.ItemDataRole.UserRole, tpl["id"])
            self.tpl_list.addItem(item)

    def get_selected_template(self):
        item = self.tpl_list.currentItem()
        if not item:
            return None
        tid = item.data(Qt.ItemDataRole.UserRole)
        return self.storage.get_template(tid)

    def add_template(self):
        dlg = TemplateEditorDialog(None, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_result()
            if not data["name"]:
                QMessageBox.warning(self, "LightClip", _("template.warn_name"))
                return
            self.storage.add_template(data["name"], data["content"])
            self.storage.save_all()
            self.refresh_template_list()

    def edit_selected_template(self):
        tpl = self.get_selected_template()
        if not tpl:
            return
        dlg = TemplateEditorDialog(tpl, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_result()
            if not data["name"]:
                QMessageBox.warning(self, "LightClip", _("template.warn_name"))
                return
            self.storage.update_template(tpl["id"], data["name"], data["content"])
            self.storage.save_all()
            self.refresh_template_list()

    def delete_selected_template(self):
        tpl = self.get_selected_template()
        if not tpl:
            return
        if QMessageBox.question(self, "LightClip", _("template.confirm_delete")) == QMessageBox.StandardButton.Yes:
            self.storage.delete_template(tpl["id"])
            self.storage.save_all()
            self.refresh_template_list()
            self.tpl_preview.clear()

    def copy_selected_template(self):
        tpl = self.get_selected_template()
        if not tpl:
            return
        QApplication.clipboard().setText(tpl["content"])
        self.update_status(_("template.copied_status"))

    def update_template_preview(self):
        tpl = self.get_selected_template()
        if not tpl:
            self.tpl_preview.clear()
            return
        self.tpl_preview.setPlainText(tpl["content"])

    # --- Menu / Docs / Cloud ---

    def show_user_guide(self):
        path = self.storage.docs_dir / "操作說明.txt"
        if not path.exists():
            QMessageBox.warning(self, "LightClip", _("docs.missing_user_guide"))
            return
        text = path.read_text(encoding="utf-8")
        dlg = TextViewerDialog(_("menu.user_guide"), text, self)
        dlg.exec()

    def show_changelog(self):
        path = self.storage.docs_dir / "更新日誌.txt"
        if not path.exists():
            QMessageBox.warning(self, "LightClip", _("docs.missing_changelog"))
            return
        # 直接顯示檔案內容（依你寫入順序：最新在最上）
        text = path.read_text(encoding="utf-8")
        dlg = TextViewerDialog(_("menu.changelog"), text, self)
        dlg.exec()

    def open_report_email(self):
        # 使用 Gmail 寫信，預填收件人
        url = "https://mail.google.com/mail/u/0/?view=cm&fs=1&to=trialscales0430@gmail.com&su=LightClip%20Feedback"
        webbrowser.open(url)

    def do_cloud_sync(self):
        self.cloud.export_all()
        self.update_status(_("cloud.synced_status"))

    def open_settings(self):
        dlg = SettingsDialog(self.storage, self.lang_mgr, self.theme_mgr, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.apply()
            # 語言與主題更新
            self.retranslate_ui()
            self.apply_theme()

    def show_about(self):
        QMessageBox.information(self, "LightClip",
                                _("about.text").format(version=APP_VERSION))

    # --- Theme / Language ---

    def retranslate_ui(self):
        self.setWindowTitle(f"LightClip v{APP_VERSION} - " + _("app.subtitle"))
        idx = self.tabs.currentIndex()
        self.tabs.setTabText(0, _("tab.clipboard"))
        self.tabs.setTabText(1, _("tab.templates"))
        self._init_menu_bar()  # 依語言重建 menu bar

        # clipboard tab labels
        self.search_edit.setPlaceholderText(_("clipboard.search_placeholder"))
        self.btn_copy_clip.setText(_("clipboard.btn_copy"))
        self.btn_delete_clip.setText(_("clipboard.btn_delete"))
        self.btn_pin_clip.setText(_("clipboard.btn_pin_toggle"))
        self.clip_preview.setPlaceholderText(_("clipboard.preview_placeholder"))

        # template tab labels
        self.btn_tpl_add.setText(_("template.btn_add"))
        self.btn_tpl_edit.setText(_("template.btn_edit"))
        self.btn_tpl_delete.setText(_("template.btn_delete"))
        self.btn_tpl_copy.setText(_("template.btn_copy"))

        self.tabs.setCurrentIndex(idx)

    def apply_theme(self):
        css = self.theme_mgr.build_stylesheet()
        self.setStyleSheet(css)

    # --- Utils ---

    def update_status(self, text: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status.showMessage(f"[{ts}] {text}")


def ensure_dirs():
    base = Path(__file__).resolve().parent
    for d in ["data", "docs", "languages", "assets", "cloud"]:
        (base / d).mkdir(exist_ok=True)
    return base


def main():
    base = ensure_dirs()
    app = QApplication(sys.argv)

    storage = StorageManager(base)
    lang_mgr = LanguageManager(base)
    theme_mgr = ThemeManager(base)

    # 套用已儲存的語言與主題到管理器
    lang_code = storage.settings.get("language", "zh_TW")
    theme_key = storage.settings.get("theme", "dark_default")
    lang_mgr.set_language(lang_code)
    theme_mgr.set_theme(theme_key)
    init_language_manager(lang_mgr)

    win = LightClipWindow(storage, lang_mgr, theme_mgr)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
