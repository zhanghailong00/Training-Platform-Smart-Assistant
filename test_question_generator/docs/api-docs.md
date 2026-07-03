# 试题生成助手 — API 文档

> 版本：1.0.0
> 基础地址：`http://<服务器IP>:7860`

---

## 目录

1. [健康检查](#1-健康检查)
2. [生成试题](#2-生成试题)
3. [错误码](#3-错误码)
4. [请求/响应示例](#4-请求响应示例)
5. [对接注意事项](#5-对接注意事项)

---

## 1. 健康检查

检查服务是否正常运行。

### 请求

```
GET /api/v1/health
```

### 响应

```json
{
  "status": "ok",
  "service": "试题生成助手",
  "version": "1.0.0"
}
```

### curl 示例

```bash
curl http://localhost:7860/api/v1/health
```

---

## 2. 生成试题

上传教学内容，AI 自动生成试题。

### 请求

```
POST /api/v1/generate
Content-Type: application/json
```

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `subject_bank_name` | string | 否 | `"默认题库"` | 题库名称 |
| `subject_bank_remark` | string | 否 | `""` | 题库描述 |
| `document_text` | string | 否 | `null` | 教学内容文本（与上传文件二选一） |
| `requirements` | string | 否 | `""` | 老师的具体要求，如"侧重基础概念" |
| `question_types` | int[] | 否 | `[0, 1, 2, 3]` | 题型：`0`=单选, `1`=多选, `2`=判断, `3`=简答 |
| `count_per_type` | int | 否 | `5` | 每种题型数量，范围 1-20 |
| `difficulty` | int | 否 | `0` | 难度：`0`=简单, `1`=困难 |

### 响应

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

### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `success` | bool | 是否生成成功。部分题型失败时也为 true |
| `subjectBanks` | array | 题库列表，通常只有一个元素 |
| `subjectBanks[].name` | string | 题库名称 |
| `subjectBanks[].remark` | string | 题库描述 |
| `subjectBanks[].questions` | array | 试题列表 |
| `error` | string\|null | 成功时为 null，部分题型失败时说明哪些题型失败 |
| `usage` | object\|null | Token 用量统计（当前为 null，预留字段） |

### 试题字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | int | 题型：0=单选, 1=多选, 2=判断, 3=简答 |
| `typeName` | string | 题型名称：单选题/多选题/判断题/简答题 |
| `level` | int | 难度：0=简单, 1=困难 |
| `levelName` | string | 难度名称：简单/困难 |
| `content` | string | 题干内容 |
| `analysis` | string | 题目解析 |
| `subAnswer` | string\|null | 简答题的参考答案（仅 type=3 时有效，其余为 null） |
| `options` | array | 选项列表（简答题为空数组） |
| `options[].content` | string | 选项内容 |
| `options[].isRight` | bool | 是否为正确答案 |
| `options[].analysis` | string\|null | 选项解析。错误选项必填，正确选项可为 null |

### 题型规则

| type | typeName | 选项规则 |
|---|---|---|
| 0 | 单选题 | 4 个选项，恰好 1 个正确答案 |
| 1 | 多选题 | 至少 2 个正确答案 |
| 2 | 判断题 | 2 个选项："正确" / "错误" |
| 3 | 简答题 | options 为空数组，subAnswer 填写答案 |

---

## 3. 错误码

| HTTP 状态码 | 说明 | 常见原因 |
|---|---|---|
| 200 | 成功 | 正常返回，即使部分题型失败也是 200 |
| 400 | 请求参数错误 | 文档解析失败、不支持的文件格式 |
| 500 | 服务器内部错误 | LLM 调用失败、JSON 解析失败 |
| 502 | 上游服务不可用 | 所有 LLM 模型均不可用（主模型 + 备用模型都失败） |

### 错误响应格式

```json
{
  "detail": "错误信息描述"
}
```

---

## 4. 请求/响应示例

### 示例 1：基础用法

```bash
curl -X POST http://localhost:7860/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "subject_bank_name": "Python基础",
    "document_text": "Python是一种解释型语言，支持面向对象编程。变量不需要声明类型。循环有for和while两种。",
    "requirements": "侧重基础概念",
    "question_types": [0, 2],
    "count_per_type": 2,
    "difficulty": 0
  }'
```

### 示例 2：只有文本，不出判断题和简答

```bash
curl -X POST http://localhost:7860/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "二进制只有0和1两个数字，冯诺依曼结构由运算器、控制器、存储器、输入设备、输出设备组成。",
    "question_types": [0, 1],
    "count_per_type": 3,
    "difficulty": 1
  }'
```

### 示例 3：部分题型失败时的响应

```json
{
  "success": true,
  "subjectBanks": [
    {
      "name": "默认题库",
      "remark": "",
      "questions": [
        {
          "type": 0,
          "typeName": "单选题",
          "level": 0,
          "levelName": "简单",
          "content": "Python中用于终止循环的语句是？",
          "analysis": "break用于完全终止循环",
          "subAnswer": null,
          "options": [
            { "content": "break", "isRight": true, "analysis": null },
            { "content": "continue", "isRight": false, "analysis": "continue跳过当前循环进入下一轮" },
            { "content": "pass", "isRight": false, "analysis": "pass是空语句" },
            { "content": "exit", "isRight": false, "analysis": "exit退出程序" }
          ]
        }
      ]
    }
  ],
  "error": "以下题型生成失败: 多选题, 判断题"
}
```

---

## 5. 对接注意事项

### 5.1 响应格式

顶层字段 `success`、`error`、`usage` 是 API 的响应包装。入库时请取 `subjectBanks` 字段，而非整个 JSON。

```python
# Python 示例：提取题库数据
response = requests.post("http://localhost:7860/api/v1/generate", json=payload)
data = response.json()
subject_banks = data["subjectBanks"]  # 这才是入库需要的数据
```

### 5.2 服务地址

| 环境 | 地址 |
|---|---|
| 开发环境 | `http://localhost:7860` |
| 生产环境 | 待定 |

### 5.3 超时建议

建议调用方设置至少 60 秒的超时时间。单次生成通常需要 10-30 秒。

### 5.4 并发说明

当前为单进程服务，不支持高并发。适合老师手动使用。如需批量生成，请联系开发方。

### 5.5 文件上传（暂未开放 API 版）

当前文件上传（PDF/Word）仅在 Gradio Web 界面中支持。API 版如需文件上传，需使用 `multipart/form-data`，请联系开发方开放此功能。
