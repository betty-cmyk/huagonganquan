import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

def main():
    if not JSON_CLEAN.exists():
        print("[!] papers_clean.json 不存在")
        return

    data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
    scholar_papers = [p for p in data.get('papers', []) if 'GoogleScholar' in p.get('db_source', '')]

    print(f"\n[*] Google Scholar (谷歌学术) 自动扩充抓取总数: {len(scholar_papers)} 篇")
    print("=" * 60)
    
    for p in scholar_papers[:10]:
        print(f"  - 标题: {p.get('title', '')}")
        print(f"    年份: {p.get('year', '未知')} | 分类: {p.get('category_9', '')}")
        abs_txt = p.get('abstract', '').replace('\n', ' ')
        print(f"    摘要: {abs_txt[:60]}..." if abs_txt else "    摘要: [无]")
        print(f"    链接: {p.get('source_url', '')[:60]}...\n")

    print(f"[!] 抽样完成。共展示了最新的 {min(10, len(scholar_papers))} 篇文献。")

if __name__ == '__main__':
    main()