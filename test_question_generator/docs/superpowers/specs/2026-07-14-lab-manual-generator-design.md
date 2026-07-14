# 实验手册生成助手 — 设计文档

> 日期：2026-07-14
> 状态：待审批
> 作者：zhanghailong

---

## 一、功能概述

### 1.1 背景

实训平台需要为课程配套实验指导手册和实验报告模板。目前实验手册由老师手动编写，效率低。本功能利用大模型，根据老师上传的文档或输入的教学内容，自动生成实验手册和实验报告模板，支持在线预览、编辑修改，最终导出为 Word 文件。

### 1.2 核心流程

```
老师上传文档或输入文本
  → AI 生成实验手册（Markdown）
  → 老师在编辑区修改
  → 实时预览效果
  → 确认后下载 Word
```

### 1.3 第一期范围

| 做 | 不做 |
|---|---|
| 实验指导手册生成 | 实验报告模板自动填入学号/姓名 |
| 实验报告模板生成 | 批量生成 |
| Markdown 在线编辑 + 实时预览 | 富文本编辑器（TinyMCE 等） |
| Word 文件下载 | PDF 导出 |
| 上传文档 + 自由文本输入 | 历史版本管理 |
| 老师可自由增删改章节 | 协作编辑 |

---

## 二、技术选型

### 2.1 复用现有代码

| 模块 | 是否复用 | 说明 |
|---|---|---|
| `core/` | ✅ | settings, logger, exceptions, constants 全部复用 |
| `utils/` | ✅ | token_utils, json_utils, file_utils 全部复用 |
| `components/parser.py` | ✅ | PDF/Word 文档解析，直接复用 |
| `components/preprocessor.py` | ✅ | 文本清洗 + 截断，直接复用 |
| `components/llm_client.py` | ✅ | DeepSeek + Qwen 双模型 + fallback，直接复用 |
| `api/routes.py` | ⚠️ 追加 | 新增 `/api/v1/lab-manual` 路由 |

### 2.2 新增文件

| 文件 | 说明 |
|---|---|
| `schemas/lab.py` | 请求/响应 Pydantic 模型 |
| `prompts/lab_manual.yaml` | 实验手册生成 Prompt |
| `services/lab_service.py` | 实验手册生成编排 |
| `components/docx_builder.py` | Markdown → Word 转换 |

### 2.3 新增依赖

```bash
pip install pypandoc
```

需要服务器安装 pandoc：

```bash
apt install pandoc
```

### 2.4 不需要

- `components/validator.py` — 输出是 Markdown，不需要 JSON 校验
- `components/business_validator.py` — 没有业务规则需要校验
- JSON Mode — 输出纯文本/Markdown，不需要 JSON Mode

---

## 三、数据模型

### 3.1 请求模型 — `schemas/lab.py`

```python
from pydantic import BaseModel, Field
from typing import Optional


class LabManualRequest(BaseModel):
    """实验手册生成请求"""
    title: str = Field(description="实验名称")
    document_text: Optional[str] = Field(default=None, description="教学内容文本")
    requirements: str = Field(default="", description="老师的具体要求")
    template_type: str = Field(default="manual", description="manual=实验手册, report=实验报告模板")
```

### 3.2 响应模型

```python
class LabManualResponse(BaseModel):
    """实验手册生成响应"""
    success: bool
    title: Optional[str] = Field(default=None, description="实验名称")
    markdown: Optional[str] = Field(default=None, description="生成的 Markdown 内容")
    download_url: Optional[str] = Field(default=None, description="Word 下载地址")
    error: Optional[str] = Field(default=None, description="错误信息")
```

---

## 四、Prompt 设计

### 4.1 实验手册 Prompt — `prompts/lab_manual.yaml`

```yaml
system: |
  你是一位实验教学专家。你的任务是根据教学内容，生成一份结构清晰、内容完整的实验指导手册。

  请严格遵循以下要求：
  1. 内容必须基于提供的教学内容，不能编造不存在的内容
  2. 实验步骤要清晰、可操作，分步骤编号
  3. 实验结果要给出预期结果或示例
  4. 使用 Markdown 格式输出
  5. 不要输出额外的解释文字，直接输出 Markdown 内容

manual_template: |
  请根据以下信息生成一份实验指导手册。

  实验名称：{title}

  教学内容：
  {document_text}

  额外要求：
  {requirements}

  请输出 Markdown 格式，包含以下章节（如果教学内容中有相关内容则填充，没有则合理编写）：

  ## 一、实验目的
  （阐述本次实验的学习目标）

  ## 二、实验原理
  （介绍实验涉及的核心理论知识）

  ## 三、实验环境
  （列出所需的硬件、软件、工具等）

  ## 四、实验步骤
  （分步骤详细描述实验操作过程）

  ## 五、实验结果
  （描述预期的实验结果或输出示例）

  ## 六、思考题
  （提出 2-3 个与实验相关的思考题）

report_template: |
  请根据以下信息生成一份实验报告模板。

  实验名称：{title}

  教学内容：
  {document_text}

  额外要求：
  {requirements}

  请输出 Markdown 格式，包含以下章节：

  ## 一、实验目的
  （学生填写本次实验的学习目标）

  ## 二、实验原理
  （学生填写实验涉及的核心理论知识）

  ## 三、实验环境
  （列出实验所需的硬件、软件配置）

  ## 四、实验过程与记录
  （学生填写实验操作步骤和过程中观察到的现象）

  ## 五、实验结果与分析
  （学生填写实验结果，并对结果进行分析）

  ## 六、实验总结
  （学生填写实验的心得体会、遇到的问题及解决方法）
```

