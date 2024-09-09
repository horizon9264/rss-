import requests
from bs4 import BeautifulSoup
import json
import os
import logging
import time  # 确保这里没有被覆盖
#loc新贴微信推送
# WeChat configuration
CORP_ID = 'xxxxxxxxx'  # Replace with your Corp ID
CORP_SECRET = 'xxxxxxxxxxx'  # Replace with your Corp Secret
AGENT_ID = 'xxxxxxxx'  # Replace with your Agent ID
seen_guids_file = 'seen_guids_hostloc.json'

# Load already sent post IDs
def load_seen_guids():
    if os.path.exists(seen_guids_file):
        with open(seen_guids_file, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen_guids(seen_guids):
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

def send_wechat_message(title, url, time):
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
            "description": f'<div class="gray">{time}</div> <div class="normal">点击查看详情</div>',
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

# Target URL
url = "https://hostloc.com/forum.php?mod=forumdisplay&fid=45&filter=author&orderby=dateline"

# Excluded post titles
exclude_titles = [
    "VPS讨论区T楼规则 (2020-06-16)",
    "VPS综合资料导航帖，找到所需资料迅速解决问题(2011.7.9更新)"
]

# Main loop for monitoring
def monitor():
    seen_guids = load_seen_guids()
    while True:
        posts_to_send = []
        
        # Send GET request
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the webpage
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all posts
            threads = soup.find_all('tbody')
            
            for thread in threads:
                # Extract post title
                title_tag = thread.find('a', class_='s xst')
                if title_tag:
                    title = title_tag.text.strip()
                    link = title_tag['href'].rstrip('/')  # Remove trailing slash
                    post_id = link.split('=')[-1]  # Extracting post ID from the link
                    
                    # Construct the full link
                    full_link = f"https://hostloc.com/{link}"
                    
                    # Skip if the title is in the exclude list or if it has already been sent
                    if title in exclude_titles or post_id in seen_guids:
                        continue
                    
                    # Extract author and time
                    author_tag = thread.find('cite')
                    time_tag = thread.find('em').find('span')
                    
                    author = author_tag.text.strip() if author_tag else "未知"
                    post_time = time_tag.get('title', '未知') if time_tag else "未知"  # 使用不同的变量名
                    
                    # Append the post information to the list
                    posts_to_send.append((title, full_link, post_time, post_id))
            
            # Reverse the order of the posts
            posts_to_send.reverse()

            # Send WeChat messages in reversed order
            for title, full_link, post_time, post_id in posts_to_send:
                send_wechat_message(title, full_link, post_time)
                seen_guids.add(post_id)  # Mark this post ID as seen after sending the message
            
            # Save seen post IDs after processing all threads
            save_seen_guids(seen_guids)
            print("New post information processed and sent.")
        else:
            print(f"Request failed with status code: {response.status_code}")

        # Wait for 10 minutes before the next check
        time.sleep(600)  # 600 seconds = 10 minutes

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor()
