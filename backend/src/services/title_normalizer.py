"""算法 B：岗位标题归一与职级/职能映射（纯标准库，可复现）。

流程：
1. 清洗：NFKC 全角→半角、小写、去括号内容（急招/城市）、去营销词（高薪/急聘/包住…）。
2. 词典最大匹配分词：职能词（60 词）优先命中最长词，按权重求和选职能。
3. 职级映射：职级词（12 词）+ 经验年限（3-5 年）→ seniority；规则版本化。
4. 相似标题合并：字符 3-gram Jaccard ≥ 0.80 归并到已有 canonical，
   取频次最高的写法（batch_merge_titles）；输出 matched_terms。
输出：canonical_title / function_type / seniority / confidence / matched_terms。
失败态：无职能词命中 → function_type 取置信度最低的 data 兜底并低 confidence，
  由质量门禁 needs_review 标记，不静默当成正确答案。
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from src.constants.enums import FUNCTION_TYPES, FUNCTION_LABELS, SENIORITIES, SENIORITY_LABELS

TITLE_DICT_VERSION = "title-dict-v2"
# 3-gram 相似阈值（Jaccard）
NGRAM_MERGE_THRESHOLD = 0.8

MARKETING_WORDS = [
    "急招", "急聘", "高薪", "包住", "包吃", "双休", "五险一金", "年终奖", "直招",
    "大厂", "长期招聘", "高提成", "轻松", "稳定", "六险一金", "弹性工作",
]

# 职能词典（60 词）：keyword -> (function_type, weight)
FUNCTION_DICT: dict[str, tuple[str, float]] = {
    "后端": ("backend", 3.0),
    "服务端": ("backend", 3.0),
    "java": ("backend", 2.2),
    "golang": ("backend", 2.2),
    "go开发": ("backend", 2.2),
    "python": ("backend", 2.0),
    "c++": ("backend", 2.0),
    "spring": ("backend", 2.0),
    "微服务": ("backend", 2.4),
    "分布式": ("backend", 2.2),
    "中间件": ("backend", 2.0),
    "消息队列": ("backend", 1.8),
    "api": ("backend", 1.5),
    "前端": ("frontend", 3.0),
    "react": ("frontend", 2.2),
    "vue": ("frontend", 2.2),
    "h5": ("frontend", 1.8),
    "web": ("frontend", 1.6),
    "小程序": ("frontend", 1.8),
    "taro": ("frontend", 1.6),
    "node": ("frontend", 1.5),
    "工程化": ("frontend", 1.6),
    "组件库": ("frontend", 1.6),
    "算法": ("algorithm", 3.0),
    "机器学习": ("algorithm", 2.6),
    "深度学习": ("algorithm", 2.6),
    "推荐": ("algorithm", 2.2),
    "搜索": ("algorithm", 1.8),
    "nlp": ("algorithm", 2.2),
    "cv": ("algorithm", 2.0),
    "大模型": ("algorithm", 2.2),
    "llm": ("algorithm", 2.2),
    "测试": ("test", 3.0),
    "自动化测试": ("test", 2.8),
    "测试开发": ("test", 2.8),
    "qa": ("test", 1.6),
    "性能测试": ("test", 2.2),
    "接口测试": ("test", 2.0),
    "运维": ("devops", 3.0),
    "devops": ("devops", 2.6),
    "sre": ("devops", 2.4),
    "k8s": ("devops", 2.2),
    "kubernetes": ("devops", 2.0),
    "云平台": ("devops", 2.0),
    "容器": ("devops", 1.8),
    "监控": ("devops", 1.6),
    "产品经理": ("product", 3.0),
    "产品": ("product", 2.4),
    "需求分析": ("product", 2.2),
    "用户增长": ("product", 2.0),
    "商业化": ("product", 1.8),
    "数据分析": ("data", 2.8),
    "数仓": ("data", 2.8),
    "数据开发": ("data", 2.8),
    "大数据": ("data", 2.6),
    "etl": ("data", 2.2),
    "bi": ("data", 1.8),
    "数据治理": ("data", 2.2),
    "设计": ("design", 2.6),
    "设计师": ("design", 3.0),
    "ui": ("design", 2.4),
    "交互": ("design", 2.4),
    "视觉": ("design", 2.2),
    "用户体验": ("design", 2.0),
    "ux": ("design", 2.2),
}

# 职级词典（12 词）
SENIORITY_DICT: dict[str, str] = {
    "初级": "junior",
    "junior": "junior",
    "应届": "junior",
    "助理": "junior",
    "中级": "mid",
    "高级": "senior",
    "senior": "senior",
    "资深": "staff",
    "专家": "staff",
    "principal": "staff",
    "负责人": "manager",
    "主管": "manager",
    "经理": "manager",
    "总监": "director",
    "director": "director",
}

FUNCTION_CANONICAL = {
    "backend": "后端工程师",
    "frontend": "前端工程师",
    "algorithm": "算法工程师",
    "test": "测试工程师",
    "devops": "运维工程师",
    "product": "产品经理",
    "design": "设计师",
    "data": "数据工程师",
}
SENIORITY_PREFIX = {
    "junior": "初级",
    "mid": "",
    "senior": "高级",
    "staff": "资深",
}
# 管理序列标题单独成词，避免出现「经理产品经理」这类拼接错位
MANAGER_TITLES = {
    "backend": "后端负责人",
    "frontend": "前端负责人",
    "algorithm": "算法负责人",
    "test": "测试负责人",
    "devops": "运维负责人",
    "product": "产品负责人",
    "design": "设计负责人",
    "data": "数据负责人",
}
DIRECTOR_TITLES = {
    "backend": "后端总监",
    "frontend": "前端总监",
    "algorithm": "算法总监",
    "test": "测试总监",
    "devops": "运维总监",
    "product": "产品总监",
    "design": "设计总监",
    "data": "数据总监",
}
SENIORITY_RANK = {name: idx for idx, name in enumerate(SENIORITIES)}

_YEAR_RANGE_RE = re.compile(r"(\d{1,2})\s*[-~至]\s*(\d{1,2})\s*年")
_YEAR_PLUS_RE = re.compile(r"(\d{1,2})\s*年(?:以上|\+)")
_YEAR_SINGLE_RE = re.compile(r"(\d{1,2})\s*年")


@dataclass
class TitleParseResult:
    canonical_title: str
    function_type: str
    seniority: str
    confidence: float
    matched_terms: list[str] = field(default_factory=list)
    merged_from: str = ""

    def to_dict(self) -> dict:
        return {
            "canonical_title": self.canonical_title,
            "function_type": self.function_type,
            "seniority": self.seniority,
            "confidence": round(self.confidence, 2),
            "matched_terms": self.matched_terms,
            "merged_from": self.merged_from,
        }


def clean_title(title: str) -> str:
    s = unicodedata.normalize("NFKC", title or "")
    s = s.lower()
    s = re.sub(r"[（(][^）)]*[）)]", " ", s)
    for word in MARKETING_WORDS:
        s = s.replace(word.lower(), " ")
    s = re.sub(r"[\s/|·,，、:：\-]+", " ", s).strip()
    return s


def _max_match_keywords(text: str) -> list[tuple[str, str, float]]:
    """词典最大匹配：在每个位置尝试最长词，命中后跳过该词长度。

    返回 [(keyword, function_type, weight), ...]，按出现顺序。
    """
    keys = sorted(FUNCTION_DICT.keys(), key=len, reverse=True)
    found: list[tuple[str, str, float]] = []
    i = 0
    n = len(text)
    while i < n:
        hit = None
        for key in keys:
            if key and text.startswith(key, i):
                hit = key
                break
        if hit:
            func, weight = FUNCTION_DICT[hit]
            found.append((hit, func, weight))
            i += len(hit)
        else:
            i += 1
    return found


def _detect_seniority_from_years(experience_raw: str) -> str | None:
    text = unicodedata.normalize("NFKC", experience_raw or "")
    m = _YEAR_RANGE_RE.search(text)
    if m:
        low = int(m.group(1))
    else:
        m = _YEAR_PLUS_RE.search(text) or _YEAR_SINGLE_RE.search(text)
        low = int(m.group(1)) if m else None
    if low is None:
        return None
    if low <= 2:
        return "junior"
    if low <= 4:
        return "mid"
    if low <= 7:
        return "senior"
    if low <= 10:
        return "staff"
    return "manager"


def normalize_title(title: str, experience_raw: str = "") -> TitleParseResult:
    cleaned = clean_title(title)
    matched = _max_match_keywords(cleaned)
    matched_terms = [term for term, _, _ in matched]

    score: dict[str, float] = {}
    for _, func, weight in matched:
        score[func] = score.get(func, 0.0) + weight
    if score:
        function_type = max(score, key=lambda k: (score[k], -FUNCTION_TYPES.index(k)))
        top_weight = score[function_type]
        confidence = min(0.98, 0.55 + top_weight * 0.11)
    else:
        function_type = "data"
        top_weight = 0.0
        confidence = 0.35

    seniority = None
    for term, _, _ in matched:
        for key, level in SENIORITY_DICT.items():
            if key == term:
                seniority = level
                break
        if seniority:
            break
    if seniority is None:
        for key, level in SENIORITY_DICT.items():
            if key in cleaned:
                seniority = level
                break
    if seniority is None:
        seniority = _detect_seniority_from_years(experience_raw) or "mid"

    if seniority == "manager":
        canonical = MANAGER_TITLES[function_type]
    elif seniority == "director":
        canonical = DIRECTOR_TITLES[function_type]
    else:
        canonical = f"{SENIORITY_PREFIX[seniority]}{FUNCTION_CANONICAL[function_type]}"
    return TitleParseResult(
        canonical_title=canonical,
        function_type=function_type,
        seniority=seniority,
        confidence=round(confidence, 2),
        matched_terms=matched_terms,
    )


def ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    """字符 n-gram Jaccard 相似度（用于相似标题归并）。"""
    def grams(text: str) -> set[str]:
        compact = re.sub(r"\s+", "", text)
        if len(compact) < n:
            return {compact} if compact else set()
        return {compact[i : i + n] for i in range(len(compact) - n + 1)}

    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def batch_merge_titles(titles: list[str], threshold: float = NGRAM_MERGE_THRESHOLD) -> dict:
    """相似标题归并：3-gram Jaccard ≥ 0.8 归到已有 canonical，取频次最高写法。

    返回 {merged: [...], clusters: [{canonical, members, count}], threshold}。
    """
    normalized = [normalize_title(t) for t in titles]
    clusters: list[dict] = []
    merged: list[dict] = []
    for title, parsed in zip(titles, normalized):
        target = None
        for cluster in clusters:
            if ngram_jaccard(title, cluster["canonical"], n=3) >= threshold:
                target = cluster
                break
        if target is not None:
            target["members"].append(title)
            target["counter"][title] += 1
            merged.append({"from": title, "to": target["canonical"]})
        else:
            clusters.append(
                {
                    "canonical": title,
                    "members": [title],
                    "counter": Counter([title]),
                    "function_type": parsed.function_type,
                    "seniority": parsed.seniority,
                }
            )
    out = []
    for cluster in clusters:
        canonical, count = max(cluster["counter"].items(), key=lambda kv: kv[1])
        out.append(
            {
                "canonical": canonical,
                "members": cluster["members"],
                "count": count,
                "function_type": cluster["function_type"],
                "seniority": cluster["seniority"],
            }
        )
    return {
        "version": TITLE_DICT_VERSION,
        "threshold": threshold,
        "clusters": out,
        "merged": merged,
        "merged_count": len(merged),
    }
