"""
异常检测子智能体工具
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
    "name": "anomaly_detection",
    "display_name": "异常检测子智能体",
    "workspace": "subagents/anomaly-detection-agent/",
    "description": "负责检测废水监测数据中的异常和违规模式",
    "capabilities": [
        "统计异常检测",
        "机器学习异常检测",
        "深度学习异常检测",
        "违规模式检测"
    ]
}

def anomaly_detection(task: str, params: dict = None) -> dict:
    """
    调用异常检测子智能体
    
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
    "name": "anomaly_detection",
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
                    "detection_method": {"type": "string", "enum": ["statistical", "ml", "dl", "specialized"]},
                    "threshold": {"type": "number"}
                }
            }
        },
        "required": ["task"]
    }
}

if __name__ == "__main__":
    # 测试调用
    result = anomaly_detection(
        task="检测pH值异常",
        params={"detection_method": "statistical", "threshold": 3.0}
    )
    print("Result:", result)
