
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QTextEdit,
    QLineEdit,
    QDialog,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QMessageBox,
    QSystemTrayIcon,
    QMenu,
    QStyle,
    QFrame,
)

# optional global keyboard hotkey
try:
    import keyboard  # type: ignore[import]
except Exception:  # pragma: no cover
    keyboard = None

from app.storage import StorageManager
from app.language import LanguageManager, _, init_language_manager
from app.theme import ThemeManager
from app.cloud_sync import CloudSync
from app.google_sync import GoogleDriveSync

APP_VERSION = "1.8.0"


def ensure_base_dir() -> Path:
    # 單 EXE 或原始碼都使用同一個目錄邏輯：以 main.py 所在路徑為基準
    return Path(__file__).resolve().parent


# --------- UI 組件：剪貼簿卡片 ---------


class ClipCard(QWidget):
    """剪貼簿列表中的卡片式項目，支援自動換行與展開/收合。"""

    def __init__(self, parent, text: str, meta: str, pinned: bool, can_expand: bool):
        super().__init__(parent)
        self._expanded = False
        self._can_expand = can_expand

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)

        # 卡片外框
        frame = QFrame(self)
        frame.setObjectName("CardFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 8, 10, 8)
        frame_layout.setSpacing(4)

        # 第一行：釘選 + 展開按鈕
        top_row = QHBoxLayout()
        self.btn_pin = QPushButton(frame)
        self.btn_pin.setFlat(True)
        self.btn_pin.setIconSize(QSize(20, 20))
        top_row.addWidget(self.btn_pin)
        top_row.addStretch(1)

        self.btn_expand = QPushButton("展開", frame)
        self.btn_expand.setFlat(True)
        self.btn_expand.setVisible(can_expand)
        top_row.addWidget(self.btn_expand)
        frame_layout.addLayout(top_row)

        # 內容文字
        self.lbl_text = QLabel(text, frame)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setMinimumHeight(24)
        frame_layout.addWidget(self.lbl_text)

        # meta 資訊
        self.lbl_meta = QLabel(meta, frame)
        self.lbl_meta.setObjectName("metaLabel")
        frame_layout.addWidget(self.lbl_meta)

        root.addWidget(frame)

        self.set_pinned(pinned)
        self._set_collapsed_height()

        self.btn_expand.clicked.connect(self.toggle_expand)

    def set_pinned(self, pinned: bool):
        icon_name = "icon_pin_filled.svg" if pinned else "icon_pin_outline.svg"
        icon = QIcon(str(ensure_base_dir() / "assets" / icon_name))
        self.btn_pin.setIcon(icon)

    def _set_collapsed_height(self):
        # 限制為約 3 行高度
        fm = self.lbl_text.fontMetrics()
        max_h = fm.lineSpacing() * 3 + 8
        self.lbl_text.setMaximumHeight(max_h)

    def toggle_expand(self):
        if not self._can_expand:
            return
        self._expanded = not self._expanded
        if self._expanded:
            self.lbl_text.setMaximumHeight(16777215)  # 無限制
            self.btn_expand.setText("收合")
        else:
            self._set_collapsed_height()
            self.btn_expand.setText("展開")


# --------- 設定視窗與模板編輯 ---------


class SettingsDialog(QDialog):
    def __init__(self, parent, storage: StorageManager, lang_mgr: LanguageManager, theme_mgr: ThemeManager):
        super().__init__(parent)
        self.storage = storage
        self.lang_mgr = lang_mgr
        self.theme_mgr = theme_mgr

        self.setWindowTitle(_("settings.title"))
        layout = QFormLayout(self)

        self.spin_history = QSpinBox(self)
        self.spin_history.setRange(10, 1000)
        self.spin_history.setValue(int(storage.settings.get("max_history", 100)))
        layout.addRow(_("settings.max_history"), self.spin_history)

        self.combo_lang = QComboBox(self)
        self.combo_lang.addItem("繁體中文", "zh_TW")
        self.combo_lang.addItem("English", "en_US")
        cur_lang = storage.settings.get("language", "zh_TW")
        idx = self.combo_lang.findData(cur_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        layout.addRow(_("settings.language"), self.combo_lang)

        self.combo_theme = QComboBox(self)
        for key, info in theme_mgr.themes.items():
            self.combo_theme.addItem(info["name"], key)
        cur_theme = storage.settings.get("theme", "dark_default")
        idx = self.combo_theme.findData(cur_theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        layout.addRow(_("settings.theme"), self.combo_theme)

        self.chk_hotkey = QPushButton(self)
        self.chk_hotkey.setCheckable(True)
        self.chk_hotkey.setChecked(bool(storage.settings.get("global_hotkey_enabled", False)))
        self.chk_hotkey.setText(_("settings.global_hotkey_enable"))
        layout.addRow(self.chk_hotkey)

        self.edit_hotkey = QLineEdit(self)
        self.edit_hotkey.setText(storage.settings.get("global_hotkey", "ctrl+shift+v"))
        layout.addRow(_("settings.global_hotkey"), self.edit_hotkey)

        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton(_("settings.apply"), self)
        self.btn_cancel = QPushButton(_("settings.cancel"), self)
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_cancel)
        layout.addRow(btn_row)

        self.btn_apply.clicked.connect(self.apply)
        self.btn_cancel.clicked.connect(self.reject)

    def apply(self):
        self.storage.settings["max_history"] = int(self.spin_history.value())
        lang_code = self.combo_lang.currentData()
        theme_key = self.combo_theme.currentData()
        self.storage.settings["language"] = lang_code
        self.storage.settings["theme"] = theme_key
        self.storage.settings["global_hotkey_enabled"] = self.chk_hotkey.isChecked()
        self.storage.settings["global_hotkey"] = self.edit_hotkey.text().strip() or "ctrl+shift+v"
        self.storage.save_all()

        # 即時更新語言與主題，但同時提醒重新啟動以完全套用
        self.lang_mgr.set_language(lang_code)
        self.theme_mgr.set_theme(theme_key)
        QMessageBox.information(
            self,
            _("settings.title"),
            _("settings.restart_hint"),
        )
        self.accept()


class TemplateEditorDialog(QDialog):
    def __init__(self, parent, name: str = "", content: str = ""):
        super().__init__(parent)
        self.setWindowTitle("模板編輯")
        layout = QVBoxLayout(self)
        self.edit_name = QLineEdit(self)
        self.edit_name.setPlaceholderText("模板名稱")
        self.edit_name.setText(name)
        self.edit_content = QTextEdit(self)
        self.edit_content.setPlainText(content)
        self.edit_content.setMinimumHeight(220)

        layout.addWidget(self.edit_name)
        layout.addWidget(self.edit_content)

        self.btn_row = QHBoxLayout()
        self.btn_ok = QPushButton("確定", self)
        self.btn_cancel = QPushButton("取消", self)
        self.btn_row.addWidget(self.btn_ok)
        self.btn_row.addWidget(self.btn_cancel)
        layout.addLayout(self.btn_row)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_values(self):
        return self.edit_name.text().strip(), self.edit_content.toPlainText()


# --------- 主視窗 ---------


class LightClipWindow(QMainWindow):
    def __init__(self, storage: StorageManager, lang_mgr: LanguageManager, theme_mgr: ThemeManager, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.storage = storage
        self.lang_mgr = lang_mgr
        self.theme_mgr = theme_mgr
        self.cloud_sync = CloudSync(base_dir, storage)
        self.google_sync = GoogleDriveSync(base_dir)
        self.global_hotkey_registered = False

        init_language_manager(lang_mgr)

        self.setWindowTitle(_("app.title"))
        self.resize(980, 640)

        icon_path = self.base_dir / "assets" / "lightclip_logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._init_ui()
        self.apply_theme()
        self.setup_tray()
        self.setup_global_hotkey()

    # --- UI ---
    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # top bar
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel("LightClip", self)
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch(1)

        # cloud sync icon button
        self.btn_cloud = QPushButton(self)
        cloud_icon_path = self.base_dir / "assets" / "icon_cloud.svg"
        if cloud_icon_path.exists():
            self.btn_cloud.setIcon(QIcon(str(cloud_icon_path)))
            self.btn_cloud.setIconSize(QSize(24, 24))
        else:
            self.btn_cloud.setText("☁")
        self.btn_cloud.setFixedSize(36, 32)
        self.btn_cloud.setFlat(True)
        self.btn_cloud.clicked.connect(self.on_cloud_sync_clicked)
        top_bar.addWidget(self.btn_cloud)

        # three-dot menu button
        self.btn_menu = QPushButton(self)
        more_icon = QIcon(str(self.base_dir / "assets" / "icon_more.svg"))
        self.btn_menu.setIcon(more_icon)
        self.btn_menu.setIconSize(QSize(20, 20))
        self.btn_menu.setFixedSize(36, 32)
        self.btn_menu.setFlat(True)
        self.btn_menu.clicked.connect(self.show_main_menu)
        top_bar.addWidget(self.btn_menu)

        root_layout.addLayout(top_bar)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tab_clipboard = QWidget(self)
        self.tab_templates = QWidget(self)
        self.tabs.addTab(self.tab_clipboard, _("ui.tab.clipboard"))
        self.tabs.addTab(self.tab_templates, _("ui.tab.templates"))
        root_layout.addWidget(self.tabs)

        self._init_clipboard_tab()
        self._init_templates_tab()

    def _init_clipboard_tab(self):
        layout = QVBoxLayout(self.tab_clipboard)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # search row
        search_row = QHBoxLayout()
        lbl = QLabel(_("ui.search.placeholder"), self)
        self.edit_search = QLineEdit(self)
        self.edit_search.setPlaceholderText(_("ui.search.placeholder"))
        self.edit_search.textChanged.connect(self.refresh_clipboard_lists)
        search_row.addWidget(lbl)
        search_row.addWidget(self.edit_search)
        layout.addLayout(search_row)

        # main row: left lists + right preview
        row = QHBoxLayout()

        left_col = QVBoxLayout()

        # pincard section
        pin_header_row = QHBoxLayout()
        self.btn_toggle_pin_section = QPushButton("📌 釘選項目（展開）", self)
        self.btn_toggle_pin_section.setCheckable(True)
        self.btn_toggle_pin_section.setChecked(True)
        self.btn_toggle_pin_section.clicked.connect(self.toggle_pin_section)
        pin_header_row.addWidget(self.btn_toggle_pin_section)
        pin_header_row.addStretch(1)
        left_col.addLayout(pin_header_row)

        self.list_pinned = QListWidget(self)
        self.list_pinned.setSpacing(6)
        self.list_pinned.currentItemChanged.connect(self.on_clip_selection_changed)
        left_col.addWidget(self.list_pinned)

        # normal section label
        lbl_history = QLabel("剪貼簿歷史", self)
        left_col.addWidget(lbl_history)

        self.clip_list = QListWidget(self)
        self.clip_list.setSpacing(6)
        self.clip_list.currentItemChanged.connect(self.on_clip_selection_changed)
        left_col.addWidget(self.clip_list, 1)

        row.addLayout(left_col, 2)

        # right preview panel
        right_panel = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_clip_copy = QPushButton(_("clipboard.copy"), self)
        self.btn_clip_delete = QPushButton(_("clipboard.delete"), self)
        self.btn_clip_pin = QPushButton(_("clipboard.pin"), self)
        btn_row.addWidget(self.btn_clip_copy)
        btn_row.addWidget(self.btn_clip_delete)
        btn_row.addWidget(self.btn_clip_pin)
        right_panel.addLayout(btn_row)

        self.clip_preview_text = QTextEdit(self)
        self.clip_preview_text.setReadOnly(True)
        self.clip_preview_text.setPlaceholderText(_("clipboard.preview_placeholder"))
        right_panel.addWidget(self.clip_preview_text, 3)

        self.clip_preview_image = QLabel(self)
        self.clip_preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clip_preview_image.setMinimumHeight(200)
        self.clip_preview_image.setFrameShape(QFrame.Shape.StyledPanel)
        right_panel.addWidget(self.clip_preview_image, 2)

        row.addLayout(right_panel, 3)
        layout.addLayout(row)

        self.btn_clip_copy.clicked.connect(self.copy_selected_clip)
        self.btn_clip_delete.clicked.connect(self.delete_selected_clip)
        self.btn_clip_pin.clicked.connect(self.toggle_pin_selected_clip)

        self.refresh_clipboard_lists()

    def toggle_pin_section(self):
        expanded = self.btn_toggle_pin_section.isChecked()
        self.list_pinned.setVisible(expanded)
        self.btn_toggle_pin_section.setText("📌 釘選項目（展開）" if expanded else "📌 釘選項目（收合）")

    def _init_templates_tab(self):
        layout = QVBoxLayout(self.tab_templates)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.tpl_list = QListWidget(self)
        self.tpl_list.itemDoubleClicked.connect(self.edit_selected_template)
        layout.addWidget(self.tpl_list)

        row = QHBoxLayout()
        self.btn_tpl_add = QPushButton(_("templates.add"), self)
        self.btn_tpl_edit = QPushButton(_("templates.edit"), self)
        self.btn_tpl_delete = QPushButton(_("templates.delete"), self)
        self.btn_tpl_copy = QPushButton(_("templates.copy"), self)
        row.addWidget(self.btn_tpl_add)
        row.addWidget(self.btn_tpl_edit)
        row.addWidget(self.btn_tpl_delete)
        row.addWidget(self.btn_tpl_copy)
        layout.addLayout(row)

        self.tpl_preview = QTextEdit(self)
        self.tpl_preview.setReadOnly(True)
        self.tpl_preview.setFixedHeight(140)
        layout.addWidget(self.tpl_preview)

        self.btn_tpl_add.clicked.connect(self.add_template)
        self.btn_tpl_edit.clicked.connect(self.edit_selected_template)
        self.btn_tpl_delete.clicked.connect(self.delete_selected_template)
        self.btn_tpl_copy.clicked.connect(self.copy_selected_template)
        self.tpl_list.currentItemChanged.connect(self.update_template_preview)

        self.refresh_template_list()

    # --- clipboard helpers ---

    def _build_card_for_item(self, item_dict) -> QWidget:
        text = item_dict.get("preview") or item_dict.get("full_text", "")
        text = text.strip()
        if not text:
            text = "(空內容)"
        # meta: 可以之後擴充為時間戳，這裡先放類型
        meta = f"type: {item_dict.get('type', 'text')}"
        can_expand = len(text) > 80
        card = ClipCard(self, text, meta, bool(item_dict.get("pinned")), can_expand)
        return card

    def refresh_clipboard_lists(self):
        term = self.edit_search.text().strip().lower()
        self.list_pinned.clear()
        self.clip_list.clear()

        pinned_items = [c for c in self.storage.clipboard_items if c.get("pinned")]
        normal_items = [c for c in self.storage.clipboard_items if not c.get("pinned")]

        def add_items_to_list(target_list: QListWidget, items):
            for item in items:
                text = item.get("preview", "") or item.get("full_text", "")
                if term and term not in text.lower():
                    continue
                lw_item = QListWidgetItem(target_list)
                lw_item.setData(Qt.ItemDataRole.UserRole, item.get("id"))
                card = self._build_card_for_item(item)
                # 釘選按鈕行為
                card.btn_pin.clicked.connect(lambda checked=False, cid=item.get("id"): self.toggle_pin_by_id(cid))
                target_list.setItemWidget(lw_item, card)
                lw_item.setSizeHint(card.sizeHint())

        add_items_to_list(self.list_pinned, pinned_items)
        add_items_to_list(self.clip_list, normal_items)

    def on_clip_selection_changed(self, current, previous):
        if current is None:
            return
        cid = current.data(Qt.ItemDataRole.UserRole)
        self.update_clip_preview_by_id(cid)

    def get_selected_clip_id(self):
        cur = self.list_pinned.currentItem()
        if cur is None:
            cur = self.clip_list.currentItem()
        if cur is None:
            return None
        return cur.data(Qt.ItemDataRole.UserRole)

    def update_clip_preview_by_id(self, cid: str | None):
        self.clip_preview_text.clear()
        self.clip_preview_image.clear()
        if not cid:
            return
        clip = self.storage.get_clipboard_item(cid)
        if not clip:
            return
        ctype = clip.get("type", "text")
        self.clip_preview_text.setPlainText(clip.get("full_text", ""))
        if ctype == "image":
            path = clip.get("image_path")
            if path:
                p = Path(path)
                if p.exists():
                    pix = QPixmap(str(p))
                    if not pix.isNull():
                        self.clip_preview_image.setPixmap(
                            pix.scaledToHeight(260, Qt.TransformationMode.SmoothTransformation)
                        )

    def copy_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        clip = self.storage.get_clipboard_item(cid)
        if not clip:
            return
        text = clip.get("full_text", "")
        QApplication.clipboard().setText(text)

    def delete_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        self.storage.delete_clipboard_item(cid)
        self.storage.save_all()
        self.refresh_clipboard_lists()
        self.clip_preview_text.clear()
        self.clip_preview_image.clear()

    def toggle_pin_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        self.toggle_pin_by_id(cid)

    def toggle_pin_by_id(self, cid: str):
        clip = self.storage.get_clipboard_item(cid)
        if not clip:
            return
        clip["pinned"] = not bool(clip.get("pinned"))
        self.storage.save_all()
        self.refresh_clipboard_lists()

    # --- templates actions ---
    def refresh_template_list(self):
        self.tpl_list.clear()
        for tpl in self.storage.templates:
            item = QListWidgetItem(tpl.get("name", ""), self.tpl_list)
            item.setData(Qt.ItemDataRole.UserRole, tpl.get("id"))

    def get_selected_template_id(self):
        cur = self.tpl_list.currentItem()
        if not cur:
            return None
        return cur.data(Qt.ItemDataRole.UserRole)

    def update_template_preview(self):
        tid = self.get_selected_template_id()
        self.tpl_preview.clear()
        if not tid:
            return
        for tpl in self.storage.templates:
            if tpl.get("id") == tid:
                self.tpl_preview.setPlainText(tpl.get("content", "")[:500])
                break

    def add_template(self):
        dlg = TemplateEditorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, content = dlg.get_values()
            if not name:
                return
            tpl = {"id": str(uuid.uuid4()), "name": name, "content": content}
            self.storage.upsert_template(tpl)
            self.storage.save_all()
            self.refresh_template_list()

    def edit_selected_template(self):
        tid = self.get_selected_template_id()
        if not tid:
            return
        tpl = None
        for t in self.storage.templates:
            if t.get("id") == tid:
                tpl = t
                break
        if tpl is None:
            return
        dlg = TemplateEditorDialog(self, tpl.get("name", ""), tpl.get("content", ""))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, content = dlg.get_values()
            if not name:
                return
            tpl["name"] = name
            tpl["content"] = content
            self.storage.upsert_template(tpl)
            self.storage.save_all()
            self.refresh_template_list()
            self.update_template_preview()

    def delete_selected_template(self):
        tid = self.get_selected_template_id()
        if not tid:
            return
        self.storage.delete_template(tid)
        self.storage.save_all()
        self.refresh_template_list()
        self.tpl_preview.clear()

    def copy_selected_template(self):
        tid = self.get_selected_template_id()
        if not tid:
            return
        for tpl in self.storage.templates:
            if tpl.get("id") == tid:
                QApplication.clipboard().setText(tpl.get("content", ""))
                break

    # --- main menu / tray / cloud ---
    def show_main_menu(self):
        menu = QMenu(self)

        icon_settings = QIcon(str(self.base_dir / "assets" / "icon_settings.svg"))
        icon_info = QIcon(str(self.base_dir / "assets" / "icon_info.svg"))
        icon_help = QIcon(str(self.base_dir / "assets" / "icon_help.svg"))

        act_settings = QAction(icon_settings, _("menu.settings"), self)
        act_about = QAction(icon_info, _("menu.about"), self)
        act_manual = QAction(icon_help, _("menu.manual"), self)
        act_changelog = QAction(_("menu.changelog"), self)
        act_report = QAction(_("menu.report"), self)
        menu.addAction(act_settings)
        menu.addAction(act_about)
        menu.addAction(act_manual)
        menu.addAction(act_changelog)
        menu.addAction(act_report)

        act_settings.triggered.connect(self.open_settings)
        act_about.triggered.connect(self.show_about)
        act_manual.triggered.connect(self.show_manual)
        act_changelog.triggered.connect(self.show_changelog)
        act_report.triggered.connect(self.open_report_email)

        menu.exec(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomRight()))

    def open_settings(self):
        dlg = SettingsDialog(self, self.storage, self.lang_mgr, self.theme_mgr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # 重新套用主題與語言
            self.apply_theme()
            self.setup_global_hotkey()

    def show_about(self):
        QMessageBox.information(self, _("menu.about"), _("about.text"))

    def show_manual(self):
        path = self.base_dir / "docs" / "操作說明.txt"
        text = path.read_text(encoding="utf-8") if path.exists() else "(找不到操作說明.txt)"
        dlg = QDialog(self)
        dlg.setWindowTitle(_("manual.title"))
        lay = QVBoxLayout(dlg)
        edit = QTextEdit(dlg)
        edit.setReadOnly(True)
        edit.setPlainText(text)
        lay.addWidget(edit)
        dlg.resize(640, 520)
        dlg.exec()

    def show_changelog(self):
        path = self.base_dir / "docs" / "更新日誌.txt"
        text = path.read_text(encoding="utf-8") if path.exists() else "(找不到更新日誌.txt)"
        dlg = QDialog(self)
        dlg.setWindowTitle(_("changelog.title"))
        lay = QVBoxLayout(dlg)
        edit = QTextEdit(dlg)
        edit.setReadOnly(True)
        edit.setPlainText(text)
        lay.addWidget(edit)
        dlg.resize(640, 520)
        dlg.exec()

    def open_report_email(self):
        import webbrowser

        url = "https://mail.google.com/mail/?view=cm&to=trialscales0430@gmail.com&su=LightClip%20Feedback"
        webbrowser.open(url)

    def on_cloud_sync_clicked(self):
        # 匯出 JSON
        files = self.cloud_sync.export_json()
        # 上傳到 Google Drive
        try:
            self.google_sync.upload_files(files)
            QMessageBox.information(self, "Cloud", "已匯出並上傳到 Google Drive。")
        except Exception as e:  # pragma: no cover
            QMessageBox.warning(self, "Cloud", f"無法上傳到雲端：{e}")

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = self.windowIcon()
        if not icon.isNull():
            self.tray.setIcon(icon)
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        menu = QMenu(self)
        act_show = QAction("顯示主視窗", self)
        act_quit = QAction("退出", self)
        menu.addAction(act_show)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        act_show.triggered.connect(self.showNormal)
        act_quit.triggered.connect(QApplication.instance().quit)
        self.tray.show()

    def apply_theme(self):
        self.theme_mgr.set_theme(self.storage.settings.get("theme", "dark_default"))
        css = self.theme_mgr.build_stylesheet()
        QApplication.instance().setStyleSheet(css)

    # --- global hotkey ---
    def setup_global_hotkey(self):
        if keyboard is None:
            return
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        if not self.storage.settings.get("global_hotkey_enabled", False):
            return
        seq = self.storage.settings.get("global_hotkey", "ctrl+shift+v")

        def on_hotkey():
            self.showNormal()
            self.activateWindow()
            self.raise_()

        try:
            keyboard.add_hotkey(seq, on_hotkey)
            self.global_hotkey_registered = True
        except Exception:
            QMessageBox.warning(self, "Hotkey", "無法註冊全域快捷鍵，請嘗試其他組合或確認系統權限。")


def main():
    base = ensure_base_dir()
    app = QApplication(sys.argv)

    storage = StorageManager(base)
    lang_mgr = LanguageManager(base)
    theme_mgr = ThemeManager(base)

    # apply user settings
    lang_mgr.set_language(storage.settings.get("language", "zh_TW"))
    theme_mgr.set_theme(storage.settings.get("theme", "dark_default"))
    init_language_manager(lang_mgr)

    win = LightClipWindow(storage, lang_mgr, theme_mgr, base)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
