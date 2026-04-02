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
        print("\n[!] 无法接管浏览器。请确保 Chrome 是以 --remote-debugging-port=9222 启动的！")
        return None

def classify_paper(title):
    rules = {
        "A_风险评价": ["风险", "评价", "评估", "HAZOP", "隐患", "模糊综合", "定量风险", "风险矩阵"],
        "B_灾害防控": ["火灾", "爆炸", "泄漏", "消防", "防控", "燃爆", "多米诺", "阻火", "防爆"],
        "D_安全技术监测": ["监测", "物联网", "智能", "预警", "视觉", "检测", "大数据", "数字孪生", "传感器", "算法"],
        "E_事故应急": ["事故", "应急", "救援", "致因", "疏散", "演练", "预案"],
        "F_基础理论": ["理论", "安全文化", "人因", "行为", "心理", "人为", "安全绩效"],
        "G_职业卫生": ["职业卫生", "职业健康", "职业病", "毒物", "噪声", "粉尘", "暴露", "防护"],
        "H_运输储存": ["运输", "储存", "仓储", "物流", "道路", "罐区", "储罐", "管道"],
        "I_园区企业": ["园区", "企业", "中小微", "责任", "审计", "安全监管", "容量"],
        "J_工艺安全": ["工艺", "反应", "反应热", "热失控", "精细化工", "催化", "加氢", "硝化"],
    }
    for cat_id, kws in rules.items():
        if any(kw in title for kw in kws):
            return cat_id
    return "C_安全管理体系"

# 海量深潜词库（去掉了你已经搜完的 A_风险评价 类，直接从 B 类开始）
SEARCH_QUERIES = [
    # 灾害防控类
    {'cat': 'B_灾害防控', 'q': '"化工安全" AND "火灾爆炸"'},
    {'cat': 'B_灾害防控', 'q': '"危险化学品" AND "泄漏扩散"'},
    {'cat': 'B_灾害防控', 'q': '"化工园区" AND "多米诺效应"'},
    # 体系与管理
    {'cat': 'C_安全管理体系', 'q': '"化工企业" AND "安全生产标准化"'},
    {'cat': 'C_安全管理体系', 'q': '"化工企业" AND "双重预防机制"'},
    {'cat': 'C_安全管理体系', 'q': '"石油化工" AND "HSE管理体系"'},
    # 智能化与监测
    {'cat': 'D_安全技术监测', 'q': '"化工安全" AND "物联网"'},
    {'cat': 'D_安全技术监测', 'q': '"化工安全" AND "数字孪生"'},
    {'cat': 'D_安全技术监测', 'q': '"化工生产" AND "机器视觉"'},
    {'cat': 'D_安全技术监测', 'q': '"化工园区" AND "智能预警"'},
    # 事故与应急
    {'cat': 'E_事故应急', 'q': '"化工安全事故" AND "致因分析"'},
    {'cat': 'E_事故应急', 'q': '"化工园区" AND "应急救援"'},
    {'cat': 'E_事故应急', 'q': '"危险化学品" AND "应急物资调度"'},
    # 基础理论与人因
    {'cat': 'F_基础理论', 'q': '"化工企业" AND "不安全行为"'},
    {'cat': 'F_基础理论', 'q': '"化工企业" AND "安全文化建设"'},
    {'cat': 'F_基础理论', 'q': '"化工安全" AND "人因工程"'},
    # 职业卫生
    {'cat': 'G_职业卫生', 'q': '"化工企业" AND "职业病危害"'},
    {'cat': 'G_职业卫生', 'q': '"石油化工" AND "职业暴露"'},
    {'cat': 'G_职业卫生', 'q': '"化工行业" AND "职业健康风险"'},
    # 储运
    {'cat': 'H_运输储存', 'q': '"危险化学品" AND "道路运输安全"'},
    {'cat': 'H_运输储存', 'q': '"化工仓储" AND "安全风险"'},
    {'cat': 'H_运输储存', 'q': '"化工储罐区" AND "安全评价"'},
    # 园区与企业生态
    {'cat': 'I_园区企业', 'q': '"化工园区" AND "封闭化管理"'},
    {'cat': 'I_园区企业', 'q': '"化工园区" AND "安全监管模式"'},
    {'cat': 'I_园区企业', 'q': '"中小化工企业" AND "安全管理对策"'},
    # 工艺本质安全
    {'cat': 'J_工艺安全', 'q': '"精细化工" AND "反应安全风险"'},
    {'cat': 'J_工艺安全', 'q': '"化工工艺" AND "热失控"'}
]

