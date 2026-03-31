# -*- coding: utf-8 -*-
"""
按年份汇总论文标题
使用方法：
  1. 将书签脚本下载的 JSON 文件放入 ../data/ 目录
  2. 运行本脚本：python analyze_by_year.py
  3. 脚本会提示你为没有年份的文章手动输入年份
  4. 汇总结果保存到 ../data/按年份汇总.txt
"""

import os, json, re
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, '..', 'data')
OUT_FILE   = os.path.join(DATA_DIR, '按年份汇总.txt')


def load_titles():
    """加载所有 JSON 文件中的标题"""
    all_items = []
    if not os.path.exists(DATA_DIR):
        print(f'[错误] 找不到目录：{DATA_DIR}')
        return all_items

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    if not files:
        print('[提示] data/ 下没有 JSON 文件，请先用书签脚本提取')
        return all_items

    for fname in sorted(files):
        fpath = os.path.join(DATA_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f'  [跳过] {fname}：{e}')
            continue

        keyword  = data.get('keyword', '')
        filedate = data.get('date', '')
        titles   = data.get('titles', [])

        for item in titles:
            if isinstance(item, dict):
                t = item.get('title', '').strip()
            else:
                t = str(item).strip()
            if t:
                all_items.append({
                    'title':     t,
                    'keyword':   keyword,
                    'file_date': filedate,
                    'year':      ''
                })
        print(f'  [加载] {fname}  →  {len(titles)} 条')

    # 按标题去重
    seen = set()
    uniq = []
    for item in all_items:
        if item['title'] not in seen:
            seen.add(item['title'])
            uniq.append(item)

    print(f'\n共 {len(all_items)} 条，去重后 {len(uniq)} 条')
    return uniq


def try_auto_year(title, file_date):
    """从标题或文件日期中自动识别年份"""
    m = re.search(r'(20[12][0-9])', title)
    if m:
        return m.group(1)
    m = re.search(r'(20[12][0-9])', str(file_date))
    if m:
        return m.group(1)
    return ''


def collect_years(items):
    """自动识别 + 手动补录年份"""
    print('\n==== 年份录入 ====')
    manual_list = []

    for item in items:
        yr = try_auto_year(item['title'], item['file_date'])
        if yr:
            item['year'] = yr
        else:
            manual_list.append(item)

    auto_count = len(items) - len(manual_list)
    print(f'自动识别年份：{auto_count} 条')
    print(f'需要手动补充：{len(manual_list)} 条')

    if manual_list:
        print()
        print('以下标题未能自动识别年份，请输入4位年份（回车跳过，q 退出录入）：')
        print('-' * 55)
        for i, item in enumerate(manual_list):
            print(f'[{i+1}/{len(manual_list)}] {item["title"][:60]}')
            yr_input = input('  年份 > ').strip()
            if yr_input.lower() == 'q':
                print('已退出，剩余条目年份标记为"未知"')
                break
            if re.match(r'^20[12][0-9]$', yr_input):
                item['year'] = yr_input
            else:
                item['year'] = '未知'

    # 没填到的也标记为未知
    for item in items:
        if not item['year']:
            item['year'] = '未知'

    return items


def build_report(items):
    """按年份汇总，生成报告文本"""
    by_year = defaultdict(list)
    for item in items:
        by_year[item['year']].append(item)

    lines = []
    sep  = '=' * 60
    sep2 = '-' * 40

    lines.append(sep)
    lines.append('  危险化学品安全论文  ——  按年份汇总报告')
    lines.append(f'  总计：{len(items)} 篇')
    lines.append(sep)

    # 年份分布统计
    lines.append('\n【年份分布统计】')
    lines.append(sep2)
    sorted_years = sorted(
        by_year.keys(),
        key=lambda x: x if re.match(r'^20[12][0-9]$', x) else '9999'
    )
    max_cnt = max(len(v) for v in by_year.values())
    for yr in sorted_years:
        cnt = len(by_year[yr])
        bar = '█' * int(cnt / max_cnt * 25)
        lines.append(f'  {yr}  {bar:<25}  {cnt} 篇')

    # 各年份详细标题
    lines.append('\n\n【各年份论文标题列表】')
    for yr in sorted_years:
        lines.append('')
        lines.append(f'▶ {yr} 年  （{len(by_year[yr])} 篇）')
        lines.append(sep2)
        for idx, item in enumerate(by_year[yr], 1):
            kw = f'[{item["keyword"]}]' if item['keyword'] else ''
            lines.append(f'  {idx:>3}. {item["title"]}  {kw}')

    lines.append('')
    lines.append(sep)
    lines.append('  汇总完毕')
    lines.append(sep)
    return '\n'.join(lines)


def main():
    print('\n==== 论文标题年份汇总工具 ====')
    print(f'数据目录：{os.path.abspath(DATA_DIR)}\n')

    items = load_titles()
    if not items:
        return

    items = collect_years(items)
    report = build_report(items)

    print('\n' + report)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'\n[已保存] {OUT_FILE}')


if __name__ == '__main__':
    main()
