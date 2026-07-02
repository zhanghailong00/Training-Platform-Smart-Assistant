"""
Prompt 调试脚本 — 不依赖 Web 服务，直接测试 Prompt 效果。

使用方法：
    cd test_question_generator
    python playground/prompt_test.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.request import GenerateRequest
from services.exam_service import generate_questions


def test_single_choice():
    """测试单选题生成"""
    print("\n" + "=" * 60)
    print("测试：单选题生成")
    print("=" * 60)

    req = GenerateRequest(
        subject_bank_name="测试题库",
        subject_bank_remark="Prompt 调试测试",
        document_text="""
        二进制是计算机的基础。二进制数只有 0 和 1 两个数字。
        二进制转十进制：每一位乘以 2 的幂次再求和。
        例如：1010₂ = 1×2³ + 0×2² + 1×2¹ + 0×2⁰ = 8 + 0 + 2 + 0 = 10₁₀

        冯诺依曼结构计算机由五大部件组成：运算器、控制器、存储器、输入设备、输出设备。
        运算器负责算术和逻辑运算。控制器负责控制指令执行顺序。
        存储器存储程序和数据。输入设备向计算机输入数据。输出设备将计算结果输出。

        存储程序思想是冯诺依曼结构的核心：程序和数据以二进制形式预先存入存储器。
        """,
        requirements="侧重基础概念理解",
        question_types=[0],  # 只测单选
        count_per_type=2,
        difficulty=0,
    )

    resp = generate_questions(req)
    print(resp.model_dump_json(indent=2))

    if resp.success:
        print(f"\n✅ 成功生成 {len(resp.subjectBanks[0].questions)} 道题")
    else:
        print(f"\n❌ 生成失败: {resp.error}")


def test_text_input():
    """测试纯文本输入（不传文件）"""
    print("\n" + "=" * 60)
    print("测试：纯文本输入")
    print("=" * 60)

    req = GenerateRequest(
        subject_bank_name="计算机网络基础",
        document_text="""
        TCP 是面向连接的传输层协议，提供可靠的数据传输。
        UDP 是无连接的传输层协议，不保证可靠传输。
        TCP 通过三次握手建立连接，通过四次挥手释放连接。
        IP 地址分为 IPv4 和 IPv6，IPv4 地址长度为 32 位。
        """,
        requirements="出 2 道单选和 2 道判断",
        question_types=[0, 2],
        count_per_type=2,
        difficulty=0,
    )

    resp = generate_questions(req)
    print(resp.model_dump_json(indent=2))

    if resp.success:
        bank = resp.subjectBanks[0]
        print(f"\n✅ 成功！题库「{bank.name}」共 {len(bank.questions)} 道题")
        for q in bank.questions:
            print(f"  [{q.typeName}] {q.content[:50]}...")
    else:
        print(f"\n❌ 失败: {resp.error}")


if __name__ == "__main__":
    print("🧪 试题生成助手 — Prompt 调试工具")
    print("注意：请确保已配置 .env 文件中的 DEEPSEEK_API_KEY")

    try:
        test_single_choice()
    except Exception as e:
        print(f"\n❌ 单选题测试异常: {e}")

    try:
        test_text_input()
    except Exception as e:
        print(f"\n❌ 文本输入测试异常: {e}")
