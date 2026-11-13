"""采集源控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import audit_service, source_service


def list_sources(db: Session) -> list[dict]:
    return source_service.list_sources(db)


def sync_source(db: Session, source_id: int, actor: User, ip: str = "") -> dict:
    result = source_service.dispatch_sync(db, source_id)
    audit_service.record(db, actor, "source.sync", "source", source_id, f"task={result['task_id']}", ip)
    db.commit()
    return result
