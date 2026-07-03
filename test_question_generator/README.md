# 试题生成助手

基于 DeepSeek 大模型的试题自动生成服务。实训平台老师上传教学文档或输入教学内容，AI 自动生成结构化试题 JSON，对接平台题库入库。

## 第一版功能

- **📄 文档输入** — 上传 PDF / Word 文档，或直接在文本框输入教学内容
- **🤖 四种题型** — 单选题、多选题、判断题、简答题
- **⚙️ 参数控制** — 每题型数量（1-20）、难度（简单/困难）、具体要求
- **📋 结构化输出** — JSON 格式，完全对齐同事题库字段（subjectBanks schema）
- **🌐 两种使用方式** — Gradio Web 界面（老师用）+ REST API（平台集成）
- **🔌 独立服务** — 不依赖实训平台代码，提供 API 供平台调用

## 快速开始

### 环境要求

- Python 3.11+
- DeepSeek API Key

### 1. 安装依赖

```bash
pip install fastapi uvicorn gradio python-multipart python-docx PyMuPDF openai pydantic pyyaml httpx tiktoken
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=sk-your-key-here
```

### 3. 启动服务

```bash
python -m app.main
```

浏览器打开 **http://localhost:7860** 即可使用。

## 使用方式

### 方式一：Gradio Web 界面

浏览器打开 http://localhost:7860，操作步骤：

1. 填写题库名称和描述（可选）
2. 上传 PDF/Word 文档，或直接输入教学内容
3. 选择要生成的题型
4. 设置每种题型数量和难度
5. 点击「生成试题」
6. 复制输出的 JSON 交给同事入库

### 方式二：REST API

```bash
curl -X POST http://localhost:7860/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "subject_bank_name": "Python基础",
    "subject_bank_remark": "覆盖变量、循环、函数等核心概念",
    "document_text": "Python是一种解释型语言...",
    "requirements": "侧重基础概念理解",
    "question_types": [0, 1, 2, 3],
    "count_per_type": 5,
    "difficulty": 0
  }'
```

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `subject_bank_name` | string | 否 | 题库名称（默认"默认题库"） |
| `subject_bank_remark` | string | 否 | 题库描述 |
| `document_text` | string | 否 | 教学内容文本（与文件二选一） |
| `requirements` | string | 否 | 老师的具体要求 |
| `question_types` | int[] | 否 | 题型：0=单选, 1=多选, 2=判断, 3=简答（默认全部） |
| `count_per_type` | int | 否 | 每种题型数量（默认5，范围1-20） |
| `difficulty` | int | 否 | 难度：0=简单, 1=困难（默认0） |

#### 响应格式

```json
{
  "success": true,
  "subjectBanks": [
    {
      "name": "题库名称",
      "remark": "题库描述",
      "questions": [
        {
          "type": 0,
          "typeName": "单选题",
          "level": 0,
          "levelName": "简单",
          "content": "题干内容",
          "analysis": "题目解析",
          "subAnswer": null,
          "options": [
            { "content": "选项A", "isRight": false, "analysis": "错误原因" },
            { "content": "选项B", "isRight": true, "analysis": null },
            { "content": "选项C", "isRight": false, "analysis": "错误原因" },
            { "content": "选项D", "isRight": false, "analysis": "错误原因" }
          ]
        }
      ]
    }
  ],
  "error": null,
  "usage": null
}
```

#### 健康检查

```bash
curl http://localhost:7860/api/v1/health
# → {"status":"ok","service":"试题生成助手","version":"1.0.0"}
```

## 项目结构

```
test_question_generator/
│
├── app/main.py              应用入口，挂载 Gradio + 注册 API 路由
├── api/routes.py             REST API 端点（/api/v1/generate, /health）
├── services/exam_service.py  业务编排层，串联整个生成流程
├── components/
│   ├── parser.py             文档解析（PDF / Word → 纯文本）
│   ├── preprocessor.py       文本预处理（清洗、截断、token 估算）
│   ├── prompt_builder.py     Prompt 构建（加载 YAML 模板 + 变量替换）
│   ├── llm_client.py         DeepSeek API 调用（重试 + 超时处理）
│   └── validator.py          JSON 提取 + Pydantic 校验
├── schemas/
│   ├── enums.py              枚举定义（题型、难度）
│   ├── request.py            请求模型
│   ├── question.py           试题模型（对齐同事格式）
│   └── response.py           响应模型
├── core/
│   ├── settings.py           配置管理（.env + 环境变量）
│   ├── logger.py             统一日志
│   ├── exceptions.py         自定义异常
│   └── constants.py          常量
├── prompts/
│   └── exam_generation.yaml  Prompt 模板（按题型拆分）
├── utils/
│   ├── token_utils.py        Token 估算与截断
│   ├── json_utils.py         JSON 提取与格式修复
│   └── file_utils.py         文件类型判断
├── ui/gradio_app.py          Gradio Web 界面
├── tests/                    模拟验证
├── playground/               Prompt 调试沙箱
├── .env                      API Key 配置（不提交到 git）
├── .env.example              配置模板
├── .gitignore
└── environment.yml           conda 环境定义
```

## 生成示例

上传一份 Python 实验指导书 PDF，生成结果（部分）：

| 题型 | 题数 | 示例 |
|---|---|---|
| 单选题 | 2 | "Python中用于终止循环的语句是？" → break |
| 多选题 | 2 | "Python中哪些属于循环控制语句？" → break, continue, pass |
| 判断题 | 2 | "Python有switch...case语句" → 错误 |
| 简答题 | 2 | "简述if条件语句的基本语法结构" |

所有题目均基于文档内容生成，不超纲。

## 开发

### 验证模拟流程

```bash
python tests/test_full_pipeline.py
```

测试 5 个步骤：文本预处理 → Prompt 构建 → JSON 校验 → 响应组装 → 请求模型

### 调试 Prompt

```bash
python playground/prompt_test.py
```

## 技术栈

| 层 | 选型 |
|---|---|
| 语言 | Python 3.11+ |
| Web 框架 | FastAPI |
| 前端 | Gradio |
| LLM | DeepSeek API（OpenAI 兼容 SDK） |
| PDF 解析 | PyMuPDF |
| Word 解析 | python-docx |
| 数据校验 | Pydantic v2 |
| Prompt 管理 | YAML |

## 许可证

仅供实训平台内部使用。
