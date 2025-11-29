
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StorageManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.data_dir = base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "data.json"

        self.clipboard_items: list[dict[str, Any]] = []
        self.templates: list[dict[str, Any]] = []
        self.settings: dict[str, Any] = {
            "max_history": 100,
            "language": "zh_TW",
            "theme": "dark_default",
            "global_hotkey_enabled": False,
            "global_hotkey": "ctrl+shift+v",
        }

        self.load_all()

    def load_all(self):
        if not self.data_file.exists():
            self.save_all()
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
        except Exception:
            return
        self.clipboard_items = data.get("clipboard", [])
        self.templates = data.get("templates", [])
        self.settings.update(data.get("settings", {}))

    def save_all(self):
        payload = {
            "clipboard": self.clipboard_items,
            "templates": self.templates,
            "settings": self.settings,
        }
        self.data_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---- clipboard ----
    def add_clipboard_item(self, item: dict[str, Any]):
        # pinned item will stay; we only trim non-pinned
        self.clipboard_items.insert(0, item)
        self._trim_history()

    def _trim_history(self):
        max_hist = int(self.settings.get("max_history", 100))
        pinned = [c for c in self.clipboard_items if c.get("pinned")]
        others = [c for c in self.clipboard_items if not c.get("pinned")]
        if len(pinned) + len(others) <= max_hist:
            self.clipboard_items = pinned + others
            return
        others = others[: max(0, max_hist - len(pinned))]
        self.clipboard_items = pinned + others

    def get_clipboard_item(self, cid: str | None):
        if not cid:
            return None
        for c in self.clipboard_items:
            if c.get("id") == cid:
                return c
        return None

    def delete_clipboard_item(self, cid: str):
        self.clipboard_items = [c for c in self.clipboard_items if c.get("id") != cid]

    # ---- templates ----
    def upsert_template(self, tpl: dict[str, Any]):
        tid = tpl.get("id")
        for i, t in enumerate(self.templates):
            if t.get("id") == tid:
                self.templates[i] = tpl
                return
        self.templates.append(tpl)

    def delete_template(self, tid: str):
        self.templates = [t for t in self.templates if t.get("id") != tid]

