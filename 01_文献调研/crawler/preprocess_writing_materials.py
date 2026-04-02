# -*- coding: utf-8 -*-
"""
preprocess_writing_materials.py
论文写作材料预处理：按章节分桶 + 证据卡片生成
"""

import json
import os
import re
from collections import defaultdict

CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CRAWLER_DIR, '..', 'data')
IN_JSON = os.path.join(DATA_DIR, 'papers_clean.json')
OUT_BUCKETS = os.path.join(DATA_DIR, 'writing_materials.json')
OUT_CARDS = os.path.join(DATA_DIR, 'evidence_cards.json')


CHAPTER_RULES = [
    ('2.1 危化品运输安全监管现状', ['监管现状', '安全监管', '监管体系', '监管机制', '监管']),
    ('2.2.1 监管主体协同不足', ['协同', '多部门', '联动', '协作', '信息共享']),
    ('2.2.2 全链条管控漏洞', ['运输', '储存', '装卸', '物流', '路径', '全链条']),
    ('2.2.3 从业人员素质与安全意识', ['人员', '从业人员', '培训', '行为', '意识', '素质']),
    ('2.2.4 技术应用与智能化不足', ['智能', '监测', '预警', '物联网', '大数据', '人工智能', '信息化']),
    ('2.2.5 应急处置体系不足', ['应急', '救援', '预案', '事故处置', '应急管理']),
    ('3.1 强化部门协同与监管机制', ['协同', '机制', '制度', '责任', '监管机制']),
    ('3.2 加强全链条管控', ['全链条', '运输', '储存', '装卸', '流程', '管控']),
    ('3.3 提升人员素质与安全文化', ['培训', '安全文化', '人员', '意识', '能力提升']),
    ('3.4 推进技术创新与智能监管', ['智能监管', '预警系统', '监测系统', '数字化', '技术创新']),
    ('3.5 完善应急处置体系', ['应急体系', '应急能力', '应急预案', '应急处置']),
]

CATEGORY_FALLBACK = {
    '运输与储存安全类': '2.2.2 全链条管控漏洞',
    '事故分析与应急类': '2.2.5 应急处置体系不足',
    '安全技术与监测类': '2.2.4 技术应用与智能化不足',
    '安全管理与体系类': '2.1 危化品运输安全监管现状',
    '职业卫生健康类': '2.2.3 从业人员素质与安全意识',
    '园区与企业安全类': '2.2.1 监管主体协同不足',
    '风险评价类': '2.1 危化品运输安全监管现状',
    '工艺安全类': '2.1 危化品运输安全监管现状',
}


def clean_text(s):
    s = str(s or '')
    s = s.replace('\u3000', ' ').replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def split_sentences(s):
    text = clean_text(s)
    if not text:
        return []
    parts = re.split(r'[。！？；;.!?]+', text)
    return [p.strip() for p in parts if len(p.strip()) >= 12]


def pick_chapter(paper):
    text = ' '.join([
        clean_text(paper.get('title')),
        clean_text(paper.get('keywords')),
        clean_text(paper.get('abstract')),
    ])

    scores = []
    for chapter, kws in CHAPTER_RULES:
        score = sum(1 for kw in kws if kw in text)
        if score > 0:
            scores.append((chapter, score))

    if scores:
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    cat = clean_text(paper.get('category_9'))
    return CATEGORY_FALLBACK.get(cat, '2.1 危化品运输安全监管现状')


def build_evidence(paper, chapter):
    title = clean_text(paper.get('title'))
    abstract = clean_text(paper.get('abstract'))
    keywords = [k.strip() for k in re.split(r'[，,;；、\s]+', clean_text(paper.get('keywords'))) if k.strip()]

    chapter_kws = []
    for c, kws in CHAPTER_RULES:
        if c == chapter:
            chapter_kws = kws
            break

    sents = split_sentences(abstract)
    hit = ''
    for sent in sents:
        if any(kw in sent for kw in chapter_kws):
            hit = sent
            break

    if not hit and sents:
        hit = sents[0]
    if not hit:
        hit = abstract[:180] if abstract else '暂无摘要句证据。'

    card = {
        'chapter': chapter,
        'title': title,
        'year': paper.get('year'),
        'author': clean_text(paper.get('author')),
        'unit': clean_text(paper.get('unit')),
        'keywords': keywords[:8],
        'evidence_sentence': hit,
        'source_url': clean_text(paper.get('source_url') or paper.get('url')),
    }
    return card


def main():
    with open(IN_JSON, 'r', encoding='utf-8') as f:
        all_papers = json.load(f).get('papers', [])

    papers = all_papers

    buckets = defaultdict(list)
    cards = []

    for p in papers:
        chapter = pick_chapter(p)
        card = build_evidence(p, chapter)
        buckets[chapter].append({
            'title': card['title'],
            'year': card['year'],
            'author': card['author'],
            'unit': card['unit'],
            'source_url': card['source_url'],
            'evidence_sentence': card['evidence_sentence'],
        })
        cards.append(card)

    ordered = []
    for chapter, _ in CHAPTER_RULES:
        items = buckets.get(chapter, [])
        items.sort(key=lambda x: str(x.get('year', '')), reverse=True)
        ordered.append({
            'chapter': chapter,
            'count': len(items),
            'papers': items,
        })

    with open(OUT_BUCKETS, 'w', encoding='utf-8') as f:
        json.dump({
            'total_papers': len(papers),
            'total_all': len(all_papers),
            'excluded_low_quality': len(all_papers) - len(papers),
            'chapters': ordered
        }, f, ensure_ascii=False, indent=2)

    cards.sort(key=lambda x: (x['chapter'], str(x.get('year', ''))), reverse=False)
    with open(OUT_CARDS, 'w', encoding='utf-8') as f:
        json.dump({'total_cards': len(cards), 'cards': cards}, f, ensure_ascii=False, indent=2)

    non_empty = sum(1 for c in ordered if c['count'] > 0)
    excluded = len(all_papers) - len(papers)
    print(f'total_papers={len(papers)}')
    print(f'excluded_low_quality={excluded}')
    print(f'chapters_with_materials={non_empty}')
    print(f'cards={len(cards)}')
    print(f'written={OUT_BUCKETS}')
    print(f'written={OUT_CARDS}')


if __name__ == '__main__':
    main()

