import time
import io
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

# 企业微信配置
CORP_ID = 'xxxxxx'  # 替换为你的企业ID
CORP_SECRET = 'xxxxxx'  # 替换为你的企业Secret
AGENT_ID = 'xxxxxxx'  # 替换为你的应用ID

# 百度翻译API配置
API_KEY = "xxxxxx"
SECRET_KEY = "xxxxxxx"

def get_baidu_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"获取百度访问令牌失败: {response.text}")

def translate_text(text):
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token={get_baidu_access_token()}"
    
    payload = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": f"请将以下英文文本翻译成中文，你只要给我翻译之后的文字，我不需要你解释什么：\n{text}"
            }
        ]
    })
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    
    if response.status_code == 200:
        result = response.json()
        return result.get('result', '翻译失败')
    else:
        return f"翻译失败: {response.status_code}, {response.text}"

# 获取企业微信访问令牌
def get_wechat_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception("获取企业微信访问令牌失败")

# 发送文本消息
def send_text_message(access_token, content):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    data = {
        "touser": "@all",
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {
            "content": content
        }
    }
    response = requests.post(url, json=data)
    if response.status_code != 200 or response.json()['errcode'] != 0:
        print(f"发送文本消息失败: {response.text}")

# 上传图片并发送图片消息
def send_image_message(access_token, image_path):
    # 上传图片
    upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image"
    with open(image_path, 'rb') as f:
        files = {'media': f}
        response = requests.post(upload_url, files=files)
    if response.status_code != 200 or response.json()['errcode'] != 0:
        print(f"上传图片失败: {response.text}")
        return

    media_id = response.json()['media_id']

    # 发送图片消息
    send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    data = {
        "touser": "@all",
        "msgtype": "image",
        "agentid": AGENT_ID,
        "image": {
            "media_id": media_id
        }
    }
    response = requests.post(send_url, json=data)
    if response.status_code != 200 or response.json()['errcode'] != 0:
        print(f"发送图片消息失败: {response.text}")

def main_process():
    try:
        # 设置浏览器选项，禁用SSL证书校验
        chrome_options = Options()
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--window-size=1920,1080")  # 设置窗口大小为1920x1080

        # 启动Chrome浏览器
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        # 设置浏览器窗口大小为1920x1080
        driver.set_window_size(1920, 1080)

        url = "https://www.bybit.com/en/tradegpt/chat/"
        driver.get(url)

        # 等待页面加载
        time.sleep(5)

        # 输入文本到输入框
        input_box = driver.find_element(By.CLASS_NAME, "chat-box_textArea__f5VXn")
        input_box.send_keys("BTC行情")

        # 点击按钮
        submit_button = driver.find_element(By.CLASS_NAME, "button_btn__Cfilj")
        submit_button.click()

        # 等待图表元素加载
        wait = WebDriverWait(driver, 30)
        chart_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "Kline_gptChartWrap__831U4")))

        # 滚动到图表元素
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", chart_element)

        # 额外等待时间，确保图表完全加载和滚动完成
        time.sleep(10)

        # 获取图表元素的位置和大小
        location = chart_element.location_once_scrolled_into_view
        size = chart_element.size

        # 截取整个页面
        screenshot = driver.get_screenshot_as_png()
        screenshot_image = Image.open(io.BytesIO(screenshot))

        # 计算图表元素在截图中的位置
        left = location['x']
        top = location['y']
        right = left + size['width']
        bottom = top + size['height']

        # 裁剪图表区域
        cropped_image = screenshot_image.crop((left, top, right, bottom))

        # 保存截图
        cropped_image.save('chart_screenshot.png')

        # 获取并打印指定div的文本内容
        try:
            indicator_text_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "indicator_indicatorTitleDesc__oxWIt")))
            indicator_text = indicator_text_element.text
            print("原文:")
            print(indicator_text)
            
            # 翻译文本
            translated_text = translate_text(indicator_text)
            print("\n翻译后的文本:")
            print(translated_text)

            # 获取企业微信访问令牌
            access_token = get_wechat_access_token()

            # 发送翻译后的文本，添加"翻译："前缀
            send_text_message(access_token, f"翻译：{translated_text}")

            # 发送图片
            send_image_message(access_token, 'chart_screenshot.png')

        except Exception as e:
            print(f"获取或翻译文本时出错: {e}")

    except Exception as e:
        print(f"执行过程中出错: {e}")

    finally:
        # 关闭浏览器
        driver.quit()

# 主循环
while True:
    print("开始执行...")
    main_process()
    print("执行完成,等待1小时...")
    time.sleep(3600)  # 等待1小时(3600秒)
