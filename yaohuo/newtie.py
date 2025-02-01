import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from config import *
import urllib3
import certifi
import logging
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CONTENT_DIR, exist_ok=True)
    if not os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_posts():
    """加载帖子列表"""
    with open(POSTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_posts(posts):
    """保存帖子列表"""
    with open(POSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

def fetch_new_posts():
    print("开始获取新帖子...")
    
    # 构建请求头
    headers = {
        'Cookie': f'sidyaohuo={SID}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # 发送请求
    response = requests.get(NEWTIE, headers=headers, verify=certifi.where())
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 查找所有帖子
    posts = []
    for div in soup.find_all('div', class_='listdata'):
        post = {}
        
        # 获取标题和链接
        a_tag = div.find('a')
        if a_tag:
            post['title'] = a_tag.text.strip()
            post['link'] = a_tag.get('href', '')
            import re
            link_match = re.search(r'(\d+)\.html', post['link'])
            post['link'] = int(link_match.group(1)) if link_match else None

        # 获取作者等信息
        br_tag = div.find('br')
        if br_tag and br_tag.next_sibling:
            author_text = br_tag.next_sibling.text
            post['author'] = author_text.split('/')[0].strip()

        post['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        post['isok'] = None
        
        posts.append(post)
        print(f"获取到帖子：{post['title']} - 作者：{post['author']}")

    return posts

def get_access_token():
    """获取企业微信访问令牌"""
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        logger.error(f'获取访问令牌失败. 状态码: {response.status_code}')
        return None

def send_wechat_notification(post):
    """发送企业微信通知"""
    access_token = get_access_token()
    if not access_token:
        return

    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    content = f"新帖子\n标题：{post['title']}\n作者：{post['author']}\n链接：https://yaohuo.me/bbs-{post['link']}.html"
    
    data = {
        "touser": "@all",
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {
            "content": content
        },
        "safe": 0
    }

    response = requests.post(url, json=data)
    if response.status_code == 200 and response.json().get('errcode') == 0:
        logger.info(f'已推送通知: {post["title"]}')
    else:
        logger.error(f'推送通知失败. 响应: {response.json()}')

def main():
    while True:
        try:
            ensure_data_dir()
            new_posts = fetch_new_posts()
            existing_posts = load_posts()
            
            # 合并新旧帖子，避免重复
            existing_links = {post['link'] for post in existing_posts}
            new_count = 0
            for post in new_posts:
                if post['link'] not in existing_links:
                    existing_posts.append(post)
                    new_count += 1
                    # 对新帖子进行推送
                    send_wechat_notification(post)
            
            # 保存更新后的帖子列表
            save_posts(existing_posts)
            
            logger.info(f"\n采集完成！新增 {new_count} 个帖子")
            logger.info(f"总共有 {len(existing_posts)} 个帖子")

        except Exception as e:
            logger.error(f"发生错误：{str(e)}")
        
        # 休眠5分钟
        logger.info("等待5分钟后进行下一次检查...")
        time.sleep(300)  # 300秒 = 5分钟

if __name__ == '__main__':
    logger.info("启动帖子监控脚本...")
    main() 