"""审计日志路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def recent(limit: int = 50, db: Session = Depends(get_db),
           _: User = Depends(require_permission("audit:read"))) -> list[dict]:
    return audit_controller.recent(db, min(limit, 200))
