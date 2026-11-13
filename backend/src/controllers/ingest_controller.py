"""采集入库控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import ingest_service


def run_batch(db: Session, payload: dict, actor: User, ip: str = "") -> dict:
    result = ingest_service.run_batch(db, payload, actor, ip)
    db.commit()
    return result


def list_batches(db: Session) -> list[dict]:
    return ingest_service.list_batches(db)


def get_batch(db: Session, batch_id: int) -> dict:
    return ingest_service.get_batch(db, batch_id)


def list_records(db: Session, batch_id: int, action: str | None, conflict_only: bool) -> list[dict]:
    return ingest_service.list_records(db, batch_id, action, conflict_only)


def summary(db: Session) -> dict:
    return ingest_service.summary(db)


def demo(db: Session) -> dict:
    return ingest_service.demo_payload(db)
