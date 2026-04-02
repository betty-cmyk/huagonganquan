# -*- coding: utf-8 -*-
import sqlite3, json, time, re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "papers.db"
JSON_CLEAN = ROOT / "data" / "papers_clean.json"

def get_attached_driver():
    options = webdriver.ChromeOptions()
    # 【核心魔法】：告诉 Selenium 不要新开浏览器，直接接管本地 9222 端口上的那个
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print("\n[!] 无法接管浏览器。请确保你已经用 --remote-debugging-port=9222 启动了 Chrome！")
        print(f"错误信息: {e}")
        return None

def main():
    if not DB_PATH.exists(): return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 查找还剩下没有摘要的论文
    cur.execute("SELECT id, title FROM papers WHERE (abstract IS NULL OR length(abstract) < 80)")
    rows = cur.fetchall()
    print(f"\n--- [接管模式] 准备抓取剩余的 {len(rows)} 篇论文摘要 ---")
    if not rows:
        print("所有论文都已有摘要啦！")
        return

    driver = get_attached_driver()
    if not driver: return
    print("[+] 成功接管已打开的 Chrome 浏览器！")

    updated = 0
    try:
        for pid, title in rows:
            print(f"\n- 搜索: {title}")
            url = f"https://xueshu.baidu.com/s?wd={urllib.parse.quote(title)}"
            driver.get(url)
            
            # 智能防封禁等待：只要遇到百度安全验证，就挂起死等，绝不报错退出！
            # 这时你只需在页面上手动滑过拼图即可。
            page_title = driver.title or ""
            page_source = driver.page_source or ""
            while "安全验证" in page_title or "tuxing_v2" in page_source:
                print("  [🚨] 触发百度安全验证！请在浏览器中手动滑块... (等待 3 秒后重试)")
                time.sleep(3)
                page_title = driver.title or ""
                page_source = driver.page_source or ""
                if "安全验证" not in page_title and "tuxing_v2" not in page_source:
                    print("  [*] 验证通过！恢复抓取...")
                    driver.get(url) # 过完验证后刷新一下搜素结果
                    time.sleep(2)
                    break
            
            try:
                # 等待列表加载出结果
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".paper-abstract, .c_abstract"))
                )
                
                abs_elements = driver.find_elements(By.CSS_SELECTOR, ".paper-abstract, .c_abstract")
                abstract = ""
                for el in abs_elements:
                    txt = el.text.strip()
                    if len(txt) > 30:
                        abstract = txt
                        break
                
                if abstract:
                    # 清洗前缀
                    abstract = re.sub(r'^(?:【?摘要】?：?|Abstract:?\s*|\[摘要\]\s*)', '', abstract, flags=re.I).strip()
                    print(f"  [+] 成功 ({len(abstract)} 字): {abstract[:30]}...")
                    cur.execute("UPDATE papers SET abstract=? WHERE id=?", (abstract, pid))
                    conn.commit()
                    updated += 1
                else:
                    print("  [-] 搜索结果中未找到有效的摘要文字")
                    
            except Exception as e:
                print("  [-] 未搜索到结果，或页面结构不匹配")
                
            # 适当的等待时间，做一个优雅的爬虫，降低再次触发验证码的几率
            time.sleep(2.5)
            
    except KeyboardInterrupt:
        print("\n[!] 你按下了 Ctrl+C，已安全中断。")
    except Exception as e:
        print(f"\n[!] 脚本异常: {e}")
    finally:
        # 【极其重要】千万不要 driver.quit()，否则会把你当前开着的浏览器关掉！
        print("\n[*] 释放浏览器控制权，浏览器保持打开状态。")

    if updated > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n[!] 完美同步 {updated} 篇论文摘要至 JSON 文件。")

    conn.close()

if __name__ == '__main__': main()