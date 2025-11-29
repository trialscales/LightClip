
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .storage import StorageManager


class CloudSync:
    def __init__(self, base_dir: Path, storage: StorageManager):
        self.base_dir = base_dir
        self.storage = storage
        self.cloud_dir = base_dir / "cloud"
        self.cloud_dir.mkdir(exist_ok=True)

    def export_json(self) -> list[Path]:
        files: list[Path] = []

        hist_file = self.cloud_dir / "history_export.json"
        tpl_file = self.cloud_dir / "templates_export.json"
        settings_file = self.cloud_dir / "settings_export.json"

        hist_file.write_text(
            json.dumps(self.storage.clipboard_items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tpl_file.write_text(
            json.dumps(self.storage.templates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        settings_file.write_text(
            json.dumps(self.storage.settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        files.extend([hist_file, tpl_file, settings_file])
        return files
