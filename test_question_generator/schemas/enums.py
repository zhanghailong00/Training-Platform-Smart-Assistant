from enum import IntEnum


class QuestionType(IntEnum):
    """题型（数字编码，对齐同事格式）"""
    SINGLE_CHOICE = 0    # 单选题
    MULTI_CHOICE = 1     # 多选题
    TRUE_FALSE = 2       # 判断题
    ESSAY = 3            # 简答题


class Difficulty(IntEnum):
    """难度（数字编码，对齐同事格式）"""
    EASY = 0             # 简单
    HARD = 1             # 困难
