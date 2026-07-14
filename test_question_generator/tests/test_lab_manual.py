"""实验手册生成功能验证脚本"""

import sys, os, json, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("实验手册生成功能验证")
print("=" * 60)

# 1. 验证数据模型
print("\n[1/4] 验证数据模型...")
from schemas.lab import LabManualRequest, LabManualResponse
req = LabManualRequest(title="Python循环实验", document_text="for和while循环", template_type="manual")
assert req.title == "Python循环实验"
assert req.template_type == "manual"
print("  [OK] LabManualRequest 构建成功")

resp = LabManualResponse(success=True, title="test", markdown="# 内容", download_url="/download/test.docx")
assert resp.success == True
assert resp.markdown == "# 内容"
print("  [OK] LabManualResponse 构建成功")

# 2. 验证 Prompt 模板加载
print("\n[2/4] 验证 Prompt 模板加载...")
import yaml
from pathlib import Path
prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "lab_manual.yaml"
with open(prompt_path, "r", encoding="utf-8") as f:
    templates = yaml.safe_load(f)
assert "system" in templates
assert "manual_template" in templates
assert "report_template" in templates
print("  [OK] Prompt 模板加载成功: system, manual_template, report_template")

# 验证模板格式化
user_prompt = templates["manual_template"].format(
    title="Python循环实验",
    document_text="for和while循环",
    requirements="无",
)
assert "Python循环实验" in user_prompt
assert "for和while循环" in user_prompt
print("  [OK] Prompt 模板格式化成功")

# 3. 验证 Word 文档生成
print("\n[3/4] 验证 Word 文档生成...")
from components.docx_builder import markdown_to_docx
md = """# Python循环结构实验

## 一、实验目的

掌握Python循环语句的使用。

## 二、实验步骤

1. 安装Python环境
2. 编写for循环代码
3. 编写while循环代码

- 注意缩进
- 注意冒号

## 三、实验结果

```
for i in range(5):
    print(i)
```
"""
path = markdown_to_docx(md)
assert os.path.exists(path)
size = os.path.getsize(path)
print(f"  [OK] Word 文件生成成功: {size} bytes")
os.remove(path)

# 4. 验证服务导入
print("\n[4/4] 验证服务导入...")
from services.lab_service import generate_lab_manual
from components.llm_client import generate
from api.routes import router
print("  [OK] 所有模块导入成功")

print("\n" + "=" * 60)
print("[SUCCESS] 全部验证通过！")
print("=" * 60)
print("""
测试方法:
  1. 启动服务: python -m app.main
  2. 浏览器打开 http://localhost:7860
  3. 切换到"实验手册"Tab
  4. 输入实验名称和教学内容，点击生成
  5. 查看 Markdown 编辑区和预览区
  6. 修改内容后预览自动更新

API 测试:
  curl -X POST http://localhost:7860/api/v1/lab-manual \
    -H "Content-Type: application/json" \
    -d '{"title":"Python循环实验","document_text":"for和while循环","requirements":"基础语法","template_type":"manual"}'

预期返回:
  {"success":true,"title":"...","markdown":"# 实验名称...","download_url":"/api/v1/lab-manual/xxx/download"}
""")