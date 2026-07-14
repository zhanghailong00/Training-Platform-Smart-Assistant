"""实验手册/实验报告模板生成 — 数据模型"""

from pydantic import BaseModel, Field
from typing import Optional


class LabManualRequest(BaseModel):
    """实验手册/报告模板生成请求"""
    title: str = Field(description="实验名称")
    document_text: Optional[str] = Field(default=None, description="教学内容文本")
    requirements: str = Field(default="", description="老师的具体要求")
    template_type: str = Field(
        default="manual",
        description="manual=实验指导手册, report=实验报告模板",
    )


class LabManualResponse(BaseModel):
    """实验手册/报告模板生成响应"""
    success: bool = Field(description="是否成功")
    title: Optional[str] = Field(default=None, description="实验名称")
    markdown: Optional[str] = Field(default=None, description="生成的 Markdown 内容")
    download_url: Optional[str] = Field(default=None, description="Word 下载地址")
    error: Optional[str] = Field(default=None, description="错误信息")