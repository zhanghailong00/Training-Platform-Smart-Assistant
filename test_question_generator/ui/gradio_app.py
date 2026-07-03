"""Gradio UI：试题生成助手前端界面"""

import json
import gradio as gr
from services.exam_service import generate_questions
from schemas.request import GenerateRequest
from core.logger import get_logger

logger = get_logger(__name__)


def _handle_generate(
    name: str,
    remark: str,
    file,
    text: str,
    requirements: str,
    types: list,
    count: int,
    difficulty: str,
) -> str:
    """
    Gradio 回调函数：处理生成请求，返回 JSON 字符串。
    """
    # 处理文件（Gradio 6.x 返回文件路径，需手动读取）
    file_bytes = None
    filename = None
    if file is not None:
        # Gradio 6.x 返回文件路径（str 或 NamedString）
        file_path = str(file)
        filename = file_path.split("/")[-1] if hasattr(file, "name") else file_path.split("\\")[-1]
        if hasattr(file, "name"):
            filename = file.name.split("/")[-1].split("\\")[-1]
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        logger.info(f"读取文件: {filename}, {len(file_bytes)} bytes")

    # 处理题型：Gradio CheckboxGroup 可能返回字符串列表
    type_values = []
    for t in types:
        if isinstance(t, str):
            # "0 - 单选题" → 0
            type_values.append(int(t.split()[0]))
        else:
            type_values.append(int(t))

    # 构造请求
    req = GenerateRequest(
        subject_bank_name=name,
        subject_bank_remark=remark,
        document_text=text.strip() if text else None,
        requirements=requirements,
        question_types=type_values,
        count_per_type=int(count),
        difficulty=0 if difficulty == "简单" else 1,
    )

    logger.info(f"Gradio 请求: {req.model_dump()}")

    try:
        resp = generate_questions(req, file_bytes=file_bytes, filename=filename)
        return json.dumps(resp.model_dump(), ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception(f"生成失败: {e}")
        return json.dumps(
            {"success": False, "error": str(e)},
            ensure_ascii=False,
            indent=2,
        )


def create_ui() -> gr.Blocks:
    """创建 Gradio 界面"""
    with gr.Blocks(title="试题生成助手", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 📝 试题生成助手

            上传教学文档或输入教学内容，选择题型和数量，AI 自动生成考试试题。
            生成的 JSON 可直接用于实训平台题库导入。
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📋 基本信息")
                name = gr.Textbox(
                    label="题库名称",
                    value="默认题库",
                    placeholder="如：计算机基础第一章",
                )
                remark = gr.Textbox(
                    label="题库描述",
                    placeholder="如：覆盖二进制、冯诺依曼结构等核心概念",
                )

                gr.Markdown("### 📄 教学内容")
                file = gr.File(
                    label="上传文档",
                    file_types=[".pdf", ".docx"],
                )
                text = gr.Textbox(
                    label="或直接输入教学内容",
                    lines=10,
                    placeholder="输入教学内容，如：\n第一章 计算机基础\n1. 二进制转换规则...\n2. 冯诺依曼结构...",
                )

                gr.Markdown("### ⚙️ 生成参数")
                requirements = gr.Textbox(
                    label="具体要求",
                    placeholder="如：侧重基础概念，不要考太偏的知识点",
                )

                with gr.Row():
                    types = gr.CheckboxGroup(
                        label="题型",
                        choices=[
                            ("0 - 单选题", 0),
                            ("1 - 多选题", 1),
                            ("2 - 判断题", 2),
                            ("3 - 简答题", 3),
                        ],
                        value=[0, 1, 2, 3],
                    )
                    difficulty = gr.Radio(
                        label="难度",
                        choices=["简单", "困难"],
                        value="简单",
                    )
                    count = gr.Slider(
                        label="每种题型数量",
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                    )

                btn = gr.Button("🚀 生成试题", variant="primary", size="lg")

            with gr.Column(scale=1):
                gr.Markdown("### 📦 生成结果")
                output = gr.Code(
                    label="JSON 输出",
                    language="json",
                    lines=30,
                )

        btn.click(
            fn=_handle_generate,
            inputs=[name, remark, file, text, requirements, types, count, difficulty],
            outputs=output,
        )

        gr.Markdown(
            """
            ---
            ### 使用说明

            1. **填写题库信息**：题库名称和描述
            2. **提供教学内容**：上传 PDF/Word 文档，或直接在文本框输入
            3. **设置参数**：选择题型、数量、难度
            4. **点击生成**：等待 AI 生成试题
            5. **复制 JSON**：将输出结果交给同事导入题库
            """
        )

    return demo
