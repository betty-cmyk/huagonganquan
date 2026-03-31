# -*- coding: utf-8 -*-
"""
论文选题方向分析脚本
读取 data/ 目录下所有 JSON 文件，统计分析选题方向
用法：python analyze.py
"""

import os
import json
import re
from collections import Counter

# ── 路径配置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, '..', 'data')
OUT_FILE   = os.path.join(DATA_DIR, '选题方向分析报告.txt')

# ── 子方向关键词映射 ──────────────────────────────────────
DIRECTION_KEYWORDS = {
    '运输监管':     ['运输', '道路运输', '公路运输', '押运', '托运', '配送'],
    '储存仓储':     ['储存', '仓储', '储罐', '库房', '堆场', '存放'],
    '应急处置':     ['应急', '应急处置', '应急预案', '事故处理', '救援', '处置'],
    '安全监管体系': ['监管', '监督管理', '法规', '标准', '制度', '体系', '机制'],
    '事故分析':     ['事故', '泄漏', '爆炸', '火灾', '中毒', '案例分析', '原因分析'],
    '技术与信息化': ['信息化', '智能', 'GPS', '大数据', '物联网', '追踪', '监控系统'],
    '人员与培训':   ['人员', '培训', '素质', '安全意识', '驾驶员', '从业人员'],
    '企业安全管理': ['企业', '安全管理', 'HSE', '双重预防', '隐患排查', '风险管控'],
    '消防安全':     ['消防', '灭火', '防火', '火灾预防'],
    '职业卫生':     ['职业卫生', '职业病', '职业健康', '有毒', '粉尘', '噪声'],
}

# ── 高频词（用于词频统计，过滤无意义词） ─────────────────
STOP_WORDS = set([
    '的', '了', '在', '是', '和', '与', '对', '及', '中', '为',
    '以', '其', '于', '从', '被', '等', '该', '一', '有', '将',
    '研究', '分析', '探讨', '问题', '措施', '我国', '现状',
    '基于', '关于', '论', '浅谈', '浅析', '初探',
])


