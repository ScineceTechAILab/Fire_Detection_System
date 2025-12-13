import requests
import json
import time
import os
import sys
from pathlib import Path
# 【改动1】引入 dotenv_values 用于直接读取文件
from dotenv import load_dotenv, dotenv_values

# 强制关闭代理
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent
sys.path.append(str(project_root))
from utils.logger import setup_logger


class FeishuNotifier:
    def __init__(self, webhook_url=None):
        self.logger = setup_logger("Feishu")

        # 1. 先确定 .env 路径
        current_dir = Path(__file__).resolve().parent
        self.project_root = current_dir.parent.parent
        self.env_path = self.project_root / ".env"

        # 2. 加载环境变量 (用于读取 AppID 等常规配置)
        self._load_env()
        self.headers = {'Content-Type': 'application/json'}

        # 3. 基础配置
        self.webhook_url = webhook_url or os.getenv("feishuwebhook")
        self.keyword = os.getenv("feishu_keyword", "")
        self.app_id = os.getenv("feishu_app_id")
        self.app_secret = os.getenv("feishu_app_secret")

        # 4. 自动加载管理员 ID
        self.admin_ids = []
        if self.app_id and self.app_secret:
            self._auto_load_admins()
        else:
            self.logger.warning("未配置 AppID/Secret，无法自动加载管理员 ID")

    def _load_env(self):
        if self.env_path.exists():
            # override=True 确保强制读取最新文件，覆盖旧缓存
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
        """通过手机号查 User ID"""
        if not mobile.startswith("+"):
            mobile = f"+{mobile}"

        token = self._get_tenant_access_token()
        if not token: return None

        url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"user_id_type": "open_id"}
        body = {"mobiles": [mobile]}

        try:
            resp = requests.post(url, headers=headers, params=params, json=body, proxies={"http": None, "https": None})
            data = resp.json()
            if data.get("code") == 0:
                user_list = data.get("data", {}).get("user_list", [])
                if user_list:
                    user_id = user_list[0].get("user_id")
                    if user_id:
                        return user_id

            # 这里用 debug 级别，防止因为找不到某个手机号刷屏报错
            self.logger.warning(f"手机号 {mobile} 未匹配到用户 (请检查应用可用范围)")
            return None
        except Exception:
            return None

    def _auto_load_admins(self):
        """
        【修复版】直接读取 .env 文件内容，不依赖 os.environ 缓存
        """
        self.logger.info(f"正在从文件加载管理员: {self.env_path}")

        if not self.env_path.exists():
            self.logger.error("❌ 找不到 .env 文件！")
            return

        # 【关键修复】使用 dotenv_values 直接把文件读成字典
        # 这样绝对能读到你刚写的 admin_phone1
        env_config = dotenv_values(self.env_path)

        count = 0
        for key, value in env_config.items():
            # 只要 key 是以 admin_phone 开头的
            if key.startswith("admin_phone") and value:
                self.logger.info(f"发现配置 [{key}: {value}]，正在去飞书查询 ID...")

                user_id = self.get_open_id_by_mobile(value)

                if user_id:
                    if user_id not in self.admin_ids:
                        self.admin_ids.append(user_id)
                        count += 1
                        self.logger.info(f"✅ 管理员 {key} 添加成功 (ID: {user_id})")
                else:
                    self.logger.error(f"❌ 管理员 {key} 查询失败 (可能未发布版本或不在可用范围)")

        self.logger.info(f"管理员加载完毕，共 {count} 人")

    # --- 下面是发送逻辑 (保持不变) ---
    def upload_image(self, image_path):
        if not self.app_id: return None
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

    def buzz_message(self, message_id, user_id_list, urgent_type="app"):
        """
        通用加急方法
        :param urgent_type:
            - 'app': 应用内加急 (弹窗)
            - 'sms': 短信加急 (应用内+短信) -> 【需要企业认证 + 额度】
            - 'phone': 电话加急 (应用内+短信+电话) -> 【需要企业认证 + 额度】
        """
        token = self._get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/urgent_{urgent_type}"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"user_id_type": "open_id"}

        # 构造请求体
        data = {
            "user_id_list": user_id_list,
            "urgent_type": urgent_type
        }
        self.logger.info(f"DEBUG: 正在发起加急请求 | URL: {url} | Data: {data}")

        try:
            resp = requests.patch(url, headers=headers, params=params, json=data, proxies={"http": None, "https": None})
            res = resp.json()

            if res.get("code") == 0:
                # 记录成功日志
                type_map = {"app": "应用内", "sms": "短信", "phone": "电话"}
                self.logger.info(f"🚀 [{type_map.get(urgent_type)}] 加急发送成功！")
                return True
            else:
                # 记录详细错误，方便排查额度问题
                err_msg = res.get("msg")
                err_code = res.get("code")
                self.logger.error(f"❌ 加急失败 (Code: {err_code}): {err_msg}")

                # 常见错误提示
                if err_code == 230001:
                    self.logger.warning("提示：请检查飞书后台是否开通了'加急'权限")
                elif err_code == 1070003:
                    self.logger.warning("提示：可能是加急额度不足，或管理员关闭了短信加急功能")

                return False
        except Exception:
            self.logger.exception("加急请求网络异常")
            return False

    def send_to_all_admins(self, title, content, image_path=None, urgent_type="app"):
        if not self.admin_ids:
            self.logger.error("❌ 没有可用的管理员 ID，无法发送消息！请检查 .env 配置")
            return False

        shared_image_key = None
        if image_path:
            shared_image_key = self.upload_image(image_path)
            if not shared_image_key:
                self.logger.warning("图片上传失败，将降级为纯文字报警")

        success_count = 0
        self.logger.info(f"开始向 {len(self.admin_ids)} 位管理员发送报警...")

        for user_id in self.admin_ids:
            success = self._send_single_card(title, content, user_id, shared_image_key, urgent_type)
            if success:
                success_count += 1

        self.logger.info(f"群发任务结束: 成功 {success_count}/{len(self.admin_ids)}")
        return success_count > 0

    def _send_single_card(self, title, content, receiver_id, image_key, urgent_type):
        token = self._get_tenant_access_token()
        if not token: return False

        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        final_title = f"【{self.keyword}】{title}" if self.keyword else title
        elements = [{"tag": "div", "text": {"content": f"**时间**: {time_str}\n**详情**: {content}", "tag": "lark_md"}}]

        if image_key:
            elements.append({"tag": "img", "img_key": image_key, "alt": {"content": "现场图", "tag": "plain_text"}})

        elements.append({"tag": "hr"})
        elements.append({"tag": "note", "elements": [{"content": "系统自动加急报警", "tag": "plain_text"}]})

        card_content = {
            "header": {"template": "red", "title": {"content": f"🔥 {final_title}", "tag": "plain_text"}},
            "elements": elements
        }

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        params = {"receive_id_type": "open_id"}
        body = {
            "receive_id": receiver_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }

        try:
            resp = requests.post(url, headers=headers, params=params, json=body, proxies={"http": None, "https": None})
            res = resp.json()
            if res.get("code") == 0:
                msg_id = res.get("data", {}).get("message_id")
                self.buzz_message(msg_id, [receiver_id], urgent_type)
                return True
            else:
                self.logger.error(f"发送给 {receiver_id} 失败: {res}")
                return False
        except Exception as e:
            self.logger.error(f"发送异常: {e}")
            return False


if __name__ == "__main__":
    notifier = FeishuNotifier()
    print(f"DEBUG: 最终管理员 ID 列表: {notifier.admin_ids}")