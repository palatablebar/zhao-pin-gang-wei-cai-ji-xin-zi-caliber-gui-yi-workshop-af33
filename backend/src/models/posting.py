"""标准化岗位：薪资口径归一后的结果 + 质量标记 + 人工修正位。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class Posting(Base):
    __tablename__ = "postings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("raw_postings.id"), unique=True, nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    canonical_title: Mapped[str] = mapped_column(String(120), nullable=False)
    function_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    seniority: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_median: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_unit: Mapped[str] = mapped_column(String(16), default="monthly", nullable=False)
    annual_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    is_fulltime: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(16), default="v1", nullable=False)
    title_matches: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(16), default="open", nullable=False, index=True)
    disposition_note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    disposed_by: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    corrected_by: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parse_reason: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
