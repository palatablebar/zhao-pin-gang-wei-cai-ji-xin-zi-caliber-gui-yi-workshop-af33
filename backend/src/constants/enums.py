"""共享枚举（后端副本）。前端副本见 frontend/src/constants/enums.ts。

出现位置：
- roles: src/constants/roles.py / src/models/user.py / schemas/auth.py / routes / frontend/src/constants/enums.ts
- site_type: models/source.py / schemas/source.py / seed / Sources 页
- raw_status: models/raw_posting.py / raw_service / Raw 页筛选项
- function_type / seniority / salary_unit: models/posting.py / schemas / benchmark_service / Postings·Benchmarks 页
- quality_flag: posting_service / quality_service / Quality 页
- rule_type: models/parse_rule.py / rule_service / Rules 页
- benchmark_status: models/benchmark.py / Benchmarks 页
"""
from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_CLIENT = "client"
ROLES = [ROLE_ADMIN, ROLE_ANALYST, ROLE_CLIENT]

SITE_RECRUIT = "recruit_site"
SITE_COMPANY = "company_site"
SITE_HEADHUNTER = "headhunter"
SITE_TYPES = [SITE_RECRUIT, SITE_COMPANY, SITE_HEADHUNTER]
SITE_TYPE_LABELS = {
    SITE_RECRUIT: "招聘网站",
    SITE_COMPANY: "企业官网",
    SITE_HEADHUNTER: "猎头渠道",
}

RAW_PARSED = "parsed"
RAW_NEEDS_REVIEW = "needs_review"
RAW_FAILED = "failed"
RAW_DUPLICATE = "duplicate"
RAW_INVALID = "invalid"
RAW_CORRECTED = "corrected"
RAW_STATUSES = [RAW_PARSED, RAW_NEEDS_REVIEW, RAW_FAILED, RAW_DUPLICATE, RAW_INVALID, RAW_CORRECTED]
RAW_STATUS_LABELS = {
    RAW_PARSED: "已解析",
    RAW_NEEDS_REVIEW: "待修正",
    RAW_FAILED: "解析失败",
    RAW_DUPLICATE: "重复折叠",
    RAW_INVALID: "脏原文",
    RAW_CORRECTED: "人工修正",
}

FUNCTION_TYPES = ["backend", "frontend", "algorithm", "test", "devops", "product", "design", "data"]
FUNCTION_LABELS = {
    "backend": "后端",
    "frontend": "前端",
    "algorithm": "算法",
    "test": "测试",
    "devops": "运维",
    "product": "产品",
    "design": "设计",
    "data": "数据",
}
SENIORITIES = ["junior", "mid", "senior", "staff", "manager", "director"]
SENIORITY_LABELS = {
    "junior": "初级",
    "mid": "中级",
    "senior": "高级",
    "staff": "资深",
    "manager": "经理",
    "director": "总监",
}
SALARY_UNIT_MONTHLY = "monthly"
SALARY_UNIT_ANNUAL = "annual"
SALARY_UNITS = [SALARY_UNIT_MONTHLY, SALARY_UNIT_ANNUAL]

SALARY_OK = "ok"
SALARY_NEGOTIABLE = "negotiable"
SALARY_UNPARSED = "unparsed"

RULE_TYPE_SALARY = "salary"
RULE_TYPE_TITLE = "title"
RULE_TYPES = [RULE_TYPE_SALARY, RULE_TYPE_TITLE]

QUALITY_NEGOTIABLE = "negotiable"
QUALITY_DAILY_WAGE = "daily_wage"
QUALITY_SWAPPED = "swapped"
QUALITY_OUTLIER = "outlier"
QUALITY_PARTTIME = "parttime"
QUALITY_NEEDS_REVIEW = "needs_review"
QUALITY_FLags = [
    QUALITY_NEGOTIABLE,
    QUALITY_DAILY_WAGE,
    QUALITY_SWAPPED,
    QUALITY_OUTLIER,
    QUALITY_PARTTIME,
    QUALITY_NEEDS_REVIEW,
]
QUALITY_LABELS = {
    QUALITY_NEGOTIABLE: "面议待补",
    QUALITY_DAILY_WAGE: "日结/时薪折算",
    QUALITY_SWAPPED: "上下限倒置",
    QUALITY_OUTLIER: "极端值",
    QUALITY_PARTTIME: "兼职混入",
    QUALITY_NEEDS_REVIEW: "待人工复核",
}

QUALITY_STATUS_OPEN = "open"
QUALITY_STATUS_DISPOSED = "disposed"
QUALITY_STATUS_IGNORED = "ignored"

BENCHMARK_PUBLISHED = "published"
BENCHMARK_DRAFT = "draft"
