"""质量门禁控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import quality_service


def list_quality(db: Session, flag: str | None, status: str | None,
                 page: int | None, size: int | None) -> dict:
    return quality_service.list_quality(db, flag, status, page, size)


def dispose(db: Session, posting_id: int, action: str, note: str, actor: User, ip: str = "") -> dict:
    result = quality_service.dispose(db, posting_id, action, note, actor, ip)
    db.commit()
    return result
