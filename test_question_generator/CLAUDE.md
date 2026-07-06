# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

试题生成助手 — 基于 DeepSeek/Qwen 大模型的试题自动生成服务。老师上传 PDF/Word 文档或输入教学内容，AI 自动生成结构化试题 JSON，对接实训平台题库。

## Commands

```bash
# 启动服务
python -m app.main
# 浏览器打开 http://localhost:7860

# 模拟验证（不需要 API Key）
python tests/test_full_pipeline.py

# 调试 Prompt（需要 API Key）
python playground/prompt_test.py

# API 文档
http://localhost:7860/docs  # FastAPI Swagger UI
```

## Architecture

7 层分层架构，每层只依赖下层，不跨层调用：

```
core → schemas → utils → components → services → api → ui
```

### Layer Descriptions

- **core/** — 基础设施：settings（.env 配置）、logger（统一日志）、exceptions（7 种自定义异常）、constants
- **schemas/** — Pydantic 数据模型：enums（题型/难度枚举）、request（GenerateRequest）、question（Question/Option，对齐同事格式）、response（GenerateResponse/SubjectBank）
- **utils/** — 无状态工具函数：token_utils（tiktoken 估算与截断）、json_utils（4 层 JSON 提取 + 格式修复 + unwrap_questions）、file_utils（文件类型判断）
- **components/** — 功能组件（每个文件一个职责）：
  - parser.py — PDF/Word → 纯文本
  - preprocessor.py — 文本清洗 + token 截断
  - prompt_builder.py — 加载 YAML 模板 + 变量替换 → messages
  - llm_client.py — 多模型调用（DeepSeek 主 + Qwen 备），自动切换 + 指数退避重试
  - validator.py — JSON 提取 + Pydantic 校验 + 业务规则校验
  - business_validator.py — 题型业务规则（单选题1个答案、多选题至少2个等）
- **services/exam_service.py** — 唯一编排者，串联所有 components。每题型最多自修复重试 3 次，降级返回
- **api/routes.py** — FastAPI 路由：POST /api/v1/generate, GET /api/v1/health
- **ui/gradio_app.py** — Gradio Web 界面，挂载到 FastAPI 的 /
- **prompts/exam_generation.yaml** — Prompt 模板，按题型拆分，与代码分离

### Key Design Decisions

- **JSON 稳定性保障**（7 层）：JSON Mode → 文本修复 → Pydantic 校验 → 业务规则校验 → 自修复重试（最多3次）→ 降级返回 → 人工兜底
- **多模型 fallback**：DeepSeek 失败自动切到 Qwen，同一请求内只失败一次。两个厂商独立账户互不影响
- **双入口**：Gradio UI 和 REST API 共享同一个 exam_service，行为一致
- **无数据库**：轻量无状态服务，Prompt 存 YAML，不持久化数据

### JSON Output Schema

最终输出严格对齐同事格式：

```json
{
  "subjectBanks": [{
    "name": "题库名称",
    "remark": "题库描述",
    "questions": [{
      "type": 0,          // 0=单选, 1=多选, 2=判断, 3=简答
      "typeName": "单选题",
      "level": 0,         // 0=简单, 1=困难
      "levelName": "简单",
      "content": "题干",
      "analysis": "解析",
      "subAnswer": null,  // 仅简答题
      "options": [
        { "content": "选项", "isRight": true/false, "analysis": "解析或null" }
      ]
    }]
  }]
}
```

## Environment

- Python 3.11+
- Key deps: fastapi, uvicorn, gradio, openai, PyMuPDF, python-docx, pydantic, pyyaml
- .env file with DEEPSEEK_API_KEY (主模型) and optional FALLBACK_API_KEY (备用模型 Qwen)
- Fallback 通义千问 base_url: `https://dashscope.aliyuncs.com/compatible-mode/v1`

## Important Notes

- `.env` 包含 API Key，已加入 `.gitignore`，不会提交
- 修改 Prompt 调优时改 `prompts/exam_generation.yaml`，不需要改 Python 代码
- 新增题型时需要同步修改：schemas/enums.py → prompts/exam_generation.yaml → components/business_validator.py
- 所有组件可以独立测试，不依赖 LLM（见 tests/test_full_pipeline.py）
