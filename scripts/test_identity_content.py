#!/usr/bin/env python
"""测试主智能体身份文件内容

验证身份文件是否包含正确的信息
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from shared.framework.hermes_agent.agent.identity_loader import (
    load_identity_files_from_path,
    load_single_identity_file
)


def test_identity_content():
    """测试身份文件内容"""
    print("=" * 60)
    print("主智能体身份文件内容验证")
    print("=" * 60)

    workspace_path = project_root / "workspace"

    # 测试1：SOUL.md应该包含的核心内容
    print("\n测试1: SOUL.md 核心内容")
    soul_content = load_single_identity_file(workspace_path, "SOUL.md")

    soul_checks = [
        ("核心原则", "Core Truths" in soul_content),
        ("主智能体角色", "Master Agent" in soul_content),
        ("全局优先", "全局优先" in soul_content or "Global First" in soul_content),
        ("数据驱动", "数据驱动" in soul_content or "Data Driven" in soul_content),
        ("及时响应", "及时响应" in soul_content or "Timely Response" in soul_content),
    ]

    for name, passed in soul_checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    # 测试2：AGENTS.md应该包含的核心内容
    print("\n测试2: AGENTS.md 核心内容")
    agents_content = load_single_identity_file(workspace_path, "AGENTS.md")

    agents_checks = [
        ("工作区规范", "Your Workspace" in agents_content or "工作区规范" in agents_content),
        ("内存管理", "Memory" in agents_content),
        ("红线", "Red Lines" in agents_content or "红线" in agents_content),
        ("子智能体列表", "子智能体" in agents_content or "Sub-Agent" in agents_content),
    ]

    for name, passed in agents_checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    # 测试3：MEMORY.md应该包含的核心内容
    print("\n测试3: MEMORY.md 核心内容")
    memory_content = load_single_identity_file(workspace_path, "MEMORY.md")

    memory_checks = [
        ("监测指标", "监测指标" in memory_content),
        ("违规类型", "违规类型" in memory_content),
        ("插瓶干扰", "插瓶干扰" in memory_content),
        ("水力停留时间", "水力停留时间" in memory_content),
    ]

    for name, passed in memory_checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    # 测试4：IDENTITY.md应该包含的核心内容
    print("\n测试4: IDENTITY.md 核心内容")
    identity_content = load_single_identity_file(workspace_path, "IDENTITY.md")

    identity_checks = [
        ("名称", "废水监测主智能体" in identity_content),
        ("核心价值", "核心价值" in identity_content),
        ("子智能体管理", "管理的子智能体" in identity_content),
    ]

    for name, passed in identity_checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    # 汇总结果
    all_checks = soul_checks + agents_checks + memory_checks + identity_checks
    passed_count = sum(1 for _, p in all_checks if p)
    total_count = len(all_checks)

    print("\n" + "=" * 60)
    print(f"验证结果: {passed_count}/{total_count} 通过")
    print("=" * 60)

    if passed_count == total_count:
        print("[PASS] 所有验证通过！身份文件内容正确。")
        return True
    else:
        print("[FAIL] 部分验证失败，请检查上面的错误信息。")
        return False


def test_sample_questions():
    """测试示例问题和预期答案"""
    print("\n" + "=" * 60)
    print("示例问题与预期答案")
    print("=" * 60)

    workspace_path = project_root / "workspace"
    memory_content = load_single_identity_file(workspace_path, "MEMORY.md")

    questions_and_answers = [
        ("违规类型有哪几种？", ["插瓶干扰", "稀释排放", "人工拟合", "恶意逃避"]),
        ("水力停留时间是多长？", ["4-5.5", "小时"]),
    ]

    for question, keywords in questions_and_answers:
        print(f"\n问题: {question}")
        print("预期答案关键词:", ", ".join(keywords))

        found = all(kw in memory_content for kw in keywords)
        status = "[PASS]" if found else "[FAIL]"
        print(f"{status} 可以从MEMORY.md中找到答案")


def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("主智能体身份文件内容验证")
    print("=" * 60)
    print(f"项目根目录: {project_root}\n")

    success = test_identity_content()
    test_sample_questions()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
