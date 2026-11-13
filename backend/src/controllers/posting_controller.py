"""标准化岗位控制器。"""
from __future__ import annotations

from fastapi import Response
from sqlalchemy.orm import Session

from src.models.user import User
from src.services import posting_service


def list_postings(db: Session, city, function_type, seniority, unit, q,
                  flagged, corrected, page, size) -> dict:
    return posting_service.list_postings(
        db, city, function_type, seniority, unit, q, flagged, corrected, page, size
    )


def stats(db: Session) -> dict:
    return posting_service.stats(db)


def get_posting(db: Session, posting_id: int) -> dict:
    return posting_service.get_posting(db, posting_id)


def correct_posting(db: Session, posting_id: int, payload: dict, actor: User, ip: str = "") -> dict:
    result = posting_service.correct_posting(db, posting_id, payload, actor, ip)
    db.commit()
    return result


def export_csv(db: Session, city: str | None, function_type: str | None) -> Response:
    content = posting_service.export_csv(db, city, function_type)
    return Response(
        content="\ufeff" + content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="jobnorm-postings.csv"'},
    )
