"""原始岗位：采集落库原文 + 解析状态机。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class RawPosting(Base):
    __tablename__ = "raw_postings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title_raw: Mapped[str] = mapped_column(String(200), nullable=False)
    salary_raw: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    city_raw: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    experience_raw: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    employment_type_raw: Mapped[str] = mapped_column(String(40), default="全职", nullable=False)
    company: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="parsed", nullable=False, index=True)
    parse_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rule_version: Mapped[str] = mapped_column(String(16), default="v1", nullable=False)
    # 采集入库：同一公司+城市+职位的自然键（dedupe_key）与最近一次覆盖它的批次
    dedupe_key: Mapped[str] = mapped_column(String(200), default="", nullable=False, index=True)
    ingest_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    superseded_by_raw_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = ()
