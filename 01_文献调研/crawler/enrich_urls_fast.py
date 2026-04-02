import sqlite3, json, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

def main():
    if not DB_PATH.exists(): return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 查找尚未有有效 source_url 的论文
    cur.execute("SELECT id, title FROM papers WHERE (source_url IS NULL OR source_url = '')")
    rows = cur.fetchall()
    print(f"\n--- 极速本地补全论文 URL ({len(rows)} 篇) ---")
    
    updated = 0
    for pid, title in rows:
        # 跳过那些奇怪的乱码标题
        if "?" * 5 in title:
            continue
            
        # 静态拼接百度学术搜索链接，无需任何网络请求
        paper_url = f"https://xueshu.baidu.com/s?wd={urllib.parse.quote(title)}"
        
        cur.execute("UPDATE papers SET source_url=? WHERE id=?", (paper_url, pid))
        updated += 1

    conn.commit()

    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n[+] 完美同步 {updated} 篇论文的百度学术快捷链接至数据库和 JSON 文件！")

    conn.close()

if __name__ == '__main__': main()