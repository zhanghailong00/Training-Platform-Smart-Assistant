import os
from pathlib import Path
from dotenv import load_dotenv
from .constants import (
    DEFAULT_LLM_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_P,
    MAX_RETRIES,
    LLM_REQUEST_TIMEOUT,
    MAX_DOCUMENT_TOKENS,
    DEFAULT_HOST,
    DEFAULT_PORT,
)


# 加载 .env 文件
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class Settings:
    """全局配置单例"""

    # DeepSeek API（主模型）
    llm_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    llm_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    llm_model: str = os.getenv("DEEPSEEK_MODEL", DEFAULT_LLM_MODEL)
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    llm_top_p: float = float(os.getenv("LLM_TOP_P", str(DEFAULT_TOP_P)))

    # Qwen API（备用模型，主模型不可用时自动切换）
    fallback_api_key: str = os.getenv("FALLBACK_API_KEY", "")
    fallback_base_url: str = os.getenv("FALLBACK_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    fallback_model: str = os.getenv("FALLBACK_MODEL", "qwen-plus")

    # 重试 & 超时
    max_retries: int = int(os.getenv("MAX_RETRIES", str(MAX_RETRIES)))
    llm_request_timeout: int = int(os.getenv("LLM_REQUEST_TIMEOUT", str(LLM_REQUEST_TIMEOUT)))

    # 文档处理
    max_document_tokens: int = int(os.getenv("MAX_DOCUMENT_TOKENS", str(MAX_DOCUMENT_TOKENS)))

    # 服务
    host: str = os.getenv("HOST", DEFAULT_HOST)
    port: int = int(os.getenv("PORT", str(DEFAULT_PORT)))

    # 日志
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __repr__(self) -> str:
        return (
            f"Settings(model={self.llm_model}, "
            f"temperature={self.llm_temperature}, "
            f"max_tokens={self.llm_max_tokens})"
        )


settings = Settings()
