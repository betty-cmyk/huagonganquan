# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By

def main():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        print("[+] 成功连接浏览器。当前页面:", driver.title)
        
        # 找到页面中最大的列表块
        items = driver.find_elements(By.CSS_SELECTOR, ".book1, li, tr")
        for item in items:
            html = item.get_attribute('innerHTML')
            if "化工" in html or "安全" in html:
                print("\n--- 找到相关区块，它的内部 HTML 结构是：---")
                # 截取前 800 个字符展示
                print(html.strip()[:800])
                break
        print("\n[*] 调查结束。")
    except Exception as e:
        print("[!] 连接失败:", e)

if __name__ == '__main__': main()