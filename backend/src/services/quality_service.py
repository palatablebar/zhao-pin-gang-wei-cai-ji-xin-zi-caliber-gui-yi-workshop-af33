"""质量门禁服务：异常分类队列 + 处置（fix/ignore）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import QUALITY_LABELS, QUALITY_STATUS_DISPOSED, QUALITY_STATUS_IGNORED
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.services import audit_service
from src.services.posting_service import serialize_posting
from src.utils.errors import AppError
from src.utils.pagination import normalize_pagination, page_payload


def list_quality(db: Session, flag: str | None, status: str | None,
                 page: int | None, size: int | None) -> dict:
    offset, limit = normalize_pagination(page, size)
    query = (
        db.query(Posting, RawPosting, Source.name)
        .join(RawPosting, RawPosting.id == Posting.raw_id)
        .join(Source, Source.id == Posting.source_id)
        .filter(func.json_length(Posting.quality_flags) > 0)
    )
    if status:
        query = query.filter(Posting.quality_status == status)
    if flag:
        query = query.filter(func.json_contains(Posting.quality_flags, f'"{flag}"'))
    total = query.count()
    rows = query.order_by(Posting.id).offset(offset).limit(limit).all()
    items = []
    for posting, raw, source_name in rows:
        flags = posting.quality_flags or []
        items.append(
            {
                "posting": serialize_posting(posting, raw, source_name),
                "primary_flag": flags[0] if flags else "",
                "flag_labels": [QUALITY_LABELS.get(f, f) for f in flags],
            }
        )
    by_type = (
        db.query(func.json_unquote(func.json_extract(Posting.quality_flags, "$[0]")), func.count(Posting.id))
        .filter(func.json_length(Posting.quality_flags) > 0)
        .group_by(func.json_unquote(func.json_extract(Posting.quality_flags, "$[0]")))
        .all()
    )
    return {
        **page_payload(items, total, offset // limit + 1, limit),
        "by_type": [
            {"flag": key, "label": QUALITY_LABELS.get(key or "", key or ""), "count": count}
            for key, count in by_type
        ],
    }


def dispose(db: Session, posting_id: int, action: str, note: str, actor, ip: str) -> dict:
    posting = db.get(Posting, posting_id)
    if posting is None:
        raise AppError(codes.NOT_FOUND, "标准化岗位不存在", f"posting_id={posting_id}")
    status = QUALITY_STATUS_DISPOSED if action == "disposed" else QUALITY_STATUS_IGNORED
    posting.quality_status = status
    posting.disposition_note = note[:255]
    posting.disposed_by = actor.email
    posting.disposed_at = datetime.utcnow()
    audit_service.record(
        db, actor, "quality.dispose", "posting", posting.id,
        f"action={action} flags={posting.quality_flags} note={note}", ip,
    )
    db.flush()
    return {"posting_id": posting.id, "quality_status": posting.quality_status, "note": posting.disposition_note}
