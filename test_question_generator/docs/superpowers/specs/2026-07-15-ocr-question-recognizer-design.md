# OCR 试题识别助手 — 设计文档

> 日期：2026-07-15
> 状态：待审批
> 作者：zhanghailong

---

## 一、功能概述

### 1.1 背景

高职/专科院校的老师手里有大量纸质试卷、习题集、教材扫描件，想把这些题目录入到平台题库中。手动录入一道题需要几分钟，一个老师一学期可能需要录入几百道题。本功能通过 OCR 识别图片中的文字，再利用 LLM 结构化提取，自动将纸质题目转为电子题库 JSON，直接入库。

### 1.2 核心流程

```
老师拍照或上传试卷图片
  → OCR 识别图片中的文字
  → LLM 结构化提取（识别题型、选项、答案）
  → 输出标准 subjectBanks JSON
  → 直接入库
```

### 1.3 第一期范围

| 做 | 不做 |
|---|---|
| 图片 OCR 文字识别 | 手写体识别 |
| 选择题（单选/多选）识别 | 复杂表格识别 |
| 判断题识别 | 公式/图表识别 |
| 简答题识别 | 批量上传（一次多张） |
| 输出标准 subjectBanks JSON | 图片预处理（裁切、旋转矫正） |
| 复用现有 llm_client、core、utils | 端到端训练 OCR 模型 |

---

## 二、技术方案

### 2.1 整体架构

```
用户上传图片
  ↓
components/ocr_recognizer.py（新增）
  → PaddleOCR 识别图片中的文字
  → 返回纯文本
  ↓
复用 services/exam_service.py 的部分逻辑
  → 但不是"生成新题"，而是"结构化提取"
  → 调 LLM 识别题型、选项、答案
  ↓
输出 subjectBanks JSON
  → 直接复用现有入库流程
```

### 2.2 复用现有代码

| 模块 | 是否复用 | 说明 |
|---|---|---|
| `core/` | ✅ | settings, logger, exceptions, constants 全部复用 |
| `utils/` | ✅ | token_utils, json_utils 复用 |
| `components/llm_client.py` | ✅ | DeepSeek + Qwen 双模型 + fallback 复用 |
| `components/validator.py` | ✅ | Pydantic 校验复用，但不需要业务规则校验 |
| `schemas/question.py` | ✅ | 复用现有 Question/Option 模型 |
| `schemas/response.py` | ✅ | 复用 SubjectBank/GenerateResponse |
| `api/routes.py` | ⚠️ 追加 | 新增 `/api/v1/ocr-recognize` 路由 |

### 2.3 新增文件

| 文件 | 说明 |
|---|---|
| `components/ocr_recognizer.py` | OCR 识别核心组件（基于 PaddleOCR） |
| `prompts/ocr_extract.yaml` | OCR 结果结构化提取 Prompt |
| `services/ocr_service.py` | OCR 识别 + 结构化提取编排 |
| `schemas/ocr.py` | OCR 请求/响应模型 |

### 2.4 新增依赖

```bash
pip install paddlepaddle paddleocr
```

### 2.5 不需要

- `components/parser.py` — 不需要解析 PDF/Word
- `components/preprocessor.py` — OCR 出来的文本不需要清洗
- `components/business_validator.py` — 识别出来的题目不需要业务规则校验

---

## 三、核心组件设计

### 3.1 OCR 识别组件 — `components/ocr_recognizer.py`

```python
"""OCR 识别组件：基于 PaddleOCR 识别图片中的文字"""

import numpy as np
from paddleocr import PaddleOCR
from core.logger import get_logger

logger = get_logger(__name__)

# 全局 OCR 实例（延迟初始化，避免模块导入时加载模型）
_ocr = None


def _get_ocr():
    """延迟初始化 OCR 实例"""
    global _ocr
    if _ocr is None:
        logger.info("加载 PaddleOCR 模型（首次加载可能需要 30-60 秒）")
        _ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False)
        logger.info("PaddleOCR 模型加载完成")
    return _ocr


def recognize(image_bytes: bytes) -> str:
    """
    识别图片中的文字。

    Args:
        image_bytes: 图片文件的二进制数据

    Returns:
        识别出的文本，按阅读顺序排列
    """
    import cv2
    import numpy as np

    ocr = _get_ocr()

    # 将 bytes 转为 OpenCV 图像
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 执行 OCR 识别
    result = ocr.ocr(img, cls=True)

    # 提取文字，按行排列
    lines = []
    if result and result[0]:
        for line in result[0]:
            text = line[1][0]  # 识别出的文字
            confidence = line[1][1]  # 置信度
            if confidence > 0.5:  # 过滤低置信度结果
                lines.append(text)

    text = "\n".join(lines)
    logger.info(f"OCR 识别完成: {len(lines)} 行文字")
    return text
```

### 3.2 Prompt 设计 — `prompts/ocr_extract.yaml`

```yaml
system: |
  你是一位试题识别专家。你的任务是从OCR识别出的文本中，提取出完整的试题信息。

  请严格遵循以下原则：
  1. 识别每道题的题型（单选/多选/判断/简答）
  2. 提取题干内容
  3. 提取选项（如果有）
  4. 提取正确答案（如果有标注）
  5. 输出为 JSON 格式

  注意：
  - 如果题目没有标注答案，answer 字段设为 null
  - 如果无法确定题型，默认为单选题
  - 不要修改题目的原始内容，只做提取

user: |
  请从以下OCR识别出的文本中提取试题信息。

  OCR文本：
  {ocr_text}

  输出格式：
  {{
    "questions": [
      {{
        "type": 0,
        "typeName": "单选题",
        "content": "题干内容",
        "options": [
          {{"content": "A选项", "isRight": true}},
          {{"content": "B选项", "isRight": false}}
        ],
        "analysis": "解析（如果有）"
      }}
    ]
  }}
```

