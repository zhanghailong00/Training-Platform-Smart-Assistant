"""文件工具"""

import os
from typing import Optional
from core.constants import SUPPORTED_FORMATS


def detect_file_type(filename: str) -> Optional[str]:
    """
    根据文件扩展名判断文件类型。

    Returns:
        "pdf" | "docx" | None（不支持的类型）
    """
    _, ext = os.path.splitext(filename.lower())
    return SUPPORTED_FORMATS.get(ext)


def get_file_extension(filename: str) -> str:
    """获取文件扩展名（小写，含点）"""
    _, ext = os.path.splitext(filename.lower())
    return ext


def is_supported_format(filename: str) -> bool:
    """判断文件格式是否支持"""
    return detect_file_type(filename) is not None
