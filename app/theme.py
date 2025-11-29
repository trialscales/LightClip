
from __future__ import annotations

from pathlib import Path


class ThemeManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        # 定義多組主題（與你之前給的色票相符的簡化版）
        self.themes = {
            "dark_default": {
                "name": "Dark · 深灰黑",
                "bg": "#1E1E1E",
                "bg_alt": "#252525",
                "panel": "#2C2C2C",
                "text": "#E4E4E4",
                "text_sub": "#A0A0A0",
                "accent": "#4DA8DA",
            },
            "dark_reading": {
                "name": "Dark · 閱讀模式",
                "bg": "#1C1B1F",
                "bg_alt": "#2A292D",
                "panel": "#2A292D",
                "text": "#E8E6E3",
                "text_sub": "#B8B4AE",
                "accent": "#D6A75B",
            },
            "dark_tech": {
                "name": "Dark · 科技藍綠",
                "bg": "#0F1419",
                "bg_alt": "#1C2530",
                "panel": "#162026",
                "text": "#E5E9F0",
                "text_sub": "#88C0D0",
                "accent": "#81A1C1",
            },
            "light_default": {
                "name": "Light · 霧白藍",
                "bg": "#F5F5F7",
                "bg_alt": "#E8E8EA",
                "panel": "#FFFFFF",
                "text": "#2E2E2E",
                "text_sub": "#6A6A6A",
                "accent": "#4D89FF",
            },
            "light_warm": {
                "name": "Light · 奶油暖",
                "bg": "#FAF9F7",
                "bg_alt": "#F1EEE7",
                "panel": "#FFFFFF",
                "text": "#2B2B2B",
                "text_sub": "#7A7A7A",
                "accent": "#E89F4F",
            },
            "light_cool": {
                "name": "Light · 冷色清爽",
                "bg": "#F4F7FA",
                "bg_alt": "#E9EEF2",
                "panel": "#FFFFFF",
                "text": "#27343F",
                "text_sub": "#76828B",
                "accent": "#4AB3F4",
            },
        }
        self.current_theme_key = "dark_default"

    def set_theme(self, key: str):
        if key in self.themes:
            self.current_theme_key = key

    def current(self):
        return self.themes[self.current_theme_key]

    def build_stylesheet(self) -> str:
        t = self.current()
        bg = t["bg"]
        bg_alt = t["bg_alt"]
        panel = t["panel"]
        text = t["text"]
        text_sub = t["text_sub"]
        accent = t["accent"]

        # QMenuBar 跟著主題切換顏色
        css = f"""
        QWidget {{
            background-color: {bg};
            color: {text};
            font-size: 18px;
        }}
        QTabWidget::pane {{
            border: 1px solid {bg_alt};
        }}
        QTabBar::tab {{
            background: {bg_alt};
            padding: 6px 14px;
        }}
        QTabBar::tab:selected {{
            background: {panel};
        }}
        QListWidget {{
            background: {panel};
            border: 1px solid {bg_alt};
        }}
        QTextEdit, QLineEdit {{
            background: {panel};
            border: 1px solid {bg_alt};
        }}
        QPushButton {{
            background-color: {accent};
            border: none;
            padding: 6px 12px;
            color: #ffffff;
        }}
        QPushButton:hover {{
            background-color: {accent};
            opacity: 0.9;
        }}
        QMenuBar {{
            background-color: {bg_alt};
            color: {text};
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 4px 10px;
        }}
        QMenuBar::item:selected {{
            background: {panel};
        }}
        QStatusBar {{
            background: {bg_alt};
            color: {text_sub};
        }}
        """
        return css
