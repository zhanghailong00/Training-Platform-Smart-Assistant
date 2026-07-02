"""LLM 调用组件：DeepSeek API + 重试 + 超时"""

import time
from typing import List, Dict
from openai import OpenAI
from core.settings import settings
from core.logger import get_logger
from core.exceptions import LLMTimeoutError, LLMAPIError

logger = get_logger(__name__)


def _get_client() -> OpenAI:
    """延迟初始化 OpenAI 客户端（避免模块导入时报 Missing credentials）"""
    if not settings.llm_api_key:
        raise LLMAPIError("DeepSeek API Key 未配置，请在 .env 文件中设置 DEEPSEEK_API_KEY")
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_request_timeout,
    )


def generate(messages: List[Dict[str, str]]) -> str:
    """
    调用 DeepSeek API 生成响应，带指数退避重试。

    Args:
        messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    Returns:
        LLM 响应的原始文本

    Raises:
        LLMTimeoutError: 请求超时
        LLMAPIError: API 调用失败（Key 无效、余额不足等）
    """
    if not settings.llm_api_key:
        raise LLMAPIError("DeepSeek API Key 未配置，请在 .env 文件中设置 DEEPSEEK_API_KEY")

    last_error = None

    for attempt in range(settings.max_retries):
        try:
            logger.info(
                f"调用 DeepSeek API (attempt {attempt + 1}/{settings.max_retries}): "
                f"model={settings.llm_model}, messages_count={len(messages)}"
            )

            client = _get_client()
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                top_p=settings.llm_top_p,
            )

            content = response.choices[0].message.content
            usage = response.usage

            logger.info(
                f"DeepSeek API 调用成功: "
                f"prompt_tokens={usage.prompt_tokens}, "
                f"completion_tokens={usage.completion_tokens}, "
                f"total_tokens={usage.total_tokens}"
            )

            return content

        except Exception as e:
            last_error = e
            error_msg = str(e)

            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                logger.warning(f"DeepSeek API 超时 (attempt {attempt + 1}): {e}")
                if attempt == settings.max_retries - 1:
                    raise LLMTimeoutError(f"DeepSeek API 请求超时（已重试 {settings.max_retries} 次）")
            elif "401" in error_msg or "403" in error_msg:
                raise LLMAPIError("DeepSeek API Key 无效或无权访问，请检查 DEEPSEEK_API_KEY")
            elif "402" in error_msg or "429" in error_msg or "insufficient" in error_msg.lower():
                raise LLMAPIError("DeepSeek API 余额不足或请求频率过高，请检查账户")
            else:
                logger.warning(f"DeepSeek API 调用失败 (attempt {attempt + 1}): {e}")

            if attempt < settings.max_retries - 1:
                delay = settings.RETRY_BASE_DELAY ** (attempt + 1) if hasattr(settings, 'RETRY_BASE_DELAY') else 2 ** (attempt + 1)
                logger.info(f"等待 {delay}s 后重试...")
                time.sleep(delay)

    raise LLMAPIError(f"DeepSeek API 调用失败（已重试 {settings.max_retries} 次）: {last_error}")
