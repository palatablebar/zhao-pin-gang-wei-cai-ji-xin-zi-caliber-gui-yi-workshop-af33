"""标准化岗位服务：筛选/统计/人工修正/CSV 导出。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import (
    FUNCTION_LABELS,
    QUALITY_LABELS,
    QUALITY_NEGOTIABLE,
    SENIORITY_LABELS,
)
from src.constants.limits import MAX_EXPORT_ROWS
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.services import audit_service
from src.utils.errors import AppError
from src.utils.pagination import normalize_pagination, page_payload


def serialize_posting(posting: Posting, raw: RawPosting | None = None, source_name: str = "",
                      source_names: list[str] | None = None, batch_id: int | None = None) -> dict:
    return {
        "id": posting.id,
        "raw_id": posting.raw_id,
        "source_id": posting.source_id,
        "source_name": source_name,
        "canonical_title": posting.canonical_title,
        "function_type": posting.function_type,
        "function_label": FUNCTION_LABELS.get(posting.function_type, posting.function_type),
        "seniority": posting.seniority,
        "seniority_label": SENIORITY_LABELS.get(posting.seniority, posting.seniority),
        "city": posting.city,
        "salary_min": posting.salary_min,
        "salary_max": posting.salary_max,
        "salary_median": posting.salary_median,
        "salary_unit": posting.salary_unit,
        "annual_months": posting.annual_months,
        "is_fulltime": posting.is_fulltime,
        "confidence": posting.confidence,
        "rule_version": posting.rule_version,
        "title_matches": posting.title_matches or [],
        "quality_flags": posting.quality_flags or [],
        "quality_flag_labels": [QUALITY_LABELS.get(f, f) for f in (posting.quality_flags or [])],
        "quality_status": posting.quality_status,
        "is_corrected": posting.is_corrected,
        "parse_reason": posting.parse_reason,
        "raw_title": raw.title_raw if raw else "",
        "raw_salary": raw.salary_raw if raw else "",
        "dedupe_key": posting.dedupe_key or "",
        "ingest_batch_id": posting.ingest_batch_id,
        "source_names": source_names or ([source_name] if source_name else []),
    }


def _base_query(db: Session):
    return (
        db.query(Posting, RawPosting, Source.name)
        .join(RawPosting, RawPosting.id == Posting.raw_id)
        .join(Source, Source.id == Posting.source_id)
    )


def list_postings(
    db: Session,
    city: str | None,
    function_type: str | None,
    seniority: str | None,
    unit: str | None,
    q: str | None,
    flagged: bool | None,
    corrected: bool | None,
    page: int | None,
    size: int | None,
) -> dict:
    offset, limit = normalize_pagination(page, size)
    query = _base_query(db)
    if city:
        query = query.filter(Posting.city == city)
    if function_type:
        query = query.filter(Posting.function_type == function_type)
    if seniority:
        query = query.filter(Posting.seniority == seniority)
    if unit:
        query = query.filter(Posting.salary_unit == unit)
    if flagged is True:
        query = query.filter(func.json_length(Posting.quality_flags) > 0)
    if flagged is False:
        query = query.filter(func.json_length(Posting.quality_flags) == 0)
    if corrected is not None:
        query = query.filter(Posting.is_corrected == corrected)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Posting.canonical_title.like(like), RawPosting.title_raw.like(like)))
    total = query.count()
    rows = query.order_by(Posting.id).offset(offset).limit(limit).all()
    source_sets = _source_names_for(db, [posting.dedupe_key for posting, _, _ in rows if posting.dedupe_key])
    items = [
        serialize_posting(posting, raw, source_name, source_sets.get(posting.dedupe_key or ""))
        for posting, raw, source_name in rows
    ]
    return page_payload(items, total, offset // limit + 1, limit)


def _source_names_for(db: Session, dedupe_keys: list[str]) -> dict[str, list[str]]:
    """同一自然键被哪些采集源投递过（标准化行的「合并前后来源」）。"""
    if not dedupe_keys:
        return {}
    rows = (
        db.query(RawPosting.dedupe_key, Source.name)
        .join(Source, Source.id == RawPosting.source_id)
        .filter(RawPosting.dedupe_key.in_(dedupe_keys))
        .order_by(RawPosting.id)
        .all()
    )
    result: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    for dedupe_key, source_name in rows:
        if not dedupe_key:
            continue
        bucket = seen.setdefault(dedupe_key, set())
        if source_name in bucket:
            continue
        bucket.add(source_name)
        result.setdefault(dedupe_key, []).append(source_name)
    return result


def stats(db: Session) -> dict:
    def group(column, limit: int = 12) -> list[dict]:
        rows = (
            db.query(column, func.count(Posting.id))
            .group_by(column)
            .order_by(func.count(Posting.id).desc())
            .limit(limit)
            .all()
        )
        return [{"key": key, "count": count} for key, count in rows]

    from src.constants.enums import RAW_DUPLICATE, RAW_QUARANTINED

    return {
        "total": db.query(Posting).count(),
        "flagged": db.query(Posting).filter(func.json_length(Posting.quality_flags) > 0).count(),
        "corrected": db.query(Posting).filter(Posting.is_corrected.is_(True)).count(),
        "merged": db.query(RawPosting).filter(RawPosting.status == RAW_DUPLICATE).count(),
        "quarantined": db.query(RawPosting).filter(RawPosting.status == RAW_QUARANTINED).count(),
        "by_city": group(Posting.city),
        "by_function": group(Posting.function_type),
        "by_seniority": group(Posting.seniority),
    }


def get_posting(db: Session, posting_id: int) -> dict:
    row = _base_query(db).filter(Posting.id == posting_id).first()
    if row is None:
        raise AppError(codes.NOT_FOUND, "标准化岗位不存在", f"posting_id={posting_id}")
    posting, raw, source_name = row
    return serialize_posting(posting, raw, source_name)


def correct_posting(db: Session, posting_id: int, payload: dict, actor, ip: str) -> dict:
    posting = db.get(Posting, posting_id)
    if posting is None:
        raise AppError(codes.NOT_FOUND, "标准化岗位不存在", f"posting_id={posting_id}")
    before = {
        "canonical_title": posting.canonical_title,
        "function_type": posting.function_type,
        "seniority": posting.seniority,
        "city": posting.city,
        "salary": [posting.salary_min, posting.salary_max],
    }
    for field in ("canonical_title", "function_type", "seniority", "city"):
        value = payload.get(field)
        if value:
            setattr(posting, field, value)
    salary_min = payload.get("salary_min")
    salary_max = payload.get("salary_max")
    if salary_min is not None or salary_max is not None:
        low = salary_min if salary_min is not None else posting.salary_min
        high = salary_max if salary_max is not None else posting.salary_max
        if low is None or high is None:
            raise AppError(codes.VALIDATION_ERROR, "修正薪资需同时给出上下限", "salary_min/salary_max")
        if low > high:
            low, high = high, low
        posting.salary_min = int(low)
        posting.salary_max = int(high)
        posting.salary_median = (int(low) + int(high)) // 2
        flags = list(posting.quality_flags or [])
        if QUALITY_NEGOTIABLE in flags and posting.salary_min is not None:
            flags = [f for f in flags if f != QUALITY_NEGOTIABLE]
            posting.quality_flags = flags
    posting.is_corrected = True
    posting.corrected_by = actor.email
    posting.corrected_at = datetime.utcnow()
    posting.parse_reason = "manual_correction"
    audit_service.record(
        db, actor, "posting.correct", "posting", posting.id,
        f"before={before} after={payload} note={payload.get('note', '')}", ip,
    )
    db.flush()
    return get_posting(db, posting_id)


def export_csv(db: Session, city: str | None, function_type: str | None) -> str:
    query = _base_query(db)
    if city:
        query = query.filter(Posting.city == city)
    if function_type:
        query = query.filter(Posting.function_type == function_type)
    rows = query.order_by(Posting.id).limit(MAX_EXPORT_ROWS).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "posting_id", "city", "function_type", "seniority", "canonical_title",
        "salary_min", "salary_max", "salary_median", "annual_months", "salary_unit",
        "is_fulltime", "quality_flags", "rule_version", "source", "raw_salary",
    ])
    for posting, raw, source_name in rows:
        writer.writerow([
            posting.id, posting.city, posting.function_type, posting.seniority,
            posting.canonical_title, posting.salary_min, posting.salary_max,
            posting.salary_median, posting.annual_months, posting.salary_unit,
            "全职" if posting.is_fulltime else "兼职",
            "|".join(posting.quality_flags or []), posting.rule_version,
            source_name, raw.salary_raw,
        ])
    return buffer.getvalue()
