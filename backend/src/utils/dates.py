"""时间与数值格式化工具。"""
from __future__ import annotations

from datetime import datetime, timezone


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone().isoformat()
    return dt.astimezone().isoformat()


def now() -> datetime:
    return datetime.now()
