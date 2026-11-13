"""分位计算：numpy 线性插值（linear），输入为月薪中位数列表。"""
from __future__ import annotations

import numpy as np

from src.constants.enums import FUNCTION_LABELS, SENIORITY_LABELS


def percentiles(values: list[int], qs: tuple[float, ...] = (25, 50, 75)) -> dict[float, int] | None:
    if not values:
        return None
    arr = np.asarray(sorted(values), dtype=float)
    return {q: int(round(float(np.percentile(arr, q, method="linear")))) for q in qs}


def distribution(values: list[int], buckets: int = 8) -> list[dict]:
    if not values:
        return []
    arr = np.asarray(values, dtype=float)
    lo, hi = float(arr.min()), float(arr.max())
    if lo == hi:
        return [{"low": int(lo), "high": int(hi), "count": int(arr.size)}]
    edges = np.linspace(lo, hi, buckets + 1)
    out = []
    for i in range(buckets):
        low, high = edges[i], edges[i + 1]
        count = int(((arr >= low) & (arr < high)).sum()) if i < buckets - 1 else int((arr >= low).sum())
        out.append({"low": int(round(low)), "high": int(round(high)), "count": count})
    return out


def median_of(values: list[int]) -> int | None:
    if not values:
        return None
    arr = np.asarray(sorted(values), dtype=float)
    return int(round(float(np.percentile(arr, 50, method="linear"))))


def label_function(code: str) -> str:
    return FUNCTION_LABELS.get(code, code)


def label_seniority(code: str) -> str:
    return SENIORITY_LABELS.get(code, code)
