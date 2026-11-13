"""认证服务：邮箱密码校验 + JWT 签发。"""
from __future__ import annotations

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.models.user import User
from src.utils.errors import AppError
from src.utils.jwt import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:  # noqa: BLE001
        return False


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(codes.AUTH_BAD_CREDENTIALS, "邮箱或密码不正确", f"email={email}")
    if not user.is_active:
        raise AppError(codes.FORBIDDEN, "账号已停用", f"email={email}")
    return user


def issue_token(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role)
