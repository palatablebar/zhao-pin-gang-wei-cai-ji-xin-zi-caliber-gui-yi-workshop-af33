"""标准化岗位 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PostingOut(BaseModel):
    id: int
    raw_id: int
    source_id: int
    source_name: str = ""
    canonical_title: str
    function_type: str
    function_label: str = ""
    seniority: str
    seniority_label: str = ""
    city: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_median: int | None = None
    salary_unit: str
    annual_months: int
    is_fulltime: bool
    confidence: float
    rule_version: str
    title_matches: list[str] = []
    quality_flags: list[str] = []
    quality_status: str
    is_corrected: bool
    parse_reason: str = ""
    raw_title: str = ""
    raw_salary: str = ""
    dedupe_key: str = ""
    ingest_batch_id: int | None = None
    source_names: list[str] = []


class PostingPage(BaseModel):
    items: list[PostingOut]
    total: int
    page: int
    size: int
    pages: int


class PostingStats(BaseModel):
    total: int
    flagged: int
    corrected: int
    merged: int = 0
    quarantined: int = 0
    by_city: list[dict]
    by_function: list[dict]
    by_seniority: list[dict]


class PostingCorrectIn(BaseModel):
    canonical_title: str | None = Field(default=None, max_length=120)
    function_type: str | None = None
    seniority: str | None = None
    city: str | None = Field(default=None, max_length=24)
    salary_min: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=10_000_000)
    note: str = Field(default="", max_length=200)
