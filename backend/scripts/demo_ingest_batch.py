"""五渠道重送演示批次：同一批岗位从 5 个来源重复投递、版本先后混排。

用于验证采集入库的三条验收行为：
1. 同一公司 + 城市 + 职位，新版本覆盖旧版本薪酬（合并并记录合并前后来源）；
2. 迟到旧版本（发布时间更早）不覆盖最新薪酬，台账留冲突说明；
3. 面议 / 无法解析 / 缺字段 / 兼职 / 批内重复 external_id 异常记录单独隔离；
4. 同一来源重复投递已入湖的 external_id 按幂等忽略。

批次以 batch_key 幂等：同一批重复运行不新增岗位，不改写人工修正。
"""
from __future__ import annotations

from datetime import datetime

# (source_name, external_id, title, company, city, salary_raw, published_at, employment)
DEMO_ITEMS: list[tuple[str, str, str, str, str, str, str, str]] = [
    # ① 同一岗位 5 个渠道同日重送：BOSS 最早 22-32K，后续渠道逐版本下调/上调
    ("BOSS直聘", "DEMO-BOSS-001", "高级Java工程师", "杭州云栖网络科技有限公司", "杭州",
     "22-32K", "2026-11-10T09:00:00", "全职"),
    ("拉勾招聘", "DEMO-LAGOU-001", "高级Java工程师", "杭州云栖网络科技有限公司", "杭州",
     "22-32K·14薪", "2026-11-11T09:00:00", "全职"),
    ("猎聘", "DEMO-LIEPIN-001", "高级Java工程师", "杭州云栖网络科技有限公司", "杭州",
     "28-38万/年", "2026-11-12T09:00:00", "全职"),
    ("岗线企业招聘官网", "DEMO-SITE-001", "高级Java工程师", "杭州云栖网络科技有限公司", "杭州",
     "20-30K", "2026-11-13T09:00:00", "全职"),
    # 迟到旧版本：发布时间比已入库版本早一天，不得覆盖最新 20-30K
    ("锐仕方达猎头", "DEMO-HEAD-001", "高级Java工程师", "杭州云栖网络科技有限公司", "杭州",
     "26-36K", "2026-11-09T09:00:00", "全职"),

    # ② 新岗位：猎头渠道先投，官网后投更晚的版本
    ("锐仕方达猎头", "DEMO-HEAD-002", "资深数据开发工程师", "上海数澜信息技术", "上海",
     "30-40K", "2026-11-11T15:00:00", "全职"),
    ("岗线企业招聘官网", "DEMO-SITE-002", "资深数据开发工程师", "上海数澜信息技术", "上海",
     "35-45K·15薪", "2026-11-12T15:00:00", "全职"),

    # ③ 异常记录：面议 / 无法解析 / 缺 external_id / 兼职 / 批内重复
    ("猎聘", "DEMO-LIEPIN-003", "数据治理工程师", "北京星河数据", "北京",
     "面议", "2026-11-13T10:00:00", "全职"),
    ("BOSS直聘", "DEMO-BOSS-003", "推荐算法工程师", "北京明湖智能", "北京",
     "薪资详聊", "2026-11-13T10:00:00", "全职"),
    ("拉勾招聘", "", "测试开发工程师", "深圳前海智联", "深圳",
     "18-28K", "2026-11-13T10:00:00", "全职"),
    ("锐仕方达猎头", "DEMO-HEAD-004", "SRE工程师", "深圳南山云", "深圳",
     "8-12K", "2026-11-13T10:00:00", "兼职"),
    ("BOSS直聘", "DEMO-BOSS-003", "推荐算法工程师", "北京明湖智能", "北京",
     "25-35K", "2026-11-13T10:00:00", "全职"),

    # ④ 同一来源重复投递已入湖的 external_id：按幂等忽略，不改写已有数据
    ("拉勾招聘", "LAGOU-0001", "Java后端开发工程师", "上海数澜信息技术", "杭州",
     "12K", "2026-11-01T09:30:00", "全职"),
    # ⑤ 新岗位（算法）：与上面的异常记录自然键不同
    ("猎聘", "DEMO-LIEPIN-005", "推荐算法工程师", "北京明湖智能", "北京",
     "35-50K·16薪", "2026-11-13T11:00:00", "全职"),
]

DEMO_BATCH_KEY = "demo-five-channel-2026-11-13"


def demo_batch(source_ids: dict[str, int] | None = None) -> dict:
    source_ids = source_ids or {}
    items = []
    for source_name, external_id, title, company, city, salary, published, employment in DEMO_ITEMS:
        entry = {
            "source_name": source_name,
            "external_id": external_id,
            "title": title,
            "company": company,
            "city": city,
            "salary_raw": salary,
            "published_at": published,
            "employment_type_raw": employment,
            "experience_raw": "3-5年",
        }
        if source_name in source_ids:
            entry["source_id"] = source_ids[source_name]
        items.append(entry)
    return {
        "batch_key": DEMO_BATCH_KEY,
        "name": "五渠道重送演示批（同一岗位多来源 + 迟到旧版本 + 异常隔离）",
        "note": "同一公司/城市/职位只保留最新薪酬；迟到旧版本留冲突说明；异常记录隔离",
        "items": items,
    }


if __name__ == "__main__":
    import json
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.config.database import SessionLocal
    from src.models.source import Source

    ids: dict[str, int] = {}
    try:
        db = SessionLocal()
        try:
            ids = {source.name: source.id for source in db.query(Source).all()}
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - 无数据库时仍可打印 source_name 版本
        ids = {}
    print(json.dumps(demo_batch(ids), ensure_ascii=False, indent=2))
