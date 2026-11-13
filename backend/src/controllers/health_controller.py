"""健康检查控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import health_service


def health(db: Session) -> dict:
    return health_service.check(db)
