"""口径规则服务：试跑命中率、切版本重跑、激活版本（admin）。"""
from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import (
    QUALITY_DAILY_WAGE,
    QUALITY_NEGOTIABLE,
    RAW_CORRECTED,
    RAW_DUPLICATE,
    RAW_FAILED,
    RAW_INVALID,
    RAW_NEEDS_REVIEW,
    RAW_PARSED,
)
from src.models.parse_rule import ParseRule
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.services import audit_service
from src.services.salary_parser import parse_salary, trial_rate
from src.services.title_normalizer import normalize_title
from src.utils.cities import normalize_city
from src.utils.errors import AppError

TRIAL_SAMPLE = 12

# 规则动作 → salary_parser 命中的模式键（用于把试跑命中数落到每条规则）
RULE_HIT_KEYS = {
    "salary.k_range": ["k_range"],
    "salary.wan_period": ["wan_year", "wan_month"],
    "salary.annual_months": ["annual_months"],
    "salary.negotiable": ["negotiable"],
    "salary.period_convert": ["daily_wage", "hourly_wage"],
    "salary.qian_range": ["qian_range"],
}


def apply_rule_hit_counts(db: Session, version: str, rate: dict) -> None:
    rules = db.query(ParseRule).filter(ParseRule.version == version).all()
    for rule in rules:
        keys = RULE_HIT_KEYS.get(rule.action, [])
        rule.hit_count = sum(rate["rule_hits"].get(key, 0) for key in keys)


def serialize_rule(rule: ParseRule) -> dict:
    return {
        "id": rule.id,
        "code": rule.code,
        "rule_set": rule.rule_set,
        "version": rule.version,
        "rule_type": rule.rule_type,
        "name": rule.name,
        "pattern": rule.pattern,
        "action": rule.action,
        "description": rule.description,
        "hit_count": rule.hit_count,
        "enabled": rule.enabled,
        "is_active_set": rule.is_active_set,
    }


def list_rules(db: Session) -> list[dict]:
    rules = db.query(ParseRule).order_by(ParseRule.version, ParseRule.id).all()
    return [serialize_rule(rule) for rule in rules]


def active_version(db: Session) -> str:
    rule = db.query(ParseRule).filter(ParseRule.is_active_set.is_(True)).first()
    return rule.version if rule else "v1"


def trial(db: Session, version: str) -> dict:
    raws = db.query(RawPosting).order_by(RawPosting.id).all()
    texts = [raw.salary_raw for raw in raws]
    result = trial_rate(texts, version)
    samples = []
    for raw in raws:
        if len(samples) >= TRIAL_SAMPLE:
            break
        parsed = parse_salary(raw.salary_raw, version)
        if parsed.status in ("unparsed", "negotiable") or "薪" in raw.salary_raw:
            samples.append(
                {
                    "raw": raw.salary_raw,
                    "status": parsed.status,
                    "salary_min": parsed.salary_min,
                    "salary_max": parsed.salary_max,
                    "annual_months": parsed.annual_months,
                    "reason_code": parsed.reason_code,
                }
            )
    result["samples"] = samples
    return result


def _status_after(raw: RawPosting, salary_ok: bool, negotiable: bool,
                  title_confidence: float, unparsed: bool = False) -> str:
    if raw.status in (RAW_DUPLICATE, RAW_INVALID):
        return raw.status
    if raw.status == RAW_CORRECTED:
        return RAW_CORRECTED
    # 硬失败（任何版本都解析不出的文本）保持 failed，不被降级成「待修正」
    if not salary_ok and unparsed and raw.status == RAW_FAILED:
        return RAW_FAILED
    if negotiable or not salary_ok or title_confidence < 0.6:
        return RAW_NEEDS_REVIEW
    return RAW_PARSED


def _flags_after(posting: Posting, raw: RawPosting, salary, title_confidence: float) -> list[str]:
    flags = list(salary.flags)
    text = raw.salary_raw
    if salary.salary_min is None and ("面议" in text or "可谈" in text):
        flags.append(QUALITY_NEGOTIABLE)
    if any(token in text for token in ("/天", "日结", "元/天", "/小时", "元/时")):
        flags.append(QUALITY_DAILY_WAGE)
    if "兼职" in (raw.employment_type_raw or ""):
        flags.append("parttime")
    if title_confidence < 0.6:
        flags.append("needs_review")
    deduped: list[str] = []
    for flag in flags:
        if flag not in deduped:
            deduped.append(flag)
    return deduped


