# -*- coding: utf-8 -*-
"""
import_candidates.py  —  把 manual_review_candidates.json 中 verdict=keep 的新论文
导入 papers_clean.json，然后重新生成图并部署
"""
import os, json, subprocess, sys
from pathlib import Path

CRAWLER_DIR = Path(__file__).resolve().parent
DATA_DIR    = CRAWLER_DIR.parent / 'data'
CAND_JSON   = DATA_DIR / 'manual_review_candidates.json'
CLEAN_JSON  = DATA_DIR / 'papers_clean.json'

# 新论文的细分方向映射
CAT_MAP = {
    '运输与储存安全类': ['运输与储存安全类'],
    '事故分析与应急类': ['事故分析与应急类'],
    '职业卫生健康类':   ['职业卫生健康类'],
}

def main():
    cands = json.loads(CAND_JSON.read_text(encoding='utf-8'))
    clean = json.loads(CLEAN_JSON.read_text(encoding='utf-8'))
    existing = {p['title'].strip() for p in clean['papers']}

    new_papers = []
    for c in cands:
        if c.get('verdict') != 'keep':
            continue
        title = c.get('title','').strip()
        if not title or title in existing:
            continue
        cat = c.get('category', '其他')
        new_papers.append({
            'title':          title,
            'author':         '',
            'unit':           '',
            'degree':         '硕士',
            'year':           str(c.get('year', '')),
            'keywords':       '',
            'abstract':       c.get('summary', '')[:200],
            'direction':      CAT_MAP.get(cat, ['其他']),
            'source_keyword': cat,
            'sub_direction':  CAT_MAP.get(cat, ['其他']),
            'directions_str': cat,
            'category':       CAT_MAP.get(cat, ['其他']),
        })
        existing.add(title)

    print(f'新增论文：{len(new_papers)} 篇')
    clean['papers'].extend(new_papers)
    clean['total'] = len(clean['papers'])
    CLEAN_JSON.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f'papers_clean.json 现有：{clean["total"]} 篇')

    # 重新生成图和网站
    for script in ['gen_graph_v2.py', 'build_site.py']:
        print(f'运行 {script}...')
        subprocess.run([sys.executable, str(CRAWLER_DIR / script)], check=True)

    print('完成！')

if __name__ == '__main__':
    main()

