
from __future__ import annotations

from pathlib import Path
from typing import Iterable

# Google API 套件：需要安裝
# google-auth, google-auth-oauthlib, google-api-python-client
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
except Exception:  # pragma: no cover - 在沒安裝套件時略過
    Credentials = None
    build = None
    MediaFileUpload = None
    InstalledAppFlow = None

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveSync:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.token_file = base_dir / "google_token.json"
        self.client_secret_file = base_dir / "google_client_secret.json"

    def _get_creds(self):
        if Credentials is None:
            raise RuntimeError("Google API 套件未安裝，請先安裝相關套件。")

        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.client_secret_file.exists():
                    raise RuntimeError("缺少 google_client_secret.json，請先到 Google Cloud 建立 OAuth 用戶端。")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secret_file), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def upload_files(self, files: Iterable[Path]):
        if build is None or MediaFileUpload is None:
            raise RuntimeError("Google API 套件未安裝，無法上傳到雲端。")

        creds = self._get_creds()
        service = build("drive", "v3", credentials=creds)

        for path in files:
            media = MediaFileUpload(str(path), resumable=True)
            file_metadata = {
                "name": path.name,
            }
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()
