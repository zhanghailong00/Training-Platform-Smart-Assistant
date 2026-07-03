# 试题生成助手 — 实现计划

> 日期：2026-07-02
> 基于设计文档：`docs/superpowers/specs/2026-07-02-test-question-generator-design.md`
> 状态：✅ V1 MVP 完成，已通过真实 LLM 端到端验证

**Goal:** 构建试题自动生成服务，老师上传文档或输入文本 → DeepSeek 生成试题 → 输出同事格式 JSON

**Architecture:** 独立 FastAPI 服务，组件化分层（core → schemas → utils → components → services → api/ui），Gradio UI + REST API 双入口

**Tech Stack:** Python 3.11+, FastAPI, Gradio, DeepSeek API (openai SDK), PyMuPDF, python-docx, Pydantic v2

## Global Constraints

- Python 3.11+, 用 pip 管理依赖（当前环境 helper）
- DeepSeek API 调用，OpenAI 兼容 SDK
- 文档支持：PDF (PyMuPDF) + Word (python-docx)
- 输出格式：同事提供的 subjectBanks JSON schema
- 题型：单选(0)、多选(1)、判断(2)、简答(3)
- 难度：简单(0)、困难(1)
- 第一期轻量：同步调用，无数据库，无任务队列
- Windows 本地服务器部署

---

## V1 MVP 完成状态总览（2026-07-02）

| Phase | 内容 | 文件数 | 状态 |
|---|---|---|---|
| 1 | 项目初始化 & 基础设置 | 7 | ✅ 完成 |
| 2 | 数据模型层 (schemas/) | 4 | ✅ 完成 |
| 3 | 工具层 (utils/) | 3 | ✅ 完成 |
| 4 | 功能组件层 (components/) + prompts/ | 6 | ✅ 完成 |
| 5 | 服务编排层 (services/) | 1 | ✅ 完成 |
| 6 | API 路由层 (api/) | 1 | ✅ 完成 |
| 7 | Gradio UI 层 (ui/ + app/) | 2 | ✅ 完成 |
| 8 | 联调验证 | 2 | ✅ 端到端通过（真实 LLM） |

### V1 核心验证

```
模拟验证（无 API Key）: python tests/test_full_pipeline.py        → 5/5 通过
端到端验证（真实 LLM） : python -m app.main 后上传 PDF             → ✅ 4题型全部成功
```

---

## V1.1 TODO（稳定性增强）

> V1.1 不改架构、不改数据模型、不改部署方式。在现有代码上增强稳定性。

### 优先级说明

| 优先级 | 事项 | 改动量 | 涉及文件 | 原因 |
|---|---|---|---|---|
| P0 | JSON 解析失败自动重试（最多 3 次） | 小 | `validator.py`, `exam_service.py` | 现在一次失败就报错 |
| P0 | 降级返回：部分题型成功时返回已成功题目 | 小 | `exam_service.py` | 现在一个题型失败全盘失败 |
| P0 | LLM 原始输出中加入 DeepSeek JSON Mode | 小 | `llm_client.py`, `prompts/` | 提高 JSON 输出稳定性 |
| P1 | 兜底模型（fallback API） | 小 | `core/settings.py`, `llm_client.py` | DeepSeek 满载时自动切换 |
| P2 | 字段合法性自动修正 | 中 | `validator.py`, `question.py` | typeName/levelName 不匹配时自动补 |

### V1.1 TODO 清单

