# 部署指南

> 将试题生成助手部署到 Ubuntu 服务器

---

## 前置条件

- Ubuntu 服务器（已通过 WindTerm 连接）
- Windows 本地有项目代码

---

## 第一步：上传代码

在 **Windows 本地** 打开 CMD 或 PowerShell，执行：

```bash
scp -r C:\Users\zhanghailong\Desktop\实训平台智能助手\test_question_generator user@服务器IP:/home/user/
```

输入服务器密码，等待传输完成。

---

## 第二步：服务器配置

在 **WindTerm**（已连接到服务器）中执行以下命令：

### 2.1 进入项目目录

```bash
cd /zhl/test_question_generator
```

### 2.2 创建虚拟环境

```bash
sudo apt install python3-venv -y
python3 -m venv venv
```

### 2.3 激活虚拟环境

```bash
source venv/bin/activate
```

激活后命令行前面会出现 `(venv)` 提示。

### 2.4 安装依赖

```bash
pip install -r requirements.txt
```

### 2.5 配置 .env

```bash
nano .env
```

粘贴以下内容（鼠标右键粘贴）：

```env
DEEPSEEK_API_KEY=sk-
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
FALLBACK_API_KEY=sk-
FALLBACK_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
FALLBACK_MODEL=qwen-plus
```

按 `Ctrl+X` → `Y` → `Enter` 保存退出。

### 2.6 启动服务

```bash
nohup python -m app.main > output.log 2>&1 &
```

### 2.7 验证服务

```bash
curl http://localhost:7860/api/v1/health
```

预期返回：

```json
{"status":"ok","service":"试题生成助手","version":"1.0.0"}
```

### 2.8 开放防火墙

```bash
sudo ufw allow 7860
```

---

## 第三步：验证外部访问

在 **Windows 本地浏览器** 打开：

```
http://服务器IP:7860/api/v1/health
```

看到 JSON 响应即部署成功。

---

## 常用命令

### 查看日志

```bash
cd /zhl/test_question_generator
tail -f output.log
```

### 重启服务

```bash
cd /zhl/test_question_generator
source venv/bin/activate
ps aux | grep app.main
kill -9 进程ID
nohup python -m app.main > output.log 2>&1 &
```

### 停止服务

```bash
ps aux | grep app.main
kill -9 进程ID
```

---

## 设置开机自启（推荐）

```bash
sudo nano /etc/systemd/system/ai-assistant.service
```

粘贴：

```ini
[Unit]
Description=AI Assistant Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/zhl/test_question_generator
ExecStart=/zhl/test_question_generator/venv/bin/python -m app.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

然后：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-assistant
sudo systemctl start ai-assistant
sudo systemctl status ai-assistant
```

设置后服务器重启会自动启动服务，无需手动操作。

---

## 服务器重启后手动启动（如果没有设置开机自启）

如果服务器关机了再开机，按以下步骤启动服务：

```bash
# 1. 进入项目目录
cd /zhl/test_question_generator

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 启动服务
nohup python -m app.main > output.log 2>&1 &

# 4. 验证
sleep 3
curl http://localhost:7860/api/v1/health
```

看到 `{"status":"ok"}` 即恢复成功。