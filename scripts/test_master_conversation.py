#!/usr/bin/env python
"""测试主智能体对话功能

实际测试主智能体回答问题（需要配置LLM API）
"""

import os
import sys
from pathlib import Path

# 加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from shared.framework.hermes_agent.run_agent import AIAgent


def test_conversation():
    """测试主智能体对话"""
    print("=" * 60)
    print("主智能体对话测试")
    print("=" * 60)

    # 从环境变量获取配置
    model = os.getenv("LLM_MODEL", "LongCat-2.0")
    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        print("❌ 未配置LLM_API_KEY，请检查.env文件")
        return False

    print(f"\n配置信息:")
    print(f"  模型: {model}")
    print(f"  API: {base_url}")

    try:
        # 创建主智能体
        print("\n正在创建主智能体...")
        agent = AIAgent(
            model=model,
            base_url=base_url,
            api_key=api_key,
            identity_path="workspace",
            load_soul_identity=True
        )

        # 临时修复：初始化缺失的属性
        if not hasattr(agent, '_session_db_created'):
            agent._session_db_created = False
        if not hasattr(agent, '_session_db'):
            agent._session_db = None

        print("✅ 主智能体创建成功\n")

        # 测试问题列表
        questions = [
            "你是谁？你的职责是什么？",
            "你管理几个子智能体？分别是什么？",
            "违规类型有哪几种？",
            "什么是插瓶干扰？",
        ]

        for i, question in enumerate(questions, 1):
            print(f"\n{'='*60}")
            print(f"问题 {i}: {question}")
            print(f"{'='*60}")

            try:
                # 调用主智能体
                result = agent.run_conversation(question)

                # 提取回答
                if isinstance(result, dict):
                    answer = result.get("final_response", str(result))
                else:
                    answer = str(result)

                print(f"\n回答:\n{answer}")

            except Exception as e:
                print(f"\n❌ 回答失败: {e}")
                break

        print(f"\n{'='*60}")
        print("测试完成")
        print(f"{'='*60}\n")

        return True

    except Exception as e:
        print(f"❌ 创建主智能体失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("主智能体对话功能测试")
    print("=" * 60)
    print(f"项目根目录: {project_root}\n")

    success = test_conversation()

    if success:
        print("✅ 对话测试成功完成！")
        return 0
    else:
        print("❌ 对话测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
