"""限流中间件：滑动窗口（60s）按客户端 IP 计数，超限 429。"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.constants import error_codes as codes


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int | None = None, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit or settings.rate_limit_per_minute
        self.window = window_seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path.endswith("/health"):
            return await call_next(request)
        ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        now = time.time()
        bucket = self.hits[ip]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "code": codes.RATE_LIMITED,
                    "message": f"请求过于频繁（>{self.limit}/min），请稍后再试",
                    "detail": f"ip={ip}",
                },
            )
        bucket.append(now)
        return await call_next(request)
