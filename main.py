
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
    QStackedWidget,
    QScrollArea,
    QSplitter,
)

try:
    import keyboard  # type: ignore[import]
except Exception:  # pragma: no cover
    keyboard = None

from app.storage import StorageManager
from app.language import LanguageManager, _, init_language_manager
from app.theme import ThemeManager
from app.cloud_sync import CloudSync
from app.google_sync import GoogleDriveSync
from app.ocr_engine import OCREngine
from app.translator import Translator

APP_VERSION = "1.9"


def ensure_base_dir() -> Path:
    return Path(__file__).resolve().parent


# ---------- custom widgets ----------


class ClipListWidget(QListWidget):
    """自訂列表，在視窗縮放時重新計算 item size，改善自動換行效果。"""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i in range(self.count()):
            item = self.item(i)
            w = self.itemWidget(item)
            if w is not None:
                item.setSizeHint(w.sizeHint())


class ClipCard(QWidget):
    """剪貼簿項目的卡片：自動換行、最多 3 行，可展開。"""

    def __init__(self, parent, text: str, meta: str, pinned: bool, can_expand: bool):
        super().__init__(parent)
        self._expanded = False
        self._can_expand = can_expand

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        frame = QFrame(self)
        frame.setObjectName("CardFrame")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 8, 10, 8)
        fl.setSpacing(4)

        top_row = QHBoxLayout()
        self.btn_pin = QPushButton(frame)
        self.btn_pin.setFlat(True)
        self.btn_pin.setIconSize(QSize(18, 18))
        top_row.addWidget(self.btn_pin)
        top_row.addStretch(1)
        self.btn_expand = QPushButton("展開", frame)
        self.btn_expand.setFlat(True)
        self.btn_expand.setVisible(can_expand)
        top_row.addWidget(self.btn_expand)
        fl.addLayout(top_row)

        self.lbl_text = QLabel(text, frame)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setMinimumHeight(24)
        fl.addWidget(self.lbl_text)

        self.lbl_meta = QLabel(meta, frame)
        self.lbl_meta.setObjectName("metaLabel")
        fl.addWidget(self.lbl_meta)

        root.addWidget(frame)

        self.set_pinned(pinned)
        self._set_collapsed_height()
        self.btn_expand.clicked.connect(self.toggle_expand)

    def set_pinned(self, pinned: bool):
        base = ensure_base_dir() / "assets"
        icon_name = "icon_pin_filled.svg" if pinned else "icon_pin_outline.svg"
        icon = QIcon(str(base / icon_name))
        self.btn_pin.setIcon(icon)

    def _set_collapsed_height(self):
        fm = self.lbl_text.fontMetrics()
        max_h = fm.lineSpacing() * 3 + 8
        self.lbl_text.setMaximumHeight(max_h)

    def toggle_expand(self):
        if not self._can_expand:
            return
        self._expanded = not self._expanded
        if self._expanded:
            self.lbl_text.setMaximumHeight(16777215)
            self.btn_expand.setText("收合")
        else:
            self._set_collapsed_height()
            self.btn_expand.setText("展開")


