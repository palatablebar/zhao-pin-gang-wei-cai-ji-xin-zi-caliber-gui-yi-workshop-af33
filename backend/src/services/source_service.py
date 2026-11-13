"""采集源服务：列表 + 模拟同步（Celery 异步）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import SITE_TYPE_LABELS
from src.models.source import Source
from src.utils.errors import AppError


def serialize(source: Source) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "site_type": source.site_type,
        "site_type_label": SITE_TYPE_LABELS.get(source.site_type, source.site_type),
        "enabled": source.enabled,
        "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
        "raw_count": source.raw_count,
        "sync_status": source.sync_status,
        "note": source.note,
    }


def list_sources(db: Session) -> list[dict]:
    return [serialize(row) for row in db.query(Source).order_by(Source.id).all()]


def get_source(db: Session, source_id: int) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise AppError(codes.NOT_FOUND, "采集源不存在", f"source_id={source_id}")
    return source


def dispatch_sync(db: Session, source_id: int) -> dict:
    source = get_source(db, source_id)
    if not source.enabled:
        raise AppError(codes.CONFLICT, "采集源已停用，无法同步", f"source={source.name}")
    source.sync_status = "queued"
    db.flush()
    from src.tasks import sync_source

    task = sync_source.delay(source_id)
    return {
        "task_id": task.id,
        "source_id": source_id,
        "message": "已投递 Celery 同步任务（worker 消费）",
    }
