import time
from selenium import webdriver
from selenium.webdriver.common.by import By

def main():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
    except:
        print("[!] 无法连接到 9222 端口")
        return

    # 切换到用户最近活动的那个标签页
    driver.switch_to.window(driver.window_handles[-1])
    
    print("\n[*] 成功连接！当前所在页面:")
    print("    标题:", driver.title)
    print("    网址:", driver.current_url)
    
    print("\n[*] 正在扫描页面上有可能是论文列表的区域...")
    
    # 搜寻所有包含链接的大块
    blocks = driver.find_elements(By.CSS_SELECTOR, "div, li, tr")
    candidates = []
    for b in blocks:
        try:
            txt = b.text.strip()
            if "化工" in txt and "安全" in txt and len(txt) > 50 and len(txt) < 1000:
                candidates.append((b.tag_name, b.get_attribute("class"), txt))
        except:
            pass
            
    if not candidates:
        print("    [-] 当前页面没有发现包含 '化工' 和 '安全' 的论文列表块！")
    else:
        print(f"    [+] 发现 {len(candidates)} 个可能的论文区块！")
        print("\n--- 这是最典型的一个区块的内容：---")
        tag, cls, txt = candidates[-1]
        print(f"Tag: <{tag}>, Class: '{cls}'")
        print(txt)
        print("-----------------------------------------\n")
        
    driver.quit() # 这里因为只做短暂探测，不影响其他，也可以不退出

if __name__ == '__main__': main()