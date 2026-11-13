"""通用响应 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class MessageOut(BaseModel):
    ok: bool = True
    message: str = ""
    trace_id: str = ""


class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    db: bool
    redis: bool
    worker_heartbeat: bool
    active_rule_version: str = "v1"
