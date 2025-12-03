from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import os

try:  # 避免沒裝套件時整個程式壞掉
    import argostranslate.translate as argos_translate  # type: ignore[import]
    import argostranslate.package as argos_package  # type: ignore[import]
except Exception:  # pragma: no cover
    argos_translate = None  # type: ignore[assignment]
    argos_package = None  # type: ignore[assignment]


DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "argos"))


@dataclass
class LanguageInfo:
    code: str
    name: str


class Translator:
    """使用 Argos Translate 的離線翻譯器。"""

    def __init__(self, model_dir: str | None = None) -> None:
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self._code_map: Dict[str, str] = {
            "auto": "auto",
            "zh_TW": "zh",
            "zh_CN": "zh",
            "en": "en",
            "ja": "ja",
        }
        self._languages: Dict[str, LanguageInfo] = {
            "auto": LanguageInfo("auto", "自動偵測"),
            "zh_TW": LanguageInfo("zh_TW", "繁體中文"),
            "zh_CN": LanguageInfo("zh_CN", "簡體中文"),
            "en": LanguageInfo("en", "English"),
            "ja": LanguageInfo("ja", "日本語"),
        }

    def list_languages(self) -> List[LanguageInfo]:
        items = list(self._languages.values())
        items.sort(key=lambda x: (0 if x.code == "auto" else 1, x.name))
        return items

    def translate(self, text: str, src: str, tgt: str) -> str:
        text = text or ""
        if not text.strip():
            return ""
        if argos_translate is None:
            return text

        src = src or "auto"
        tgt = tgt or "zh_TW"
        src_code = self._code_map.get(src, "auto")
        tgt_code = self._code_map.get(tgt, "zh")

        if src_code != "auto" and src_code == tgt_code:
            return text

        try:
            langs = argos_translate.get_installed_languages()
        except Exception:
            return text

        from_lang = None
        to_lang = None
        for lang in langs:
            if src_code != "auto" and getattr(lang, "code", None) == src_code:
                from_lang = lang
            if getattr(lang, "code", None) == tgt_code:
                to_lang = lang

        if from_lang is None and src_code == "auto" and to_lang is not None:
            # 這裡簡單處理 auto：實務上應搭配多模型與語言偵測
            pass

        if from_lang is None or to_lang is None:
            return text

        try:
            translation = from_lang.get_translation(to_lang)
            result = translation.translate(text)
        except Exception:
            return text
        return result or text

    def load_models_from_dir(self, directory: str | None = None) -> None:
        if argos_package is None:
            return
        directory = directory or self.model_dir
        if not directory or not os.path.isdir(directory):
            return
        for filename in os.listdir(directory):
            if not filename.endswith(".argos"):
                continue
            path = os.path.join(directory, filename)
            try:
                pkg = argos_package.Package(path)
                pkg.install()
            except Exception:
                continue
