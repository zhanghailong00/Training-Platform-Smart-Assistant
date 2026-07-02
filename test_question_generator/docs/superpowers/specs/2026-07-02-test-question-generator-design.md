# 试题生成助手 — 第一版设计文档

> 日期：2026-07-02
> 状态：待审批
> 作者：zhanghailong

---

## 一、项目概览

### 1.1 背景

实训平台已有课程和学生考试功能，老师需要在平台上设计考试内容。本助手作为独立服务嵌入平台，老师上传文档或输入文字需求，大模型自动生成试题（按题型分类），生成结果以 JSON 格式交给同事入库到平台题库。

### 1.2 核心流程

```
老师上传文档(Word/PDF) + 文字描述需求 + 指定题型/数量
         → DeepSeek 生成试题
         → 返回结构化 JSON（单选/多选/判断/主观）
         → 同事入库
```

### 1.3 第一期范围

| 做 | 不做 |
|---|---|
| 文档上传（PDF + Word） | 题库管理 |
| 自由文本输入 | 组卷功能 |
| 四种题型生成：单选/多选/判断/主观 | 历史记录 / 用户登录 |
| 简易 Web 上传页面 | 批量生成 / 任务队列 |
| API 端点（供平台调用） | 试题编辑 / 审核流程 |
| JSON 结构化输出 | 导出 Word / Excel |
| DeepSeek API 接入 | 其他 AI 功能 |

---

## 二、技术选型

### 2.1 技术栈

| 层 | 选型 | 版本 | 理由 |
|---|---|---|---|
| 语言 | Python | 3.11+ | LLM 生态最成熟 |
| Web 框架 | FastAPI | latest | 异步支持好，自带 Swagger，适合 API 服务 |
| 包/环境管理 | conda | — | 团队统一管理 |
| 前端 | Gradio | latest | 纯 Python，内置文件上传/下拉/JSON 展示组件，可挂载到 FastAPI |
| Word 解析 | python-docx | latest | 读取 .docx 文本 |
| PDF 解析 | PyMuPDF (fitz) | latest | 对中文 PDF 支持优于 PyPDF2 |
| LLM 服务 | DeepSeek API | — | 用户指定，性价比高 |
| LLM SDK | openai Python SDK | latest | DeepSeek 完全兼容 OpenAI 接口格式 |
| Prompt 管理 | YAML 配置文件 | — | 可热加载，无需数据库 |
| 数据校验 | Pydantic v2 | — | FastAPI 内置，模型校验一体 |
| 部署 | uvicorn 单进程 | — | 第一期轻量 |
| HTTP 客户端 | httpx | latest | FastAPI 推荐，备用于非 openai SDK 场景 |

### 2.2 环境配置

```yaml
# environment.yml
name: ai-assistant
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - pip
  - pip:
    - fastapi
    - uvicorn
    - gradio              # 前端 UI
    - python-multipart    # 文件上传
    - python-docx
    - PyMuPDF
    - openai              # DeepSeek 兼容
    - pydantic
    - pyyaml
    - httpx
```

### 2.3 关键决策记录

| 决策 | 选择 | 原因 |
|---|---|---|
| 同步 vs 异步 | 同步调用 | 第一期轻量，文档不大，十几秒可接受 |
| 数据库 vs 配置文件 | 配置文件 | 无状态服务，Prompt 模板存 YAML，数据不需要持久化 |
| 项目结构 | 单功能单文件夹 | 先聚焦试题生成，不预设未来扩展 |
| API 格式 | OpenAI 兼容 | DeepSeek 完全兼容，代码写一遍，后续切模型只需换 base_url |
| PDF 库 | PyMuPDF | 中文支持好，但 AGPL 许可，校内使用无影响 |

---

## 三、项目结构

### 3.1 文件树

