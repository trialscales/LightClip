from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image  # type: ignore[import]
    import pytesseract  # type: ignore[import]
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    pytesseract = None  # type: ignore[assignment]


def ocr_image(path: Path, lang_hint: str = "chi_tra+eng") -> str:
    """簡單的 OCR 包裝函式。"""
    if Image is None or pytesseract is None:
        return ""
    try:
        img = Image.open(path)
    except Exception:
        return ""
    try:
        text = pytesseract.image_to_string(img, lang=lang_hint)
    except Exception:
        return ""
    return text or ""
