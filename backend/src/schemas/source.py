"""采集源 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class SourceOut(BaseModel):
    id: int
    name: str
    site_type: str
    site_type_label: str = ""
    enabled: bool
    last_sync_at: str | None = None
    raw_count: int
    sync_status: str
    note: str = ""


class SyncAccepted(BaseModel):
    task_id: str
    source_id: int
    message: str
