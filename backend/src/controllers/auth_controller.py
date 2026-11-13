"""认证控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.auth import serialize_user
from src.services import audit_service, auth_service


def login(db: Session, email: str, password: str, ip: str = "") -> dict:
    user = auth_service.authenticate(db, email, password)
    token = auth_service.issue_token(user)
    audit_service.record(db, user, "auth.login", "user", user.id, f"role={user.role}", ip)
    db.commit()
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}


def me(user: User) -> dict:
    return serialize_user(user)


def list_users(db: Session) -> list[dict]:
    users = db.query(User).order_by(User.id).all()
    return [serialize_user(user) for user in users]
