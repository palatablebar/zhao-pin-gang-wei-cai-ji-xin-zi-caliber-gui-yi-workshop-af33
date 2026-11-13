"""城市归一：把「杭州市·西湖区」等原文映射到 24 个标准城市名。"""
from __future__ import annotations

import re

KNOWN_CITIES = ["杭州", "上海", "北京", "深圳", "广州", "成都", "武汉", "南京", "苏州", "西安"]


def normalize_city(raw: str) -> str:
    text = (raw or "").strip()
    for city in KNOWN_CITIES:
        if city in text:
            return city
    cleaned = re.sub(r"[市省].*$", "", text).strip()
    return cleaned[:12] or "未知"