```
test_question_generator/              # 一个功能一个文件夹
│
├── app/                              # 应用主体
│   ├── __init__.py
│   └── main.py                       # 🔧 FastAPI 入口 + 挂载 Gradio + 注册路由
│
├── api/                              # API 路由层（对外接口）
│   ├── __init__.py
│   └── routes.py                     # 🔧 POST /api/v1/generate, GET /api/v1/health
│
├── services/                         # 业务服务层（编排逻辑）
│   ├── __init__.py
│   └── exam_service.py               # 🔧 试题生成编排：串联 components 完成一次生成
│
├── components/                       # 功能组件层（可复用的构建块）
│   ├── __init__.py
│   ├── parser.py                     # 🔧 文档解析：PDF/Word 字节流 → 纯文本
│   ├── preprocessor.py               # 🔧 文本预处理：清洗空白 + 超长截断 + token 估算
│   ├── prompt_builder.py             # 🔧 Prompt 构建：加载 YAML 模板 + 变量替换 → messages
│   ├── llm_client.py                 # 🔧 LLM 调用：调 DeepSeek API + 重试 + 超时处理
│   └── validator.py                  # 🔧 JSON 校验：从 LLM 响应中提取 JSON + Pydantic 校验
│
├── schemas/                          # 数据模型层（Pydantic，非数据库模型）
│   ├── __init__.py
│   ├── enums.py                      # 🔧 枚举定义：QuestionType, Difficulty
│   ├── request.py                    # 🔧 请求模型：GenerateRequest
│   ├── question.py                   # 🔧 试题模型：Question, ChoiceQuestion, EssayQuestion 等
│   └── response.py                   # 🔧 响应模型：GenerateResponse
│
├── core/                             # 核心基础设施（全局通用）
│   ├── __init__.py
│   ├── settings.py                   # 🔧 配置管理：读环境变量 + .env 文件 → Settings 对象
│   ├── logger.py                     # 🔧 日志：统一日志格式 + 分级输出
│   ├── exceptions.py                 # 🔧 自定义异常：DocumentParseError, LLMTimeoutError 等
│   └── constants.py                  # 🔧 常量：默认值、限制值、Magic Number 集中管理
│
├── prompts/                          # Prompt 模板（独立于代码，方便调优）
│   ├── __init__.py
│   └── exam_generation.yaml          # 🔧 试题生成 Prompt：system + 四种题型的 instruction
│
├── utils/                            # 工具函数（无状态的纯函数）
│   ├── __init__.py
│   ├── token_utils.py                # 🔧 Token 工具：文本 → token 数估算（tiktoken）
│   ├── json_utils.py                 # 🔧 JSON 工具：从字符串中提取 JSON、格式修复
│   └── file_utils.py                 # 🔧 文件工具：读取文件、判断格式、临时文件管理
│
├── ui/                               # 前端界面（Gradio，开发期使用）
│   ├── __init__.py
│   └── gradio_app.py                 # 🔧 Gradio UI：上传 + 参数选择 + JSON 结果展示
│
├── tests/                            # 测试（一对一映射 src 文件）
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_preprocessor.py
│   ├── test_prompt_builder.py
│   ├── test_llm_client.py
│   ├── test_validator.py
│   └── test_exam_service.py
│
├── playground/                       # Prompt 调试沙箱（不参与生产代码）
│   ├── prompt_test.py                # 🔧 单文件快速测试 Prompt 效果
│   ├── examples/                     # 示例输出
│   └── sample_docs/                  # 测试用样本文档
│
├── docs/                             # 文档
│   └── superpowers/
│       └── specs/
│           └── 2026-07-02-test-question-generator-design.md
│
├── environment.yml                   # conda 环境定义
└── README.md                         # 项目说明
```

### 3.2 模块职责表

#### 3.2.1 入口与路由

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `app/` | `main.py` | 🚀 应用入口 | 创建 FastAPI 实例，注册 API 路由，挂载 Gradio UI，启动 uvicorn |

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `api/` | `routes.py` | 🌐 API 端点 | 定义 `/api/v1/generate` 和 `/api/v1/health`，参数校验，调用 exam_service，返回 JSON |

#### 3.2.2 业务服务

| 目录 | 文件 | 角色 | 职责 | 输入 → 输出 |
|---|---|---|---|---|
| `services/` | `exam_service.py` | 🧠 业务编排 | 串联所有 components，控制生成流程；是唯一知道"完整流程"的地方 | `GenerateRequest` → `GenerateResponse` |

#### 3.2.3 功能组件

| 目录 | 文件 | 角色 | 职责 | 输入 → 输出 |
|---|---|---|---|---|
| `components/` | `parser.py` | 📄 文档解析 | 根据文件扩展名分发到 PDF/Word 解析器，统一返回纯文本 | `bytes + filename` → `str` |
| | `preprocessor.py` | 🧹 文本预处理 | 清洗多余空白、合并空行、按 token 上限截断、估算 token 数 | `str + max_tokens` → `str` |
| | `prompt_builder.py` | ✍️ Prompt 构建 | 从 YAML 加载模板，变量替换（题型/数量/难度），拼装 system + user messages | `文本 + 题型 + 参数` → `List[Message]` |
| | `llm_client.py` | 🤖 LLM 调用 | 通过 openai SDK 调 DeepSeek，指数退避重试（最多 2 次），超时控制 | `List[Message]` → `str` |
| | `validator.py` | ✅ JSON 校验 | 用正则从 LLM 响应提取 JSON 块，Pydantic 校验字段完整性，尝试自动修复 | `str + schema` → `List[Question]` |

