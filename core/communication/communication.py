import threading
import time
from core.communication.feishu import FeishuNotifier
from utils.logger import setup_logger

notifier = FeishuNotifier()


class Communication:
    def __init__(self):
        self.logger = setup_logger("Communication")

    def run_fire_alarm_process_feishu(self, image_path):
        self.logger.info(f"🔥 [线程启动] 执行群聊报警流程...")
        start_time = time.time()

        # 1. 发送群消息
        self.logger.info("Step 1: 发送群卡片...")
        msg_id = notifier.send_card_to_group(
            title="实验室火灾警报",
            content="检测到明火！请成员立即检查!!。",
            image_path=image_path
        )

        if not msg_id:
            self.logger.error("❌ 致命错误：群消息发送失败，无法进行后续加急")
            return

        # 2. 短信加急 (Buzz)
        # 虽然消息在群里，但我们可以指定“只提醒这几个管理员”
        if notifier.admin_ids:
            self.logger.info(f"Step 2: 对 {len(notifier.admin_ids)} 位管理员发起 [短信] 加急...")
            notifier.buzz_message(msg_id, notifier.admin_ids, urgent_type="sms")
        else:
            self.logger.info("⚠️ 无管理员 ID，跳过加急")

        # 3. 等待回复 (3分钟)
        wait_seconds = 180
        is_confirmed = False
        self.logger.info(f"Step 3: 等待群回复 (限时 {wait_seconds} 秒)...")

        for i in range(wait_seconds // 5):
            if notifier.check_chat_reply(start_time):
                is_confirmed = True
                break
            time.sleep(5)

        # 4. 结果判断
        if is_confirmed:
            self.logger.info("✅ 警报解除：管理员已在群内响应。")
            # 可选：再发一条群消息告知大家
            # notifier.send_card_to_group("警报解除", "管理员已确认。")
        else:
            self.logger.info("⚠️ 超时未回复！")
            self.logger.info("Step 4: 升级为 [电话] 加急报警！")

            # 对同一条消息发起电话加急 (或者你可以发一条新的再加急)
            if notifier.admin_ids:
                notifier.buzz_message(msg_id, notifier.admin_ids, urgent_type="phone")
