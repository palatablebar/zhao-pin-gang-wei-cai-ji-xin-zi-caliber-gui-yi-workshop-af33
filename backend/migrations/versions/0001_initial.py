"""initial schema (jobnorm)

Revision ID: 0001
Revises:
Create Date: 2026-11-10

迁移直接调用 SQLAlchemy metadata 建表，避免手写 DDL 与 models 漂移。
"""
from __future__ import annotations

from alembic import op

from src.config.database import Base
from src.models import *  # noqa: F401,F403

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
