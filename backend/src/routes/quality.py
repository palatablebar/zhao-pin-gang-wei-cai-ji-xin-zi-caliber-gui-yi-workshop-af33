"""质量门禁路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import quality_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.quality import DisposeIn

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("")
def list_quality(flag: str | None = None, status: str | None = None,
                 page: int = 1, size: int = 20, db: Session = Depends(get_db),
                 _: User = Depends(require_permission("read"))) -> dict:
    return quality_controller.list_quality(db, flag, status, page, size)


@router.post("/{posting_id}/dispose")
def dispose(posting_id: int, payload: DisposeIn, request: Request,
            db: Session = Depends(get_db),
            actor: User = Depends(require_permission("quality:dispose"))) -> dict:
    return quality_controller.dispose(
        db, posting_id, payload.action, payload.note, actor, client_ip(request)
    )
