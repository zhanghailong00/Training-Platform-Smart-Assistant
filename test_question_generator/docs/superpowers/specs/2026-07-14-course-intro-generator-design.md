# 课程简介生成助手 — 设计文档

> 日期：2026-07-13
> 状态：待审批
> 作者：zhanghailong

---

## 一、功能概述

### 1.1 背景

实训平台已有课程数据（课程名称、章节结构、实验名称），但缺少一段可直接展示的课程简介。目前 `lesson.remark` 字段虽然有简介，但内容需要人工编写。本功能利用大模型，根据课程的章节结构和实验名称，自动生成一段 200-300 字的课程简介。

### 1.2 核心流程

```
前端提供课程结构化 JSON
  → 后端提取课程名 + 章节 + 实验名
  → 构建 Prompt → 调 DeepSeek
  → 返回纯文本课程简介
```

### 1.3 第一期范围

| 做 | 不做 |
|---|---|
| 根据课程章节结构生成简介 | 根据实验文档内容生成简介（需要下载PDF/Word解析） |
| 纯文本输出 | 富文本/HTML/Markdown |
| 一次 Prompt 直接返回 | 自修复重试、多轮校验 |
| 新增 API 端点 | Gradio 界面（当前用 curl/平台调用测试） |
| 复用试题生成的 llm_client、core、utils | 文档解析、JSON 校验、业务规则校验 |

---

## 二、技术方案

### 2.1 复用现有代码

| 模块 | 是否复用 | 说明 |
|---|---|---|
| `core/settings.py` | ✅ | 配置管理，读 DeepSeek/Qwen API Key |
| `core/logger.py` | ✅ | 统一日志 |
| `core/exceptions.py` | ✅ | 自定义异常 |
| `core/constants.py` | ✅ | 常量 |
| `utils/token_utils.py` | ✅ | token 估算与截断 |
| `components/llm_client.py` | ✅ | DeepSeek + Qwen 双模型调用 + fallback |
| `api/routes.py` | ⚠️ 追加 | 新增 `/api/v1/course-intro` 路由 |

### 2.2 新增文件

| 文件 | 说明 |
|---|---|
| `schemas/course_intro.py` | 请求/响应 Pydantic 模型 |
| `prompts/course_intro.yaml` | 课程简介生成 Prompt |
| `services/course_intro_service.py` | 课程简介生成编排 |

### 2.3 不需要

- parser.py — 不需要解析文档
- preprocessor.py — 输入是结构化数据，不需要清洗
- validator.py — 输出是纯文本，不需要 JSON 校验
- business_validator.py — 没有业务规则需要校验
- JSON Mode — 输出纯文本，不需要 JSON Mode

---

## 三、数据模型

### 3.1 请求模型 — `schemas/course_intro.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ChapterInfo(BaseModel):
    """章节信息"""
    name: str = Field(description="章节名称，如'第一章 SDK 配置和测试用例'")
    lessons: List[str] = Field(description="该章节下的实验/课时名称列表")

class CourseIntroRequest(BaseModel):
    """课程简介生成请求"""
    course_name: str = Field(description="课程名称")
    chapters: List[ChapterInfo] = Field(description="章节列表")
```

### 3.2 响应模型

```python
class CourseIntroResponse(BaseModel):
    """课程简介生成响应"""
    success: bool
    intro: Optional[str] = Field(default=None, description="生成的课程简介文本")
    error: Optional[str] = Field(default=None, description="错误信息")
```

### 3.3 前端调用时数据提取规则

前端拿到平台的课程 JSON 后，提取关键字段构造请求：

```
course_name → lesson.name
chapters[].name → content[].name
chapters[].lessons → content[].lessonDetails[].name（含 experiment.name）
```

忽略字段：`lessonChapterId`、`addTime`、`updateTime`、`sort`、`enabled`、`image`、`file`、`remark` 等与生成无关的字段。

---

## 四、Prompt 设计

### 4.1 Prompt 配置 — `prompts/course_intro.yaml`

```yaml
system: |
  你是一位课程设计专家。你的任务是根据课程名称和章节结构，为这门课程撰写一段简洁的课程简介。

  要求：
  1. 简介必须基于提供的课程结构和章节名称，不能编造不存在的内容
  2. 语言流畅、专业、有吸引力
  3. 突出课程的核心内容和学习价值
  4. 控制在 200-300 字之间
  5. 不要输出标题，直接输出正文
  6. 不要输出 Markdown 格式，纯文本即可

