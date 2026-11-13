"""原始岗位队列 schema（含 raw ↔ 归一 对照）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ParsePreview(BaseModel):
    version: str
    status: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_median: int | None = None
    annual_months: int = 12
    unit_kind: str = "monthly"
    confidence: float = 0.0
    reason_code: str = ""
    flags: list[str] = []
    matched_rules: list[str] = []
    canonical_title: str = ""
    function_type: str = ""
    seniority: str = ""
    title_confidence: float = 0.0
    matched_terms: list[str] = []
    city: str = ""


class RawOut(BaseModel):
    id: int
    source_id: int
    source_name: str = ""
    external_id: str
    title_raw: str
    salary_raw: str
    city_raw: str
    experience_raw: str
    employment_type_raw: str
    company: str
    status: str
    status_label: str = ""
    parse_reason: str = ""
    rule_version: str
    published_at: str | None = None
    posting_id: int | None = None


class RawDetailOut(RawOut):
    raw_json: dict = {}
    current: ParsePreview | None = None
    compare_versions: list[ParsePreview] = []


class RawCorrectIn(BaseModel):
    salary_raw: str | None = None
    city_raw: str | None = None
    title_raw: str | None = None
    salary_min: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=10_000_000)
