from core.communication.feishu import FeishuNotifier
from pathlib import Path


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
