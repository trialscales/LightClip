
from typing import Dict

THEMES: Dict[str, Dict[str, str]] = {
    "dark_default": {
        "name": "深色模式",
        "background": "#1E1E1E",
        "background_alt": "#252525",
        "panel": "#2C2C2C",
        "text": "#E4E4E4",
        "text_secondary": "#A0A0A0",
        "accent": "#4DA8DA"
    },
    "dark_reading": {
        "name": "深色閱讀模式",
        "background": "#1C1B1F",
        "background_alt": "#2A292D",
        "panel": "#2A292D",
        "text": "#E8E6E3",
        "text_secondary": "#B8B4AE",
        "accent": "#D6A75B"
    },
    "dark_cyber": {
        "name": "深色科技藍綠",
        "background": "#0F1419",
        "background_alt": "#1C2530",
        "panel": "#162026",
        "text": "#E5E9F0",
        "text_secondary": "#81A1C1",
        "accent": "#88C0D0"
    },
    "light_default": {
        "name": "淺色模式",
        "background": "#F5F5F7",
        "background_alt": "#E8E8EA",
        "panel": "#FFFFFF",
        "text": "#2E2E2E",
        "text_secondary": "#6A6A6A",
        "accent": "#4D89FF"
    },
    "light_cream": {
        "name": "淺色奶油模式",
        "background": "#FAF9F7",
        "background_alt": "#F1EEE7",
        "panel": "#FFFFFF",
        "text": "#2B2B2B",
        "text_secondary": "#7A7A7A",
        "accent": "#E89F4F"
    },
    "light_cool": {
        "name": "冷色系清爽模式",
        "background": "#F4F7FA",
        "background_alt": "#E9EEF2",
        "panel": "#FFFFFF",
        "text": "#27343F",
        "text_secondary": "#76828B",
        "accent": "#4AB3F4"
    },
}


def build_stylesheet(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES["dark_default"])
    bg = t["background"]
    bg_alt = t["background_alt"]
    panel = t["panel"]
    text = t["text"]
    text2 = t["text_secondary"]
    accent = t["accent"]

    return f'''
    * {{
        font-size: 18px;
        font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
        color: {text};
    }}
    QMainWindow {{
        background-color: {bg};
    }}
    QWidget {{
        background-color: {bg};
        color: {text};
    }}
    QTabWidget::pane {{
        border: 1px solid {bg_alt};
        background: {bg_alt};
    }}
    QTabBar::tab {{
        background: {bg_alt};
        color: {text2};
        padding: 6px 16px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {panel};
        color: {text};
    }}
    QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox {{
        background-color: {panel};
        color: {text};
        border: 1px solid {bg_alt};
        selection-background-color: {accent};
    }}
    QPushButton {{
        background-color: {accent};
        color: #FFFFFF;
        border-radius: 4px;
        padding: 4px 10px;
        border: none;
    }}
    QPushButton:hover {{
        background-color: {bg_alt};
    }}
    QLabel {{
        color: {text};
    }}
    QMenuBar {{
        background-color: {bg_alt};
        color: {text};
    }}
    QMenuBar::item:selected {{
        background-color: {accent};
    }}
    QMenu {{
        background-color: {bg_alt};
        color: {text};
    }}
    QMenu::item:selected {{
        background-color: {accent};
    }}
    '''
