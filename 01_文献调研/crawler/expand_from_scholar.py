# -*- coding: utf-8 -*-
import sqlite3, json, time, re, random
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
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        return webdriver.Chrome(options=options)
    except Exception as e:
        print("\n[!] 无法接管浏览器。请确保你已经用 --remote-debugging-port=9222 启动了 Chrome！")
        return None

def classify_paper(title):
    rules = {
        "A_风险评价": ["风险", "评价", "评估", "HAZOP", "隐患", "模糊综合", "定量"],
        "B_灾害防控": ["火灾", "爆炸", "泄漏", "消防", "防控", "燃爆", "多米诺"],
        "D_安全技术监测": ["监测", "物联网", "智能", "预警", "视觉", "检测", "大数据", "数字孪生", "AI"],
        "E_事故应急": ["事故", "应急", "救援", "致因", "疏散"],
        "F_基础理论": ["理论", "安全文化", "人因", "行为", "心理"],
        "G_职业卫生": ["职业卫生", "职业健康", "职业病", "毒物", "噪声", "暴露"],
        "H_运输储存": ["运输", "储存", "仓储", "物流", "危化品道路"],
        "I_园区企业": ["园区", "企业", "中小微", "责任"],
        "J_工艺安全": ["工艺", "反应", "反应热", "热失控", "精细化工"],
    }
    for cat_id, kws in rules.items():
        if any(kw in title for kw in kws):
            return cat_id
    return "C_安全管理体系"

# 涵盖 10 个领域的深度搜索词
SEARCH_QUERIES = [
    {'cat': 'A_风险评价', 'q': '"化工安全" AND ("风险评价" OR "HAZOP" OR "定量风险")'},
    {'cat': 'B_灾害防控', 'q': '"化工安全" AND ("泄漏扩散" OR "火灾" OR "爆炸" OR "多米诺效应")'},
    {'cat': 'C_安全管理体系', 'q': '"化工安全" AND ("管理体系" OR "HSE" OR "双重预防机制")'},
    {'cat': 'D_安全技术监测', 'q': '"化工安全" AND ("物联网" OR "数字孪生" OR "机器视觉" OR "智能预警")'},
    {'cat': 'E_事故应急', 'q': '"化工安全" AND ("应急救援" OR "事故演化" OR "应急物资" OR "事故致因")'},
    {'cat': 'F_基础理论', 'q': '"化工安全" AND ("安全原理" OR "人因工程" OR "不安全行为")'},
    {'cat': 'G_职业卫生', 'q': '"化工" AND ("职业卫生" OR "职业健康" OR "职业暴露" OR "职业病")'},
    {'cat': 'H_运输储存', 'q': '"危险化学品" AND ("道路运输" OR "仓储安全" OR "路径优化")'},
    {'cat': 'I_园区企业', 'q': '"化工园区" AND ("安全容量" OR "封闭化管理" OR "安全监管")'},
    {'cat': 'J_工艺安全', 'q': '"精细化工" AND ("反应安全" OR "热失控" OR "工艺风险")'}
]

def extract_year(text):
    match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    return int(match.group(1)) if match else 2024

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("SELECT title FROM papers")
    existing_titles = {row[0].replace(" ", "").lower() for row in cur.fetchall()}
    print(f"\n[*] 数据库已有 {len(existing_titles)} 篇论文。")

    driver = get_attached_driver()
    if not driver: return
    print("[+] 成功接管浏览器！开启十大领域【深度扩容模式】...\n")

    pages_per_category = 5 # 每个分类抓 5 页
    new_papers_count = 0
    
    try:
        for search_item in SEARCH_QUERIES:
            cat_label = search_item['cat']
            query_str = search_item['q']
            
            print(f"\n=========================================================")
            print(f"[*] 正在定向检索: [{cat_label}]")
            print(f"    搜索词: {query_str}")
            print(f"=========================================================")
            
            url = f"https://scholar.google.com/scholar?hl=zh-CN&q={urllib.parse.quote(query_str)}"
            driver.get(url)
            time.sleep(2)
            
            for page in range(1, pages_per_category + 1):
                print(f"\n--- 正在吸取 [{cat_label}] 的第 {page} 页 ---")
                
                while "recaptcha" in driver.page_source or "robot" in driver.title.lower() or "人机身份验证" in driver.title:
                    print("  [🚨] 触发谷歌学术人机验证！请手动打钩或选图... (等待中)")
                    time.sleep(5)
                
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".gs_ri"))
                    )
                except:
                    print("  [-] 当前页似乎没有搜索结果，已到底。")
                    break

                paper_blocks = driver.find_elements(By.CSS_SELECTOR, ".gs_ri")
                for block in paper_blocks:
                    try:
                        title_el = block.find_element(By.CSS_SELECTOR, ".gs_rt a")
                        title = title_el.text.strip()
                        
                        clean_title = title.replace(" ", "").lower()
                        title = re.sub(r'^\[.*?\]\s*', '', title)
                        
                        if clean_title in existing_titles:
                            continue
                            
                        # 抓取真实 URL 和 摘要
                        source_url = title_el.get_attribute("href")
                        
                        meta_text = block.find_element(By.CSS_SELECTOR, ".gs_a").text.strip()
                        author = meta_text.split('-')[0].strip() if '-' in meta_text else ""
                        year = extract_year(meta_text)
                        
                        abstract = ""
                        try:
                            abs_el = block.find_element(By.CSS_SELECTOR, ".gs_rs")
                            abstract = abs_el.text.strip()
                        except:
                            pass
                            
                        print(f"  [+] 收录: {title[:25]}... | {year}年")
                        
                        cur.execute("""
                            INSERT INTO papers 
                            (title, author, year, abstract, source_url, category_9, directions, db_source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (title, author, year, abstract, source_url, cat_label, cat_label, "GoogleScholar_深度扩充"))
                        
                        existing_titles.add(clean_title)
                        new_papers_count += 1
                        
                    except Exception as e:
                        continue
                        
                if page < pages_per_category:
                    try:
                        next_btn = driver.find_element(By.XPATH, "//span[contains(@class, 'gs_ico_nav_next')] | //b[contains(text(), 'Next')] | //b[contains(text(), '下一页')]")
                        driver.execute_script("arguments[0].click();", next_btn)
                        
                        # 随机停顿 3-6 秒，装得像人一点
                        sleep_time = random.uniform(3, 6)
                        print(f"  [*] 翻到下一页 (休眠 {sleep_time:.1f} 秒)...")
                        time.sleep(sleep_time)
                    except:
                        print("  [-] 找不到下一页按钮或该类目没有更多结果。")
                        break
                        
    except Exception as e:
        print(f"\n[!] 脚本异常中断: {e}")
    finally:
        print("\n[*] 释放 Google Scholar 浏览器控制权。")

    if new_papers_count > 0:
        conn.commit()
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n[!] 震撼！成功向图谱强力注入了 {new_papers_count} 篇全新论文（带摘要和URL）。")
    else:
        print("\n[!] 没有抓取到新论文。")

    conn.close()

if __name__ == '__main__': main()