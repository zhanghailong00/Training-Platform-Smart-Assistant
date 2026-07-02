"""文本预处理组件：清洗 + 截断"""

import re
from core.logger import get_logger
from utils.token_utils import estimate_tokens, truncate_by_tokens
from core.constants import MAX_DOCUMENT_TOKENS

logger = get_logger(__name__)


def clean(text: str) -> str:
    """
    清洗文本：
    - 合并多个连续空行为单个空行
    - 去除首尾空白
    - 去除行首尾多余空格
    """
    if not text:
        return ""

    # 去除每行首尾空格
    lines = [line.strip() for line in text.splitlines()]
    # 合并多个连续空行
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        is_empty = not line
        if is_empty:
            if not prev_empty:
                cleaned_lines.append(line)
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    result = "\n".join(cleaned_lines).strip()
    logger.debug(f"文本清洗: {len(text)} → {len(result)} 字符")
    return result


def process(text: str, max_tokens: int = MAX_DOCUMENT_TOKENS) -> str:
    """
    预处理入口：清洗 + token 估算 + 截断。

    Returns:
        处理后的文本
    """
    text = clean(text)

    if not text:
        return ""

    token_count = estimate_tokens(text)

    if token_count <= max_tokens:
        logger.info(f"文本预处理完成: {len(text)} 字符, {token_count} tokens（无需截断）")
        return text

    # 需要截断
    text, was_truncated = truncate_by_tokens(text, max_tokens)
    if was_truncated:
        logger.warning(
            f"文本过长，已截断: {token_count} → {max_tokens} tokens "
            f"({len(text)} 字符)"
        )

    return text
