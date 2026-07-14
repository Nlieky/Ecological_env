#!/usr/bin/env python
"""测试子智能体身份文件内容

验证所有子智能体的身份文件是否包含正确的信息
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from shared.framework.hermes_agent.agent.identity_loader import (
    load_single_identity_file
)


# 4个子智能体
SUBAGENTS = [
    {
        "name": "multi-dimensional-data-perception-agent",
        "display_name": "多维数据感知子智能体",
        "path": project_root / "subagents" / "multi-dimensional-data-perception-agent"
    },
    {
        "name": "anomaly-detection-agent",
        "display_name": "异常检测子智能体",
        "path": project_root / "subagents" / "anomaly-detection-agent"
    },
    {
        "name": "rule-reasoning-agent",
        "display_name": "规则推理子智能体",
        "path": project_root / "subagents" / "rule-reasoning-agent"
    },
    {
        "name": "disposition-execution-agent",
        "display_name": "研判预警与处置执行子智能体",
        "path": project_root / "subagents" / "disposition-execution-agent"
    }
]


def test_subagent_files_exist():
    """测试子智能体身份文件是否存在"""
    print("=" * 70)
    print("子智能体身份文件存在性检查")
    print("=" * 70)

    all_exist = True
    for subagent in SUBAGENTS:
        print(f"\n{subagent['display_name']} ({subagent['name']})")
        path = subagent['path']

        for file_name in ["SOUL.md", "AGENTS.md", "MEMORY.md"]:
            file_path = path / file_name
            exists = file_path.exists()
            status = "[PASS]" if exists else "[FAIL]"
            print(f"  {status} {file_name}: {file_path}")

            if not exists:
                all_exist = False

    return all_exist


def test_soul_content(subagent):
    """测试SOUL.md内容"""
    path = subagent['path']
    content = load_single_identity_file(path, "SOUL.md")

    checks = []

    # 核心原则检查
    checks.append(("Core Truths", "Core Truths" in content))

    # 角色检查
    checks.append(("子智能体角色", "Sub-Agent" in content or "子智能体" in content))

    # 工作哲学检查
    checks.append(("工作哲学", any(kw in content for kw in ["Work Philosophy", "Your Work Philosophy", "工作哲学"])))

    # 边界检查
    checks.append(("职责边界", any(kw in content for kw in ["Boundaries", "You don't do", "你不负责"])))

    # Session Mode检查
    checks.append(("Session Mode", "Session Mode" in content))

    return all(check for _, check in checks), checks


def test_agents_content(subagent):
    """测试AGENTS.md内容"""
    path = subagent['path']
    content = load_single_identity_file(path, "AGENTS.md")

    checks = []

    # 身份声明检查
    checks.append(("身份声明", any(kw in content for kw in ["Who You Are", "你是", "Your role"])))

    # 职责检查
    checks.append(("核心职责", any(kw in content for kw in ["Responsibilities", "Core Tasks", "职责", "任务"])))

    # 工作流程检查
    checks.append(("工作流程", any(kw in content for kw in ["Flow", "流程", "Processing Flow"])))

    # 红线检查
    checks.append(("红线规则", any(kw in content for kw in ["Red Lines", "红线"])))

    # 工具检查
    checks.append(("工具列表", any(kw in content for kw in ["Tools", "skills/", "scripts/"])))

    return all(check for _, check in checks), checks


def test_memory_content(subagent):
    """测试MEMORY.md内容"""
    path = subagent['path']
    content = load_single_identity_file(path, "MEMORY.md")

    checks = []

    # 专业知识检查（不同子智能体有不同的专业知识）
    agent_name = subagent['name']

    if "data-perception" in agent_name:
        # 数据感知子智能体
        checks.append(("数据源类型", "数据源" in content or "data source" in content.lower()))
        checks.append(("质量标准", "质量" in content or "quality" in content.lower()))
        checks.append(("时间滞后", "水力停留时间" in content or "2小时" in content))
    elif "anomaly-detection" in agent_name:
        # 异常检测子智能体
        checks.append(("算子库", "算子" in content or "operator" in content.lower()))
        checks.append(("异常模式", "异常模式" in content or "anomaly" in content.lower()))
        checks.append(("检测策略", "检测" in content or "detection" in content.lower()))
    elif "rule-reasoning" in agent_name:
        # 规则推理子智能体
        checks.append(("法规库", "法规" in content or "regulation" in content.lower()))
        checks.append(("工艺知识", "工艺" in content or "process" in content.lower()))
        checks.append(("嫌疑等级", "嫌疑" in content or "suspicion" in content.lower()))
    elif "disposition-execution" in agent_name:
        # 研判预警与处置执行子智能体
        checks.append(("预警分级", "预警" in content or "alert" in content.lower()))
        checks.append(("工单模板", "工单" in content or "work order" in content.lower()))
        checks.append(("处置流程", "处置" in content or "disposition" in content.lower()))

    # 历史案例检查
    checks.append(("历史案例", any(kw in content for kw in ["案例", "历史", "case", "history"])))

    return all(check for _, check in checks), checks


def test_all_subagents_content():
    """测试所有子智能体的身份文件内容"""
    print("\n" + "=" * 70)
    print("子智能体身份文件内容验证")
    print("=" * 70)

    total_checks = 0
    total_passed = 0

    for subagent in SUBAGENTS:
        print(f"\n{'='*70}")
        print(f"{subagent['display_name']}")
        print(f"{'='*70}")

        # 测试SOUL.md
        print("\nSOUL.md:")
        soul_ok, soul_checks = test_soul_content(subagent)
        for name, passed in soul_checks:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {name}")
        total_checks += len(soul_checks)
        total_passed += sum(1 for _, p in soul_checks if p)

        # 测试AGENTS.md
        print("\nAGENTS.md:")
        agents_ok, agents_checks = test_agents_content(subagent)
        for name, passed in agents_checks:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {name}")
        total_checks += len(agents_checks)
        total_passed += sum(1 for _, p in agents_checks if p)

        # 测试MEMORY.md
        print("\nMEMORY.md:")
        memory_ok, memory_checks = test_memory_content(subagent)
        for name, passed in memory_checks:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {name}")
        total_checks += len(memory_checks)
        total_passed += sum(1 for _, p in memory_checks if p)

    print("\n" + "=" * 70)
    print(f"总体验证结果: {total_passed}/{total_checks} 通过")
    print("=" * 70)

    return total_passed == total_checks


def main():
    """运行测试"""
    print("\n" + "=" * 70)
    print("子智能体身份文件验证")
    print("=" * 70)
    print(f"项目根目录: {project_root}")

    # 1. 检查文件存在性
    files_exist = test_subagent_files_exist()

    if not files_exist:
        print("\n[FAIL] 部分身份文件不存在，请先创建缺失的文件")
        return 1

    # 2. 检查文件内容
    content_ok = test_all_subagents_content()

    if content_ok:
        print("\n[PASS] 所有验证通过！子智能体身份文件内容正确。")
        return 0
    else:
        print("\n[FAIL] 部分验证失败，请检查上面的错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
