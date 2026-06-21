"""
规则推理子智能体工具
Hermes Agent Framework - 子智能体委托工具
"""

import sys
import os
from pathlib import Path

# 添加 Hermes 框架路径
HERMES_PATH = Path("D:/Hermes/hermes-agent")
if str(HERMES_PATH) not in sys.path:
    sys.path.insert(0, str(HERMES_PATH))

from tools.delegate_tool import delegate_tool

# 子智能体配置
SUBAGENT_CONFIG = {
    "name": "rule_reasoning",
    "display_name": "规则推理子智能体",
    "workspace": "subagents/rule-reasoning-agent/",
    "description": "负责基于法规和专家知识进行规则推理和违规判定",
    "capabilities": [
        "法规合规性校验",
        "工艺机理推理",
        "专家经验应用",
        "违规判定"
    ]
}

def rule_reasoning(task: str, params: dict = None) -> dict:
    """
    调用规则推理子智能体
    
    Args:
        task: 任务描述
        params: 任务参数
        
    Returns:
        子智能体执行结果
    """
    return delegate_tool(
        subagent_name=SUBAGENT_CONFIG["name"],
        workspace=SUBAGENT_CONFIG["workspace"],
        task=task,
        params=params or {}
    )


# 工具定义（供 Hermes 注册）
TOOL_DEFINITION = {
    "name": "rule_reasoning",
    "description": SUBAGENT_CONFIG["description"],
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "任务描述"
            },
            "params": {
                "type": "object",
                "description": "任务参数",
                "properties": {
                    "data": {"type": "object"},
                    "regulation_type": {"type": "string"},
                    "knowledge_base": {"type": "string", "enum": ["regulations", "process", "expert"]}
                }
            }
        },
        "required": ["task"]
    }
}

if __name__ == "__main__":
    # 测试调用
    result = rule_reasoning(
        task="校验COD排放是否符合GB18918-2002标准",
        params={"regulation_type": "GB18918-2002", "knowledge_base": "regulations"}
    )
    print("Result:", result)
