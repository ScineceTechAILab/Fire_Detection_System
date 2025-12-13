import threading

from core.communication.feishu import FeishuNotifier
from pathlib import Path
from core.communication.communication import Communication
from core.communication.communication import notifier
from main import Main


def test_feishu_send_alert_card():
    feishu_notifier = FeishuNotifier()

    # 获取发送结果 (True/False)
    result = feishu_notifier.send_alert_card("单元测试,火灾!!!", "这是一条测试消息")

    # 【关键】断言：如果 result 是 False，测试直接报错(FAILED)
    assert result is True, "测试失败：飞书消息未能发送，请检查日志输出"


def test_send_image_alert():
    # 1. 初始化
    notifier = FeishuNotifier()

    # 2. 找到测试图片的绝对路径
    # 假设你的测试脚本在 test/test_communication/ 下
    # 图片在项目根目录的 test_imgs/ 下
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    image_path = project_root / "test_imgs" / "test1.jpg"

    print(f"正在使用测试图片: {image_path}")

    # 3. 发送报警 (传入图片路径)
    # 注意：确保 .env 里配置了 AppID 和 Secret，否则只能收到文字
    result = notifier.send_alert_card(
        title="单元测试",
        content="这是一个单元测试",
        image_path=str(image_path)  # 转成字符串传进去
    )

    assert result is True


# 测试加急图片消息发送
# def test_send_image_alert_urge():
#     notifier = FeishuNotifier()
#     current_dir = Path(__file__).resolve().parent
#     project_root = current_dir.parent
#     image_path = project_root / "test_imgs" / "test1.jpg"
#     notifier.send_card_and_urgent(
#         title="加急单元测试",
#         content="这是加急单元测试",
#         receiver_open_id="ou_913d65a4c53ced131746da62d163efa3",
#         image_path=str(image_path)
#     )


def test_send_all_admins_alert():
    notifier = FeishuNotifier()
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    image_path = project_root / "test_imgs" / "test1.jpg"
    result = notifier.send_to_all_admins(
        title="全管理员加急单元测试",
        content="这是发送给所有管理员的加急单元测试消息",
        image_path=str(image_path)
    )
    assert result is True


def test_send_all_admins_alert_sms():
    notifier = FeishuNotifier()
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    image_path = project_root / "test_imgs" / "test1.jpg"
    result = notifier.send_to_all_admins(
        title="全管理员加急单元测试",
        content="这是发送给所有管理员的加急单元测试消息",
        image_path=str(image_path),
        urgent_type="sms"
    )
    assert result is True


def test_send_all_admins_alert_phone():
    notifier = FeishuNotifier()
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    image_path = project_root / "test_imgs" / "test1.jpg"
    result = notifier.send_to_all_admins(
        title="全管理员加急单元测试",
        content="这是发送给所有管理员的加急单元测试消息",
        image_path=str(image_path),
        urgent_type="phone"
    )
    assert result is True


def test_send_all_admins_alert_all():
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    image_path = project_root / "test_imgs" / "test1.jpg"
    communication = Communication()
    t = threading.Thread(target=communication.run_fire_alarm_process_feishu, args=(image_path,))
    t.start()
    t.join()


def test_feishu_member():
    print("管理员 Open IDs:", notifier.admin_ids)
    assert len(notifier.admin_ids) > 0, "未能加载任何管理员 ID，请检查配置"
