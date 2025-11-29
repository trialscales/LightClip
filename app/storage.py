
from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import QImage


class StorageManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.data_path = base_dir / "data" / "data.json"
        self.image_dir = base_dir / "data" / "images"
        self.docs_dir = base_dir / "docs"
        self.languages_dir = base_dir / "languages"
        self.image_dir.mkdir(parents=True, exist_ok=True)

        self.clipboard_items: list[dict] = []
        self.templates: list[dict] = []
        self.settings: dict = {
            "max_history": 100,
            "language": "zh_TW",
            "theme": "dark_default",
        }

        self.load_all()

    # --- load/save ---

    def load_all(self):
        if not self.data_path.exists():
            self.save_all()
            return
        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
        except Exception:
            return

        self.clipboard_items = raw.get("clipboard", [])
        self.templates = raw.get("templates", [])
        self.settings.update(raw.get("settings", {}))

        # sort clipboard: pinned first, then newest
        self.clipboard_items.sort(key=lambda x: (not x.get("pinned", False), x.get("timestamp", "")), reverse=True)

    def save_all(self):
        payload = {
            "clipboard": self.clipboard_items,
            "templates": self.templates,
            "settings": self.settings,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- clipboard ---

    def handle_new_clipboard(self, mime: QMimeData):
        """從 QMimeData 解析並儲存到剪貼簿歷史。"""
        # 只收 text / image / urls
        item = None
        if mime.hasImage():
            img = mime.imageData()
            if isinstance(img, QImage):
                item = self._save_image_clip(img)
        elif mime.hasUrls():
            # 以檔案或連結文字形式存
            urls = [u.toString() for u in mime.urls()]
            text = "\n".join(urls)
            item = self._make_clip("url", text, full_text=text)
        elif mime.hasText():
            text = mime.text()
            item = self._make_clip("text", text, full_text=text)

        if not item:
            return

        # 插入最前面
        self.clipboard_items.insert(0, item)
        # 去重：同 preview 的舊項目刪掉
        seen = set()
        dedup = []
        for it in self.clipboard_items:
            key = (it.get("type"), it.get("preview"))
            if key in seen:
                continue
            seen.add(key)
            dedup.append(it)
        self.clipboard_items = dedup

        # 限制長度，但保留 pinned
        max_history = self.settings.get("max_history", 100)
        normal = [x for x in self.clipboard_items if not x.get("pinned")]
        pinned = [x for x in self.clipboard_items if x.get("pinned")]
        normal = normal[:max_history]
        self.clipboard_items = pinned + normal

        self.save_all()

    def _make_clip(self, ctype: str, preview: str, full_text: str | None = None, extra: dict | None = None):
        data = {
            "id": str(uuid.uuid4()),
            "type": ctype,
            "preview": preview.strip() if isinstance(preview, str) else preview,
            "full_text": full_text if full_text is not None else preview,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pinned": False,
        }
        if extra:
            data.update(extra)
        return data

    def _save_image_clip(self, img: QImage):
        img_id = str(uuid.uuid4())
        path = self.image_dir / f"{img_id}.png"
        img.save(str(path), "PNG")
        preview = f"[Image] {path.name}"
        return self._make_clip("image", preview, full_text=str(path), extra={"image_path": str(path)})

    def iter_clipboard_items(self):
        # pinned 先、新到舊
        return sorted(self.clipboard_items,
                      key=lambda x: (not x.get("pinned", False), x.get("timestamp", "")),
                      reverse=True)

    def get_clipboard_item(self, cid: str):
        for it in self.clipboard_items:
            if it["id"] == cid:
                return it
        return None

    def delete_clipboard_item(self, cid: str):
        self.clipboard_items = [x for x in self.clipboard_items if x["id"] != cid]
        self.save_all()

    def toggle_pin(self, cid: str):
        for it in self.clipboard_items:
            if it["id"] == cid:
                it["pinned"] = not it.get("pinned", False)
                break
        self.save_all()

    def copy_clip_to_clipboard(self, clip: dict):
        from PyQt6.QtWidgets import QApplication
        cb = QApplication.clipboard()
        ctype = clip.get("type")
        if ctype == "text" or ctype == "url":
            cb.setText(clip.get("full_text", ""))
        elif ctype == "image":
            path = Path(clip.get("image_path", ""))
            if path.exists():
                img = QImage(str(path))
                cb.setImage(img)
        else:
            cb.setText(clip.get("full_text", ""))

    # --- templates ---

    def _next_template_id(self) -> int:
        if not self.templates:
            return 1
        return max(t["id"] for t in self.templates) + 1

    def add_template(self, name: str, content: str):
        tpl = {
            "id": self._next_template_id(),
            "name": name,
            "content": content,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.templates.append(tpl)

    def get_template(self, tid: int):
        for t in self.templates:
            if t["id"] == tid:
                return t
        return None

    def update_template(self, tid: int, name: str, content: str):
        for t in self.templates:
            if t["id"] == tid:
                t["name"] = name
                t["content"] = content
                t["updated_at"] = datetime.now().isoformat(timespec="seconds")
                break

    def delete_template(self, tid: int):
        self.templates = [t for t in self.templates if t["id"] != tid]

    # --- misc ---
