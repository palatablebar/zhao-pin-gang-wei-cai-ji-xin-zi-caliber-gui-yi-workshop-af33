"""Celery 入口：backend 侧投递，worker 容器消费（同一份镜像）。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "jobnorm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "jobnorm-heartbeat": {
            "task": "jobnorm.heartbeat",
            "schedule": 15.0,
        },
    },
)

TASK_SYNC_SOURCE = "jobnorm.sync_source"
TASK_HEARTBEAT = "jobnorm.heartbeat"

# `celery -A src.config.celery_app` 会查找模块级 app 属性
app = celery_app
