"""口径规则控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import rule_service


def list_rules(db: Session) -> list[dict]:
    return rule_service.list_rules(db)


def trial(db: Session, version: str) -> dict:
    return rule_service.trial(db, version)


def reparse(db: Session, version: str, actor: User, ip: str = "") -> dict:
    result = rule_service.reparse(db, version, actor, ip)
    db.commit()
    return result


def activate(db: Session, version: str, actor: User, ip: str = "") -> dict:
    result = rule_service.activate(db, version, actor, ip)
    db.commit()
    return result


def title_merge(db: Session) -> dict:
    return rule_service.title_merge_demo(db)
