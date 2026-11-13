"""Celery 任务：worker 容器真实消费。

1. jobnorm.heartbeat：beat 每 15s 写 Redis 心跳（worker 健康检查依据）。
2. jobnorm.sync_source：模拟采集源增量同步（生成 2 条新原始岗位，自然键幂等），
   由 /api/sources/{id}/sync 异步投递，前端轮询 sync_status。
"""
from __future__ import annotations

import time

import redis
from sqlalchemy import func

from src.config.celery_app import celery_app
from src.config.database import SessionLocal
from src.config.settings import settings
from src.models.source import Source

HEARTBEAT_KEY = "jobnorm:worker:heartbeat"


@celery_app.task(name="jobnorm.heartbeat")
def heartbeat() -> str:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    stamp = str(time.time())
    client.set(HEARTBEAT_KEY, stamp, ex=120)
    return stamp


@celery_app.task(name="jobnorm.sync_source")
def sync_source(source_id: int) -> dict:
    """模拟同步：把该源的 2 条演示岗位交给采集入库服务（自然键去重 + 幂等）。

    与 /api/ingest/batches 走同一套逻辑：同一公司+城市+职位只保留最新薪酬，
    迟到旧版本留冲突说明，异常记录隔离；重复执行不新增岗位。
    """
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            return {"ok": False, "reason": "source_not_found"}
        source.sync_status = "running"
        db.commit()

        from datetime import datetime, timedelta

        from src.services.ingest_service import run_batch

        now = datetime.utcnow()
        items = [
            {
                "source_id": source_id,
                "external_id": f"SYNC-{source_id}-901",
                "title": "高级数据开发工程师",
                "salary_raw": "22-32K·14薪",
                "city": "杭州市·滨江区",
                "company": "岗线数据服务",
                "experience_raw": "3-5年",
                "employment_type_raw": "全职",
                "published_at": (now - timedelta(hours=1)).isoformat(timespec="seconds"),
                "raw_json": {"synced": True, "channel": source.name},
            },
            {
                "source_id": source_id,
                "external_id": f"SYNC-{source_id}-902",
                "title": "后端开发工程师",
                "salary_raw": "16-26K",
                "city": "杭州市·滨江区",
                "company": "岗线数据服务",
                "experience_raw": "3-5年",
                "employment_type_raw": "全职",
                "published_at": now.isoformat(timespec="seconds"),
                "raw_json": {"synced": True, "channel": source.name},
            },
        ]
        result = run_batch(
            db,
            {
                "batch_key": f"sync-source-{source_id}-{now:%Y%m%d}",
                "name": f"{source.name} 增量同步",
                "items": items,
            },
            None,
        )
        source.last_sync_at = func.now()
        source.sync_status = "idle"
        db.commit()
        return {
            "ok": True,
            "source_id": source_id,
            "created": result["new_count"],
            "merged": result["merged_count"],
            "ignored": result["ignored_count"],
            "failed": result["failed_count"],
            "duplicate_batch": result["duplicate_batch"],
        }
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
