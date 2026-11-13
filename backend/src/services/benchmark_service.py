"""薪资基准服务：生成（numpy 线性插值分位）、发布、导出 CSV。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import FUNCTION_LABELS, SENIORITY_LABELS
from src.models.benchmark import Benchmark
from src.models.posting import Posting
from src.services import audit_service
from src.services.percentile import distribution, percentiles
from src.utils.errors import AppError


def serialize(benchmark: Benchmark) -> dict:
    return {
        "id": benchmark.id,
        "city": benchmark.city,
        "function_type": benchmark.function_type,
        "function_label": FUNCTION_LABELS.get(benchmark.function_type, benchmark.function_type),
        "sample_count": benchmark.sample_count,
        "p25": benchmark.p25,
        "p50": benchmark.p50,
        "p75": benchmark.p75,
        "rule_version": benchmark.rule_version,
        "version": benchmark.version,
        "published": benchmark.published,
        "generated_at": benchmark.generated_at.isoformat() if benchmark.generated_at else None,
    }


def list_benchmarks(db: Session) -> list[dict]:
    rows = db.query(Benchmark).order_by(Benchmark.city, Benchmark.function_type).all()
    return [serialize(row) for row in rows]


def generate(db: Session, city: str, function_type: str, actor, ip: str) -> dict:
    values = _sample_values(db, city, function_type)
    if not values:
        raise AppError(codes.CONFLICT, "样本不足，无法生成基准", f"{city}/{function_type}")
    pct = percentiles(values)
    if pct is None:
        raise AppError(codes.CONFLICT, "样本不足，无法生成基准", f"{city}/{function_type}")
    from src.services.rule_service import active_version

    rule_version = active_version(db)
    benchmark = (
        db.query(Benchmark)
        .filter(Benchmark.city == city, Benchmark.function_type == function_type)
        .first()
    )
    if benchmark is None:
        benchmark = Benchmark(city=city, function_type=function_type)
        db.add(benchmark)
    benchmark.sample_count = len(values)
    benchmark.p25 = pct[25]
    benchmark.p50 = pct[50]
    benchmark.p75 = pct[75]
    benchmark.rule_version = rule_version
    benchmark.version = (benchmark.version or 1) + 1 if benchmark.id else 1
    benchmark.generated_at = datetime.utcnow()
    db.flush()
    audit_service.record(
        db, actor, "benchmark.generate", "benchmark", benchmark.id,
        f"{city}/{function_type} n={len(values)} p25={pct[25]} p50={pct[50]} p75={pct[75]}", ip,
    )
    return serialize(benchmark)


def _sample_values(db: Session, city: str, function_type: str) -> list[int]:
    rows = (
        db.query(Posting.salary_median)
        .filter(Posting.city == city, Posting.function_type == function_type)
        .filter(Posting.salary_median.isnot(None))
        .filter(func.json_length(Posting.quality_flags) == 0)
        .all()
    )
    return sorted(int(row[0]) for row in rows if row[0] is not None)


def report(db: Session, benchmark_id: int) -> dict:
    benchmark = db.get(Benchmark, benchmark_id)
    if benchmark is None:
        raise AppError(codes.NOT_FOUND, "基准不存在", f"benchmark_id={benchmark_id}")
    data = serialize(benchmark)
    values = _sample_values(db, benchmark.city, benchmark.function_type)
    data["distribution"] = distribution(values)
    rows = (
        db.query(Posting.seniority, Posting.salary_median)
        .filter(Posting.city == benchmark.city, Posting.function_type == benchmark.function_type)
        .filter(Posting.salary_median.isnot(None))
        .filter(func.json_length(Posting.quality_flags) == 0)
        .all()
    )
    buckets: dict[str, list[int]] = {}
    for seniority, median in rows:
        buckets.setdefault(seniority, []).append(int(median))
    data["seniority_breakdown"] = [
        {
            "seniority": seniority,
            "label": SENIORITY_LABELS.get(seniority, seniority),
            "sample_count": len(values_),
            "p50": percentiles(values_)[50] if values_ else 0,
        }
        for seniority, values_ in sorted(buckets.items())
    ]
    return data


def publish(db: Session, benchmark_id: int, actor, ip: str) -> dict:
    benchmark = db.get(Benchmark, benchmark_id)
    if benchmark is None:
        raise AppError(codes.NOT_FOUND, "基准不存在", f"benchmark_id={benchmark_id}")
    benchmark.published = True
    audit_service.record(
        db, actor, "benchmark.publish", "benchmark", benchmark.id,
        f"{benchmark.city}/{benchmark.function_type} v{benchmark.version}", ip,
    )
    db.flush()
    return {"id": benchmark.id, "published": benchmark.published}


def export_csv(db: Session, benchmark_id: int) -> str:
    data = report(db, benchmark_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "city", "function_type", "sample_count", "p25", "p50", "p75",
        "rule_version", "version", "published", "generated_at",
    ])
    writer.writerow([
        data["city"], data["function_type"], data["sample_count"],
        data["p25"], data["p50"], data["p75"], data["rule_version"],
        data["version"], data["published"], data["generated_at"],
    ])
    writer.writerow([])
    writer.writerow(["seniority", "sample_count", "p50"])
    for row in data["seniority_breakdown"]:
        writer.writerow([row["seniority"], row["sample_count"], row["p50"]])
    return buffer.getvalue()
