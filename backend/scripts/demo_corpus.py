"""演示语料（纯标准库、确定性）：180 条原始岗位 + 分类/脏数据标签。

规模与 batch-plan gb-566 一致：
- 5 采集源、180 RawPosting（150 可归一 + 28 重复折叠 + 2 解析失败）
- 12 条脏数据：面议 4 / 日结 3 / 上下限倒置 2 / 兼职混入 2 / 极端值 1
- 150 Posting：杭州 backend 32 条干净样本用于基准报表（P25/P50/P75）

语料设计使规则 v1 试跑命中 164/180（91.1%），v2 增补面议/日结/时薪/中文千后
命中 173/180（96.1%）；数字由算法真实计算，不是前端写死。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 杭州 backend 32 条薪资中位数（元），刻意排列使 numpy 线性插值分位为
# P25=20500 / P50=28500 / P75=36000（与验收剧本一致）。
HANGZHOU_BACKEND_MEDIANS = [
    12000, 13000, 14000, 15000, 16000, 17500, 18800, 19600,
    20800, 21500, 22600, 23500, 24600, 25500, 26200, 27000,
    30000, 30800, 31500, 32200, 33000, 33800, 34500, 35000,
    39000, 40000, 41500, 43000, 45000, 47000, 49000, 52000,
]

TITLE_POOL: dict[str, list[str]] = {
    "backend": [
        "Java后端开发工程师", "Golang服务端工程师", "Python后端工程师", "资深后端工程师",
        "高级Java工程师", "后端开发Leader", "微服务后端工程师", "分布式后端工程师",
        "Java后端工程师", "后端开发工程师",
    ],
    "frontend": [
        "前端开发工程师", "资深React前端工程师", "Vue前端开发", "H5前端工程师",
        "Web前端工程师", "前端工程化工程师",
    ],
    "algorithm": [
        "算法工程师", "机器学习工程师", "推荐算法专家", "NLP算法工程师",
        "CV算法工程师", "大模型算法工程师",
    ],
    "test": [
        "测试工程师", "自动化测试工程师", "资深测试开发", "性能测试工程师", "接口测试工程师",
    ],
    "devops": ["运维工程师", "DevOps工程师", "K8s平台工程师", "SRE工程师", "云平台运维工程师"],
    "product": [
        "产品经理", "高级产品经理", "B端产品经理", "数据产品经理", "商业化产品经理", "用户增长产品经理",
    ],
    "design": ["UI设计师", "交互设计师", "视觉设计师", "用户体验设计师"],
    "data": [
        "数据分析师", "数据开发工程师", "数仓工程师", "大数据开发工程师", "ETL工程师", "数据治理工程师",
    ],
}

EXPERIENCES = ["1-3年", "3-5年", "5-10年", "不限", "应届"]

NORMAL_SALARIES = [
    "15-25K", "18-28K", "12-18K·13薪", "20-35K·14薪", "16-24K", "25-40K",
    "10-15K", "22-30K·15薪", "13-20K", "8-12K", "30-45K", "26-38K·16薪",
    "14-22K", "17-26K", "20-30万/年", "24-36万/年", "19-27K", "11-16K",
]

# (source_code, city, function_type, count, dirty_kind)
BUCKETS: list[tuple[str, str, str, int, str]] = [
    ("lagou", "杭州", "backend", 32, "crafted"),
    ("boss", "上海", "backend", 28, "swapped_outlier"),
    ("liepin", "北京", "data", 24, "negotiable"),
    ("lagou", "杭州", "frontend", 14, "clean"),
    ("boss", "上海", "frontend", 6, "daily"),
    ("liepin", "北京", "algorithm", 14, "clean"),
    ("lagou", "杭州", "test", 6, "clean"),
    ("boss", "北京", "test", 4, "daily"),
    ("ruishi", "深圳", "devops", 8, "parttime"),
    ("company", "杭州", "product", 5, "clean"),
    ("boss", "上海", "product", 3, "clean"),
    ("lagou", "杭州", "design", 3, "clean"),
    ("liepin", "北京", "design", 3, "clean"),
]

SOURCES: list[dict] = [
    {"name": "拉勾招聘", "site_type": "recruit_site", "note": "主站，IT/互联网岗位", "enabled": True},
    {"name": "BOSS直聘", "site_type": "recruit_site", "note": "直聊岗位，薪资口径较杂", "enabled": True},
    {"name": "猎聘", "site_type": "recruit_site", "note": "中高端岗位，年薪制较多", "enabled": True},
    {"name": "岗线企业招聘官网", "site_type": "company_site", "note": "客户自有官网，字段规范", "enabled": True},
    {"name": "锐仕方达猎头", "site_type": "headhunter", "note": "猎头渠道，JD 简略", "enabled": True},
]

SOURCE_CODE_TO_NAME = {
    "lagou": "拉勾招聘",
    "boss": "BOSS直聘",
    "liepin": "猎聘",
    "company": "岗线企业招聘官网",
    "ruishi": "锐仕方达猎头",
}

COMPANIES = [
    "杭州云栖网络科技有限公司", "上海数澜信息技术", "北京星河数据", "深圳前海智联",
    "杭州岗线数据服务", "上海橙链科技", "北京明湖智能", "深圳南山云",
    "广州穗云科技", "杭州西溪数科",
]


@dataclass
class RawItem:
    external_id: str
    source_code: str
    title_raw: str
    salary_raw: str
    city_raw: str
    experience_raw: str
    employment_type_raw: str
    company: str
    status: str
    category: str
    meta: dict = field(default_factory=dict)


def _salary_for_median(median: int, variant: int) -> str:
    """按目标月薪中位数构造薪资文本（单位 K）。"""
    if variant % 3 == 0:
        return f"{median / 1000:g}K"
    delta = 2000 if variant % 3 == 1 else 1500
    low = median - delta
    high = median + delta
    if low >= 10000 and high % 1000 == 0 and variant % 3 == 1:
        return f"{low // 1000}K-{high // 1000}K"
    return f"{low / 1000:g}K-{high / 1000:g}K"


def _clean_raw_salary(index: int) -> str:
    return NORMAL_SALARIES[index % len(NORMAL_SALARIES)]


def build_corpus() -> list[RawItem]:
    items: list[RawItem] = []
    seq = 0

    def add(source_code: str, title: str, salary: str, city: str, status: str, category: str,
            experience: str | None = None, employment: str = "全职", meta: dict | None = None) -> None:
        nonlocal seq
        seq += 1
        idx = seq
        items.append(
            RawItem(
                external_id=f"{source_code.upper()}-{idx:04d}",
                source_code=source_code,
                title_raw=title,
                salary_raw=salary,
                city_raw=f"{city}市·核心区" if idx % 3 == 0 else f"{city}·{['西湖区', '浦东新区', '海淀区', '南山区'][idx % 4]}",
                experience_raw=experience or EXPERIENCES[idx % len(EXPERIENCES)],
                employment_type_raw=employment,
                company=COMPANIES[idx % len(COMPANIES)],
                status=status,
                category=category,
                meta=meta or {},
            )
        )

    # 1) 150 条可归一岗位
    for bucket_index, (source_code, city, function_type, count, dirty) in enumerate(BUCKETS):
        titles = TITLE_POOL[function_type]
        for i in range(count):
            title = titles[(i + bucket_index) % len(titles)]
            if dirty == "crafted":
                salary = _salary_for_median(HANGZHOU_BACKEND_MEDIANS[i], i)
                cat = "posting"
            elif dirty == "swapped_outlier":
                if function_type == "backend" and i == 0:
                    salary, cat = "28K-18K", "posting_dirty"
                elif function_type == "backend" and i == 1:
                    salary, cat = "45K-25K", "posting_dirty"
                elif function_type == "backend" and i == 2:
                    salary, cat = "1200K", "posting_dirty"
                elif function_type == "backend" and i == 3:
                    # 验收剧本指定样例：15-25K·14薪 → min=17500 / max=29166 / median=23333
                    salary, cat = "15-25K·14薪", "posting"
                else:
                    salary, cat = _clean_raw_salary(bucket_index * 7 + i), "posting"
            elif dirty == "negotiable" and i < 4:
                salary = ["面议", "薪资面议", "薪资可谈", "面议（含奖金）"][i]
                cat = "posting_dirty"
            elif dirty == "daily" and i < (2 if function_type == "frontend" else 1):
                salary = ["300/天", "日结260", "280元/天"][i]
                cat = "posting_dirty"
            elif dirty == "parttime" and i < 2:
                salary = "8-12K"
                cat = "posting_dirty"
            else:
                salary = _clean_raw_salary(bucket_index * 5 + i + (3 if dirty == "swapped_outlier" else 0))
                cat = "posting"
            employment = "兼职" if cat == "posting_dirty" and dirty == "parttime" and i < 2 else "全职"
            add(source_code, title, salary, city, "parsed", cat, employment=employment)

    # 2) 28 条重复折叠（21 条正常薪资 + 2 条中文千 + 5 条脏原文无法归一）
    dup_numeric = ["15-25K", "18-28K", "20-35K·14薪", "12-18K", "22-30K·15薪", "16-24K"]
    for i in range(21):
        add("lagou", TITLE_POOL["backend"][i % len(TITLE_POOL["backend"])],
            dup_numeric[i % len(dup_numeric)], ["杭州", "上海"][i % 2], "duplicate", "duplicate")
    add("liepin", "数据开发工程师", "8千-1.2万", "北京", "duplicate", "duplicate")
    add("liepin", "数仓工程师", "9千-1.5万", "北京", "duplicate", "duplicate")
    invalid_salaries = [
        "薪资结构：12+3", "250元/班次", "综合收入1-2w（含加班）",
        "月发薪，年终另计", "按项目结算，月结",
    ]
    for i, salary in enumerate(invalid_salaries):
        add("boss", TITLE_POOL["test"][i % len(TITLE_POOL["test"])], salary, "上海", "invalid", "invalid")

    # 3) 2 条硬失败（人工补充后进入标准化）
    add("company", "资深数据开发工程师", "薪资详聊", "杭州", "failed", "failed")
    add("ruishi", "技术负责人（数据方向）", "另议（base+期权）", "深圳", "failed", "failed")

    assert len(items) == 180, len(items)
    return items


def build_hit_expectations() -> dict:
    """语料设计期望值（seed 会真实重算并打印实际命中率）。"""
    return {
        "total_raws": 180,
        "v1_hits": 164,
        "v2_hits": 173,
        "postings": 150,
        "dirty": 12,
        "failed": 2,
        "duplicate": 23,
        "invalid": 5,
    }
