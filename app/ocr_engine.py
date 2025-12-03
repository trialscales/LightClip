from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from google.cloud import vision  # type: ignore[import]
except Exception:
    vision = None  # type: ignore[assignment]

try:
    import pytesseract  # type: ignore[import]
    from PIL import Image  # type: ignore[import]
except Exception:
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]


class OCREngine:
    """OCR engine wrapper.

    Priority:
      1. Google Cloud Vision (if installed & GOOGLE_APPLICATION_CREDENTIALS set)
      2. pytesseract + PIL
      3. Fallback: return empty string
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def _google_vision_client(self):
        if vision is None:
            return None
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return None
        try:
            return vision.ImageAnnotatorClient()
        except Exception:
            return None

    def extract_text(self, image_path: Path) -> str:
        if not image_path.exists():
            return ""
        # Google Vision first
        client = self._google_vision_client()
        if client is not None:
            try:
                with image_path.open("rb") as f:
                    content = f.read()
                image = vision.Image(content=content)  # type: ignore[attr-defined]
                response = client.text_detection(image=image)
                if not response.error.message and response.text_annotations:
                    return response.text_annotations[0].description or ""
            except Exception:
                pass
        # Tesseract fallback
        if pytesseract is not None and Image is not None:
            try:
                img = Image.open(str(image_path))
                return pytesseract.image_to_string(img) or ""
            except Exception:
                return ""
        return ""
