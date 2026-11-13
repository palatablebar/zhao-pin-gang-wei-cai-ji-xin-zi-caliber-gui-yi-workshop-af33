"""健康检查：DB / Redis / worker 心跳。"""
from __future__ import annotations

import redis

from src.config.database import ping_db
from src.config.settings import settings


def check(db=None) -> dict:
    redis_ok = False
    worker_heartbeat = False
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        redis_ok = bool(client.ping())
        worker_heartbeat = client.get("jobnorm:worker:heartbeat") is not None
    except Exception:  # noqa: BLE001
        redis_ok = False
    db_ok = ping_db()
    active = "v1"
    if db_ok and db is not None:
        try:
            from src.services.rule_service import active_version

            active = active_version(db)
        except Exception:  # noqa: BLE001
            active = "v1"
    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "db": db_ok,
        "redis": redis_ok,
        "worker_heartbeat": worker_heartbeat,
        "active_rule_version": active,
    }
