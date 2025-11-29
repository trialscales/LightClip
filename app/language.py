
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_current_lang_mgr = None


def _(key: str) -> str:
    global _current_lang_mgr
    if _current_lang_mgr is None:
        return key
    return _current_lang_mgr.get(key)


class LanguageManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.lang_dir = self.base_dir / "languages"
        self.lang_dir.mkdir(exist_ok=True)
        self.current_lang = "zh_TW"
        self.messages: Dict[str, str] = {}

    def set_language(self, lang_code: str) -> None:
        self.current_lang = lang_code
        path = self.lang_dir / f"{lang_code}.json"
        if not path.exists():
            self.messages = {}
            return
        try:
            self.messages = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self.messages = {}

    def get(self, key: str) -> str:
        return self.messages.get(key, key)


def init_language_manager(lang_mgr: LanguageManager) -> None:
    global _current_lang_mgr
    _current_lang_mgr = lang_mgr
