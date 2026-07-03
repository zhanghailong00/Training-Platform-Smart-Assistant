"""
完整流程验证（无需 API Key，使用模拟 LLM 响应）

使用方法：
    cd test_question_generator
    python tests/test_full_pipeline.py
"""

import sys
import json
import io
from pathlib import Path

# 修复 Windows GBK 终端无法输出中文/emoji 的问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.request import GenerateRequest
from schemas.response import GenerateResponse, SubjectBank
from schemas.question import Question, Option
from components.preprocessor import clean, process
from components.prompt_builder import build_messages, load_template
from components.validator import validate
from utils.token_utils import estimate_tokens
from core.constants import QUESTION_TYPE_NAMES, DIFFICULTY_NAMES


# ============================================================
# 模拟 LLM 响应（符合同事 JSON 格式）
# ============================================================
MOCK_LLM_RESPONSE = """
[
  {
    "type": 0,
    "typeName": "单选题",
    "level": 0,
    "levelName": "简单",
    "content": "二进制数 1010 转换为十进制是多少？",
    "analysis": "二进制转十进制：1×2³ + 0×2² + 1×2¹ + 0×2⁰ = 8 + 0 + 2 + 0 = 10",
    "subAnswer": null,
    "options": [
      { "content": "8", "isRight": false, "analysis": "计算错误，遗漏了 2¹ 位" },
      { "content": "10", "isRight": true, "analysis": null },
      { "content": "12", "isRight": false, "analysis": "计算错误，将 2³ 算成了 8" },
      { "content": "14", "isRight": false, "analysis": "计算错误，多加了 2² 位" }
    ]
  },
  {
    "type": 0,
    "typeName": "单选题",
    "level": 0,
    "levelName": "简单",
    "content": "冯·诺依曼结构计算机的核心思想是什么？",
    "analysis": "存储程序是冯·诺依曼结构的核心特征，程序和数据以二进制形式预先存入存储器。",
    "subAnswer": null,
    "options": [
      { "content": "存储程序", "isRight": true, "analysis": null },
      { "content": "并行处理", "isRight": false, "analysis": "并行处理不是冯·诺依曼结构的特征" },
      { "content": "分布式计算", "isRight": false, "analysis": "分布式计算是后来的发展" },
      { "content": "神经网络计算", "isRight": false, "analysis": "神经网络不属于冯·诺依曼体系" }
    ]
  },
  {
    "type": 2,
    "typeName": "判断题",
    "level": 0,
    "levelName": "简单",
    "content": "二进制数系统中只有 0 和 1 两个数字。",
    "analysis": "二进制确实只使用 0 和 1 两个数码，这是二进制的基本定义。",
    "subAnswer": null,
    "options": [
      { "content": "正确", "isRight": true, "analysis": null },
      { "content": "错误", "isRight": false, "analysis": "二进制确实只有 0 和 1 两个数字" }
    ]
  },
  {
    "type": 2,
    "typeName": "判断题",
    "level": 0,
    "levelName": "简单",
    "content": "冯·诺依曼结构计算机中，程序和数据分开存储在不同的存储器中。",
    "analysis": "冯·诺依曼结构中程序和数据以相同方式存储在同一存储器中，这是存储程序思想的核心。",
    "subAnswer": null,
    "options": [
      { "content": "正确", "isRight": false, "analysis": "冯·诺依曼结构中程序和数据存储在同一存储器中" },
      { "content": "错误", "isRight": true, "analysis": null }
    ]
  }
]
"""


def test_step1_text_preprocessing():
    """步骤1：文本预处理"""
    print("\n" + "=" * 60)
    print("步骤 1：文本预处理")
    print("=" * 60)

    raw_text = """
    二进制是计算机的基础。二进制数只有 0 和 1 两个数字。

    二进制转十进制：每一位乘以 2 的幂次再求和。

    冯诺依曼结构计算机由五大部件组成：运算器、控制器、存储器、输入设备、输出设备。
    """

    cleaned = clean(raw_text)
    print(f"  原始字符数: {len(raw_text)}")
    print(f"  清洗后字符数: {len(cleaned)}")

    processed = process(cleaned, max_tokens=8000)
    tokens = estimate_tokens(processed)
    print(f"  处理后字符数: {len(processed)}")
    print(f"  Token 数: {tokens}")
    print("  [OK] 文本预处理通过")

    return processed


def test_step2_prompt_building(text: str):
    """步骤2：Prompt 构建"""
    print("\n" + "=" * 60)
    print("步骤 2：Prompt 构建")
    print("=" * 60)

    # 测试加载模板
    templates = load_template()
    assert "system" in templates, "缺少 system prompt"
    assert "single_choice" in templates, "缺少 single_choice 模板"
    assert "multi_choice" in templates, "缺少 multi_choice 模板"
    assert "true_false" in templates, "缺少 true_false 模板"
    assert "essay" in templates, "缺少 essay 模板"
    print(f"  [OK] 模板加载成功: 5 个模板")

    # 测试构建单选题 messages
    msgs = build_messages(
        text=text,
        question_type=0,  # 单选
        count=2,
        level=0,
        level_name="简单",
        requirements="侧重基础概念",
    )
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "{count}" not in msgs[1]["content"], "变量替换未完成"
    print(f"  [OK] 单选题 messages 构建成功")
    print(f"     system prompt: {len(msgs[0]['content'])} 字符")
    print(f"     user prompt: {len(msgs[1]['content'])} 字符")

    # 测试判断题
    msgs2 = build_messages(text, 2, 2, 1, "困难", "")
    assert msgs2[1]["role"] == "user"
    print(f"  [OK] 判断题 messages 构建成功")

    # 测试简答题
    msgs3 = build_messages(text, 3, 1, 0, "简单", "")
    assert msgs3[1]["role"] == "user"
    print(f"  [OK] 简答题 messages 构建成功")

    return msgs


