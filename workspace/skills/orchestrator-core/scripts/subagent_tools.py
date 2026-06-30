"""
主智能体工具集 - 子智能体调用工具

供主智能体通过 LLM 调用，实现动态子智能体编排。
"""

from typing import Dict, Any, List, Optional


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    调用子智能体执行任务

    Args:
        subagent_name: 子智能体名称 (如 "anomaly-detection")
        task: 任务描述
        context: 上一个子智能体的结果（可选）

    Returns:
        {
            "task_id": str,
            "status": "completed" | "failed",
            "result": dict | None,
            "error": str | None,
            "metadata": {
                "duration_seconds": float,
                "timestamp": str,
                "subagent_name": str
            }
        }

    Raises:
        ValueError: 未知子智能体名称
        IOError: 会话目录创建失败
    """
    from .call_subagent import call_subagent as _call_subagent
    return _call_subagent(subagent_name, task, context)


def read_result(result_file: str) -> Dict[str, Any]:
    """
    读取子智能体结果文件

    Args:
        result_file: 结果文件路径（相对于 sessions/{session_id}/）

    Returns:
        结果数据字典
    """
    import json
    from pathlib import Path
    from .create_session import get_session_dir

    session_dir = get_session_dir()
    result_path = Path(session_dir) / result_file

    if not result_path.exists():
        return {"error": f"Result file not found: {result_file}"}

    with open(result_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_subagents() -> List[Dict[str, str]]:
    """
    列出所有可用的子智能体

    Returns:
        [
            {"id": "anomaly-detection", "name": "异常检测子智能体", "path": "..."},
            {"id": "rule-reasoning", "name": "规则推理子智能体", "path": "..."},
            ...
        ]
    """
    from .call_subagent import SUBAGENT_PATHS

    agents = []
    for agent_id, path in SUBAGENT_PATHS.items():
        # 只返回完整名称的子智能体（包含 - 的）
        if "-" in agent_id:
            agents.append({
                "id": agent_id,
                "name": agent_id.replace("-", " ").replace("_", " ").title(),
                "path": path
            })
    return agents


def create_session() -> str:
    """
    创建新的会话目录

    Returns:
        session_id: 会话ID（用于通信）
    """
    from .create_session import create_session as _create_session
    return _create_session()