### 3.3 服务编排 — `services/ocr_service.py`

```python
def ocr_recognize(request: OcrRequest) -> GenerateResponse:
    """
    OCR 识别 + 结构化提取完整流程。

    流程：
    1. OCR 识别图片中的文字
    2. LLM 结构化提取（识别题型、选项、答案）
    3. Pydantic 校验
    4. 输出 subjectBanks JSON
    """
    # 1. OCR 识别
    ocr_text = recognize(request.image_bytes)

    # 2. 构建 Prompt
    messages = build_ocr_messages(ocr_text)

    # 3. 调 LLM
    raw_response = llm_generate(messages, use_json_mode=True)

    # 4. Pydantic 校验
    questions, errors = validate(raw_response)

    # 5. 组装响应
    return GenerateResponse(
        success=True,
        subjectBanks=[SubjectBank(
            name=request.subject_bank_name,
            questions=questions,
        )],
    )
```

---

## 四、数据模型

### 4.1 请求模型 — `schemas/ocr.py`

```python
from pydantic import BaseModel, Field
from typing import Optional


class OcrRequest(BaseModel):
    """OCR 试题识别请求"""
    subject_bank_name: str = Field(default="OCR识别题库", description="题库名称")
    subject_bank_remark: str = Field(default="", description="题库描述")
    # 图片以二进制上传，不在 JSON 中
```

### 4.2 响应模型

复用现有的 `GenerateResponse`（`schemas/response.py`），不需要新增。

---

## 五、API 设计

### 5.1 新增 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/ocr-recognize` | OCR 识别图片中的试题 |

### 5.2 请求

```
POST /api/v1/ocr-recognize
Content-Type: multipart/form-data

参数：
  image: (binary, 图片文件)
  subject_bank_name: "OCR识别题库"（可选）
  subject_bank_remark: ""（可选）
```

### 5.3 响应

复用 `GenerateResponse` 格式，与试题生成接口完全一致。

```json
{
  "success": true,
  "subjectBanks": [
    {
      "name": "OCR识别题库",
      "remark": "",
      "questions": [
        {
          "type": 0,
          "typeName": "单选题",
          "level": 0,
          "levelName": "简单",
          "content": "Python中用于终止循环的语句是？",
          "analysis": "",
          "subAnswer": null,
          "options": [
            { "content": "break", "isRight": true, "analysis": null },
            { "content": "continue", "isRight": false, "analysis": null },
            { "content": "pass", "isRight": false, "analysis": null },
            { "content": "exit", "isRight": false, "analysis": null }
          ]
        }
      ]
    }
  ],
  "error": null
}
```

---

## 六、学生端拍照上传流程

### 6.1 场景

学生考试结束后，老师想快速把纸质试卷录入题库。学生用手机拍照上传，系统自动识别并入库。

### 6.2 流程

```
学生/老师拍照上传
  → 平台前端接收图片
  → Java 后端转发到 Python AI 服务
  → OCR 识别 → 结构化提取 → 返回 JSON
  → Java 后端入库
```

### 6.3 前端交互

```
┌──────────────────────────────────────────────┐
│  📷 OCR 试题识别                              │
│                                              │
│  上传试卷图片：[选择文件] 或 [拍照]             │
│                                              │
│  题库名称：[OCR识别题库]                       │
│                                              │
│  [🚀 识别]                                    │
│                                              │
│  ┌──── 识别结果 ───────────────────────────┐  │
│  │ 1. 单选题：Python中用于终止循环的语句是？   │  │
│  │    A. break ✓  B. continue  C. pass      │  │
│  │ 2. 判断题：Python是解释型语言 ✓            │  │
│  │                                          │  │
│  │  [确认入库]  [重新识别]                   │  │
│  └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

---

## 七、实现计划

### 7.1 涉及文件

| 文件 | 操作 |
|---|---|
| `schemas/ocr.py` | **新增**：请求模型 |
| `components/ocr_recognizer.py` | **新增**：PaddleOCR 封装 |
| `prompts/ocr_extract.yaml` | **新增**：结构化提取 Prompt |
| `services/ocr_service.py` | **新增**：OCR 识别编排 |
| `api/routes.py` | **修改**：追加 `/api/v1/ocr-recognize` 路由 |
| `core/constants.py` | **修改**：增加 OCR 相关常量 |

### 7.2 步骤

| 步 | 内容 | 时间 |
|---|---|---|
| 1 | 安装 PaddleOCR + 验证 | 30 分钟 |
| 2 | 新增 `schemas/ocr.py` | 10 分钟 |
| 3 | 新增 `components/ocr_recognizer.py` | 30 分钟 |
| 4 | 新增 `prompts/ocr_extract.yaml` | 20 分钟 |
| 5 | 新增 `services/ocr_service.py` | 30 分钟 |
| 6 | 修改 `api/routes.py` | 15 分钟 |
| 7 | 联调验证 | 30 分钟 |
| **总计** | | **约 2.5 小时** |

---

## 八、预期效果

### 输入

一张手机拍摄的试卷照片（包含选择题、判断题）：

```
1. Python中用于终止循环的语句是？
A. break  B. continue  C. pass  D. exit

2. 判断：Python是解释型语言。（对/错）
```

### 输出

标准化的 subjectBanks JSON，直接入库。

### 演示价值

- 老师现场用手机拍照 → 系统自动识别入库 → 整个过程 10 秒
- 对比：手动录入一道题要 2 分钟，一套试卷 20 道题就是 40 分钟
- 销售话术："AI 赋能传统教学，让老师从繁琐的录入工作中解放出来"