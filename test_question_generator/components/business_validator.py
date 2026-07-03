"""业务规则校验组件：校验题型相关的业务规则

JSON Mode 保证语法合法，Pydantic 保证字段正确，
但业务规则（如单选题只能有 1 个正确答案）需要这一层来保证。
"""

from typing import List
from core.logger import get_logger
from schemas.question import Question

logger = get_logger(__name__)


def validate_business_rules(questions: List[Question]) -> List[str]:
    """
    校验每道题的题型业务规则，返回错误信息列表。

    校验规则：
    - 单选题：恰好 4 个选项，恰好 1 个正确答案
    - 多选题：至少 2 个正确答案
    - 判断题：选项必须为"正确"和"错误"
    - 简答题：options 为空，subAnswer 不为空
    """
    errors = []

    for i, q in enumerate(questions):
        try:
            if q.type == 0:  # 单选题
                _validate_single_choice(q, i, errors)
            elif q.type == 1:  # 多选题
                _validate_multi_choice(q, i, errors)
            elif q.type == 2:  # 判断题
                _validate_true_false(q, i, errors)
            elif q.type == 3:  # 简答题
                _validate_essay(q, i, errors)
        except Exception as e:
            errors.append(f"题型 [{i}] 校验异常: {e}")

    if errors:
        logger.warning(f"业务规则校验不通过: {len(errors)} 个问题")

    return errors


def _validate_single_choice(q: Question, i: int, errors: List[str]) -> None:
    """校验单选题"""
    if len(q.options) != 4:
        errors.append(f"单选题 [{i}] 应有 4 个选项，实际 {len(q.options)} 个")

    right_count = sum(1 for o in q.options if o.isRight)
    if right_count != 1:
        errors.append(f"单选题 [{i}] 应有 1 个正确答案，实际 {right_count} 个")

    # 检查错误选项是否有解析
    for j, opt in enumerate(q.options):
        if not opt.isRight and not opt.analysis:
            errors.append(f"单选题 [{i}] 错误选项 [{j}] 缺少 analysis 解析")


def _validate_multi_choice(q: Question, i: int, errors: List[str]) -> None:
    """校验多选题"""
    if len(q.options) < 2:
        errors.append(f"多选题 [{i}] 至少应有 2 个选项，实际 {len(q.options)} 个")

    right_count = sum(1 for o in q.options if o.isRight)
    if right_count < 2:
        errors.append(f"多选题 [{i}] 至少应有 2 个正确答案，实际 {right_count} 个")

    if right_count > 4:
        errors.append(f"多选题 [{i}] 最多 4 个正确答案，实际 {right_count} 个")

    # 检查错误选项是否有解析
    for j, opt in enumerate(q.options):
        if not opt.isRight and not opt.analysis:
            errors.append(f"多选题 [{i}] 错误选项 [{j}] 缺少 analysis 解析")


def _validate_true_false(q: Question, i: int, errors: List[str]) -> None:
    """校验判断题"""
    if len(q.options) != 2:
        errors.append(f"判断题 [{i}] 应有 2 个选项，实际 {len(q.options)} 个")
        return

    contents = {o.content for o in q.options}
    expected = {"正确", "错误"}
    if contents != expected:
        errors.append(f"判断题 [{i}] 选项必须为'正确'和'错误'，实际为: {contents}")

    right_count = sum(1 for o in q.options if o.isRight)
    if right_count != 1:
        errors.append(f"判断题 [{i}] 应有 1 个正确答案，实际 {right_count} 个")

    # 错误选项应有解析
    for j, opt in enumerate(q.options):
        if not opt.isRight and not opt.analysis:
            errors.append(f"判断题 [{i}] 错误选项 [{j}] 缺少 analysis 解析")


def _validate_essay(q: Question, i: int, errors: List[str]) -> None:
    """校验简答题"""
    if q.options:
        errors.append(f"简答题 [{i}] options 应为空数组，实际有 {len(q.options)} 个选项")

    if not q.subAnswer or not q.subAnswer.strip():
        errors.append(f"简答题 [{i}] subAnswer（参考答案）不能为空")
