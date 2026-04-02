import sqlite3, urllib.request, urllib.parse, re, json

DB_PATH = '01_文献调研/data/papers.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 取出一条有意义的博硕论文（为了保证大纲测试成功）
cur.execute("SELECT id, title FROM papers WHERE title LIKE '%基于%' LIMIT 1")
pid, title = cur.fetchone()
print(f'Test Title: {title}')

body = urllib.parse.urlencode({'Theme': title, 'Order': '1', 'Page': '1', 'ArticleType': '0'}).encode('utf-8')
req = urllib.request.Request('https://search.cnki.com.cn/api/search/listresult', data=body, headers={'User-Agent': 'Mozilla/5.0'})

try:
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode('utf-8'))
    items = data.get('articleList', [])
    print(f'Found {len(items)} items in search API')
    
    for it in items:
        clean_t = it.get('title', '').replace('~#@', '').replace('@#~', '').replace(' ', '')
        if title.replace(' ', '') in clean_t or clean_t in title.replace(' ', ''):
            f_name = it.get('fileName', '')
            p_code = it.get('publishCode', '')
            db_type = it.get('dbType', '')
            
            if db_type in ['CMFD', 'CDFD', 'CDMD']:
                url = f'https://cdmd.cnki.com.cn/Article/CDMD-{p_code}-{f_name.replace(".nh", "")}.htm'
            else:
                url = f'https://www.cnki.com.cn/Article/CJFDTOTAL-{f_name}.htm'
                
            print(f'Match! URL: {url}')
            
            # 强化防封禁策略
            import random
            ua = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
            ])
            headers = {
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Connection': 'keep-alive',
                'Referer': 'https://search.cnki.com.cn/',
                'Upgrade-Insecure-Requests': '1',
            }
            req2 = urllib.request.Request(url, headers=headers)
            html = urllib.request.urlopen(req2, timeout=15).read().decode('utf-8', 'ignore')
            print(f'HTML fetched. Length: {len(html)}')
            
            print('\n--- Scanning HTML tags ---')
            print('All IDs with "abstract" or "summary":', re.findall(r'id=["\']([^"]*(?:abstract|summary)[^"]*)["\']', html, re.I))
            print('All classes with "abstract" or "summary":', re.findall(r'class=["\']([^"]*(?:abstract|summary)[^"]*)["\']', html, re.I))
            
            print('All IDs with "catalog" or "menu" or "content":', re.findall(r'id=["\']([^"]*(?:catalog|menu|content)[^"]*)["\']', html, re.I))
            print('All classes with "catalog" or "menu":', re.findall(r'class=["\']([^"]*(?:catalog|menu)[^"]*)["\']', html, re.I))
            
            break
except Exception as e:
    print('Error:', e)

conn.close()
