import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
from pathlib import Path
from datetime import datetime
import random
# 在文件顶部添加
import os
from pathlib import Path

# 配置文件路径
CONFIG_FILE = 'config.json'
SESSION_FILE = 'lianjia_session.json'
OUTPUT_FILE = f'链家租房数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

# 修改OUTPUT_FILE的定义，使其可以被其他模块导入
DATA_DIR = 'data'
OUTPUT_FILE = os.path.join(DATA_DIR, f'链家租房数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')

def load_session():
    """从文件加载session"""
    if not Path(SESSION_FILE).exists():
        print(f"Session文件 {SESSION_FILE} 不存在，请先运行save_session.py")
        return None

    try:
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)

        session = requests.Session()
        session.cookies.update(session_data['cookies'])
        session.headers.update(session_data['headers'])
        return session
    except Exception as e:
        print(f"加载session失败: {str(e)}")
        return None


def load_config():
    """从配置文件加载URL列表"""
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


def fetch_page(session, url: str, retry=3) -> BeautifulSoup:
    """获取页面内容（带自动重试）"""
    for attempt in range(retry):
        try:
            time.sleep(random.uniform(0.8, 1.4))  # 随机延迟

            response = session.get(url, timeout=15)
            if "captcha" in response.url:
                raise Exception("触发人机验证")

            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')

        except Exception as e:
            if attempt == retry - 1:
                print(f"请求失败（已达最大重试次数）: {url} - {str(e)}")
            else:
                print(f"请求失败（即将重试）: {url} - {str(e)}")
                time.sleep(5)
    return None


def extract_location_info(des_tag):
    """提取三级位置信息"""
    location_data = {
        '一级区域': '',
        '二级区域': '',
        '小区名称': '',
        '小区链接': ''
    }

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
    """解析单个房源信息（保持原有字段结构）"""
    data = {}
    try:
        # 1. 基础信息
        title_tag = house.find('a', class_='content__list--item--aside')
        data['标题'] = title_tag.get('title', '').strip() if title_tag else ''
        data['链接'] = 'https://sh.lianjia.com' + title_tag.get('href', '').strip() if title_tag else ''

        # 2. 价格信息
        price_tag = house.find('span', class_='content__list--item-price')
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            data['价格(元)'] = int(re.sub(r'\D', '', price_text))
            data['价格单位'] = price_text.replace(str(data['价格(元)']), '').strip()

        # 3. 位置信息
        des_tag = house.find('p', class_='content__list--item--des')
        data.update(extract_location_info(des_tag))

        # 4. 房屋特征
        if des_tag:
            features = [f.strip() for f in des_tag.stripped_strings if f.strip() not in ['-', '/']]
            for item in features:
                if '㎡' in item:
                    data['面积(㎡)'] = float(re.search(r'(\d+\.?\d*)', item).group(1))
                elif any(c in item for c in ['东', '南', '西', '北']):
                    data['朝向'] = item
                elif any(c in item for c in ['室', '厅', '卫']):
                    data['户型'] = item
                elif '层' in item:
                    data['楼层'] = item
                    if '（' in item and '）' in item:
                        data['总楼层'] = int(re.search(r'(\d+)层', item).group(1))
                elif '年建' in item:
                    data['建成年份'] = int(re.search(r'(\d+)', item).group(1))

        # 5. 标签信息
        tags = house.find('p', class_='content__list--item--bottom')
        if tags:
            tag_list = [tag.get_text(strip=True) for tag in tags.find_all('i')]
            data['标签'] = '|'.join(tag_list)
            data['官方核验'] = '官方核验' in tag_list
            data['近地铁'] = '近地铁' in tag_list
            data['精装'] = '精装' in tag_list

        # 6. 其他信息
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
    """保存数据到Excel（保持原有格式）"""
    try:
        # 确保关键字段存在
        for col in ['一级区域', '二级区域', '小区名称']:
            if col not in df.columns:
                df[col] = ''

        # 调整列顺序
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


def main():
    target_urls, max_pages, delay = load_config()
    session = load_session()

    if not session:
        print("无法创建有效会话，程序终止")
        return

    all_data = []

    for base_url in target_urls:
        print(f"\n开始爬取: {base_url}")
        page = 1
        total_pages = None  # 初始化为None，表示尚未获取总页数

        while True:
            # 检查是否超过最大页数限制
            if page > max_pages:
                print(f"已达到最大页数限制({max_pages})，停止爬取")
                break

            url = f"{base_url}pg{page}/"
            print(f"正在处理第 {page} 页...")

            soup = fetch_page(session, url)
            if not soup:
                break

            # 如果是第一页，尝试获取总页数
            if page == 1 and total_pages is None:
                pagination = soup.find('div', class_='content__pg')
                if pagination and 'data-totalpage' in pagination.attrs:
                    total_pages = int(pagination['data-totalpage'])
                    print(f"检测到总页数: {total_pages}")

            houses = soup.find_all('div', class_='content__list--item')
            if not houses:
                print(f"第 {page} 页无数据，停止爬取")
                break

            for house in houses:
                house_data = parse_house(house)
                if house_data:
                    all_data.append(house_data)

            # 检查是否还有下一页
            if total_pages is not None:
                if page >= total_pages:
                    print("已到达最后一页，停止爬取")
                    break
            else:
                # 如果没有获取到总页数，使用备用方法检查是否有下一页
                next_page = soup.find('a', class_='content__pg--next')
                if not next_page or 'disabled' in next_page.get('class', []):
                    print("未检测到下一页按钮，停止爬取")
                    break

            page += 1
            time.sleep(delay + random.uniform(0, 1))  # 基础延迟+随机波动

    if all_data:
        df = pd.DataFrame(all_data)

        # 确保数据目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

        # 保存数据到文件
        save_to_excel(df, OUTPUT_FILE)

        # 将最新文件名保存到last_file.txt
        with open('last_file.txt', 'w', encoding='utf-8') as f:
            f.write(OUTPUT_FILE)

        print(f"最新数据文件已保存到: {OUTPUT_FILE}")
        
    else:
        print("没有获取到任何数据")


if __name__ == "__main__":
    main()