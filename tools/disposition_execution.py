"""
研判预警与处置执行子智能体工具
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
    "name": "disposition_execution",
    "display_name": "研判预警与处置执行子智能体",
    "workspace": "subagents/disposition-execution-agent/",
    "description": "负责融合共识、预警分级和生成处置工单",
    "capabilities": [
        "融合共识",
        "预警分级",
        "工单生成",
        "处置建议"
    ]
}

def disposition_execution(task: str, params: dict = None) -> dict:
    """
    调用研判预警与处置执行子智能体
    
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
    "name": "disposition_execution",
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
                    "anomaly_results": {"type": "object"},
                    "rule_results": {"type": "object"},
                    "alert_level": {"type": "string", "enum": ["info", "warning", "critical"]}
                }
            }
        },
        "required": ["task"]
    }
}

if __name__ == "__main__":
    # 测试调用
    result = disposition_execution(
        task="生成预警工单",
        params={"alert_level": "warning"}
    )
    print("Result:", result)
