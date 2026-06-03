#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主智能体综合测试脚本

测试内容：
1. LLM客户端能否正常工作
2. 主智能体配置加载（AGENTS.md、SOUL.md等）
3. 读取Skills/SKILL.md
4. 任务编排、自然语言理解、任务分解、调度决策
5. 读取工作流模式库、决策规则库
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared" / "configs"))

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def test_llm_client():
    """测试1：LLM客户端能否正常工作"""
    logger.info("=" * 50)
    logger.info("测试1：LLM客户端")
    logger.info("=" * 50)

    try:
        from llm_client import get_llm_client

        # 获取客户端
        client = get_llm_client()
        logger.info(f"✓ LLM客户端初始化成功")
        logger.info(f"  - 主模型: {client.config.primary_model}")
        logger.info(f"  - 快速模型: {client.config.fast_model}")
        logger.info(f"  - 分析模型: {client.config.analysis_model}")
        logger.info(f"  - API密钥: {'已设置' if client.config.api_key else '未设置'}")
        logger.info(f"  - Base URL: {client.config.base_url}")
        logger.info(f"  - 超时: {client.config.timeout}秒")

        # 测试简单聊天
        logger.info("\n测试聊天请求...")
        response = client.chat("你好，请用一句话介绍你的角色。", model_type="fast")
        logger.info(f"✓ 聊天成功")
        logger.info(f"  响应: {response[:100]}...")

        return True

    except Exception as e:
        logger.error(f"✗ LLM客户端测试失败: {e}")
        return False


