#!/usr/bin/env python3
"""
Orchestrator Tools Registry (Standalone Version)

This file previously registered tools with the external Hermes framework.
Since we now use a local Hermes implementation, this file serves as:
1. Documentation of available orchestrator tools
2. A reference for tool schemas that could be used by other integrations

The actual tool implementations are in:
- call_subagent.py: Core subagent calling logic
- subagent_tools.py: Tool wrappers for subagent operations
- orchestrator_core_bridge.py: Bridge module for workspace integration
"""
import os
import sys
from pathlib import Path


def _get_bridge():
    """Lazy import of orchestrator_core_bridge to avoid circular imports"""
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Import directly from the module file (in workspace/skills/)
    import importlib.util
    bridge_path = project_root / "workspace" / "skills" / "orchestrator_core_bridge.py"
    spec = importlib.util.spec_from_file_location("orchestrator_core_bridge", bridge_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_subagent(*args, **kwargs):
    """Proxy for orchestrator_core_bridge.call_subagent"""
    return _get_bridge().call_subagent(*args, **kwargs)


def list_subagents(*args, **kwargs):
    """Proxy for orchestrator_core_bridge.list_subagents"""
    return _get_bridge().list_subagents(*args, **kwargs)


def create_session(*args, **kwargs):
    """Proxy for orchestrator_core_bridge.create_session"""
    return _get_bridge().create_session(*args, **kwargs)


def read_result(result_file: str):
    """Read subagent result file"""
    return _get_bridge().read_result(result_file)


# Tool schemas for documentation/future integration
ORCHESTRATOR_TOOLS = {
    "call_subagent": {
        "description": (
            "【重要】调用指定的子智能体执行任务。你必须从4个子智能体中选择一个并明确指定。\n\n"
            "可用的子智能体（必须选择其中一个）：\n"
            "1. multi-dimensional-data-perception - 数据感知子智能体，用于获取进出水监测数据\n"
            "2. anomaly-detection - 异常检测子智能体，用于检测水质异常和违规模式\n"
            "3. rule-reasoning - 规则推理子智能体，用于根据法规判定违规类型\n"
            "4. disposition-execution - 处置执行子智能体，用于生成预警报告和工单\n\n"
            "【使用规则】\n"
            "- 必须同时提供 subagent_name 和 task 参数\n"
            "- subagent_name 必须是上述4个名称之一\n"
            "- task 是对子智能体的具体任务描述\n\n"
            "示例：\n"
            "- 获取数据：subagent_name='multi-dimensional-data-perception', task='获取最近24小时进出水数据'\n"
            "- 检测异常：subagent_name='anomaly-detection', task='检测最近48小时的水质异常'"
        ),
        "parameters": {
            "name": {
                "type": "string",
                "enum": [
                    "multi-dimensional-data-perception",
                    "anomaly-detection",
                    "rule-reasoning",
                    "disposition-execution"
                ],
                "description": "【必需】子智能体名称（4选1）"
            },
            "task": {
                "type": "string",
                "description": "【必需】具体任务描述"
            },
            "context": {
                "type": "string",
                "description": "【可选】前置子智能体的执行结果（JSON字符串）"
            }
        },
        "required": ["name", "task"]
    },
    "list_subagents": {
        "description": "列出所有可用的子智能体及其功能",
        "parameters": {}
    },
    "create_orchestrator_session": {
        "description": "创建新的会话目录用于子智能体通信",
        "parameters": {}
    },
    "read_subagent_result": {
        "description": "读取子智能体的执行结果文件",
        "parameters": {
            "result_file": {
                "type": "string",
                "description": "结果文件名（如 data_result.json）"
            }
        },
        "required": ["result_file"]
    }
}


# Export functions for direct use
__all__ = [
    "call_subagent",
    "list_subagents",
    "create_session",
    "read_result",
    "ORCHESTRATOR_TOOLS"
]


# Note: This file no longer auto-registers tools on import.
# The external Hermes tools.registry is no longer required.
# Tools are available through direct import from orchestrator_core_bridge.
