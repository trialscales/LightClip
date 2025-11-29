
import json
import os
from typing import List, Optional
from app.models import ClipEntry, TemplateEntry

DEFAULT_DATA = {
    "settings": {
        "max_entries": 100,
        "theme": "dark_default",
        "language": "zh_TW",
        "icon_theme": "light",
        "hotkeys": {
            "open": "Ctrl+Shift+C"
        }
    },
    "entries": [],
    "templates": []
}


class Storage:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))
        self.entries: List[ClipEntry] = []
        self.templates: List[TemplateEntry] = []
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        if not os.path.exists(self.data_path):
            self._save()
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))
            self._save()

        self.entries = [ClipEntry.from_dict(e) for e in self.data.get("entries", [])]
        self.templates = [TemplateEntry.from_dict(t) for t in self.data.get("templates", [])]

    def _save(self):
        self.data["entries"] = [e.to_dict() for e in self.entries]
        self.data["templates"] = [t.to_dict() for t in self.templates]
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    @property
    def max_entries(self) -> int:
        return int(self.data.get("settings", {}).get("max_entries", 100))

    @max_entries.setter
    def max_entries(self, value: int):
        self.data.setdefault("settings", {})["max_entries"] = int(value)
        self._save()

    @property
    def language(self) -> str:
        return self.data.get("settings", {}).get("language", "zh_TW")

    @language.setter
    def language(self, code: str):
        self.data.setdefault("settings", {})["language"] = code
        self._save()

    @property
    def icon_theme(self) -> str:
        return self.data.get("settings", {}).get("icon_theme", "light")

    @icon_theme.setter
    def icon_theme(self, theme: str):
        self.data.setdefault("settings", {})["icon_theme"] = theme
        self._save()

    @property
    def theme(self) -> str:
        return self.data.get("settings", {}).get("theme", "dark_default")

    @theme.setter
    def theme(self, theme_key: str):
        self.data.setdefault("settings", {})["theme"] = theme_key
        self._save()

    def get_entries(self) -> List[ClipEntry]:
        return list(self.entries)

    def next_entry_id(self) -> int:
        return (max((e.id for e in self.entries), default=0) + 1)

    def add_entry(self, entry: ClipEntry):
        if not entry.pinned:
            non_pinned = [e for e in self.entries if not e.pinned]
            if len(non_pinned) >= self.max_entries and non_pinned:
                oldest = non_pinned[-1]
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

    def get_templates(self) -> List[TemplateEntry]:
        return list(self.templates)

    def next_template_id(self) -> int:
        return (max((t.id for t in self.templates), default=0) + 1)

    def add_template(self, tpl: TemplateEntry):
        self.templates.append(tpl)
        self._save()

    def update_template(self, tpl: TemplateEntry):
        for i, t in enumerate(self.templates):
            if t.id == tpl.id:
                self.templates[i] = tpl
                break
        self._save()

    def delete_template(self, tpl_id: int):
        self.templates = [t for t in self.templates if t.id != tpl_id]
        self._save()

    def find_template_by_hotkey(self, index: int) -> Optional[TemplateEntry]:
        for t in self.templates:
            if t.hotkey_index == index:
                return t
        return None
