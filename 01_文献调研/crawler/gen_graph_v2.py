# -*- coding: utf-8 -*-
"""
gen_graph_v2.py  —  按科学分类体系生成关联图数据
分类体系：
  A. 风险评价类
  B. 灾害防控类
  C. 安全管理与体系类
  D. 安全技术与监测类
  E. 事故分析与应急类
  F. 安全科学基础理论类
  G. 职业卫生健康类
"""
import os, json, re
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
IN_JSON  = os.path.join(DATA_DIR, 'papers_clean.json')
OUT_JSON = os.path.join(DATA_DIR, 'graph_v2.json')

# ── 新分类体系 ────────────────────────────────────────────
CATEGORIES = {
    'A_风险评价': {
        'label': '风险评价类',
        'color': '#ff7b72',
        'keywords': ['风险评价', '安全评价', '风险评估', '安全评估', '风险分析',
                     '风险矩阵', 'AHP', 'HAZOP', '定量风险', '定性风险',
                     '风险管控', '风险等级', '风险分级', '隐患排查', '脆弱性'],
    },
    'B_灾害防控': {
        'label': '灾害防控类',
        'color': '#ffa657',
        'keywords': ['火灾', '爆炸', '泄漏', '中毒', '防火', '消防', '灭火',
                     '扩散', '泄漏扩散', '灾害', '防控', '防爆', '防泄漏',
                     '安全疏散', '火灾预防', '爆炸事故'],
    },
    'C_安全管理体系': {
        'label': '安全管理与体系类',
        'color': '#79c0ff',
        'keywords': ['安全管理', '安全文化', '安全生产管理', 'HSE', '双重预防',
                     '安全责任', '管理体系', '安全体系', '安全制度', '安全监管',
                     '监管体系', '监管机制', '监管现状', '监管对策', '安全监督',
                     '监管问题', '监管模式', '安全生产'],
    },
    'D_安全技术监测': {
        'label': '安全技术与监测类',
        'color': '#56d364',
        'keywords': ['物联网', '信息化', '数字化', '智能监管', '监控系统',
                     'GPS', '大数据', '人工智能', '机器学习', '深度学习',
                     '知识图谱', '机器视觉', '预警系统', '监测', '智能化',
                     '传感器', '巡检', '检测系统'],
    },
    'E_事故应急': {
        'label': '事故分析与应急类',
        'color': '#d2a8ff',
        'keywords': ['事故分析', '事故原因', '事故致因', '事故调查', '应急',
                     '应急处置', '应急预案', '应急救援', '应急能力', '应急管理',
                     '事故演化', '事故对策', '事故预防', '应急体系', '应急演练'],
    },
    'F_基础理论': {
        'label': '安全科学基础理论类',
        'color': '#e3b341',
        'keywords': ['安全理论', '安全原理', '安全科学', '安全行为', '不安全行为',
                     '安全心理', '安全意识', '行为安全', '安全系统', '本质安全',
                     '安全评价理论', '事故机理', '灾害机理'],
    },
    'G_职业卫生': {
        'label': '职业卫生健康类',
        'color': '#f0883e',
        'keywords': ['职业卫生', '职业健康', '职业病', '职业暴露', '有毒有害',
                     '粉尘', '噪声', '职业危害', '职业安全健康', '劳动保护'],
    },
    'H_运输储存': {
        'label': '运输与储存安全类',
        'color': '#76e3ea',
        'keywords': ['运输安全', '道路运输', '危险品运输', '危化品运输', '押运',
                     '储存安全', '储罐', '仓储', '危险品储存', '运输监管',
                     '运输风险', '路径优化', '运输许可'],
    },
    'I_园区企业': {
        'label': '园区与企业安全类',
        'color': '#89d4f5',
        'keywords': ['化工园区', '园区安全', '园区风险', '园区监管',
                     '企业安全', '安全绩效', '安全投入', '中小企业安全'],
    },
}


def classify_paper(title, keywords=''):
    text = title + ' ' + keywords
    matched = []
    for cat_id, cat in CATEGORIES.items():
        for kw in cat['keywords']:
            if kw in text:
                matched.append(cat_id)
                break
    return matched if matched else ['Z_其他']


