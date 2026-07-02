# 最大输入 token 数（超过则截断）
MAX_DOCUMENT_TOKENS = 8000

# LLM 默认配置
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TOP_P = 0.95

# 重试配置
MAX_RETRIES = 2
RETRY_BASE_DELAY = 2  # 秒，指数退避：2, 4

# 请求超时（秒）
LLM_REQUEST_TIMEOUT = 60

# 服务配置
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 7860

# 题型映射
QUESTION_TYPE_MAP = {
    0: "single_choice",
    1: "multi_choice",
    2: "true_false",
    3: "essay",
}

QUESTION_TYPE_NAMES = {
    0: "单选题",
    1: "多选题",
    2: "判断题",
    3: "简答题",
}

# 难度映射
DIFFICULTY_NAMES = {
    0: "简单",
    1: "困难",
}

# 支持的文档格式
SUPPORTED_FORMATS = {
    ".pdf": "pdf",
    ".docx": "docx",
}
