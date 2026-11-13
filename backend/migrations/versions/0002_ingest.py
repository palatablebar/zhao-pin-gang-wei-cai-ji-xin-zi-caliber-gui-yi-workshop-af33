"""ingest: batches / records + 原始与标准化岗位去重列

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-13

- 新增 ingest_batches / ingest_records 两张台账表（批次幂等、逐条动作与冲突说明）。
- raw_postings：dedupe_key / ingest_batch_id / superseded_by_raw_id / superseded_at。
- postings：dedupe_key（唯一）/ ingest_batch_id，保证同一公司+城市+职位只有一条标准化岗位。

0001 用 metadata.create_all 建表，新库执行 0001 时已经带上新表/新列，
因此本迁移对已存在的表/列做存在性判断，重复执行安全。历史 postings 的 dedupe_key
保持 NULL（历史数据本身可能违反自然键唯一），由后续采集入库按唯一候选回填。
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    inspector = inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table)}


def upgrade() -> None:
    existing = _tables()
    if "ingest_batches" not in existing:
        op.execute(
            """
            CREATE TABLE ingest_batches (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                batch_key VARCHAR(120) NOT NULL,
                name VARCHAR(160) NOT NULL DEFAULT '',
                status VARCHAR(16) NOT NULL DEFAULT 'running',
                total_count INT NOT NULL DEFAULT 0,
                new_count INT NOT NULL DEFAULT 0,
                merged_count INT NOT NULL DEFAULT 0,
                ignored_count INT NOT NULL DEFAULT 0,
                failed_count INT NOT NULL DEFAULT 0,
                source_count INT NOT NULL DEFAULT 0,
                created_by VARCHAR(160) NOT NULL DEFAULT '',
                note TEXT NOT NULL,
                started_at DATETIME NOT NULL,
                finished_at DATETIME NULL,
                created_at DATETIME NOT NULL,
                UNIQUE KEY uq_ingest_batches_batch_key (batch_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
    if "ingest_records" not in existing:
        op.execute(
            """
            CREATE TABLE ingest_records (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                batch_id INT NOT NULL,
                line_no INT NOT NULL DEFAULT 0,
                source_id INT NULL,
                source_name VARCHAR(80) NOT NULL DEFAULT '',
                external_id VARCHAR(80) NOT NULL DEFAULT '',
                raw_id INT NULL,
                posting_id INT NULL,
                action VARCHAR(16) NOT NULL DEFAULT 'failed',
                reason VARCHAR(64) NOT NULL DEFAULT '',
                note TEXT NOT NULL,
                conflict_kind VARCHAR(32) NOT NULL DEFAULT '',
                company VARCHAR(120) NOT NULL DEFAULT '',
                city VARCHAR(24) NOT NULL DEFAULT '',
                canonical_title VARCHAR(120) NOT NULL DEFAULT '',
                salary_raw VARCHAR(120) NOT NULL DEFAULT '',
                salary_median INT NULL,
                published_at DATETIME NULL,
                before_source_id INT NULL,
                before_source_name VARCHAR(80) NOT NULL DEFAULT '',
                after_source_id INT NULL,
                after_source_name VARCHAR(80) NOT NULL DEFAULT '',
                before_salary_min INT NULL,
                before_salary_max INT NULL,
                incoming_salary_min INT NULL,
                incoming_salary_max INT NULL,
                created_at DATETIME NOT NULL,
                KEY ix_ingest_records_batch_id (batch_id),
                KEY ix_ingest_records_action (action),
                KEY ix_ingest_records_conflict_kind (conflict_kind),
                KEY ix_ingest_records_source_id (source_id),
                KEY ix_ingest_records_raw_id (raw_id),
                KEY ix_ingest_records_posting_id (posting_id),
                CONSTRAINT fk_ingest_records_batch FOREIGN KEY (batch_id) REFERENCES ingest_batches (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    raw_columns = _columns("raw_postings")
    if "dedupe_key" not in raw_columns:
        op.execute("ALTER TABLE raw_postings ADD COLUMN dedupe_key VARCHAR(200) NOT NULL DEFAULT ''")
    if "ingest_batch_id" not in raw_columns:
        op.execute("ALTER TABLE raw_postings ADD COLUMN ingest_batch_id INT NULL")
    if "superseded_by_raw_id" not in raw_columns:
        op.execute("ALTER TABLE raw_postings ADD COLUMN superseded_by_raw_id INT NULL")
    if "superseded_at" not in raw_columns:
        op.execute("ALTER TABLE raw_postings ADD COLUMN superseded_at DATETIME NULL")
    raw_indexes = _indexes("raw_postings")
    if "ix_raw_postings_dedupe_key" not in raw_indexes:
        op.execute("CREATE INDEX ix_raw_postings_dedupe_key ON raw_postings (dedupe_key)")
    if "ix_raw_postings_ingest_batch_id" not in raw_indexes:
        op.execute("CREATE INDEX ix_raw_postings_ingest_batch_id ON raw_postings (ingest_batch_id)")

    posting_columns = _columns("postings")
    if "dedupe_key" not in posting_columns:
        op.execute("ALTER TABLE postings ADD COLUMN dedupe_key VARCHAR(200) NULL")
    if "ingest_batch_id" not in posting_columns:
        op.execute("ALTER TABLE postings ADD COLUMN ingest_batch_id INT NULL")
    posting_indexes = _indexes("postings")
    if "ix_postings_dedupe_key" not in posting_indexes:
        op.execute("CREATE UNIQUE INDEX ix_postings_dedupe_key ON postings (dedupe_key)")
    if "ix_postings_ingest_batch_id" not in posting_indexes:
        op.execute("CREATE INDEX ix_postings_ingest_batch_id ON postings (ingest_batch_id)")


def downgrade() -> None:
    posting_columns = _columns("postings")
    if "ingest_batch_id" in posting_columns:
        op.execute("DROP INDEX ix_postings_ingest_batch_id ON postings")
        op.execute("ALTER TABLE postings DROP COLUMN ingest_batch_id")
    if "dedupe_key" in posting_columns:
        op.execute("DROP INDEX ix_postings_dedupe_key ON postings")
        op.execute("ALTER TABLE postings DROP COLUMN dedupe_key")
    raw_columns = _columns("raw_postings")
    if "superseded_at" in raw_columns:
        op.execute("ALTER TABLE raw_postings DROP COLUMN superseded_at")
    if "superseded_by_raw_id" in raw_columns:
        op.execute("ALTER TABLE raw_postings DROP COLUMN superseded_by_raw_id")
    if "ingest_batch_id" in raw_columns:
        op.execute("DROP INDEX ix_raw_postings_ingest_batch_id ON raw_postings")
        op.execute("ALTER TABLE raw_postings DROP COLUMN ingest_batch_id")
    if "dedupe_key" in raw_columns:
        op.execute("DROP INDEX ix_raw_postings_dedupe_key ON raw_postings")
        op.execute("ALTER TABLE raw_postings DROP COLUMN dedupe_key")
    existing = _tables()
    if "ingest_records" in existing:
        op.execute("DROP TABLE ingest_records")
    if "ingest_batches" in existing:
        op.execute("DROP TABLE ingest_batches")
