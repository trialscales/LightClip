from __future__ import annotations

import os
from typing import Optional

try:
    from openai import OpenAI  # type: ignore[import]
except Exception:
    OpenAI = None  # type: ignore[assignment]


class Translator:
    """Simple GPT-based translator with safe fallback."""

    def __init__(self, ui_language: str = "zh_TW") -> None:
        self.ui_language = ui_language
        self._client: Optional[object] = None

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
        if OpenAI is not None and api_key:
            try:
                self._client = OpenAI(api_key=api_key)
            except Exception:
                self._client = None

    def translate(self, text: str, target_lang: str = "zh-TW") -> str:
        text = (text or "").strip()
        if not text:
            return ""

        if self._client is None:
            return text

        prompt = (
            f"Translate the following text into {target_lang}. "
            "Keep formatting reasonably similar, but reply with translated text only.\n\n"
            f"Text:\n{text}"
        )

        try:
            resp = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translation engine."},
                    {"role": "user", "content": prompt},
                ],
            )
            choice = resp.choices[0]
            result = choice.message.content if choice and choice.message else ""
            return result or text
        except Exception:
            return text
