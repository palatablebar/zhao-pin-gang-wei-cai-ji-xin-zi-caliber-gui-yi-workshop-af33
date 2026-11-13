"""口径规则 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class RuleOut(BaseModel):
    id: int
    code: str
    rule_set: str
    version: str
    rule_type: str
    name: str
    pattern: str
    action: str
    description: str
    hit_count: int
    enabled: bool
    is_active_set: bool


class TrialOut(BaseModel):
    version: str
    attempts: int
    hits: int
    misses: int
    hit_rate: float
    hit_rate_pct: int
    reason_breakdown: dict
    rule_hits: dict
    samples: list[dict] = []


class ReparseOut(BaseModel):
    previous_version: str
    active_version: str
    before: dict
    after: dict
    updated_raws: int
    updated_postings: int
    skipped_corrected: int
    duration_ms: int


class ActivateOut(BaseModel):
    version: str
    active: bool
    rules: int
