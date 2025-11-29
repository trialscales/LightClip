
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class StorageManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.history_path = self.data_dir / "history.json"
        self.templates_path = self.data_dir / "templates.json"
        self.settings_path = self.data_dir / "settings.json"

        self.clipboard_items: List[Dict[str, Any]] = []
        self.templates: List[Dict[str, Any]] = []
        self.settings: Dict[str, Any] = {}
        self._load_all()

    # ---------- load / save ----------
    def _load_all(self) -> None:
        self.clipboard_items = self._load_json(self.history_path, default=[])
        self.templates = self._load_json(self.templates_path, default=[])
        self.settings = self._load_json(self.settings_path, default={})

        # default settings
        self.settings.setdefault("language", "zh_TW")
        self.settings.setdefault("theme", "dark_default")
        self.settings.setdefault("max_history", 100)
        self.settings.setdefault("global_hotkey_enabled", False)
        self.settings.setdefault("global_hotkey", "ctrl+shift+v")
        self.settings.setdefault(
            "categories",
            ["文字", "圖片", "檔案", "未分類"],
        )

    def save_all(self) -> None:
        self._save_json(self.history_path, self.clipboard_items)
        self._save_json(self.templates_path, self.templates)
        self._save_json(self.settings_path, self.settings)

    def _load_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _save_json(self, path: Path, data) -> None:
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ---------- clipboard ----------
    def add_clipboard_item(self, item: Dict[str, Any]) -> None:
        # 不覆蓋 pinned，將新項目加在最前方
        self.clipboard_items.insert(0, item)
        self._truncate_history()

    def _truncate_history(self) -> None:
        max_hist = int(self.settings.get("max_history", 100))
        # 不計入 pinned，只針對未釘選的尾端項目裁切
        new_list: List[Dict[str, Any]] = []
        normal_count = 0
        for it in self.clipboard_items:
            if it.get("pinned"):
                new_list.append(it)
            else:
                if normal_count < max_hist:
                    new_list.append(it)
                    normal_count += 1
        self.clipboard_items = new_list

    def clear_history(self, keep_pinned: bool = True) -> None:
        if keep_pinned:
            self.clipboard_items = [c for c in self.clipboard_items if c.get("pinned")]
        else:
            self.clipboard_items = []

    def get_clipboard_item(self, cid: str) -> Optional[Dict[str, Any]]:
        for it in self.clipboard_items:
            if it.get("id") == cid:
                return it
        return None

    def delete_clipboard_item(self, cid: str) -> None:
        self.clipboard_items = [c for c in self.clipboard_items if c.get("id") != cid]

    # ---------- templates ----------
    def upsert_template(self, tpl: Dict[str, Any]) -> None:
        tid = tpl.get("id")
        for i, t in enumerate(self.templates):
            if t.get("id") == tid:
                self.templates[i] = tpl
                break
        else:
            self.templates.append(tpl)

    def delete_template(self, tid: str) -> None:
        self.templates = [t for t in self.templates if t.get("id") != tid]
