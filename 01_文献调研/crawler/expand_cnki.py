# -*- coding: utf-8 -*-
"""
expand_cnki.py

从 CNKI 搜索接口批量补充化工安全相关文献，并尽量回填摘要。
优先处理用户给出的九类方向，统一写回 JSON / CSV / SQLite。
"""

import csv
import json
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
JSON_CLEAN = os.path.join(DATA_DIR, "papers_clean.json")
JSON_MERGED = os.path.join(DATA_DIR, "所有论文_merged.json")
CSV_PATH = os.path.join(DATA_DIR, "papers.csv")
DB_PATH = os.path.join(DATA_DIR, "papers.db")

CNKI_API = "https://search.cnki.com.cn/api/search/listresult"
USER_AGENT = "Mozilla/5.0"
MAX_PAGE_ALL = min(int(os.environ.get("CNKI_MAX_PAGE_ALL", "2")), 5)
MAX_PAGE_THESIS = min(int(os.environ.get("CNKI_MAX_PAGE_THESIS", "2")), 5)


CATEGORY_QUERIES: Dict[str, List[Tuple[str, str]]] = {
    "安全管理与体系类": [
        ("化工 安全管理", "0"),
        ("化工企业 HSE 管理体系", "0"),
        ("双重预防 化工", "0"),
        ("化工 安全管理", "14"),
    ],
    "运输与储存安全类": [
        ("危险化学品 运输 安全", "0"),
        ("危险化学品 储存 安全", "0"),
        ("危化品 道路运输 安全", "0"),
        ("危险化学品 储存 安全", "14"),
    ],
    "风险评价类": [
        ("化工 风险评价", "0"),
        ("化工园区 风险评估", "0"),
        ("HAZOP 化工", "0"),
        ("化工 风险评价", "14"),
    ],
    "安全技术与监测类": [
        ("化工 安全监测", "0"),
        ("化工 安全 预警 系统", "0"),
        ("物联网 化工 安全", "0"),
        ("化工 安全监测", "14"),
    ],
    "园区与企业安全类": [
        ("化工园区 安全", "0"),
        ("化工企业 安全", "0"),
        ("重大危险源 化工园区", "0"),
        ("化工园区 安全", "14"),
    ],
    "事故分析与应急类": [
        ("化工 事故 分析", "0"),
        ("化工 事故 应急", "0"),
        ("危险化学品 事故 应急", "0"),
        ("化工 事故 应急", "14"),
    ],
    "灾害防控类": [
        ("化工 火灾 爆炸 防控", "0"),
        ("化工 泄漏 扩散", "0"),
        ("化工 爆炸 防护", "0"),
        ("化工 火灾 爆炸 防控", "14"),
    ],
    "安全科学基础理论类": [
        ("安全科学 理论", "0"),
        ("事故致因 理论", "0"),
        ("风险评估 方法 安全", "0"),
        ("安全科学 理论 化工", "14"),
    ],
    "职业卫生健康类": [
        ("化工 职业卫生", "0"),
        ("化工 职业健康", "0"),
        ("化工 有毒有害 暴露", "0"),
        ("化工 职业卫生", "14"),
    ],
}


CHEMICAL_RELEVANT = [
    "化工", "石化", "石油化工", "危险化学品", "危化品", "化工园区",
    "储罐", "罐区", "油气", "天然气", "氢气", "甲醇", "火灾", "爆炸",
    "泄漏", "HSE", "安全生产", "重大危险源",
]

EXCLUDE_PATTERNS = [
    r"政协.*会议",
    r"会议.*决议",
    r"关于召开",
    r"换届会议",
    r"征稿",
    r"征稿简则",
    r"食品",
    r"药品",
    r"护理学会",
    r"自动扶梯",
    r"民事诉讼",
    r"检察应对",
    r"化工管理\b",
    r"^化工管理\s",
    r".{0,8}(省|市|县|区|镇|村).{0,10}(化工管理|化工分析|化工设计|化工工艺)",
    r".*(化工分析|化工设计|化工工艺).*(探讨|浅谈|简析)$",
]


