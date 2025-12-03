from __future__ import annotations

import os
from typing import Optional

try:
    # New style OpenAI client (>=1.0.0)
    from openai import OpenAI  # type: ignore[import]
except Exception:
    OpenAI = None  # type: ignore[assignment]


class Translator:
    """Simple translation helper, optionally using OpenAI (GPT).

    If OPENAI_API_KEY is set and openai client is installed, we will call GPT
    to translate text. Otherwise, we just return the original text so the app
    does not crash.

    You can customize this file with your own provider (DeepL, Google, etc.).
    """

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

        # If no client, just return original text, so UI still works.
        if self._client is None:
            return text

        prompt = (
            f"Translate the following text into {target_lang}. "
            "Keep formatting reasonably similar, but do not include any extra commentary.\n\n"
            f"Text:\n{text}"
        )

        try:
            # Using the new chat.completions API; adjust model name as you prefer.
            resp = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a translation engine. Reply with translated text only.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            choice = resp.choices[0]
            translated = choice.message.content if choice and choice.message else ""
            return translated or text
        except Exception:
            # If anything fails, just return original text (fail-safe).
            return text
