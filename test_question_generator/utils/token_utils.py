"""Token 估算工具（基于 tiktoken）"""

import tiktoken


# 使用 cl100k_base 编码（GPT-4 / DeepSeek 通用）
_ENCODING = tiktoken.get_encoding("cl100k_base")


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量"""
    if not text:
        return 0
    return len(_ENCODING.encode(text))


def truncate_by_tokens(text: str, max_tokens: int) -> tuple[str, bool]:
    """
    按 token 上限截断文本。

    Returns:
        (截断后的文本, 是否发生了截断)
    """
    if not text:
        return text, False

    tokens = _ENCODING.encode(text)
    if len(tokens) <= max_tokens:
        return text, False

    truncated_tokens = tokens[:max_tokens]
    truncated_text = _ENCODING.decode(truncated_tokens)
    return truncated_text, True
