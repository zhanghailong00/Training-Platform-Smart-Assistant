from pydantic import BaseModel, Field
from typing import Optional, List


class Option(BaseModel):
    """选项（同事格式）"""
    content: str = Field(description="选项文本")
    isRight: bool = Field(description="是否为正确答案")
    analysis: Optional[str] = Field(default=None, description="选项解析（错误选项必填，正确选项可为 null）")


class Question(BaseModel):
    """统一试题模型（同事格式）"""
    type: int = Field(description="题型：0=单选, 1=多选, 2=判断, 3=简答")
    typeName: str = Field(description="题型名称：单选题/多选题/判断题/简答题")
    level: int = Field(description="难度：0=简单, 1=困难")
    levelName: str = Field(description="难度名称：简单/困难")
    content: str = Field(description="题干内容")
    analysis: str = Field(description="题目解析")
    subAnswer: Optional[str] = Field(default=None, description="简答题答案（仅 type=3 时填写，其余为 null）")
    options: List[Option] = Field(description="选项列表（简答题为空数组）")