def clean_markers(text: str) -> str:
    if not text:
        return ""
    text = text.replace("~#@", "").replace("@#~", "")
    text = text.replace(";;", ";")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_sub_direction(title: str, keywords: str = "") -> List[str]:
    text = f"{title} {keywords}"
    rules = [
        ("运输监管", ["运输监管", "道路运输", "公路运输", "押运", "运输许可"]),
        ("运输路径优化", ["路径优化", "路径规划", "选址", "VRP", "配送"]),
        ("运输风险评估", ["运输风险", "风险评估", "风险量化", "定量风险"]),
        ("储存安全", ["储存", "储罐", "仓储", "库区"]),
        ("应急处置", ["应急", "预案", "救援", "演练", "处置"]),
        ("事故分析", ["事故", "爆炸", "燃爆", "泄漏", "故障", "致因"]),
        ("安全监管体系", ["监管体系", "监管机制", "安全监管", "管理体系"]),
        ("园区安全管理", ["化工园区", "园区安全", "园区风险"]),
        ("企业安全管理", ["企业安全", "安全生产管理", "双重预防", "安全文化", "HSE"]),
        ("风险评价方法", ["风险评价", "安全评价", "HAZOP", "AHP", "TOPSIS", "矩阵", "QRA"]),
        ("人员安全行为", ["行为", "意识", "培训", "从业人员"]),
        ("智能化监管", ["物联网", "信息化", "数智化", "智能", "大数据", "传感", "预警系统"]),
        ("职业卫生健康", ["职业卫生", "职业病", "职业健康", "暴露"]),
    ]
    out = [name for name, kws in rules if any(kw in text for kw in kws)]
    return out if out else ["其他"]


def guess_degree(db_type: str, db_source: str) -> str:
    if db_type == "CMFD":
        return "硕士"
    if db_type in {"CDFD", "CDMD"}:
        return "博士"
    if db_source == "硕士":
        return "硕士"
    if db_source == "博士":
        return "博士"
    return ""


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


def is_relevant(item: dict) -> bool:
    title = clean_markers(item.get("title", ""))
    summary = clean_markers(item.get("summary", ""))
    text = f"{title} {summary}"
    if item.get("dbType") not in {"CJFD", "CMFD", "CDFD", "CDMD", "CPFD", "IPFD"}:
        return False
    if not any(token in text for token in CHEMICAL_RELEVANT):
        return False
    # 标题必须体现安全主题，避免把仅带“化工”的管理/分析类水文混进来
    safety_tokens = [
        "安全", "风险", "应急", "事故", "消防", "火灾", "爆炸", "泄漏", "职业卫生",
        "职业健康", "监测", "预警", "防控", "HSE", "双重预防", "重大危险源"
    ]
    if not any(token in title for token in safety_tokens):
        return False
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, text):
            return False
    return True


