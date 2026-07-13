"""课程简介生成服务：根据课程名称和章节结构，调用 LLM 生成简介"""

from core.logger import get_logger
from core.exceptions import LLMAPIError
from schemas.course_intro import CourseIntroRequest, CourseIntroResponse
from components.llm_client import generate as llm_generate

logger = get_logger(__name__)


def _format_chapters(chapters) -> str:
    """将章节列表格式化为带缩进的文本"""
    lines = []
    for ch in chapters:
        lines.append(f"- {ch.name}")
        if ch.lessons:
            for lesson in ch.lessons:
                lines.append(f"  - {lesson}")
    return "\n".join(lines)


def generate_course_intro(request: CourseIntroRequest) -> CourseIntroResponse:
    """
    生成课程简介。

    Args:
        request: 课程简介生成请求（课程名称 + 章节列表）

    Returns:
        CourseIntroResponse（包含生成的简介文本）
    """
    # 参数校验
    if not request.course_name or not request.course_name.strip():
        return CourseIntroResponse(success=False, error="课程名称不能为空")

    if not request.chapters:
        return CourseIntroResponse(success=False, error="章节列表不能为空")

    # 格式化章节列表
    chapter_list = _format_chapters(request.chapters)
    logger.info(
        f"生成课程简介: course={request.course_name}, "
        f"chapters={len(request.chapters)} 章"
    )

    # 加载 Prompt 模板
    try:
        from components.prompt_builder import load_template as _load_template
        # 直接用 yaml 加载 course_intro.yaml
        import yaml
        from pathlib import Path

        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "course_intro.yaml"
        with open(prompt_path, "r", encoding="utf-8") as f:
            templates = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载 Prompt 模板失败: {e}")
        return CourseIntroResponse(success=False, error=f"加载 Prompt 模板失败: {e}")

    # 构建 messages
    system_prompt = templates.get("system", "")
    user_prompt = templates["user"].format(
        course_name=request.course_name,
        chapter_list=chapter_list,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 调 LLM
    try:
        raw_response = llm_generate(messages, use_json_mode=False)
    except LLMAPIError as e:
        logger.error(f"LLM 调用失败: {e}")
        return CourseIntroResponse(success=False, error=f"LLM 服务不可用: {e}")
    except Exception as e:
        logger.error(f"生成失败: {e}")
        return CourseIntroResponse(success=False, error=str(e))

    # 清理响应文本
    intro = raw_response.strip()

    if not intro:
        return CourseIntroResponse(success=False, error="生成的简介为空")

    logger.info(f"课程简介生成成功: {len(intro)} 字")
    return CourseIntroResponse(success=True, intro=intro)
