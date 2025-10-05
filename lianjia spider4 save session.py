import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path

SESSION_FILE = 'lianjia_session.json'


def init_selenium():
    """初始化Selenium浏览器"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("user-data-dir=C:\\Temp\\LianjiaProfile")  # 保存登录状态

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        return driver
    except Exception as e:
        print(f"Selenium初始化失败: {str(e)}")
        return None


def save_session_to_file():
    """通过Selenium获取有效的requests会话并保存到文件"""
    driver = init_selenium()
    if not driver:
        return False

    try:
        # 访问链家首页获取初始Cookies
        driver.get("https://sh.lianjia.com/")
        time.sleep(2)

        # 访问租房页面触发验证（如果需要）
        driver.get("https://sh.lianjia.com/zufang/")
        print("请手动完成人机验证（如有）...")
        input("👉 验证完成后按回车键继续...")

        # 获取验证后的Cookies
        cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}

        # 获取User-Agent
        user_agent = driver.execute_script("return navigator.userAgent;")

        # 准备保存的数据
        session_data = {
            'cookies': cookies,
            'headers': {
                'User-Agent': user_agent,
                'Referer': 'https://sh.lianjia.com/',
                'Accept-Language': 'zh-CN,zh;q=0.9'
            }
        }

        # 保存到文件
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)

        print(f"Session已保存到 {SESSION_FILE}")
        return True
    finally:
        driver.quit()


if __name__ == "__main__":
    if save_session_to_file():
        print("登录成功，session已保存。现在可以运行爬虫脚本了。")
    else:
        print("登录失败，请检查问题后重试。")