class AppException(Exception):
    """应用基础异常"""
    pass


class DocumentParseError(AppException):
    """文档解析失败"""

    def __init__(self, message: str = "文档无法解析，请检查文件是否损坏"):
        self.message = message
        super().__init__(message)


class UnsupportedFormatError(AppException):
    """不支持的文件格式"""

    def __init__(self, filename: str):
        self.message = f"不支持的文件格式: {filename}，仅支持 PDF 和 Word (.docx)"
        super().__init__(self.message)


class TextTooLongError(AppException):
    """文本超过 token 限制（会被自动截断，此异常仅在极端情况下抛出）"""

    def __init__(self, actual_tokens: int, max_tokens: int):
        self.actual_tokens = actual_tokens
        self.max_tokens = max_tokens
        self.message = f"文本过长 ({actual_tokens} tokens)，上限为 {max_tokens} tokens"
        super().__init__(self.message)


class LLMTimeoutError(AppException):
    """LLM 请求超时"""

    def __init__(self, message: str = "LLM 请求超时，请稍后重试"):
        self.message = message
        super().__init__(message)


class LLMAPIError(AppException):
    """LLM API 错误（Key 无效、余额不足等）"""

    def __init__(self, message: str = "LLM 服务不可用，请联系管理员"):
        self.message = message
        super().__init__(message)


class JSONExtractionError(AppException):
    """从 LLM 响应中提取 JSON 失败"""

    def __init__(self, message: str = "无法从响应中提取有效的 JSON"):
        self.message = message
        super().__init__(message)


class ValidationError(AppException):
    """数据校验失败"""

    def __init__(self, message: str = "数据校验失败"):
        self.message = message
        super().__init__(message)
