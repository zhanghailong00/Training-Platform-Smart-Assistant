"""Prompt 构建组件：加载 YAML 模板 + 变量替换 → messages"""

import yaml
from pathlib import Path
from typing import List, Dict
from core.logger import get_logger
from core.constants import QUESTION_TYPE_MAP, QUESTION_TYPE_NAMES, DIFFICULTY_NAMES

logger = get_logger(__name__)

# Prompt 模板路径
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_yaml(filepath: Path) -> dict:
    """加载 YAML 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_template() -> dict:
    """加载试题生成 Prompt 模板"""
    filepath = _PROMPTS_DIR / "exam_generation.yaml"
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {filepath}")
    return _load_yaml(filepath)


def build_messages(
    text: str,
    question_type: int,
    count: int,
    level: int,
    level_name: str,
    requirements: str,
) -> List[Dict[str, str]]:
    """
    构建发送给 LLM 的 messages。

    Args:
        text: 教学内容文本
        question_type: 题型（0=单选, 1=多选, 2=判断, 3=简答）
        count: 生成数量
        level: 难度（0=简单, 1=困难）
        level_name: 难度名称
        requirements: 老师的具体要求

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    templates = load_template()
    system_prompt = templates.get("system", "")

    type_key = QUESTION_TYPE_MAP.get(question_type)
    if not type_key or type_key not in templates:
        raise ValueError(f"不支持的题型: {question_type}")

    type_name = QUESTION_TYPE_NAMES.get(question_type, "未知")

    # 构建 user prompt
    instruction_template = templates[type_key].get("instruction", "")
    user_prompt = instruction_template.format(
        count=count,
        level=level,
        levelName=level_name,
    )

    # 拼接教学内容和要求
    user_prompt += f"\n\n## 教学内容\n\n{text}"

    if requirements:
        user_prompt += f"\n\n## 额外要求\n\n{requirements}"

    user_prompt += "\n\n请严格按 JSON 格式输出，不要输出任何 JSON 之外的内容。"

    logger.info(
        f"Prompt 构建完成: type={type_name}, count={count}, "
        f"difficulty={level_name}, text_len={len(text)}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
