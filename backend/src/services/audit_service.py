"""审计日志服务：所有写操作显式调用，带 actor/实体/明细/IP。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.models.user import User


def record(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str = "",
    entity_id: str | int = "",
    detail: str = "",
    ip: str = "",
) -> AuditLog:
    entry = AuditLog(
        actor_email=actor.email if actor else "system",
        actor_role=actor.role if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        detail=detail[:2000],
        ip=ip or "",
    )
    db.add(entry)
    return entry


def recent(db: Session, limit: int = 50) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
