"""
Orchestrator tool - 注册废水监测主智能体的子智能体调用工具

此工具为废水监测系统提供调用子智能体的能力，实现多智能体协调。

注意：使用延迟导入，避免在 Hermes 上下文导入时失败。
"""
import os
import sys
from pathlib import Path

# 添加项目路径（仅在运行时可用）
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # shared/framework/hermes-overlays/tools/ → 项目根

# 工具函数：延迟导入子智能体工具（从 bridge，它正确聚合了 4 个函数）
def _get_subagent_tools():
    """延迟导入 orchestrator_core_bridge，仅在调用时加载。

    bridge 正确聚合了 call_subagent / create_session / list_subagents / read_result
    （分别来自 call_subagent.py / create_session.py / subagent_tools.py / bridge 自身）。
    不直接 import subagent_tools——它不导出 create_session/read_result。
    """
    import importlib

    # 确保项目目录在 sys.path
    project_str = str(PROJECT_ROOT)
    if project_str not in sys.path:
        sys.path.insert(0, project_str)

    try:
        module = importlib.import_module('workspace.skills.orchestrator_core_bridge')
        return (
            module.call_subagent,
            module.create_session,
            module.list_subagents,
            module.read_result
        )
    except ImportError as e:
        # 如果在非项目上下文中运行，返回空实现
        def _not_available(*args, **kwargs):
            return {"error": f"Subagent tools not available: {e}"}

        return (_not_available,) * 4

from tools.registry import registry

# 注册 call_subagent 工具
def _call_subagent_handler(args=None, **kwargs):
    """延迟调用 call_subagent（hermes dispatch 把工具参数 dict 作第 1 个位置参数传入）"""
    a = args or kwargs or {}
    call_subagent_fn, _, _, _ = _get_subagent_tools()
    result = call_subagent_fn(a.get("subagent_name"), a.get("task"), a.get("context"))
    return {"result": result}

registry.register(
    name="call_subagent",
    toolset="hermes-cli",
    schema={
        "type": "function",
        "function": {
            "name": "call_subagent",
            "description": "调用废水监测子智能体执行任务。可用的子智能体：multi-dimensional-data-perception（数据感知）、anomaly-detection（异常检测）、rule-reasoning（规则推理）、disposition-execution（处置执行）",
            "parameters": {
                "type": "object",
                "properties": {
                    "subagent_name": {
                        "type": "string",
                        "description": "子智能体名称",
                        "enum": [
                            "multi-dimensional-data-perception",
                            "anomaly-detection",
                            "rule-reasoning",
                            "disposition-execution",
                            "data-perception",
                            "anomaly",
                            "rule",
                            "disposition"
                        ]
                    },
                    "task": {
                        "type": "string",
                        "description": "任务描述"
                    },
                    "context": {
                        "type": "object",
                        "description": "上下文信息（前置子智能体的结果）"
                    }
                },
                "required": ["subagent_name", "task"]
            }
        }
    },
    handler=_call_subagent_handler,
    check_fn=lambda: True,  # 始终可用
    requires_env=[],
    is_async=False,
    description="调用废水监测子智能体",
    emoji="🔧"
)

# 注册 create_session 工具
def _create_session_handler(args=None, **kwargs):
    """延迟调用 create_session"""
    _, create_session_fn, _, _ = _get_subagent_tools()
    session_id = create_session_fn()
    return {"result": {"session_id": session_id}}

registry.register(
    name="create_session",
    toolset="hermes-cli",
    schema={
        "type": "function",
        "function": {
            "name": "create_session",
            "description": "创建新的会话目录，用于隔离子智能体的任务和结果",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    handler=_create_session_handler,
    check_fn=lambda: True,
    requires_env=[],
    is_async=False,
    description="创建新会话",
    emoji="📁"
)

# 注册 list_subagents 工具
def _list_subagents_handler(args=None, **kwargs):
    """延迟调用 list_subagents"""
    _, _, list_subagents_fn, _ = _get_subagent_tools()
    return {"result": list_subagents_fn()}

registry.register(
    name="list_subagents",
    toolset="hermes-cli",
    schema={
        "type": "function",
        "function": {
            "name": "list_subagents",
            "description": "列出所有可用的废水监测子智能体",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    handler=_list_subagents_handler,
    check_fn=lambda: True,
    requires_env=[],
    is_async=False,
    description="列出子智能体",
    emoji="📋"
)

# 注册 read_result 工具
def _read_result_handler(args=None, **kwargs):
    """延迟调用 read_result"""
    a = args or kwargs or {}
    _, _, _, read_result_fn = _get_subagent_tools()
    return {"result": read_result_fn(a.get("result_file"))}

registry.register(
    name="read_result",
    toolset="hermes-cli",
    schema={
        "type": "function",
        "function": {
            "name": "read_result",
            "description": "读取子智能体的执行结果文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_file": {
                        "type": "string",
                        "description": "结果文件名（如 data_result.json）"
                    }
                },
                "required": ["result_file"]
            }
        }
    },
    handler=_read_result_handler,
    check_fn=lambda: True,
    requires_env=[],
    is_async=False,
    description="读取结果文件",
    emoji="📄"
)
