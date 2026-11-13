"""质量门禁 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.posting import PostingOut


class QualityItemOut(BaseModel):
    posting: PostingOut
    primary_flag: str = ""
    flag_labels: list[str] = []


class QualityPage(BaseModel):
    items: list[QualityItemOut]
    total: int
    page: int
    size: int
    pages: int
    by_type: list[dict]


class DisposeIn(BaseModel):
    action: str = Field(pattern="^(disposed|ignored)$")
    note: str = Field(min_length=1, max_length=200)


class DisposeOut(BaseModel):
    posting_id: int
    quality_status: str
    note: str
