from pydantic import BaseModel, Field
from typing import Optional, List
from .question import Question


class SubjectBank(BaseModel):
    """题库（同事格式）"""
    name: str = Field(description="题库名称")
    remark: str = Field(default="", description="题库描述")
    questions: List[Question] = Field(default_factory=list, description="试题列表")


class GenerateResponse(BaseModel):
    """试题生成响应"""
    success: bool = Field(description="是否成功")
    subjectBanks: List[SubjectBank] = Field(default_factory=list, description="题库列表（通常只有一个）")
    error: Optional[str] = Field(default=None, description="错误信息")
    usage: Optional[dict] = Field(default=None, description="token 用量统计")
