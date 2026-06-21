"""
多维数据感知子智能体工具
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
    "name": "multi_dimensional_data_perception",
    "display_name": "多维数据感知子智能体",
    "workspace": "subagents/multi-dimensional-data-perception-agent/",
    "description": "负责接入、预处理和标准化废水监测数据",
    "capabilities": [
        "实时数据接入",
        "历史数据查询",
        "数据清洗与对齐",
        "数据标准化"
    ]
}

def multi_dimensional_data_perception(task: str, params: dict = None) -> dict:
    """
    调用多维数据感知子智能体
    
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
    "name": "multi_dimensional_data_perception",
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
                    "data_type": {"type": "string", "enum": ["real_time", "historical"]},
                    "time_range": {"type": "string"},
                    "parameters": {"type": "object"}
                }
            }
        },
        "required": ["task"]
    }
}

if __name__ == "__main__":
    # 测试调用
    result = multi_dimensional_data_perception(
        task="获取最近24小时的实时监测数据",
        params={"data_type": "real_time", "time_range": "24h"}
    )
    print("Result:", result)
