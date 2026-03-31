# -*- coding: utf-8 -*-
"""
build_db.py
读取 所有论文_merged.json，过滤无意义标题，写入 SQLite + CSV
"""
import os, json, re, csv, sqlite3

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
JSON_IN  = os.path.join(DATA_DIR, '所有论文_merged.json')
DB_PATH  = os.path.join(DATA_DIR, 'papers.db')
CSV_PATH = os.path.join(DATA_DIR, 'papers.csv')

# ── 无意义标题过滤规则 ────────────────────────────────────
# 1. 纯「地名/机构名 + 搜索词」模式
# 2. 纯企业战略/财务/供应链（与安全无关）
FILTER_PATTERNS = [
    r'^[A-Z]{1,3}(化工|石化|煤化工).{0,6}(战略|成本|盈利|供应链|财务|绩效|并购|贸易|竞争)',
    r'^(\w{2,6}市|\w{2,4}省|\w{2,4}县|\w{2,4}区|\w{2,4}园).{0,4}(化工|石化).{0,6}(战略|成本|盈利|供应链|贸易)',
    r'(供应链优化|O2O|发展战略|盈利能力|财务绩效|创新链|产业链耦合|竞争战略|存货内部控制|成本管理|跨国并购)',
    r'^(中俄|中美).{0,10}(贸易|产品)',
    r'(BIM技术.*施工进度|管道焊接.*质量控制|ESG视角)',
    r'^基于Modelica',  # 纯化工仿真软件
    r'(舆情分析|O2O供应链|杜邦分析体系)',
]

FILTER_RE = [re.compile(p) for p in FILTER_PATTERNS]


def is_meaningful(paper):
    title = paper.get('title', '')
    for pat in FILTER_RE:
        if pat.search(title):
            return False
    return True


# ── 研究方向细化标签（比原来更细） ───────────────────────
SUB_DIRECTIONS = {
    '运输监管':       ['运输监管', '道路运输', '公路运输', '运输安全管理', '押运', '运输许可'],
    '运输路径优化':   ['路径优化', '路径规划', '配送路径', 'VRP', '选址'],
    '运输风险评估':   ['运输.*风险', '风险评估.*运输', '风险.*道路'],
    '储存安全':       ['储存', '储罐', '仓储', '库区'],
    '应急处置':       ['应急处置', '应急预案', '应急救援', '应急管理', '应急能力', '事故应对'],
    '事故分析':       ['事故分析', '事故原因', '事故致因', '爆炸事故', '泄漏事故', '火灾事故', '事故演化', '事故调查'],
    '安全监管体系':   ['监管体系', '监管机制', '监管现状', '监管问题', '监管对策', '安全监管', '监管模式', '监管制度'],
    '园区安全管理':   ['化工园区', '园区安全', '园区风险', '园区监管'],
    '企业安全管理':   ['安全生产管理', '安全管理体系', '安全文化', '安全责任', 'HSE', '双重预防', '隐患排查'],
    '风险评价方法':   ['风险评价', '安全评价', '风险评估', 'AHP', 'HAZOP', '模糊综合', '风险矩阵'],
    '人员安全行为':   ['不安全行为', '安全行为', '人员培训', '安全意识', '安全培训', '从业人员'],
    '智能化监管':     ['信息化', '数字化', '智能监管', '物联网', 'GPS', '大数据', 'AI', '智能化'],
    '职业卫生健康':   ['职业卫生', '职业病', '职业健康', '职业暴露'],
}


def reclassify(title, keywords=''):
    text = title + ' ' + keywords
    dirs = []
    for d, kws in SUB_DIRECTIONS.items():
        for kw in kws:
            if re.search(kw, text):
                dirs.append(d)
                break
    return dirs if dirs else ['其他']


def main():
    with open(JSON_IN, 'r', encoding='utf-8') as f:
        data = json.load(f)

    papers = data['papers']
    print(f'原始论文数：{len(papers)}')

    # 过滤
    filtered = [p for p in papers if is_meaningful(p)]
    removed  = len(papers) - len(filtered)
    print(f'过滤掉无意义标题：{removed} 篇')
    print(f'保留：{len(filtered)} 篇')

    # 重新分类
    for p in filtered:
        p['sub_direction'] = reclassify(p['title'], p.get('keywords', ''))
        p['directions_str'] = ' / '.join(p['sub_direction'])

    # ── 写 SQLite ────────────────────────────────────────
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute('''
        CREATE TABLE papers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT,
            author       TEXT,
            unit         TEXT,
            degree       TEXT,
            year         INTEGER,
            abstract     TEXT,
            keywords     TEXT,
            directions   TEXT,
            source_kw    TEXT,
            source_url   TEXT,
            source_site  TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE paper_directions (
            paper_id  INTEGER,
            direction TEXT
        )
    ''')
    for p in filtered:
        cur.execute(
            'INSERT INTO papers (title,author,unit,degree,year,abstract,keywords,directions,source_kw,source_url,source_site) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (p['title'], p.get('author',''), p.get('unit',''),
             p.get('degree',''), int(p['year']) if p.get('year','').isdigit() else 0,
             p.get('abstract',''), p.get('keywords',''), p['directions_str'], p.get('source_keyword',''),
             p.get('source_url',''), p.get('source_site',''))
        )
        pid = cur.lastrowid
        for d in p['sub_direction']:
            cur.execute('INSERT INTO paper_directions VALUES (?,?)', (pid, d))
    conn.commit()
    conn.close()
    print(f'已写入 SQLite：{DB_PATH}')

    # ── 写 CSV ───────────────────────────────────────────
    with open(CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=[
            'title','author','unit','degree','year',
            'abstract','keywords','directions_str','source_keyword','source_url','source_site'
        ])
        w.writeheader()
        for p in filtered:
            w.writerow({
                'title':          p['title'],
                'author':         p.get('author',''),
                'unit':           p.get('unit',''),
                'degree':         p.get('degree',''),
                'year':           p.get('year',''),
                'abstract':       p.get('abstract',''),
                'keywords':       p.get('keywords',''),
                'directions_str': p['directions_str'],
                'source_keyword': p.get('source_keyword',''),
                'source_url':     p.get('source_url',''),
                'source_site':    p.get('source_site',''),
            })
    print(f'已写入 CSV：{CSV_PATH}')

    # ── 输出方向统计 ──────────────────────────────────────
    from collections import Counter
    dir_cnt = Counter()
    for p in filtered:
        for d in p['sub_direction']:
            dir_cnt[d] += 1

    print('\n【细分方向统计】')
    for d, c in dir_cnt.most_common():
        bar = '█' * int(c / dir_cnt.most_common(1)[0][1] * 25)
        print(f'  {d:<12}  {bar:<25}  {c} 篇')

    # 保存过滤后JSON供图谱使用
    out_json = os.path.join(DATA_DIR, 'papers_clean.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({'total': len(filtered), 'papers': filtered}, f, ensure_ascii=False, indent=2)
    print(f'\n已保存清洁数据：{out_json}')


if __name__ == '__main__':
    main()

