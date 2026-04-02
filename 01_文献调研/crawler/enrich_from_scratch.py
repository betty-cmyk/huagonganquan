# -*- coding: utf-8 -*-
import sqlite3, time, urllib.request, urllib.parse, re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CNKI_SEARCH_API = "https://search.cnki.com.cn/api/search/listresult"

def search_cnki(title):
    body = urllib.parse.urlencode({
        "Theme": title,
        "Order": "1",
        "Page": "1",
        "ArticleType": "0"
    }).encode("utf-8")
    req = urllib.request.Request(
        CNKI_SEARCH_API,
        data=body,
        headers={ "User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("articleList", [])
            if not items: return None
            # 找到标题最匹配的
            for it in items:
                clean_t = it.get("title", "").replace("~#@", "").replace("@#~", "").replace(" ","")
                if title.replace(" ","") in clean_t or clean_t in title.replace(" ",""):
                    # 构建 URL
                    db_type = it.get("dbType", "")
                    f_name = it.get("fileName", "")
                    p_code = it.get("publishCode", "")
                    url = ""
                    if db_type == "CJFD": url = f"https://www.cnki.com.cn/Article/CJFDTOTAL-{f_name}.htm"
                    elif db_type in ["CMFD", "CDFD", "CDMD"]: url = f"https://cdmd.cnki.com.cn/Article/CDMD-{p_code}-{f_name.replace('.nh', '')}.htm"
                    return url
    except Exception as e:
        print("    [Search API Error]", e)
    return None

def fetch_html(url):
    if not url: return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception as e:
        print("    [Fetch Error]", e)
        return ""

def extract(html):
    res = {"abs": "", "out": ""}
    if not html: return res
    abs_m = re.search(r'id="ChDivSummary"[^>]*>(.*?)</div>', html, re.S) or re.search(r'class="abstract-text"[^>]*>(.*?)</div>', html, re.S)
    if abs_m: res["abs"] = re.sub(r'<[^>]+>', '', abs_m.group(1)).strip()
    cat_m = re.search(r'id="Catalog"[^>]*>(.*?)</div>', html, re.S)
    if cat_m:
        txts = re.findall(r'>([^<\r\n\t]+)<', cat_m.group(1))
        res["out"] = "\n".join([t.strip() for t in txts if len(t.strip()) > 2])
    return res

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    try: cur.execute("ALTER TABLE papers ADD COLUMN outline TEXT")
    except: pass

    # 查找没有大纲的论文（由于它们也没有URL，我们需要按标题搜索）
    cur.execute("SELECT id, title FROM papers WHERE outline IS NULL OR outline = '' LIMIT 10")
    rows = cur.fetchall()
    print(f"--- Super Scraper: Processing {len(rows)} papers ---")
    
    updated = 0
    for pid, title in rows:
        print("\n[*] Title:", title)
        
        # 1. 搜索 URL
        url = search_cnki(title)
        if not url:
            print("    [-] URL not found via Search API.")
            time.sleep(1.5)
            continue
            
        print("    [+] URL found:", url)
        
        # 2. 访问详情页并提取
        html = fetch_html(url)
        info = extract(html)
        
        if info["abs"] or info["out"]:
            print("    [SUCCESS] Abs: %d chars, Out: %d lines" % (len(info["abs"]), len(info["out"].splitlines())))
            cur.execute("UPDATE papers SET source_url=?, abstract=?, outline=? WHERE id=?", (url, info["abs"], info["out"], pid))
            conn.commit()
            updated += 1
        else:
            print("    [-] No detailed data found on page.")
            cur.execute("UPDATE papers SET source_url=? WHERE id=?", (url, pid)) # 至少存下URL
            conn.commit()
            
        time.sleep(2.5)

    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print("\n[+] JSON synced.")

    conn.close()
    print("--- Finished. Updated %d papers ---" % updated)

if __name__ == '__main__': main()