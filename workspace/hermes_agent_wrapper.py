#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes Agent Wrapper - 真正使用 Hermes 框架

使用 Hermes AIAgent 的 run_conversation() 方法处理用户查询。
LLM 通过 delegate_task 工具决定调用哪些子智能体。
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# 添加 Hermes 框架路径
HERMES_PATH = Path("D:/Hermes/hermes-agent")
if HERMES_PATH.exists() and str(HERMES_PATH) not in sys.path:
    sys.path.insert(0, str(HERMES_PATH))

logger = logging.getLogger(__name__)

# 全局 AIAgent 实例
_agent_instance = None


def get_agent():
    """获取或创建 AIAgent 实例（单例模式）"""
    global _agent_instance
    if _agent_instance is None:
        try:
            from run_agent import AIAgent

            # CTGU-VLM 端点配置
            base_url = "http://172.16.12.41:30000/v1"
            api_key = os.getenv("LLM_API_KEY", "sk-placeholder")
            model = "ctgu-vlm"

            # 创建主智能体实例
            _agent_instance = AIAgent(
                base_url=base_url,
                api_key=api_key,
                provider="custom",
                model=model,
                max_iterations=90,
                load_soul_identity=True,          # 加载 workspace/SOUL.md
                skip_context_files=False,         # 加载 workspace/AGENTS.md 等
                enabled_toolsets=["delegation", "terminal", "file_ops"],
                quiet_mode=True
            )

            logger.info("[HERMES-WRAPPER] AIAgent 实例创建成功")
            print(f"[HERMES-WRAPPER] AIAgent 初始化成功，模型: {model}")

        except Exception as e:
            logger.error(f"[HERMES-WRAPPER] AIAgent 初始化失败: {e}")
            print(f"[HERMES-WRAPPER] 初始化失败: {e}")
            _agent_instance = None

    return _agent_instance


def process_query(query: str, data: Optional[Dict[str, Any]] = None,
                  context: Optional[str] = None) -> Dict[str, Any]:
    """
    处理用户查询

    使用 AIAgent.run_conversation() 让 LLM 决定如何处理查询，
    包括是否调用子智能体。

    Args:
        query: 用户查询文本
        data: 附加数据（可选）
        context: 附加上下文（可选）

    Returns:
        处理结果字典
    """
    agent = get_agent()
    if agent is None:
        return {
            "status": "error",
            "error": "Hermes AIAgent 未初始化"
        }

    # 构建消息
    content = query

    # 添加数据
    if data:
        content += f"\n\n数据:\n{json.dumps(data, ensure_ascii=False, indent=2)}"

    # 添加上下文
    if context:
        content += f"\n\n上下文:\n{context}"

    messages = [{"role": "user", "content": content}]

    try:
        # 使用 run_conversation 让 LLM 处理
        print(f"[HERMES-WRAPPER] 处理查询: {query[:100]}...")

        response = agent.run_conversation(messages)

        # 解析响应
        result = {
            "status": "success",
            "query": query,
            "response": str(response),
            "summary": "查询已由 Hermes AIAgent 处理"
        }

        print(f"[HERMES-WRAPPER] 查询处理完成")
        return result

    except Exception as e:
        logger.error(f"[HERMES-WRAPPER] 查询处理失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }


# 兼容旧接口
class HermesMasterAgent:
    """
    兼容类 - 保持与旧代码的接口兼容

    旧的 coordinate_agent_execution 方法映射到新的 process_query 函数。
    """

    def __init__(self, project_root: Optional[Path] = None, llm_client=None):
        """初始化（兼容接口）"""
        self.project_root = project_root or Path(__file__).resolve().parent.parent.parent
        self.llm_client = llm_client
        self.hermes_available = get_agent() is not None
        self.identity_loader = SubAgentIdentityLoader(project_root)

        if self.hermes_available:
            print("[HERMES-MASTER] Hermes 框架已启用（通过 run_conversation）")
        else:
            print("[HERMES-MASTER] 警告: Hermes 框架不可用")

    def coordinate_agent_execution(self, agent_id: str, task: Dict[str, Any],
                                   previous_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        兼容接口 - 映射到 process_query

        注意：这个接口不再直接调用特定子智能体。
        查询会传递给 AIAgent，由 LLM 决定调用哪些子智能体。
        """
        # 构建查询文本
        query = task.get("description", f"执行 {agent_id} 的任务")

        # 添加前序结果
        context = None
        if previous_results:
            context = f"前序结果:\n{json.dumps(previous_results, ensure_ascii=False, indent=2)}"

        # 使用新的 process_query
        result = process_query(
            query=query,
            data=task.get("data"),
            context=context
        )

        # 添加兼容字段
        if result.get("status") == "success":
            result["agent_id"] = agent_id
            result["task_id"] = task.get("task_id")
            result["processed_data"] = {"response": result.get("response")}

        return result


# 导出
__all__ = [
    'get_agent',
    'process_query',
    'HermesMasterAgent',  # 兼容别名
    'LLMAgentCoordinator'  # 兼容别名
]

# 兼容性别名
LLMAgentCoordinator = HermesMasterAgent


class SubAgentIdentityLoader:
    """
    子智能体身份加载器（兼容接口）

    提供子智能体的身份信息，用于向后兼容。
    """

    SUB_AGENTS = {
        "multi-dimensional-data-perception": {
            "name": "多维数据感知子智能体",
            "skill_path": "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core",
            "description": "获取多维时序数据，分解、清洗、标准化"
        },
        "anomaly-detection": {
            "name": "异常检测子智能体",
            "skill_path": "subagents/anomaly-detection-agent/skills/anomaly-detection-core",
            "description": "使用多种算子检测时序数据异常"
        },
        "rule-reasoning": {
            "name": "规则推理子智能体",
            "skill_path": "subagents/rule-reasoning-agent/skills/rule-reasoning-core",
            "description": "基于法规和工艺知识进行规则推理"
        },
        "disposition-execution": {
            "name": "研判预警与处置执行子智能体",
            "skill_path": "subagents/disposition-execution-agent/skills/disposition-execution-core",
            "description": "融合异常检测和规则推理结果，生成处置工单"
        }
    }

    def __init__(self, project_root=None):
        """初始化加载器"""
        self.project_root = project_root or Path(__file__).resolve().parent.parent

    def load_agent_identity(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """加载子智能体身份"""
        if agent_id not in self.SUB_AGENTS:
            return None

        config = self.SUB_AGENTS[agent_id]
        return {
            "agent_id": agent_id,
            "agent_name": config["name"],
            "skill_path": config["skill_path"],
            "description": config["description"]
        }

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """获取所有子智能体信息"""
        return self.SUB_AGENTS.copy()
