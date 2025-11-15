import json
import re
import logging
import requests
from datetime import datetime
from telethon import TelegramClient, events

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger('telethon').setLevel(logging.WARNING)

# Telegram API 配置
api_id =
api_hash = ''
phone = ''   # 建议用+86开头的完整格式

# 企业微信配置
CORP_ID = ''
CORP_SECRET = ''
AGENT_ID = ''

# 创建客户端会话
client = TelegramClient('my_bot_session', api_id, api_hash)

def get_access_token():
    """获取企业微信访问token"""
    url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}'
    response = requests.get(url)
    return response.json()['access_token']

def send_to_wecom(message):
    """发送消息到企业微信"""
    access_token = get_access_token()
    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
    data = {
        "touser": "@all",
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {"content": message}
    }
    response = requests.post(url, data=json.dumps(data))
    return response.json()

# ====== 从外部 JSON 文件读取群组列表 ======
try:
    with open("groups.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    MONITOR_GROUPS = config.get("groups", [])
except FileNotFoundError:
    MONITOR_GROUPS = []
    print("⚠️ 未找到 groups.json 文件，请先运行导出脚本或手动创建。")

@client.on(events.NewMessage(chats=MONITOR_GROUPS))
async def handle_new_message(event):
    """处理多个群组的新消息事件"""
    message = event.message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = message.text or ""
    text = re.sub(r"(https?://[^\s]+)\)", r"\1", text)
    chat = await event.get_chat()
    chat_name = getattr(chat, "title", "未知群组")
    formatted_message = f"[{chat_name}] 新消息 ({timestamp}):\n{text}"
    send_to_wecom(formatted_message)
    print(f"已转发消息到企业微信: {formatted_message}")

async def main():
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("第一次登录，需要输入验证码")
            await client.send_code_request(phone)
            code = input("请输入验证码: ")
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                if "PASSWORD_REQUIRED" in str(e):
                    password = input("请输入两步验证密码: ")
                    await client.sign_in(password=password)
                else:
                    raise e
            print("登录成功！")
        else:
            print("已经登录，无需再次输入验证码！")

        # 获取对话列表并导出
        result = await client.get_dialogs()
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'telegram_groups_{current_time}.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("群组名称 | 群组ID\n")
            f.write("-" * 50 + "\n")
            for dialog in result:
                if dialog.is_group or dialog.is_channel:
                    group_info = f"{dialog.name} | {dialog.id}"
                    print(group_info)
                    f.write(group_info + "\n")
        print(f"\n群组信息已保存到文件: {output_file}")

        # 开始监控
        print("\n开始监控群组:", MONITOR_GROUPS)
        await client.run_until_disconnected()

    except Exception as e:
        print(f"发生错误: {str(e)}")

# 运行客户端
with client:
    client.loop.run_until_complete(main())
print("当前监控群组列表:", MONITOR_GROUPS)