def fetch_cnki(theme: str, page: int, article_type: str) -> dict:
    body = urllib.parse.urlencode({
        "Theme": theme,
        "Order": "1",
        "Page": str(page),
        "ArticleType": str(article_type),
        "Type": str(article_type) if str(article_type) != "0" else "",
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


def to_record(item: dict, query: str, category: str) -> dict:
    title = clean_markers(item.get("title", ""))
    abstract = clean_markers(item.get("summary", ""))[:600]
    keywords = clean_markers(item.get("keyWord", "")).replace(";", " / ")
    db_type = item.get("dbType", "")
    db_source = item.get("dbSource", "")
    degree = guess_degree(db_type, db_source)
    return {
        "title": title,
        "author": clean_markers(item.get("author", "")).replace(";", " / "),
        "unit": "",
        "degree": degree,
        "year": str(item.get("year", "")),
        "abstract": abstract,
        "keywords": keywords,
        "direction": [category],
        "category_9": category,
        "source_keyword": f"联网补充_CNKI_{category}",
        "sub_direction": classify_sub_direction(title, keywords),
        "directions_str": " / ".join(classify_sub_direction(title, keywords)),
        "db_type": db_type,
        "db_source": db_source,
        "source_url": build_source_url(item, query),
        "source_site": "CNKI搜索API",
    }


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def ensure_defaults(paper: dict) -> None:
    paper.setdefault("abstract", "")
    paper.setdefault("keywords", "")
    paper.setdefault("category_9", classify_category_9(paper.get("title", ""), paper.get("keywords", "")))
    paper.setdefault("sub_direction", classify_sub_direction(paper.get("title", ""), paper.get("keywords", "")))
    paper.setdefault("directions_str", " / ".join(paper.get("sub_direction", ["其他"])))
    paper.setdefault("source_url", "")
    paper.setdefault("source_site", "")
    paper.setdefault("db_type", "")
    paper.setdefault("db_source", "")


def classify_category_9(title: str, keywords: str = "") -> str:
    text = f"{title} {keywords}"
    rules = [
        ("职业卫生健康类", ["职业卫生", "职业病", "职业健康", "有毒有害", "暴露"]),
        ("安全科学基础理论类", ["安全科学", "事故致因理论", "事故致因", "理论体系", "基础理论"]),
        ("灾害防控类", ["火灾", "爆炸", "爆轰", "泄漏扩散", "热失控", "防控", "灭火", "防护"]),
        ("事故分析与应急类", ["事故分析", "事故致因", "应急", "应急救援", "应急演练", "处置"]),
        ("安全技术与监测类", ["监测", "传感", "预警", "物联网", "智能", "红外", "控制系统", "数字孪生"]),
        ("风险评价类", ["风险评价", "风险评估", "安全评价", "HAZOP", "AHP", "QRA", "TOPSIS"]),
        ("运输与储存安全类", ["运输", "道路运输", "储存", "储罐", "仓储", "库区", "罐区"]),
        ("园区与企业安全类", ["化工园区", "园区安全", "企业安全", "重大危险源"]),
        ("安全管理与体系类", ["安全管理", "管理体系", "HSE", "双重预防", "安全文化", "监管"]),
    ]
    for category, kws in rules:
        if any(kw in text for kw in kws):
            return category
    return "安全管理与体系类"


def rewrite_csv(papers: List[dict]) -> None:
    fieldnames = [
        "title", "author", "unit", "degree", "year", "abstract", "keywords",
        "category_9", "directions_str", "source_keyword", "db_type", "db_source",
        "source_url", "source_site",
    ]
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in papers:
            writer.writerow({k: p.get(k, "") for k in fieldnames})


def rewrite_db(papers: List[dict]) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(papers)")
    cols = {row[1] for row in cur.fetchall()}
    if "abstract" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN abstract TEXT")
    if "category_9" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN category_9 TEXT")
    if "db_type" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN db_type TEXT")
    if "db_source" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN db_source TEXT")
    if "source_url" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN source_url TEXT")
    if "source_site" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN source_site TEXT")

    cur.execute("DELETE FROM paper_directions")
    for p in papers:
        cur.execute(
            """
            UPDATE papers
            SET author=?, unit=?, degree=?, year=?, abstract=?, keywords=?, category_9=?,
                directions=?, source_kw=?, db_type=?, db_source=?, source_url=?, source_site=?
            WHERE title=?
            """,
            (
                p.get("author", ""),
                p.get("unit", ""),
                p.get("degree", ""),
                int(p["year"]) if str(p.get("year", "")).isdigit() else 0,
                p.get("abstract", ""),
                p.get("keywords", ""),
                p.get("category_9", ""),
                p.get("directions_str", ""),
                p.get("source_keyword", ""),
                p.get("db_type", ""),
                p.get("db_source", ""),
                p.get("source_url", ""),
                p.get("source_site", ""),
                p["title"],
            ),
        )
        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO papers
                (title, author, unit, degree, year, abstract, keywords, category_9,
                 directions, source_kw, db_type, db_source, source_url, source_site)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    p["title"],
                    p.get("author", ""),
                    p.get("unit", ""),
                    p.get("degree", ""),
                    int(p["year"]) if str(p.get("year", "")).isdigit() else 0,
                    p.get("abstract", ""),
                    p.get("keywords", ""),
                    p.get("category_9", ""),
                    p.get("directions_str", ""),
                    p.get("source_keyword", ""),
                    p.get("db_type", ""),
                    p.get("db_source", ""),
                    p.get("source_url", ""),
                    p.get("source_site", ""),
                ),
            )

    cur.execute("SELECT id, title FROM papers")
    id_map = {title: pid for pid, title in cur.fetchall()}
    for p in papers:
        pid = id_map.get(p["title"])
        if not pid:
            continue
        for direction in p.get("sub_direction", ["其他"]):
            cur.execute("INSERT INTO paper_directions (paper_id, direction) VALUES (?, ?)", (pid, direction))

    conn.commit()
    conn.close()


