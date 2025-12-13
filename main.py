# 程序入口
import time
from core.communication.feishu import FeishuNotifier
from utils.logger import setup_logger

# 初始化通知器 (会自动加载 .env 里的管理员)
notifier = FeishuNotifier()


class Main:

    def __init__(self):
        self.logger = setup_logger("Main")

    def run_fire_alarm_process_feishu(self, image_path):

        """
        【核心逻辑】全自动分级报警线程
        该函数会独立运行，不会阻塞摄像头画面
        """

        self.logger.info(f"🔥 [线程启动] 开始执行报警流程...")

        # 1. 记录开始时间
        start_time = time.time()

        # 2. 第一轮：发送 [短信 + App] 加急
        # urgent_type="sms" 意味着 App弹窗 + 短信 都会发
        self.logger.info("Step 1: 发送短信加急报警...")
        notifier.send_to_all_admins(
            title="实验室火灾警报",
            content="检测到明火！请在 3 分钟内回复【1】确认，否则将触发电话报警。",
            image_path=str(image_path),
            urgent_type="sms"
        )

        # 3. 准备轮询：获取所有管理员的 Chat ID
        # 我们只要收到任意一个管理员的回复，就停止升级
        admin_chat_ids = []
        for uid in notifier.admin_ids:
            cid = notifier.get_p2p_chat_id(uid)
            if cid:
                admin_chat_ids.append(cid)

        if not admin_chat_ids:
            self.logger.error("❌ 警告：无法获取管理员会话 ID，无法接收回复，流程中止")
            return

        # 4. 进入 3 分钟等待期 (轮询查岗)
        # 3分钟 = 180秒，每 5 秒查一次
        wait_seconds = 180
        is_confirmed = False

        self.logger.info(f"Step 2: 等待回复中 (限时 {wait_seconds} 秒)...")

        for i in range(wait_seconds // 5):
            # 遍历所有管理员的聊天记录
            for chat_id in admin_chat_ids:
                if notifier.check_user_reply(chat_id, start_time):
                    is_confirmed = True
                    break  # 跳出管理员循环

            if is_confirmed:
                break  # 跳出时间循环

            time.sleep(5)  # 休息5秒再查

        # 5. 判断结果
        if is_confirmed:
            self.logger.info("✅ 警报解除：管理员已确认收到。")
            # 可以发一条消息告诉大家：危机解除，有人处理了
            notifier.send_to_all_admins("警报解除", "管理员已响应，流程结束。", urgent_type="app")
        else:
            self.logger.info("⚠️ 超时未回复！")
            self.logger.info("Step 3: 升级为 [电话] 加急报警！")

            # 6. 第二轮：升级为 [电话] 加急
            # urgent_type="phone" 意味着 App + 短信 + 电话 都会轰炸
            notifier.send_to_all_admins(
                title="【紧急】火灾未响应",
                content="您未在规定时间内回复，系统发起自动电话通知！请立即处置！",
                image_path=str(image_path),
                urgent_type="phone"  # <--- 核心升级点
            )

# --- 在 YOLO 检测逻辑中调用 ---
# 假设你在 main loop 里检测到了火灾
# if is_fire_detected and (现在不在冷却时间内):
#     # 启动一个新线程去跑报警，这样 main loop 可以继续检测下一帧
#     t = threading.Thread(target=run_fire_alarm_process, args=("output/fire.jpg",))
#     t.start()
