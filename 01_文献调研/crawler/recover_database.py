# -*- coding: utf-8 -*-
import sqlite3, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"
JSON_MERGED = ROOT / "data" / "所有论文_merged.json"
JSON_CANDIDATES = ROOT / "data" / "manual_review_candidates.json"

VOCAB = [
    "风险评价", "风险评估", "HAZOP", "定量风险", "风险矩阵", "安全评价", "安全评估",
    "火灾", "爆炸", "泄漏", "消防", "多米诺", "燃爆", "扩散", "热失控",
    "物联网", "智能", "预警", "数字孪生", "机器视觉", "大数据", "信息化", "传感器",
    "事故演化", "应急救援", "应急预案", "事故致因", "应急管理", "事故分析", "故障树",
    "安全文化", "人因工程", "不安全行为", "本质安全", "双重预防", "安全绩效",
    "职业卫生", "职业病", "职业健康", "职业暴露", "粉尘", "噪声", "有毒有害",
    "道路运输", "仓储", "危化品", "危险化学品", "储罐", "罐区", "管道", "物流",
    "化工园区", "安全监管", "封闭化管理", "指标体系", "应急物资", "精细化工"
]

def main():
    print("\n--- 正在启动【浴火重生】抢救计划 ---")
    if not DB_PATH.exists():
        print("[!] 数据库文件丢失！")
        return

    # 1. 收集本地所有可能的论文备份
    recovered_papers = {}

    # 来源A：所有论文_merged.json (最大，最全，含之前爬的所有原始数据)
    if JSON_MERGED.exists():
        try:
            data = json.loads(JSON_MERGED.read_text(encoding='utf-8'))
            for p in data.get('papers', []):
                title = p.get('title', '').strip()
                if not title or "?" * 3 in title:
                    continue # 跳过乱码
                # 如果存在旧记录，合并（保留最长的数据）
                if title not in recovered_papers:
                    recovered_papers[title] = p
                else:
                    old_p = recovered_papers[title]
                    if len(p.get('abstract', '')) > len(old_p.get('abstract', '')):
                        old_p['abstract'] = p['abstract']
                    if len(p.get('outline', '')) > len(old_p.get('outline', '')):
                        old_p['outline'] = p['outline']
        except Exception as e:
            print(f"[-] 读取 {JSON_MERGED.name} 失败: {e}")

    # 来源B：候选清单 (含有非常详细的 summary 摘要)
    if JSON_CANDIDATES.exists():
        try:
            cands = json.loads(JSON_CANDIDATES.read_text(encoding='utf-8'))
            for c in cands:
                title = c.get('title', '').strip()
                if not title or "?" * 3 in title:
                    continue
                
                if title in recovered_papers:
                    if len(c.get('summary', '')) > len(recovered_papers[title].get('abstract', '')):
                        recovered_papers[title]['abstract'] = c['summary']
                    if not recovered_papers[title].get('source_url') and c.get('source_url'):
                        recovered_papers[title]['source_url'] = c['source_url']
                else:
                    recovered_papers[title] = {
                        'title': title,
                        'year': c.get('year', ''),
                        'abstract': c.get('summary', ''),
                        'source_url': c.get('source_url', ''),
                        'db_source': c.get('dbSource', ''),
                        'category_9': c.get('category', '')
                    }
        except Exception as e:
            print(f"[-] 读取 {JSON_CANDIDATES.name} 失败: {e}")

    print(f"[+] 从本地深海沉船中成功打捞出 {len(recovered_papers)} 篇纯净论文！")

    # 2. 清空并重建数据库
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("DELETE FROM papers")
    conn.commit()

    inserted = 0
    for title, p in recovered_papers.items():
        # 净化被百度知道污染的摘要
        abs_txt = p.get('abstract', '') or p.get('summary', '')
        for nk in ['可以这样用吗', '关注者', '被浏览', '查看问题描述', '知乎', '下载自然人', 'Como ya se sabe', '国家的大学生就业']:
            if nk in abs_txt:
                abs_txt = ""
                break
                
        # 智能补全缺失关键词
        kws = p.get('keywords', '')
        if not kws or kws == '无':
            f_kws = []
            text = title + " " + abs_txt
            for v in VOCAB:
                if v in text:
                    f_kws.append(v)
            if not f_kws:
                chunks = re.findall(r'[\u4e00-\u9fa5]{3,5}', title.replace("化工安全", "").replace("基于", "").replace("研究", ""))
                f_kws = list(set(chunks))[:3]
            kws = " / ".join(f_kws)
            
        year = p.get('year', '')
        try: year = int(year) if str(year).isdigit() else 2024
        except: year = 2024
        
        cur.execute("""
            INSERT INTO papers 
            (title, author, unit, degree, year, abstract, outline, keywords, 
             category_9, directions, source_kw, db_type, db_source, source_url, source_site)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            title,
            p.get('author', ''),
            p.get('unit', ''),
            p.get('degree', ''),
            year,
            abs_txt,
            p.get('outline', ''),
            kws,
            p.get('category_9', ''),
            p.get('directions_str', p.get('directions', '')),
            p.get('source_keyword', p.get('source_kw', '')),
            p.get('db_type', ''),
            p.get('db_source', ''),
            p.get('source_url', ''),
            p.get('source_site', '')
        ))
        inserted += 1

    conn.commit()
    print(f"[+] {inserted} 篇浴火重生的论文已成功灌入数据库！所有关键词已补齐！")

    # 3. 完美同步至 JSON_CLEAN
    cur.execute("PRAGMA table_info(papers)")
    cols = [d[1] for d in cur.fetchall()]
    cur.execute("SELECT * FROM papers")
    data = {'total': inserted, 'papers': [dict(zip(cols, r)) for r in cur.fetchall()]}
    JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print("[!] 图谱前端数据已更新。")

    conn.close()

if __name__ == '__main__': main()