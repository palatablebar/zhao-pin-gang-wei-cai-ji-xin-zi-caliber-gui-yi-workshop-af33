"""基准报表路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import benchmark_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.benchmark import BenchmarkGenerateIn

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("")
def list_benchmarks(db: Session = Depends(get_db),
                    _: User = Depends(require_permission("read"))) -> list[dict]:
    return benchmark_controller.list_benchmarks(db)


@router.post("/generate")
def generate(payload: BenchmarkGenerateIn, request: Request, db: Session = Depends(get_db),
             actor: User = Depends(require_permission("benchmark:generate"))) -> dict:
    return benchmark_controller.generate(
        db, payload.city, payload.function_type, actor, client_ip(request)
    )


@router.get("/{benchmark_id}")
def report(benchmark_id: int, db: Session = Depends(get_db),
           _: User = Depends(require_permission("read"))) -> dict:
    return benchmark_controller.report(db, benchmark_id)


@router.post("/{benchmark_id}/publish")
def publish(benchmark_id: int, request: Request, db: Session = Depends(get_db),
            actor: User = Depends(require_permission("benchmark:publish"))) -> dict:
    return benchmark_controller.publish(db, benchmark_id, actor, client_ip(request))


@router.get("/{benchmark_id}/export.csv")
def export_csv(benchmark_id: int, db: Session = Depends(get_db),
               _: User = Depends(require_permission("export"))):
    return benchmark_controller.export_csv(db, benchmark_id)
