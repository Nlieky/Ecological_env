#!/usr/bin/env python
"""验证子智能体是否被底层框架正确加载

这个脚本演示：
1. 每个子智能体可以接受identity_path参数
2. 子智能体从各自的subagents/*/加载身份文件
3. SubagentManager可以创建所有子智能体
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from shared.framework.hermes_agent.agent.identity_loader import (
    load_single_identity_file,
    resolve_identity_path
)
from shared.framework.hermes_agent.run_agent import AIAgent


SUBAGENTS = [
    "multi-dimensional-data-perception-agent",
    "anomaly-detection-agent",
    "rule-reasoning-agent",
    "disposition-execution-agent"
]


def test_subagent_identity_files():
    """测试1：验证每个子智能体都有身份文件"""
    print("=" * 60)
    print("测试1: 验证每个子智能体都有身份文件")
    print("=" * 60)

    all_found = True
    for subagent_name in SUBAGENTS:
        subagent_path = project_root / "subagents" / subagent_name
        print(f"\n📂 {subagent_name}:")
        print(f"   路径: {subagent_path}")

        if not subagent_path.exists():
            print(f"   ❌ 目录不存在")
            all_found = False
            continue

        # 检查SOUL.md
        soul_path = subagent_path / "SOUL.md"
        if soul_path.exists():
            soul_content = load_single_identity_file(subagent_path, "SOUL.md")
            print(f"   ✅ SOUL.md: {len(soul_content)} 字符")
            preview = soul_content[:100] + "..." if len(soul_content) > 100 else soul_content
            print(f"      预览: {preview}")
        else:
            print(f"   ⚠️  SOUL.md: 未找到")

    return all_found


def test_subagent_path_resolution():
    """测试2：验证子智能体路径解析正确"""
    print("\n" + "=" * 60)
    print("测试2: 验证子智能体路径解析正确")
    print("=" * 60)

    all_correct = True
    for subagent_name in SUBAGENTS:
        # 构建相对路径
        relative_path = f"subagents/{subagent_name}"
        resolved = resolve_identity_path(relative_path, project_root)

        print(f"\n{subagent_name}:")
        print(f"  相对路径: {relative_path}")
        print(f"  解析后: {resolved}")
        print(f"  存在: {resolved.exists()}")

        if not resolved.exists():
            all_correct = False

    return all_correct


def test_subagent_ai_agent_creation():
    """测试3：验证可以为每个子智能体创建AIAgent实例"""
    print("\n" + "=" * 60)
    print("测试3: 验证可以为每个子智能体创建AIAgent实例")
    print("=" * 60)

    all_created = True
    agents = {}

    for subagent_name in SUBAGENTS:
        relative_path = f"subagents/{subagent_name}"
        print(f"\n{subagent_name}:")

        try:
            agent = AIAgent(
                model="dummy-model",
                identity_path=relative_path,
                load_soul_identity=True
            )

            print(f"  ✅ AIAgent创建成功")
            print(f"     identity_path: {agent._identity_path}")
            print(f"     目录名: {agent._identity_path.name}")

            agents[subagent_name] = agent

        except Exception as e:
            print(f"  ❌ 创建失败: {e}")
            all_created = False

    return all_created


def test_subagent_manager():
    """测试4：验证SubagentManager可以创建所有子智能体"""
    print("\n" + "=" * 60)
    print("测试4: 验证SubagentManager可以创建所有子智能体")
    print("=" * 60)

    try:
        # 导入SubagentManager - 处理路径中的连字符
        import sys
        subagent_scripts_path = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"
        if str(subagent_scripts_path) not in sys.path:
            sys.path.insert(0, str(subagent_scripts_path))

        from subagent_manager import SubagentManager

        manager = SubagentManager(project_root=project_root)

        print(f"\n✅ SubagentManager创建成功")
        print(f"   配置的子智能体数量: {len(SubagentManager.SUBAGENT_CONFIGS)}")

        print(f"\n子智能体配置:")
        for name, config in SubagentManager.SUBAGENT_CONFIGS.items():
            print(f"  - {name}:")
            print(f"    描述: {config.get('description', 'N/A')}")
            print(f"    路径: {config.get('identity_path', 'N/A')}")

        print(f"\n尝试创建子智能体实例...")

        # 尝试创建所有子智能体（但不实际调用LLM）
        manager.create_subagents(
            model="dummy-model",
            base_url="http://dummy",
            api_key="dummy-key"
        )

        print(f"✅ 成功创建 {len(manager.subagents)} 个子智能体")

        for name in manager.list_subagents():
            subagent = manager.get_subagent(name)
            if subagent:
                print(f"  - {name}: identity_path={subagent._identity_path}")

        return True

    except Exception as e:
        print(f"❌ SubagentManager测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有子智能体验证测试"""
    print("\n" + "=" * 60)
    print("子智能体加载验证")
    print("=" * 60)
    print(f"项目根目录: {project_root}\n")

    results = []

    # 测试1
    try:
        results.append(("子智能体身份文件", test_subagent_identity_files()))
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        results.append(("子智能体身份文件", False))

    # 测试2
    try:
        results.append(("子智能体路径解析", test_subagent_path_resolution()))
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        results.append(("子智能体路径解析", False))

    # 测试3
    try:
        results.append(("子智能体AIAgent创建", test_subagent_ai_agent_creation()))
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        results.append(("子智能体AIAgent创建", False))

    # 测试4
    try:
        results.append(("SubagentManager", test_subagent_manager()))
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        results.append(("SubagentManager", False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！子智能体已被底层框架正确加载。")
    else:
        print("❌ 部分测试失败，请检查上面的错误信息。")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
