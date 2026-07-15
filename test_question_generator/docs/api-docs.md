# 实训平台 AI 助手 — API 对接文档

> 版本：1.0.0
> 最后更新：2026-07-15
> 基础地址：`http://192.168.1.248:7860`

---

## 目录

1. [接口总览](#1-接口总览)
2. [健康检查](#2-健康检查)
3. [试题生成](#3-试题生成)
4. [课程简介生成](#4-课程简介生成)
5. [实验手册生成](#5-实验手册生成)
6. [错误码](#6-错误码)
7. [对接注意事项](#7-对接注意事项)

---

## 1. 接口总览

| 序号 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 1 | GET | `/api/v1/health` | 健康检查 |
| 2 | POST | `/api/v1/generate` | 生成试题 |
| 3 | POST | `/api/v1/course-intro` | 生成课程简介 |
| 4 | POST | `/api/v1/lab-manual` | 生成实验手册/报告模板 |
| 5 | GET | `/api/v1/lab-manual/{filename}/download` | 下载 Word 文件 |

---

## 2. 健康检查

检查服务是否正常运行。

### 请求

```
GET /api/v1/health
```

### 响应

```json
{
  "status": "ok",
  "service": "实训平台 AI 助手",
  "version": "1.0.0"
}
```

### curl 示例

```bash
curl http://192.168.1.248:7860/api/v1/health
```

---

## 3. 试题生成

根据教学内容（文档或文本），自动生成四种题型的试题，返回结构化 JSON。

### 请求

```
POST /api/v1/generate
Content-Type: application/json
```

### 请求体参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `subject_bank_name` | string | 否 | `"默认题库"` | 题库名称 |
| `subject_bank_remark` | string | 否 | `""` | 题库描述 |
| `document_text` | string | 否 | `null` | 教学内容文本（必填一项，与上传文件二选一） |
| `requirements` | string | 否 | `""` | 具体要求，如"侧重基础概念" |
| `question_types` | int[] | 否 | `[0, 1, 2, 3]` | 题型：`0`=单选, `1`=多选, `2`=判断, `3`=简答 |
| `count_per_type` | int | 否 | `5` | 每种题型数量，范围 1-20 |
| `difficulty` | int | 否 | `0` | 难度：`0`=简单, `1`=困难 |

### 响应体

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
          "content": "Python中用于实现循环的语句有哪些？",
          "analysis": "本题考查Python循环语句的基本知识",
          "subAnswer": null,
          "options": [
            { "content": "for和while", "isRight": true, "analysis": null },
            { "content": "只有for", "isRight": false, "analysis": "Python中除了for循环，还有while循环" },
            { "content": "只有while", "isRight": false, "analysis": "Python中除了while循环，还有for循环" },
            { "content": "for、while和do-while", "isRight": false, "analysis": "Python中没有do-while循环" }
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
| `usage` | object\|null | Token 用量（预留字段，当前为 null） |

### 试题字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | int | 题型：0=单选, 1=多选, 2=判断, 3=简答 |
| `typeName` | string | 题型名称 |
| `level` | int | 难度：0=简单, 1=困难 |
| `levelName` | string | 难度名称 |
| `content` | string | 题干内容 |
| `analysis` | string | 题目解析 |
| `subAnswer` | string\|null | 简答题答案（仅 type=3 时有效） |
| `options` | array | 选项列表 |
| `options[].content` | string | 选项内容 |
| `options[].isRight` | bool | 是否为正确答案 |
| `options[].analysis` | string\|null | 选项解析（错误选项必填，正确选项为 null） |

### 题型规则

| type | typeName | 规则 |
|---|---|---|
| 0 | 单选题 | 4 个选项，恰好 1 个正确答案 |
| 1 | 多选题 | 至少 2 个正确答案 |
| 2 | 判断题 | 2 个选项："正确" / "错误" |
| 3 | 简答题 | options 为空数组，subAnswer 填写答案 |

### curl 示例

```bash
curl -X POST http://192.168.1.248:7860/api/v1/generate \
  -H "Content-Type: application/json" \
  -d "{\"document_text\":\"Python循环有for和while两种\",\"question_types\":[0,2],\"count_per_type\":2,\"difficulty\":0}"
```

---

## 4. 课程简介生成

根据课程名称和章节结构，生成一段 200-300 字的课程简介文本。

### 请求

```
POST /api/v1/course-intro
Content-Type: application/json
```

### 请求体参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `course_name` | string | 是 | 课程名称 |
| `chapters` | array | 是 | 章节列表 |
| `chapters[].name` | string | 是 | 章节名称，如"第一章 基础语法" |
| `chapters[].lessons` | string[] | 是 | 该章节下的实验/课时名称列表 |

### 请求示例

```json
{
  "course_name": "Python程序设计",
  "chapters": [
    {
      "name": "第一章 基础语法",
      "lessons": ["01-变量与数据类型", "01-变量与数据类型实验"]
    },
    {
      "name": "第二章 流程控制",
      "lessons": ["02-条件判断", "02-循环结构"]
    }
  ]
}
```

### 响应体

```json
{
  "success": true,
  "intro": "本课程《Python程序设计》旨在为初学者打下坚实的编程基础。课程内容精心设计，从最核心的基础语法入手，深入讲解变量与数据类型的定义与使用，帮助学员理解程序如何存储和操作数据。随后进入流程控制部分，重点学习条件判断和循环结构，掌握如何让程序根据不同的情况做出决策。通过理论与实践结合的方式，学员将建立起对Python语言的基本认知，为后续学习更复杂的编程概念奠定扎实的根基。",
  "error": null
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `success` | bool | 是否成功 |
| `intro` | string\|null | 生成的课程简介文本（200-300 字） |
| `error` | string\|null | 错误信息 |

### curl 示例

```bash
curl -X POST http://192.168.1.248:7860/api/v1/course-intro \
  -H "Content-Type: application/json" \
  -d "{\"course_name\":\"Python程序设计\",\"chapters\":[{\"name\":\"第一章 基础语法\",\"lessons\":[\"01-变量与数据类型\"]},{\"name\":\"第二章 流程控制\",\"lessons\":[\"02-条件判断\"]}]}"
```

### 前端对接说明

前端从平台课程详情 API 拿到课程 JSON 后，提取关键字段构造请求：

```
course_name → lesson.name
chapters[].name → content[].name
chapters[].lessons → content[].lessonDetails[].name（含 experiment.name）
```

忽略字段：`lessonChapterId`、`addTime`、`updateTime`、`sort`、`enabled`、`image`、`file`、`remark` 等无关字段。

---

## 5. 实验手册生成

生成实验指导手册或实验报告模板，返回 Markdown 内容 + Word 文件下载地址。

### 5.1 生成内容

```
POST /api/v1/lab-manual
Content-Type: application/json
```

#### 请求体参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `title` | string | 是 | — | 实验名称 |
| `document_text` | string | 否 | `null` | 教学内容文本 |
| `requirements` | string | 否 | `""` | 具体要求 |
| `template_type` | string | 否 | `"manual"` | `"manual"`=实验指导手册, `"report"`=实验报告模板 |

#### 请求示例

```json
{
  "title": "Python循环实验",
  "document_text": "for循环用于遍历序列，while循环在条件为真时执行",
  "requirements": "适合大一学生",
  "template_type": "manual"
}
```

#### 响应体

```json
{
  "success": true,
  "title": "Python循环实验",
  "markdown": "## 一、实验目的\n\n1. 掌握 for 循环的基本语法...\n\n## 二、实验原理\n...",
  "download_url": "/api/v1/lab-manual/650065c65ed344cd859e8426e5fb227b.docx/download",
  "error": null
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `success` | bool | 是否成功 |
| `title` | string\|null | 实验名称 |
| `markdown` | string\|null | Markdown 格式的完整内容，前端用 marked.js 渲染预览 |
| `download_url` | string\|null | Word 文件下载地址，拼接完整 URL 为 `http://192.168.1.248:7860{download_url}` |
| `error` | string\|null | 错误信息 |

#### curl 示例

```bash
curl -X POST http://192.168.1.248:7860/api/v1/lab-manual \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Python循环实验\",\"document_text\":\"for循环和while循环\",\"template_type\":\"manual\"}"
```

### 5.2 下载 Word 文件

```
GET /api/v1/lab-manual/{filename}/download
```

从生成接口返回的 `download_url` 获取文件名，拼接完整 URL 下载。

#### curl 示例

```bash
curl -O http://192.168.1.248:7860/api/v1/lab-manual/650065c65ed344cd859e8426e5fb227b.docx/download
```

### 5.3 实验手册模板结构

| 章节 | 内容 |
|---|---|
| 一、实验目的 | 实验的学习目标 |
| 二、实验原理 | 核心理论知识 |
| 三、实验环境 | 硬件、软件、工具 |
| 四、实验步骤 | 分步骤操作过程 |
| 五、实验结果 | 预期结果或输出示例 |
| 六、思考题 | 2-3 个思考题 |

### 5.4 实验报告模板结构

| 章节 | 内容（留空供学生填写） |
|---|---|
| 一、实验目的 | 学生填写学习目标 |
| 二、实验原理 | 学生填写理论知识 |
| 三、实验环境 | 列出软硬件配置 |
| 四、实验过程与记录 | 学生填写操作步骤和观察 |
| 五、实验结果与分析 | 学生填写结果和分析 |
| 六、实验总结 | 学生填写心得体会 |

### 5.5 前端对接说明（Markdown 预览）

前端拿到 `markdown` 字段后，使用 marked.js 渲染预览：

```javascript
// 安装: npm install marked
import { marked } from 'marked';

// 渲染预览
document.getElementById('preview').innerHTML = marked(markdown);

// 编辑时实时更新
editor.oninput = () => {
  preview.innerHTML = marked(editor.value);
};
```

---

## 6. 错误码

| HTTP 状态码 | 说明 | 常见原因 |
|---|---|---|
| 200 | 成功 | 正常返回 |
| 400 | 请求参数错误 | 必填字段缺失、JSON 格式错误、文档解析失败 |
| 500 | 服务器内部错误 | LLM 调用失败、JSON 解析异常 |
| 502 | 上游服务不可用 | 主模型 + 备用模型均不可用 |

### 错误响应格式

```json
{
  "detail": "错误信息描述"
}
```

---

## 7. 对接注意事项

### 7.1 调用架构

```
前端页面（Vue/React）
    ↓ HTTP
Java 后端（业务层）
    ↓ HTTP
Python AI 服务（http://192.168.1.248:7860）
```

严禁前端直接调 Python 服务，必须经 Java 后端转发，避免 API Key 暴露。

### 7.2 超时设置

建议 Java 后端设置 60 秒以上的读取超时：

```java
SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
factory.setConnectTimeout(10000);
factory.setReadTimeout(60000);  // 60秒
restTemplate.setRequestFactory(factory);
```

### 7.3 试题生成入库

API 返回的 `subjectBanks` 是完整题库结构，直接入库。`success`、`error`、`usage` 是 API 包装字段，入库时取 `subjectBanks` 即可。

### 7.4 实验手册下载

Word 下载地址是相对路径，需拼接完整 URL：

```java
String baseUrl = "http://192.168.1.248:7860";
String downloadUrl = response.getDownloadUrl();  // /api/v1/lab-manual/xxx/download
String fullUrl = baseUrl + downloadUrl;          // 完整下载地址
```

### 7.5 并发说明

当前为单进程服务，适合老师手动使用，不支持高并发批量调用。如需批量生成，请联系开发方。

### 7.6 文件上传说明

当前 API 仅支持文本输入（`document_text` 字段）。如需上传 PDF/Word 文档解析，需在 Java 后端先解析文档提取文本，再传入 `document_text` 字段。