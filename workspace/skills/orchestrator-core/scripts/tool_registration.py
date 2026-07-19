#!/usr/bin/env python3
"""
工具注册模块 - 将orchestrator工具注册到AIAgent工具系统

这个模块负责将orchestrator-core的工具注册到AIAgent的工具列表中，
使主智能体能够通过LLM决策调用子智能体。
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入工具桥接
try:
    from workspace.skills.orchestrator_core_bridge import (
        call_subagent,
        list_subagents,
        create_session,
        read_result
    )
except ImportError:
    # 如果直接导入失败，通过脚本导入
    import importlib.util
    bridge_path = project_root / "workspace" / "skills" / "orchestrator_core_bridge.py"
    spec = importlib.util.spec_from_file_location("orchestrator_core_bridge", bridge_path)
    bridge_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge_module)

    call_subagent = bridge_module.call_subagent
    list_subagents = bridge_module.list_subagents
    create_session = bridge_module.create_session
    read_result = bridge_module.read_result


def register_orchestrator_tools(agent):
    """将orchestrator工具注册到AIAgent实例（hermes-agent兼容版本）

    Args:
        agent: AIAgent实例
    """
    # 确保agent有tools列表
    if not hasattr(agent, 'tools') or agent.tools is None:
        agent.tools = []

    # 导入桥接模块
    try:
        from workspace.skills.orchestrator_core_bridge import (
            call_subagent,
            list_subagents,
            create_session,
            read_result
        )
    except ImportError:
        import importlib.util
        bridge_path = Path(__file__).parents[4] / "workspace" / "skills" / "orchestrator_core_bridge.py"
        spec = importlib.util.spec_from_file_location("orchestrator_core_bridge", bridge_path)
        bridge_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge_module)

        call_subagent = bridge_module.call_subagent
        list_subagents = bridge_module.list_subagents
        create_session = bridge_module.create_session
        read_result = bridge_module.read_result

    # 使用hermes-agent的工具注册系统
    try:
        from tools.registry import ToolEntry

        # 注册工具到hermes-agent的注册表
        tools_to_register = [
            ToolEntry(
                name="call_subagent",
                handler=_call_subagent_handler,
                schema={
                    "type": "function",
                    "function": {
                        "name": "call_subagent",
                        "description": "调用指定的子智能体执行任务。可用子智能体：multi-dimensional-data-perception(数据感知)、anomaly-detection(异常检测)、rule-reasoning(规则推理)、disposition-execution(处置执行)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "subagent_name": {
                                    "type": "string",
                                    "enum": ["multi-dimensional-data-perception", "anomaly-detection", "rule-reasoning", "disposition-execution"],
                                    "description": "子智能体名称"
                                },
                                "task": {"type": "string", "description": "具体任务描述"},
                                "context": {"type": "string", "description": "前置结果（可选）"}
                            },
                            "required": ["subagent_name", "task"]
                        }
                    }
                }
            ),
            ToolEntry(
                name="list_subagents",
                handler=_list_subagents_handler,
                schema={
                    "type": "function",
                    "function": {
                        "name": "list_subagents",
                        "description": "列出所有可用的子智能体及其功能",
                        "parameters": {"type": "object", "properties": {}, "required": []}
                    }
                }
            ),
            ToolEntry(
                name="create_session",
                handler=_create_session_handler,
                schema={
                    "type": "function",
                    "function": {
                        "name": "create_session",
                        "description": "创建新的会话目录用于子智能体通信",
                        "parameters": {"type": "object", "properties": {}, "required": []}
                    }
                }
            ),
            ToolEntry(
                name="read_result",
                handler=_read_result_handler,
                schema={
                    "type": "function",
                    "function": {
                        "name": "read_result",
                        "description": "读取子智能体的执行结果文件",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "result_file": {"type": "string", "description": "结果文件名"}
                            },
                            "required": ["result_file"]
                        }
                    }
                }
            )
        ]

        # 注册工具
        for tool_entry in tools_to_register:
            agent.tool_registry.register(tool_entry)

        print(f"已注册 {len(tools_to_register)} 个orchestrator工具到hermes-agent注册表")

    except Exception as e:
        print(f"使用hermes-agent注册表失败: {e}，回退到传统方式")
        # 回退：直接注册处理函数到agent的工具注册表
        try:
            if hasattr(agent, 'tool_registry'):
                # 直接注册处理函数
                agent.tool_registry.register_by_name(
                    "call_subagent",
                    _call_subagent_handler,
                    {"type": "function", "function": {
                        "name": "call_subagent",
                        "description": "调用指定的子智能体执行任务"
                    }}
                )
                agent.tool_registry.register_by_name(
                    "list_subagents",
                    _list_subagents_handler,
                    {"type": "function", "function": {
                        "name": "list_subagents",
                        "description": "列出所有可用的子智能体"
                    }}
                )
                agent.tool_registry.register_by_name(
                    "create_session",
                    _create_session_handler,
                    {"type": "function", "function": {
                        "name": "create_session",
                        "description": "创建新的会话目录用于子智能体通信"
                    }}
                )
                agent.tool_registry.register_by_name(
                    "read_result",
                    _read_result_handler,
                    {"type": "function", "function": {
                        "name": "read_result",
                        "description": "读取子智能体的执行结果文件"
                    }}
                )
                print(f"已注册 4 个orchestrator工具到工具注册表（回退模式）")
        except Exception as e2:
            print(f"工具注册表注册也失败: {e2}，使用最小化方式")
            # 最小化回退：至少确保工具在工具列表中
            if not hasattr(agent, 'tools'):
                agent.tools = []

            # 添加工具名称到valid_tool_names
            if not hasattr(agent, 'valid_tool_names'):
                agent.valid_tool_names = set()

            agent.valid_tool_names.update(['call_subagent', 'list_subagents', 'create_session', 'read_result'])
            print(f"已添加工具名称到valid_tool_names（最小化模式）")


# Hermes-agent兼容的工具处理器（灵活签名以兼容多种调用方式）
def _call_subagent_handler(*args, **kwargs) -> str:
    """call_subagent工具的hermes-agent兼容处理器

    支持多种调用方式：
    - handler(args_dict) - Hermes Agent传统方式
    - handler(function_name, function_args) - 新式方式
    - handler(function_name="xxx", function_args={...}) - 关键字方式

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        # 解析参数：支持多种调用方式
        if args and isinstance(args[0], dict):
            # 传统方式：handler(args_dict)
            params = args[0]
        elif 'function_args' in kwargs:
            # 新式关键字方式：handler(function_name="xxx", function_args={...})
            params = kwargs['function_args']
        elif args and len(args) >= 2 and isinstance(args[1], dict):
            # 新式位置方式：handler(function_name, function_args)
            params = args[1]
        else:
            # 回退：使用kwargs作为参数
            params = kwargs

        # 调用原始函数
        result = call_subagent(**params)
        # 确保返回字符串格式（hermes-agent要求）
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        error_msg = f"子智能体调用失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


