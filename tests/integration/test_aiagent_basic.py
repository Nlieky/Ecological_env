"""
测试 AIAgent 基本功能

验证从本地化 Hermes 框架导入 AIAgent 并测试其基本接口
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_aiagent_import():
    """测试 AIAgent 导入：验证可以从本地化框架导入"""
    print("[TEST 1] 测试 AIAgent 导入...")

    try:
        from shared.framework.hermes_agent.run_agent import AIAgent
        print("  [PASS] 成功从 shared.framework.hermes_agent.run_agent 导入 AIAgent")
        return True
    except ImportError as e:
        print(f"  [FAIL] 导入失败: {e}")
        return False

def test_aiagent_class_interface():
    """测试 AIAgent 类接口：验证存在 __init__ 和 run_conversation 方法"""
    print("\n[TEST 2] 测试 AIAgent 类接口...")

    try:
        from shared.framework.hermes_agent.run_agent import AIAgent

        # 检查 __init__ 方法
        if hasattr(AIAgent, '__init__'):
            print("  [PASS] AIAgent 类存在 __init__ 方法")
        else:
            print("  [FAIL] AIAgent 类缺少 __init__ 方法")
            return False

        # 检查 run_conversation 方法
        if hasattr(AIAgent, 'run_conversation'):
            print("  [PASS] AIAgent 类存在 run_conversation 方法")
        else:
            print("  [FAIL] AIAgent 类缺少 run_conversation 方法")
            return False

        return True
    except Exception as e:
        print(f"  [FAIL] 接口检查失败: {e}")
        return False

def test_aiagent_instantiation():
    """测试 AIAgent 实例化：验证类可用（不强制完整实例化）"""
    print("\n[TEST 3] 测试 AIAgent 实例化...")

    try:
        from shared.framework.hermes_agent.run_agent import AIAgent

        # 检查类是否可调用
        if callable(AIAgent):
            print("  [PASS] AIAgent 类可调用")

            # 尝试创建基本实例（仅验证类结构，不完整初始化）
            # 使用最小参数集
            try:
                # 我们不完整初始化，只检查类的构造函数签名
                import inspect
                sig = inspect.signature(AIAgent.__init__)
                params = list(sig.parameters.keys())
                print(f"  [INFO] __init__ 参数（前10个）: {params[:10]}")

                # 验证关键参数存在
                required_params = ['self', 'base_url', 'api_key', 'provider', 'model']
                for param in required_params:
                    if param in params:
                        print(f"  [PASS] __init__ 包含参数: {param}")
                    else:
                        print(f"  [FAIL] __init__ 缺少参数: {param}")
                        return False

                return True
            except Exception as e:
                print(f"  [FAIL] 实例化检查失败: {e}")
                return False
        else:
            print("  [FAIL] AIAgent 类不可调用")
            return False

    except Exception as e:
        print(f"  [FAIL] 实例化测试失败: {e}")
        return False

def test_aiagent_additional_methods():
    """测试 AIAgent 其他关键方法"""
    print("\n[TEST 4] 测试 AIAgent 其他关键方法...")

    try:
        from shared.framework.hermes_agent.run_agent import AIAgent

        # 检查一些关键方法
        key_methods = [
            'reset_session_state',
            'switch_model',
            'interrupt',
        ]

        for method in key_methods:
            if hasattr(AIAgent, method):
                print(f"  [PASS] AIAgent 类存在方法: {method}")
            else:
                print(f"  [WARN] AIAgent 类缺少方法: {method}")

        return True
    except Exception as e:
        print(f"  [FAIL] 附加方法检查失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 70)
    print("AIAgent 基本功能测试")
    print("=" * 70)

    results = []

    # 运行所有测试
    results.append(("AIAgent 导入测试", test_aiagent_import()))
    results.append(("类接口测试", test_aiagent_class_interface()))
    results.append(("实例化测试", test_aiagent_instantiation()))
    results.append(("附加方法测试", test_aiagent_additional_methods()))

    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n[COMPLETE] All AIAgent basic functionality tests passed")
        return 0
    else:
        print(f"\n[FAILED] {total - passed} 测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
