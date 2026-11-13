"""原始岗位队列服务：筛选、对照预览、人工修正。"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import RAW_CORRECTED, RAW_QUARANTINED, RAW_STATUS_LABELS
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.services import audit_service
from src.services.salary_parser import parse_salary
from src.services.title_normalizer import normalize_title
from src.utils.cities import normalize_city
from src.utils.errors import AppError
from src.utils.pagination import normalize_pagination, page_payload


def _preview(raw: RawPosting, version: str) -> dict:
    salary = parse_salary(raw.salary_raw, version)
    title = normalize_title(raw.title_raw, raw.experience_raw)
    return {
        "version": version,
        "status": salary.status,
        "salary_min": salary.salary_min,
        "salary_max": salary.salary_max,
        "salary_median": salary.salary_median,
        "annual_months": salary.annual_months,
        "unit_kind": salary.unit_kind,
        "confidence": salary.confidence,
        "reason_code": salary.reason_code,
        "flags": salary.flags,
        "matched_rules": salary.matched_rules,
        "canonical_title": title.canonical_title,
        "function_type": title.function_type,
        "seniority": title.seniority,
        "title_confidence": title.confidence,
        "matched_terms": title.matched_terms,
        "city": normalize_city(raw.city_raw),
    }


def _serialize_raw(raw: RawPosting, source_name: str, posting_id: int | None) -> dict:
    return {
        "id": raw.id,
        "source_id": raw.source_id,
        "source_name": source_name,
        "external_id": raw.external_id,
        "title_raw": raw.title_raw,
        "salary_raw": raw.salary_raw,
        "city_raw": raw.city_raw,
        "experience_raw": raw.experience_raw,
        "employment_type_raw": raw.employment_type_raw,
        "company": raw.company,
        "status": raw.status,
        "status_label": RAW_STATUS_LABELS.get(raw.status, raw.status),
        "parse_reason": raw.parse_reason,
        "rule_version": raw.rule_version,
        "published_at": raw.published_at.isoformat() if raw.published_at else None,
        "posting_id": posting_id,
        "company": raw.company,
        "dedupe_key": raw.dedupe_key or "",
        "ingest_batch_id": raw.ingest_batch_id,
        "superseded_by_raw_id": raw.superseded_by_raw_id,
    }


def list_raws(db: Session, status: str | None, city: str | None, q: str | None,
              source_id: int | None, page: int | None, size: int | None) -> dict:
    offset, limit = normalize_pagination(page, size)
    query = (
        db.query(RawPosting, Source.name, Posting.id)
        .join(Source, Source.id == RawPosting.source_id)
        .outerjoin(Posting, Posting.raw_id == RawPosting.id)
    )
    if status:
        query = query.filter(RawPosting.status == status)
    if source_id:
        query = query.filter(RawPosting.source_id == source_id)
    if city:
        query = query.filter(RawPosting.city_raw.like(f"%{city}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(RawPosting.title_raw.like(like), RawPosting.salary_raw.like(like),
                RawPosting.external_id.like(like))
        )
    total = query.count()
    rows = query.order_by(RawPosting.id).offset(offset).limit(limit).all()
    items = [_serialize_raw(row[0], row[1], row[2]) for row in rows]
    return page_payload(items, total, offset // limit + 1, limit)


def status_counts(db: Session) -> list[dict]:
    from sqlalchemy import func

    rows = db.query(RawPosting.status, func.count(RawPosting.id)).group_by(RawPosting.status).all()
    return [
        {"status": status, "label": RAW_STATUS_LABELS.get(status, status), "count": count}
        for status, count in rows
    ]


def get_raw(db: Session, raw_id: int) -> dict:
    row = (
        db.query(RawPosting, Source.name, Posting)
        .join(Source, Source.id == RawPosting.source_id)
        .outerjoin(Posting, Posting.raw_id == RawPosting.id)
        .filter(RawPosting.id == raw_id)
        .first()
    )
    if row is None:
        raise AppError(codes.NOT_FOUND, "原始岗位不存在", f"raw_id={raw_id}")
    raw, source_name, posting = row
    data = _serialize_raw(raw, source_name, posting.id if posting else None)
    data["raw_json"] = raw.raw_json or {}
    data["dedupe_key"] = raw.dedupe_key or ""
    data["ingest_batch_id"] = raw.ingest_batch_id
    data["superseded_by_raw_id"] = raw.superseded_by_raw_id
    data["superseded_at"] = raw.superseded_at.isoformat() if raw.superseded_at else None
    data["conflict_note"] = (raw.raw_json or {}).get("ingest_conflict", "") if raw.raw_json else ""
    from src.services.rule_service import active_version

    current_version = active_version(db)
    data["current"] = _preview(raw, current_version)
    data["compare_versions"] = [_preview(raw, "v1"), _preview(raw, "v2")]
    return data


def correct_raw(db: Session, raw_id: int, payload: dict, actor, ip: str) -> dict:
    raw = db.get(RawPosting, raw_id)
    if raw is None:
        raise AppError(codes.NOT_FOUND, "原始岗位不存在", f"raw_id={raw_id}")
    if raw.status == RAW_QUARANTINED:
        raise AppError(
            codes.CONFLICT,
            "该记录已被采集入库隔离，需先在采集页查看冲突说明",
            f"raw_id={raw_id}",
        )
    if payload.get("title_raw"):
        raw.title_raw = payload["title_raw"][:200]
    if payload.get("salary_raw"):
        raw.salary_raw = payload["salary_raw"][:120]
    if payload.get("city_raw"):
        raw.city_raw = payload["city_raw"][:80]

    salary = parse_salary(raw.salary_raw, "v2")
    salary_min = payload.get("salary_min")
    salary_max = payload.get("salary_max")
    if salary_min is not None and salary_max is not None:
        if salary_min > salary_max:
            salary_min, salary_max = salary_max, salary_min
        salary_min = int(salary_min)
        salary_max = int(salary_max)
        salary_median = (salary_min + salary_max) // 2
    else:
        salary_min, salary_max, salary_median = salary.salary_min, salary.salary_max, salary.salary_median

    title = normalize_title(raw.title_raw, raw.experience_raw)
    from src.services.ingest_service import dedupe_key_for

    dedupe_key = raw.dedupe_key or dedupe_key_for(raw.company, raw.city_raw, raw.title_raw)
    posting = db.query(Posting).filter(Posting.raw_id == raw.id).first()
    if posting is None:
        posting = (
            db.query(Posting)
            .filter(Posting.dedupe_key == dedupe_key)
            .first()
        )
    if posting is None:
        posting = Posting(
            raw_id=raw.id,
            source_id=raw.source_id,
            canonical_title=title.canonical_title,
            function_type=title.function_type,
            seniority=title.seniority,
            city=normalize_city(raw.city_raw),
            salary_unit=salary.unit_kind,
            annual_months=salary.annual_months,
            is_fulltime="兼职" not in raw.employment_type_raw,
            title_matches=title.matched_terms,
            dedupe_key=dedupe_key,
        )
        db.add(posting)
        db.flush()
    posting.raw_id = raw.id
    posting.source_id = raw.source_id
    posting.canonical_title = title.canonical_title
    posting.function_type = title.function_type
    posting.seniority = title.seniority
    posting.city = normalize_city(raw.city_raw)
    posting.salary_min = salary_min
    posting.salary_max = salary_max
    posting.salary_median = salary_median
    posting.salary_unit = salary.unit_kind
    posting.annual_months = salary.annual_months
    posting.confidence = max(0.5, min(0.99, title.confidence))
    posting.rule_version = "manual"
    posting.title_matches = title.matched_terms
    posting.is_corrected = True
    posting.corrected_by = actor.email
    from datetime import datetime

    posting.corrected_at = datetime.utcnow()
    posting.parse_reason = "manual_correction"
    raw.status = RAW_CORRECTED
    raw.parse_reason = "manual_correction"
    raw.rule_version = "manual"
    audit_service.record(
        db, actor, "raw.correct", "raw_posting", raw.id,
        f"salary={salary_min}-{salary_max} city={posting.city}", ip,
    )
    db.flush()
    return get_raw(db, raw_id)
