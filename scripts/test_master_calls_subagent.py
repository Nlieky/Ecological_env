#!/usr/bin/env python
"""测试主智能体调用子智能体

验证主智能体能否正确调用子智能体并获取结果
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))


def test_subagent_tools():
    """测试子智能体工具"""
    print("=" * 70)
    print("测试1: 子智能体工具函数")
    print("=" * 70)

    try:
        # 直接从文件路径导入
        import importlib.util

        tools_path = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "subagent_tools.py"
        spec = importlib.util.spec_from_file_location("subagent_tools", tools_path)
        subagent_tools = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(tools_path.parent))
        spec.loader.exec_module(subagent_tools)

        initialize_subagents = subagent_tools.initialize_subagents
        list_available_subagents = subagent_tools.list_available_subagents
        get_subagent_info = subagent_tools.get_subagent_info
        shutdown_subagents = subagent_tools.shutdown_subagents

        # 获取LLM配置
        model = os.getenv("LLM_MODEL", "LongCat-2.0")
        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            print("[FAIL] 未配置 LLM_API_KEY，跳过测试")
            return False

        print(f"\n配置信息:")
        print(f"  模型: {model}")
        print(f"  API: {base_url}")

        # 1. 初始化子智能体
        print("\n1. 初始化子智能体...")
        init_result = initialize_subagents(model=model, base_url=base_url, api_key=api_key)

        if init_result.get("success"):
            print(f"[PASS] 初始化成功: {init_result.get('count')} 个子智能体")
            print(f"   子智能体列表: {init_result.get('subagents')}")
        else:
            print(f"[FAIL] 初始化失败: {init_result.get('error')}")
            return False

        # 2. 列出可用子智能体
        print("\n2. 列出可用子智能体...")
        list_result = list_available_subagents()

        if list_result.get("success"):
            print(f"[PASS] 可用子智能体: {list_result.get('subagents')}")
        else:
            print(f"[FAIL] 列出失败: {list_result.get('error')}")

        # 3. 获取子智能体信息
        print("\n3. 获取子智能体信息...")
        for subagent_name in list_result.get("subagents", []):
            info_result = get_subagent_info(subagent_name)
            if info_result.get("success"):
                print(f"   [{subagent_name}]")
                print(f"   描述: {info_result.get('description')}")
                print(f"   可用: {info_result.get('available')}")
            else:
                print(f"   [FAIL] 获取信息失败: {info_result.get('error')}")

        # 4. 关闭子智能体
        print("\n4. 关闭子智能体...")
        shutdown_result = shutdown_subagents()
        if shutdown_result.get("success"):
            print("[PASS] 子智能体已关闭")
        else:
            print(f"[FAIL] 关闭失败: {shutdown_result.get('error')}")

        return True

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_call_subagent():
    """测试调用子智能体"""
    print("\n" + "=" * 70)
    print("测试2: 调用子智能体执行任务")
    print("=" * 70)

    try:
        # 直接从文件路径导入
        import importlib.util

        tools_path = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "subagent_tools.py"
        spec = importlib.util.spec_from_file_location("subagent_tools", tools_path)
        subagent_tools = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(tools_path.parent))
        spec.loader.exec_module(subagent_tools)

        initialize_subagents = subagent_tools.initialize_subagents
        call_subagent = subagent_tools.call_subagent
        shutdown_subagents = subagent_tools.shutdown_subagents

        # 获取LLM配置
        model = os.getenv("LLM_MODEL", "LongCat-2.0")
        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            print("[FAIL] 未配置 LLM_API_KEY，跳过测试")
            return False

        # 初始化子智能体
        print("\n1. 初始化子智能体...")
        init_result = initialize_subagents(model=model, base_url=base_url, api_key=api_key)

        if not init_result.get("success"):
            print(f"[FAIL] 初始化失败: {init_result.get('error')}")
            return False

        print(f"[PASS] 初始化成功: {init_result.get('count')} 个子智能体")

        # 测试调用异常检测子智能体
        print("\n2. 调用异常检测子智能体...")
        test_task = "请介绍一下你的职责和你能检测哪些异常类型？"

        call_result = call_subagent(
            subagent_name="anomaly-detection-agent",
            task=test_task
        )

        if call_result.get("success"):
            print(f"[PASS] 调用成功")
            print(f"\n子智能体回答:")
            print(f"{'-' * 70}")
            print(call_result.get("result", ""))
            print(f"{'-' * 70}")
        else:
            print(f"[FAIL] 调用失败: {call_result.get('error')}")

        # 关闭子智能体
        print("\n3. 关闭子智能体...")
        shutdown_subagents()

        return call_result.get("success")

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_master_agent_with_subagent_tools():
    """测试主智能体使用子智能体工具"""
    print("\n" + "=" * 70)
    print("测试3: 主智能体使用子智能体工具")
    print("=" * 70)

    try:
        from shared.framework.hermes_agent.run_agent import AIAgent

        # 获取LLM配置
        model = os.getenv("LLM_MODEL", "LongCat-2.0")
        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            print("[FAIL] 未配置 LLM_API_KEY，跳过测试")
            return False

        print(f"\n配置信息:")
        print(f"  模型: {model}")
        print(f"  API: {base_url}")

        # 创建主智能体
        print("\n1. 创建主智能体...")
        master_agent = AIAgent(
            model=model,
            base_url=base_url,
            api_key=api_key,
            identity_path="workspace",
            load_soul_identity=True
        )

        print("[PASS] 主智能体创建成功")

        # 测试问题
        test_question = "请使用 call_subagent 工具调用异常检测子智能体，询问它能检测哪些异常类型？"

        print(f"\n2. 向主智能体提问...")
        print(f"问题: {test_question}")

        result = master_agent.run_conversation(test_question)

        if isinstance(result, dict):
            answer = result.get("final_response", str(result))
        else:
            answer = str(result)

        print(f"\n主智能体回答:")
        print(f"{'-' * 70}")
        print(answer)
        print(f"{'-' * 70}")

        return True

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行测试"""
    print("\n" + "=" * 70)
    print("主智能体调用子智能体集成测试")
    print("=" * 70)
    print(f"项目根目录: {project_root}\n")

    results = {}

    # 测试1: 子智能体工具函数
    results["工具函数"] = test_subagent_tools()

    # 测试2: 调用子智能体
    results["调用子智能体"] = test_call_subagent()

    # 测试3: 主智能体使用工具
    results["主智能体使用工具"] = test_master_agent_with_subagent_tools()

    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "[PASS] 通过" if passed else "[FAIL] 失败"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n总计: {passed}/{total} 通过")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