def load_all_papers():
    """加载 data/ 目录下所有 JSON 文件"""
    papers = []
    if not os.path.exists(DATA_DIR):
        print(f'[错误] data 目录不存在：{DATA_DIR}')
        return papers

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    if not files:
        print(f'[提示] data/ 目录下没有 JSON 文件，请先用书签脚本提取论文数据')
        return papers

    for fname in files:
        fpath = os.path.join(DATA_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            batch = data.get('papers', [])
            papers.extend(batch)
            print(f'  [加载] {fname}  →  {len(batch)} 篇')
        except Exception as e:
            print(f'  [跳过] {fname} 读取失败：{e}')

    # 去重（按标题）
    seen = set()
    unique = []
    for p in papers:
        t = p.get('title', '').strip()
        if t and t not in seen:
            seen.add(t)
            unique.append(p)

    print(f'\n共加载 {len(papers)} 条，去重后 {len(unique)} 条\n')
    return unique


def classify_paper(title):
    """将一篇论文按标题归入子方向（可归入多个）"""
    matched = []
    for direction, kws in DIRECTION_KEYWORDS.items():
        for kw in kws:
            if kw in title:
                matched.append(direction)
                break
    return matched if matched else ['其他/综合']


def extract_title_words(title):
    """从标题中提取有意义的词（2~6字）"""
    words = re.findall(r'[\u4e00-\u9fa5]{2,6}', title)
    return [w for w in words if w not in STOP_WORDS]


def analyze(papers):
    """核心分析逻辑"""
    direction_counter = Counter()
    word_counter      = Counter()
    year_counter      = Counter()
    titles_by_dir     = {d: [] for d in DIRECTION_KEYWORDS}
    titles_by_dir['其他/综合'] = []

    for p in papers:
        title = p.get('title', '').strip()
        if not title:
            continue

        # 子方向分类
        dirs = classify_paper(title)
        for d in dirs:
            direction_counter[d] += 1
            titles_by_dir.setdefault(d, []).append(title)

        # 词频统计
        for w in extract_title_words(title):
            word_counter[w] += 1

        # 年份统计
        year = p.get('year', '')
        yr_match = re.search(r'(20[12][0-9])', str(year))
        if yr_match:
            year_counter[yr_match.group(1)] += 1

    return direction_counter, word_counter, year_counter, titles_by_dir


def build_report(papers, direction_counter, word_counter, year_counter, titles_by_dir):
    """生成文字报告"""
    lines = []
    sep  = '=' * 60
    sep2 = '-' * 40

    lines.append(sep)
    lines.append('  危险化学品安全方向  论文选题分析报告')
    lines.append(sep)
    lines.append(f'  总样本量：{len(papers)} 篇')
    lines.append('')

    # 1. 子方向分布
    lines.append('【一、研究子方向分布】')
    lines.append(sep2)
    total_classified = sum(direction_counter.values())
    for direction, cnt in direction_counter.most_common():
        bar = '█' * int(cnt / max(direction_counter.values()) * 20)
        pct = cnt / len(papers) * 100 if papers else 0
        lines.append(f'  {direction:<12}  {bar:<20}  {cnt:>3} 篇  ({pct:.1f}%)')
    lines.append('')

    # 2. 近年发表趋势
    if year_counter:
        lines.append('【二、近年发表趋势（有年份信息的论文）】')
        lines.append(sep2)
        for yr in sorted(year_counter.keys()):
            bar = '█' * year_counter[yr]
            lines.append(f'  {yr} 年  {bar}  {year_counter[yr]} 篇')
        lines.append('')

    # 3. 标题高频词
    lines.append('【三、标题高频词 TOP 30】')
    lines.append(sep2)
    for word, cnt in word_counter.most_common(30):
        lines.append(f'  {word}  ×{cnt}')
    lines.append('')

    # 4. 各子方向代表性论文标题
    lines.append('【四、各子方向代表性论文标题（每方向最多10篇）】')
    lines.append(sep2)
    for direction, cnt in direction_counter.most_common():
        titles = titles_by_dir.get(direction, [])
        lines.append(f'\n▶ {direction}（共 {cnt} 篇）')
        for t in titles[:10]:
            lines.append(f'    · {t}')

    # 5. 选题建议
    lines.append('')
    lines.append('【五、选题建议】')
    lines.append(sep2)
    top3 = [d for d, _ in direction_counter.most_common(3)]
    lines.append(f'  文献最多的三个方向：{", ".join(top3)}')
    lines.append('  → 文献越多，写作素材越充足，建议优先从以上方向中选题。')
    lines.append('')
    lines.append('  参考选题示例：')
    suggestions = {
        '运输监管':     '危险化学品道路运输安全监管问题及对策研究',
        '储存仓储':     '危险化学品储存安全管理现状与对策分析',
        '应急处置':     '危险化学品事故应急处置体系建设研究',
        '安全监管体系': '我国危险化学品安全监管体系优化研究',
        '事故分析':     '危险化学品运输事故致因分析及预防对策',
        '技术与信息化': '基于物联网的危险化学品运输智能监管系统研究',
        '人员与培训':   '危险化学品从业人员安全培训现状与改进策略',
        '企业安全管理': '危险化学品企业双重预防机制建设研究',
    }
    for d in top3:
        if d in suggestions:
            lines.append(f'    [{d}] {suggestions[d]}')

    lines.append('')
    lines.append(sep)
    lines.append('  报告生成完毕，请结合自身兴趣确定最终选题')
    lines.append(sep)

    return '\n'.join(lines)


def main():
    print('\n==== 论文选题方向分析 ====')
    print(f'数据目录：{os.path.abspath(DATA_DIR)}\n')

    papers = load_all_papers()
    if not papers:
        return

    direction_counter, word_counter, year_counter, titles_by_dir = analyze(papers)
    report = build_report(papers, direction_counter, word_counter, year_counter, titles_by_dir)

    print(report)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'\n[已保存] {OUT_FILE}')


if __name__ == '__main__':
    main()