def main():
    with open(IN_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    papers = data['papers']

    # 重新分类
    for p in papers:
        p['category'] = classify_paper(p['title'], p.get('keywords', ''))

    # 统计
    cat_papers  = defaultdict(list)   # category -> [paper]
    cat_year    = defaultdict(lambda: defaultdict(list))  # category -> year -> [paper]
    kw_cat      = defaultdict(lambda: defaultdict(list))  # source_kw -> cat -> [paper]

    for p in papers:
        yr  = p.get('year', '')
        skw = p.get('source_keyword', '未知')
        for cat in p['category']:
            cat_papers[cat].append(p)
            if yr and yr.isdigit() and int(yr) >= 2015:
                cat_year[cat][yr].append(p)
            kw_cat[skw][cat].append(p)

    nodes = []
    edges = []
    nid   = {}
    idx   = 0

    # ── 搜索词节点 ────────────────────────────────────────
    kw_cnt = defaultdict(int)
    for p in papers:
        kw_cnt[p.get('source_keyword','未知')] += 1

    for kw, cnt in kw_cnt.items():
        nid[('kw', kw)] = idx
        nodes.append({
            'id': idx, 'label': kw, 'type': 'keyword',
            'count': cnt, 'color': '#f78166',
            'papers': []  # 搜索词节点不单独列论文
        })
        idx += 1

    # ── 分类节点 ──────────────────────────────────────────
    for cat_id, plist in sorted(cat_papers.items(), key=lambda x: -len(x[1])):
        cat_info = CATEGORIES.get(cat_id, {'label': cat_id, 'color': '#8b949e'})
        nid[('cat', cat_id)] = idx
        nodes.append({
            'id':    idx,
            'label': cat_info['label'],
            'type':  'category',
            'cat_id': cat_id,
            'count': len(plist),
            'color': cat_info['color'],
            'papers': [{
                'title':  p['title'],
                'author': p.get('author',''),
                'unit':   p.get('unit',''),
                'year':   p.get('year',''),
                'keywords': p.get('keywords','')
            } for p in plist]
        })
        idx += 1

    # ── 年份节点 ──────────────────────────────────────────
    all_years = set()
    for p in papers:
        yr = p.get('year','')
        if yr and yr.isdigit() and int(yr) >= 2015:
            all_years.add(yr)

    yr_cnt = defaultdict(int)
    for p in papers:
        yr = p.get('year','')
        if yr in all_years:
            yr_cnt[yr] += 1

    yr_papers = defaultdict(list)
    for p in papers:
        yr = p.get('year','')
        if yr in all_years:
            yr_papers[yr].append(p)

    for yr in sorted(all_years):
        nid[('yr', yr)] = idx
        nodes.append({
            'id': idx, 'label': yr, 'type': 'year',
            'count': yr_cnt[yr], 'color': '#56d364',
            'papers': [{
                'title': p['title'], 'year': p.get('year',''),
                'author': p.get('author','')
            } for p in yr_papers[yr]]
        })
        idx += 1

    # ── 边：搜索词 → 分类 ─────────────────────────────────
    for skw, cats in kw_cat.items():
        for cat, plist in cats.items():
            if len(plist) >= 1:
                edges.append({
                    'source': nid[('kw', skw)],
                    'target': nid[('cat', cat)],
                    'weight': len(plist),
                    'type': 'kw_cat'
                })

    # ── 边：分类 → 年份 ───────────────────────────────────
    for cat, yrs in cat_year.items():
        for yr, plist in yrs.items():
            if len(plist) >= 2:
                edges.append({
                    'source': nid[('cat', cat)],
                    'target': nid[('yr', yr)],
                    'weight': len(plist),
                    'type': 'cat_year'
                })

    graph = {'nodes': nodes, 'edges': edges, 'total': len(papers)}
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f'nodes: {len(nodes)}, edges: {len(edges)}')

    # 打印分类统计
    print('\n=== 新分类体系统计 ===')
    for cat_id, plist in sorted(cat_papers.items(), key=lambda x: -len(x[1])):
        label = CATEGORIES.get(cat_id, {}).get('label', cat_id)
        print(f'  {label}: {len(plist)} 篇')
    print(f'  其他: {len(cat_papers.get("Z_其他",[]))} 篇')

if __name__ == '__main__':
    main()

