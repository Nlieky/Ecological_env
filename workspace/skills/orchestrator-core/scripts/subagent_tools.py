# workspace/skills/orchestrator-core/scripts/subagent_tools.py
"""子智能体调用工具

提供主智能体调用子智能体的工具函数
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Import SubagentManager at module level for access to SUBAGENT_CONFIGS
try:
    from .subagent_manager import SubagentManager
except ImportError:
    # Fallback for when running as a module
    from workspace.skills.orchestrator_core.scripts.subagent_manager import SubagentManager

# 全局子智能体管理器实例
_subagent_manager = None


def get_subagent_manager():
    """获取全局子智能体管理器实例"""
    global _subagent_manager
    if _subagent_manager is None:
        # 使用项目根目录初始化
        project_root = Path(__file__).parents[4]  # 回到项目根目录
        _subagent_manager = SubagentManager(project_root=project_root)
    return _subagent_manager


def initialize_subagents(model: str = None, base_url: str = None, api_key: str = None) -> Dict[str, Any]:
    """初始化所有子智能体

    Args:
        model: LLM模型名称
        base_url: API基础URL
        api_key: API密钥

    Returns:
        初始化结果，包含:
        - success: bool - 是否成功
        - count: int - 创建的子智能体数量
        - subagents: list - 子智能体名称列表
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()
        manager.create_subagents(model=model, base_url=base_url, api_key=api_key)

        return {
            "success": True,
            "count": len(manager.subagents),
            "subagents": manager.list_subagents()
        }
    except Exception as e:
        logger.error(f"Failed to initialize subagents: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """调用子智能体执行任务

    Args:
        subagent_name: 子智能体名称
        task: 需要子智能体执行的任务描述
        context: 可选的上下文信息

    Returns:
        子智能体的执行结果，包含:
        - success: bool - 是否成功
        - result: str - 执行结果
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()

        # 检查子智能体是否可用
        if not manager.is_subagent_available(subagent_name):
            return {
                "success": False,
                "error": f"子智能体 '{subagent_name}' 不存在或未初始化"
            }

        # 获取子智能体实例
        subagent = manager.get_subagent(subagent_name)
        if not subagent:
            return {
                "success": False,
                "error": f"无法获取子智能体 '{subagent_name}'"
            }

        # 构建完整的任务描述（包含上下文）
        full_task = task
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            full_task = f"上下文信息：\n{context_str}\n\n任务：\n{task}"

        # 调用子智能体执行任务
        logger.info(f"Calling subagent '{subagent_name}' with task: {task[:100]}...")

        result = subagent.run_conversation(full_task)

        # 提取最终响应
        if isinstance(result, dict):
            final_response = result.get("final_response", "")
        else:
            final_response = str(result)

        logger.info(f"Subagent '{subagent_name}' completed successfully")

        return {
            "success": True,
            "result": final_response
        }

    except Exception as e:
        logger.error(f"Error calling subagent '{subagent_name}': {e}")
        return {
            "success": False,
            "error": str(e)
        }


def list_available_subagents() -> Dict[str, Any]:
    """列出所有可用的子智能体

    Returns:
        可用子智能体列表，包含:
        - success: bool - 是否成功
        - subagents: list - 子智能体名称列表
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()
        subagent_names = manager.list_subagents()

        return {
            "success": True,
            "subagents": subagent_names
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_subagent_info(subagent_name: str) -> Dict[str, Any]:
    """获取子智能体信息

    Args:
        subagent_name: 子智能体名称

    Returns:
        子智能体信息，包含:
        - success: bool - 是否成功
        - available: bool - 是否可用
        - description: str - 描述
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()

        if subagent_name not in SubagentManager.SUBAGENT_CONFIGS:
            return {
                "success": False,
                "error": f"未知的子智能体: '{subagent_name}'"
            }

        config = SubagentManager.SUBAGENT_CONFIGS[subagent_name]
        available = manager.is_subagent_available(subagent_name)

        return {
            "success": True,
            "available": available,
            "description": config["description"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def shutdown_subagents() -> Dict[str, Any]:
    """关闭所有子智能体

    Returns:
        关闭结果，包含:
        - success: bool - 是否成功
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()
        manager.shutdown()

        return {
            "success": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
