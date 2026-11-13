"""认证与用户 schema。"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from src.constants.roles import ROLE_DESCRIPTIONS, ROLE_LABELS, permissions_for


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    role_label: str = ""
    role_description: str = ""
    permissions: list[str] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def serialize_user(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "role_description": ROLE_DESCRIPTIONS.get(user.role, ""),
        "permissions": permissions_for(user.role),
    }