```
P0 - 最高优先级
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] 1. JSON 解析失败自动重试
    位置: components/validator.py → validate()
    改动: 当 JSON 提取失败时，不直接抛异常，返回空列表，由 exam_service 触发重试
    限制: 最多重试 3 次

[ ] 2. exam_service 增加重试循环
    位置: services/exam_service.py
    改动: 对每种题型，validate() 返回空时重试 prompt_builder → llm_client → validator
         最多 3 次
    设计:
         for qtype in question_types:
             for attempt in range(3):
                 messages = build_messages(...)
                 raw = llm_generate(messages)
                 questions = validate(raw)
                 if questions: break  # 成功
             如果 3 次都失败: 跳过该题型，继续下一个
             最后如果总题目数为 0 才返回错误

[ ] 3. 降级返回
    位置: services/exam_service.py
    改动: 部分题型生成成功时，返回已成功的题目 + 错误信息说明哪些题型失败
          不阻塞整个流程

[ ] 4. 启用 DeepSeek JSON Mode
    位置: components/llm_client.py
    改动: 在 API 调用中增加 response_format={"type": "json_object"}
    注意: 需要在 system prompt 末尾强调"输出 JSON 对象，不要加 markdown 代码块标记"
    验证: 通过 playground/prompt_test.py 测试

P1 - 中优先级
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] 5. fallback 模型配置
    位置:
      - core/settings.py: 增加 FALLBACK_API_KEY, FALLBACK_BASE_URL, FALLBACK_MODEL
      - .env.example: 增加 fallback 配置项
      - components/llm_client.py: 主模型失败时自动 fallback

    设计:
        def _try_providers(messages) -> str:
            providers = [
                (settings.llm_api_key, settings.llm_base_url, settings.llm_model),
                (settings.fallback_api_key, settings.fallback_base_url, settings.fallback_model),
            ]
            for api_key, base_url, model in providers:
                if not api_key: continue
                try:
                    return _call(api_key, base_url, model, messages)
                except (LLMTimeoutError, LLMAPIError):
                    continue
            raise LLMAPIError("所有 LLM 服务均不可用")

P2 - 低优先级
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] 6. 字段合法性自动修正
    位置: components/validator.py
    改动: 校验 Question 时，如果 typeName 和 type 不匹配，自动修正
          如果 levelName 和 level 不匹配，自动修正
          记录修正日志（logger.warning）
    规则:
        typeName = QUESTION_TYPE_NAMES[question.type]
        levelName = DIFFICULTY_NAMES[question.level]
```

### 明确不做（V1.1 范围外）

| 事项 | 原因 |
|---|---|
| RAG 知识库 | 需要向量库 + embedding 模型，属于 V2 |
| 并发支持 | 目前单机单用户，不存在瓶颈 |
| 题目去重 | 需要平台题库数据，非生成助手能独立完成 |
| 审核 Agent | 当前由同事人工入库审核，够用 |
| 用户登录 | 平台负责，本服务不做 |
| 记忆系统 | 一次性生成场景，不需要长期记忆 |

### 产出文件

```
test_question_generator/
├── environment.yml
├── .env.example
├── README.md
├── app/__init__.py
├── api/__init__.py
├── services/__init__.py
├── components/__init__.py
├── schemas/__init__.py
├── core/
│   ├── __init__.py
│   ├── constants.py        ✅
│   ├── settings.py          ✅
│   ├── logger.py            ✅
│   └── exceptions.py        ✅
├── prompts/__init__.py
├── utils/__init__.py
├── ui/__init__.py
├── tests/__init__.py
└── playground/__init__.py
```

### 验证方式

```python
# 进入 python 交互环境
from core.settings import settings
from core.logger import get_logger
print(settings)  # 应打印配置信息
```

---

## Phase 2：数据模型层（schemas/）

**目标**：定义所有 Pydantic 模型，作为全项目的数据契约

**依赖**：Phase 1（core/constants 中的枚举值）

### 任务清单

- [ ] 2.1 实现 `schemas/enums.py` — QuestionType(IntEnum), Difficulty(IntEnum)
- [ ] 2.2 实现 `schemas/request.py` — GenerateRequest
- [ ] 2.3 实现 `schemas/question.py` — Option, Question
- [ ] 2.4 实现 `schemas/response.py` — SubjectBank, GenerateResponse

### 验证方式

```python
from schemas.request import GenerateRequest
from schemas.question import Question, Option
from schemas.response import GenerateResponse

# 构造一个请求，序列化为 JSON，再反序列化回来
req = GenerateRequest(
    subject_bank_name="测试题库",
    document_text="二进制转换...",
    requirements="侧重基础",
    question_types=[0, 2],
    count_per_type=5,
    difficulty=0,
)
print(req.model_dump_json(indent=2))
```

---

## Phase 3：工具层（utils/）

**目标**：实现无状态的纯工具函数

**依赖**：Phase 1（core/settings 中的 token 限制配置）

### 任务清单

- [ ] 3.1 实现 `utils/token_utils.py` — `estimate_tokens()`, `truncate_by_tokens()`
- [ ] 3.2 实现 `utils/json_utils.py` — `extract_json()`, `repair_json()`
- [ ] 3.3 实现 `utils/file_utils.py` — `detect_file_type()`, `read_file_bytes()`

