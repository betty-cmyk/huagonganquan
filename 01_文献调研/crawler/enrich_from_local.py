# -*- coding: utf-8 -*-
import sqlite3, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_MERGED = ROOT / "data" / "所有论文_merged.json"
JSON_CANDIDATES = ROOT / "data" / "manual_review_candidates.json"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

def load_local_abstracts():
    abs_dict = {}
    # 从所有论文里找
    if JSON_MERGED.exists():
        data = json.loads(JSON_MERGED.read_text(encoding='utf-8'))
        for p in data.get('papers', []):
            title = p.get('title', '')
            summary = p.get('summary', '') or p.get('abstract', '')
            if title and summary:
                abs_dict[title] = summary
    
    # 从初筛记录里找
    if JSON_CANDIDATES.exists():
        cands = json.loads(JSON_CANDIDATES.read_text(encoding='utf-8'))
        for c in cands:
            title = c.get('title', '')
            summary = c.get('summary', '')
            if title and summary:
                abs_dict[title] = summary
                
    return abs_dict

def main():
    if not DB_PATH.exists():
        print("Database not found!")
        return

    abs_dict = load_local_abstracts()
    print(f"Loaded {len(abs_dict)} abstracts from local files.")

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    try: cur.execute("ALTER TABLE papers ADD COLUMN outline TEXT")
    except: pass

    cur.execute("SELECT id, title, abstract FROM papers")
    rows = cur.fetchall()
    
    updated = 0
    for pid, title, old_abs in rows:
        if title in abs_dict:
            new_abs = abs_dict[title]
            # 如果本地有的摘要比数据库里的长
            if not old_abs or len(new_abs) > len(old_abs):
                cur.execute("UPDATE papers SET abstract=? WHERE id=?", (new_abs, pid))
                updated += 1
    conn.commit()
    print(f"Updated {updated} records in database.")

    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        all_p = [dict(zip(cols, r)) for r in cur.fetchall()]
        if JSON_CLEAN.exists():
            data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
            data['papers'] = all_p
            JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            print("Synced to papers_clean.json")
            
    conn.close()

if __name__ == '__main__':
    main()