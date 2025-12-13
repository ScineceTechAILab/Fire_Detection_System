from core.communication.feishu import FeishuNotifier
import requests


def get_group_id():
    notifier = FeishuNotifier()
    token = notifier.get_tenant_access_token()

    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}

    # 获取机器人所在的群列表
    resp = requests.get(url, headers=headers)
    print(resp.json())


if __name__ == "__main__":
    get_group_id()
