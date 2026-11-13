"""分页工具：page/size -> offset/limit + 统一分页壳。"""
from __future__ import annotations

from typing import Any

from src.constants.limits import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


def normalize_pagination(page: int | None, size: int | None) -> tuple[int, int]:
    p = max(1, int(page or 1))
    s = min(MAX_PAGE_SIZE, max(1, int(size or DEFAULT_PAGE_SIZE)))
    return (p - 1) * s, s


def page_payload(items: list[Any], total: int, page: int, size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size else 0,
    }
