"""基准报表控制器。"""
from __future__ import annotations

from fastapi import Response
from sqlalchemy.orm import Session

from src.models.user import User
from src.services import benchmark_service


def list_benchmarks(db: Session) -> list[dict]:
    return benchmark_service.list_benchmarks(db)


def report(db: Session, benchmark_id: int) -> dict:
    return benchmark_service.report(db, benchmark_id)


def generate(db: Session, city: str, function_type: str, actor: User, ip: str = "") -> dict:
    result = benchmark_service.generate(db, city, function_type, actor, ip)
    db.commit()
    return result


def publish(db: Session, benchmark_id: int, actor: User, ip: str = "") -> dict:
    result = benchmark_service.publish(db, benchmark_id, actor, ip)
    db.commit()
    return result


def export_csv(db: Session, benchmark_id: int) -> Response:
    content = benchmark_service.export_csv(db, benchmark_id)
    return Response(
        content="\ufeff" + content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="jobnorm-benchmark.csv"'},
    )
