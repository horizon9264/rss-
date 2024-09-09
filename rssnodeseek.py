import feedparser
import requests
import time
import os
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 微信推送配置
CORP_ID = 'xxxxxxxxxx' # 替换为你的企业ID
CORP_SECRET = 'xxxxxxxxxxxxx' # 替换为你的应用密钥
AGENT_ID = 'xxxxxxxxxx' # 替换为你的应用ID

# 存储已推送的GUID
seen_guids_file = 'seen_guids.json'

# 读取已推送的GUID
def load_seen_guids():
    if os.path.exists(seen_guids_file):
        with open(seen_guids_file, 'r') as f:
            return set(json.load(f))
    return set()

seen_guids = load_seen_guids()
logging.info(f"Loaded seen GUIDs: {seen_guids}")

def save_seen_guids():
    with open(seen_guids_file, 'w') as f:
        json.dump(list(seen_guids), f)
    logging.info(f"Saved seen GUIDs: {seen_guids}")

def get_access_token():
    try:
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('access_token')
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting access token: {e}")
        return None

def send_wechat_message(title, msg, url):
    access_token = get_access_token()
    if not access_token:
        logging.error("Failed to get access token.")
        return

    message = {
        "touser": "@all",
        "toparty": "@all",
        "totag": "@all",
        "msgtype": "textcard",
        "agentid": AGENT_ID,
        "textcard": {
            "title": title,
            "description": f'<div class="gray">{time.strftime("%Y-%m-%d %H:%M:%S")}</div> <div class="normal">{msg}</div>',
            "url": url,
            "btntxt": "详情"
        }
    }
    
    try:
        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        response = requests.post(send_url, json=message, timeout=10)
        response.raise_for_status()
        logging.info(f"Message sent: {title}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending message: {e}")

def check_rss():
    try:
        feed = feedparser.parse('https://rss.nodeseek.com/')
        # 反转条目列表
        entries = feed.entries[::-1]

        for entry in entries:
            guid = entry.guid
            title = entry.title.strip()
            link = entry.link
            msg = getattr(entry, 'summary', getattr(entry, 'description', '无内容'))

            logging.info(f"Checking entry: {title} with GUID: {guid}")

            if guid not in seen_guids:
                send_wechat_message(title, msg, link)
                seen_guids.add(guid)
                save_seen_guids()
            else:
                logging.info(f"Already seen GUID: {guid}")

    except Exception as e:
        logging.error(f"Error checking RSS: {e}")

if __name__ == "__main__":
    while True:
        try:
            check_rss()
            time.sleep(600)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(60)  # 等待一段时间后重试
