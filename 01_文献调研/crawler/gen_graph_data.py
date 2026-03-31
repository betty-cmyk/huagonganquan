# -*- coding: utf-8 -*-
"""
gen_graph_data.py  —  从 papers_clean.json 生成关联图所需的 graph.json
节点类型：
  - keyword（搜索词）
  - direction（研究方向）
  - year（年份）
边：keyword→direction, direction→year
"""
import os, json
from collections import defaultdict

DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
IN_JSON   = os.path.join(DATA_DIR, 'papers_clean.json')
OUT_JSON  = os.path.join(DATA_DIR, 'graph.json')

def main():
    with open(IN_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    papers = data['papers']

    # 统计
    kw_dir   = defaultdict(lambda: defaultdict(int))  # kw -> dir -> count
    dir_year = defaultdict(lambda: defaultdict(int))  # dir -> year -> count
    dir_cnt  = defaultdict(int)
    kw_cnt   = defaultdict(int)
    year_cnt = defaultdict(int)

    for p in papers:
        kw   = p.get('source_keyword', '未知')
        yr   = p.get('year', '')
        dirs = p.get('sub_direction', ['其他'])
        kw_cnt[kw] += 1
        if yr:
            year_cnt[yr] += 1
        for d in dirs:
            dir_cnt[d] += 1
            kw_dir[kw][d] += 1
            if yr:
                dir_year[d][yr] += 1

    nodes = []
    edges = []
    nid   = {}
    idx   = 0

    # 搜索词节点
    for kw, cnt in kw_cnt.items():
        nid[('kw', kw)] = idx
        nodes.append({'id': idx, 'label': kw, 'type': 'keyword', 'count': cnt})
        idx += 1

    # 方向节点
    for d, cnt in dir_cnt.items():
        nid[('dir', d)] = idx
        nodes.append({'id': idx, 'label': d, 'type': 'direction', 'count': cnt})
        idx += 1

    # 年份节点（只保留2015+)
    for yr, cnt in year_cnt.items():
        if yr.isdigit() and int(yr) >= 2015:
            nid[('yr', yr)] = idx
            nodes.append({'id': idx, 'label': yr, 'type': 'year', 'count': cnt})
            idx += 1

    # 边：搜索词 → 方向
    for kw, dirs in kw_dir.items():
        for d, w in dirs.items():
            if w >= 2:  # 至少2篇才连边
                edges.append({
                    'source': nid[('kw', kw)],
                    'target': nid[('dir', d)],
                    'weight': w,
                    'type': 'kw_dir'
                })

    # 边：方向 → 年份
    for d, yrs in dir_year.items():
        for yr, w in yrs.items():
            if yr.isdigit() and int(yr) >= 2015 and w >= 2:
                edges.append({
                    'source': nid[('dir', d)],
                    'target': nid[('yr', yr)],
                    'weight': w,
                    'type': 'dir_year'
                })

    graph = {'nodes': nodes, 'edges': edges}
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f'nodes: {len(nodes)}, edges: {len(edges)}')
    print(f'saved -> {OUT_JSON}')

if __name__ == '__main__':
    main()

