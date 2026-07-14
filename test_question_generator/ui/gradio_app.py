"""Gradio UI：实训平台 AI 助手前端界面"""

import json
import os
from pathlib import Path
import gradio as gr
from services.exam_service import generate_questions
from services.lab_service import generate_lab_manual
from schemas.request import GenerateRequest
from schemas.lab import LabManualRequest
from core.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 试题生成
# ============================================================

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
    """Gradio 回调：试题生成"""
    file_bytes = None
    filename = None
    if file is not None:
        file_path = str(file)
        if hasattr(file, "name"):
            filename = file.name.split("/")[-1].split("\\")[-1]
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        logger.info(f"读取文件: {filename}, {len(file_bytes)} bytes")

    type_values = []
    for t in types:
        if isinstance(t, str):
            type_values.append(int(t.split()[0]))
        else:
            type_values.append(int(t))

    req = GenerateRequest(
        subject_bank_name=name,
        subject_bank_remark=remark,
        document_text=text.strip() if text else None,
        requirements=requirements,
        question_types=type_values,
        count_per_type=int(count),
        difficulty=0 if difficulty == "简单" else 1,
    )

    try:
        resp = generate_questions(req, file_bytes=file_bytes, filename=filename)
        return json.dumps(resp.model_dump(), ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception(f"生成失败: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)


# ============================================================
# 实验手册生成
# ============================================================

def _handle_lab_manual(
    title: str,
    file,
    text: str,
    requirements: str,
    template_type: str,
) -> tuple:
    """Gradio 回调：实验手册生成，只返回 Markdown，不生成 Word"""
    file_bytes = None
    document_text = text.strip() if text else None

    if file is not None:
        file_path = str(file)
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        if not document_text:
            from components.parser import parse
            filename = file.name.split("/")[-1].split("\\")[-1] if hasattr(file, "name") else "upload.pdf"
            try:
                document_text = parse(file_bytes, filename)
            except Exception as e:
                return "", f"文档解析失败: {e}"

    req = LabManualRequest(
        title=title,
        document_text=document_text,
        requirements=requirements,
        template_type=template_type,
    )

    try:
        resp = generate_lab_manual(req)
        if resp.success:
            return resp.markdown or "", "✅ 生成成功，可在编辑区修改后点击「下载 Word」"
        else:
            return "", f"❌ 生成失败: {resp.error}"
    except Exception as e:
        logger.exception(f"实验手册生成失败: {e}")
        return "", f"❌ 生成失败: {e}"


def _handle_lab_download(markdown_text: str, title: str) -> tuple:
    """Gradio 回调：从当前 Markdown 编辑区内容生成 Word 文件"""
    if not markdown_text or not markdown_text.strip():
        return None, "Markdown 内容为空，请先生成内容"

    try:
        from components.docx_builder import markdown_to_docx
        import uuid
        downloads_dir = Path(__file__).resolve().parent.parent / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.docx"
        output_path = str(downloads_dir / filename)
        markdown_to_docx(markdown_text, output_path)
        return output_path, f"✅ Word 文件已生成"
    except Exception as e:
        logger.exception(f"Word 生成失败: {e}")
        return None, f"❌ Word 生成失败: {e}"


# ============================================================
# UI 构建
# ============================================================

def create_ui() -> gr.Blocks:
    """创建 Gradio 界面（多 Tab）"""
    with gr.Blocks(title="实训平台 AI 助手", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🧠 实训平台 AI 助手")

        with gr.Tabs():
            # ========== Tab 1：试题生成 ==========
            with gr.Tab("📝 试题生成"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📋 基本信息")
                        name = gr.Textbox(label="题库名称", value="默认题库")
                        remark = gr.Textbox(label="题库描述")

                        gr.Markdown("### 📄 教学内容")
                        file = gr.File(label="上传文档", file_types=[".pdf", ".docx"])
                        text = gr.Textbox(label="或直接输入教学内容", lines=8)

                        gr.Markdown("### ⚙️ 生成参数")
                        requirements = gr.Textbox(label="具体要求")

                        with gr.Row():
                            types = gr.CheckboxGroup(
                                label="题型",
                                choices=[("0 - 单选题", 0), ("1 - 多选题", 1), ("2 - 判断题", 2), ("3 - 简答题", 3)],
                                value=[0, 1, 2, 3],
                            )
                            difficulty = gr.Radio(label="难度", choices=["简单", "困难"], value="简单")
                            count = gr.Slider(label="每种题型数量", minimum=1, maximum=20, value=5, step=1)

                        btn = gr.Button("🚀 生成试题", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        gr.Markdown("### 📦 生成结果")
                        output = gr.Code(label="JSON 输出", language="json", lines=30)

                btn.click(
                    fn=_handle_generate,
                    inputs=[name, remark, file, text, requirements, types, count, difficulty],
                    outputs=output,
                )

            # ========== Tab 2：实验手册 ==========
            with gr.Tab("📄 实验手册"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📋 基本信息")
                        lab_title = gr.Textbox(
                            label="实验名称",
                            placeholder="如：Python 循环结构实验",
                        )
                        template_type = gr.Radio(
                            label="生成类型",
                            choices=[("实验指导手册", "manual"), ("实验报告模板", "report")],
                            value="manual",
                        )

                        gr.Markdown("### 📄 教学内容")
                        lab_file = gr.File(label="上传文档", file_types=[".pdf", ".docx"])
                        lab_text = gr.Textbox(
                            label="或直接输入教学内容",
                            lines=8,
                            placeholder="输入教学内容，如：\nPython 循环有 for 和 while 两种...",
                        )

                        lab_requirements = gr.Textbox(
                            label="具体要求",
                            placeholder="如：侧重基础语法，适合大一学生",
                        )

                        lab_btn = gr.Button("🚀 生成 Markdown", variant="primary", size="lg")
                        lab_status = gr.Markdown("")

                        lab_download_btn = gr.Button("📥 下载 Word", variant="secondary", size="lg")
                        lab_download_file = gr.File(label="下载文件", visible=True)

                        lab_regenerate = gr.Button("🔄 重新生成", variant="secondary")

                    with gr.Column(scale=1):
                        gr.Markdown("### ✏️ 编辑 Markdown")
                        lab_md_editor = gr.Textbox(
                            label="Markdown 内容（可编辑）",
                            lines=25,
                            show_label=False,
                        )
                        gr.Markdown("### 👁️ 预览")
                        lab_preview = gr.Markdown("")

                # 生成按钮点击（只生成 Markdown，不生成 Word）
                lab_btn.click(
                    fn=_handle_lab_manual,
                    inputs=[lab_title, lab_file, lab_text, lab_requirements, template_type],
                    outputs=[lab_md_editor, lab_status],
                ).then(
                    fn=lambda md: md,
                    inputs=[lab_md_editor],
                    outputs=[lab_preview],
                )

                # 下载 Word 按钮（从当前 Markdown 编辑区内容生成）
                lab_download_btn.click(
                    fn=_handle_lab_download,
                    inputs=[lab_md_editor, lab_title],
                    outputs=[lab_download_file, lab_status],
                )

                # 重新生成
                lab_regenerate.click(
                    fn=_handle_lab_manual,
                    inputs=[lab_title, lab_file, lab_text, lab_requirements, template_type],
                    outputs=[lab_md_editor, lab_status],
                ).then(
                    fn=lambda md: md,
                    inputs=[lab_md_editor],
                    outputs=[lab_preview],
                )

                # 编辑区变化时实时更新预览
                lab_md_editor.change(
                    fn=lambda md: md,
                    inputs=[lab_md_editor],
                    outputs=[lab_preview],
                )

    return demo