### 关键函数签名

```python
# token_utils.py
def estimate_tokens(text: str) -> int
def truncate_by_tokens(text: str, max_tokens: int) -> str

# json_utils.py
def extract_json(text: str) -> list | dict  # 从 LLM 响应中提取 JSON
def repair_json(text: str) -> str           # 修复常见格式问题

# file_utils.py
def detect_file_type(filename: str) -> str  # 返回 "pdf" | "docx" | "unknown"
def read_file_bytes(file) -> bytes
```

### 验证方式

```python
from utils.token_utils import estimate_tokens, truncate_by_tokens
from utils.json_utils import extract_json

text = "这是一段测试文本" * 100
print(f"Token 数: {estimate_tokens(text)}")

# 测试 JSON 提取
raw = 'some text {"key": "value"} more text'
print(extract_json(raw))
```

---

## Phase 4：功能组件层（components/）

**目标**：实现 5 个独立组件，每个可单独测试

**依赖**：Phase 2（schemas）、Phase 3（utils）

### 任务清单

- [ ] 4.1 实现 `components/parser.py`
  - `parse_pdf(file_bytes: bytes) -> str`
  - `parse_docx(file_bytes: bytes) -> str`
  - `parse(file_bytes: bytes, filename: str) -> str`（统一入口）

- [ ] 4.2 实现 `components/preprocessor.py`
  - `clean(text: str) -> str`（去噪、合并空白）
  - `process(text: str, max_tokens: int) -> str`（清洗 + 截断）

- [ ] 4.3 实现 `components/prompt_builder.py`
  - `load_template() -> dict`（从 YAML 加载）
  - `build_messages(text: str, question_type: int, count: int, level: int, level_name: str, requirements: str) -> List[dict]`

- [ ] 4.4 实现 `components/llm_client.py`
  - `generate(messages: List[dict]) -> str`（调 DeepSeek + 重试）

- [ ] 4.5 实现 `components/validator.py`
  - `validate(raw_response: str) -> List[Question]`（提取 JSON + Pydantic 校验 + 修复）

### 关键设计点

```python
# parser.py — 统一入口，根据扩展名分发
def parse(file_bytes: bytes, filename: str) -> str:
    file_type = detect_file_type(filename)
    if file_type == "pdf":
        return parse_pdf(file_bytes)
    elif file_type == "docx":
        return parse_docx(file_bytes)
    else:
        raise DocumentParseError(f"不支持的文件格式: {filename}")

# prompt_builder.py — 从 YAML 加载模板，渲染
def build_messages(...) -> list:
    templates = load_template()  # 读 prompts/exam_generation.yaml
    type_key = {0: "single_choice", 1: "multi_choice", 2: "true_false", 3: "essay"}
    system = templates["system"]
    user = templates[type_key[question_type]]["instruction"].format(...)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

# llm_client.py — 指数退避重试
def generate(messages: list) -> str:
    for attempt in range(settings.max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"LLM 调用失败 (attempt {attempt+1}): {e}")
            if attempt == settings.max_retries - 1:
                raise LLMAPIError(f"DeepSeek API 调用失败: {e}")
            time.sleep(2 ** attempt)
```

### 验证方式

```python
# 每个组件独立测试
from components.parser import parse
text = parse(open("test.pdf", "rb").read(), "test.pdf")
print(f"解析结果: {text[:200]}...")

from components.llm_client import generate
from components.prompt_builder import build_messages
msgs = build_messages("二进制转换...", 0, 1, 0, "简单", "")
resp = generate(msgs)
print(f"LLM 响应: {resp[:200]}...")
```

---

## Phase 5：服务编排层（services/）

**目标**：串联所有组件，实现完整的试题生成流程

**依赖**：Phase 4（所有 components）

### 任务清单

- [ ] 5.1 实现 `services/exam_service.py`
  - `generate_questions(request: GenerateRequest, file_bytes: Optional[bytes] = None, filename: Optional[str] = None) -> GenerateResponse`

### 关键流程

