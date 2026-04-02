import sqlite3, time, urllib.request, urllib.parse, re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

# 通过 Bing 搜索，不带任何 Cookie 的极简 Header，反爬概率低
def search_bing(title):
    query = urllib.parse.urlencode({'q': title + " site:cnki.com.cn"})
    url = f'https://cn.bing.com/search?{query}'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', 'ignore')
            
            # Bing 搜索结果的摘要通常位于 <div class="b_caption"><p> 中，或者是 <p class="b_lineclamp...">
            # 匹配最通用的段落
            snippets = re.findall(r'<div class="b_caption">.*?<p[^>]*>(.*?)</p>', html, re.S)
            if snippets:
                # 清除其中的 <strong> 关键词高亮等 HTML 标签
                clean_abs = re.sub(r'<[^>]+>', '', snippets[0]).strip()
                # 有时开头有日期
                clean_abs = re.sub(r'^\d{4}年\d{1,2}月\d{1,2}日\s*·?\s*', '', clean_abs)
                return clean_abs
    except Exception as e:
        print(f"  [Error] {e}")
    return ""

def main():
    if not DB_PATH.exists(): return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    try: cur.execute("ALTER TABLE papers ADD COLUMN outline TEXT")
    except: pass

    # 查找尚未补充摘要的论文
    cur.execute("SELECT id, title, abstract FROM papers WHERE abstract IS NULL OR abstract = '' LIMIT 20")
    rows = cur.fetchall()
    print(f"Processing {len(rows)} papers using Bing...")
    
    updated = 0
    for pid, title, old_abs in rows:
        print(f"\n- Search: {title}")
        abstract = search_bing(title)
        if abstract:
            print(f"  [+] Found ({len(abstract)} chars): {abstract[:60]}...")
            cur.execute("UPDATE papers SET abstract=? WHERE id=?", (abstract, pid))
            conn.commit()
            updated += 1
        else:
            print("  [-] No snippet found on Bing.")
            
        time.sleep(1.5) # 防止 Bing 也拦截

    # 同步回 JSON
    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        all_p = [dict(zip(cols, r)) for r in cur.fetchall()]
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = all_p
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    conn.close()
    print(f"\nDone. Updated {updated} papers.")

if __name__ == '__main__': main()