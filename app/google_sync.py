
from __future__ import annotations

from pathlib import Path
from typing import Iterable

# 此模組提供一個簡單的 Google Drive 上傳介面。
# 實際使用時需要在執行環境中放置 credentials.json 並安裝相關套件。
#
# pip install google-auth google-auth-oauthlib google-api-python-client


class GoogleDriveSync:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def upload_files(self, files: Iterable[Path]) -> None:
        # 為了讓專案可以在沒有 Google 套件的環境下運作，
        # 這裡只提供範例結構；實務上可依需求補上真實上傳流程。
        # 如果需要完整串接，可在此加入 Drive API 呼叫。
        # 目前僅當作占位程式碼，以免匯入失敗。
        pass
