# -*- coding: utf-8 -*-
"""
解析从全国图书馆参考联盟复制的论文文本，提取结构化信息
用法：python parse_txt.py
将在 data/ 目录下生成：
  - 化工安全_按年份汇总.txt    按年份汇总报告
  - 所有论文_merged.json       结构化数据
"""

import os, re, json
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, '..', 'data')

# ── 子方向分类关键词 ──────────────────────────────────────
DIRECTIONS = {
    '安全监管':     ['监管', '监督管理', '监督检查', '安全生产监管'],
    '应急管理':     ['应急', '应急处置', '应急预案', '应急救援', '应急能力'],
    '事故分析':     ['事故', '爆炸', '泄漏', '火灾', '中毒', '致因', '事故演化'],
    '风险评价':     ['风险评价', '安全评价', '风险评估', '安全评估', '风险管控', '风险预警', '危险性分析'],
    '园区安全':     ['化工园区', '园区'],
    '企业安全管理': ['企业', '安全管理', '安全生产', '安全文化', '安全责任'],
    '人员行为':     ['员工', '不安全行为', '培训', '从业人员', '安全意识'],
    '智能技术':     ['机器学习', '深度学习', '神经网络', '知识图谱', '物联网',
                    '大数据', '机器视觉', '人工智能', '信息化', '数字化', '智能'],
    '运输物流':     ['运输', '物流', '危险品运输', '危化品'],
    '工艺过程':     ['工艺', 'HAZOP', '化工过程', '工艺流程', '故障诊断', '过程监测'],
    '实验室安全':   ['实验室'],
}


def classify(title, keywords=''):
    text = title + keywords
    dirs = []
    for d, kws in DIRECTIONS.items():
        for kw in kws:
            if kw in text:
                dirs.append(d)
                break
    return dirs if dirs else ['其他']


def parse_file(filepath):
    """解析单个 txt 文件，返回论文列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    # 把 \xa0 替换为普通空格，方便后续处理
    raw = raw.replace('\xa0', ' ')

    papers = []
    # 每条记录特征：标题单独一行（末尾有空格），下一行以「作者：」开头
    # 实际格式：标题\n作者：XXX  学位授予单位：XXX  学位名称：XXX  学位年度：XXXX  [关键词：...] [摘要：...]
    lines = raw.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 找到「作者：」行
        if line.startswith('作者：') and i > 0:
            # 标题是上一个非空行
            title = ''
            for j in range(i - 1, max(i - 5, -1), -1):
                candidate = lines[j].strip()
                if candidate and '获取途径' not in candidate and '邮箱' not in candidate:
                    title = candidate
                    break

            if not title or len(title) < 4:
                i += 1
                continue

            # 从当前行提取字段（用多个空格或制表符分隔）
            info_line = line

            def extract(pattern, text, default=''):
                m = re.search(pattern, text)
                return m.group(1).strip() if m else default

            author   = extract(r'作者：([^\s学]+)', info_line)
            unit     = extract(r'学位授予单位：([^\s学]+(?:大学|学院|学校|研究院|研究所|大学\(\S+\))?)', info_line)
            # 更宽松地提取单位（到下一个字段为止）
            unit_m = re.search(r'学位授予单位：(.+?)\s{2,}学位名称', info_line)
            if unit_m:
                unit = unit_m.group(1).strip()
            degree   = extract(r'学位名称：(\S+)', info_line)
            year     = extract(r'学位年度：(\d{4})', info_line)
            kw_m     = re.search(r'关键词：(.+?)(?:\s{2,}摘要：|$)', info_line)
            keywords = kw_m.group(1).strip() if kw_m else ''
            abs_m    = re.search(r'摘要：(.+)', info_line)
            abstract = abs_m.group(1).strip()[:200] if abs_m else ''

            if not year:  # 必须有年份才保留
                i += 1
                continue

            papers.append({
                'title':          title,
                'author':         author,
                'unit':           unit,
                'degree':         degree,
                'year':           year,
                'keywords':       keywords,
                'abstract':       abstract,
                'direction':      classify(title, keywords),
            })

        i += 1

    return papers


def build_year_report(papers, source_keyword):
    """生成按年份汇总报告"""
    by_year = defaultdict(list)
    for p in papers:
        by_year[p['year']].append(p)

    by_dir = defaultdict(list)
    for p in papers:
        for d in p['direction']:
            by_dir[d].append(p)

    lines = []
    SEP  = '=' * 65
    SEP2 = '-' * 45

    lines.append(SEP)
    lines.append(f'  搜索词：{source_keyword}    共提取：{len(papers)} 篇')
    lines.append(SEP)

    # 年份分布
    lines.append('\n【一、年份分布】')
    lines.append(SEP2)
    sorted_years = sorted(by_year.keys())
    max_cnt = max(len(v) for v in by_year.values())
    for yr in sorted_years:
        cnt = len(by_year[yr])
        bar = '█' * int(cnt / max_cnt * 30)
        lines.append(f'  {yr}  {bar:<30}  {cnt:>3} 篇')

    # 子方向分布
    lines.append('\n\n【二、研究方向分布】')
    lines.append(SEP2)
    for d, ps in sorted(by_dir.items(), key=lambda x: -len(x[1])):
        bar = '█' * max(1, int(len(ps) / len(papers) * 30))
        lines.append(f'  {d:<12}  {bar:<30}  {len(ps):>3} 篇')

    # 各年份详细列表
    lines.append('\n\n【三、各年份论文列表】')
    for yr in sorted_years:
        lines.append('')
        lines.append(f'▶ {yr} 年  （{len(by_year[yr])} 篇）')
        lines.append(SEP2)
        for i, p in enumerate(by_year[yr], 1):
            dirs_str = ' / '.join(p['direction'])
            lines.append(f'  {i:>3}. 【{dirs_str}】{p["title"]}')
            lines.append(f'       作者：{p["author"]}  单位：{p["unit"]}  学位：{p["degree"]}')
            if p['keywords']:
                lines.append(f'       关键词：{p["keywords"]}')

    lines.append('')
    lines.append(SEP)
    return '\n'.join(lines)


def main():
    txt_files = [
        f for f in os.listdir(DATA_DIR)
        if f.endswith('.txt')
        and '汇总' not in f and '报告' not in f
    ]
    if not txt_files:
        print(f'[提示] {DATA_DIR} 下没有 .txt 文件')
        return

    all_papers = []
    for fname in sorted(txt_files):
        fpath   = os.path.join(DATA_DIR, fname)
        keyword = fname.replace('.txt', '')
        print(f'\n解析：{fname}')
        papers = parse_file(fpath)
        for p in papers:
            p['source_keyword'] = keyword
        print(f'  提取到 {len(papers)} 篇')

        if not papers:
            print('  [警告] 未提取到数据，跳过')
            continue

        report = build_year_report(papers, keyword)
        out_txt = os.path.join(DATA_DIR, f'{keyword}_按年份汇总.txt')
        with open(out_txt, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'  已保存：{out_txt}')
        print('\n' + report[:1200])
        all_papers.extend(papers)

    # 合并去重保存 JSON
    seen = set(); uniq = []
    for p in all_papers:
        if p['title'] not in seen:
            seen.add(p['title']); uniq.append(p)

    out_json = os.path.join(DATA_DIR, '所有论文_merged.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({'total': len(uniq), 'papers': uniq}, f, ensure_ascii=False, indent=2)
    print(f'\n[完成] 去重后共 {len(uniq)} 篇，已保存：{out_json}')


if __name__ == '__main__':
    main()
