# -*- coding: utf-8 -*-
import os
import smtplib
import time  # 注意：你原来在 if __name__ == "__main__" 里 import time，建议移到顶部
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formataddr, COMMASPACE
from email import encoders
from api_key import SMTP_SERVER, SMTP_PORT, USERNAME, PASSWORD, RECIPIENTS  # ← 新增导入 RECIPIENTS


def get_latest_data_file():
    """获取最新生成的数据文件（修正路径处理）"""
    try:
        # 检查记录文件是否存在
        if not os.path.exists('last_file.txt'):
            print("未找到last_file.txt记录文件")
            return None

        with open('last_file.txt', 'r', encoding='utf-8') as f:
            file_path = f.read().strip()

        # 统一转换为绝对路径
        file_path = os.path.abspath(file_path)
        print(f"检测到文件路径: {file_path}")

        # 严格验证文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None

        print(f"文件验证通过: {file_path}")
        return file_path

    except Exception as e:
        print(f"获取最新文件失败: {str(e)}")
        return None

def send_email_with_attachment(file_path):
    """发送带附件的邮件（修正MIME类型问题）"""
    try:
        print(f"\n开始发送邮件，附件路径: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024  # KB

        print(f"附件信息: {file_name} ({file_size:.1f}KB)")

        # 创建邮件对象
        msg = MIMEMultipart()
        msg["From"] = formataddr(("机器牛马", USERNAME))
        msg["To"] = COMMASPACE.join(RECIPIENTS)  # ← 使用从 api_key 导入的收件人列表
        msg["Subject"] = f"链家租房数据 - {file_name}"

        # 添加正文
        msg.attach(MIMEText(
            f"附件是最近摘录的链家租房数据：\n"
            f"文件名: {file_name}\n"
            f"大小: {file_size:.1f}KB\n"
            f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "plain", "utf-8"
        ))

        # 添加附件
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)

        # 处理中文文件名（使用 gb2312 或 utf-8，但多数邮件客户端接受 utf-8）
        # 更稳妥的方式：使用 RFC 2231 编码（email.utils 会自动处理）
        # 简化写法（推荐）：
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{file_name}"'
        )
        # 如果文件名含中文，建议使用以下方式（兼容性更好）：
        from email.header import Header
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=Header(file_name, 'utf-8').encode()
        )

        msg.attach(part)

        # 发送邮件
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, RECIPIENTS, msg.as_string())  # ← 收件人列表

        print(f"邮件发送成功！附件：{file_name}")
        return True

    except Exception as e:
        print(f"发送失败: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    import time

    print("=" * 50)
    print("链家租房数据邮件发送程序")
    print("=" * 50)

    latest_file = get_latest_data_file()

    if latest_file:
        print(f"\n找到最新数据文件: {latest_file}")
        if send_email_with_attachment(latest_file):
            print("\n邮件发送成功！")
        else:
            print("\n邮件发送失败！")
    else:
        print("\n未找到有效数据文件，请检查：")
        print("1. 是否已运行爬虫程序生成数据")
        print("2. last_file.txt内容是否正确")
        print("3. 数据文件是否被移动或删除")