def reparse(db: Session, version: str, actor, ip: str) -> dict:
    """切规则版本重跑全部原始队列；人工修正过的岗位不再覆盖。"""
    if version not in ("v1", "v2"):
        raise AppError(codes.VALIDATION_ERROR, "规则版本仅支持 v1/v2", f"version={version}")
    started = time.perf_counter()
    previous = active_version(db)
    raws = db.query(RawPosting).order_by(RawPosting.id).all()
    before = trial_rate([raw.salary_raw for raw in raws], previous)
    after = trial_rate([raw.salary_raw for raw in raws], version)

    updated_postings = 0
    skipped_corrected = 0
    for raw in raws:
        if raw.status in (RAW_DUPLICATE, RAW_INVALID):
            raw.rule_version = version
            continue
        salary = parse_salary(raw.salary_raw, version)
        title = normalize_title(raw.title_raw, raw.experience_raw)
        posting = db.query(Posting).filter(Posting.raw_id == raw.id).first()
        raw.rule_version = version
        if posting is not None and posting.is_corrected:
            skipped_corrected += 1
            raw.status = RAW_CORRECTED
            continue
        raw.status = _status_after(
            raw,
            salary.is_hit,
            salary.status == "negotiable",
            title.confidence,
            unparsed=salary.status == "unparsed",
        )
        raw.parse_reason = salary.reason_code
        if posting is None:
            continue
        posting.salary_min = salary.salary_min
        posting.salary_max = salary.salary_max
        posting.salary_median = salary.salary_median
        posting.salary_unit = salary.unit_kind
        posting.annual_months = salary.annual_months
        posting.canonical_title = title.canonical_title
        posting.function_type = title.function_type
        posting.seniority = title.seniority
        posting.city = normalize_city(raw.city_raw)
        posting.confidence = round(
            0.5 * (salary.confidence if salary.is_hit else 0.4) + 0.5 * title.confidence, 2
        )
        posting.rule_version = version
        posting.title_matches = title.matched_terms
        posting.quality_flags = _flags_after(posting, raw, salary, title.confidence)
        posting.parse_reason = salary.reason_code
        updated_postings += 1

    # 规则版本激活标记 + 版本级命中数（写进该版本第一条规则，供 UI 直接展示）
    db.query(ParseRule).update({ParseRule.is_active_set: False})
    db.query(ParseRule).filter(ParseRule.version == version).update({ParseRule.is_active_set: True})
    apply_rule_hit_counts(db, previous, before)
    apply_rule_hit_counts(db, version, after)
    duration_ms = int((time.perf_counter() - started) * 1000)
    audit_service.record(
        db, actor, "rule.reparse", "rule_set", version,
        f"{previous}->{version} before={before['hits']}/{before['attempts']} after={after['hits']}/{after['attempts']} updated={updated_postings}",
        ip,
    )
    db.flush()
    return {
        "previous_version": previous,
        "active_version": version,
        "before": before,
        "after": after,
        "updated_raws": len(raws),
        "updated_postings": updated_postings,
        "skipped_corrected": skipped_corrected,
        "duration_ms": duration_ms,
    }


def activate(db: Session, version: str, actor, ip: str) -> dict:
    if version not in ("v1", "v2"):
        raise AppError(codes.VALIDATION_ERROR, "规则版本仅支持 v1/v2", f"version={version}")
    db.query(ParseRule).update({ParseRule.is_active_set: False})
    count = db.query(ParseRule).filter(ParseRule.version == version).update({ParseRule.is_active_set: True})
    audit_service.record(db, actor, "rule.activate", "rule_set", version, f"rules={count}", ip)
    db.flush()
    return {"version": version, "active": True, "rules": count}


def title_merge_demo(db: Session) -> dict:
    """标题 3-gram 归并演示：对当前 canonical_title 做一次真实归并统计。"""
    from src.services.title_normalizer import batch_merge_titles

    postings = db.query(Posting).order_by(Posting.id).all()
    titles = [posting.canonical_title for posting in postings]
    return batch_merge_titles(titles)
