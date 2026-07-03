"""JSON 提取与修复工具"""

import re
import json
from typing import Any


def extract_json(text: str) -> Any:
    """
    从 LLM 原始响应中提取 JSON。

    尝试顺序：
    1. 直接解析整个文本
    2. 匹配 ```json ... ``` 代码块
    3. 匹配 ``` ... ``` 代码块
    4. 匹配最外层 [...] 或 {...}
    """
    if not text:
        raise ValueError("响应文本为空")

    text = text.strip()

    # 尝试 1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 2：```json 代码块
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试 3：``` 代码块
    match = re.search(r"```\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试 4：最外层 JSON 数组或对象
    # 找最外层 [...]
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 找最外层 {...}
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从响应中提取有效 JSON。原始响应前 200 字符: {text[:200]}")


def unwrap_questions(data: Any) -> Any:
    """
    解包 JSON Mode 输出的 {"questions": [...]} 格式。

    JSON Mode 要求输出 JSON 对象，不能输出数组。
    所以 LLM 会输出 {"questions": [...]}，这个函数把它转回 [...]。
    如果 data 已经是数组，直接返回。
    """
    if isinstance(data, dict) and "questions" in data:
        return data["questions"]
    return data


def repair_json(text: str) -> str:
    """
    修复常见的 JSON 格式问题。
    """
    text = text.strip()

    # 去除首尾的 markdown 标记
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?\s*```$", "", text)

    # 修复：LLM 有时输出单引号 JSON
    # 简单策略：如果双引号很少，尝试替换单引号
    if text.count('"') < 5 and text.count("'"):
        text = text.replace("'", '"')

    # 修复：尾部多余逗号
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text.strip()