class SettingsDialog(QDialog):
    def __init__(self, parent, storage: StorageManager, lang_mgr: LanguageManager, theme_mgr: ThemeManager):
        super().__init__(parent)
        self.storage = storage
        self.lang_mgr = lang_mgr
        self.theme_mgr = theme_mgr

        self.setWindowTitle(_("settings.title"))
        layout = QFormLayout(self)
        layout.setVerticalSpacing(10)
        layout.setSpacing(10)

        self.spin_history = QSpinBox(self)
        self.spin_history.setRange(10, 2000)
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

        # 分類管理
        self.btn_manage_categories = QPushButton("管理分類…", self)
        layout.addRow(self.btn_manage_categories)

        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton(_("settings.apply"), self)
        self.btn_cancel = QPushButton(_("settings.cancel"), self)
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_cancel)
        layout.addRow(btn_row)

        self.btn_apply.clicked.connect(self.apply)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_manage_categories.clicked.connect(self.manage_categories)

    def manage_categories(self):
        # 簡單對話框：一行一個分類
        dlg = QDialog(self)
        dlg.setWindowTitle("管理分類")
        lay = QVBoxLayout(dlg)
        edit = QTextEdit(dlg)
        cats = self.storage.settings.get("categories", [])
        edit.setPlainText("\n".join(cats))
        lay.addWidget(edit)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("確定", dlg)
        btn_cancel = QPushButton("取消", dlg)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        def apply_cats():
            text = edit.toPlainText().strip()
            if text:
                cats_new = [c.strip() for c in text.splitlines() if c.strip()]
                if cats_new:
                    self.storage.settings["categories"] = cats_new
            dlg.accept()

        btn_ok.clicked.connect(apply_cats)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.resize(360, 260)
        dlg.exec()

    def apply(self):
        self.storage.settings["max_history"] = int(self.spin_history.value())
        lang_code = self.combo_lang.currentData()
        theme_key = self.combo_theme.currentData()
        self.storage.settings["language"] = lang_code
        self.storage.settings["theme"] = theme_key
        self.storage.settings["global_hotkey_enabled"] = self.chk_hotkey.isChecked()
        self.storage.settings["global_hotkey"] = self.edit_hotkey.text().strip() or "ctrl+shift+v"
        self.storage.save_all()

        self.lang_mgr.set_language(lang_code)
        self.theme_mgr.set_theme(theme_key)
        QMessageBox.information(self, _("settings.title"), _("settings.restart_hint"))
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

        btn_row = QHBoxLayout()
        self.btn_ok = QPushButton("確定", self)
        self.btn_cancel = QPushButton("取消", self)
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_values(self):
        return self.edit_name.text().strip(), self.edit_content.toPlainText()


