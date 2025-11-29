
import os
import sys
import datetime
from typing import List

from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, QLabel,
    QTextEdit, QComboBox, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QFileDialog, QSplitter
)

from app.storage import Storage
from app.models import ClipEntry


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "data.json")
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LightClip - 輕量剪貼簿工具")
        self.resize(900, 600)

        self.storage = Storage(DATA_FILE)

        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

        self._building_list = False

        self.init_ui()
        self.init_tray()
        self.refresh_list()

    # ---------------- UI -----------------

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        # 搜尋列 + 類型篩選
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜尋歷史內容、網址、檔名、標籤...")
        self.search_edit.textChanged.connect(self.refresh_list)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "文字", "圖片", "網址", "檔案", "釘選"])
        self.filter_combo.currentIndexChanged.connect(self.refresh_list)

        search_layout.addWidget(QLabel("搜尋："))
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(QLabel("類型："))
        search_layout.addWidget(self.filter_combo)

        main_layout.addLayout(search_layout)

        # 主區域：左側清單 + 右側預覽
        splitter = QSplitter()
        main_layout.addWidget(splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_pin = QPushButton("釘選/取消釘選")
        self.btn_delete = QPushButton("刪除")
        self.btn_copy = QPushButton("複製到剪貼簿")
        self.btn_clear = QPushButton("清除歷史(保留釘選)")

        self.btn_pin.clicked.connect(self.toggle_pin)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_copy.clicked.connect(self.copy_selected_to_clipboard)
        self.btn_clear.clicked.connect(self.clear_history_keep_pinned)

        for b in (self.btn_pin, self.btn_delete, self.btn_copy, self.btn_clear):
            btn_layout.addWidget(b)

        left_layout.addLayout(btn_layout)

        # 右側預覽
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        self.preview_title = QLabel("預覽")
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

    def init_tray(self):
        # 托盤圖示
        self.tray = QSystemTrayIcon(self)
        icon = self.windowIcon()
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.SP_FileDialogInfoView) if hasattr(self, "style") else QIcon()
        self.tray.setIcon(icon)
        self.tray.setToolTip("LightClip - 輕量剪貼簿工具")

        menu = QMenu()
        act_show = QAction("開啟視窗", self)
        act_quit = QAction("退出", self)

        act_show.triggered.connect(self.show_normal_from_tray)
        act_quit.triggered.connect(QApplication.instance().quit)

        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def show_normal_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 單擊
            if self.isHidden() or self.isMinimized():
                self.show_normal_from_tray()
            else:
                self.hide()

    def closeEvent(self, event):
        # 關閉時改為最小化到系統托盤
        if self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage("LightClip", "程式已縮小至系統托盤。", QSystemTrayIcon.Information, 3000)
        else:
            super().closeEvent(event)

    # ------------- 列表與預覽 ---------------

    def get_filtered_entries(self) -> List[ClipEntry]:
        keyword = self.search_edit.text().strip().lower()
        f = self.filter_combo.currentText()

        entries = self.storage.get_entries()

        # 類型篩選
        def match_type(e: ClipEntry) -> bool:
            if f == "全部":
                return True
            if f == "釘選":
                return e.pinned
            mapping = {
                "文字": "text",
                "圖片": "image",
                "網址": "url",
                "檔案": "file",
            }
            t = mapping.get(f)
            return e.type == t

        filtered = [e for e in entries if match_type(e)]

        # 關鍵字搜尋
        if keyword:
            result = []
            for e in filtered:
                text = (e.content or "").lower()
                tags = " ".join(e.tags or []).lower()
                if keyword in text or keyword in tags or keyword in (e.timestamp or "").lower():
                    result.append(e)
            filtered = result

        return filtered

    def refresh_list(self):
        self._building_list = True
        self.list_widget.clear()

        entries = self.get_filtered_entries()
        for e in entries:
            display = f"[{e.type}] {e.content}"
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

    def current_entry(self) -> ClipEntry:
        item = self.list_widget.currentItem()
        if not item:
            return None
        entry_id = item.data(Qt.UserRole)
        return self.get_entry_by_id(entry_id)

    def on_selection_changed(self, current, previous):
        if self._building_list:
            return
        entry = self.current_entry()
        if not entry:
            self.preview_area.clear()
            self.image_label.clear()
            self.image_label.setVisible(False)
            return

        self.preview_title.setText(f"預覽 - ID {entry.id} ({entry.type})")
        self.image_label.clear()
        self.image_label.setVisible(False)

        if entry.type == "text" or entry.type == "url" or entry.type == "file":
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

    # ------------- 操作按鈕 ---------------

    def toggle_pin(self):
        entry = self.current_entry()
        if not entry:
            return
        entry.pinned = not entry.pinned
        self.storage.update_entry(entry)
        self.refresh_list()

    def delete_selected(self):
        entry = self.current_entry()
        if not entry:
            return
        reply = QMessageBox.question(self, "刪除確認", "確定要刪除此項目？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.storage.delete_entry(entry.id)
            self.refresh_list()

    def copy_selected_to_clipboard(self):
        entry = self.current_entry()
        if not entry:
            return
        if entry.type in ("text", "url", "file"):
            self.clipboard.setText(entry.content)
        elif entry.type == "image":
            img_path = entry.extra.get("image_path") if entry.extra else None
            if img_path and os.path.exists(img_path):
                pix = QPixmap(img_path)
                self.clipboard.setPixmap(pix)
        # 不強制模擬貼上，讓使用者自行 Ctrl+V

    def clear_history_keep_pinned(self):
        reply = QMessageBox.question(self, "清除確認", "確定要清除所有非釘選歷史？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.storage.clear_history(keep_pinned=True)
            self.refresh_list()

    # ------------- 剪貼簿監聽 ---------------

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
                now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                img_path = os.path.join(IMAGE_DIR, f"clip_{now}.png")
                image.save(img_path, "PNG")
                content = img_path
                extra["image_path"] = img_path
        elif mime.hasUrls():
            urls = mime.urls()
            if urls:
                # 若是本機檔案
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

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = ClipEntry(
            id=self.storage.next_id(),
            type=entry_type,
            content=content,
            timestamp=timestamp,
            pinned=False,
            tags=[],
            extra=extra
        )
        self.storage.add_entry(new_entry)
        # 只有在目前顯示的篩選條件符合時才刷新
        self.refresh_list()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
