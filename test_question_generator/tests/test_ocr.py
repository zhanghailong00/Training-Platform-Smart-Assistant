"""OCR 功能验证脚本"""

import sys, os, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("OCR 功能验证")
print("=" * 60)

# 1. 验证数据模型
print("\n[1/4] 验证数据模型...")
from schemas.ocr import OcrRequest
req = OcrRequest(subject_bank_name="测试题库", subject_bank_remark="OCR测试")
assert req.subject_bank_name == "测试题库"
print("  [OK] OcrRequest 构建成功")

# 2. 验证 Prompt 模板
print("\n[2/4] 验证 Prompt 模板...")
import yaml
from pathlib import Path
prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "ocr_extract.yaml"
with open(prompt_path, "r", encoding="utf-8") as f:
    t = yaml.safe_load(f)
assert "system" in t
assert "user" in t
assert "{ocr_text}" in t["user"]
print("  [OK] OCR Prompt 模板加载成功")

# 3. 验证 OCR 组件导入
print("\n[3/4] 验证 OCR 组件导入...")
from components.ocr_recognizer import recognize, OcrError
from components.llm_client import generate
print("  [OK] OCR 组件导入成功")

# 4. 验证服务导入
print("\n[4/4] 验证服务导入...")
from services.ocr_service import ocr_recognize
from api.routes import router
print("  [OK] OCR 服务 + 路由导入成功")

print("\n" + "=" * 60)
print("[SUCCESS] 全部验证通过！")
print("=" * 60)
print("""
使用方法:
  1. 配置 .env 中已包含 DASHSCOPE_API_KEY（复用 Qwen Key）
  2. 启动服务: python -m app.main
  3. 测试:
     curl -X POST http://localhost:7860/api/v1/ocr-recognize \\
       -F "image=@试卷图片.jpg" \\
       -F "subject_bank_name=OCR识别题库"
""")