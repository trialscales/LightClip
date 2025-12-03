
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any


class ThemeManager:
    """Simple theme manager backed by a JSON config + QSS files.

    Expected project structure (relative to this file):

        <project_root>/
          main.py
          app/
            theme.py   <- this file
          themes/
            themes.json
            dark_default.qss
            light_default.qss
            ...

    themes.json format:

        {
          "dark_default": {
            "name": "深色主題",
            "qss": "themes/dark_default.qss"
          },
          "light_default": {
            "name": "淺色主題",
            "qss": "themes/light_default.qss"
          }
        }

    This class is designed to stay compatible with existing usage in main.py:
        - ThemeManager()
        - theme_mgr.themes  (dict with key -> {"name": str, ...})
        - theme_mgr.set_theme(key)
        - css = theme_mgr.build_stylesheet()
    """

    def __init__(self) -> None:
        # project root: .../app/theme.py -> project_root
        self.base_dir: Path = Path(__file__).resolve().parent.parent
        self.themes: Dict[str, Dict[str, Any]] = {}
        self.current_theme_key: str | None = None
        self._load_themes()

    # -------- internal helpers --------

    def _themes_json_path(self) -> Path:
        return self.base_dir / "themes" / "themes.json"

    def _load_themes(self) -> None:
        """Load themes from JSON file, with safe fallback."""
        path = self._themes_json_path()
        if not path.exists():
            # fallback: built-in single dark theme
            self.themes = {
                "dark_default": {
                    "name": "深色預設",
                    "qss": "themes/dark_default.qss",
                }
            }
            self.current_theme_key = "dark_default"
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.themes = data
            else:
                raise ValueError("themes.json must be an object")
        except Exception:
            # when JSON is invalid, keep a safe default
            self.themes = {
                "dark_default": {
                    "name": "深色預設",
                    "qss": "themes/dark_default.qss",
                }
            }

        # pick first theme as default if not set
        if self.themes:
            self.current_theme_key = next(iter(self.themes.keys()))
        else:
            self.current_theme_key = None

    # -------- public API --------

    def set_theme(self, key: str) -> None:
        """Set current theme key (must exist in self.themes)."""
        if key in self.themes:
            self.current_theme_key = key
        # if not found, keep previous theme; don't raise to avoid crashing

    def build_stylesheet(self) -> str:
        """Return the concatenated QSS for the current theme.

        If the theme defines a 'qss' field pointing to a file, that QSS is loaded.
        If loading fails, a minimal safe fallback stylesheet is returned.
        """
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

    # -------- fallback --------

    def _fallback_qss(self) -> str:
        """Minimal dark-ish fallback styling so the app remains usable."""
        return (
            "QWidget {"
            "  background-color: #202020;"
            "  color: #E0E0E0;"
            "}"
            "QPushButton {"
            "  background-color: #2A2A2A;"
            "  border: 1px solid #444444;"
            "  padding: 4px 8px;"
            "  border-radius: 4px;"
            "}"
            "QLineEdit, QTextEdit {"
            "  background-color: #252525;"
            "  border: 1px solid #444444;"
            "  border-radius: 4px;"
            "  padding: 4px;"
            "}"
            "#CardFrame {"
            "  background-color: #252525;"
            "  border-radius: 10px;"
            "}"
            "#metaLabel {"
            "  color: #A0A0A0;"
            "}"
        )


# For type checkers / external imports
__all__ = ["ThemeManager"]
