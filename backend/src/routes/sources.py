"""采集源路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import source_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(db: Session = Depends(get_db),
                 _: User = Depends(require_permission("read"))) -> list[dict]:
    return source_controller.list_sources(db)


@router.post("/{source_id}/sync")
def sync_source(source_id: int, request: Request, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("source:sync"))) -> dict:
    return source_controller.sync_source(db, source_id, actor, client_ip(request))
