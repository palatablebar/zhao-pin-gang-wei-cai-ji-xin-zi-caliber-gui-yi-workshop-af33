"""算法 A：薪资文本解析与月薪标准化（纯标准库，可在宿主机单测）。

输入：招聘站采集到的 salary_raw 文本，如
  「15-25K·14薪」「8千-1.2万」「20-30万/年」「300/天」「45元/小时」「面议」
输出：SalaryParseResult（元/月口径的 min/max/median、unit_kind、annual_months、
  confidence、reason_code、质量旗标、命中的规则）。

公式口径：
1. 单位换算：K=千=1000，万=10000。
2. 周期折算月薪：月 ×1；年 ÷12；日 ×22（工作日）；时 ×8×22=176。
3. 年薪制月薪 = 年薪总额 / 12；岗位若标注 13~16 薪，则
   月薪 = 原始月薪 × annual_months / 12（annual_months 默认 12）。
   「13-16薪」取上限 16；「·14薪」取 14。
4. median = (min + max) // 2（向下取整，与验收剧本 15-25K·14薪 的 23333 一致）。
5. 校验：min>max 则交换并标 swapped；月薪越界 [3000, 300000] 标 outlier；
   面议 → 全 null + negotiable；无法解析 → 全 null + unparsed。
6. 规则版本：v1 基线（K/万/年/月/单值/薪数）；v2 增补面议、日结、时薪、中文千。
   规则与词典版本化，可复现（纯函数、无随机）。
失败态：返回 status=unparsed + reason_code，调用方据此写 raw.status / 质量标记。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from src.constants.enums import (
    QUALITY_DAILY_WAGE,
    QUALITY_NEGOTIABLE,
    QUALITY_OUTLIER,
    QUALITY_SWAPPED,
    SALARY_NEGOTIABLE,
    SALARY_OK,
    SALARY_UNIT_ANNUAL,
    SALARY_UNIT_MONTHLY,
    SALARY_UNPARSED,
)

SALARY_FLOOR = 3000
SALARY_CEILING = 300000
WORK_DAYS = 22
WORK_HOURS = 8

# 规则依赖：规则码 → 需要哪些模式（版本差异的唯一来源）
SUPPORTED_PATTERNS: dict[str, set[str]] = {
    "v1": {"k_range", "k_single", "wan_year", "wan_month", "annual_months"},
    "v2": {
        "k_range",
        "k_single",
        "wan_year",
        "wan_month",
        "wan_single",
        "annual_months",
        "negotiable",
        "daily_wage",
        "hourly_wage",
        "qian_range",
    },
}

RULE_META = {
    "k_range": ("薪资 K 区间", "K/千 区间，如 15-25K"),
    "k_single": ("薪资 K 单值", "单值 K，如 20K"),
    "wan_year": ("年薪万区间", "如 20-30万/年"),
    "wan_month": ("月薪万区间", "如 1.5-2万/月"),
    "wan_single": ("万单值", "如 月薪2万 / 年薪20万"),
    "annual_months": ("13-16 薪折算", "如 ·14薪 / 13-16薪"),
    "negotiable": ("面议识别", "面议 / 薪资面议 / 可谈"),
    "daily_wage": ("日结折算", "300/天 / 日结260，月薪=日×22"),
    "hourly_wage": ("时薪折算", "45元/小时，月薪=时×8×22"),
    "qian_range": ("中文千区间", "8千-1.2万"),
}


@dataclass
class SalaryParseResult:
    status: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_median: int | None = None
    unit_kind: str = SALARY_UNIT_MONTHLY
    annual_months: int = 12
    confidence: float = 0.0
    reason_code: str = ""
    flags: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)

    @property
    def is_hit(self) -> bool:
        return self.status in (SALARY_OK, SALARY_NEGOTIABLE)


_NEGOTIABLE_RE = re.compile(r"面议|可谈|面谈")
_MONTHS_RANGE_RE = re.compile(r"(\d{1,2})\s*[-~至到]\s*(\d{1,2})\s*薪")
_MONTHS_SINGLE_RE = re.compile(r"(\d{1,2})\s*薪")
_KRANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*k\s*[-~]\s*(\d+(?:\.\d+)?)\s*k")
_KRANGE_SHARED_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*k")
_KSINGLE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*k")
_QRANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*千\s*[-~]\s*(\d+(?:\.\d+)?)\s*万")
_QIAN_SINGLE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*千")
_WANYEAR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*万\s*(?:元)?\s*(?:/|每)?\s*年")
_WANYEAR_SINGLE_RE = re.compile(r"年薪\s*(\d+(?:\.\d+)?)\s*万")
_WANMONTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*万\s*(?:元)?\s*(?:/|每)?\s*月")
_WANMONTH_SINGLE_RE = re.compile(r"月薪\s*(\d+(?:\.\d+)?)\s*万")
_WANSINGLE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*万")
_DAILY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:元)?\s*(?:/|每)\s*(?:天|日)|日结\s*(\d+(?:\.\d+)?)")
_HOURLY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:元)?\s*(?:/|每)\s*(?:小时|时)|时薪\s*(\d+(?:\.\d+)?)")


def normalize_text(text: str) -> str:
    """全角→半角、小写、统一连接符、去千分位逗号。"""
    s = unicodedata.normalize("NFKC", text or "").lower()
    s = s.replace("，", ",").replace(" ", "")
    s = re.sub(r"[~～—–－]", "-", s)
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)
    return s.strip()


def _annual_months(text: str) -> int:
    m = _MONTHS_RANGE_RE.search(text)
    if m:
        return max(12, int(m.group(2)))
    m = _MONTHS_SINGLE_RE.search(text)
    if m:
        return max(12, int(m.group(1)))
    return 12


def _apply_months(value: float, months: int) -> int:
    """先对基准数取整再折算，避免浮点误差把 29.3K 算成 29299。"""
    return int(round(value) * months / 12)


def _finish(
    low: float,
    high: float,
    unit_kind: str,
    months: int,
    confidence: float,
    rule_code: str,
    flags: list[str],
    rules: list[str],
) -> SalaryParseResult:
    salary_min = int(low)
    salary_max = int(high)
    if salary_min > salary_max:
        salary_min, salary_max = salary_max, salary_min
        flags.append(QUALITY_SWAPPED)
    salary_median = (salary_min + salary_max) // 2
    if salary_min < SALARY_FLOOR or salary_max > SALARY_CEILING:
        flags.append(QUALITY_OUTLIER)
    reason = "swapped" if QUALITY_SWAPPED in flags else ("outlier" if QUALITY_OUTLIER in flags else "")
    return SalaryParseResult(
        status=SALARY_OK,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_median=salary_median,
        unit_kind=unit_kind,
        annual_months=months,
        confidence=confidence,
        reason_code=reason or f"parsed:{rule_code}",
        flags=flags,
        matched_rules=rules,
    )


def parse_salary(text: str, version: str = "v2") -> SalaryParseResult:
    """解析单条薪资文本。version 决定可用模式（v1 历史基线 / v2 当前）。"""
    patterns = SUPPORTED_PATTERNS.get(version, SUPPORTED_PATTERNS["v2"])
    raw = normalize_text(text)
    if not raw:
        return SalaryParseResult(status=SALARY_UNPARSED, reason_code="empty_salary")

    months = _annual_months(raw) if "annual_months" in patterns else 12
    rules: list[str] = []
    if "annual_months" in patterns and months != 12:
        rules.append("annual_months")

    if "negotiable" in patterns and _NEGOTIABLE_RE.search(raw):
        return SalaryParseResult(
            status=SALARY_NEGOTIABLE,
            annual_months=months,
            confidence=0.9,
            reason_code="negotiable",
            flags=[QUALITY_NEGOTIABLE],
            matched_rules=rules + ["negotiable"],
        )

    # 1) K 区间
    m = _KRANGE_RE.search(raw) or _KRANGE_SHARED_RE.search(raw)
    if m:
        low = _apply_months(float(m.group(1)) * 1000, months)
        high = _apply_months(float(m.group(2)) * 1000, months)
        return _finish(low, high, SALARY_UNIT_MONTHLY, months, 0.95, "k_range", [], rules + ["k_range"])

    # 2) 中文千 - 万区间（v2）
    if "qian_range" in patterns:
        m = _QRANGE_RE.search(raw)
        if m:
            low = _apply_months(float(m.group(1)) * 1000, months)
            high = _apply_months(float(m.group(2)) * 10000, months)
            return _finish(low, high, SALARY_UNIT_MONTHLY, months, 0.92, "qian_range", [], rules + ["qian_range"])

    # 3) 年薪万区间
    m = _WANYEAR_RE.search(raw)
    if m:
        low = int(float(m.group(1)) * 10000 / 12)
        high = int(float(m.group(2)) * 10000 / 12)
        return _finish(low, high, SALARY_UNIT_ANNUAL, 12, 0.9, "wan_year", [], rules[:1] + ["wan_year"])
    m = _WANYEAR_SINGLE_RE.search(raw)
    if m:
        annual = float(m.group(1)) * 10000
        return _finish(int(annual / 12), int(annual / 12), SALARY_UNIT_ANNUAL, 12, 0.8, "wan_year", [], ["wan_year"])

    # 4) 月薪万区间
    m = _WANMONTH_RE.search(raw)
    if m:
        low = _apply_months(float(m.group(1)) * 10000, months)
        high = _apply_months(float(m.group(2)) * 10000, months)
        return _finish(low, high, SALARY_UNIT_MONTHLY, 12, 0.9, "wan_month", [], ["wan_month"])
    m = _WANMONTH_SINGLE_RE.search(raw)
    if m:
        v = _apply_months(float(m.group(1)) * 10000, 12)
        return _finish(v, v, SALARY_UNIT_MONTHLY, 12, 0.8, "wan_month", [], ["wan_month"])

    # 5) 日结 / 时薪（v2）
    if "daily_wage" in patterns:
        m = _DAILY_RE.search(raw)
        if m:
            value = m.group(1) or m.group(2)
            monthly = int(float(value) * WORK_DAYS)
            return _finish(
                monthly, monthly, SALARY_UNIT_MONTHLY, 12, 0.85, "daily_wage", [QUALITY_DAILY_WAGE], rules + ["daily_wage"]
            )
    if "hourly_wage" in patterns:
        m = _HOURLY_RE.search(raw)
        if m:
            value = m.group(1) or m.group(2)
            monthly = int(float(value) * WORK_HOURS * WORK_DAYS)
            return _finish(
                monthly, monthly, SALARY_UNIT_MONTHLY, 12, 0.85, "hourly_wage", [QUALITY_DAILY_WAGE], rules + ["hourly_wage"]
            )

    # 6) K 单值
    m = _KSINGLE_RE.search(raw)
    if m:
        v = _apply_months(float(m.group(1)) * 1000, months)
        return _finish(v, v, SALARY_UNIT_MONTHLY, months, 0.8, "k_single", [], rules + ["k_single"])

    # 7) 万单值（无 /月 视为年薪；v1 不做该猜测，避免把「8千-1.2万」误判成 1.2万/12）
    if "wan_single" in patterns:
        m = _WANSINGLE_RE.search(raw)
        if m:
            if "月" in raw:
                v = _apply_months(float(m.group(1)) * 10000, 12)
                return _finish(v, v, SALARY_UNIT_MONTHLY, 12, 0.75, "wan_month", [], ["wan_month"])
            annual = int(float(m.group(1)) * 10000 / 12)
            return _finish(annual, annual, SALARY_UNIT_ANNUAL, 12, 0.72, "wan_year", [], ["wan_single"])

    if "qian_range" in patterns:
        m = _QIAN_SINGLE_RE.search(raw)
        if m:
            v = _apply_months(float(m.group(1)) * 1000, months)
            return _finish(v, v, SALARY_UNIT_MONTHLY, months, 0.75, "qian_range", [], ["qian_range"])

    return SalaryParseResult(status=SALARY_UNPARSED, reason_code="no_pattern_matched")


def trial_rate(texts: list[str], version: str) -> dict:
    """规则试跑：命中率 = 成功判定（ok + negotiable）/ 尝试条数。"""
    hits = 0
    reasons: dict[str, int] = {}
    rule_hits: dict[str, int] = {}
    for text in texts:
        result = parse_salary(text, version)
        reasons[result.reason_code] = reasons.get(result.reason_code, 0) + 1
        if result.is_hit:
            hits += 1
            for code in result.matched_rules:
                rule_hits[code] = rule_hits.get(code, 0) + 1
    total = len(texts)
    return {
        "version": version,
        "attempts": total,
        "hits": hits,
        "misses": total - hits,
        "hit_rate": round(hits * 100.0 / total, 1) if total else 0.0,
        "hit_rate_pct": round(hits * 100.0 / total) if total else 0,
        "reason_breakdown": reasons,
        "rule_hits": rule_hits,
    }
