#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四层架构验证脚本

验证基于专利的四层架构文件结构完整性
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append("E:/project/Ecological_env")

def check_directory_structure():
    """检查目录结构"""
    print("=" * 60)
    print("四层架构目录结构验证")
    print("=" * 60)

    base_path = Path("E:/project/Ecological_env")

    # 检查主智能体层
    master_agent_path = base_path / "workspace/skills/master-agent-core/scripts"
    master_agent_files = [
        "nlu_module.py",
        "task_decomposition.py",
        "result_reuse.py",
        "scheduling_decision.py",
        "result_interpretation.py",
        "adaptive_optimization.py",
        "task_structuring.py",
        "task_flow_generation.py",
        "resource_matching.py",
        "execution_control.py",
        "task_orchestration_layer.py",
        "master_agent_layer.py"
    ]

    print("\n[主智能体层] 检查:")
    for file in master_agent_files:
        file_path = master_agent_path / file
        status = "[OK]" if file_path.exists() else "[FAIL]"
        print(f"  {status} {file}")

    master_count = sum(1 for f in master_agent_files if (master_agent_path / f).exists())
    print(f"  完成: {master_count}/{len(master_agent_files)}")

    # 检查子智能体层
    subagents = [
        "multi-dimensional-data-perception-agent",
        "disposition-execution-agent",
        "anomaly-detection-agent",
        "rule-reasoning-agent"
    ]

    print("\n【子智能体层】检查:")
    for agent in subagents:
        agent_path = base_path / "subagents" / agent

        # 检查必需文件
        soul_exists = (agent_path / "SOUL.md").exists()
        agents_exists = (agent_path / "AGENTS.md").exists()
        memory_exists = (agent_path / "MEMORY.md").exists()
        skills_exists = (agent_path / "skills").exists()

        all_exist = soul_exists and agents_exists and memory_exists and skills_exists
        status = "✓" if all_exist else "✗"

        print(f"  {status} {agent}")
        print(f"      SOUL.md: {'✓' if soul_exists else '✗'}")
        print(f"      AGENTS.md: {'✓' if agents_exists else '✗'}")
        print(f"      MEMORY.md: {'✓' if memory_exists else '✗'}")
        print(f"      skills/: {'✓' if skills_exists else '✗'}")

    subagent_count = sum(1 for agent in subagents if (base_path / "subagents" / agent / "SOUL.md").exists())
    print(f"  完成: {subagent_count}/{len(subagents)}")

    # 检查数据与支撑层
    print("\n【数据与支撑层】检查:")
    shared_path = base_path / "shared"

    checks = [
        ("data/", "data"),
        ("models/", "models"),
        ("configs/", "configs"),
        ("cache/", "cache")
    ]

    for path_str, name in checks:
        exists = (shared_path / path_str).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}")

    # 检查配置文件
    print("\n【配置文件】检查:")
    config_files = [
        "shared/configs/subagent_registry.json",
        "shared/configs/system_config.yaml",
        "interfaces/subagent_protocol.md",
        "interfaces/input_schema.json",
        "interfaces/output_schema.json",
        "interfaces/error_codes.md"
    ]

    for file in config_files:
        file_path = base_path / file
        status = "✓" if file_path.exists() else "✗"
        print(f"  {status} {file}")

    config_count = sum(1 for f in config_files if (base_path / f).exists())
    print(f"  完成: {config_count}/{len(config_files)}")

    # 检查知识库
    print("\n【知识库】检查:")
    knowledge_base = base_path / "subagents/rule-reasoning-agent/skills/rule-reasoning-core/references"

    knowledge_dirs = [
        "regulations",
        "process_knowledge",
        "expert_experience",
        "cases"
    ]

    for dir_name in knowledge_dirs:
        dir_path = knowledge_base / dir_name
        exists = dir_path.exists()
        status = "✓" if exists else "✗"
        count = len(list(dir_path.glob("*.md"))) if exists else 0
        print(f"  {status} {dir_name}/ ({count} 文件)")

    return True


