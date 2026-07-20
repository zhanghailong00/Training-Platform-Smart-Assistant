"""API 路由：提供 REST API 端点供实训平台调用"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from pathlib import Path
from schemas.request import GenerateRequest
from schemas.response import GenerateResponse
from schemas.course_intro import CourseIntroRequest, CourseIntroResponse
from schemas.lab import LabManualRequest, LabManualResponse
from schemas.ocr import OcrRequest
from services.exam_service import generate_questions
from services.course_intro_service import generate_course_intro
from services.lab_service import generate_lab_manual
from services.ocr_service import ocr_recognize
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


@router.post("/course-intro", response_model=CourseIntroResponse)
async def course_intro(req: CourseIntroRequest):
    """
    生成课程简介。

    接收课程名称和章节结构，返回一段 200-300 字的课程简介文本。
    """
    try:
        return generate_course_intro(req)
    except Exception as e:
        logger.exception(f"课程简介生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lab-manual", response_model=LabManualResponse)
async def lab_manual(req: LabManualRequest):
    """
    生成实验指导手册或实验报告模板。

    接收实验名称和教学内容，返回 Markdown 内容 + Word 下载地址。
    """
    try:
        return generate_lab_manual(req)
    except Exception as e:
        logger.exception(f"实验手册生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lab-manual/{filename}/download")
async def download_lab_manual(filename: str):
    """
    下载生成的 Word 文件。
    """
    file_path = Path(__file__).resolve().parent.parent / "downloads" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/ocr-recognize", response_model=GenerateResponse)
async def ocr_recognize_endpoint(
    image: UploadFile = File(..., description="试卷图片"),
    subject_bank_name: str = Form("OCR识别题库", description="题库名称"),
    subject_bank_remark: str = Form("", description="题库描述"),
):
    """
    OCR 识别图片中的试题。

    上传试卷图片，自动识别图片中的文字，提取试题信息，返回标准题库 JSON。
    """
    # 读取上传的图片
    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="上传的图片为空")

    logger.info(
        f"OCR 识别请求: image={image.filename}, "
        f"size={len(image_bytes)} bytes"
    )

    req = OcrRequest(
        subject_bank_name=subject_bank_name,
        subject_bank_remark=subject_bank_remark,
    )

    try:
        return ocr_recognize(req, image_bytes)
    except Exception as e:
        logger.exception(f"OCR 识别失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
