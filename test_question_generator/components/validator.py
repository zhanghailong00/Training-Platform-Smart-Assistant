"""JSON 校验组件：从 LLM 响应中提取 JSON + Pydantic 校验"""

from typing import List
from pydantic import ValidationError as PydanticValidationError
from core.logger import get_logger
from core.exceptions import JSONExtractionError, ValidationError
from utils.json_utils import extract_json, repair_json
from schemas.question import Question

logger = get_logger(__name__)


def validate(raw_response: str) -> List[Question]:
    """
    从 LLM 原始响应中提取并校验试题列表。

    流程：
    1. 尝试修复常见 JSON 格式问题
    2. 提取 JSON 数据
    3. 用 Pydantic 逐条校验
    4. 跳过校验失败的条目，记录警告

    Args:
        raw_response: LLM 返回的原始文本

    Returns:
        校验通过的 Question 列表

    Raises:
        JSONExtractionError: 无法从响应中提取 JSON
    """
    if not raw_response or not raw_response.strip():
        raise JSONExtractionError("LLM 返回了空响应")

    # 1. 尝试修复 + 提取
    try:
        repaired = repair_json(raw_response)
        data = extract_json(repaired)
    except ValueError as e:
        logger.error(f"JSON 提取失败: {e}")
        raise JSONExtractionError(str(e))

    # 2. 确保是列表
    if isinstance(data, dict):
        # 有些 LLM 可能返回 {"questions": [...]} 之类的包裹
        if "questions" in data:
            data = data["questions"]
        else:
            # 尝试把 dict 当单条试题处理
            data = [data]
    elif not isinstance(data, list):
        raise JSONExtractionError(f"期望 JSON 数组，实际得到: {type(data).__name__}")

    # 3. 逐条校验
    questions = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"跳过非对象元素 [{i}]: {type(item).__name__}")
            continue

        try:
            question = Question.model_validate(item)
            questions.append(question)
        except PydanticValidationError as e:
            logger.warning(f"试题 [{i}] 校验失败，跳过: {e.errors()}")
            continue

    if not questions:
        raise ValidationError(
            f"所有试题校验失败（共 {len(data)} 条原始数据）。"
            f"原始响应前 300 字符: {raw_response[:300]}"
        )

    logger.info(f"JSON 校验完成: {len(questions)}/{len(data)} 条通过")
    return questions