def _list_subagents_handler(*args, **kwargs) -> str:
    """list_subagents工具的hermes-agent兼容处理器

    支持多种调用方式，参见 _call_subagent_handler

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        result = list_subagents()
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        error_msg = f"列出子智能体失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


def _create_session_handler(*args, **kwargs) -> str:
    """create_session工具的hermes-agent兼容处理器

    支持多种调用方式，参见 _call_subagent_handler

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        session_dir = create_session()
        return json.dumps({"session_dir": session_dir}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"创建会话失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


def _read_result_handler(*args, **kwargs) -> str:
    """read_result工具的hermes-agent兼容处理器

    支持多种调用方式，参见 _call_subagent_handler

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        # 从参数获取result_file
        if args and isinstance(args[0], dict):
            result_file = args[0].get("result_file")
        elif 'function_args' in kwargs:
            result_file = kwargs['function_args'].get("result_file") if isinstance(kwargs['function_args'], dict) else None
        else:
            result_file = kwargs.get("result_file")

        result = read_result(result_file)
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        error_msg = f"读取结果失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


# 导出函数
__all__ = [
    "register_orchestrator_tools",
    "handle_orchestrator_tool_call"
]


def handle_orchestrator_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """处理orchestrator工具调用（由conversation_loop调用）

    Args:
        tool_name: 工具名称
        tool_args: 工具参数

    Returns:
        Dict[str, Any]: 工具执行结果
    """
    try:
        # 根据工具名称调用相应的处理器
        tool_handlers = {
            "call_subagent": _call_subagent_handler,
            "list_subagents": _list_subagents_handler,
            "create_session": _create_session_handler,
            "read_result": _read_result_handler
        }

        if tool_name not in tool_handlers:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        # 调用处理器（传递正确的参数）
        handler = tool_handlers[tool_name]
        result_str = handler(
            function_name=tool_name,
            function_args=tool_args
        )

        # 解析JSON结果
        try:
            result = json.loads(result_str) if isinstance(result_str, str) else result_str
        except:
            result = {"result": result_str}

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Tool call failed: {str(e)}"
        }
