"""原始岗位控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import raw_service


def list_raws(db: Session, status: str | None, city: str | None, q: str | None,
              source_id: int | None, page: int | None, size: int | None) -> dict:
    return raw_service.list_raws(db, status, city, q, source_id, page, size)


def status_counts(db: Session) -> list[dict]:
    return raw_service.status_counts(db)


def get_raw(db: Session, raw_id: int) -> dict:
    return raw_service.get_raw(db, raw_id)


def correct_raw(db: Session, raw_id: int, payload: dict, actor: User, ip: str = "") -> dict:
    result = raw_service.correct_raw(db, raw_id, payload, actor, ip)
    db.commit()
    return result
