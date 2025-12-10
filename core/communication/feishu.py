import requests
import json
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 引入日志
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent
sys.path.append(str(project_root))
from utils.logger import setup_logger


class FeishuNotifier:
    def __init__(self, webhook_url=None):
        self.logger = setup_logger("Feishu")
        self._load_env()

        self.headers = {'Content-Type': 'application/json'}

        # 1. 基础配置
        self.webhook_url = webhook_url or os.getenv("feishuwebhook")
        self.keyword = os.getenv("feishu_keyword", "")

        # 2. 图片上传需要的配置
        self.app_id = os.getenv("feishu_app_id")
        self.app_secret = os.getenv("feishu_app_secret")

        if not self.app_id or not self.app_secret:
            self.logger.warning("未配置 AppID/Secret，将无法发送图片，仅能发送文字！")

    def _load_env(self):
        # ... (和之前一样，保持不变) ...
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

    def _get_tenant_access_token(self):
        """
        获取飞书 API 的访问令牌 (Tenant Access Token)
        上传图片必须要有这个令牌
        """
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        try:
            resp = requests.post(url, headers=headers, json=data)
            resp_dict = resp.json()
            if resp_dict.get("code") == 0:
                return resp_dict.get("tenant_access_token")
            else:
                self.logger.error(f"获取 Token 失败: {resp_dict}")
                return None
        except Exception as e:
            self.logger.exception("获取 Token 异常")
            return None

    def upload_image(self, image_path):
        """
        上传本地图片到飞书，获取 image_key
        :param image_path: 图片的本地绝对路径或相对路径
        :return: image_key (字符串) 或 None
        """
        if not self.app_id:
            self.logger.error("缺少 AppID，无法上传图片")
            return None

        # 1. 拿到 Token
        token = self._get_tenant_access_token()
        if not token:
            return None

        # 2. 准备上传
        url = "https://open.feishu.cn/open-apis/im/v1/images"
        headers = {"Authorization": f"Bearer {token}"}  # 注意这里必须带 Token

        # 3. 打开图片文件并发送
        # multipart/form-data 格式上传
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()

            files = {
                'image_type': (None, 'message'),
                'image': image_data
            }

            self.logger.info(f"正在上传图片: {image_path}")
            resp = requests.post(url, headers=headers, files=files)
            result = resp.json()

            if result.get("code") == 0:
                image_key = result.get("data", {}).get("image_key")
                self.logger.info(f"图片上传成功，Key: {image_key}")
                return image_key
            else:
                self.logger.error(f"图片上传失败: {result}")
                return None

        except FileNotFoundError:
            self.logger.error(f"找不到图片文件: {image_path}")
            return None
        except Exception as e:
            self.logger.exception("上传图片过程发生异常")
            return None

    def send_alert_card(self, title, content, image_path=None):
        """
        发送报警卡片 (支持带图片)
        :param image_path: 本地图片路径，如果不传就不发图
        """
        if not self.webhook_url:
            return False

        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        final_title = f"【{self.keyword}】{title}" if self.keyword else title

        # --- 核心改动：构建卡片元素 ---
        elements = [
            {
                "tag": "div",
                "text": {
                    "content": f"**检测时间**: {time_str}\n**详细情况**: {content}",
                    "tag": "lark_md"
                }
            }
        ]

        # 如果传入了图片路径，先上传，拿到 Key，再把图片元素塞进卡片里
        if image_path:
            image_key = self.upload_image(image_path)
            if image_key:
                elements.append({
                    "tag": "img",  # 图片组件
                    "img_key": image_key,
                    "alt": {
                        "content": "现场截图",
                        "tag": "plain_text"
                    }
                })
            else:
                # 如果上传失败，追加一行文字提示，不要让整个报警失败
                elements.append({
                    "tag": "div",
                    "text": {"content": "⚠️ (图片上传失败，请检查日志)", "tag": "lark_md"}
                })

        # 追加分割线和提示
        elements.append({"tag": "hr"})
        elements.append({"tag": "note", "elements": [{"content": "请立即响应！", "tag": "plain_text"}]})

        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "red",
                    "title": {"content": f"🔥 {final_title}", "tag": "plain_text"}
                },
                "elements": elements
            }
        }
        return self._post(data)

    def _post(self, data):
        try:
            self.logger.debug(f"正在发送请求，Payload摘要: {str(data)[:100]}...")
            response = requests.post(self.webhook_url, headers=self.headers, data=json.dumps(data), timeout=5)
            result = response.json()

            if result.get("code") == 0:
                self.logger.info("✅ 消息发送成功")
                return True
            else:
                # 如果失败，通常就是关键词没对上
                self.logger.error(f"❌ 发送失败 (Code: {result.get('code')}): {result.get('msg')}")
                return False
        except Exception as e:
            self.logger.exception("网络请求异常")
            return False


