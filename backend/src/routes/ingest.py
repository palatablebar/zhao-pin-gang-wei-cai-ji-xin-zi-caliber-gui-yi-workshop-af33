"""采集入库路由：POST /ingest/batches（幂等批次）、台账查询、总览。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import ingest_controller
from src.middlewares.auth import client_ip
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.ingest import IngestBatchIn, IngestRecordOut

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/summary")
def summary(db: Session = Depends(get_db),
            _: User = Depends(require_permission("read"))) -> dict:
    return ingest_controller.summary(db)


@router.get("/demo-batch")
def demo_batch(db: Session = Depends(get_db),
               _: User = Depends(require_permission("read"))) -> dict:
    return ingest_controller.demo(db)


@router.get("/batches")
def list_batches(db: Session = Depends(get_db),
                 _: User = Depends(require_permission("read"))) -> list[dict]:
    return ingest_controller.list_batches(db)


@router.post("/batches")
def run_batch(payload: IngestBatchIn, request: Request, db: Session = Depends(get_db),
              actor: User = Depends(require_permission("ingest:run"))) -> dict:
    return ingest_controller.run_batch(db, payload.model_dump(), actor, client_ip(request))


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_db),
              _: User = Depends(require_permission("read"))) -> dict:
    return ingest_controller.get_batch(db, batch_id)


@router.get("/batches/{batch_id}/records")
def list_records(batch_id: int, action: str | None = None, conflict_only: bool = False,
                 db: Session = Depends(get_db),
                 _: User = Depends(require_permission("read"))) -> list[IngestRecordOut]:
    return ingest_controller.list_records(db, batch_id, action, conflict_only)
