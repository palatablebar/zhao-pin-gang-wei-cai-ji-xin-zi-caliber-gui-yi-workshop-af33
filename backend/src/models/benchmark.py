"""薪资基准：城市 × 职能 的 P25/P50/P75。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    function_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    p25: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    p50: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    p75: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(16), default="v1", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = ()