#### 3.2.4 数据模型

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `schemas/` | `enums.py` | 🏷️ 枚举 | `QuestionType`（单选/多选/判断/主观）、`Difficulty`（易/中/难） |
| | `request.py` | 📥 请求 | `GenerateRequest`：文本内容 + 要求 + 题型 + 数量 + 难度 |
| | `question.py` | 📝 试题 | `Question` 基类 + `ChoiceQuestion` + `TrueFalseQuestion` + `EssayQuestion` |
| | `response.py` | 📤 响应 | `GenerateResponse`：成功标志 + 试题列表 + 错误信息 + token 用量 |

#### 3.2.5 基础设施

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `core/` | `settings.py` | ⚙️ 配置 | 从环境变量 / `.env` 读取 DeepSeek API Key、模型名、超时等，封装为 `Settings` 单例 |
| | `logger.py` | 📋 日志 | 统一日志格式（时间 + 级别 + 模块 + 消息），控制台输出，可选文件输出 |
| | `exceptions.py` | ❌ 异常 | `DocumentParseError`, `LLMTimeoutError`, `LLMAPIError`, `ValidationError` 等自定义异常 |
| | `constants.py` | 📌 常量 | `MAX_DOCUMENT_TOKENS`, `DEFAULT_MODEL`, `MAX_RETRIES`, 默认值集中管理 |

#### 3.2.6 Prompt 模板

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `prompts/` | `exam_generation.yaml` | 📝 模板 | system prompt + 四种题型各自的 instruction 模板（含输出 JSON schema） |

#### 3.2.7 工具函数

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `utils/` | `token_utils.py` | 🔢 Token | 用 tiktoken 估算文本 token 数，判断是否需要截断 |
| | `json_utils.py` | 🔍 JSON | 从 LLM 原始响应中用正则提取 JSON 数组/对象，修复常见格式问题 |
| | `file_utils.py` | 📁 文件 | 判断文件类型、读取为 bytes、生成临时文件路径 |

#### 3.2.8 前端界面

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `ui/` | `gradio_app.py` | 🖥️ UI | 构建 Gradio 界面（文件上传 + 文本输入 + 题型选择 + 数量滑块 + 难度单选 + JSON 展示），绑定 exam_service |

#### 3.2.9 调试沙箱

| 目录 | 文件 | 角色 | 职责 |
|---|---|---|---|
| `playground/` | `prompt_test.py` | 🧪 调试 | 本地快速测试 Prompt 效果，不依赖 Web 服务 |
| | `examples/` | 📦 样本 | 存放历史生成结果的优秀案例，作为 Prompt 调优参考 |
| | `sample_docs/` | 📄 素材 | 测试用的 PDF/Word 样本文件 |

### 3.3 模块调用链

```
┌─────────────────────────────────────────────────┐
│  入口：Gradio UI 或 API 路由                      │
│  gradio_app.py          api/routes.py            │
└─────────┬───────────────────┬───────────────────┘
          │                   │
          └─────────┬─────────┘
                    │ GenerateRequest
                    ▼
          ┌─────────────────────┐
          │  services/          │
          │  exam_service.py    │  ← 唯一的编排者
          └────────┬────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼
components/   components/    components/    components/    components/
parser.py     preprocessor   prompt_        llm_client     validator
              .py            builder.py     .py            .py

解析文档      清洗+截断      拼装Prompt    调DeepSeek     提取+校验
bytes→str    str→str       →messages     →raw text      →List[Question]
                   │
                   │ 各组件共享的依赖：
                   ├── schemas/  (数据模型)
                   ├── core/     (配置/日志/异常/常量)
                   ├── prompts/  (Prompt 模板)
                   └── utils/    (token/json/file 工具)
```

**原则：**
- `exam_service.py` 是唯一知道完整流程的地方，其他组件互相不知道对方存在
- 组件之间不直接调用，通过 `exam_service` 传递数据
- `schemas/`、`core/`、`utils/` 是被动依赖，不包含业务逻辑

---

## 四、数据模型（已对齐同事格式）

> 以下模型完全对齐同事提供的题库 JSON schema。

