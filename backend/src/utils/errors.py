"""业务异常：统一带 code / message / detail / http_status。"""
from __future__ import annotations

from src.constants import error_codes as codes


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        detail: str = "",
        http_status: int | None = None,
    ) -> None:
        self.code = code
        self.message = message or codes.ERROR_MESSAGES.get(code, code)
        self.detail = detail
        self.http_status = http_status or _default_status(code)
        super().__init__(self.message)

    def to_payload(self, trace_id: str | None = None) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "trace_id": trace_id,
        }


def _default_status(code: str) -> int:
    return {
        codes.AUTH_REQUIRED: 401,
        codes.AUTH_INVALID: 401,
        codes.AUTH_BAD_CREDENTIALS: 401,
        codes.FORBIDDEN: 403,
        codes.NOT_FOUND: 404,
        codes.CONFLICT: 409,
        codes.RATE_LIMITED: 429,
        codes.VALIDATION_ERROR: 422,
    }.get(code, 500)
