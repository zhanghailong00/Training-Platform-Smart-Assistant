"""课程简介生成 — 数据模型"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ChapterInfo(BaseModel):
    """章节信息"""
    name: str = Field(description="章节名称，如'第一章 SDK 配置和测试用例'")
    lessons: List[str] = Field(description="该章节下的实验/课时名称列表")


class CourseIntroRequest(BaseModel):
    """课程简介生成请求"""
    course_name: str = Field(description="课程名称")
    chapters: List[ChapterInfo] = Field(description="章节列表")


class CourseIntroResponse(BaseModel):
    """课程简介生成响应"""
    success: bool = Field(description="是否成功")
    intro: Optional[str] = Field(default=None, description="生成的课程简介文本")
    error: Optional[str] = Field(default=None, description="错误信息")
