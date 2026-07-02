# 试题生成助手

基于 DeepSeek 大模型的试题自动生成服务。

## 功能

- 📄 上传 PDF / Word 文档，或直接输入教学内容
- 🤖 自动生成四种题型：单选题、多选题、判断题、简答题
- 📋 输出结构化 JSON，可直接入库到实训平台题库
- 🌐 提供 REST API 和 Gradio Web 界面

## 快速开始

### 1. 创建环境

```bash
conda env create -f environment.yml
conda activate ai-assistant
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key
```

### 3. 启动服务

```bash
python -m app.main
```

浏览器打开 http://localhost:7860 即可使用。

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/generate` | 生成试题 |
| GET | `/api/v1/health` | 健康检查 |

## 项目结构

```
test_question_generator/
├── app/           # 应用入口
├── api/           # API 路由
├── services/      # 业务编排
├── components/    # 功能组件
├── schemas/       # 数据模型
├── core/          # 基础设施
├── prompts/       # Prompt 模板
├── utils/         # 工具函数
├── ui/            # Gradio 界面
├── tests/         # 测试
└── playground/    # 调试沙箱
```
