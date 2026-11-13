"""演示数据 seed（幂等）。

运行方式：
  - 容器启动时 SEED_DEMO=true 自动执行一次（见 src/config/app.py）
  - 手动：docker compose exec -T backend python -m scripts.seed_demo

幂等：自然键 upsert，重复执行不新增、不覆盖用户修改；结束时打印一行
`SEED_SUMMARY brand=jobnorm sources=... raws=... postings=... rules=... benchmarks=... users=...`
两次执行该行必须逐字一致（Lead 用这一行判幂等）。

数据规模：5 采集源 / 180 原始岗位（150 可归一 + 23 重复折叠 + 5 脏原文 + 2 硬失败）
/ 150 标准化岗位（12 条质量标记）/ 6 条规则（v1/v2）/ 3 份基准 / 3 个账号。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from scripts.demo_corpus import BUCKETS, SOURCES, build_corpus
from src.config.database import session_scope
from src.constants.enums import (
    QUALITY_DAILY_WAGE,
    QUALITY_NEGOTIABLE,
    QUALITY_PARTTIME,
    RAW_CORRECTED,
    RAW_DUPLICATE,
    RAW_FAILED,
    RAW_INVALID,
    RAW_NEEDS_REVIEW,
    RAW_PARSED,
    RULE_TYPE_SALARY,
)
from src.models.audit_log import AuditLog
from src.models.benchmark import Benchmark
from src.models.parse_rule import ParseRule
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.models.user import User
from src.services.percentile import percentiles
from src.services.salary_parser import parse_salary, trial_rate
from src.services.title_normalizer import normalize_title
from src.utils.cities import normalize_city

BRAND = "jobnorm"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEMO_PASSWORD = "Demo@2026"

DEMO_USERS = [
    {"email": "admin@jobnorm.io", "name": "陈知远", "role": "admin"},
    {"email": "analyst@jobnorm.io", "name": "林小满", "role": "analyst"},
    {"email": "client@jobnorm.io", "name": "周雨桐", "role": "client"},
]

RULES = [
    {
        "code": "v1-k-range",
        "rule_set": "salary",
        "version": "v1",
        "name": "K 区间 / 单值",
        "pattern": r"(\d+(?:\.\d+)?)\s*k\s*[-~]?\s*(\d+(?:\.\d+)?)\s*k",
        "action": "salary.k_range",
        "description": "15-25K / 18K，K=千=1000",
    },
    {
        "code": "v1-wan",
        "rule_set": "salary",
        "version": "v1",
        "name": "年薪/月薪 万口径",
        "pattern": r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*万\s*(?:元)?\s*(?:/|每)?\s*(年|月)",
        "action": "salary.wan_period",
        "description": "20-30万/年 ÷12；1.5-2万/月 ×10000",
    },
    {
        "code": "v1-annual-months",
        "rule_set": "salary",
        "version": "v1",
        "name": "13-16 薪折算",
        "pattern": r"(\d{1,2})\s*(?:[-~]\s*(\d{1,2}))?\s*薪",
        "action": "salary.annual_months",
        "description": "·14薪 / 13-16薪（取上限）→ 月薪 ×months/12",
    },
    {
        "code": "v2-negotiable",
        "rule_set": "salary",
        "version": "v2",
        "name": "面议识别",
        "pattern": r"面议|可谈|面谈",
        "action": "salary.negotiable",
        "description": "面议 → 薪资 null + negotiable，不再当作解析失败",
    },
    {
        "code": "v2-period-convert",
        "rule_set": "salary",
        "version": "v2",
        "name": "日结/时薪折算",
        "pattern": r"(\d+(?:\.\d+)?)\s*(?:元)?\s*(?:/|每)\s*(天|日|小时|时)|日结\s*(\d+)",
        "action": "salary.period_convert",
        "description": "日结 ×22、时薪 ×8×22，统一折月薪",
    },
    {
        "code": "v2-qian-range",
        "rule_set": "salary",
        "version": "v2",
        "name": "中文千区间",
        "pattern": r"(\d+(?:\.\d+)?)\s*千\s*[-~]\s*(\d+(?:\.\d+)?)\s*万",
        "action": "salary.qian_range",
        "description": "8千-1.2万 → 8000-12000 元/月",
    },
]

BENCHMARK_TARGETS = [
    ("杭州", "backend", False),   # 演示：admin 在流程中发布这一份
    ("上海", "backend", True),
    ("北京", "data", True),
]


def _ensure_users(db: Session) -> int:
    created = 0
    for spec in DEMO_USERS:
        existing = db.query(User).filter(User.email == spec["email"]).first()
        if existing:
            continue
        db.add(
            User(
                email=spec["email"],
                name=spec["name"],
                role=spec["role"],
                password_hash=pwd_context.hash(DEMO_PASSWORD),
                is_active=True,
            )
        )
        created += 1
    db.flush()
    return created


def _ensure_sources(db: Session) -> int:
    created = 0
    for spec in SOURCES:
        existing = db.query(Source).filter(Source.name == spec["name"]).first()
        if existing:
            continue
        db.add(
            Source(
                name=spec["name"],
                site_type=spec["site_type"],
                enabled=spec["enabled"],
                note=spec["note"],
                raw_count=0,
            )
        )
        created += 1
    db.flush()
    return created


def _ensure_rules(db: Session) -> int:
    created = 0
    for spec in RULES:
        existing = db.query(ParseRule).filter(ParseRule.code == spec["code"]).first()
        if existing:
            continue
        db.add(
            ParseRule(
                code=spec["code"],
                rule_set=spec["rule_set"],
                version=spec["version"],
                rule_type=RULE_TYPE_SALARY,
                name=spec["name"],
                pattern=spec["pattern"],
                action=spec["action"],
                description=spec["description"],
                hit_count=0,
                enabled=True,
                is_active_set=spec["version"] == "v1",
            )
        )
        created += 1
    db.flush()
    return created


def _status_for(category: str, salary_hit: bool, title_confidence: float) -> str:
    if category == "duplicate":
        return RAW_DUPLICATE
    if category == "invalid":
        return RAW_INVALID
    if category == "failed":
        return RAW_FAILED
    if not salary_hit or title_confidence < 0.6:
        return RAW_NEEDS_REVIEW
    return RAW_PARSED


def _quality_flags(salary_raw: str, result, employment_raw: str, title_confidence: float) -> list[str]:
    flags = list(result.flags)
    lowered = salary_raw.lower()
    if result.salary_min is None and ("面议" in salary_raw or "可谈" in salary_raw):
        flags.append(QUALITY_NEGOTIABLE)
    if any(token in lowered for token in ("/天", "日结", "元/天", "/小时", "元/时")):
        if QUALITY_DAILY_WAGE not in flags:
            flags.append(QUALITY_DAILY_WAGE)
    if "兼职" in (employment_raw or ""):
        flags.append(QUALITY_PARTTIME)
    if title_confidence < 0.6:
        flags.append("needs_review")
    # 去重且保持稳定顺序
    seen: list[str] = []
    for flag in flags:
        if flag not in seen:
            seen.append(flag)
    return seen


def _create_corpus(db: Session) -> dict:
    sources = {s.name: s for s in db.query(Source).all()}
    source_by_code = {
        "lagou": "拉勾招聘",
        "boss": "BOSS直聘",
        "liepin": "猎聘",
        "company": "岗线企业招聘官网",
        "ruishi": "锐仕方达猎头",
    }
    corpus = build_corpus()
    created_raw = 0
    created_postings = 0
    base_day = datetime(2026, 11, 1, 9, 30)
    for index, item in enumerate(corpus):
        source = sources[source_by_code[item.source_code]]
        external_id = item.external_id
        exists = (
            db.query(RawPosting)
            .filter(RawPosting.source_id == source.id, RawPosting.external_id == external_id)
            .first()
        )
        if exists:
            continue
        salary_result = parse_salary(item.salary_raw, "v1")
        title_result = normalize_title(item.title_raw, item.experience_raw)
        status = _status_for(item.category, salary_result.is_hit, title_result.confidence)
        flags = (
            _quality_flags(item.salary_raw, salary_result, item.employment_type_raw, title_result.confidence)
            if item.category.startswith("posting")
            else []
        )
        raw = RawPosting(
            source_id=source.id,
            external_id=external_id,
            title_raw=item.title_raw,
            salary_raw=item.salary_raw,
            city_raw=item.city_raw,
            experience_raw=item.experience_raw,
            employment_type_raw=item.employment_type_raw,
            company=item.company,
            published_at=base_day + timedelta(hours=index),
            raw_json={
                "external_id": external_id,
                "title": item.title_raw,
                "salary": item.salary_raw,
                "city": item.city_raw,
                "experience": item.experience_raw,
                "employment_type": item.employment_type_raw,
                "company": item.company,
                "source": source.name,
                "collected_by": "jobnorm-collector/1.4",
                "category": item.category,
            },
            status=status,
            parse_reason=salary_result.reason_code,
            rule_version="v1",
        )
        db.add(raw)
        db.flush()
        source.raw_count += 1
        created_raw += 1
        if item.category.startswith("posting"):
            confidence = round(
                0.5 * (salary_result.confidence if salary_result.is_hit else 0.4)
                + 0.5 * title_result.confidence,
                2,
            )
            posting = Posting(
                raw_id=raw.id,
                source_id=source.id,
                canonical_title=title_result.canonical_title,
                function_type=title_result.function_type,
                seniority=title_result.seniority,
                city=normalize_city(item.city_raw),
                salary_min=salary_result.salary_min,
                salary_max=salary_result.salary_max,
                salary_median=salary_result.salary_median,
                salary_unit=salary_result.unit_kind,
                annual_months=salary_result.annual_months,
                is_fulltime="兼职" not in item.employment_type_raw,
                confidence=confidence,
                rule_version="v1",
                title_matches=title_result.matched_terms,
                quality_flags=flags,
                quality_status="open",
                parse_reason=salary_result.reason_code,
            )
            db.add(posting)
            created_postings += 1
    db.flush()

    # 规则试跑命中率（真实重算，按规则动作映射写入每条规则 hit_count）
    from src.services.rule_service import apply_rule_hit_counts

    texts = [item.salary_raw for item in corpus]
    for version in ("v1", "v2"):
        rate = trial_rate(texts, version)
        apply_rule_hit_counts(db, version, rate)

    # 基准报表：杭州/backend（干净样本 32）、上海/backend、北京/data
    for city, function_type, published in BENCHMARK_TARGETS:
        rows = (
            db.query(Posting)
            .filter(Posting.city == city, Posting.function_type == function_type)
            .filter(Posting.salary_median.isnot(None))
            .filter(func.json_length(Posting.quality_flags) == 0)
            .all()
        )
        values = [row.salary_median for row in rows if row.salary_median is not None]
        pct = percentiles(values)
        if pct is None:
            continue
        exists = (
            db.query(Benchmark)
            .filter(Benchmark.city == city, Benchmark.function_type == function_type)
            .first()
        )
        if exists:
            continue
        db.add(
            Benchmark(
                city=city,
                function_type=function_type,
                sample_count=len(values),
                p25=pct[25],
                p50=pct[50],
                p75=pct[75],
                rule_version="v1",
                version=1,
                published=published,
            )
        )
    return {"raws": created_raw, "postings": created_postings}


def _ensure_audit(db: Session) -> int:
    if db.query(AuditLog).count() > 0:
        return 0
    events = [
        ("seed.demo_loaded", "system", "seed", "180 raw / 150 posting"),
        ("rule.trial", "analyst@jobnorm.io", "rule_set", "v1 hit=164/180"),
        ("benchmark.generate", "admin@jobnorm.io", "benchmark", "杭州/backend sample=32"),
        ("quality.dispose", "analyst@jobnorm.io", "quality", "首批质量队列 12 条待处置"),
    ]
    for action, actor, entity, detail in events:
        db.add(
            AuditLog(
                actor_email=actor,
                actor_role="system" if actor == "system" else ("analyst" if "analyst" in actor else "admin"),
                action=action,
                entity_type=entity,
                entity_id="-",
                detail=detail,
                ip="127.0.0.1",
            )
        )
    return len(events)


def summary_counts(db: Session) -> dict:
    return {
        "sources": db.query(Source).count(),
        "raws": db.query(RawPosting).count(),
        "postings": db.query(Posting).count(),
        "rules": db.query(ParseRule).count(),
        "benchmarks": db.query(Benchmark).count(),
        "users": db.query(User).count(),
    }


def summary_line(counts: dict) -> str:
    return (
        f"SEED_SUMMARY brand={BRAND} sources={counts['sources']} raws={counts['raws']} "
        f"postings={counts['postings']} rules={counts['rules']} "
        f"benchmarks={counts['benchmarks']} users={counts['users']}"
    )


def seed_all() -> dict:
    created: dict[str, int] = {}
    with session_scope() as db:
        created["users"] = _ensure_users(db)
        created["sources"] = _ensure_sources(db)
        created["rules"] = _ensure_rules(db)
        raw_count = db.query(RawPosting).count()
        if raw_count == 0:
            corpus_result = _create_corpus(db)
            created.update(corpus_result)
        else:
            created["raws"] = 0
            created["postings"] = 0
        created["audit"] = _ensure_audit(db)
        db.flush()
        counts = summary_counts(db)
    line = summary_line(counts)
    print(line, flush=True)
    return {"created": created, "counts": counts, "summary": line}


def main() -> None:
    result = seed_all()
    print(f"seed_demo done created={result['created']}", flush=True)


if __name__ == "__main__":
    main()