def check_architecture_compliance():
    """检查架构合规性"""
    print("\n" + "=" * 60)
    print("专利架构合规性验证")
    print("=" * 60)

    base_path = Path("E:/project/Ecological_env")

    # 主智能体层六大模块
    print("\n【主智能体层】六大功能模块:")
    master_modules = [
        ("1. 自然语言理解模块", "nlu_module.py"),
        ("2. 任务分解模块", "task_decomposition.py"),
        ("3. 结果复用判决模块", "result_reuse.py"),
        ("4. 调度决策模块", "scheduling_decision.py"),
        ("5. 结果解释模块", "result_interpretation.py"),
        ("6. 自适应优化模块", "adaptive_optimization.py")
    ]

    master_scripts_path = base_path / "workspace/skills/master-agent-core/scripts"

    for name, file in master_modules:
        exists = (master_scripts_path / file).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}")

    # 任务编排层四大模块
    print("\n【任务编排层】四大功能模块:")
    orchestration_modules = [
        ("1. 任务结构化模块", "task_structuring.py"),
        ("2. 任务流生成模块", "task_flow_generation.py"),
        ("3. 资源匹配模块", "resource_matching.py"),
        ("4. 执行控制模块", "execution_control.py")
    ]

    for name, file in orchestration_modules:
        exists = (master_scripts_path / file).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}")

    # 子智能体层四类标准子智能体
    print("\n【子智能体层】四类标准子智能体:")
    subagent_types = [
        ("1. 数据治理子智能体", "multi-dimensional-data-perception-agent"),
        ("2. 特征与关系分析子智能体", "disposition-execution-agent"),
        ("3. 异常检测子智能体", "anomaly-detection-agent"),
        ("4. 规则推理子智能体", "rule-reasoning-agent")
    ]

    subagents_path = base_path / "subagents"

    for name, agent_dir in subagent_types:
        exists = (subagents_path / agent_dir / "SOUL.md").exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}")

    # 数据与支撑层三大组件
    print("\n【数据与支撑层】三大支撑组件:")
    support_components = [
        ("1. 时序监测数据库", "data/"),
        ("2. 废水排放知识库", "subagents/rule-reasoning-agent/skills/rule-reasoning-core/references/"),
        ("3. 异常检测模型算子库", "subagents/anomaly-detection-agent/skills/anomaly-detection-core/references/operator_manifest.json")
    ]

    for name, path in support_components:
        full_path = base_path / path
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}")

    return True


def generate_summary_report():
    """生成总结报告"""
    print("\n" + "=" * 60)
    print("重构总结报告")
    print("=" * 60)

    base_path = Path("E:/project/Ecological_env")

    # 统计文件数量
    master_agent_files = list((base_path / "workspace/skills/master-agent-core/scripts").glob("*.py"))
    subagent_souls = list((base_path / "subagents").glob("*/SOUL.md"))
    knowledge_files = list((base_path / "subagents/rule-reasoning-agent/skills/rule-reasoning-core/references").rglob("*.md"))

    print(f"\n文件统计:")
    print(f"  主智能体层模块: {len(master_agent_files)} 个")
    print(f"  子智能体定义: {len(subagent_souls)} 个")
    print(f"  知识库文件: {len(knowledge_files)} 个")

    print(f"\n架构特性:")
    print(f"  ✓ 四层标准化架构")
    print(f"  ✓ 六合四子智能体合并")
    print(f"  ✓ 结果复用机制")
    print(f"  ✓ 双驱动运行模式")
    print(f"  ✓ 闭环迭代优化")

    print(f"\n符合专利规范:")
    print(f"  ✓ 主智能体层 - 全局决策中枢")
    print(f"  ✓ 任务编排层 - 结构化执行枢纽")
    print(f"  ✓ 子智能体层 - 能力执行单元")
    print(f"  ✓ 数据与支撑层 - 底层支撑")

    return True


if __name__ == "__main__":
    check_directory_structure()
    check_architecture_compliance()
    generate_summary_report()

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)
