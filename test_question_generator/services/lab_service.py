"""实验手册生成服务：AI 生成 Markdown → 预览编辑 → 下载 Word"""

import uuid
from pathlib import Path
from core.logger import get_logger
from core.exceptions import LLMAPIError
from schemas.lab import LabManualRequest, LabManualResponse
from components.llm_client import generate as llm_generate
from components.docx_builder import markdown_to_docx

logger = get_logger(__name__)

# 下载目录
_DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / "downloads"


def _load_prompt_template(template_type: str) -> tuple[str, str]:
    """加载 Prompt 模板"""
    import yaml

    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "lab_manual.yaml"
    with open(prompt_path, "r", encoding="utf-8") as f:
        templates = yaml.safe_load(f)

    system_prompt = templates.get("system", "")

    if template_type == "report":
        user_template = templates.get("report_template", "")
    else:
        user_template = templates.get("manual_template", "")

    return system_prompt, user_template


def generate_lab_manual(request: LabManualRequest) -> LabManualResponse:
    """
    生成实验手册或实验报告模板。

    Args:
        request: 实验手册生成请求

    Returns:
        LabManualResponse（包含 Markdown 内容和下载地址）
    """
    # 参数校验
    if not request.title or not request.title.strip():
        return LabManualResponse(success=False, error="实验名称不能为空")

    if not request.document_text or not request.document_text.strip():
        return LabManualResponse(success=False, error="请输入教学内容或上传文档")

    logger.info(
        f"生成实验{'报告模板' if request.template_type == 'report' else '指导手册'}: "
        f"title={request.title}"
    )

    # 加载 Prompt 模板
    try:
        system_prompt, user_template = _load_prompt_template(request.template_type)
    except Exception as e:
        logger.error(f"加载 Prompt 模板失败: {e}")
        return LabManualResponse(success=False, error=f"加载 Prompt 模板失败: {e}")

    # 构建 messages
    user_prompt = user_template.format(
        title=request.title,
        document_text=request.document_text,
        requirements=request.requirements if request.requirements else "无",
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 调 LLM（use_json_mode=False，因为输出纯文本）
    try:
        raw_response = llm_generate(messages, use_json_mode=False)
    except LLMAPIError as e:
        logger.error(f"LLM 调用失败: {e}")
        return LabManualResponse(success=False, error=f"LLM 服务不可用: {e}")
    except Exception as e:
        logger.error(f"生成失败: {e}")
        return LabManualResponse(success=False, error=str(e))

    # 清理响应文本
    markdown = raw_response.strip()

    if not markdown:
        return LabManualResponse(success=False, error="生成的内容为空")

    # 生成 Word 文件
    try:
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.docx"
        output_path = str(_DOWNLOAD_DIR / filename)
        markdown_to_docx(markdown, output_path)
        download_url = f"/api/v1/lab-manual/{filename}/download"
    except Exception as e:
        logger.error(f"Word 文件生成失败: {e}")
        return LabManualResponse(
            success=True,
            title=request.title,
            markdown=markdown,
            error=f"Word 生成失败（Markdown 已保留）: {e}",
        )

    logger.info(
        f"实验{'报告模板' if request.template_type == 'report' else '指导手册'}生成成功: "
        f"{len(markdown)} 字符"
    )
    return LabManualResponse(
        success=True,
        title=request.title,
        markdown=markdown,
        download_url=download_url,
    )