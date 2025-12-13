import requests
import json
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

# 强制关闭代理
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

# 引入日志
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent
sys.path.append(str(project_root))
from utils.logger import setup_logger


class FeishuNotifier:
    def __init__(self, webhook_url=None):
        self.logger = setup_logger("Feishu")

        # 1. 加载 .env
        current_dir = Path(__file__).resolve().parent
        self.project_root = current_dir.parent.parent
        self.env_path = self.project_root / ".env"
        self._load_env()
        self.headers = {'Content-Type': 'application/json'}

        # 2. 基础配置
        self.app_id = os.getenv("feishu_app_id")
        self.app_secret = os.getenv("feishu_app_secret")
        self.keyword = os.getenv("feishu_keyword", "")
        self.group_chat_id = os.getenv("feishu_group_chat_id")  # 【新增】群ID

        # 3. 自动加载管理员 ID
        self.admin_ids = []
        if self.app_id and self.app_secret:
            self._auto_load_admins()
        else:
            self.logger.warning("未配置 AppID/Secret，功能受限")

    def _load_env(self):
        if self.env_path.exists():
            load_dotenv(dotenv_path=self.env_path, override=True)

    def _get_tenant_access_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {"app_id": self.app_id, "app_secret": self.app_secret}
        try:
            resp = requests.post(url, json=data, proxies={"http": None, "https": None})
            if resp.json().get("code") == 0:
                return resp.json().get("tenant_access_token")
            self.logger.error(f"Token 获取失败: {resp.text}")
            return None
        except Exception:
            self.logger.exception("获取 Token 异常")
            return None

    def get_open_id_by_mobile(self, mobile):
        self.logger.info("通过手机号获取 User ID " + mobile)
        """通过手机号查 User ID"""
        if not mobile.startswith("+"): mobile = f"+{mobile}"
        token = self._get_tenant_access_token()
        if not token: return None
        url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.post(url, headers=headers, params={"user_id_type": "open_id"}, json={"mobiles": [mobile]},
                                 proxies={"http": None, "https": None})
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("user_list"):
                return data.get("data").get("user_list")[0].get("user_id")
            return None
        except Exception:
            self.logger.error("通过手机号获取 User ID 异常" + mobile)
            return None

    def _auto_load_admins(self):
        """加载管理员列表 (优化日志版)"""
        if not self.env_path.exists(): return

        env_config = dotenv_values(self.env_path)

        self.logger.info("====== 开始扫描管理员 ======")

        for key, value in env_config.items():
            if key.startswith("admin_phone") and value:
                self.logger.info(f"正在查询: {key} -> {value}")

                uid = self.get_open_id_by_mobile(value)

                if uid:
                    if uid not in self.admin_ids:
                        self.admin_ids.append(uid)
                        self.logger.info(f"✅ 成功添加: {key} (ID: {uid})")
                    else:
                        self.logger.info(f"⚠️ 跳过重复: {key}")
                else:
                    # 【新增】这里会告诉你为什么没加载上
                    self.logger.error(f"❌ 加载失败: {key} - 未找到用户ID (请检查飞书后台'可用范围')")

        self.logger.info(f"====== 扫描结束，共加载 {len(self.admin_ids)} 人 ======")

    def upload_image(self, image_path):
        """上传图片"""
        token = self._get_tenant_access_token()
        if not token: return None
        url = "https://open.feishu.cn/open-apis/im/v1/images"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            files = {'image_type': (None, 'message'), 'image': image_data}
            resp = requests.post(url, headers=headers, files=files, proxies={"http": None, "https": None})
            if resp.json().get("code") == 0:
                return resp.json().get("data", {}).get("image_key")
            return None
        except Exception:
            return None

    def buzz_message(self, message_id, user_id_list, urgent_type="sms"):
        """
        【加急核心】
        注意：即使消息发在群里，也可以对特定的 User ID 列表进行加急！
        """
        token = self._get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/urgent_{urgent_type}"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"user_id_list": user_id_list, "urgent_type": urgent_type}
        try:
            resp = requests.patch(url, headers=headers, params={"user_id_type": "open_id"}, json=data,
                                  proxies={"http": None, "https": None})
            if resp.json().get("code") == 0:
                self.logger.info(f"🚀 [{urgent_type}] 加急发送成功！")
                return True
            else:
                self.logger.error(f"加急失败: {resp.json()}")
                return False
        except Exception:
            return False

    def send_card_to_group(self, title, content, image_path=None):
        """
        发送卡片到群聊，并返回 message_id
        """
        if not self.group_chat_id:
            self.logger.error("❌ 未配置 feishu_group_chat_id")
            return None

        token = self._get_tenant_access_token()
        if not token: return None

        # 1. 准备图片
        image_key = None
        if image_path:
            image_key = self.upload_image(image_path)

        # 2. 构建卡片
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        final_title = f"【{self.keyword}】{title}" if self.keyword else title

        elements = [
            {"tag": "div", "text": {"content": f"**时间**: {time_str}\n**详情**: {content}", "tag": "lark_md"}},
        ]
        if image_key:
            elements.append({"tag": "img", "img_key": image_key, "alt": {"content": "现场图", "tag": "plain_text"}})

        # 引导语
        elements.append({"tag": "hr"})
        elements.append({"tag": "div",
                         "text": {"content": "🔴 **所有成员请注意**：\n收到请在群内回复 **1** 或 **收到** 以解除警报。",
                                  "tag": "lark_md"}})

        card_content = {
            "header": {"template": "red", "title": {"content": f"🔥 {final_title}", "tag": "plain_text"}},
            "elements": elements
        }

        # 3. 发送
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        # receive_id 就是群ID，receive_id_type 选 chat_id
        params = {"receive_id_type": "chat_id"}
        body = {
            "receive_id": self.group_chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }

        try:
            resp = requests.post(url, headers=headers, params=params, json=body, proxies={"http": None, "https": None})
            res = resp.json()
            if res.get("code") == 0:
                msg_id = res.get("data", {}).get("message_id")
                self.logger.info(f"群消息发送成功 ID: {msg_id}")
                return msg_id
            else:
                self.logger.error(f"群发失败: {res}")
                return None
        except Exception as e:
            self.logger.exception("发送异常")
            return None

    def check_chat_reply(self, start_time_ts):
        """
        检查群里有没有人回复
        """
        if not self.group_chat_id: return False

        token = self._get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}

        safe_start_time = str(int(start_time_ts - 10))

        params = {
            "container_id_type": "chat",
            "container_id": self.group_chat_id,
            "start_time": safe_start_time,
            # "sort_type": "ByCreateTime",
            "page_size": 50
        }

        try:
            resp = requests.get(url, headers=headers, params=params, proxies={"http": None, "https": None})
            data = resp.json()

            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])

                for msg in items:
                    # 解析
                    content_json = msg.get("body", {}).get("content", "{}")
                    content_dict = json.loads(content_json)
                    text = content_dict.get("text", "").strip()
                    sender_type = msg.get("sender", {}).get("sender_type")

                    if sender_type != "user":
                        continue

                    # 只要回复了以下内容
                    if text in ["1", "收到", "ok", "OK", "确认", "知道了"]:
                        self.logger.info(f"✅ 检测到确认回复: {text}")
                        return True
            else:
                # 如果还有错，打印出来
                self.logger.warning(f"轮询接口报错: {data}")

            return False
        except Exception as e:
            self.logger.exception("轮询异常")
            return False

    def get_tenant_access_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {"app_id": self.app_id, "app_secret": self.app_secret}
        try:
            resp = requests.post(url, json=data, proxies={"http": None, "https": None})
            if resp.json().get("code") == 0:
                return resp.json().get("tenant_access_token")
            self.logger.error(f"Token 获取失败: {resp.text}")
            return None
        except Exception:
            self.logger.exception("获取 Token 异常")
            return None