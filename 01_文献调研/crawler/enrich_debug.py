# -*- coding: utf-8 -*-
import sqlite3, time, urllib.request, re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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
    
    cur.execute("SELECT id, title, source_url FROM papers WHERE (outline IS NULL OR outline = '') AND source_url LIKE '%cdmd%' LIMIT 10")
    rows = cur.fetchall()
    print("--- Starting Debug Scraper (%d papers) ---" % len(rows))
    
    updated = 0
    for pid, title, url in rows:
        print("\n[*] Title:", title.encode('utf-8','replace').decode('utf-8','replace'))
        print("    URL:", url)
        html = fetch(url)
        
        info = extract(html)
        if info["abs"] or info["out"]:
            print("    [SUCCESS] Abs: %d chars, Out: %d chars" % (len(info["abs"]), len(info["out"])))
            cur.execute("UPDATE papers SET abstract=?, outline=? WHERE id=?", (info["abs"], info["out"], pid))
            conn.commit()
            updated += 1
        else:
            print("    [FAIL] No data found. HTML size: %d bytes" % len(html))
            if len(html) < 2000 and len(html) > 0:
                print("    [HTML Snippet]", html[:150].replace('\n',' '))
        
        time.sleep(2)

    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    conn.close()
    print("\n--- Finished. Updated %d papers ---" % updated)

if __name__ == '__main__': main()