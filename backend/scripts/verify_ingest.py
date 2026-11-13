"""采集入库验收脚本（SQLite 内存库，真实 service 调用，不依赖 MySQL/Docker）。

覆盖需求：
1. 同公司+城市+职位：新版本覆盖旧版本薪酬；迟到旧版本留下冲突说明且不覆盖。
2. 异常记录（面议/无法解析/缺字段/兼职/批内重复 external_id）隔离，不进标准化表。
3. 重复运行同一批：不新增岗位、不改写已人工修正的数据。
4. 合并前后来源写入台账（before/after source）。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SEED_DEMO", "false")

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from src.config.database import Base
from src.models.ingest import IngestBatch, IngestRecord
from src.models.posting import Posting
from src.models.raw_posting import RawPosting
from src.models.source import Source
from src.models.user import User
from src.services import ingest_service

engine = create_engine("sqlite:///:memory:", future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)


def seed_base(db):
    db.add_all(
        [
            Source(name="拉勾招聘", site_type="recruit_site"),
            Source(name="BOSS直聘", site_type="recruit_site"),
            Source(name="猎聘", site_type="recruit_site"),
        ]
    )
    db.add(User(email="admin@jobnorm.io", name="陈知远", role="admin", password_hash="x"))
    db.commit()
    return db.query(User).filter(User.email == "admin@jobnorm.io").first()


def item(source, external_id, salary, published, **kwargs):
    base = {
        "source_id": source.id,
        "external_id": external_id,
        "title": "高级Java工程师",
        "salary_raw": salary,
        "city": "杭州市·西湖区",
        "company": "杭州云栖网络科技有限公司",
        "experience_raw": "3-5年",
        "employment_type_raw": "全职",
        "published_at": published,
    }
    base.update(kwargs)
    return base


def counts(db):
    return {
        "raws": db.query(func.count(RawPosting.id)).scalar(),
        "postings": db.query(func.count(Posting.id)).scalar(),
        "batches": db.query(func.count(IngestBatch.id)).scalar(),
        "records": db.query(func.count(IngestRecord.id)).scalar(),
    }


def test_late_old_version_and_newer_overwrite(db, actor):
    lagou = db.query(Source).filter(Source.name == "拉勾招聘").first()
    boss = db.query(Source).filter(Source.name == "BOSS直聘").first()

    # v1（拉勾，11-10）：20-30K；v2（BOSS，11-12）：22-32K 新版本应覆盖；
    # v0（猎聘，11-08）迟到旧版本 18-28K 不得覆盖。
    result = ingest_service.run_batch(
        db,
        {
            "batch_key": "T1",
            "items": [
                item(lagou, "L-1", "20-30K", "2026-11-10T09:00:00"),
                item(boss, "B-1", "22-32K", "2026-11-12T09:00:00"),
            ],
        },
        actor,
    )
    assert result["new_count"] == 1 and result["merged_count"] == 1, result
    posting = db.query(Posting).one()
    assert (posting.salary_min, posting.salary_max) == (22000, 32000), posting.salary_min
    latest_record = [r for r in result["records"] if r["action"] == "merged"][0]
    assert latest_record["before_source_name"] == "拉勾招聘"
    assert latest_record["after_source_name"] == "BOSS直聘"
    assert (latest_record["before_salary_min"], latest_record["before_salary_max"]) == (20000, 30000)
    assert (latest_record["incoming_salary_min"], latest_record["incoming_salary_max"]) == (22000, 32000)

    liepin = db.query(Source).filter(Source.name == "猎聘").first()
    second = ingest_service.run_batch(
        db,
        {"batch_key": "T2", "items": [item(liepin, "L-0", "18-28K", "2026-11-08T09:00:00")]},
        actor,
    )
    assert second["merged_count"] == 1 and second["new_count"] == 0, second
    record = second["records"][0]
    assert record["conflict_kind"] == "late_old_version", record
    assert "迟到旧版本" in record["note"]
    assert record["before_source_name"] == "BOSS直聘"
    assert record["after_source_name"] == "BOSS直聘"
    db.refresh(posting)
    assert (posting.salary_min, posting.salary_max) == (22000, 32000), "迟到旧版本不得覆盖最新薪酬"
    late_raw = db.get(RawPosting, record["raw_id"])
    assert late_raw.status == "duplicate"
    assert late_raw.superseded_by_raw_id == posting.raw_id
    assert late_raw.raw_json["ingest_conflict"]["kind"] == "late_old_version"
    print("  ✓ 新版本覆盖 / 迟到旧版本不覆盖且留冲突说明")


def test_quarantine(db, actor):
    lagou = db.query(Source).filter(Source.name == "拉勾招聘").first()
    before = counts(db)
    result = ingest_service.run_batch(
        db,
        {
            "batch_key": "T3",
            "items": [
                item(lagou, "Q-1", "面议", "2026-11-13T09:00:00", title="产品经理"),
                item(lagou, "Q-2", "薪资详聊", "2026-11-13T09:00:00", title="数据分析师"),
                item(lagou, "", "15-25K", "2026-11-13T09:00:00", title="测试工程师"),
                item(lagou, "Q-4", "8-12K", "2026-11-13T09:00:00", title="SRE工程师",
                     employment_type_raw="兼职"),
                item(lagou, "Q-1", "15-25K", "2026-11-13T09:00:00", title="测试工程师"),
            ],
        },
        actor,
    )
    assert result["failed_count"] == 5, result
    assert result["new_count"] == 0 and result["merged_count"] == 0
    after = counts(db)
    assert after["postings"] == before["postings"], "隔离记录不得进入标准化表"
    assert after["raws"] == before["raws"] + 5, "隔离记录仍入湖便于追溯"
    quarantined = db.query(RawPosting).filter(RawPosting.status == "quarantined").all()
    assert len(quarantined) == 5
    reasons = {r["reason"] for r in result["records"]}
    assert {"negotiable", "unparsed", "missing:external_id", "parttime", "external_id_duplicate"} <= reasons, reasons
    print("  ✓ 面议/无法解析/缺字段/兼职/批内重复 全部隔离且不进标准化表")


def test_idempotent_and_correction_guard(db, actor):
    lagou = db.query(Source).filter(Source.name == "拉勾招聘").first()
    batch = {
        "batch_key": "T4",
        "items": [item(lagou, "I-1", "25-35K", "2026-11-14T09:00:00", title="Python后端工程师")],
    }
    first = ingest_service.run_batch(db, batch, actor)
    assert first["new_count"] == 1
    before = counts(db)
    repeat = ingest_service.run_batch(db, batch, actor)
    assert repeat["duplicate_batch"] is True
    assert counts(db) == before, "重复运行同一批不得新增岗位/记录"
    assert repeat["new_count"] == first["new_count"]

    # 人工修正后，同一自然键的新版本 / 迟到旧版本都不得改写修正值
    posting = db.query(Posting).filter(Posting.dedupe_key == posting_key(db, "I-1")).one()
    posting.salary_min, posting.salary_max, posting.salary_median = 28000, 28000, 28000
    posting.is_corrected = True
    posting.corrected_by = actor.email
    db.commit()
    corrected_before = (posting.salary_min, posting.salary_max)

    boss = db.query(Source).filter(Source.name == "BOSS直聘").first()
    later = ingest_service.run_batch(
        db,
        {"batch_key": "T5", "items": [item(boss, "I-2", "30-40K", "2026-11-20T09:00:00", title="Python后端工程师")]},
        actor,
    )
    record = later["records"][0]
    assert record["action"] == "ignored", record
    assert record["conflict_kind"] == "manual_correction_protected", record
    db.refresh(posting)
    assert (posting.salary_min, posting.salary_max) == corrected_before, "人工修正被采集覆盖"

    older = ingest_service.run_batch(
        db,
        {"batch_key": "T6", "items": [item(boss, "I-0", "20-24K", "2026-11-01T09:00:00", title="Python后端工程师")]},
        actor,
    )
    db.refresh(posting)
    assert (posting.salary_min, posting.salary_max) == corrected_before, "旧版本覆盖了人工修正"
    assert older["records"][0]["conflict_kind"] == "manual_correction_protected"

    # external_id 幂等：同一批数据换个 batch_key 重放，不新增岗位
    replay = ingest_service.run_batch(
        db,
        {"batch_key": "T7", "items": batch["items"]},
        actor,
    )
    assert replay["ignored_count"] == 1, replay
    assert replay["records"][0]["reason"] == "external_id_exists"
    assert counts(db)["postings"] == before["postings"], "重放不得新增岗位"
    print("  ✓ 同批重复运行幂等 / 人工修正不被新版本或旧版本覆盖")


def posting_key(db, external_id):
    raw = db.query(RawPosting).filter(RawPosting.external_id == external_id).first()
    posting = db.query(Posting).filter(Posting.raw_id == raw.id).first()
    return posting.dedupe_key if posting else None


def test_source_breakdown(db, actor):
    payload = ingest_service.get_batch(db, 1)
    assert payload["source_breakdown"], payload
    for row in payload["source_breakdown"]:
        assert row["total"] == row["new"] + row["merged"] + row["ignored"] + row["failed"], row
    print("  ✓ 批次分源统计：新增+合并+忽略+失败 = 总数")


def main():
    db = Session()
    actor = seed_base(db)
    try:
        print("== 采集入库验收 ==")
        test_late_old_version_and_newer_overwrite(db, actor)
        test_quarantine(db, actor)
        test_idempotent_and_correction_guard(db, actor)
        test_source_breakdown(db, actor)
        print("ALL PASS", counts(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
