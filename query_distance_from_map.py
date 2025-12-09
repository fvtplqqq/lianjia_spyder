import pandas as pd
import requests
import json
import time
import sys
import warnings
from openpyxl import load_workbook
from api_key import BAIDU_MAP_AK

# 忽略Pandas的版本警告
warnings.filterwarnings("ignore", message="Pandas requires version")

# 百度地图API密钥（需自行申请）


def get_coordinates(address, city="上海市"):
    """获取地址的经纬度坐标"""
    try:
        url = f"http://api.map.baidu.com/geocoding/v3/?address={address}&city={city}&output=json&ak={BAIDU_MAP_AK}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data['status'] == 0:
            location = data['result']['location']
            return f"纬度 {location['lat']}, 经度 {location['lng']}"
        elif data['status'] == 302:  # 配额超限错误码
            print("\n错误：API配额已用尽")
            return "QUOTA_EXCEEDED"
        else:
            print(f"获取坐标失败：{data['message']}")
            return ""
    except Exception as e:
        print(f"获取坐标异常：{str(e)}")
        return ""


def get_driving_info(origin, destination):
    """获取驾车路线信息"""
    try:
        url = f"http://api.map.baidu.com/directionlite/v1/driving?origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}&ak={BAIDU_MAP_AK}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data['status'] == 0:
            route = data['result']['routes'][0]
            distance = route['distance']  # 单位：米
            duration = route['duration']  # 单位：秒
            return distance / 1000, duration / 60  # 返回公里和分钟
        elif data['status'] == 302:  # 配额超限错误码
            print("\n错误：API配额已用尽")
            return "QUOTA_EXCEEDED", "QUOTA_EXCEEDED"
        else:
            print(f"获取驾车路线失败：{data['message']}")
            return None, None
    except Exception as e:
        print(f"获取驾车信息异常：{str(e)}")
        return None, None


def get_transit_info(origin, destination):
    """获取公共交通信息"""
    try:
        url = f"http://api.map.baidu.com/directionlite/v1/transit?origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}&ak={BAIDU_MAP_AK}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data['status'] == 0 and data['result']['routes']:
            best_route = min(data['result']['routes'], key=lambda x: x['duration'])
            duration = best_route['duration']  # 总时间（秒）
            return duration / 60  # 返回分钟
        elif data['status'] == 302:  # 配额超限错误码
            print("\n错误：API配额已用尽")
            return "QUOTA_EXCEEDED"
        else:
            print(f"获取公共交通信息失败：{data.get('message', '无合适路线')}")
            return None
    except Exception as e:
        print(f"获取公共交通信息异常：{str(e)}")
        return None


def parse_coordinates(coord_str):
    """从字符串解析坐标"""
    if not coord_str or not isinstance(coord_str, str):
        return None, None
    try:
        lat = float(coord_str.split("纬度 ")[1].split(",")[0])
        lng = float(coord_str.split("经度 ")[1])
        return lat, lng
    except:
        return None, None


def process_excel(input_file):
    """处理Excel文件"""
    try:
        # 生成输出文件名（自动添加"-结果"后缀）
        if input_file.endswith('.xlsx'):
            output_file = input_file.replace('.xlsx', '-结果.xlsx')
        else:
            output_file = input_file + '-结果.xlsx'

        # 尝试使用openpyxl引擎读取Excel
        try:
            df = pd.read_excel(input_file, engine='openpyxl')
        except:
            # 如果失败，尝试其他引擎
            try:
                df = pd.read_excel(input_file, engine='xlrd')
            except:
                print("无法读取Excel文件，请确保文件格式正确且已安装必要的依赖包")
                return

        # 检查必要列是否存在
        required_columns = ['出发地', '目的地坐标']
        for col in required_columns:
            if col not in df.columns:
                print(f"缺少必要列：{col}")
                return

        # 解析目的地坐标（假设所有行的目的地坐标相同）
        dest_coord_str = df.iloc[0]['目的地坐标']
        dest_lat, dest_lng = parse_coordinates(dest_coord_str)
        if dest_lat is None:
            print("无法解析目的地坐标")
            return

        # 添加新列（如果不存在）
        new_columns = {
            '出发地坐标': "",
            '行车距离(公里)': None,
            '行车时间(分钟)': None,
            '公共交通时间(分钟)': None
        }

        for col, default_value in new_columns.items():
            if col not in df.columns:
                df[col] = default_value

        # 处理每一行数据
        quota_exceeded = False
        for index, row in df.iterrows():
            try:
                print(f"\n处理第 {index + 1}/{len(df)} 行: {row['出发地']}")

                # 检查配额是否已用尽
                if quota_exceeded:
                    print("\nAPI配额已用尽，停止处理")
                    break

                # 1. 获取出发地坐标（如果为空）
                if pd.isna(row['出发地坐标']) or row['出发地坐标'] == "":
                    coord_result = get_coordinates(row['出发地'])
                    if coord_result == "QUOTA_EXCEEDED":
                        quota_exceeded = True
                        break
                    df.at[index, '出发地坐标'] = coord_result
                    time.sleep(1)  # 避免请求过于频繁

                # 2. 解析出发地坐标
                start_lat, start_lng = parse_coordinates(df.at[index, '出发地坐标'])
                if start_lat is None:
                    print(f"无法解析出发地坐标: {row['出发地']}")
                    continue

                # 3. 获取行车信息
                if pd.isna(row['行车距离(公里)']):
                    distance, driving_time = get_driving_info((start_lat, start_lng), (dest_lat, dest_lng))
                    if distance == "QUOTA_EXCEEDED":
                        quota_exceeded = True
                        break
                    if distance:
                        df.at[index, '行车距离(公里)'] = round(distance, 2)
                        df.at[index, '行车时间(分钟)'] = round(driving_time, 1)
                        time.sleep(1)

                # 4. 获取公共交通信息
                if pd.isna(row['公共交通时间(分钟)']):
                    transit_time = get_transit_info((start_lat, start_lng), (dest_lat, dest_lng))
                    if transit_time == "QUOTA_EXCEEDED":
                        quota_exceeded = True
                        break
                    if transit_time:
                        df.at[index, '公共交通时间(分钟)'] = round(transit_time, 1)
                        time.sleep(1)

                # 每处理5行保存一次进度
                if (index + 1) % 5 == 0:
                    df.to_excel(output_file, index=False, engine='openpyxl')
                    print(f"已保存临时进度到 {output_file}")

            except Exception as e:
                print(f"处理第 {index + 1} 行出错: {str(e)}")
                continue

        # 最终保存结果
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n处理完成，结果已保存到 {output_file}")

    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")


if __name__ == "__main__":

    input_file = 'data\小区信息20250816 - 副本.xlsx'
    print(f"开始处理文件: {input_file}")
    process_excel(input_file)