```python
def generate_questions(request, file_bytes=None, filename=None) -> GenerateResponse:
    # 1. 获取文本
    if file_bytes and filename:
        text = parse(file_bytes, filename)
    else:
        text = request.document_text or ""

    if not text:
        raise ValidationError("请提供文档或输入教学内容")

    # 2. 预处理
    text = process(text, settings.max_document_tokens)

    # 3. 按题型逐个生成
    all_questions = []
    level_name = "简单" if request.difficulty == 0 else "困难"

    for qtype in request.question_types:
        # 构建 Prompt
        messages = build_messages(
            text=text,
            question_type=qtype,
            count=request.count_per_type,
            level=request.difficulty,
            level_name=level_name,
            requirements=request.requirements,
        )
        # 调 LLM
        raw = generate(messages)
        # 校验
        questions = validate(raw)
        all_questions.extend(questions)

    # 4. 组装响应
    return GenerateResponse(
        success=True,
        subjectBanks=[SubjectBank(
            name=request.subject_bank_name,
            remark=request.subject_bank_remark,
            questions=all_questions,
        )],
    )
```

### 验证方式

```python
from services.exam_service import generate_questions
from schemas.request import GenerateRequest

req = GenerateRequest(
    subject_bank_name="测试",
    document_text="二进制转换是将二进制数转为十进制...",
    question_types=[0],
    count_per_type=2,
    difficulty=0,
)
resp = generate_questions(req)
print(resp.model_dump_json(indent=2))
```

---

## Phase 6：API 路由层（api/）

**目标**：提供 REST API 端点，供实训平台调用

**依赖**：Phase 5（exam_service）

### 任务清单

- [ ] 6.1 实现 `api/routes.py`
  - `POST /api/v1/generate` — 接收 JSON，返回 JSON
  - `GET /api/v1/health` — 健康检查
  - 异常处理（各异常类型 → 对应 HTTP 状态码）

### 关键代码

```python
from fastapi import APIRouter, HTTPException
from schemas.request import GenerateRequest
from schemas.response import GenerateResponse
from services.exam_service import generate_questions
from core.exceptions import DocumentParseError, LLMTimeoutError, LLMAPIError

router = APIRouter(prefix="/api/v1")

@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    try:
        return generate_questions(req)
    except DocumentParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMTimeoutError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except LLMAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {"status": "ok"}
```

### 验证方式

```bash
curl -X POST http://localhost:7860/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"subject_bank_name":"测试","document_text":"二进制...","question_types":[0],"count_per_type":1,"difficulty":0}'
```

---

## Phase 7：Gradio UI 层（ui/ + app/）

**目标**：提供可视化操作界面，老师可直接使用

**依赖**：Phase 5（exam_service）、Phase 6（API）

### 任务清单

- [ ] 7.1 实现 `ui/gradio_app.py` — 构建 Gradio 界面
- [ ] 7.2 实现 `app/main.py` — FastAPI 入口，注册路由 + 挂载 Gradio

### Gradio 界面设计

```python
# ui/gradio_app.py
import gradio as gr
from services.exam_service import generate_questions
from schemas.request import GenerateRequest

def create_ui():
    def handle_generate(name, remark, file, text, requirements, types, count, difficulty):
        file_bytes = None
        filename = None
        if file is not None:
            file_bytes = file  # Gradio 直接传 bytes
            filename = getattr(file, 'name', 'upload.pdf')

        req = GenerateRequest(
            subject_bank_name=name,
            subject_bank_remark=remark,
            document_text=text or None,
            requirements=requirements,
            question_types=types,
            count_per_type=count,
            difficulty=0 if difficulty == "简单" else 1,
        )

        resp = generate_questions(req, file_bytes=file_bytes, filename=filename)
        return resp.model_dump_json(indent=2)

    with gr.Blocks(title="试题生成助手") as demo:
        gr.Markdown("# 📝 试题生成助手")

        with gr.Row():
            name = gr.Textbox(label="题库名称", value="默认题库")
            remark = gr.Textbox(label="题库描述")

        with gr.Row():
            file = gr.File(label="上传文档（PDF/Word）", file_types=[".pdf", ".docx"])
            text = gr.Textbox(label="或直接输入教学内容", lines=8, placeholder="如：第一章计算机基础，包含二进制转换、冯诺依曼结构...")

        requirements = gr.Textbox(label="具体要求", placeholder="如：侧重基础概念，不要考太偏的知识点")

        with gr.Row():
            types = gr.CheckboxGroup(
                label="题型",
                choices=[(0, "单选题"), (1, "多选题"), (2, "判断题"), (3, "简答题")],
                value=[0, 1, 2, 3],
            )
            count = gr.Slider(label="每种题型数量", minimum=1, maximum=20, value=5, step=1)
            difficulty = gr.Radio(label="难度", choices=["简单", "困难"], value="简单")

        btn = gr.Button("🚀 生成试题", variant="primary")
        output = gr.JSON(label="生成结果")

        btn.click(
            fn=handle_generate,
            inputs=[name, remark, file, text, requirements, types, count, difficulty],
            outputs=output,
        )

    return demo
```

