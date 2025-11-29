
import json
import os
from typing import Dict


class Language:
    _texts: Dict[str, str] = {}
    _code: str = "zh_TW"

    @classmethod
    def load(cls, code: str, base_path: str):
        cls._code = code
        path = os.path.join(base_path, f"{code}.json")
        if not os.path.exists(path):
            path = os.path.join(base_path, "zh_TW.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                cls._texts = json.load(f)
        except Exception:
            cls._texts = {}

    @classmethod
    def T(cls, key: str, default: str = "") -> str:
        return cls._texts.get(key, default or key)

    @classmethod
    def code(cls) -> str:
        return cls._code