---

## 五、Markdown → Word 转换

### 5.1 方案

使用 `pandoc` 将 Markdown 转换为 Word：

```bash
pandoc input.md -o output.docx
```

### 5.2 Python 实现 — `components/docx_builder.py`

```python
import pypandoc
import tempfile
import os
from pathlib import Path


def markdown_to_docx(markdown_text: str, output_path: str) -> str:
    """
    将 Markdown 文本转换为 Word 文档。

    Args:
        markdown_text: Markdown 格式的文本
        output_path: 输出文件路径

    Returns:
        Word 文件的路径
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 用 pypandoc 转换
    pypandoc.convert_text(
        markdown_text,
        'docx',
        format='md',
        outputfile=output_path,
    )

    return output_path
```

### 5.3 兜底方案

如果服务器没有 pandoc，使用 python-docx 手动构建 Word 文档：

```python
from docx import Document

def markdown_to_docx_fallback(markdown_text: str, output_path: str) -> str:
    """
    不使用 pandoc，用 python-docx 手动构建 Word 文档。
    """
    doc = Document()
    # 添加标题
    doc.add_heading('实验指导手册', level=0)
    # 逐行解析 Markdown，分段处理
    for line in markdown_text.split('\n'):
        if line.startswith('## '):
            doc.add_heading(line[3:], level=2)
        elif line.startswith('# '):
            doc.add_heading(line[2:], level=1)
        elif line.strip():
            doc.add_paragraph(line.strip())
    doc.save(output_path)
    return output_path
```

---

## 六、API 设计

### 6.1 新增 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/lab-manual` | 生成实验手册/报告模板 |
| GET | `/api/v1/lab-manual/{task_id}/download` | 下载 Word 文件 |

### 6.2 请求示例

```json
POST /api/v1/lab-manual
Content-Type: application/json

{
  "title": "Python 循环结构实验",
  "document_text": "Python 循环有 for 和 while 两种。for 循环用于遍历序列，while 循环在条件为真时持续执行。",
  "requirements": "侧重基础语法，适合大一学生",
  "template_type": "manual"
}
```

### 6.3 响应示例

```json
{
  "success": true,
  "title": "Python 循环结构实验",
  "markdown": "# Python 循环结构实验\n\n## 一、实验目的\n掌握...\n\n## 二、实验原理\n...",
  "download_url": "/api/v1/lab-manual/a1b2c3/download",
  "error": null
}
```

---

## 七、Gradio UI 设计

在现有 Gradio 页面中新增一个 Tab，和试题生成共存：

```python
with gr.Blocks(title="实训平台 AI 助手") as demo:
    with gr.Tab("试题生成"):
        # 现有试题生成界面
        ...

    with gr.Tab("实验手册"):
        # 实验手册生成界面
        ...
```

### 实验手册 Tab 布局

```
┌──────────────────────────────────────────────────┐
│  📝 实验手册生成                                  │
├──────────────────────────────────────────────────┤
│  [manual] 实验指导手册  [report] 实验报告模板      │
│                                                  │
│  实验名称：[Python 循环结构实验]                   │
│  上传文档：[选择文件]    或   输入内容：[          │
│                                        ]          │
│  具体要求：[侧重基础语法，适合大一学生]             │
│                                                  │
│  [🚀 生成]                                        │
│                                                  │
│  ┌─────── 编辑区 (Markdown) ────┬─ 预览区 ──────┐│
│  │                              │              ││
│  │ # 实验名称                   │ 实验名称      ││
│  │                              │ ==========  ││
│  │ ## 一、实验目的              │              ││
│  │ 掌握...                      │ 一、实验目的  ││
│  │                              │ -------------││
│  │                              │              ││
│  │                              │              ││
│  └──────────────────────────────┴──────────────┘│
│                                                  │
│  [重新生成]  [📥 下载 Word]                       │
└──────────────────────────────────────────────────┘
```

---

## 八、错误处理

| 场景 | 处理方式 |
|---|---|
| `title` 为空 | 返回 400 "实验名称不能为空" |
| 文档解析失败 | 复用 `DocumentParseError`，返回 400 |
| LLM 调用失败 | 复用 fallback 机制，自动切到 Qwen |
| pandoc 未安装 | 自动降级为 python-docx 手动构建 |
| Word 生成失败 | 返回 500 "Word 文件生成失败" |

---

## 九、实现计划

### 涉及文件

| 文件 | 操作 |
|---|---|
| `schemas/lab.py` | **新增**：请求/响应模型 |
| `prompts/lab_manual.yaml` | **新增**：实验手册 + 报告模板 Prompt |
| `components/docx_builder.py` | **新增**：Markdown → Word 转换 |
| `services/lab_service.py` | **新增**：实验手册生成编排 |
| `api/routes.py` | **修改**：追加 `/api/v1/lab-manual` 路由 |
| `ui/gradio_app.py` | **修改**：新增实验手册 Tab |
| `app/main.py` | **修改**：传参给 Gradio（如果需要） |

### 步骤

| 步 | 内容 | 时间 |
|---|---|---|
| 1 | 新增 `schemas/lab.py` | 10 分钟 |
| 2 | 新增 `prompts/lab_manual.yaml` | 15 分钟 |
| 3 | 新增 `components/docx_builder.py` | 20 分钟 |
| 4 | 新增 `services/lab_service.py` | 30 分钟 |
| 5 | 修改 `api/routes.py` 追加路由 | 15 分钟 |
| 6 | 修改 `ui/gradio_app.py` 加 Tab | 20 分钟 |
| 7 | 联调验证 | 30 分钟 |
| **总计** | | **约 2 小时** |