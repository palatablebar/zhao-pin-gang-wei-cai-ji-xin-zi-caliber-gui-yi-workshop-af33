"""原始岗位队列路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import raw_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.raw import RawCorrectIn

router = APIRouter(prefix="/raw", tags=["raw"])


@router.get("")
def list_raws(status: str | None = None, city: str | None = None, q: str | None = None,
              source_id: int | None = None, page: int = 1, size: int = 20,
              db: Session = Depends(get_db),
              _: User = Depends(require_permission("read"))) -> dict:
    return raw_controller.list_raws(db, status, city, q, source_id, page, size)


@router.get("/status-counts")
def status_counts(db: Session = Depends(get_db),
                  _: User = Depends(require_permission("read"))) -> list[dict]:
    return raw_controller.status_counts(db)


@router.get("/{raw_id}")
def get_raw(raw_id: int, db: Session = Depends(get_db),
            _: User = Depends(require_permission("read"))) -> dict:
    return raw_controller.get_raw(db, raw_id)


@router.post("/{raw_id}/correct")
def correct_raw(raw_id: int, payload: RawCorrectIn, request: Request,
                db: Session = Depends(get_db),
                actor: User = Depends(require_permission("raw:correct"))) -> dict:
    return raw_controller.correct_raw(db, raw_id, payload.model_dump(exclude_none=True), actor, client_ip(request))