### 4.1 枚举定义 — `schemas/enums.py`

```python
from enum import IntEnum

class QuestionType(IntEnum):
    SINGLE_CHOICE = 0    # 单选题
    MULTI_CHOICE = 1     # 多选题
    TRUE_FALSE = 2       # 判断题
    ESSAY = 3            # 简答题

class Difficulty(IntEnum):
    EASY = 0             # 简单
    HARD = 1             # 困难
```

### 4.2 请求模型 — `schemas/request.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from .enums import QuestionType, Difficulty

class GenerateRequest(BaseModel):
    subject_bank_name: str = "默认题库"          # 题库名称（老师可填）
    subject_bank_remark: str = ""                # 题库描述（老师可填）
    document_text: Optional[str] = None           # 自由文本 / 文档解析后的文本
    requirements: str = ""                        # 老师的具体要求
    question_types: List[QuestionType] = [0, 1, 2, 3]  # 需要生成的题型
    count_per_type: int = Field(default=5, ge=1, le=20)
    difficulty: Difficulty = Difficulty.EASY
```

### 4.3 试题模型 — `schemas/question.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from .enums import QuestionType, Difficulty

class Option(BaseModel):
    """选项（同事格式）"""
    content: str                    # 选项文本（不含 A/B/C/D 前缀，如 "二进制转换规则"）
    isRight: bool                   # 是否为正确答案
    analysis: Optional[str] = None  # 选项解析（可为 null）

class Question(BaseModel):
    """统一试题模型（同事格式）"""
    type: QuestionType              # 0=单选, 1=多选, 2=判断, 3=简答
    typeName: str                   # "单选题" / "多选题" / "判断题" / "简答题"
    level: Difficulty               # 0=简单, 1=困难
    levelName: str                  # "简单" / "困难"
    content: str                    # 题干内容
    analysis: str                   # 题目解析
    subAnswer: Optional[str] = None # 简答题答案（仅 type=3 时填写，其余为 null）
    options: List[Option]           # 选项列表
```

### 4.4 响应模型 — `schemas/response.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from .question import Question

class SubjectBank(BaseModel):
    """题库（同事格式）"""
    name: str                       # 题库名称
    remark: str                     # 题库描述
    questions: List[Question] = []  # 试题列表

class GenerateResponse(BaseModel):
    success: bool
    subjectBanks: List[SubjectBank] = []   # 题库列表（通常只有一个）
    error: Optional[str] = None
    usage: Optional[dict] = None           # token 用量统计
```

### 4.5 题型对应的 options 规则

| type | typeName | options 结构 |
|---|---|---|
| 0 | 单选题 | 4个选项，恰好 1 个 `isRight: true` |
| 1 | 多选题 | 4个选项，至少 2 个 `isRight: true` |
| 2 | 判断题 | 2个选项（"正确"/"错误"），1 个 `isRight: true` |
| 3 | 简答题 | `options: []`（空数组），`subAnswer` 填写答案文本 |

### 4.6 完整输出示例

```json
{
  "subjectBanks": [
    {
      "name": "计算机基础第一章",
      "remark": "覆盖二进制、冯诺依曼结构等核心概念",
      "questions": [
        {
          "type": 0,
          "typeName": "单选题",
          "level": 0,
          "levelName": "简单",
          "content": "二进制数 1010 转换为十进制是多少？",
          "analysis": "二进制转十进制：1×2³ + 0×2² + 1×2¹ + 0×2⁰ = 8 + 0 + 2 + 0 = 10",
          "subAnswer": null,
          "options": [
            { "content": "8", "isRight": false, "analysis": "计算错误，遗漏了 2¹ 位" },
            { "content": "10", "isRight": true, "analysis": null },
            { "content": "12", "isRight": false, "analysis": "计算错误，将 2³ 算成了 8" },
            { "content": "14", "isRight": false, "analysis": "计算错误，多加了 2² 位" }
          ]
        },
        {
          "type": 2,
          "typeName": "判断题",
          "level": 0,
          "levelName": "简单",
          "content": "冯·诺依曼结构计算机采用存储程序的思想。",
          "analysis": "冯·诺依曼结构的核心思想就是将程序和数据以二进制形式预先存入存储器。",
          "subAnswer": null,
          "options": [
            { "content": "正确", "isRight": true, "analysis": null },
            { "content": "错误", "isRight": false, "analysis": "存储程序是冯·诺依曼结构的核心特征" }
          ]
        },
        {
          "type": 3,
          "typeName": "简答题",
          "level": 1,
          "levelName": "困难",
          "content": "请简述冯·诺依曼计算机的五大组成部分及其功能。",
          "analysis": "五大部件：运算器、控制器、存储器、输入设备、输出设备，各司其职。",
          "subAnswer": "1. 运算器：完成算术和逻辑运算\n2. 控制器：控制指令执行顺序\n3. 存储器：存储程序和数据\n4. 输入设备：向计算机输入数据\n5. 输出设备：将计算结果输出",
          "options": []
        }
      ]
    }
  ]
}
```

---

## 五、Prompt 设计

### 5.1 Prompt 配置 — `prompts/exam_generation.yaml`

```yaml
system: |
  你是一位资深的教育考试命题专家。你的任务是根据提供的教学内容，
  设计高质量的考试试题。请严格遵循以下原则：

  1. 试题必须基于提供的教学内容，不能超纲
  2. 题干表述清晰、准确、无歧义
  3. 每个选项必须附带解析（analysis 字段），说明该选项为什么对/错
  4. 每道题必须附带题目解析（analysis 字段）
  5. 输出必须为严格的 JSON 格式，符合下方指定的 schema

