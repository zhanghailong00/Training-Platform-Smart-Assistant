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


def generate_questions(
    request: GenerateRequest,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> GenerateResponse:
    """
    完整的试题生成流程。

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

    # 3. 按题型逐个生成
    all_questions: list[Question] = []
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

        try:
            # 构建 Prompt
            messages = build_messages(
                text=text,
                question_type=qtype,
                count=request.count_per_type,
                level=request.difficulty,
                level_name=level_name,
                requirements=request.requirements,
            )

            # 调 LLM
            raw_response = llm_generate(messages)

            # 校验
            questions = validate(raw_response)
            all_questions.extend(questions)

            logger.info(f"{type_name} 生成完成: {len(questions)} 道")

        except Exception as e:
            logger.error(f"{type_name} 生成失败: {e}")
            return GenerateResponse(
                success=False,
                error=f"{type_name} 生成失败: {e}",
            )

    # 4. 组装响应
    logger.info(f"试题生成完成，共 {len(all_questions)} 道")

    return GenerateResponse(
        success=True,
        subjectBanks=[
            SubjectBank(
                name=request.subject_bank_name,
                remark=request.subject_bank_remark,
                questions=all_questions,
            )
        ],
    )
