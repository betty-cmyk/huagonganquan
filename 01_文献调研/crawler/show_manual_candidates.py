# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

path = Path(__file__).resolve().parents[1] / "data" / "manual_review_candidates.json"
rows = json.loads(path.read_text(encoding="utf-8"))

categories = ["运输与储存安全类", "事故分析与应急类", "职业卫生健康类"]
for cat in categories:
    print(f"\n### {cat}")
    items = [r for r in rows if r["category"] == cat and r["verdict"] == "keep" and not r["already_in_db"]]
    for i, r in enumerate(items[:15], 1):
        print(f"{i:02d}. {r['year']} | {r['title']} | {r['dbType']} | {r['query']}")