def extract_year(text):
    match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    return int(match.group(1)) if match else 2024

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("SELECT title FROM papers")
    existing_titles = {row[0].replace(" ", "").lower() for row in cur.fetchall()}
    print(f"\n[*] 数据库初始容量： {len(existing_titles)} 篇论文。")

    driver = get_attached_driver()
    if not driver: return
    print("[+] 成功接管浏览器！开启【极缓深度休眠挂机模式】...\n")

    PAGES_PER_QUERY = 15 # 每个长尾词挖 15 页
    new_papers_count = 0
    
    try:
        for search_item in SEARCH_QUERIES:
            cat_label = search_item['cat']
            query_str = search_item['q']
            
            print(f"\n=========================================================")
            print(f"[*] 深潜目标: [{cat_label}]")
            print(f"    搜索语法: {query_str}")
            print(f"=========================================================")
            
            url = f"https://scholar.google.com/scholar?hl=zh-CN&q={urllib.parse.quote(query_str)}"
            driver.get(url)
            
            for page in range(1, PAGES_PER_QUERY + 1):
                print(f"\n--- 正在深潜 [{cat_label}] 的第 {page} 深度 ---")
                
                # 人机验证智能挂起（无限死等，去除了乱码Emoji）
                while "recaptcha" in driver.page_source or "robot" in driver.title.lower() or "人机身份验证" in driver.title:
                    print("\a\a\a  [WARNING] 触发谷歌学术人机验证！程序将在此无限挂起，等待您在浏览器中手动完成验证解封...")
                    time.sleep(10)
                
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".gs_ri"))
                    )
                except:
                    print("  [-] 该深度的文献已穷尽。")
                    break

                # 解析论文块
                paper_blocks = driver.find_elements(By.CSS_SELECTOR, ".gs_ri")
                page_found = 0
                for block in paper_blocks:
                    try:
                        title_el = block.find_element(By.CSS_SELECTOR, ".gs_rt a")
                        title = title_el.text.strip()
                        clean_title = title.replace(" ", "").lower()
                        title = re.sub(r'^\[.*?\]\s*', '', title)
                        
                        if clean_title in existing_titles:
                            continue
                            
                        source_url = title_el.get_attribute("href")
                        meta_text = block.find_element(By.CSS_SELECTOR, ".gs_a").text.strip()
                        author = meta_text.split('-')[0].strip() if '-' in meta_text else ""
                        year = extract_year(meta_text)
                        
                        abstract = ""
                        try:
                            abs_el = block.find_element(By.CSS_SELECTOR, ".gs_rs")
                            abstract = abs_el.text.strip()
                        except: pass
                            
                        print(f"  [+] 捕获新知: {title[:25]}... | {year}年")
                        
                        # 立即存盘保证数据绝对安全
                        cur.execute("""
                            INSERT INTO papers 
                            (title, author, year, abstract, source_url, category_9, directions, db_source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (title, author, year, abstract, source_url, cat_label, cat_label, "GoogleScholar_DeepSleep"))
                        conn.commit()
                        
                        existing_titles.add(clean_title)
                        new_papers_count += 1
                        page_found += 1
                        
                    except Exception as e:
                        continue
                
                print(f"  [*] 本层深度捕获 {page_found} 篇全新论文。累计已吸取: {new_papers_count} 篇。")
                
                # 尝试点击下一页
                if page < PAGES_PER_QUERY:
                    try:
                        next_btn = driver.find_element(By.XPATH, "//span[contains(@class, 'gs_ico_nav_next')] | //b[contains(text(), 'Next')] | //b[contains(text(), '下一页')]")
                        driver.execute_script("arguments[0].click();", next_btn)
                        
                        # 【极速暴风吸入模式】：快速翻页，等待人工处理可能的验证码
                        sleep_time = random.uniform(1.5, 3.5)
                        print(f"  [>>] 快速翻页休眠 {sleep_time:.1f} 秒...")
                        time.sleep(sleep_time)
                    except:
                        print("  [-] 找不到下一页按钮或该类目没有更多结果。")
                        break
                        
    except Exception as e:
        print(f"\n[!] 脚本异常中断: {e}")
    finally:
        print("\n[*] 挂机结束。释放浏览器控制权。")

    if new_papers_count > 0:
        cur.execute("PRAGMA table_info(papers)")
        cols = [d[1] for d in cur.fetchall()]
        cur.execute("SELECT * FROM papers")
        data = json.loads(JSON_CLEAN.read_text(encoding='utf-8'))
        data['papers'] = [dict(zip(cols, r)) for r in cur.fetchall()]
        JSON_CLEAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n[!] 守夜人任务圆满结束！共计强力注入了 {new_papers_count} 篇全新论文入库！")
    else:
        print("\n[!] 今夜没有捕获到新论文。")

    conn.close()

if __name__ == '__main__': main()