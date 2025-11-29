
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .storage import StorageManager


class CloudSync:
    """將目前的資料匯出成 JSON 檔案，方便備份或同步到雲端。"""

    def __init__(self, base_dir: Path, storage: StorageManager):
        self.base_dir = base_dir
        self.storage = storage
        self.cloud_dir = self.base_dir / "cloud"
        self.cloud_dir.mkdir(exist_ok=True)

    def export_json(self) -> List[Path]:
        files: List[Path] = []

        history_path = self.cloud_dir / "history_export.json"
        templates_path = self.cloud_dir / "templates_export.json"
        settings_path = self.cloud_dir / "settings_export.json"

        history_path.write_text(
            json.dumps(self.storage.clipboard_items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        templates_path.write_text(
            json.dumps(self.storage.templates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        settings_path.write_text(
            json.dumps(self.storage.settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        files.extend([history_path, templates_path, settings_path])
        return files
