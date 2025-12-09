# lianjia_selenium_crawler.py
import time
import random
import json
import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 配置路径
CONFIG_FILE = 'config.json'
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, f'链家租房数据_Selenium_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')


def init_driver():
    """初始化带持久化配置的 Chrome 浏览器"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("user-data-dir=C:\\Temp\\LianjiaProfile_Selenium")  # 保存登录/验证状态

    # 静默模式（可选）：取消下面两行注释可后台运行（但无法人工过验证！）
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-gpu")

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                delete navigator.__proto__.webdriver;
                window.navigator.permissions.query = (parameters) => {
                    return parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters);
                };
            '''
        })
        return driver
    except Exception as e:
        print(f"初始化浏览器失败: {e}")
        return None


def load_config():
    if not Path(CONFIG_FILE).exists():
        default_config = {
            "urls": [
                "https://sh.lianjia.com/zufang/jingan/rco11rt200600000001ra1ra2ra3ra4ra5rp6rp7rp4rp5",
                "https://sh.lianjia.com/zufang/xuhui/rco11rt200600000001ra1ra2ra3ra4ra5rp6rp7rp4rp5"
            ],
            "max_pages": 5,
            "delay": 3
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print(f"已创建默认配置文件 {CONFIG_FILE}")

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config['urls'], config.get('max_pages', 5), config.get('delay', 1)


# ========== 保留你原有的解析函数 ==========

def extract_location_info(des_tag):
    location_data = {'一级区域': '', '二级区域': '', '小区名称': '', '小区链接': ''}
    if des_tag:
        try:
            links = des_tag.find_all('a')
            if len(links) >= 1:
                location_data['一级区域'] = links[0].get_text(strip=True)
            if len(links) >= 2:
                location_data['二级区域'] = links[1].get_text(strip=True)
            if len(links) >= 3:
                location_data['小区名称'] = links[2].get_text(strip=True)
                location_data['小区链接'] = 'https://sh.lianjia.com' + links[2]['href']
        except Exception as e:
            print(f"提取位置信息出错: {str(e)}")
    return location_data


def parse_house(house) -> dict:
    data = {}
    try:
        title_tag = house.find('a', class_='content__list--item--aside')
        data['标题'] = title_tag.get('title', '').strip() if title_tag else ''
        data['链接'] = 'https://sh.lianjia.com' + title_tag.get('href', '').strip() if title_tag else ''

        price_tag = house.find('span', class_='content__list--item-price')
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            data['价格(元)'] = int(''.join(filter(str.isdigit, price_text)))
            data['价格单位'] = price_text.replace(str(data['价格(元)']), '').strip()

        des_tag = house.find('p', class_='content__list--item--des')
        data.update(extract_location_info(des_tag))

        if des_tag:
            features = [f.strip() for f in des_tag.stripped_strings if f.strip() not in ['-', '/']]
            for item in features:
                if '㎡' in item:
                    data['面积(㎡)'] = float(''.join(filter(lambda x: x.isdigit() or x == '.', item)))
                elif any(c in item for c in ['东', '南', '西', '北']):
                    data['朝向'] = item
                elif any(c in item for c in ['室', '厅', '卫']):
                    data['户型'] = item
                elif '层' in item:
                    data['楼层'] = item
                    if '（' in item and '）' in item:
                        nums = re.findall(r'(\d+)层', item)
                        if nums:
                            data['总楼层'] = int(nums[-1])
                elif '年建' in item:
                    data['建成年份'] = int(''.join(filter(str.isdigit, item)))

        tags = house.find('p', class_='content__list--item--bottom')
        if tags:
            tag_list = [tag.get_text(strip=True) for tag in tags.find_all('i')]
            data['标签'] = '|'.join(tag_list)
            data['官方核验'] = '官方核验' in tag_list
            data['近地铁'] = '近地铁' in tag_list
            data['精装'] = '精装' in tag_list

        brand_tag = house.find('p', class_='content__list--item--brand')
        if brand_tag:
            data['中介公司'] = brand_tag.find('span', class_='brand').get_text(strip=True) if brand_tag.find('span',
                                                                                                             class_='brand') else ''
            data['维护时间'] = brand_tag.find('span', class_='content__list--item--time').get_text(
                strip=True) if brand_tag.find('span', class_='content__list--item--time') else ''

        data['必看好房'] = bool(house.find('img', alt='必看好房'))
        data['VR看房'] = bool(house.find('i', class_='vr-logo'))
        data['爬取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        print(f"解析房源出错: {str(e)}")
    return data


def save_to_excel(df: pd.DataFrame, filename: str):
    try:
        for col in ['一级区域', '二级区域', '小区名称']:
            if col not in df.columns:
                df[col] = ''
        priority_cols = ['一级区域', '二级区域', '小区名称', '价格(元)', '面积(㎡)', '户型', '标题']
        remaining_cols = [col for col in df.columns if col not in priority_cols]
        df = df[priority_cols + remaining_cols]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
            worksheet = writer.sheets['Sheet1']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
        print(f"数据已保存到 {filename}")
    except Exception as e:
        print(f"保存Excel失败: {str(e)}")
        csv_file = filename.replace('.xlsx', '.csv')
        df.to_csv(csv_file, index=False, encoding='utf_8_sig')
        print(f"已改为保存到CSV文件: {csv_file}")


# ============================================

def crawl_with_selenium():
    urls, max_pages, base_delay = load_config()
    driver = init_driver()
    if not driver:
        return

    all_data = []

    try:
        for base_url in urls:
            print(f"\n🚀 开始爬取区域: {base_url}")
            page = 1

            for page in range(1, max_pages + 1):
                url = f"{base_url}pg{page}/"
                print(f"  ➤ 访问第 {page} 页: {url}")

                driver.get(url)
                time.sleep(2)

                # 检查是否跳转到验证码/拦截页
                current_url = driver.current_url
                if "captcha" in current_url or "verify" in current_url or "unauthorized" in current_url:
                    print("⚠️ 检测到人机验证或拦截页面，请手动完成验证...")
                    input("👉 验证完成后，请确保已回到房源列表页，然后按回车继续...")

                # 解析页面
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                houses = soup.find_all('div', class_='content__list--item')

                if not houses:
                    print("  📭 本页无房源，提前终止")
                    break

                print(f"  📥 解析到 {len(houses)} 条房源")

                # 提取数据
                for house in houses:
                    house_data = parse_house(house)
                    if house_data.get('标题'):
                        all_data.append(house_data)

                # ✅ 核心逻辑：如果本页 < 30 条，说明是最后一页，停止翻页
                if len(houses) < 30:
                    print("  🛑 本页房源少于30条，判定为最后一页，停止翻页")
                    break

                # 延迟
                delay = base_delay + random.uniform(0.5, 1.5)
                print(f"  ⏳ 等待 {delay:.1f} 秒后加载下一页...")
                time.sleep(delay)

    finally:
        driver.quit()

    # 保存结果
    if all_data:
        df = pd.DataFrame(all_data)
        save_to_excel(df, OUTPUT_FILE)
        with open('last_file.txt', 'w', encoding='utf-8') as f:
            f.write(OUTPUT_FILE)
        print(f"\n✅ 全部完成！共爬取 {len(all_data)} 条数据")
    else:
        print("❌ 未获取到任何数据")


if __name__ == "__main__":
    crawl_with_selenium()