"""采集入库（ingest）：同一公司 + 城市 + 职位只保留最新薪酬。

规则（纯函数 + 落库台账，重复提交同一批幂等）：

1. 自然键 dedupe_key = sha1(公司 | 归一城市 | 清洗后职位)。
   同一自然键在标准化表中最多一条 Posting（库级唯一约束兜底）。
2. 只有「更新版本的来源」才能覆盖旧版本：
   - published_at 更大 → 新版本：更新 Posting 薪酬等字段，原始记录标 superseded；
   - published_at 更小 → 迟到旧版本：Posting 保持最新，原始记录入湖但标
     RAW_DUPLICATE + 冲突说明，台账 action=merged / conflict=late_old_version；
   - 相同 published_at → 保留先入库版本，台账 action=ignored / same_published_at；
   - Posting.is_corrected=True → 人工修正保护，不覆盖薪资/城市/标题；
   - 新数据解析不出薪酬而现有 Posting 有值 → 不覆盖薪酬。
3. 异常记录（缺字段、公司/城市/职位为空、external_id 重复、薪酬面议或无法解析、
   兼职混入）单独隔离为 RAW_QUARANTINED：不进入标准化表、不参与基准样本。
4. 幂等：批次以 batch_key 唯一；同一批重复提交返回首次结果，不新增岗位。
   external_id 已入湖的记录按 natural key 幂等忽略，绝不改写已修正数据。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import (
    CONFLICT_LABELS,
    CONFLICT_LATE_OLD_VERSION,
    CONFLICT_MANUAL_CORRECTION,
    CONFLICT_SAME_PUBLISHED_AT,
    INGEST_ACTION_LABELS,
    INGEST_BATCH_COMPLETED,
    INGEST_BATCH_RUNNING,
    INGEST_FAILED,
    INGEST_IGNORED,
    INGEST_MERGED,
    INGEST_NEW,
    QUALITY_DAILY_WAGE,
    QUALITY_NEGOTIABLE,
    QUALITY_PARTTIME,
    RAW_CORRECTED,
    RAW_DUPLICATE,
    RAW_FAILED,
    RAW_INVALID,
    RAW_NEEDS_REVIEW,
    RAW_PARSED,
    RAW_QUARANTINED,
    RAW_STATUS_LABELS,
)
from src.models.ingest import IngestBatch, IngestRecord
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.services import audit_service
from src.services.salary_parser import parse_salary
from src.services.title_normalizer import clean_title, normalize_title
from src.utils.cities import normalize_city
from src.utils.errors import AppError

MAX_ITEMS_PER_BATCH = 500
REQUIRED_FIELDS = ("external_id", "title", "company", "city")
FIELD_LABELS = {
    "external_id": "external_id",
    "title": "职位标题",
    "company": "公司",
    "city": "城市",
}
QUARANTINE_REASON_TEXT = {
    "negotiable": "薪酬面议，缺少可比较月薪",
    "unparsed": "薪酬文本无法解析",
    "external_id_duplicate": "同一批次内 external_id 重复，仅保留首条",
    "company_city_title_empty": "公司/城市/职位清洗后为空，无法建立自然键",
    "parttime": "兼职/非全日制岗位，隔离出基准样本",
    "salary_reparse_failed": "薪酬无法解析且该自然键已有可用岗位",
    "title_unresolved": "职位标题无职能词命中，无法归一",
}


def dedupe_key_for(company: str, city: str, title_raw: str) -> str:
    """自然键：公司 + 归一城市 + 清洗后职位（去营销词/括号/空白，NFKC 小写）。

    用清洗后的原文标题而不是 canonical_title，避免把「高级Java工程师」与
    「Java后端工程师」这类不同岗位误合并。
    """
    company_key = re.sub(r"\s+", "", unicodedata.normalize("NFKC", company or "").lower())
    title_key = re.sub(r"\s+", "", clean_title(title_raw or ""))
    if not title_key:
        title_key = re.sub(r"\s+", "", unicodedata.normalize("NFKC", title_raw or "").lower())
    material = "|".join([company_key, normalize_city(city or ""), title_key])
    return hashlib.sha1(material.encode("utf-8")).hexdigest()


def serialize_batch(batch: IngestBatch) -> dict:
    return {
        "id": batch.id,
        "batch_key": batch.batch_key,
        "name": batch.name,
        "status": batch.status,
        "total_count": batch.total_count,
        "new_count": batch.new_count,
        "merged_count": batch.merged_count,
        "ignored_count": batch.ignored_count,
        "failed_count": batch.failed_count,
        "source_count": batch.source_count,
        "created_by": batch.created_by,
        "note": batch.note,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "finished_at": batch.finished_at.isoformat() if batch.finished_at else None,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


def serialize_record(record: IngestRecord) -> dict:
    return {
        "id": record.id,
        "batch_id": record.batch_id,
        "line_no": record.line_no,
        "source_id": record.source_id,
        "source_name": record.source_name,
        "external_id": record.external_id,
        "raw_id": record.raw_id,
        "posting_id": record.posting_id,
        "action": record.action,
        "action_label": INGEST_ACTION_LABELS.get(record.action, record.action),
        "reason": record.reason,
        "note": record.note,
        "conflict_kind": record.conflict_kind,
        "conflict_label": CONFLICT_LABELS.get(record.conflict_kind, ""),
        "company": record.company,
        "city": record.city,
        "canonical_title": record.canonical_title,
        "salary_raw": record.salary_raw,
        "salary_median": record.salary_median,
        "published_at": record.published_at.isoformat() if record.published_at else None,
        "before_source_id": record.before_source_id,
        "before_source_name": record.before_source_name,
        "after_source_id": record.after_source_id,
        "after_source_name": record.after_source_name,
        "before_salary_min": record.before_salary_min,
        "before_salary_max": record.before_salary_max,
        "incoming_salary_min": record.incoming_salary_min,
        "incoming_salary_max": record.incoming_salary_max,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


# ---------------------------------------------------------------- 输入规范化


def _parse_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None)


def _normalize_item(item: dict) -> dict:
    return {
        "external_id": str(item.get("external_id") or "").strip()[:80],
        "title": str(item.get("title") or "").strip()[:200],
        "salary_raw": str(item.get("salary_raw") or "").strip()[:120],
        "city": str(item.get("city") or "").strip()[:80],
        "company": str(item.get("company") or "").strip()[:120],
        "experience_raw": str(item.get("experience_raw") or "").strip()[:80],
        "employment_type_raw": str(item.get("employment_type_raw") or "全职").strip()[:40],
        "published_at": _parse_datetime(item.get("published_at")),
        "raw_json": item.get("raw_json") if isinstance(item.get("raw_json"), dict) else {},
    }


def _resolve_source(db: Session, item: dict) -> tuple[Source | None, str]:
    source_id = item.get("source_id")
    if source_id:
        source = db.get(Source, int(source_id))
        return (source, "") if source is not None else (None, f"source_id={source_id} 不存在")
    name = str(item.get("source_name") or "").strip()
    if name:
        source = db.query(Source).filter(Source.name == name).first()
        return (source, "") if source is not None else (None, f"采集源「{name}」不存在")
    return None, "缺少 source_id 或 source_name"


# ---------------------------------------------------------------- 主流程


def run_batch(db: Session, payload: dict, actor, ip: str = "") -> dict:
    """执行一批采集入库。返回批次统计 + 逐条台账 + 分源统计。"""
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise AppError(codes.VALIDATION_ERROR, "采集批次不能为空", "items 至少 1 条")
    if len(items) > MAX_ITEMS_PER_BATCH:
        raise AppError(codes.VALIDATION_ERROR, f"单批最多 {MAX_ITEMS_PER_BATCH} 条", f"items={len(items)}")
    batch_key = str(payload.get("batch_key") or "").strip()[:120]
    if not batch_key:
        raise AppError(codes.VALIDATION_ERROR, "batch_key 必填", "用于重复运行幂等")

    existing = db.query(IngestBatch).filter(IngestBatch.batch_key == batch_key).first()
    if existing is not None:
        return _batch_payload(db, existing, duplicate_batch=True)

    batch = IngestBatch(
        batch_key=batch_key,
        name=str(payload.get("name") or batch_key)[:160],
        status=INGEST_BATCH_RUNNING,
        total_count=len(items),
        created_by=getattr(actor, "email", "") or "system",
        note=str(payload.get("note") or "")[:2000],
    )
    db.add(batch)
    db.flush()

    seen_external: set[tuple[int, str]] = set()
    for line_no, raw_item in enumerate(items, start=1):
        if not isinstance(raw_item, dict):
            db.add(_failed_ledger(batch, line_no, {}, "invalid_payload", "单条不是 JSON 对象"))
            continue
        item = _normalize_item(raw_item)
        source, source_error = _resolve_source(db, raw_item)
        ledger = IngestRecord(
            batch_id=batch.id,
            line_no=line_no,
            external_id=item["external_id"],
            company=item["company"],
            city=item["city"],
            salary_raw=item["salary_raw"],
            published_at=item["published_at"],
            incoming_salary_min=None,
            incoming_salary_max=None,
        )
        if source is None:
            ledger.action = INGEST_FAILED
            ledger.reason = "source_unresolved"
            ledger.note = source_error
            ledger.after_source_id = None
            db.add(ledger)
            # 无法确定采集源：只失败不入湖（原始记录缺 source_id 无法追溯）
            continue
        ledger.source_id = source.id
        ledger.source_name = source.name
        ledger.after_source_id = source.id
        ledger.after_source_name = source.name

        missing = [field for field in REQUIRED_FIELDS if not item.get(field)]
        if missing:
            reason = "missing:" + ",".join(FIELD_LABELS.get(field, field) for field in missing)
            _quarantine(db, batch, ledger, item, source, reason)
            continue

        external_key = (source.id, item["external_id"])
        if external_key in seen_external:
            _quarantine(db, batch, ledger, item, source, "external_id_duplicate")
            continue
        seen_external.add(external_key)

        existing_raw = (
            db.query(RawPosting)
            .filter(RawPosting.source_id == source.id, RawPosting.external_id == item["external_id"])
            .first()
        )
        if existing_raw is not None:
            posting = db.query(Posting).filter(Posting.raw_id == existing_raw.id).first()
            ledger.action = INGEST_IGNORED
            ledger.reason = "external_id_exists"
            ledger.note = "同一采集源 external_id 已入湖，按幂等忽略（不改写已有数据）"
            ledger.raw_id = existing_raw.id
            ledger.posting_id = posting.id if posting else None
            ledger.canonical_title = posting.canonical_title if posting else ""
            ledger.salary_median = posting.salary_median if posting else None
            ledger.before_source_id = existing_raw.source_id
            ledger.before_source_name = source.name
            ledger.after_source_id = existing_raw.source_id
            ledger.after_source_name = source.name
            db.add(ledger)
            continue

        dedupe_key = dedupe_key_for(item["company"], item["city"], item["title"])
        if not dedupe_key:
            _quarantine(db, batch, ledger, item, source, "company_city_title_empty")
            continue

        salary = parse_salary(item["salary_raw"], "v2")
        title = normalize_title(item["title"], item["experience_raw"])
        ledger.canonical_title = title.canonical_title
        ledger.salary_median = salary.salary_median
        ledger.incoming_salary_min = salary.salary_min
        ledger.incoming_salary_max = salary.salary_max

        posting = _find_posting(db, dedupe_key, item["company"], item["city"], title.canonical_title)
        reason = _quarantine_reason(item, salary, title)
        if reason:
            if posting is not None and salary.salary_min is not None:
                reason = ""  # 已有可用岗位且本条能解析薪酬：走正常合并
            elif posting is not None:
                reason = "salary_reparse_failed"
        if reason:
            _quarantine(db, batch, ledger, item, source, reason, dedupe_key=dedupe_key, posting=posting)
            continue

        raw = _insert_raw(db, batch, item, source, salary, dedupe_key, RAW_PARSED)
        source.raw_count = (source.raw_count or 0) + 1
        ledger.raw_id = raw.id

        if posting is None:
            posting = _create_posting(db, raw, item, salary, title, batch)
            ledger.action = INGEST_NEW
            ledger.reason = "new_posting"
            ledger.posting_id = posting.id
            ledger.after_source_id = source.id
            ledger.after_source_name = source.name
            ledger.note = f"新增标准化岗位 #{posting.id}（{source.name}）"
        else:
            _merge_existing(db, posting, raw, item, salary, title, batch, ledger)
        db.add(ledger)

    db.flush()
    _finalize_batch(db, batch)
    audit_service.record(
        db, actor, "ingest.run", "ingest_batch", batch.id,
        f"batch={batch_key} total={batch.total_count} new={batch.new_count} "
        f"merged={batch.merged_count} ignored={batch.ignored_count} failed={batch.failed_count}",
        ip,
    )
    db.flush()
    return _batch_payload(db, batch, duplicate_batch=False)


def _finalize_batch(db: Session, batch: IngestBatch) -> None:
    def count(action: str) -> int:
        return int(
            db.query(func.count(IngestRecord.id))
            .filter(IngestRecord.batch_id == batch.id, IngestRecord.action == action)
            .scalar()
            or 0
        )

    batch.status = INGEST_BATCH_COMPLETED
    batch.finished_at = datetime.utcnow()
    batch.new_count = count(INGEST_NEW)
    batch.merged_count = count(INGEST_MERGED)
    batch.ignored_count = count(INGEST_IGNORED)
    batch.failed_count = count(INGEST_FAILED)
    batch.source_count = int(
        db.query(func.count(func.distinct(IngestRecord.source_id)))
        .filter(IngestRecord.batch_id == batch.id)
        .scalar()
        or 0
    )
    db.flush()


def _merge_existing(db: Session, posting: Posting, raw: RawPosting, item: dict, salary, title,
                    batch: IngestBatch, ledger: IngestRecord) -> None:
    """把新采到的同一自然键记录合并进现有 Posting，并把合并前后写进台账。"""
    ledger.posting_id = posting.id
    ledger.before_source_id = posting.source_id
    ledger.before_source_name = _source_name(db, posting.source_id)
    ledger.before_salary_min = posting.salary_min
    ledger.before_salary_max = posting.salary_max
    existing_raw = db.get(RawPosting, posting.raw_id)
    existing_published = existing_raw.published_at if existing_raw else None

    def settle(action: str, conflict: str, note: str) -> None:
        ledger.action = action
        ledger.conflict_kind = conflict
        ledger.reason = conflict or "dedupe_merge"
        ledger.note = note
        ledger.after_source_id = posting.source_id
        ledger.after_source_name = _source_name(db, posting.source_id)
        ledger.salary_median = posting.salary_median
        ledger.canonical_title = posting.canonical_title
        # 冲突说明同时写进 raw_json，原始队列详情可直接看到
        raw.raw_json = dict(raw.raw_json or {})
        raw.raw_json["ingest_conflict"] = {
            "kind": conflict,
            "label": CONFLICT_LABELS.get(conflict, ""),
            "note": note,
            "batch_key": batch.batch_key,
            "before_source": ledger.before_source_name,
            "after_source": ledger.after_source_name,
        }

    if posting.is_corrected:
        raw.status = RAW_DUPLICATE
        raw.parse_reason = CONFLICT_MANUAL_CORRECTION
        raw.superseded_by_raw_id = posting.raw_id
        raw.superseded_at = datetime.utcnow()
        settle(
            INGEST_IGNORED,
            CONFLICT_MANUAL_CORRECTION,
            f"现有岗位 #{posting.id} 已人工修正，收到的新数据不覆盖修正值",
        )
        return
    if item["published_at"] is None or existing_published is None:
        settle(INGEST_IGNORED, CONFLICT_SAME_PUBLISHED_AT,
               "发布时间缺失，无法判定版本先后，保留先入库版本")
        return
    if item["published_at"] == existing_published:
        settle(INGEST_IGNORED, CONFLICT_SAME_PUBLISHED_AT,
               f"发布时间相同（{item['published_at']:%Y-%m-%d %H:%M}），保留先入库版本")
        return
    if item["published_at"] < existing_published:
        raw.status = RAW_DUPLICATE
        raw.parse_reason = CONFLICT_LATE_OLD_VERSION
        raw.superseded_by_raw_id = posting.raw_id
        raw.superseded_at = datetime.utcnow()
        settle(
            INGEST_MERGED,
            CONFLICT_LATE_OLD_VERSION,
            f"迟到旧版本（{item['published_at']:%Y-%m-%d %H:%M} < "
            f"{existing_published:%Y-%m-%d %H:%M}），保留最新薪酬 "
            f"{posting.salary_min}-{posting.salary_max}（来源 {_source_name(db, posting.source_id)}）",
        )
        return
    if salary.salary_min is None and posting.salary_min is not None:
        settle(INGEST_MERGED, CONFLICT_SAME_PUBLISHED_AT,
               "新版本薪酬无法解析，保留现有薪酬")
        return

    before = (posting.salary_min, posting.salary_max)
    before_source_name = _source_name(db, posting.source_id)
    posting.salary_min = salary.salary_min
    posting.salary_max = salary.salary_max
    posting.salary_median = salary.salary_median
    posting.salary_unit = salary.unit_kind
    posting.annual_months = salary.annual_months
    posting.canonical_title = title.canonical_title
    posting.function_type = title.function_type
    posting.seniority = title.seniority
    posting.city = normalize_city(item["city"])
    posting.source_id = raw.source_id
    posting.raw_id = raw.id
    posting.confidence = round(
        0.5 * (salary.confidence if salary.is_hit else 0.4) + 0.5 * title.confidence, 2
    )
    posting.rule_version = "v2"
    posting.title_matches = title.matched_terms
    posting.quality_flags = _quality_flags(salary, item["employment_type_raw"])
    posting.parse_reason = salary.reason_code
    posting.ingest_batch_id = batch.id
    posting.updated_at = datetime.utcnow()
    if existing_raw is not None and existing_raw.id != raw.id:
        existing_raw.superseded_by_raw_id = raw.id
        existing_raw.superseded_at = datetime.utcnow()
        if existing_raw.status != RAW_CORRECTED:
            existing_raw.status = RAW_DUPLICATE
    settle(
        INGEST_MERGED,
        "",
        f"新版本覆盖旧版本：{before[0]}-{before[1]}（{before_source_name}）→ "
        f"{salary.salary_min}-{salary.salary_max}（{_source_name(db, raw.source_id)}）",
    )
    ledger.after_source_id = raw.source_id
    ledger.after_source_name = _source_name(db, raw.source_id)
    ledger.salary_median = salary.salary_median


def _create_posting(db: Session, raw: RawPosting, item: dict, salary, title,
                    batch: IngestBatch) -> Posting:
    posting = Posting(
        raw_id=raw.id,
        source_id=raw.source_id,
        canonical_title=title.canonical_title,
        function_type=title.function_type,
        seniority=title.seniority,
        city=normalize_city(item["city"]),
        salary_min=salary.salary_min,
        salary_max=salary.salary_max,
        salary_median=salary.salary_median,
        salary_unit=salary.unit_kind,
        annual_months=salary.annual_months,
        is_fulltime="兼职" not in item["employment_type_raw"],
        confidence=round(0.5 * salary.confidence + 0.5 * title.confidence, 2),
        rule_version="v2",
        title_matches=title.matched_terms,
        quality_flags=_quality_flags(salary, item["employment_type_raw"]),
        parse_reason=salary.reason_code,
        dedupe_key=raw.dedupe_key,
        ingest_batch_id=batch.id,
    )
    db.add(posting)
    db.flush()
    return posting


def _find_posting(db: Session, dedupe_key: str, company: str, city: str,
                  canonical_title: str) -> Posting | None:
    """先按自然键找标准化岗位；历史数据（dedupe_key 为空）按原始字段回填后匹配。

    历史库可能同一自然键已有多条 Posting：取发布时间最新的一条作为合并目标并回填
    dedupe_key，其余历史行保持原样（不删除用户数据），新采集不会再新增重复岗位。
    """
    posting = db.query(Posting).filter(Posting.dedupe_key == dedupe_key).first()
    if posting is not None:
        return posting
    candidates: list[tuple[datetime, Posting]] = []
    legacy_rows = (
        db.query(Posting, RawPosting)
        .join(RawPosting, RawPosting.id == Posting.raw_id)
        .filter(Posting.dedupe_key.is_(None))
        .filter(RawPosting.company == company)
        .filter(Posting.city == normalize_city(city))
        .all()
    )
    for legacy_posting, legacy_raw in legacy_rows:
        if dedupe_key_for(legacy_raw.company, legacy_raw.city_raw, legacy_raw.title_raw) != dedupe_key:
            continue
        candidates.append((legacy_raw.published_at or legacy_raw.created_at, legacy_posting))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    survivor = candidates[0][1]
    survivor.dedupe_key = dedupe_key
    return survivor


def _insert_raw(db: Session, batch: IngestBatch, item: dict, source: Source, salary,
                dedupe_key: str, status: str) -> RawPosting:
    raw = RawPosting(
        source_id=source.id,
        external_id=item["external_id"],
        title_raw=item["title"],
        salary_raw=item["salary_raw"],
        city_raw=item["city"],
        experience_raw=item["experience_raw"],
        employment_type_raw=item["employment_type_raw"],
        company=item["company"],
        published_at=item["published_at"],
        raw_json=item["raw_json"] or {
            "external_id": item["external_id"],
            "title": item["title"],
            "salary": item["salary_raw"],
            "city": item["city"],
            "experience": item["experience_raw"],
            "employment_type": item["employment_type_raw"],
            "company": item["company"],
            "source": source.name,
            "ingest_batch": batch.batch_key,
        },
        status=status,
        parse_reason=salary.reason_code,
        rule_version="v2",
        dedupe_key=dedupe_key,
        ingest_batch_id=batch.id,
    )
    db.add(raw)
    db.flush()
    return raw


def _quarantine_reason(item: dict, salary, title) -> str:
    """只隔离「无法形成可比较岗位」的记录。

    面议/无法解析/缺字段/兼职/批内重复/标题无法归一等异常不进标准化表；
    「上下限倒置」「极端值」「日结折算」仍属于已有质量门禁（quality_flags）范畴，
    照常入库并打标记，不在这里重复隔离。
    """
    if salary.status == "negotiable":
        return "negotiable"
    if salary.status == "unparsed" or salary.salary_min is None:
        return "unparsed"
    if not title.matched_terms and title.confidence < 0.6:
        return "title_unresolved"
    if "兼职" in item["employment_type_raw"]:
        return "parttime"
    return ""


def _raw_status_for_quarantine(reason: str) -> str:
    if reason.startswith("missing:") or reason in (
        "external_id_duplicate",
        "company_city_title_empty",
        "title_unresolved",
    ):
        return RAW_INVALID
    if reason in ("negotiable", "unparsed", "salary_reparse_failed"):
        return RAW_FAILED
    return RAW_NEEDS_REVIEW


def _quarantine_text(reason: str) -> str:
    if reason.startswith("missing:"):
        return "缺少必填字段：" + reason.split(":", 1)[1]
    return QUARANTINE_REASON_TEXT.get(reason, reason)


def _quarantine(db: Session, batch: IngestBatch, ledger: IngestRecord, item: dict, source: Source,
                reason: str, dedupe_key: str | None = None,
                posting: Posting | None = None) -> None:
    """异常记录隔离：原始记录照常入湖（状态 quarantined），不进标准化表与基准样本。"""
    if not dedupe_key:
        dedupe_key = dedupe_key_for(item["company"], item["city"], item["title"])
    raw_status = _raw_status_for_quarantine(reason)
    raw = _insert_raw(db, batch, item, source, _StubParse(reason), dedupe_key, RAW_QUARANTINED)
    raw.parse_reason = reason
    raw.raw_json = dict(raw.raw_json or {})
    raw.raw_json["quarantine"] = {"reason": reason, "inner_status": raw_status}
    source.raw_count = (source.raw_count or 0) + 1

    ledger.action = INGEST_FAILED
    ledger.reason = reason
    ledger.note = _quarantine_text(reason)
    ledger.raw_id = raw.id
    ledger.posting_id = posting.id if posting else None
    ledger.conflict_kind = ""
    if posting is not None:
        ledger.before_source_id = posting.source_id
        ledger.before_source_name = _source_name(db, posting.source_id)
        ledger.canonical_title = posting.canonical_title
        ledger.salary_median = posting.salary_median
    db.add(ledger)


class _StubParse:
    """隔离记录没有可用的薪资解析结果，只保留 reason_code。"""

    reason_code = ""
    salary_min = None
    salary_max = None
    salary_median = None

    def __init__(self, reason: str) -> None:
        self.reason_code = reason[:64]


def _failed_ledger(batch: IngestBatch, line_no: int, item: dict, reason: str, note: str) -> IngestRecord:
    return IngestRecord(
        batch_id=batch.id,
        line_no=line_no,
        external_id=str(item.get("external_id") or "")[:80],
        company=str(item.get("company") or "")[:120],
        city=str(item.get("city") or "")[:24],
        salary_raw=str(item.get("salary_raw") or "")[:120],
        action=INGEST_FAILED,
        reason=reason,
        note=note[:2000],
    )


def _quality_flags(result, employment_raw: str) -> list[str]:
    flags = list(result.flags)
    if result.status == "negotiable" and QUALITY_NEGOTIABLE not in flags:
        flags.append(QUALITY_NEGOTIABLE)
    if any(token in (result.matched_rules or []) for token in ("daily_wage", "hourly_wage")):
        if QUALITY_DAILY_WAGE not in flags:
            flags.append(QUALITY_DAILY_WAGE)
    if "兼职" in (employment_raw or ""):
        flags.append(QUALITY_PARTTIME)
    deduped: list[str] = []
    for flag in flags:
        if flag not in deduped:
            deduped.append(flag)
    return deduped


def _source_name(db: Session, source_id: int | None) -> str:
    if not source_id:
        return "—"
    source = db.get(Source, source_id)
    return source.name if source else f"source#{source_id}"


def _records_for_batch(db: Session, batch_id: int) -> list[IngestRecord]:
    return (
        db.query(IngestRecord)
        .filter(IngestRecord.batch_id == batch_id)
        .order_by(IngestRecord.line_no, IngestRecord.id)
        .all()
    )


def _source_breakdown(db: Session, batch_id: int) -> list[dict]:
    rows = (
        db.query(IngestRecord.source_name, IngestRecord.action, func.count(IngestRecord.id))
        .filter(IngestRecord.batch_id == batch_id)
        .group_by(IngestRecord.source_name, IngestRecord.action)
        .all()
    )
    result: dict[str, dict] = {}
    for source_name, action, count in rows:
        entry = result.setdefault(
            source_name or "—",
            {"source_name": source_name or "—", "total": 0, "new": 0, "merged": 0,
             "ignored": 0, "failed": 0},
        )
        entry["total"] += count
        entry[action] = entry.get(action, 0) + count
    return sorted(result.values(), key=lambda entry: (-entry["total"], entry["source_name"]))


def _batch_payload(db: Session, batch: IngestBatch, duplicate_batch: bool) -> dict:
    return {
        **serialize_batch(batch),
        "duplicate_batch": duplicate_batch,
        "records": [serialize_record(record) for record in _records_for_batch(db, batch.id)],
        "source_breakdown": _source_breakdown(db, batch.id),
    }


# ---------------------------------------------------------------- 查询


def list_batches(db: Session, limit: int = 20) -> list[dict]:
    rows = db.query(IngestBatch).order_by(IngestBatch.id.desc()).limit(limit).all()
    return [serialize_batch(batch) for batch in rows]


def get_batch(db: Session, batch_id: int) -> dict:
    batch = db.get(IngestBatch, batch_id)
    if batch is None:
        raise AppError(codes.NOT_FOUND, "采集批次不存在", f"batch_id={batch_id}")
    return _batch_payload(db, batch, duplicate_batch=False)


def list_records(db: Session, batch_id: int, action: str | None = None,
                 conflict_only: bool = False, limit: int = 500) -> list[dict]:
    query = db.query(IngestRecord).filter(IngestRecord.batch_id == batch_id)
    if action:
        query = query.filter(IngestRecord.action == action)
    if conflict_only:
        query = query.filter(IngestRecord.conflict_kind != "")
    rows = query.order_by(IngestRecord.line_no).limit(limit).all()
    return [serialize_record(record) for record in rows]


def demo_payload(db: Session) -> dict:
    """五渠道重送演示批（含 source_id 映射），前端一键投递。"""
    from scripts.demo_ingest_batch import demo_batch

    source_ids = {
        name: source_id
        for source_id, name in db.query(Source.id, Source.name).all()
    }
    return demo_batch(source_ids)


def summary(db: Session) -> dict:
    """采集总览：累计新增/合并/忽略/失败 + 隔离/冲突/折叠计数 + 最近一批。"""
    counts = {INGEST_NEW: 0, INGEST_MERGED: 0, INGEST_IGNORED: 0, INGEST_FAILED: 0}
    for action, count in (
        db.query(IngestRecord.action, func.count(IngestRecord.id))
        .group_by(IngestRecord.action)
        .all()
    ):
        counts[action] = count
    conflict_count = int(
        db.query(func.count(IngestRecord.id))
        .filter(IngestRecord.conflict_kind != "")
        .scalar() or 0
    )
    quarantined = int(
        db.query(func.count(RawPosting.id))
        .filter(RawPosting.status == RAW_QUARANTINED).scalar() or 0
    )
    duplicate_folded = int(
        db.query(func.count(RawPosting.id))
        .filter(RawPosting.status == RAW_DUPLICATE).scalar() or 0
    )
    batches = int(db.query(func.count(IngestBatch.id)).scalar() or 0)
    latest = db.query(IngestBatch).order_by(IngestBatch.id.desc()).first()
    return {
        "batches": batches,
        "new": counts[INGEST_NEW],
        "merged": counts[INGEST_MERGED],
        "ignored": counts[INGEST_IGNORED],
        "failed": counts[INGEST_FAILED],
        "conflicts": conflict_count,
        "quarantined_raws": quarantined,
        "duplicate_folded_raws": duplicate_folded,
        "latest_batch": serialize_batch(latest) if latest else None,
        "action_labels": INGEST_ACTION_LABELS,
        "conflict_labels": CONFLICT_LABELS,
        "quarantine_status": RAW_QUARANTINED,
        "quarantine_status_label": RAW_STATUS_LABELS.get(RAW_QUARANTINED, RAW_QUARANTINED),
    }
