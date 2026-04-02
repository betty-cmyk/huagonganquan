import sqlite3, json, urllib.request, urllib.parse, time, socket, base64, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"
CDP_URL = "http://127.0.0.1:9222"

# --- WebSocket 客户端 ---
def simple_ws_request(ws_url, req_dict):
    parsed = urllib.parse.urlparse(ws_url)
    host, port = parsed.hostname, parsed.port
    path = parsed.path
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((host, port))
    
    key = base64.b64encode(hashlib.sha1(str(time.time()).encode()).digest()).decode()
    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(handshake.encode())
    resp = s.recv(4096)
    if b"101 Switching Protocols" not in resp:
        s.close()
        return None
        
    payload = json.dumps(req_dict).encode('utf-8')
    header = bytearray([0x81, len(payload)])
    if len(payload) >= 126:
        header = bytearray([0x81, 126]) + len(payload).to_bytes(2, 'big')
    s.sendall(header + payload)
    
    response_data = b""
    while True:
        header = s.recv(2)
        if not header: break
        length = header[1] & 127
        if length == 126:
            length = int.from_bytes(s.recv(2), 'big')
        elif length == 127:
            length = int.from_bytes(s.recv(8), 'big')
            
        data = b""
        while len(data) < length:
            chunk = s.recv(length - len(data))
            if not chunk: break
            data += chunk
        response_data = data
        break
        
    s.close()
    try:
        return json.loads(response_data.decode('utf-8'))
    except:
        return None

def get_chrome_page():
    try:
        req = urllib.request.Request(f"{CDP_URL}/json")
        resp = urllib.request.urlopen(req, timeout=5)
        pages = json.loads(resp.read().decode('utf-8'))
        for p in pages:
            if p.get('type') == 'page' and not p.get('url', '').startswith('chrome-extension'):
                return p.get('webSocketDebuggerUrl')
    except:
        pass
    return None

# 提取百度学术摘要的 JS
js_script = """
(function() {
    let el = document.querySelector('.c_abstract');
    if (el) {
        let text = el.innerText;
        if (text.startsWith('摘要：') || text.startsWith('[摘要]')) {
            text = text.substring(3).trim();
        }
        return text;
    }
    return '';
})();
"""

def get_abstract_via_cdp(ws_url, title):
    url = f"https://xueshu.baidu.com/s?wd={urllib.parse.quote(title)}"
    nav_req = {"id": 1, "method": "Page.navigate", "params": {"url": url}}
    simple_ws_request(ws_url, nav_req)
    
    time.sleep(2) # 等待百度搜索结果加载
    
    eval_req = {"id": 2, "method": "Runtime.evaluate", "params": {"expression": js_script, "returnByValue": True}}
    res = simple_ws_request(ws_url, eval_req)
    
    if res and "result" in res and "result" in res["result"]:
        return res["result"]["result"].get("value", "")
    return ""

def main():
    ws_url = get_chrome_page()
    if not ws_url:
        print("\n[!] 未发现开启了 9222 端口的 Chrome 页面，请确保你的浏览器未被关闭！")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # 取 30 篇测试一下
    cur.execute("SELECT id, title FROM papers WHERE (abstract IS NULL OR length(abstract) < 80) LIMIT 30")
    rows = cur.fetchall()
    print(f"\n--- 复用现有浏览器窗口，自动抓取 {len(rows)} 篇 ---")
    
    updated = 0
    for pid, title in rows:
        print(f"\n- 搜索: {title}")
        abstract = get_abstract_via_cdp(ws_url, title)
        
        if abstract and len(abstract) > 30:
            print(f"  [+] 成功提取 ({len(abstract)} 字): {abstract[:40]}...")
            cur.execute("UPDATE papers SET abstract=? WHERE id=?", (abstract, pid))
            conn.commit()
            updated += 1
        else:
            print("  [-] 页面未加载或未找到摘要（可能被拦截，请看浏览器界面）")
            
        time.sleep(1)

    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n[!] 成功同步 {updated} 篇论文摘要至 JSON 文件。")

    conn.close()

if __name__ == '__main__': main()