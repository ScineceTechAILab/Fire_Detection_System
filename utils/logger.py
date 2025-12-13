# utils/logger.py
import logging
import sys


# 使用方法 : self.logger = setup_logger("Feishu") 像这样创建实例,然后使用,需要先导入这个logger模块
def setup_logger(name):
    """
    获取一个配置好的 Logger 对象
    :param name: 模块名称，比如 "Feishu", "YOLO", "Main"
    :return: logger 对象
    """
    # 1. 创建 logger 实例
    logger = logging.getLogger(name)

    # 2. 如果已经有 handler 了，就不要重复添加 (防止日志重复打印)
    if logger.hasHandlers():
        return logger

    # 3. 设置全局日志级别 (INFO 表示只显示 INFO, WARNING, ERROR, CRITICAL)
    # 如果调试时想看更多细节，可以改成 logging.DEBUG
    logger.setLevel(logging.INFO)

    # 4. 创建控制台处理器 (输出到屏幕)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 5. 定义日志格式 (时间 - 模块名 - 等级 - 消息)
    # 比如: 2023-10-27 10:00:00 - Feishu - ERROR - 发送失败
    formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
    console_handler.setFormatter(formatter)

    # 6. 将处理器添加到 logger
    logger.addHandler(console_handler)

    return logger
