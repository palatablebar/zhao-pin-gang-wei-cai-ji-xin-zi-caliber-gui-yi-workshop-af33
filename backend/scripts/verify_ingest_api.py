"""API 冒烟测试：SQLite 内存库 + FastAPI TestClient，走真实路由与鉴权。

覆盖：
- POST /api/ingest/batches（admin 可提交，analyst/client 403）
- 采集总览 / 批次台账 / 合并前后来源
- 原始队列 quarantined 筛选、标准化表不重复
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SEED_DEMO", "false")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.database import Base, get_db
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.models.user import User

engine = create_engine(
    "sqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def bootstrap():
    db = Session()
    db.add_all(
        [
            Source(name="拉勾招聘", site_type="recruit_site"),
            Source(name="BOSS直聘", site_type="recruit_site"),
            Source(name="猎聘", site_type="recruit_site"),
            User(email="admin@jobnorm.io", name="陈知远", role="admin", password_hash="x"),
            User(email="analyst@jobnorm.io", name="林小满", role="analyst", password_hash="x"),
            User(email="client@jobnorm.io", name="周雨桐", role="client", password_hash="x"),
        ]
    )
    db.commit()
    db.close()


def main():
    from src.utils.jwt import create_access_token
    from src.main import app

    app.dependency_overrides[get_db] = override_get_db
    bootstrap()
    client = TestClient(app)

    def token(email: str) -> dict:
        db = Session()
        user = db.query(User).filter(User.email == email).one()
        db.close()
        return {"Authorization": f"Bearer {create_access_token(str(user.id), user.role)}"}

    admin = token("admin@jobnorm.io")
    analyst = token("analyst@jobnorm.io")
    reader = token("client@jobnorm.io")

    payload = {
        "batch_key": "API-1",
        "name": "五渠道日报 11-13",
        "items": [
            {"source_name": "BOSS直聘", "external_id": "A-2", "title": "高级Java工程师",
             "salary_raw": "20-30K", "city": "杭州", "company": "杭州云栖网络科技有限公司",
             "published_at": "2026-11-12T09:00:00"},
            {"source_name": "拉勾招聘", "external_id": "A-1", "title": "高级Java工程师",
             "salary_raw": "22-32K", "city": "杭州", "company": "杭州云栖网络科技有限公司",
             "published_at": "2026-11-13T09:00:00"},
            {"source_name": "猎聘", "external_id": "A-3", "title": "产品经理",
             "salary_raw": "面议", "city": "北京", "company": "北京星河数据",
             "published_at": "2026-11-13T09:00:00"},
            {"source_name": "猎聘", "external_id": "", "title": "数据分析师",
             "salary_raw": "15-25K", "city": "北京", "company": "北京明湖智能"},
        ],
    }

    denied_client = client.post("/api/ingest/batches", json=payload, headers=reader)
    assert denied_client.status_code == 403, denied_client.text
    assert "ingest:run" in client.get("/api/auth/me", headers=analyst).json()["permissions"]

    result = client.post("/api/ingest/batches", json=payload, headers=admin)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["new_count"] == 1, body
    assert body["merged_count"] == 1, body
    assert body["failed_count"] == 2, body
    merged = [record for record in body["records"] if record["action"] == "merged"][0]
    assert merged["before_source_name"] == "BOSS直聘", merged
    assert merged["after_source_name"] == "拉勾招聘", merged
    assert (merged["before_salary_min"], merged["before_salary_max"]) == (20000, 30000)
    assert (merged["incoming_salary_min"], merged["incoming_salary_max"]) == (22000, 32000)
    assert merged["conflict_kind"] == ""

    replay = client.post("/api/ingest/batches", json=payload, headers=admin)
    assert replay.json()["duplicate_batch"] is True
    assert replay.json()["new_count"] == 1

    summary = client.get("/api/ingest/summary", headers=reader).json()
    assert summary["new"] == 1 and summary["merged"] == 1 and summary["failed"] == 2, summary
    assert summary["quarantined_raws"] == 2

    batches = client.get("/api/ingest/batches", headers=reader).json()
    assert len(batches) == 1 and batches[0]["batch_key"] == "API-1"

    detail = client.get(f"/api/ingest/batches/{body['id']}", headers=reader).json()
    assert detail["source_breakdown"], detail
    for row in detail["source_breakdown"]:
        assert row["total"] == row["new"] + row["merged"] + row["ignored"] + row["failed"]

    raw_page = client.get("/api/raw?status=quarantined", headers=reader).json()
    assert raw_page["total"] == 2, raw_page
    assert all(item["status"] == "quarantined" for item in raw_page["items"])

    postings = client.get("/api/postings", headers=reader).json()
    assert postings["total"] == 1, "同一自然键只允许一条标准化岗位"

    db = Session()
    assert db.query(func.count(Posting.id)).scalar() == 1
    assert db.query(func.count(RawPosting.id)).scalar() == 4, "隔离记录仍入湖"
    posting = db.query(Posting).one()
    assert (posting.salary_min, posting.salary_max) == (22000, 32000), "最新版本薪酬"
    db.close()

    print("API SMOKE PASS")


if __name__ == "__main__":
    main()