def test_master_agent_config():
    """测试2：主智能体配置加载"""
    logger.info("\n" + "=" * 50)
    logger.info("测试2：主智能体配置加载")
    logger.info("=" * 50)

    workspace_path = project_root / "workspace"

    # 测试的文件列表
    config_files = {
        "AGENTS.md": "全局使用说明",
        "SOUL.md": "主智能体身份",
        "IDENTITY.md": "身份卡片",
        "MEMORY.md": "全局长期记忆",
        "HEARTBEAT.md": "周期性任务清单",
        "TOOLS.md": "工具配置笔记",
    }

    results = {}

    for filename, description in config_files.items():
        file_path = workspace_path / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 统计信息
            lines = content.count('\n')
            chars = len(content)
            results[filename] = {
                "exists": True,
                "description": description,
                "lines": lines,
                "chars": chars
            }
            logger.info(f"✓ {filename}: {description} ({lines}行)")

        except FileNotFoundError:
            results[filename] = {"exists": False, "description": description}
            logger.error(f"✗ {filename}: 文件不存在")

    # 验证关键内容
    logger.info("\n验证关键内容:")

    # 检查AGENTS.md是否有4个子智能体
    agents_file = workspace_path / "AGENTS.md"
    with open(agents_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if "multi-dimensional-data-perception-agent" in content:
            logger.info("✓ AGENTS.md包含multi-dimensional-data-perception-agent")
        if "anomaly-detection-agent" in content:
            logger.info("✓ AGENTS.md包含anomaly-detection-agent")
        if "rule-reasoning-agent" in content:
            logger.info("✓ AGENTS.md包含rule-reasoning-agent")
        if "disposition-execution-agent" in content:
            logger.info("✓ AGENTS.md包含disposition-execution-agent")

    # 检查SOUL.md
    soul_file = workspace_path / "SOUL.md"
    with open(soul_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if "废水虚假排放智能监测系统" in content:
            logger.info("✓ SOUL.md包含系统名称")

    return all(r.get("exists", False) for r in results.values())


def test_skill_md():
    """测试3：读取Skills/SKILL.md"""
    logger.info("\n" + "=" * 50)
    logger.info("测试3：读取Skills/SKILL.md")
    logger.info("=" * 50)

    skill_path = project_root / "workspace" / "skills" / "orchestrator-core" / "SKILL.md"

    try:
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(f"✓ SKILL.md读取成功")
        logger.info(f"  - 路径: {skill_path}")
        logger.info(f"  - 大小: {len(content)}字符")

        # 验证关键内容
        key_elements = {
            "技能包名称": "orchestrator",
            "4个子智能体": "4个子智能体",
            "任务结构化": "task_structuring.py",
            "任务流生成": "task_flow_generation.py",
            "资源匹配": "resource_matching.py",
            "执行控制": "execution_control.py",
        }

        logger.info("\n验证关键内容:")
        for key, value in key_elements.items():
            if value in content:
                logger.info(f"✓ 包含{key}: {value}")
            else:
                logger.warning(f"✗ 缺少{key}: {value}")

        return True

    except FileNotFoundError:
        logger.error(f"✗ SKILL.md不存在: {skill_path}")
        return False
    except Exception as e:
        logger.error(f"✗ 读取SKILL.md失败: {e}")
        return False


def test_task_orchestration():
    """测试4：任务编排功能"""
    logger.info("\n" + "=" * 50)
    logger.info("测试4：任务编排功能")
    logger.info("=" * 50)

    try:
        # 测试脚本导入
        sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core"))

        from scripts.task_structuring import structure_task, TaskStructuringModule
        from scripts.task_flow_generation import create_task_flow
        from scripts.resource_matching import match_task_to_agent

        logger.info("✓ 脚本导入成功")

        # 测试任务结构化
        logger.info("\n测试任务结构化:")
        task_request = {
            "task_name": "出水COD异常检测",
            "category": "anomaly_detection",
            "description": "检测最近24小时出水COD异常",
            "priority": "high",
            "input_params": [
                {"name": "monitoring_point", "value": "出水", "required": True},
                {"name": "indicators", "value": ["COD"], "required": True},
                {"name": "time_range", "value": {"hours": 24}, "required": True}
            ]
        }

        structured = structure_task(task_request)
        logger.info(f"✓ 任务结构化成功")
        logger.info(f"  - 任务ID: {structured['task_id']}")
        logger.info(f"  - 任务名称: {structured['task_name']}")
        logger.info(f"  - 任务类别: {structured['category']}")

        # 测试任务流生成
        logger.info("\n测试任务流生成:")
        tasks = [structured]
        flow = create_task_flow(tasks)
        logger.info(f"✓ 任务流生成成功")
        logger.info(f"  - 流ID: {flow['flow_id']}")
        logger.info(f"  - 任务数: {flow['total_tasks']}")
        logger.info(f"  - 阶段数: {len(flow['stages'])}")

        # 测试资源匹配
        logger.info("\n测试资源匹配:")
        allocation = match_task_to_agent(structured)
        logger.info(f"✓ 资源匹配成功")
        logger.info(f"  - 任务ID: {allocation['task_id']}")
        logger.info(f"  - 分配到: {allocation['agent_id']}")
        logger.info(f"  - 匹配分数: {allocation['match_score']}")

        return True

    except ImportError as e:
        logger.error(f"✗ 脚本导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ 任务编排测试失败: {e}")
        return False


def test_workflow_and_rules():
    """测试5：读取工作流模式库、决策规则库"""
    logger.info("\n" + "=" * 50)
    logger.info("测试5：读取工作流模式库、决策规则库")
    logger.info("=" * 50)

    references_path = project_root / "workspace" / "skills" / "orchestrator-core" / "references"

    # 测试的文件列表
    reference_files = {
        "workflow_patterns.md": "工作流模式库",
        "decision_rules.md": "决策规则库",
        "escalation_protocols.md": "升级上报流程",
        "historical_cases.md": "历史案例库",
        "subagent_manifest.json": "子智能体注册表",
    }

    results = {}

    for filename, description in reference_files.items():
        file_path = references_path / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            results[filename] = {
                "exists": True,
                "description": description,
                "size": len(content)
            }
            logger.info(f"✓ {filename}: {description}")

            # 验证关键内容
            if filename == "workflow_patterns.md":
                if "标准分析流程" in content or "standard_analysis" in content:
                    logger.info(f"  - 包含标准分析流程")
            elif filename == "decision_rules.md":
                if "插瓶干扰" in content or "bottle_interference" in content:
                    logger.info(f"  - 包含插瓶干扰规则")
            elif filename == "subagent_manifest.json":
                import json
                manifest = json.loads(content)
                if "subagents" in manifest:
                    logger.info(f"  - 包含{len(manifest['subagents'])}个子智能体")

        except FileNotFoundError:
            results[filename] = {"exists": False, "description": description}
            logger.error(f"✗ {filename}: 文件不存在")
        except Exception as e:
            results[filename] = {"exists": False, "description": description, "error": str(e)}
            logger.error(f"✗ {filename}: 读取失败 - {e}")

    return all(r.get("exists", False) for r in results.values())


def test_nlu_with_llm():
    """测试6：使用LLM进行自然语言理解和任务分解"""
    logger.info("\n" + "=" * 50)
    logger.info("测试6：自然语言理解与任务分解（LLM）")
    logger.info("=" * 50)

    try:
        from llm_client import get_llm_client

        client = get_llm_client()

        # 读取主智能体配置
        workspace_path = project_root / "workspace"
        agents_content = open(workspace_path / "AGENTS.md", 'r', encoding='utf-8').read()
        soul_content = open(workspace_path / "SOUL.md", 'r', encoding='utf-8').read()
        skill_content = open(workspace_path / "skills" / "orchestrator-core" / "SKILL.md", 'r', encoding='utf-8').read()

        # 构建系统提示词
        system_prompt = f"""
你是废水虚假排放智能监测系统的主智能体。

## 你的身份
{soul_content[:1000]}...

## 你的能力
{skill_content[:1000]}...

## 使用说明
{agents_content[:1000]}...
"""

        # 测试查询
        test_query = "分析最近出水的COD异常情况"

        # 构建提示词
        user_prompt = f"""
请分析以下用户查询，识别意图并规划任务流程。

用户查询：{test_query}

请以JSON格式返回：
{{
    "intent_type": "分析查询/历史查询/状态查询/报告生成",
    "entities": {{
        "monitoring_point": "监测点位",
        "indicators": ["指标列表"],
        "time_range": {{"value": 24, "unit": "hours"}}
    }},
    "required_subagents": ["需要调用的子智能体ID列表"],
    "execution_plan": "执行计划说明"
}}
"""

        logger.info(f"测试查询: {test_query}")
        logger.info("发送到LLM...")

        response = client.chat(
            user_prompt,
            system_prompt=system_prompt,
            model_type="primary"
        )

        logger.info(f"✓ LLM响应成功")
        logger.info(f"响应内容:\n{response}")

        return True

    except Exception as e:
        logger.error(f"✗ LLM自然语言理解测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("开始主智能体综合测试\n")

    results = {}

    # 测试1：LLM客户端
    results["llm_client"] = test_llm_client()

    # 测试2：主智能体配置加载
    results["config"] = test_master_agent_config()

    # 测试3：读取SKILL.md
    results["skill"] = test_skill_md()

    # 测试4：任务编排功能
    results["orchestration"] = test_task_orchestration()

    # 测试5：工作流和规则库
    results["references"] = test_workflow_and_rules()

    # 测试6：LLM自然语言理解
    results["nlu"] = test_nlu_with_llm()

    # 汇总结果
    logger.info("\n" + "=" * 50)
    logger.info("测试结果汇总")
    logger.info("=" * 50)

    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{test_name}: {status}")

    # 总体结果
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n✓✓✓ 所有测试通过！主智能体运行正常。")
        return 0
    else:
        logger.info("\n✗✗✗ 部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