single_choice:
  instruction: |
    请生成 {count} 道单选题（type=0），难度为 {levelName}（level={level}）。

    要求：
    - 每道题 4 个选项，恰好 1 个 isRight 为 true
    - 错误选项的 analysis 要说明错在哪里（不能为 null）
    - 正确选项的 analysis 可以为 null

    输出格式：
    {{
      "type": 0,
      "typeName": "单选题",
      "level": {level},
      "levelName": "{levelName}",
      "content": "题干内容",
      "analysis": "题目解析",
      "subAnswer": null,
      "options": [
        {{ "content": "选项A", "isRight": false, "analysis": "错误原因说明" }},
        {{ "content": "选项B", "isRight": true, "analysis": null }},
        {{ "content": "选项C", "isRight": false, "analysis": "错误原因说明" }},
        {{ "content": "选项D", "isRight": false, "analysis": "错误原因说明" }}
      ]
    }}

multi_choice:
  instruction: |
    请生成 {count} 道多选题（type=1），难度为 {levelName}（level={level}）。

    要求：
    - 每道题 4 个选项，至少 2 个 isRight 为 true
    - 所有错误选项的 analysis 必须说明错在哪里

    输出格式：同单选题，type=1，typeName="多选题"。

true_false:
  instruction: |
    请生成 {count} 道判断题（type=2），难度为 {levelName}（level={level}）。

    要求：
    - 2 个选项："正确" 和 "错误"
    - 错误选项的 analysis 必须说明原因

    输出格式：
    {{
      "type": 2,
      "typeName": "判断题",
      "level": {level},
      "levelName": "{levelName}",
      "content": "判断内容",
      "analysis": "题目解析",
      "subAnswer": null,
      "options": [
        {{ "content": "正确", "isRight": true, "analysis": null }},
        {{ "content": "错误", "isRight": false, "analysis": "说明为什么是错的" }}
      ]
    }}

essay:
  instruction: |
    请生成 {count} 道简答题（type=3），难度为 {levelName}（level={level}）。

    要求：
    - options 为空数组 []
    - subAnswer 填写参考答案，分点列出

    输出格式：
    {{
      "type": 3,
      "typeName": "简答题",
      "level": {level},
      "levelName": "{levelName}",
      "content": "问题内容",
      "analysis": "答题要点解析",
      "subAnswer": "1. 要点一\\n2. 要点二\\n3. 要点三",
      "options": []
    }}
```

### 5.2 LLM 调用参数 — `core/settings.py` 中配置

```python
# 推荐初始值，后续可调优
LLM_CONFIG = {
    "model": "deepseek-chat",
    "temperature": 0.7,              # 试题需要一定创造性
    "max_tokens": 4096,
    "top_p": 0.95,
}
```

---

## 六、接口设计

### 6.1 Gradio Web UI（老师使用）

Gradio 挂载到 FastAPI 根路径 `/`，直接浏览器打开即可使用。

界面组件：
- `gr.Textbox` — 题库名称（如"计算机基础第一章"）
- `gr.Textbox` — 题库描述（如"覆盖二进制、冯诺依曼结构等核心概念"）
- `gr.File` — 上传 PDF / Word 文档
- `gr.Textbox` — 自由输入教学内容（与文件二选一或互补）
- `gr.Textbox` — 具体要求描述
- `gr.CheckboxGroup` — 选择题型（单选/多选/判断/简答）
- `gr.Slider` — 每种题型数量（1-20）
- `gr.Radio` — 难度（简单/困难）
- `gr.JSON` — 展示生成的试题 JSON（subjectBanks 格式）

主入口 `main.py` 中：

```python
import gradio as gr
from fastapi import FastAPI
from services.exam_service import generate_questions

