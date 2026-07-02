import logging
import sys
from .settings import settings


def get_logger(name: str) -> logging.Logger:
    """获取统一格式的 logger"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # 防止日志向上传播导致重复
        logger.propagate = False

    return logger
