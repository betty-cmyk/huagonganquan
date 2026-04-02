# -*- coding: utf-8 -*-
"""
clean_papers.py
清洗 papers_clean.json：去重、去乱码标题、过滤异常年份、过滤空标题
"""

import json
import os
import re
from datetime import datetime

CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CRAWLER_DIR, '..', 'data')
PAPERS_CLEAN_JSON = os.path.join(DATA_DIR, 'papers_clean.json')


def norm_text(v):
    return str(v or '').strip()


def norm_title(v):
    s = norm_text(v)
    s = re.sub(r'\s+', '', s)
    return s


def norm_unit(v):
    s = norm_text(v).replace('\u3000', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s


def year_valid(v):
    s = norm_text(v)
    if not s:
        return False
    if not re.fullmatch(r'\d{4}', s):
        return False
    y = int(s)
    return 1990 <= y <= datetime.now().year + 1


def paper_score(p):
    score = 0
    if norm_text(p.get('source_url') or p.get('url')):
        score += 2
    if norm_text(p.get('unit')):
        score += 1
    if norm_text(p.get('keywords')):
        score += 1
    score += min(len(norm_text(p.get('abstract'))) // 120, 5)
    return score


def main():
    with open(PAPERS_CLEAN_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    papers = data.get('papers', [])

    total = len(papers)
    removed_empty_title = 0
    removed_garbled_title = 0
    removed_bad_year = 0

    # 1) 基础过滤
    filtered = []
    for p in papers:
        title = norm_text(p.get('title'))
        if not title:
            removed_empty_title += 1
            continue

        if re.search(r'\?{2,}', title):
            removed_garbled_title += 1
            continue

        year = norm_text(p.get('year'))
        if not year_valid(year):
            removed_bad_year += 1
            continue

        p['title'] = title
        p['unit'] = norm_unit(p.get('unit'))
        p['year'] = int(year)
        filtered.append(p)

    # 2) 去重（同标题保留信息更完整的一条）
    by_title = {}
    duplicate_count = 0

    for p in filtered:
        key = norm_title(p.get('title'))
        if key not in by_title:
            by_title[key] = p
            continue

        duplicate_count += 1
        old = by_title[key]
        if paper_score(p) > paper_score(old):
            by_title[key] = p

    cleaned = list(by_title.values())

    # 3) 重排 id
    for i, p in enumerate(cleaned, start=1):
        p['id'] = i

    data['papers'] = cleaned
    data['total'] = len(cleaned)

    with open(PAPERS_CLEAN_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'total_before={total}')
    print(f'removed_empty_title={removed_empty_title}')
    print(f'removed_garbled_title={removed_garbled_title}')
    print(f'removed_bad_year={removed_bad_year}')
    print(f'removed_duplicates={duplicate_count}')
    print(f'total_after={len(cleaned)}')


if __name__ == '__main__':
    main()

