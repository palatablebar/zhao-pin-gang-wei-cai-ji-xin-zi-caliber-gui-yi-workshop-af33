"""Celery 任务：worker 容器真实消费。

1. jobnorm.heartbeat：beat 每 15s 写 Redis 心跳（worker 健康检查依据）。
2. jobnorm.sync_source：模拟采集源增量同步（生成 2 条新原始岗位，自然键幂等），
   由 /api/sources/{id}/sync 异步投递，前端轮询 sync_status。
"""
from __future__ import annotations

import json
import time

import redis
from sqlalchemy import func

from src.config.celery_app import celery_app
from src.config.database import SessionLocal
from src.config.settings import settings
from src.constants.enums import RAW_PARSED
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.services.salary_parser import parse_salary
from src.services.title_normalizer import normalize_title
from src.utils.cities import normalize_city

HEARTBEAT_KEY = "jobnorm:worker:heartbeat"


@celery_app.task(name="jobnorm.heartbeat")
def heartbeat() -> str:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    stamp = str(time.time())
    client.set(HEARTBEAT_KEY, stamp, ex=120)
    return stamp


@celery_app.task(name="jobnorm.sync_source")
def sync_source(source_id: int) -> dict:
    """模拟同步：为指定源追加 2 条演示岗位（external_id 幂等，重复执行不新增）。"""
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            return {"ok": False, "reason": "source_not_found"}
        source.sync_status = "running"
        db.commit()

        created = 0
        base = 900
        for offset in (1, 2):
            external_id = f"SYNC-{source_id}-{base + offset}"
            exists = (
                db.query(RawPosting)
                .filter(RawPosting.source_id == source_id, RawPosting.external_id == external_id)
                .first()
            )
            if exists:
                continue
            title = "高级数据开发工程师" if offset == 1 else "后端开发工程师"
            salary_raw = "22-32K·14薪" if offset == 1 else "16-26K"
            title_result = normalize_title(title, "3-5年")
            salary_result = parse_salary(salary_raw, "v2")
            raw = RawPosting(
                source_id=source_id,
                external_id=external_id,
                title_raw=title,
                salary_raw=salary_raw,
                city_raw="杭州市·滨江区",
                experience_raw="3-5年",
                employment_type_raw="全职",
                company="岗线数据服务",
                raw_json={"title": title, "salary": salary_raw, "synced": True},
                status=RAW_PARSED,
                parse_reason="synced",
                rule_version="v2",
            )
            db.add(raw)
            db.flush()
            from src.models.posting import Posting

            posting = Posting(
                raw_id=raw.id,
                source_id=source_id,
                canonical_title=title_result.canonical_title,
                function_type=title_result.function_type,
                seniority=title_result.seniority,
                city=normalize_city(raw.city_raw),
                salary_min=salary_result.salary_min,
                salary_max=salary_result.salary_max,
                salary_median=salary_result.salary_median,
                salary_unit=salary_result.unit_kind,
                annual_months=salary_result.annual_months,
                is_fulltime=True,
                confidence=min(title_result.confidence, salary_result.confidence),
                rule_version="v2",
                title_matches=title_result.matched_terms,
                quality_flags=salary_result.flags,
                parse_reason=salary_result.reason_code,
            )
            db.add(posting)
            source.raw_count = (source.raw_count or 0) + 1
            created += 1
        source.last_sync_at = func.now()
        source.sync_status = "idle"
        db.commit()
        return {"ok": True, "source_id": source_id, "created": created}
    except Exception:  # noqa: BLE001
        db.rollback()
        try:
            source = db.get(Source, source_id)
            if source is not None:
                source.sync_status = "failed"
                db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise
    finally:
        db.close()
