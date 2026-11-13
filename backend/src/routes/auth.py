"""认证路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import auth_controller
from src.middlewares.auth import client_ip, get_current_user
from src.middlewares.rbac import require_role
from src.models.user import User
from src.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    return auth_controller.login(db, payload.email, payload.password, client_ip(request))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return auth_controller.me(user)


@router.get("/users")
def list_users(db: Session = Depends(get_db),
               _: User = Depends(require_role("admin"))) -> list[dict]:
    return auth_controller.list_users(db)
