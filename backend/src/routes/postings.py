"""标准化岗位路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import posting_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.posting import PostingCorrectIn

router = APIRouter(prefix="/postings", tags=["postings"])


@router.get("")
def list_postings(city: str | None = None, function_type: str | None = None,
                  seniority: str | None = None, unit: str | None = None,
                  q: str | None = None, flagged: bool | None = None,
                  corrected: bool | None = None, page: int = 1, size: int = 20,
                  db: Session = Depends(get_db),
                  _: User = Depends(require_permission("read"))) -> dict:
    return posting_controller.list_postings(
        db, city, function_type, seniority, unit, q, flagged, corrected, page, size
    )


@router.get("/stats")
def stats(db: Session = Depends(get_db),
          _: User = Depends(require_permission("read"))) -> dict:
    return posting_controller.stats(db)


@router.get("/export.csv")
def export_csv(city: str | None = None, function_type: str | None = None,
               db: Session = Depends(get_db),
               _: User = Depends(require_permission("export"))):
    return posting_controller.export_csv(db, city, function_type)


@router.get("/{posting_id}")
def get_posting(posting_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_permission("read"))) -> dict:
    return posting_controller.get_posting(db, posting_id)


@router.patch("/{posting_id}/correct")
def correct_posting(posting_id: int, payload: PostingCorrectIn, request: Request,
                    db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("posting:correct"))) -> dict:
    return posting_controller.correct_posting(
        db, posting_id, payload.model_dump(exclude_none=True), actor, client_ip(request)
    )
