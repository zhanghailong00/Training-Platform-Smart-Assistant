"""API 路由：提供 REST API 端点供实训平台调用"""

from fastapi import APIRouter, HTTPException
from schemas.request import GenerateRequest
from schemas.response import GenerateResponse
from services.exam_service import generate_questions
from core.exceptions import (
    DocumentParseError,
    UnsupportedFormatError,
    LLMTimeoutError,
    LLMAPIError,
    JSONExtractionError,
    ValidationError,
)
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1")


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """
    生成试题。

    接收 JSON 格式的生成请求（包含文档文本或自由输入），
    返回符合同事题库格式的 subjectBanks JSON。
    """
    try:
        return generate_questions(req)
    except (DocumentParseError, UnsupportedFormatError) as e:
        logger.warning(f"文档解析错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        logger.warning(f"校验错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except JSONExtractionError as e:
        logger.error(f"JSON 提取错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except LLMTimeoutError as e:
        logger.error(f"LLM 超时: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except LLMAPIError as e:
        logger.error(f"LLM API 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {e}")


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "试题生成助手", "version": "1.0.0"}
