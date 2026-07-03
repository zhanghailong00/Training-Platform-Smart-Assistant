"""试题生成服务：串联所有组件，完成一次完整的试题生成"""

from typing import Optional
from core.logger import get_logger
from core.constants import QUESTION_TYPE_NAMES, DIFFICULTY_NAMES
from schemas.request import GenerateRequest
from schemas.response import GenerateResponse, SubjectBank
from schemas.question import Question
from components.parser import parse
from components.preprocessor import process
from components.prompt_builder import build_messages
from components.llm_client import generate as llm_generate
from components.validator import validate

logger = get_logger(__name__)

# 每种题型的最大重试次数
MAX_RETRIES_PER_TYPE = 3


def generate_questions(
    request: GenerateRequest,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> GenerateResponse:
    """
    完整的试题生成流程。

    每题型最多重试 3 次，校验失败时把错误喂给 LLM 自修复。
    部分题型失败时降级返回已成功的题目，不阻塞。

    Args:
        request: 生成请求参数
        file_bytes: 上传文件的字节（可选）
        filename: 上传文件的文件名（可选）

    Returns:
        GenerateResponse（包含 subjectBanks）
    """
    # 1. 获取文本
    if file_bytes and filename:
        logger.info(f"解析上传文件: {filename}")
        text = parse(file_bytes, filename)
    elif request.document_text:
        text = request.document_text
    else:
        return GenerateResponse(
            success=False,
            error="请提供文档文件或输入教学内容",
        )

    if not text.strip():
        return GenerateResponse(
            success=False,
            error="文档内容为空，请检查文件或输入文本",
        )

    # 2. 预处理（清洗 + 截断）
    text = process(text)

    # 3. 按题型逐个生成（带自修复重试）
    all_questions: list[Question] = []
    failed_types: list[str] = []
    level_name = DIFFICULTY_NAMES.get(request.difficulty, "简单")

    for qtype in request.question_types:
        if qtype not in QUESTION_TYPE_NAMES:
            logger.warning(f"跳过不支持的题型: {qtype}")
            continue

        type_name = QUESTION_TYPE_NAMES[qtype]
        logger.info(
            f"开始生成 {type_name}: count={request.count_per_type}, "
            f"difficulty={level_name}"
        )

        type_success = False
        last_errors = []

        for attempt in range(1, MAX_RETRIES_PER_TYPE + 1):
            try:
                # 构建 Prompt（第 2、3 次时附带错误信息）
                if attempt == 1:
                    messages = build_messages(
                        text=text,
                        question_type=qtype,
                        count=request.count_per_type,
                        level=request.difficulty,
                        level_name=level_name,
                        requirements=request.requirements,
                    )
                else:
                    # 自修复：把校验错误喂给 LLM
                    error_feedback = _build_fix_prompt(text, qtype, request, level_name, last_errors)
                    messages = [
                        {"role": "system", "content": _get_system_prompt()},
                        {"role": "user", "content": error_feedback},
                    ]

                # 调 LLM
                raw_response = llm_generate(messages)

                # 校验（Pydantic + 业务规则）
                questions, errors = validate(raw_response)

                if questions and not errors:
                    # 全部通过
                    all_questions.extend(questions)
                    type_success = True
                    logger.info(f"{type_name} 生成完成: {len(questions)} 道")
                    break
                elif questions and errors:
                    # 部分通过，保留已通过的题目
                    all_questions.extend(questions)
                    last_errors = errors
                    logger.warning(
                        f"{type_name} attempt {attempt}: "
                        f"{len(questions)} 道通过, "
                        f"{len(errors)} 个错误, 继续重试"
                    )
                else:
                    # 全部未通过
                    last_errors = errors if errors else ["校验全部未通过"]
                    logger.warning(
                        f"{type_name} attempt {attempt}: "
                        f"全部未通过, 错误: {last_errors}"
                    )

            except Exception as e:
                last_errors = [f"异常: {e}"]
                logger.warning(f"{type_name} attempt {attempt} 异常: {e}")

        if not type_success:
            failed_types.append(type_name)
            logger.error(f"{type_name} 生成失败（已重试 {MAX_RETRIES_PER_TYPE} 次）")

    # 4. 降级返回
    if all_questions:
        error_msg = None
        if failed_types:
            error_msg = f"以下题型生成失败: {', '.join(failed_types)}"
            logger.warning(f"部分题型失败: {error_msg}")

        return GenerateResponse(
            success=True,
            subjectBanks=[
                SubjectBank(
                    name=request.subject_bank_name,
                    remark=request.subject_bank_remark,
                    questions=all_questions,
                )
            ],
            error=error_msg,
        )
    else:
        error_msg = f"所有题型均生成失败"
        if failed_types:
            error_msg += f"（失败题型: {', '.join(failed_types)}）"
        return GenerateResponse(
            success=False,
            error=error_msg,
        )


def _get_system_prompt() -> str:
    """获取 system prompt"""
    from components.prompt_builder import load_template
    templates = load_template()
    return templates.get("system", "")


def _build_fix_prompt(
    text: str,
    qtype: int,
    request: GenerateRequest,
    level_name: str,
    errors: list[str],
) -> str:
    """构建自修复 Prompt：把校验错误告诉 LLM，要求重新生成"""
    from core.constants import QUESTION_TYPE_NAMES

    type_name = QUESTION_TYPE_NAMES.get(qtype, "未知")

    error_detail = "\n".join(f"  - {e}" for e in errors)

    prompt = f"""请根据以下教学内容重新生成 {request.count_per_type} 道{type_name}（type={qtype}），难度为 {level_name}（level={request.difficulty}）。

你之前生成的题目存在以下问题，请务必修正：

{error_detail}

要求：
- 输出格式为 JSON 对象，所有试题放在 questions 字段中
- 确保 JSON 语法正确：括号成对、引号闭合、无尾随逗号
- 题目必须基于以下教学内容，不能超纲
- 每个错误选项的 analysis 必须说明该选项为什么错
- 正确选项的 analysis 可以为 null

## 教学内容

{text}

## 额外要求

{request.requirements if request.requirements else "无"}

请输出 JSON 对象。"""
    return prompt
