"""JWT 签发与校验（HS256）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from src.config.settings import settings
from src.constants import error_codes as codes
from src.utils.errors import AppError


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.app_name,
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(codes.AUTH_INVALID, "登录已过期，请重新登录", "token expired") from exc
    except jwt.PyJWTError as exc:
        raise AppError(codes.AUTH_INVALID, "登录状态无效，请重新登录", str(exc)) from exc
