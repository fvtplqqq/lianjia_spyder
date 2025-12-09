
第一个git项目，请多指教！
python版本 3.9

功能说明

lianjia_selenium_crawler.py
爬取链家租房网站，原来用request+bs4方法，到第10页必跳人机。改用selenium方法，跳人机在chrome窗口人工处理。
1>在config.json中配置要爬取的链家租房区域
2>运行本程序，在必要时需人工在chrome中处理人机验证
3>运行结果为 data\链家租房数据_Selenium_20251210_050145.xlsx

sendmail.py
将爬取的excel文件发送邮件
1>在api_key.py 中配置邮箱授权码，和收件人
2>运行本程序即发送邮件（推荐用163邮箱作为发件邮箱，QQ邮箱作为发件邮箱不稳定）

query_distance_from_map.py
调用百度地图的api，查询目的地和小区间的距离、行车时间、公共交通时间等
1>在api_key.py 中配置百度地图授权码
2>手工整理 data\小区信息20250816 - 副本.xlsx 中需要爬取的小区，和目的地坐标
3>运行本程序
4>运行结果为 data\小区信息20250816 - 副本-结果.xlsx