# -*- coding: utf-8 -*-
"""
人工小批量筛选 CNKI 候选。

用途：
1. 只抓每个查询前几页（默认 1-2 页）
2. 只看指定类别
3. 输出候选清单，人工检查 keep / reject
4. 不直接写入数据库，避免污染现有数据
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


CNKI_API = "https://search.cnki.com.cn/api/search/listresult"
USER_AGENT = "Mozilla/5.0"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PAPERS_JSON = DATA_DIR / "papers_clean.json"
OUT_JSON = DATA_DIR / "manual_review_candidates.json"


TARGET_QUERIES = {
    "运输与储存安全类": [
        ("危险化学品道路运输安全", "14"),
        ("危险化学品储存安全", "14"),
    ],
    "事故分析与应急类": [
        ("化工事故应急", "14"),
        ("危险化学品事故应急", "14"),
    ],
    "职业卫生健康类": [
        ("化工职业卫生", "14"),
        ("化工职业健康", "14"),
    ],
}


CHEMICAL_TOKENS = [
    "化工", "石化", "石油化工", "危险化学品", "危化品", "化学品",
    "储罐", "罐区", "仓储", "化工企业", "化工园区",
]

SAFETY_TOKENS = [
    "安全", "风险", "应急", "事故", "泄漏", "爆炸", "火灾",
    "职业卫生", "职业健康", "暴露", "中毒", "救援", "监测",
]

REJECT_PATTERNS = [
    r"征稿",
    r"会议通知",
    r"会议纪要",
    r"关于召开",
    r"高校",
    r"教学",
    r"食品安全",
    r"网络安全",
    r"国家安全",
    r"校园",
    r"护理",
    r"药品",
    r"地点.{0,6}化工管理",
]


def load_existing_titles() -> set[str]:
    if not PAPERS_JSON.exists():
        return set()
    data = json.loads(PAPERS_JSON.read_text(encoding="utf-8"))
    return {str(p.get("title", "")).strip() for p in data.get("papers", []) if p.get("title")}


def fetch_cnki(theme: str, page: int, article_type: str) -> dict:
    body = urllib.parse.urlencode({
        "Theme": theme,
        "Order": "1",
        "Page": str(page),
        "ArticleType": article_type,
        "Type": article_type if article_type != "0" else "",
        "ReSearch": "",
    }).encode("utf-8")
    req = urllib.request.Request(
        CNKI_API,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("~#@", "").replace("@#~", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_source_url(item: dict, query: str) -> str:
    db_type = item.get("dbType", "")
    file_name = item.get("fileName", "")
    db_name = item.get("dbName", "")
    publish_code = item.get("publishCode", "")
    if db_type == "CJFD" and file_name:
        return f"https://www.cnki.com.cn/Article/CJFDTOTAL-{file_name}.htm"
    if db_type in {"CMFD", "CDFD", "CDMD"} and file_name and publish_code:
        return f"https://cdmd.cnki.com.cn/Article/CDMD-{publish_code}-{file_name.replace('.nh', '')}.htm"
    if db_type == "CPFD" and file_name:
        return f"https://cpfd.cnki.com.cn/Article/CPFDTOTAL-{file_name}.htm"
    if db_type == "IPFD" and file_name and db_name:
        return f"https://www.cnki.net/KCMS/detail/detail.aspx?dbcode=IPFD&filename={file_name}&dbname={db_name}"
    return f"https://search.cnki.com.cn/Search/Result?theme={urllib.parse.quote(query)}"


def auto_review(title: str, summary: str) -> tuple[str, str]:
    text = f"{title} {summary}"
    if not any(token in text for token in CHEMICAL_TOKENS):
        return "reject", "缺少化工/危化品领域词"
    if not any(token in text for token in SAFETY_TOKENS):
        return "reject", "缺少安全/应急/职业卫生主题词"
    for pattern in REJECT_PATTERNS:
        if re.search(pattern, text):
            return "reject", f"命中过滤词: {pattern}"
    if "管理" in title and "安全" not in title and "应急" not in title and "职业" not in title:
        return "reject", "偏化工管理/非安全主题"
    return "keep", "标题与摘要初筛相关"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    existing_titles = load_existing_titles()
    seen_titles: set[str] = set()
    out: list[dict] = []

    for category, query_pairs in TARGET_QUERIES.items():
        for query, article_type in query_pairs:
            for page in range(1, 2):
                payload = fetch_cnki(query, page, article_type)
                for item in payload.get("articleList", []):
                    title = clean_text(item.get("title", ""))
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)

                    summary = clean_text(item.get("summary", ""))[:500]
                    verdict, reason = auto_review(title, summary)
                    out.append({
                        "category": category,
                        "query": query,
                        "page": page,
                        "title": title,
                        "year": str(item.get("year", "")),
                        "dbType": item.get("dbType", ""),
                        "dbSource": item.get("dbSource", ""),
                        "summary": summary,
                        "source_url": build_source_url(item, query),
                        "already_in_db": title in existing_titles,
                        "verdict": verdict,
                        "reason": reason,
                    })

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(out)} candidates -> {OUT_JSON}")
    kept = [x for x in out if x["verdict"] == "keep" and not x["already_in_db"]]
    print(f"new keep candidates: {len(kept)}")
    for row in kept[:20]:
        print(f"[{row['category']}] {row['year']} {row['title']} | {row['dbType']} | {row['query']}")


if __name__ == "__main__":
    main()
