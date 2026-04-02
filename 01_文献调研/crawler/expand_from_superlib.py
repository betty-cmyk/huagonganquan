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
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        return webdriver.Chrome(options=options)
    except Exception as e:
        print("\n[!] 无法接管浏览器。请确保你已经用 --remote-debugging-port=9222 启动了 Chrome！")
        return None

# 新论文的简易分类器，保持与你现有体系一致
def classify_paper(title):
    rules = {
        "A_风险评价": ["风险", "评价", "评估", "HAZOP", "隐患"],
        "B_灾害防控": ["火灾", "爆炸", "泄漏", "消防", "防控"],
        "D_安全技术监测": ["监测", "物联网", "智能", "预警", "视觉", "检测"],
        "E_事故应急": ["事故", "应急", "救援"],
        "G_职业卫生": ["职业卫生", "职业健康", "职业病", "毒物"],
        "H_运输储存": ["运输", "储存", "仓储", "危化品道路"],
        "I_园区企业": ["园区", "企业"],
        "J_工艺安全": ["工艺", "反应"],
    }
    for cat_id, kws in rules.items():
        if any(kw in title for kw in kws):
            return cat_id
    return "C_安全管理体系" # 兜底

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # 先把数据库里已有的论文标题存进一个集合，防止抓到重复的
    cur.execute("SELECT title FROM papers")
    existing_titles = {row[0].replace(" ", "") for row in cur.fetchall()}
    print(f"\n[*] 数据库中已有 {len(existing_titles)} 篇论文。")

    driver = get_attached_driver()
    if not driver: return
    print("[+] 成功接管已打开的 Chrome 浏览器！开始从全国图书馆参考联盟扩容新论文...\n")

    search_keyword = "化工安全"
    pages_to_scrape = 5 # 打算抓取几页
    new_papers_count = 0
    
    try:
        print(f"[*] 准备进行第一步：首页输入关键词 '{search_keyword}' 并搜索。")
        driver.get("http://jour.ucdrs.superlib.net/")
        time.sleep(3)
        
        # 尝试切换到“学位论文”或“期刊”选项卡（根据网站结构可能会有 radio button）
        try:
            driver.find_element(By.XPATH, "//label[contains(text(), '学位论文')]").click()
        except:
            pass # 如果没有就算了，直接搜
            
        # 找到输入框并模拟输入（防止 URL 编码乱码问题）
        search_input = driver.find_element(By.ID, "sw") # 假设输入框 ID 为 sw
        search_input.clear()
        search_input.send_keys(search_keyword)
        
        # 点击搜索按钮
        search_btn = driver.find_element(By.CSS_SELECTOR, ".btn_search, .btn_search1, input[type='submit']")
        search_btn.click()
        
        # 给点时间让结果页加载出来
        time.sleep(5)
        
        for page in range(1, pages_to_scrape + 1):
            print(f"\n==================== 正在抓取 第 {page} 页 ====================")
            
            # 如果遇到登录或验证码
            while "login.action" in driver.current_url or "验证码" in driver.page_source:
                print("  [🚨] 被拦截或要求登录！请在浏览器中手动完成登录/验证... (等待中)")
                time.sleep(5)
            
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".book1"))
                )
            except:
                print("  [-] 这一页没有加载出 .book1 元素。如果是没有下一页了，请按 Ctrl+C 中断。")
                print("  [!] 正在重试或等待用户在浏览器中手动翻页...")
                time.sleep(5)
                # 重新尝试一次
                try:
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".book1")))
                except:
                    print("  [-] 确实没有数据了。抓取结束。")
                    break

            paper_blocks = driver.find_elements(By.CSS_SELECTOR, ".book1")
            if not paper_blocks:
                print("  [-] 未找到论文列表块，抓取结束。")
                break
                
            for block in paper_blocks:
                try:
                    title_el = block.find_element(By.CSS_SELECTOR, ".book1_title a")
                    title = title_el.text.strip()
                    
                    clean_title = title.replace(" ", "")
                    if clean_title in existing_titles:
                        continue
                        
                    source_url = title_el.get_attribute("href")
                    
                    meta_text = block.find_element(By.CSS_SELECTOR, ".book1_author").text.strip()
                    author = ""
                    year = 2024
                    year_match = re.search(r'\d{4}', meta_text)
                    if year_match: year = int(year_match.group())
                    author_match = re.search(r'作者：(.*?)\s', meta_text + " ")
                    if author_match: author = author_match.group(1)
                    
                    abstract = ""
                    try:
                        abs_el = block.find_element(By.CSS_SELECTOR, ".book1_intr")
                        abstract = abs_el.text.strip()
                        abstract = re.sub(r'^(?:摘要：|简介：)', '', abstract).strip()
                    except:
                        pass
                        
                    category = classify_paper(title)
                    print(f"  [+] 发现新论文: {title[:20]}... | {category} | {year}")
                    
                    cur.execute("""
                        INSERT INTO papers 
                        (title, author, year, abstract, source_url, category_9, directions, db_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, author, year, abstract, source_url, category, category, "SuperLib_自动扩充"))
                    
                    existing_titles.add(clean_title)
                    new_papers_count += 1
                    
                except Exception as e:
                    print(f"  [-] 解析某条记录出错: {str(e)[:50]}")
                    continue
            
            # 自动点击下一页
            if page < pages_to_scrape:
                try:
                    # 匹配“下一页”按钮。根据具体网站结构可能不同，最常见的是 <a> 标签
                    next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
                    next_btn.click()
                    print("  [*] 成功点击下一页")
                    time.sleep(4)
                except:
                    print("  [-] 找不到下一页按钮，可能已经到底了。")
                    break
            
    except Exception as e:
        print(f"\n[!] 脚本异常中断: {e}")
    finally:
        print("\n[*] 释放浏览器控制权。")

    if new_papers_count > 0:
        conn.commit()
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n[!] 完美收官！成功扩容了 {new_papers_count} 篇全新的论文并同步至 JSON。")
    else:
        print("\n[!] 没有抓取到新论文（可能是重复了，或者还没扫到新内容）。")

    conn.close()

if __name__ == '__main__': main()