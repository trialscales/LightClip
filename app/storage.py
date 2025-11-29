
import json
import os
from typing import List
from app.models import ClipEntry


DEFAULT_DATA = {
    "settings": {
        "max_entries": 100,
        "theme": "dark",
        "hotkeys": {
            "open": "Ctrl+Shift+C"
        }
    },
    "entries": []
}


class Storage:
    """負責 JSON 讀寫與資料管理。"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = DEFAULT_DATA.copy()
        self.entries: List[ClipEntry] = []
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        if not os.path.exists(self.data_path):
            self._save()
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            # 若讀檔失敗，以預設值重新建立
            self.data = DEFAULT_DATA.copy()
            self._save()

        self.entries = [ClipEntry.from_dict(e) for e in self.data.get("entries", [])]

    def _save(self):
        self.data["entries"] = [e.to_dict() for e in self.entries]
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ---- 對外操作 ----

    @property
    def max_entries(self) -> int:
        return int(self.data.get("settings", {}).get("max_entries", 100))

    def get_entries(self) -> List[ClipEntry]:
        return list(self.entries)

    def next_id(self) -> int:
        return (max((e.id for e in self.entries), default=0) + 1)

    def add_entry(self, entry: ClipEntry):
        # 若非釘選，且超過數量，移除最舊非釘選
        if not entry.pinned:
            non_pinned = [e for e in self.entries if not e.pinned]
            if len(non_pinned) >= self.max_entries:
                # 找最舊非釘選
                oldest = non_pinned[0]
                self.entries.remove(oldest)
        self.entries.insert(0, entry)
        self._save()

    def update_entry(self, entry: ClipEntry):
        for i, e in enumerate(self.entries):
            if e.id == entry.id:
                self.entries[i] = entry
                break
        self._save()

    def delete_entry(self, entry_id: int):
        self.entries = [e for e in self.entries if e.id != entry_id]
        self._save()

    def clear_history(self, keep_pinned: bool = True):
        if keep_pinned:
            self.entries = [e for e in self.entries if e.pinned]
        else:
            self.entries = []
        self._save()
