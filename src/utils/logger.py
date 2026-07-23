"""
文件名: logger.py
核心作用: 配置整个项目的统一日志系统。
"""
import logging
import sys
import os
from datetime import datetime

# 日志目录和格式
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent.log")
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
def get_logger(name: str) -> logging.Logger:
    """
    获取一个配置好的日志记录器。
    
    用法:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条信息")
        logger.error("这是一条错误")
    """
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    
    # 避免重复添加 Handler（防止日志重复打印）
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        # 1. 处理器：输出到终端（控制台）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console_handler)

        # 2. 处理器：输出到文件（自动记录所有行为）
        # 注意：需要确保 logs 文件夹存在（运行时我们会创建）
        file_handler = logging.FileHandler("logs/agent.log", encoding="utf-8")
        file_handler.setLevel(logging.INFO)  # 文件只记录 INFO 及以上级别，避免太大
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(file_handler)
    
    return logger