from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json


class ThemeManager:
    """Theme manager based on themes.json + QSS files."""

    def __init__(self) -> None:
        self.base_dir: Path = Path(__file__).resolve().parent.parent
        self.themes: Dict[str, Dict[str, Any]] = {}
        self.current_theme_key: str | None = None
        self._load_themes()

    def _themes_json_path(self) -> Path:
        return self.base_dir / "themes" / "themes.json"

    def _load_themes(self) -> None:
        path = self._themes_json_path()
        if not path.exists():
            self.themes = {
                "dark_default": {"name": "深色主題", "qss": "themes/dark_default.qss"}
            }
            self.current_theme_key = "dark_default"
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.themes = data
        except Exception:
            self.themes = {
                "dark_default": {"name": "深色主題", "qss": "themes/dark_default.qss"}
            }
        if self.themes and not self.current_theme_key:
            self.current_theme_key = next(iter(self.themes.keys()))

    def set_theme(self, key: str) -> None:
        if key in self.themes:
            self.current_theme_key = key

    def build_stylesheet(self) -> str:
        if not self.current_theme_key or self.current_theme_key not in self.themes:
            return self._fallback_qss()
        theme = self.themes[self.current_theme_key]
        qss_rel = theme.get("qss")
        if not qss_rel:
            return self._fallback_qss()
        qss_path = self.base_dir / qss_rel
        if not qss_path.exists():
            return self._fallback_qss()
        try:
            return qss_path.read_text(encoding="utf-8")
        except Exception:
            return self._fallback_qss()

    def _fallback_qss(self) -> str:
        return (
            "QWidget {background-color: #202020; color: #E0E0E0;}"
            "QPushButton {background-color: #2A2A2A; border: 1px solid #444444; padding: 4px 8px; border-radius: 4px;}"
            "QLineEdit, QTextEdit {background-color: #252525; border: 1px solid #444444; border-radius: 4px; padding: 4px;}"
            "#CardFrame {background-color: #252525; border-radius: 10px;}"
            "#metaLabel {color: #A0A0A0;}"
        )


__all__ = ["ThemeManager"]
