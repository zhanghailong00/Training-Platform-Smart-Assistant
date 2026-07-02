from pydantic import BaseModel, Field
from typing import Optional, List
from .enums import QuestionType, Difficulty


class GenerateRequest(BaseModel):
    """试题生成请求"""
    subject_bank_name: str = Field(default="默认题库", description="题库名称")
    subject_bank_remark: str = Field(default="", description="题库描述")
    document_text: Optional[str] = Field(default=None, description="文档解析后的文本或自由输入")
    requirements: str = Field(default="", description="老师的具体要求")
    question_types: List[int] = Field(
        default=[0, 1, 2, 3],
        description="需要生成的题型：0=单选, 1=多选, 2=判断, 3=简答",
    )
    count_per_type: int = Field(default=5, ge=1, le=20, description="每种题型数量")
    difficulty: int = Field(default=0, ge=0, le=1, description="难度：0=简单, 1=困难")
