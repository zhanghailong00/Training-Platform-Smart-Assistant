"""OCR 试题识别服务：图片 → OCR 识别 → LLM 结构化提取 → 输出 JSON"""

import json
import yaml
from pathlib import Path
from pydantic import ValidationError
from core.logger import get_logger
from core.exceptions import LLMAPIError
from schemas.ocr import OcrRequest
from schemas.response import GenerateResponse, SubjectBank
from schemas.question import Question
from components.ocr_recognizer import recognize, OcrError
from components.llm_client import generate as llm_generate
from utils.json_utils import extract_json, unwrap_questions

logger = get_logger(__name__)


def _load_ocr_prompt() -> tuple[str, str]:
    """加载 OCR 提取 Prompt 模板"""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "ocr_extract.yaml"
    with open(prompt_path, "r", encoding="utf-8") as f:
        templates = yaml.safe_load(f)
    return templates.get("system", ""), templates.get("user", "")


def ocr_recognize(request: OcrRequest, image_bytes: bytes) -> GenerateResponse:
    """
    OCR 识别 + 结构化提取完整流程。

    Args:
        request: OCR 请求参数（题库名称等）
        image_bytes: 图片文件的二进制数据

    Returns:
        GenerateResponse（与试题生成接口一致的 JSON 格式）
    """
    # 1. OCR 识别图片文字
    try:
        ocr_text = recognize(image_bytes)
    except OcrError as e:
        logger.error(f"OCR 识别失败: {e}")
        return GenerateResponse(success=False, error=str(e))

    if not ocr_text.strip():
        return GenerateResponse(success=False, error="OCR 未识别到文字，请检查图片")

    logger.info(f"OCR 识别结果: {len(ocr_text)} 字符")

    # 2. 加载 Prompt 模板
    try:
        system_prompt, user_template = _load_ocr_prompt()
    except Exception as e:
        logger.error(f"加载 Prompt 模板失败: {e}")
        return GenerateResponse(success=False, error=f"加载 Prompt 模板失败: {e}")

    # 3. 构建 messages
    user_prompt = user_template.format(ocr_text=ocr_text)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 4. 调 LLM 结构化提取
    try:
        raw_response = llm_generate(messages, use_json_mode=True)
    except LLMAPIError as e:
        logger.error(f"LLM 调用失败: {e}")
        return GenerateResponse(success=False, error=f"LLM 服务不可用: {e}")
    except Exception as e:
        logger.error(f"结构化提取失败: {e}")
        return GenerateResponse(success=False, error=str(e))

    # 5. 预处理：补全缺失的必填字段（level、levelName）
    try:
        data = json.loads(raw_response)
        if isinstance(data, dict) and "questions" in data:
            for q in data["questions"]:
                q.setdefault("level", 0)
                q.setdefault("levelName", "简单")
        raw_response = json.dumps(data)
    except Exception:
        pass

    # 6. Pydantic 校验（只校验字段格式，不校验业务规则）
    try:
        data = extract_json(raw_response)
        data = unwrap_questions(data)
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []

        questions = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                question = Question.model_validate(item)
                questions.append(question)
            except ValidationError:
                continue

        if not questions:
            return GenerateResponse(
                success=False,
                error=f"未能从识别结果中提取出有效试题，OCR 文本: {ocr_text[:200]}",
            )
    except Exception as e:
        return GenerateResponse(
            success=False,
            error=f"结果解析失败: {e}",
        )

    # 7. 组装响应
    logger.info(f"OCR 识别完成: {len(questions)} 道题")
    return GenerateResponse(
        success=True,
        subjectBanks=[
            SubjectBank(
                name=request.subject_bank_name,
                remark=request.subject_bank_remark,
                questions=questions,
            )
        ],
    )