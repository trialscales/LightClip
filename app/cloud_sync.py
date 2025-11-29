
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


class CloudSync:
    def __init__(self, storage):
        self.storage = storage
        self.cloud_dir = storage.base_dir / "cloud"
        self.cloud_dir.mkdir(exist_ok=True)

    def export_all(self):
        """將剪貼簿、模板與設定輸出成 JSON 檔，方便雲端同步資料夾上傳。"""
        payload_clip = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "clipboard": self.storage.clipboard_items,
        }
        payload_tpl = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "templates": self.storage.templates,
        }
        payload_settings = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "settings": self.storage.settings,
        }
        (self.cloud_dir / "history_export.json").write_text(
            json.dumps(payload_clip, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.cloud_dir / "templates_export.json").write_text(
            json.dumps(payload_tpl, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.cloud_dir / "settings_export.json").write_text(
            json.dumps(payload_settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
