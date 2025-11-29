
from __future__ import annotations

import json
from pathlib import Path


class LanguageManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.lang_dir = base_dir / "languages"
        self.current_language = "zh_TW"
        self.translations: dict[str, str] = {}
        self.load_language(self.current_language)

    def load_language(self, code: str):
        path = self.lang_dir / f"{code}.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.translations = data
        self.current_language = code

    def set_language(self, code: str):
        self.load_language(code)

    def translate(self, key: str) -> str:
        return self.translations.get(key, key)


_lang_mgr_ref: LanguageManager | None = None


def init_language_manager(mgr: LanguageManager):
    global _lang_mgr_ref
    _lang_mgr_ref = mgr


def _(key: str) -> str:
    if _lang_mgr_ref is None:
        return key
    return _lang_mgr_ref.translate(key)
