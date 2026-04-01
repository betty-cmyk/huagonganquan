# -*- coding: utf-8 -*-
"""
gen_graph_v4.py  —  仅研究分类视图：无“其他”类，分类锚点 + 论文网络
"""
import os
import re
import json
from collections import defaultdict
from itertools import combinations

CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CRAWLER_DIR, '..', 'data')
IN_JSON = os.path.join(DATA_DIR, 'papers_clean.json')
OUT_JSON = os.path.join(DATA_DIR, 'graph_v3.json')

CATEGORIES = {
    'A_风险评价': {'label': '风险评价类', 'color': '#ff7b72'},
    'B_灾害防控': {'label': '灾害防控类', 'color': '#ffa657'},
    'C_安全管理体系': {'label': '安全管理与体系类', 'color': '#79c0ff'},
    'D_安全技术监测': {'label': '安全技术与监测类', 'color': '#56d364'},
    'E_事故应急': {'label': '事故分析与应急类', 'color': '#d2a8ff'},
    'F_基础理论': {'label': '安全科学基础理论类', 'color': '#e3b341'},
    'G_职业卫生': {'label': '职业卫生健康类', 'color': '#f0883e'},
    'H_运输储存': {'label': '运输与储存安全类', 'color': '#76e3ea'},
    'I_园区企业': {'label': '园区与企业安全类', 'color': '#89d4f5'},
    'J_工艺安全': {'label': '工艺安全类', 'color': '#6e7681'},
}

CLASSIFY_KWS = {
    'A_风险评价': ['风险评价', '安全评价', '风险评估', '安全评估', '风险分析', '风险矩阵', 'AHP', 'HAZOP', '定量风险', '风险管控', '风险等级', '隐患排查', '脆弱性'],
    'B_灾害防控': ['火灾', '爆炸', '泄漏', '中毒', '防火', '消防', '灭火', '扩散', '灾害', '防控', '安全疏散'],
    'C_安全管理体系': ['安全管理', '安全文化', '安全生产管理', 'HSE', '双重预防', '安全责任', '管理体系', '安全体系', '安全制度', '安全监管', '监管体系', '监管机制', '监管现状', '监管对策', '安全监督', '安全生产'],
    'D_安全技术监测': ['物联网', '信息化', '数字化', '智能监管', '监控系统', 'GPS', '大数据', '人工智能', '机器学习', '深度学习', '知识图谱', '机器视觉', '预警系统', '监测', '智能化', '云平台', '信息系统'],
    'E_事故应急': ['事故分析', '事故原因', '事故致因', '事故调查', '应急', '应急处置', '应急预案', '应急救援', '应急能力', '应急管理', '事故演化', '事故对策', '事故预防', '应急体系', '演化机理', '后果分析'],
    'F_基础理论': ['安全理论', '安全原理', '安全科学', '安全行为', '不安全行为', '安全心理', '安全意识', '本质安全', '事故机理', '人因', '安全素质', '安全投入'],
    'G_职业卫生': ['职业卫生', '职业健康', '职业病', '职业暴露', '粉尘', '噪声', '职业危害', '职业安全健康', '中毒', '防护用品'],
    'H_运输储存': ['运输安全', '道路运输', '危险品运输', '危化品运输', '押运', '储存安全', '储罐', '仓储', '危险品储存', '运输监管', '运输风险', '路径优化', '物流', '码头', '装卸'],
    'I_园区企业': ['化工园区', '园区安全', '园区风险', '企业安全', '安全绩效', '中小企业', '小微企业'],
    'J_工艺安全': ['工艺安全', '反应热', '热失控', '精细化工', '催化', '加氢', '聚合', '氧化', '化工工艺'],
}

FALLBACK_RULES = [
    ('园区', 'I_园区企业'), ('企业', 'I_园区企业'), ('应急', 'E_事故应急'),
    ('事故', 'E_事故应急'), ('运输', 'H_运输储存'), ('储存', 'H_运输储存'),
    ('监测', 'D_安全技术监测'), ('预警', 'D_安全技术监测'), ('职业', 'G_职业卫生'),
    ('火灾', 'B_灾害防控'), ('爆炸', 'B_灾害防控'), ('风险', 'A_风险评价'),
    ('评价', 'A_风险评价'), ('工艺', 'J_工艺安全'), ('反应', 'J_工艺安全'),
]


def classify_multi(title, keywords=''):
    text = (title or '') + ' ' + (keywords or '')
    matched = []
    for cat_id, kws in CLASSIFY_KWS.items():
        if any(kw in text for kw in kws):
            matched.append(cat_id)

    if matched:
        return matched

    for kw, cat_id in FALLBACK_RULES:
        if kw in text:
            return [cat_id]

    # 不保留“其他”类：兜底归入管理与体系类
    return ['C_安全管理体系']


def main():
    with open(IN_JSON, 'r', encoding='utf-8') as f:
        papers = json.load(f)['papers']

    nodes = []
    edges = []
    idx = 0
    cat_node_id = {}
    cat_links = {}

    for cat_id, cat_info in CATEGORIES.items():
        cat_node_id[cat_id] = idx
        nodes.append({
            'id': idx,
            'cat_id': cat_id,
            'label': cat_info['label'],
            'type': 'category',
            'color': cat_info['color'],
            'count': 0,
            'r': 10,
            'papers': []
        })
        idx += 1

    for p in papers:
        cats = classify_multi(p.get('title', ''), p.get('keywords', ''))
        primary = cats[0]
        pid = idx
        nodes.append({
            'id': pid,
            'label': (p.get('title', '')[:15] + '...') if len(p.get('title', '')) > 15 else p.get('title', ''),
            'full_title': p.get('title', ''),
            'type': 'paper',
            'color': CATEGORIES[primary]['color'],
            'count': 1,
            'r': 4,
            'primary_category': primary,
            'categories': cats,
            'year': p.get('year', ''),
            'author': p.get('author', ''),
            'unit': p.get('unit', ''),
            'keywords': p.get('keywords', ''),
            'abstract': p.get('abstract', ''),
            'outline': p.get('outline', '')
        })
        idx += 1

        for c_id in cats:
            c_idx = cat_node_id[c_id]
            nodes[c_idx]['count'] += 1
            nodes[c_idx]['papers'].append({'title': p.get('title', ''), 'year': p.get('year', '')})
            edges.append({'source': pid, 'target': c_idx, 'weight': 1, 'type': 'paper_cat'})

        if len(cats) > 1:
            cc = sorted(cats)
            for i in range(len(cc)):
                for j in range(i + 1, len(cc)):
                    key = (cc[i], cc[j])
                    cat_links[key] = cat_links.get(key, 0) + 1

    for (c1, c2), weight in cat_links.items():
        edges.append({
            'source': cat_node_id[c1],
            'target': cat_node_id[c2],
            'weight': weight * 4,
            'type': 'cat_cat'
        })

    graph = {'nodes': nodes, 'edges': edges, 'total': len(papers)}
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"Nodes: {len(nodes)}, Edges: {len(edges)}, Cross-links: {len(cat_links)}")


if __name__ == '__main__':
    main()