def test_step3_json_validation():
    """步骤3：JSON 校验"""
    print("\n" + "=" * 60)
    print("步骤 3：JSON 校验（模拟 LLM 响应）")
    print("=" * 60)

    # 使用模拟 LLM 响应
    questions, errors = validate(MOCK_LLM_RESPONSE)
    assert len(questions) == 4, f"期望 4 道题，实际 {len(questions)} 道"
    assert not errors, f"期望无错误，实际: {errors}"
    print(f"  [OK] 校验通过: {len(questions)} 道题")

    for i, q in enumerate(questions):
        assert isinstance(q, Question)
        assert q.type in [0, 1, 2, 3]
        assert q.content
        assert q.analysis
        assert q.typeName in QUESTION_TYPE_NAMES.values()
        assert q.levelName in DIFFICULTY_NAMES.values()

        if q.type in [0, 1, 2]:  # 选择题/判断题
            assert len(q.options) >= 2
            # 验证恰好一个正确答案（单选/判断）
            if q.type in [0, 2]:
                right_count = sum(1 for o in q.options if o.isRight)
                assert right_count == 1, f"单选/判断题应有恰好 1 个正确答案，实际 {right_count}"
            # 验证错误选项有解析
            for opt in q.options:
                if not opt.isRight:
                    assert opt.analysis, f"错误选项缺少 analysis: {opt.content}"
        elif q.type == 3:  # 简答题
            assert q.options == []
            assert q.subAnswer

        print(f"  [{i+1}] {q.typeName} | {q.levelName} | {q.content[:50]}...")

    print("  [OK] 所有试题格式校验通过")

    return questions


def test_step4_response_assembly(questions):
    """步骤4：响应组装"""
    print("\n" + "=" * 60)
    print("步骤 4：响应组装（同事格式）")
    print("=" * 60)

    bank = SubjectBank(
        name="计算机基础测试",
        remark="验证完整流程",
        questions=questions,
    )

    resp = GenerateResponse(
        success=True,
        subjectBanks=[bank],
    )

    output = resp.model_dump_json(indent=2)
    print(f"  [OK] 响应组装成功")
    print(f"     题库名: {bank.name}")
    print(f"     试题数: {len(bank.questions)}")
    print(f"     JSON 长度: {len(output)} 字符")

    # 验证 JSON 可被解析回 Python
    parsed = json.loads(output)
    assert parsed["success"] is True
    assert len(parsed["subjectBanks"]) == 1
    assert len(parsed["subjectBanks"][0]["questions"]) == 4
    print("  [OK] JSON 反序列化验证通过")

    # 输出完整 JSON
    print("\n[OUTPUT] 完整输出：")
    print(output)

    return resp


def test_step5_request_model():
    """步骤5：请求模型验证"""
    print("\n" + "=" * 60)
    print("步骤 5：请求模型验证")
    print("=" * 60)

    req = GenerateRequest(
        subject_bank_name="计算机基础第一章",
        subject_bank_remark="覆盖二进制、冯诺依曼结构",
        document_text="二进制转换...",
        requirements="侧重基础概念",
        question_types=[0, 2],
        count_per_type=5,
        difficulty=0,
    )

    # 序列化
    req_json = req.model_dump_json(indent=2)
    print(f"  [OK] 请求序列化: {len(req_json)} 字符")

    # 反序列化
    req2 = GenerateRequest.model_validate_json(req_json)
    assert req2.subject_bank_name == req.subject_bank_name
    assert req2.question_types == [0, 2]
    assert req2.count_per_type == 5
    print(f"  [OK] 请求反序列化验证通过")

    # 验证默认值
    req3 = GenerateRequest(document_text="test")
    assert req3.subject_bank_name == "默认题库"
    assert req3.count_per_type == 5
    assert req3.difficulty == 0
    print(f"  [OK] 默认值验证通过")


def main():
    print("[TEST] 试题生成助手 - 完整流程验证（模拟模式）")
    print("=" * 60)

    # 步骤 1
    text = test_step1_text_preprocessing()

    # 步骤 2
    test_step2_prompt_building(text)

    # 步骤 3
    questions = test_step3_json_validation()

    # 步骤 4
    resp = test_step4_response_assembly(questions)

    # 步骤 5
    test_step5_request_model()

    # 总结
    print("\n" + "=" * 60)
    print("[SUCCESS] 全部 5 个步骤验证通过！")
    print("=" * 60)
    print(f"""
    验证清单:
    [OK] 步骤 1: 文本预处理（清洗 + token 估算）
    [OK] 步骤 2: Prompt 构建（YAML 模板加载 + 变量替换）
    [OK] 步骤 3: JSON 校验（提取 + Pydantic 校验 + 同事格式）
    [OK] 步骤 4: 响应组装（subjectBanks 外层包裹）
    [OK] 步骤 5: 请求模型（序列化 + 反序列化 + 默认值）

    下一步：配置 .env 中的 DEEPSEEK_API_KEY，运行 playground/prompt_test.py
    测试真实 LLM 生成效果。
    """)


if __name__ == "__main__":
    main()
