"""JSON 校验组件：从 LLM 响应中提取 JSON + Pydantic 校验 + 业务规则校验

返回校验结果和错误详情，供 exam_service 做自修复重试。
"""

from typing import List, Tuple
from pydantic import ValidationError as PydanticValidationError
from core.logger import get_logger
from core.exceptions import JSONExtractionError, ValidationError
from utils.json_utils import extract_json, repair_json, unwrap_questions
from schemas.question import Question
from .business_validator import validate_business_rules

logger = get_logger(__name__)


def validate(raw_response: str) -> Tuple[List[Question], List[str]]:
    """
    从 LLM 原始响应中提取并校验试题。

    流程：
    1. 尝试修复常见 JSON 格式问题
    2. 提取 JSON 数据，解包 {"questions": [...]}
    3. 用 Pydantic 逐条校验
    4. 业务规则校验（单选题1个答案、多选题至少2个等）
    5. 收集所有错误信息，供自修复重试使用

    Args:
        raw_response: LLM 返回的原始文本

    Returns:
        (校验通过的 Question 列表, 错误信息列表)
        两个都为空时表示提取 JSON 失败或全未通过。

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

    # 2. 解包 {"questions": [...]} → [...]
    data = unwrap_questions(data)

    # 3. 确保是列表
    if isinstance(data, dict):
        # 可能是单条试题，包裹成列表
        data = [data]
    elif not isinstance(data, list):
        raise JSONExtractionError(f"期望 JSON 数组，实际得到: {type(data).__name__}")

    # 4. Pydantic 逐条校验
    questions = []
    all_errors = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"跳过非对象元素 [{i}]: {type(item).__name__}")
            continue

        try:
            question = Question.model_validate(item)
            questions.append(question)
        except PydanticValidationError as e:
            error_detail = f"试题 [{i}] 字段校验失败: {e.errors()}"
            logger.warning(error_detail)
            all_errors.append(error_detail)
            continue

    if not questions:
        all_errors.append(
            f"所有试题字段校验失败（共 {len(data)} 条原始数据）。"
        )
        return [], all_errors

    # 5. 业务规则校验
    business_errors = validate_business_rules(questions)
    all_errors.extend(business_errors)

    # 如果有业务规则错误，移除校验不通过的题目
    if business_errors:
        # 收集有问题的题目索引
        bad_indices = set()
        for err in business_errors:
            # 解析错误信息中的索引，如 "单选题 [0] 应有..."
            import re
            match = re.search(r'\[(\d+)\]', err)
            if match:
                bad_indices.add(int(match.group(1)))

        # 按索引倒序移除，避免移位问题
        questions = [q for i, q in enumerate(questions) if i not in bad_indices]

        if not questions:
            all_errors.append("所有试题均未通过业务规则校验")
            return [], all_errors

    logger.info(
        f"校验完成: {len(questions)} 道通过, {len(all_errors)} 个错误"
    )
    return questions, all_errors