def persist(clean_data: dict, merged_data: dict, clean_papers: List[dict]) -> None:
    clean_data["total"] = len(clean_papers)
    merged_data["total"] = len(merged_data["papers"])
    save_json(JSON_CLEAN, clean_data)
    save_json(JSON_MERGED, merged_data)
    rewrite_csv(clean_papers)
    rewrite_db(clean_papers)


def main() -> None:
    clean_data = load_json(JSON_CLEAN)
    merged_data = load_json(JSON_MERGED)
    clean_papers = clean_data["papers"]
    merged_papers = merged_data["papers"]

    title_to_clean = {p["title"]: p for p in clean_papers}
    title_to_merged = {p["title"]: p for p in merged_papers}

    for p in clean_papers:
        ensure_defaults(p)
    for p in merged_papers:
        ensure_defaults(p)

    added_by_category = {name: 0 for name in CATEGORY_QUERIES}
    abstract_updated = 0

    for category, query_pairs in CATEGORY_QUERIES.items():
        category_added = 0
        category_abstracts = 0
        print(f"\n处理分类: {category}", flush=True)
        for query, article_type in query_pairs:
            max_page = MAX_PAGE_THESIS if article_type == "14" else MAX_PAGE_ALL
            for page in range(1, max_page + 1):
                print(f"  查询: {query} | 类型: {article_type} | 第{page}页", flush=True)
                payload = fetch_cnki(query, page, article_type)
                for item in payload.get("articleList", []):
                    if not is_relevant(item):
                        continue
                    rec = to_record(item, query, category)
                    title = rec["title"]
                    if not title:
                        continue

                    if title in title_to_clean:
                        existing = title_to_clean[title]
                        before = str(existing.get("abstract", "")).strip()
                        if not before and rec.get("abstract"):
                            existing["abstract"] = rec["abstract"]
                            existing["source_url"] = existing.get("source_url", "") or rec["source_url"]
                            existing["source_site"] = existing.get("source_site", "") or rec["source_site"]
                            existing["db_type"] = existing.get("db_type", "") or rec["db_type"]
                            existing["db_source"] = existing.get("db_source", "") or rec["db_source"]
                            existing["category_9"] = existing.get("category_9", "") or category
                            if title in title_to_merged:
                                title_to_merged[title].update(existing)
                            abstract_updated += 1
                            category_abstracts += 1
                        continue

                    clean_papers.append(rec)
                    merged_papers.append(dict(rec))
                    title_to_clean[title] = clean_papers[-1]
                    title_to_merged[title] = merged_papers[-1]
                    added_by_category[category] += 1
                    category_added += 1

                time.sleep(0.05)

        persist(clean_data, merged_data, clean_papers)
        print(f"  分类完成: 新增 {category_added}，回填摘要 {category_abstracts}", flush=True)

    for p in clean_papers:
        ensure_defaults(p)
    for p in merged_papers:
        ensure_defaults(p)

    persist(clean_data, merged_data, clean_papers)

    print("新增条数:")
    for category, count in added_by_category.items():
        print(f"{category}: {count}")
    print(f"回填摘要: {abstract_updated}")
    print(f"当前总数: {len(clean_papers)}")


if __name__ == "__main__":
    main()
