"""薪资基准 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkOut(BaseModel):
    id: int
    city: str
    function_type: str
    function_label: str = ""
    sample_count: int
    p25: int
    p50: int
    p75: int
    rule_version: str
    version: int
    published: bool
    generated_at: str | None = None


class BenchmarkGenerateIn(BaseModel):
    city: str = Field(min_length=1, max_length=24)
    function_type: str = Field(min_length=1, max_length=24)


class BenchmarkPublishOut(BaseModel):
    id: int
    published: bool


class BenchmarkReportOut(BenchmarkOut):
    distribution: list[dict] = []
    seniority_breakdown: list[dict] = []
