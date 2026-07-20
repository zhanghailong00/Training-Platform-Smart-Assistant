"""OCR 试题识别 — 数据模型"""

from pydantic import BaseModel, Field
from typing import Optional


class OcrRequest(BaseModel):
    """OCR 试题识别请求（图片以二进制上传，不在 JSON 中）"""
    subject_bank_name: str = Field(default="OCR识别题库", description="题库名称")
    subject_bank_remark: str = Field(default="", description="题库描述")