class CategoryDialog(QDialog):
    """選擇某個項目的分類。"""

    def __init__(self, parent, categories, current: str = ""):
        super().__init__(parent)
        self.setWindowTitle("變更分類")
        lay = QVBoxLayout(self)
        self.combo = QComboBox(self)
        for c in categories:
            self.combo.addItem(c, c)
        if current:
            idx = self.combo.findData(current)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        lay.addWidget(self.combo)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("確定", self)
        btn_cancel = QPushButton("取消", self)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    def get_category(self) -> str:
        return self.combo.currentData()


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
        self.current_image_path: Optional[Path] = None

        # OCR & translation engines
        self.ocr_engine = OCREngine(base_dir)
        self.translator = Translator(self.storage.settings.get("language", "zh_TW"))


        init_language_manager(lang_mgr)

        self.setWindowTitle(_("app.title"))
        self.resize(1000, 680)

        logo_svg = self.base_dir / "assets" / "lightclip_logo.svg"
        if logo_svg.exists():
            self.setWindowIcon(QIcon(str(logo_svg)))

        self._init_ui()
        self.apply_theme()
        self.setup_tray()
        self.setup_global_hotkey()
        self.setup_clipboard_listener()

    # ---------- UI ----------
    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # top bar: title + tab buttons + cloud + menu
        top = QHBoxLayout()
        self.lbl_title = QLabel("LightClip", self)
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: 600;")
        top.addWidget(self.lbl_title)

        self.btn_tab_clip = QPushButton(_("ui.tab.clipboard"), self)
        self.btn_tab_tpl = QPushButton(_("ui.tab.templates"), self)
        self.btn_tab_category = QPushButton("分類", self)
        self.btn_tab_screenshot = QPushButton("截圖", self)
        for btn in (self.btn_tab_clip, self.btn_tab_tpl, self.btn_tab_category, self.btn_tab_screenshot):
            btn.setCheckable(True)
            btn.setFlat(True)
        self.btn_tab_clip.setChecked(True)
        top.addWidget(self.btn_tab_clip)
        top.addWidget(self.btn_tab_tpl)
        top.addWidget(self.btn_tab_category)
        top.addWidget(self.btn_tab_screenshot)
        top.addStretch(1)

        # cloud button
        self.btn_cloud = QPushButton(self)
        self.btn_cloud.setFlat(True)
        self.btn_cloud.setFixedSize(36, 32)
        self.btn_cloud.setIconSize(QSize(22, 22))
        cloud_icon = QIcon(str(self.base_dir / "assets" / "icon_cloud.svg"))
        self.btn_cloud.setIcon(cloud_icon)
        self.btn_cloud.clicked.connect(self.on_cloud_sync_clicked)
        top.addWidget(self.btn_cloud)

        # menu button
        self.btn_menu = QPushButton(self)
        self.btn_menu.setFlat(True)
        self.btn_menu.setFixedSize(36, 32)
        self.btn_menu.setIconSize(QSize(20, 20))
        more_icon = QIcon(str(self.base_dir / "assets" / "icon_more.svg"))
        self.btn_menu.setIcon(more_icon)
        self.btn_menu.clicked.connect(self.show_main_menu)
        top.addWidget(self.btn_menu)

        root.addLayout(top)

        # stacked pages
        self.stack = QStackedWidget(self)
        self.page_clipboard = QWidget(self)
        self.page_templates = QWidget(self)
        self.page_categories = QWidget(self)
        self.page_screenshots = QWidget(self)
        self.stack.addWidget(self.page_clipboard)    # index 0
        self.stack.addWidget(self.page_templates)    # index 1
        self.stack.addWidget(self.page_categories)   # index 2
        self.stack.addWidget(self.page_screenshots)  # index 3
        root.addWidget(self.stack)

        self.btn_tab_clip.clicked.connect(lambda: self.switch_tab(0))
        self.btn_tab_tpl.clicked.connect(lambda: self.switch_tab(1))
        self.btn_tab_category.clicked.connect(lambda: self.switch_tab(2))
        self.btn_tab_screenshot.clicked.connect(lambda: self.switch_tab(3))

        self._init_clipboard_page()
        self._init_templates_page()

    def switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_tab_clip.setChecked(index == 0)
        self.btn_tab_tpl.setChecked(index == 1)
        self.btn_tab_category.setChecked(index == 2)
        self.btn_tab_screenshot.setChecked(index == 3)

    def _init_clipboard_page(self):
        layout = QVBoxLayout(self.page_clipboard)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # pinned header row
        header = QHBoxLayout()
        self.btn_toggle_pin = QPushButton("📌 釘選項目（展開）", self)
        self.btn_toggle_pin.setCheckable(True)
        self.btn_toggle_pin.setChecked(True)
        self.btn_toggle_pin.setFlat(True)
        header.addWidget(self.btn_toggle_pin)

        self.btn_clear_history = QPushButton("刪除歷史紀錄", self)
        header.addWidget(self.btn_clear_history)

        header.addSpacing(12)
        header.addWidget(QLabel("分類：", self))
        self.combo_category = QComboBox(self)
        self.refresh_category_combo()
        header.addWidget(self.combo_category)

        layout.addLayout(header)

        # pinned list
        self.list_pinned = ClipListWidget(self)
        self.list_pinned.setSpacing(6)
        layout.addWidget(self.list_pinned)

        # search row
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(_("ui.search.placeholder"), self))
        self.edit_search = QLineEdit(self)
        self.edit_search.setPlaceholderText(_("ui.search.placeholder"))
        search_row.addWidget(self.edit_search)
        layout.addLayout(search_row)

        # main row lists + preview
        row = QHBoxLayout()

        self.clip_list = ClipListWidget(self)
        self.clip_list.setSpacing(6)
        row.addWidget(self.clip_list, 2)

        right = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_clip_copy = QPushButton(_("clipboard.copy"), self)
        self.btn_clip_delete = QPushButton(_("clipboard.delete"), self)
        self.btn_clip_pin = QPushButton(_("clipboard.pin"), self)
        self.btn_clip_category = QPushButton(_("clipboard.category"), self)
        self.btn_clip_translate = QPushButton("翻譯", self)
        btn_row.addWidget(self.btn_clip_copy)
        btn_row.addWidget(self.btn_clip_delete)
        btn_row.addWidget(self.btn_clip_pin)
        btn_row.addWidget(self.btn_clip_category)
        btn_row.addWidget(self.btn_clip_translate)
        right.addLayout(btn_row)

        self.clip_preview_text = QTextEdit(self)
        self.clip_preview_text.setReadOnly(True)
        self.clip_preview_text.setPlaceholderText(_("clipboard.preview_placeholder"))
        right.addWidget(self.clip_preview_text, 3)

        self.clip_preview_image = QLabel(self)
        self.clip_preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clip_preview_image.setMinimumHeight(200)
        self.clip_preview_image.setFrameShape(QFrame.Shape.StyledPanel)
        right.addWidget(self.clip_preview_image, 2)

        row.addLayout(right, 3)
        layout.addLayout(row)

        # connections
        self.btn_toggle_pin.toggled.connect(self.toggle_pin_section)
        self.btn_clear_history.clicked.connect(self.clear_history)
        self.combo_category.currentIndexChanged.connect(self.refresh_clipboard_lists)
        self.edit_search.textChanged.connect(self.refresh_clipboard_lists)

        self.list_pinned.currentItemChanged.connect(self.on_clip_selection_changed)
        self.clip_list.currentItemChanged.connect(self.on_clip_selection_changed)

        self.btn_clip_copy.clicked.connect(self.copy_selected_clip)
        self.btn_clip_delete.clicked.connect(self.delete_selected_clip)
        self.btn_clip_pin.clicked.connect(self.toggle_pin_selected_clip)
        self.btn_clip_category.clicked.connect(self.change_category_selected_clip)
        self.btn_clip_translate.clicked.connect(self.translate_selected_clip)

        # 可點擊放大圖片
        self.clip_preview_image.mousePressEvent = self.on_image_clicked  # type: ignore[assignment]

        self.refresh_clipboard_lists()

    def _init_templates_page(self):
        layout = QVBoxLayout(self.page_templates)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.tpl_list = QListWidget(self)
        layout.addWidget(self.tpl_list)

        btn_row = QHBoxLayout()
        self.btn_tpl_add = QPushButton(_("templates.add"), self)
        self.btn_tpl_edit = QPushButton(_("templates.edit"), self)
        self.btn_tpl_delete = QPushButton(_("templates.delete"), self)
        self.btn_tpl_copy = QPushButton(_("templates.copy"), self)
        btn_row.addWidget(self.btn_tpl_add)
        btn_row.addWidget(self.btn_tpl_edit)
        btn_row.addWidget(self.btn_tpl_delete)
        btn_row.addWidget(self.btn_tpl_copy)
        layout.addLayout(btn_row)

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

    # ---------- clipboard logic ----------
    def refresh_category_combo(self):
        self.combo_category.clear()
        self.combo_category.addItem("全部", "ALL")
        for c in self.storage.settings.get("categories", []):
            self.combo_category.addItem(c, c)

    def toggle_pin_section(self, checked: bool):
        self.list_pinned.setVisible(checked)
        self.btn_toggle_pin.setText("📌 釘選項目（展開）" if checked else "📌 釘選項目（收合）")

    def clear_history(self):
        reply = QMessageBox.question(
            self,
            "刪除歷史紀錄",
            "確定要刪除所有歷史紀錄嗎？（釘選項目將會保留）",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.storage.clear_history(keep_pinned=True)
            self.storage.save_all()
            self.refresh_clipboard_lists()
            self.clip_preview_text.clear()
            self.clip_preview_image.clear()

    def _build_card_for_item(self, item_dict) -> QWidget:
        text = item_dict.get("preview") or item_dict.get("full_text", "")
        text = (text or "").strip()
        if not text:
            text = "(空內容)"
        ctype = item_dict.get("type", "text")
        category = item_dict.get("category", "")
        meta_parts = [f"type: {ctype}"]
        if category:
            meta_parts.append(f"category: {category}")
        meta = " | ".join(meta_parts)
        can_expand = len(text) > 80
        card = ClipCard(self, text, meta, bool(item_dict.get("pinned")), can_expand)
        return card

    def refresh_clipboard_lists(self):
        term = self.edit_search.text().strip().lower()
        current_cat = self.combo_category.currentData()
        self.list_pinned.clear()
        self.clip_list.clear()

        pinned_items = [c for c in self.storage.clipboard_items if c.get("pinned")]
        normal_items = [c for c in self.storage.clipboard_items if not c.get("pinned")]

        def match_filters(item):
            text = (item.get("preview") or item.get("full_text") or "").lower()
            if term and term not in text:
                return False
            if current_cat and current_cat != "ALL":
                cat = item.get("category") or self._infer_category(item)
                return cat == current_cat
            return True

        def add_items_to_list(target_list: QListWidget, items):
            for item in items:
                if not match_filters(item):
                    continue
                lw_item = QListWidgetItem(target_list)
                lw_item.setData(Qt.ItemDataRole.UserRole, item.get("id"))
                card = self._build_card_for_item(item)
                card.btn_pin.clicked.connect(lambda checked=False, cid=item.get("id"): self.toggle_pin_by_id(cid))
                target_list.setItemWidget(lw_item, card)
                lw_item.setSizeHint(card.sizeHint())

        add_items_to_list(self.list_pinned, pinned_items)
        add_items_to_list(self.clip_list, normal_items)

        # 更新分類與截圖分頁
        if hasattr(self, "page_categories"):
            self.refresh_categories_page()
        if hasattr(self, "page_screenshots"):
            self.refresh_screenshot_page()

    def _infer_category(self, item) -> str:
        ctype = item.get("type", "text")
        if ctype == "image":
            return "圖片"
        if ctype == "file":
            return "檔案"
        return "文字"

    def on_clip_selection_changed(self, current, previous):
        if current is None:
            return
        cid = current.data(Qt.ItemDataRole.UserRole)
        self.update_clip_preview_by_id(cid)

    def get_selected_clip_id(self) -> Optional[str]:
        cur = None
        # 分類分頁：優先取分類列表的選中項目
        if hasattr(self, "page_categories") and self.stack.currentWidget() is self.page_categories:
            if hasattr(self, "list_category_items"):
                cur = self.list_category_items.currentItem()
        # 截圖分頁：取截圖列表選中項目
        if cur is None and hasattr(self, "page_screenshots") and self.stack.currentWidget() is self.page_screenshots:
            if hasattr(self, "list_screenshots"):
                cur = self.list_screenshots.currentItem()
        # 其他情況：沿用原本 pinned + 主列表邏輯
        if cur is None:
            cur = self.list_pinned.currentItem()
        if cur is None:
            cur = self.clip_list.currentItem()
        if cur is None:
            return None
        return cur.data(Qt.ItemDataRole.UserRole)

    def update_clip_preview_by_id(self, cid: Optional[str]):
        self.clip_preview_text.clear()
        self.clip_preview_image.clear()
        self.current_image_path = None
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
                    self.current_image_path = p
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

def translate_selected_clip(self):
    """Translate current clip (text or image via OCR) and show result in a dialog."""
    cid = self.get_selected_clip_id()
    if not cid:
        return
    clip = self.storage.get_clipboard_item(cid)
    if not clip:
        return

    ctype = clip.get("type", "text")
    source_text = ""

    try:
        if ctype == "image":
            path = clip.get("image_path")
            if not path:
                QMessageBox.information(self, "翻譯", "找不到圖片路徑。")
                return
            p = Path(path)
            if not p.exists():
                QMessageBox.information(self, "翻譯", "圖片檔案不存在。")
                return
            source_text = self.ocr_engine.extract_text(p)
            if not source_text.strip():
                QMessageBox.information(self, "翻譯", "圖片中未辨識出明顯文字。")
                return
        else:
            source_text = clip.get("full_text", "") or clip.get("preview", "") or ""
            if not source_text.strip():
                QMessageBox.information(self, "翻譯", "此項目沒有可翻譯的文字內容。")
                return

        ui_lang = self.storage.settings.get("language", "zh_TW")
        # default: if UI is Chinese, translate to English; otherwise translate to Traditional Chinese
        target_lang = "en" if ui_lang.startswith("zh") else "zh-TW"

        translated = self.translator.translate(source_text, target_lang=target_lang)

        dlg = QDialog(self)
        dlg.setWindowTitle("翻譯結果")
        lay = QVBoxLayout(dlg)

        src_label = QLabel("原文：", dlg)
        src_edit = QTextEdit(dlg)
        src_edit.setReadOnly(True)
        src_edit.setPlainText(source_text.strip())

        dst_label = QLabel(f"翻譯（{target_lang}）：", dlg)
        dst_edit = QTextEdit(dlg)
        dst_edit.setReadOnly(True)
        dst_edit.setPlainText(translated.strip())

        lay.addWidget(src_label)
        lay.addWidget(src_edit)
        lay.addWidget(dst_label)
        lay.addWidget(dst_edit)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("關閉", dlg)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

        btn_ok.clicked.connect(dlg.accept)

        dlg.resize(640, 480)
        dlg.exec()
    except Exception as e:
        QMessageBox.warning(self, "翻譯", f"翻譯過程發生錯誤：{e}")

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

    def change_category_selected_clip(self):
        cid = self.get_selected_clip_id()
        if not cid:
            return
        clip = self.storage.get_clipboard_item(cid)
        if not clip:
            return
        cats = self.storage.settings.get("categories", [])
        cur = clip.get("category") or self._infer_category(clip)
        dlg = CategoryDialog(self, cats, current=cur)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_cat = dlg.get_category()
            clip["category"] = new_cat
            self.storage.save_all()
            self.refresh_clipboard_lists()
            self.update_clip_preview_by_id(cid)

    def on_image_clicked(self, event):
        if not self.current_image_path or not self.current_image_path.exists():
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("圖片預覽")
        lay = QVBoxLayout(dlg)
        scroll = QScrollArea(dlg)
        lbl = QLabel(dlg)
        pix = QPixmap(str(self.current_image_path))
        lbl.setPixmap(pix)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(lbl)
        scroll.setWidgetResizable(True)
        lay.addWidget(scroll)
        dlg.resize(800, 600)
        dlg.exec()

    # ---------- templates ----------
    def refresh_template_list(self):
        self.tpl_list.clear()
        for tpl in self.storage.templates:
            item = QListWidgetItem(tpl.get("name", ""), self.tpl_list)
            item.setData(Qt.ItemDataRole.UserRole, tpl.get("id"))

    def get_selected_template_id(self) -> Optional[str]:
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
        tpl = next((t for t in self.storage.templates if t.get("id") == tid), None)
        if not tpl:
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

    # ---------- menu / tray / theme ----------
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
            self.apply_theme()
            self.setup_global_hotkey()
            self.refresh_category_combo()
            self.refresh_clipboard_lists()

    def show_about(self):
        QMessageBox.information(self, _("menu.about"), _("about.text"))

    def _read_text_file(self, rel: str) -> str:
        path = self.base_dir / "docs" / rel
        if not path.exists():
            return "(找不到 " + rel + ")"
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return "(無法讀取 " + rel + ")"

    def show_manual(self):
        text = self._read_text_file("操作說明.txt")
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
        text = self._read_text_file("更新日誌.txt")
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
        files = self.cloud_sync.export_json()
        try:
            self.google_sync.upload_files(files)
            QMessageBox.information(self, "Cloud", "已匯出資料，並可手動上傳至雲端。")
        except Exception as e:
            QMessageBox.warning(self, "Cloud", f"雲端同步時發生錯誤：{e}")

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = self.windowIcon()
        if not icon.isNull():
            self.tray.setIcon(icon)
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        menu = QMenu(self)
        act_show = QAction("顯示 LightClip", self)
        act_quit = QAction("結束", self)
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

    # ---------- global hotkey & clipboard listener ----------
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
        except Exception:
            QMessageBox.warning(self, "Hotkey", "無法註冊全域快捷鍵，請嘗試其他組合或確認系統權限。")

    def setup_clipboard_listener(self):
        cb = QApplication.clipboard()
        cb.dataChanged.connect(self.on_clipboard_changed)
        self._last_clip_signature = None

    def on_clipboard_changed(self):
        cb = QApplication.clipboard()
        mime = cb.mimeData()

        # text
        text = cb.text()
        img = cb.image()

        if img is not None and not img.isNull():
            sig = f"image:{img.size().width()}x{img.size().height()}"
        else:
            sig = f"text:{text}"
        if sig == getattr(self, "_last_clip_signature", None):
            return
        self._last_clip_signature = sig

        item = {
            "id": str(uuid.uuid4()),
            "pinned": False,
        }

        if img is not None and not img.isNull():
            # save image
            images_dir = self.base_dir / "data" / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{item['id']}.png"
            path = images_dir / filename
            img.save(str(path), "PNG")
            item["type"] = "image"
            item["image_path"] = str(path)
            item["full_text"] = ""
            item["preview"] = f"[圖片] {path.name}"
            item["category"] = "圖片"
        else:
            text = text or ""
            if not text.strip():
                return
            item["type"] = "text"
            item["full_text"] = text
            preview = text.strip().replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."
            item["preview"] = preview
            item["category"] = "文字"

        self.storage.add_clipboard_item(item)
        self.storage.save_all()
        self.refresh_clipboard_lists()

    # ---------- main ----------




    
    # === Categories & Screenshot Pages ===

    def _init_categories_page(self):
        """分類分頁：左側分類列表，右側該分類項目列表（共用下方預覽區）。"""
        layout = QVBoxLayout(self.page_categories)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Horizontal, self.page_categories)
        layout.addWidget(splitter, 1)

        # 左側分類列表
        self.list_categories = QListWidget(self)
        self.list_categories.setFixedWidth(140)
        splitter.addWidget(self.list_categories)

        # 右側該分類項目列表
        self.list_category_items = ClipListWidget(self)
        splitter.addWidget(self.list_category_items)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # 下方操作列
        btn_row = QHBoxLayout()
        self.btn_cat_copy = QPushButton("複製", self)
        self.btn_cat_delete = QPushButton("刪除", self)
        self.btn_cat_pin = QPushButton("釘選 / 取消釘選", self)
        btn_row.addWidget(self.btn_cat_copy)
        btn_row.addWidget(self.btn_cat_delete)
        btn_row.addWidget(self.btn_cat_pin)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # 事件
        self.list_categories.currentItemChanged.connect(self.on_category_selected)
        self.list_category_items.itemSelectionChanged.connect(self.on_clip_selection_changed)
        self.list_category_items.itemDoubleClicked.connect(self.copy_selected_clip)

        self.btn_cat_copy.clicked.connect(self.copy_selected_clip)
        self.btn_cat_delete.clicked.connect(self.delete_selected_clip)
        self.btn_cat_pin.clicked.connect(self.toggle_pin_selected_clip)

        # 初始資料
        self.refresh_categories_page()

    def refresh_categories_page(self):
        """重建分類列表與右側內容。"""
        if not hasattr(self, "list_categories"):
            return

        by_cat = {}
        for clip in self.storage.clipboard_items:
            cat = clip.get("category") or self._infer_category(clip) or "未分類"
            by_cat.setdefault(cat, []).append(clip)

        # 左側分類列表
        self.list_categories.blockSignals(True)
        self.list_categories.clear()
        for cat in sorted(by_cat.keys()):
            self.list_categories.addItem(cat)
        self.list_categories.blockSignals(False)

        # 如果沒有選擇，就自動選第一個
        if self.list_categories.currentItem() is None and self.list_categories.count() > 0:
            self.list_categories.setCurrentRow(0)

        self._rebuild_category_items(by_cat)

    def on_category_selected(self, current, previous):
        if not current:
            return
        by_cat = {}
        for clip in self.storage.clipboard_items:
            cat = clip.get("category") or self._infer_category(clip) or "未分類"
            by_cat.setdefault(cat, []).append(clip)
        self._rebuild_category_items(by_cat)

    def _rebuild_category_items(self, by_cat: dict):
        if not hasattr(self, "list_category_items"):
            return
        cat_item = self.list_categories.currentItem()
        if not cat_item:
            self.list_category_items.clear()
            return

        cat_name = cat_item.text()
        items = by_cat.get(cat_name, [])

        self.list_category_items.clear()
        for clip in items:
            lw_item = QListWidgetItem(self.list_category_items)
            lw_item.setData(Qt.ItemDataRole.UserRole, clip.get("id"))
            card = self._build_card_for_item(clip)
            card.btn_pin.clicked.connect(
                lambda checked=False, cid=clip.get("id"): self.toggle_pin_by_id(cid)
            )
            self.list_category_items.setItemWidget(lw_item, card)
            lw_item.setSizeHint(card.sizeHint())

    def _init_screenshot_page(self):
        """截圖分頁：左側圖片型項目列表，右側獨立大圖預覽。"""
        layout = QVBoxLayout(self.page_screenshots)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Horizontal, self.page_screenshots)
        layout.addWidget(splitter, 1)

        # 左側：所有圖片項目
        self.list_screenshots = ClipListWidget(self)
        splitter.addWidget(self.list_screenshots)

        # 右側：大圖預覽
        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)

        self.label_ss_preview = QLabel("選擇左側截圖以預覽", self)
        self.label_ss_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_ss_preview.setMinimumSize(320, 240)
        self.label_ss_preview.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout.addWidget(self.label_ss_preview, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # 下方操作列
        btn_row = QHBoxLayout()
        self.btn_ss_copy = QPushButton("複製", self)
        self.btn_ss_delete = QPushButton("刪除", self)
        self.btn_ss_pin = QPushButton("釘選 / 取消釘選", self)
        btn_row.addWidget(self.btn_ss_copy)
        btn_row.addWidget(self.btn_ss_delete)
        btn_row.addWidget(self.btn_ss_pin)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # 事件
        self.list_screenshots.itemSelectionChanged.connect(self.update_screenshot_preview)
        self.list_screenshots.itemDoubleClicked.connect(self.copy_selected_clip)

        self.btn_ss_copy.clicked.connect(self.copy_selected_clip)
        self.btn_ss_delete.clicked.connect(self.delete_selected_clip)
        self.btn_ss_pin.clicked.connect(self.toggle_pin_selected_clip)

        # 初始資料
        self.refresh_screenshot_page()

    def refresh_screenshot_page(self):
        """刷新截圖分頁：列出所有圖片型項目。"""
        if not hasattr(self, "list_screenshots"):
            return

        self.list_screenshots.clear()
        for clip in self.storage.clipboard_items:
            if clip.get("type") != "image":
                continue
            lw_item = QListWidgetItem(self.list_screenshots)
            lw_item.setData(Qt.ItemDataRole.UserRole, clip.get("id"))
            card = self._build_card_for_item(clip)
            card.btn_pin.clicked.connect(
                lambda checked=False, cid=clip.get("id"): self.toggle_pin_by_id(cid)
            )
            self.list_screenshots.setItemWidget(lw_item, card)
            lw_item.setSizeHint(card.sizeHint())

        # 更新右側預覽
        self.update_screenshot_preview()

    def update_screenshot_preview(self):
        """更新右側截圖預覽，不影響主剪貼簿預覽。"""
        if not hasattr(self, "label_ss_preview"):
            return

        item = self.list_screenshots.currentItem() if hasattr(self, "list_screenshots") else None
        if item is None:
            self.label_ss_preview.setText("選擇左側截圖以預覽")
            self.label_ss_preview.setPixmap(QPixmap())
            return

        cid = item.data(Qt.ItemDataRole.UserRole)
        clip = self.storage.get_clipboard_item(cid)
        if not clip or clip.get("type") != "image":
            self.label_ss_preview.setText("非圖片項目")
            self.label_ss_preview.setPixmap(QPixmap())
            return

        path = clip.get("image_path")
        if not path:
            self.label_ss_preview.setText("找不到圖片檔案")
            self.label_ss_preview.setPixmap(QPixmap())
            return

        p = Path(path)
        if not p.exists():
            self.label_ss_preview.setText("找不到圖片檔案")
            self.label_ss_preview.setPixmap(QPixmap())
            return

        pix = QPixmap(str(p))
        if pix.isNull():
            self.label_ss_preview.setText("無法載入圖片")
            self.label_ss_preview.setPixmap(QPixmap())
            return

        target_size = self.label_ss_preview.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            self.label_ss_preview.setPixmap(pix)
            return

        scaled = pix.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label_ss_preview.setPixmap(scaled)
def main():
    base_dir = ensure_base_dir()
    app = QApplication(sys.argv)

    storage = StorageManager(base_dir)
    lang_mgr = LanguageManager(base_dir)
    theme_mgr = ThemeManager()

    lang_mgr.set_language(storage.settings.get("language", "zh_TW"))
    theme_mgr.set_theme(storage.settings.get("theme", "dark_default"))
    init_language_manager(lang_mgr)

    win = LightClipWindow(storage, lang_mgr, theme_mgr, base_dir)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

