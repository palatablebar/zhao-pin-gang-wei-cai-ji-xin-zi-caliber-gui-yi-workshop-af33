"""审计日志控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import audit_service


def recent(db: Session, limit: int = 50) -> list[dict]:
    rows = audit_service.recent(db, limit)
    return [
        {
            "id": row.id,
            "actor_email": row.actor_email,
            "actor_role": row.actor_role,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "detail": row.detail,
            "ip": row.ip,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
