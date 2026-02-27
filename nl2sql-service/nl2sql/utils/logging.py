# -*- coding: utf-8 -*-
# =====================
# 日志工具
# =====================
import sys
from pathlib import Path

from loguru import logger


def get_logger(name: str = "nl2sql"):
    """获取日志记录器"""
    return logger.bind(name=name)


def setup_logging(log_path: str = None, level: str = "INFO"):
    """配置日志"""
    # 移除默认处理器
    logger.remove()

    # 添加控制台处理器
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # 添加文件处理器
    if log_path:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path,
            level=level,
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    return logger