```python
# app/main.py
import uvicorn
import gradio as gr
from fastapi import FastAPI
from api.routes import router
from ui.gradio_app import create_ui

app = FastAPI(title="试题生成助手", version="1.0.0")
app.include_router(router)

# 挂载 Gradio
ui = create_ui()
gr.mount_gradio_app(app, ui, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
```

### 验证方式

浏览器打开 `http://localhost:7860`，上传文档或输入文本，选择题型，点击生成。

---

## Phase 8：联调验证 & Prompt 调优

**目标**：端到端测试 + 沙箱调试 Prompt

**依赖**：Phase 1-7 全部完成

### 任务清单

- [ ] 8.1 端到端测试：准备 2-3 份测试文档，走通完整流程
- [ ] 8.2 检查输出 JSON 是否完全符合同事格式
- [ ] 8.3 `playground/prompt_test.py` — 单文件 Prompt 调试脚本
- [ ] 8.4 根据测试结果微调 `prompts/exam_generation.yaml`
- [ ] 8.5 补充 `tests/` 下的单元测试（至少每个 component 一个）

---

## 依赖关系图

```
Phase 1 (core/)
    │
    ▼
Phase 2 (schemas/)  ←──────────┐
    │                           │
    ▼                           │
Phase 3 (utils/)                │
    │                           │
    ▼                           │
Phase 4 (components/) ──────────┘ (依赖 schemas + utils)
    │
    ▼
Phase 5 (services/exam_service.py)
    │
    ├──────────┬──────────┐
    ▼          ▼          │
Phase 6     Phase 7       │
(api/)      (ui/)         │
    │          │          │
    └──────────┴──────────┘
               │
               ▼
          Phase 8 (联调)
```

---

## 快速参考：关键文件清单

| 文件 | Phase | 行数估计 |
|---|---|---|
| `core/constants.py` | 1 | ~15 |
| `core/settings.py` | 1 | ~30 |
| `core/logger.py` | 1 | ~20 |
| `core/exceptions.py` | 1 | ~20 |
| `schemas/enums.py` | 2 | ~15 |
| `schemas/request.py` | 2 | ~25 |
| `schemas/question.py` | 2 | ~35 |
| `schemas/response.py` | 2 | ~20 |
| `utils/token_utils.py` | 3 | ~30 |
| `utils/json_utils.py` | 3 | ~40 |
| `utils/file_utils.py` | 3 | ~20 |
| `components/parser.py` | 4 | ~50 |
| `components/preprocessor.py` | 4 | ~40 |
| `components/prompt_builder.py` | 4 | ~50 |
| `components/llm_client.py` | 4 | ~50 |
| `components/validator.py` | 4 | ~50 |
| `prompts/exam_generation.yaml` | 4 | ~80 |
| `services/exam_service.py` | 5 | ~60 |
| `api/routes.py` | 6 | ~40 |
| `ui/gradio_app.py` | 7 | ~60 |
| `app/main.py` | 7 | ~20 |
| **总计** | | **~770 行** |

---

## 预计工作量

| Phase | 内容 | 预计时间 |
|---|---|---|
| 1 | 项目初始化 | 15 分钟 |
| 2 | 数据模型 | 15 分钟 |
| 3 | 工具层 | 20 分钟 |
| 4 | 组件层 | 45 分钟 |
| 5 | 服务层 | 15 分钟 |
| 6 | API 层 | 15 分钟 |
| 7 | UI 层 | 20 分钟 |
| 8 | 联调 | 30 分钟 |
| **合计** | | **约 3 小时** |
