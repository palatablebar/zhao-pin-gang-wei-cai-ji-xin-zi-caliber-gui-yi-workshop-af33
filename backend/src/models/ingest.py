"""采集入库批次、逐条处理台账与冲突说明。

- IngestBatch：一次采集批（batch_key 唯一，重复提交同一批直接返回旧结果）。
- IngestRecord：批次内每条原始记录的处理结果（新增/合并/忽略/失败），
  同时承载「合并前后来源」「新旧薪酬」「迟到旧版本冲突」等说明。
- 原始岗位与标准化岗位通过 ingest_batch_id / dedupe_key 关联，便于回溯。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class IngestBatch(Base):
    __tablename__ = "ingest_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    merged_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ignored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class IngestRecord(Base):
    __tablename__ = "ingest_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batches.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    external_id: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    raw_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    posting_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(16), default="failed", nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    conflict_kind: Mapped[str] = mapped_column(String(32), default="", nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(24), default="", nullable=False)
    canonical_title: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    salary_raw: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    salary_median: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    before_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_source_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    after_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_source_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    before_salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incoming_salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incoming_salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
