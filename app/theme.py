
from __future__ import annotations

from typing import Dict


class ThemeManager:
    def __init__(self):
        self.themes: Dict[str, Dict[str, str]] = {
            "dark_default": {
                "name": "Dark · Obsidian",
                "bg": "#121212",
                "bg_alt": "#1E1E1E",
                "panel": "#1F1F23",
                "text": "#F5F5F5",
                "text_sub": "#A1A1AA",
                "accent": "#4D9FFF",
            },
            "light_default": {
                "name": "Light · Soft",
                "bg": "#F5F5F7",
                "bg_alt": "#E8E8EA",
                "panel": "#FFFFFF",
                "text": "#2E2E2E",
                "text_sub": "#6A6A6A",
                "accent": "#4D89FF",
            },
        }
        self.current_key = "dark_default"

    def set_theme(self, key: str) -> None:
        if key not in self.themes:
            key = "dark_default"
        self.current_key = key

    def build_stylesheet(self) -> str:
        t = self.themes[self.current_key]
        bg = t["bg"]
        bg_alt = t["bg_alt"]
        panel = t["panel"]
        text = t["text"]
        text_sub = t["text_sub"]
        accent = t["accent"]

        css = f"""
        QWidget {{
            background-color: {bg};
            color: {text};
            font-size: 18px;
        }}
        QMainWindow {{
            background-color: {bg};
        }}
        QTabWidget::pane {{
            border: 1px solid {bg_alt};
            border-radius: 10px;
            margin-top: 4px;
        }}
        QTabBar::tab {{
            background: {bg_alt};
            padding: 8px 18px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background: {panel};
        }}
        QListWidget {{
            background: transparent;
            border: none;
        }}
        QTextEdit, QLineEdit {{
            background: {panel};
            border: 1px solid {bg_alt};
            border-radius: 8px;
            padding: 6px 10px;
        }}
        QPushButton {{
            background-color: {accent};
            border: none;
            padding: 8px 14px;
            color: #ffffff;
            border-radius: 8px;
        }}
        QPushButton:hover {{
            background-color: {text_sub};
        }}
        QPushButton:flat {{
            background-color: transparent;
            border: none;
            color: {text};
        }}
        QMenu {{
            background-color: {bg_alt};
            color: {text};
            border: 1px solid {panel};
            border-radius: 8px;
        }}
        QMenu::item {{
            padding: 6px 16px;
        }}
        QMenu::item:selected {{
            background: {panel};
        }}
        QLabel#metaLabel {{
            color: {text_sub};
            font-size: 14px;
        }}
        QFrame#CardFrame {{
            background-color: {panel};
            border-radius: 10px;
            border: 1px solid {bg_alt};
        }}
        """
        return css
