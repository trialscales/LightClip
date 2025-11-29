
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class ClipEntry:
    """剪貼簿單筆資料模型。"""
    id: int
    type: str               # text / image / url / file
    content: str            # 文字內容 / 路徑 / URL
    timestamp: str          # 字串時間
    pinned: bool = False
    tags: List[str] = None

    extra: Dict[str, Any] = None  # 額外資料，例如縮圖路徑等

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # 確保 None 不會造成 JSON 問題
        if d["tags"] is None:
            d["tags"] = []
        if d["extra"] is None:
            d["extra"] = {}
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ClipEntry":
        return ClipEntry(
            id=data.get("id", 0),
            type=data.get("type", "text"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            pinned=data.get("pinned", False),
            tags=data.get("tags") or [],
            extra=data.get("extra") or {},
        )
