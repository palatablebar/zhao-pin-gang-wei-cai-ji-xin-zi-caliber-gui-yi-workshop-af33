"""采集入库 schema：批次提交、台账查询。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class IngestItemIn(BaseModel):
    source_id: int | None = None
    source_name: str | None = None
    external_id: str = Field(default="", max_length=80)
    title: str = Field(default="", max_length=200)
    salary_raw: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=80)
    company: str = Field(default="", max_length=120)
    experience_raw: str = Field(default="", max_length=80)
    employment_type_raw: str = Field(default="全职", max_length=40)
    published_at: str | None = None
    raw_json: dict | None = None


class IngestBatchIn(BaseModel):
    batch_key: str = Field(default="", max_length=120)
    name: str = Field(default="", max_length=160)
    note: str = Field(default="", max_length=2000)
    items: list[IngestItemIn] = Field(default_factory=list)


class IngestRecordOut(BaseModel):
    id: int
    batch_id: int
    line_no: int
    source_id: int | None = None
    source_name: str = ""
    external_id: str = ""
    raw_id: int | None = None
    posting_id: int | None = None
    action: str
    action_label: str = ""
    reason: str = ""
    note: str = ""
    conflict_kind: str = ""
    conflict_label: str = ""
    company: str = ""
    city: str = ""
    canonical_title: str = ""
    salary_raw: str = ""
    salary_median: int | None = None
    published_at: str | None = None
    before_source_id: int | None = None
    before_source_name: str = ""
    after_source_id: int | None = None
    after_source_name: str = ""
    before_salary_min: int | None = None
    before_salary_max: int | None = None
    incoming_salary_min: int | None = None
    incoming_salary_max: int | None = None
    created_at: str | None = None


class SourceBreakdownOut(BaseModel):
    source_name: str
    total: int = 0
    new: int = 0
    merged: int = 0
    ignored: int = 0
    failed: int = 0