app = FastAPI()
# ... 注册 API 路由 ...

# 构建 Gradio 界面
ui = gr.Interface(
    fn=generate_questions,        # 调用生成逻辑
    inputs=[file, text, requirements, types, count, difficulty],
    outputs=gr.JSON(label="生成的试题"),
    title="试题生成助手",
    description="上传文档或输入教学内容，选择题型和数量，AI 自动生成试题",
)

gr.mount_gradio_app(app, ui, path="/")
```

### 6.2 平台集成 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/generate` | JSON 请求，返回 JSON（见 4.3） |
| GET | `/api/v1/health` | 健康检查 |

```
POST /api/v1/generate
Content-Type: application/json

{
  "subject_bank_name": "计算机基础第一章",
  "subject_bank_remark": "覆盖二进制、冯诺依曼结构等核心概念",
  "document_text": "第一章：计算机基础...",
  "requirements": "侧重基础概念，不要考太偏的知识点",
  "question_types": [0, 2],
  "count_per_type": 10,
  "difficulty": 0
}

→

{
  "success": true,
  "subjectBanks": [
    {
      "name": "计算机基础第一章",
      "remark": "覆盖二进制、冯诺依曼结构等核心概念",
      "questions": [
        {
          "type": 0,
          "typeName": "单选题",
          "level": 0,
          "levelName": "简单",
          "content": "二进制数 1010 转换为十进制是多少？",
          "analysis": "二进制转十进制...",
          "subAnswer": null,
          "options": [...]
        }
      ]
    }
  ],
  "usage": {"prompt_tokens": 1200, "completion_tokens": 3500, "total_tokens": 4700}
}
```

### 6.3 架构示意

```
浏览器 :7860  ──→  Gradio UI (/)      ← 老师使用
平台后端      ──→  FastAPI (/api/v1/*) ← 程序调用
                      │
                      └── 共享同一个 exam_service.py 逻辑
```

---

## 七、错误处理

| 场景 | 处理方式 |
|---|---|
| PDF/Word 解析失败 | `DocumentParseError` | 返回 400 + "文档无法解析，请检查文件是否损坏" |
| 文本过长超过 token 限制 | 自动截断 + 日志警告 | 告知用户截断位置 |
| DeepSeek API 超时 | `LLMTimeoutError` | 重试 2 次（指数退避），仍失败返回 502 |
| DeepSeek API 返回非 JSON | `JSONExtractionError` | JSON 提取器尝试正则匹配，失败则返回原始文本 + 错误提示 |
| Pydantic 校验不通过 | `ValidationError` | 尝试自动修复（补字段、修类型），失败则返回 500 + 详情 |
| DeepSeek 余额不足 / Key 无效 | `LLMAPIError` | 返回 500 + "LLM 服务不可用，请联系管理员" |

> 所有自定义异常定义在 `core/exceptions.py`，便于统一捕获和处理。

---

## 八、待确认事项

| 序号 | 事项 | 状态 | 负责人 |
|---|---|---|---|
| 1 | 试题 JSON 字段已对齐同事格式 → `schemas/question.py` | ✅ 已确认 | zhanghailong |
| 2 | DeepSeek API Key 申请 → 填入 `core/settings.py` 或 `.env` | ⚠️ 待确认 | — |
| 3 | 实训平台技术栈确认（前端框架、调用方式） | ⚠️ 待确认 | — |
| 4 | PyMuPDF AGPL 许可证校内合规 | ⚠️ 待确认 | — |
| 5 | 部署环境（Windows Server？端口？nginx？） | ⚠️ 待确认 | — |
| 6 | 是否需要 DeepSeek reasoner 模式（深度推理，更贵但质量更高） | 💡 可选 | — |

---

## 九、附录：DeepSeek API 接入方式

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxxxxxxx",
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0.7,
    max_tokens=4096,
    response_format={"type": "json_object"},  # JSON 模式（如果 DeepSeek 支持）
)
```

> ⚠️ 注意：`response_format` 需要确认 DeepSeek 当前版本是否支持。不支持的话，在 Prompt 里强调"只输出 JSON"即可。
