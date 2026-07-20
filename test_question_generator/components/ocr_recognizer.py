"""OCR 识别组件：基于 Qwen3.5-OCR 模型识别图片中的文字"""

import base64
from openai import OpenAI
from core.settings import settings
from core.logger import get_logger
from core.exceptions import AppException

logger = get_logger(__name__)


class OcrError(AppException):
    """OCR 识别异常"""
    pass


def _get_client() -> OpenAI:
    """获取 OpenAI 客户端（指向 Qwen3.5-OCR）"""
    if not settings.daskscope_api_key:
        raise OcrError(
            "Qwen3.5-OCR 未配置，请在 .env 中设置 DASHSCOPE_API_KEY"
        )
    return OpenAI(
        api_key=settings.daskscope_api_key,
        base_url=settings.qwen_ocr_base_url,
    )


def recognize(image_bytes: bytes) -> str:
    """
    调用 Qwen3.5-OCR 识别图片中的文字。

    Args:
        image_bytes: 图片文件的二进制数据

    Returns:
        识别出的文本

    Raises:
        OcrError: 识别失败
    """
    if not image_bytes:
        raise OcrError("图片内容为空")

    client = _get_client()

    # 将图片转为 base64 data URL
    # 通过文件头判断图片类型
    if image_bytes[:4] == b'\x89PNG':
        img_type = 'png'
    elif image_bytes[:2] in (b'\xFF\xD8',):
        img_type = 'jpeg'
    elif image_bytes[:4] == b'RIFF':
        img_type = 'webp'
    elif image_bytes[:2] == b'BM':
        img_type = 'bmp'
    else:
        img_type = 'jpeg'  # 默认

    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    data_url = f"data:image/{img_type};base64,{base64_image}"

    try:
        completion = client.chat.completions.create(
            model=settings.qwen_ocr_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {"type": "text", "text": "请仅输出图像中的文本内容，按原格式排列。"},
                    ],
                },
            ],
        )

        text = completion.choices[0].message.content
        if not text or not text.strip():
            logger.warning("OCR 识别结果为空")
            return ""

        logger.info(
            f"OCR 识别完成: {len(text)} 字符, "
            f"图片大小: {len(image_bytes)} bytes"
        )
        return text.strip()

    except Exception as e:
        raise OcrError(f"OCR 识别失败: {e}")