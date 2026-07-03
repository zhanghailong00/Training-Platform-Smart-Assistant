"""LLM 调用组件：多模型自动切换 + 重试 + 超时

调用策略：
1. 优先调用主模型（DeepSeek）
2. 主模型不可用时，自动切换到备用模型（Qwen）
3. 每个模型内部有指数退避重试
4. 只有致命错误（Key 无效）才不重试
"""

import time
from typing import List, Dict, Optional
from openai import OpenAI
from core.settings import settings
from core.logger import get_logger
from core.exceptions import LLMTimeoutError, LLMAPIError

logger = get_logger(__name__)

# 模块级状态：标记主模型是否已失效
# 一旦失效，本次请求后续题型直接走备用模型，不再重试主模型
_primary_failed = False


def reset_provider_state() -> None:
    """重置模型状态，下一次调用会重新尝试主模型"""
    global _primary_failed
    _primary_failed = False


def _call_provider(
    api_key: str,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    provider_name: str,
) -> str:
    """
    调用单个模型，带指数退避重试。

    Returns:
        LLM 响应的原始文本

    Raises:
        Exception: 所有错误都会触发 fallback（两个厂商独立账户）
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=settings.llm_request_timeout,
    )

    last_error = None

    for attempt in range(settings.max_retries):
        try:
            logger.info(
                f"调用 {provider_name} (attempt {attempt + 1}/{settings.max_retries}): "
                f"model={model}, messages_count={len(messages)}"
            )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={'type': 'json_object'},
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                top_p=settings.llm_top_p,
            )

            content = response.choices[0].message.content

            if not content or not content.strip():
                logger.warning(f"{provider_name} 返回了空 content，按失败处理")
                raise ValueError("Empty response content")

            usage = response.usage
            logger.info(
                f"{provider_name} 调用成功: "
                f"prompt_tokens={usage.prompt_tokens}, "
                f"completion_tokens={usage.completion_tokens}, "
                f"total_tokens={usage.total_tokens}"
            )
            return content

        except Exception as e:
            last_error = e
            error_msg = str(e)

            # 所有错误都走重试/fallback（两个厂商独立账户，一个欠费不影响另一个）
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                logger.warning(f"{provider_name} 超时 (attempt {attempt + 1}): {e}")
            else:
                logger.warning(f"{provider_name} 调用失败 (attempt {attempt + 1}): {e}")

            if attempt < settings.max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.info(f"等待 {delay}s 后重试...")
                time.sleep(delay)

    # 所有重试都用完了，把最后一次异常往上抛
    raise last_error  # type: ignore


def generate(messages: List[Dict[str, str]]) -> str:
    """
    调用 LLM 生成响应，主模型失败时自动切换到备用模型。

    调用策略：
    - 主模型（DeepSeek）失败一次后，本次请求后续调用直接走备用模型（Qwen）
    - 下次请求会重新尝试主模型

    Args:
        messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    Returns:
        LLM 响应的原始文本

    Raises:
        LLMAPIError: 所有模型均不可用
    """
    global _primary_failed

    if not settings.llm_api_key:
        raise LLMAPIError("DeepSeek API Key 未配置，请在 .env 文件中设置 DEEPSEEK_API_KEY")

    # 主模型已失效 → 直接走备用模型
    if _primary_failed and settings.fallback_api_key:
        logger.info("主模型已标记为不可用，直接使用备用模型 Qwen")
        return _call_provider(
            settings.fallback_api_key,
            settings.fallback_base_url,
            settings.fallback_model,
            messages,
            "Qwen",
        )

    # 主模型未失效 → 先试主模型
    try:
        result = _call_provider(
            settings.llm_api_key,
            settings.llm_base_url,
            settings.llm_model,
            messages,
            "DeepSeek",
        )
        return result
    except Exception as e:
        logger.warning(f"主模型 DeepSeek 不可用: {e}")
        _primary_failed = True  # 标记失效，后续题型直接走备用

        # 尝试备用模型
        if settings.fallback_api_key:
            logger.info("切换到备用模型 Qwen")
            try:
                return _call_provider(
                    settings.fallback_api_key,
                    settings.fallback_base_url,
                    settings.fallback_model,
                    messages,
                    "Qwen",
                )
            except Exception as fallback_error:
                raise LLMAPIError(
                    f"所有模型均不可用。主模型: {e}，备用模型: {fallback_error}"
                )

        raise LLMAPIError(f"主模型不可用且未配置备用模型: {e}")
