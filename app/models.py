
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ClipEntry:
    id: int
    type: str
    content: str
    timestamp_local: str
    timestamp_iso: str
    pinned: bool = False
    tags: List[str] = None
    extra: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["tags"] is None:
            d["tags"] = []
        if d["extra"] is None:
            d["extra"] = {}
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ClipEntry":
        ts_local = data.get("timestamp_local") or data.get("timestamp") or ""
        ts_iso = data.get("timestamp_iso") or ""
        return ClipEntry(
            id=data.get("id", 0),
            type=data.get("type", "text"),
            content=data.get("content", ""),
            timestamp_local=ts_local,
            timestamp_iso=ts_iso,
            pinned=data.get("pinned", False),
            tags=data.get("tags") or [],
            extra=data.get("extra") or {},
        )


@dataclass
class TemplateEntry:
    id: int
    name: str
    content: str
    hotkey_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TemplateEntry":
        return TemplateEntry(
            id=data.get("id", 0),
            name=data.get("name", ""),
            content=data.get("content", ""),
            hotkey_index=data.get("hotkey_index"),
        )
