"""口径规则路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import rule_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
def list_rules(db: Session = Depends(get_db),
               _: User = Depends(require_permission("read"))) -> list[dict]:
    return rule_controller.list_rules(db)


@router.get("/title-merge")
def title_merge(db: Session = Depends(get_db),
                _: User = Depends(require_permission("rule:trial"))) -> dict:
    return rule_controller.title_merge(db)


@router.get("/{version}/trial")
def trial(version: str, db: Session = Depends(get_db),
          _: User = Depends(require_permission("rule:trial"))) -> dict:
    return rule_controller.trial(db, version)


@router.post("/{version}/reparse")
def reparse(version: str, request: Request, db: Session = Depends(get_db),
            actor: User = Depends(require_permission("rule:reparse"))) -> dict:
    return rule_controller.reparse(db, version, actor, client_ip(request))


@router.post("/{version}/activate")
def activate(version: str, request: Request, db: Session = Depends(get_db),
             actor: User = Depends(require_permission("rule:activate"))) -> dict:
    return rule_controller.activate(db, version, actor, client_ip(request))
