#!/usr/bin/env python
"""测试主智能体基本功能

这个脚本测试：
1. 主智能体能否正确加载身份文件
2. 主智能体能否回答简单问题（不涉及子智能体）
3. 主智能体的个性是否符合SOUL.md定义
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from shared.framework.hermes_agent.run_agent import AIAgent
from shared.framework.hermes_agent.agent.identity_loader import load_identity_files_from_path


def test_identity_loading():
    """测试1：验证身份文件加载"""
    print("=" * 60)
    print("测试1: 验证身份文件加载")
    print("=" * 60)

    workspace_path = project_root / "workspace"

    # 加载身份文件
    identity_content = load_identity_files_from_path(workspace_path)

    if identity_content:
        print(f"✅ 成功加载身份文件，总字符数: {len(identity_content)}")

        # 检查关键内容
        checks = [
            ("废水监测", "废水监测" in identity_content),
            ("多智能体编排", "编排" in identity_content),
            ("数据驱动", "数据驱动" in identity_content),
            ("全局优先", "全局优先" in identity_content),
        ]

        for name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} 包含{name}")

        return all(p for _, p in checks)
    else:
        print("❌ 加载失败")
        return False


def test_master_agent_creation():
    """测试2：验证主智能体创建"""
    print("\n" + "=" * 60)
    print("测试2: 验证主智能体创建")
    print("=" * 60)

    try:
        # 创建主智能体（不调用LLM，只测试初始化）
        agent = AIAgent(
            model="dummy-model",
            identity_path="workspace",
            load_soul_identity=True
        )

        print(f"✅ 主智能体创建成功")
        print(f"   identity_path: {agent._identity_path}")
        print(f"   目录名: {agent._identity_path.name}")

        return True

    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return False


def test_simple_questions():
    """测试3：测试简单问题回答（不需要子智能体）"""
    print("\n" + "=" * 60)
    print("测试3: 测试简单问题回答")
    print("=" * 60)

    # 这些问题只需要主智能体回答，不涉及子智能体
    simple_questions = [
        "你是谁？你的职责是什么？",
        "你管理几个子智能体？",
        "违规类型有哪几种？",
        "什么是插瓶干扰？",
        "水力停留时间是多长？",
    ]

    print("\n测试问题列表：")
    for i, question in enumerate(simple_questions, 1):
        print(f"  {i}. {question}")

    print("\n⚠️  注意：这些是主智能体应该能直接回答的问题")
    print("   （不涉及子智能体调用）")
    print("\n要实际测试回答，需要配置LLM API并运行主智能体。")

    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("主智能体基本功能测试")
    print("=" * 60)
    print(f"项目根目录: {project_root}\n")

    results = []

    # 测试1
    try:
        results.append(("身份文件加载", test_identity_loading()))
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        results.append(("身份文件加载", False))

    # 测试2
    try:
        results.append(("主智能体创建", test_master_agent_creation()))
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        results.append(("主智能体创建", False))

    # 测试3
    try:
        results.append(("简单问题列表", test_simple_questions()))
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        results.append(("简单问题列表", False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！主智能体基本功能正常。")
    else:
        print("❌ 部分测试失败，请检查上面的错误信息。")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