user: |
  请根据以下课程信息生成一段 200-300 字的课程简介。

  课程名称：{course_name}

  章节结构：
  {chapter_list}

  请直接输出简介文本，不要输出任何额外内容。
```

### 4.2 Prompt 变量说明

| 变量 | 来源 | 示例 |
|---|---|---|
| `{course_name}` | `request.course_name` | "深度相机视觉开发实战" |
| `{chapter_list}` | 由 `chapters` 格式化生成 | "- 第一章 SDK 配置和测试用例\n  - 01-奥比中光SDK配置和测试用例\n  - 01-奥比中光SDK配置和测试用例实验\n- 第二章 基于OpenCV 的图像基础\n  - 02-彩色图像读取\n  - 02-彩色图像读取实验" |

---

## 五、API 设计

### 5.1 新增 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/course-intro` | 生成课程简介 |

### 5.2 请求示例

```json
POST /api/v1/course-intro
Content-Type: application/json

{
  "course_name": "深度相机视觉开发实战",
  "chapters": [
    {
      "name": "第一章 SDK 配置和测试用例",
      "lessons": [
        "01-奥比中光SDK配置和测试用例",
        "01-奥比中光SDK配置和测试用例实验"
      ]
    },
    {
      "name": "第二章 基于OpenCV 的图像基础",
      "lessons": [
        "02-彩色图像读取",
        "02-彩色图像读取实验"
      ]
    }
  ]
}
```

### 5.3 响应示例

```json
{
  "success": true,
  "intro": "本课程系统学习深度相机视觉开发的核心技术。课程从奥比中光 SDK 的配置与测试入手，帮助学员快速搭建开发环境。随后深入 OpenCV 图像处理基础，涵盖彩色图像读取、图像变换等核心操作。通过理论与实践相结合的方式，使学员掌握深度相机视觉开发的完整技能链。",
  "error": null
}
```

---

## 六、错误处理

| 场景 | 处理方式 |
|---|---|
| `course_name` 为空 | 返回 400 "课程名称不能为空" |
| `chapters` 为空 | 返回 400 "章节列表不能为空" |
| LLM 调用失败 | 复用 `llm_client.py` 的 fallback 机制，DeepSeek 失败自动切 Qwen |
| 所有模型均不可用 | 返回 500 "LLM 服务不可用" |

---

## 七、实现计划

### 7.1 涉及文件清单

| 文件 | 操作 |
|---|---|
| `schemas/course_intro.py` | **新增**：请求/响应模型 |
| `prompts/course_intro.yaml` | **新增**：Prompt 模板 |
| `services/course_intro_service.py` | **新增**：业务编排 |
| `api/routes.py` | **修改**：追加 `/api/v1/course-intro` 路由 |

### 7.2 步骤

#### 第 1 步：新增 `schemas/course_intro.py`

- 定义 `ChapterInfo`（章节信息）
- 定义 `CourseIntroRequest`（请求）
- 定义 `CourseIntroResponse`（响应）

#### 第 2 步：新增 `prompts/course_intro.yaml`

- system prompt：课程设计专家身份 + 要求
- user prompt：课程名称 + 章节列表变量

#### 第 3 步：新增 `services/course_intro_service.py`

- `generate_course_intro(request) -> CourseIntroResponse`
- 将 chapters 格式化为带缩进的文本列表
- 调用 `prompt_builder.load_template()` 加载 YAML
- 调用 `llm_client.generate()` 调 DeepSeek
- 返回结果

#### 第 4 步：修改 `api/routes.py`

- 导入 `CourseIntroRequest`、`CourseIntroResponse`、`generate_course_intro`
- 新增 `POST /api/v1/course-intro` 路由
- 异常处理

### 7.3 验证方式

```bash
curl -X POST http://localhost:7860/api/v1/course-intro \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "深度相机视觉开发实战",
    "chapters": [
      {"name": "第一章 SDK 配置和测试用例", "lessons": ["01-奥比中光SDK配置和测试用例", "01-奥比中光SDK配置和测试用例实验"]},
      {"name": "第二章 基于OpenCV 的图像基础", "lessons": ["02-彩色图像读取", "02-彩色图像读取实验"]}
    ]
  }'
```

预期返回 `success: true` + 200-300 字的课程简介。

---

## 八、与前端的对接约定

1. 前端从平台课程详情 API 拿到原始 JSON
2. 前端提取 `lesson.name` → `course_name`，提取 `content[]` 中的 `name` 和 `lessonDetails[].name` → `chapters`
3. 调用 `POST /api/v1/course-intro` 传入提取后的数据
4. 拿到返回的 `intro` 文本，显示在课程详情页
