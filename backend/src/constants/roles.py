"""角色权限矩阵：后端唯一事实源，前端只按 permissions 渲染。"""
from __future__ import annotations

from src.constants.enums import ROLE_ADMIN, ROLE_ANALYST, ROLE_CLIENT

PERMISSIONS: dict[str, set[str]] = {
    ROLE_ADMIN: {
        "read",
        "posting:correct",
        "raw:correct",
        "rule:trial",
        "rule:reparse",
        "rule:activate",
        "benchmark:generate",
        "benchmark:publish",
        "quality:dispose",
        "source:sync",
        "audit:read",
        "export",
    },
    ROLE_ANALYST: {
        "read",
        "posting:correct",
        "raw:correct",
        "rule:trial",
        "rule:reparse",
        "benchmark:generate",
        "quality:dispose",
        "export",
    },
    ROLE_CLIENT: {"read", "export"},
}

ROLE_LABELS = {
    ROLE_ADMIN: "数据主管",
    ROLE_ANALYST: "标注分析",
    ROLE_CLIENT: "HR 客户（只读）",
}

ROLE_DESCRIPTIONS = {
    ROLE_ADMIN: "口径规则版本、发布基准报表、采集源与审计",
    ROLE_ANALYST: "修正标准化结果、重跑解析、处置质量队列，不能发布",
    ROLE_CLIENT: "只读基准报表并导出 CSV，修正/发布一律 403",
}


def role_can(role: str, action: str) -> bool:
    return action in PERMISSIONS.get(role, set())


def permissions_for(role: str) -> list[str]:
    return sorted(PERMISSIONS.get(role, set()))
