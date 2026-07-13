#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测子智能体 - 直接执行版本

绕过 LLM，直接调用异常检测算子。
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_task(session_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    """从会话目录加载任务"""
    if not session_dir:
        return None

    session_path = Path(session_dir).resolve()
    task_file = session_path / "task.json"
    if not task_file.exists():
        return None

    try:
        with open(task_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load task: {e}")
        return None


def write_result(session_dir: str, result: Dict[str, Any], filename: str = "anomaly_result.json") -> bool:
    """将结果写入会话目录"""
    try:
        session_path = Path(session_dir).resolve()
        result_file = session_path / filename
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to write result: {e}")
        return False


def execute_anomaly_detection(task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行异常检测 - 直接调用算子脚本

    Args:
        task_description: 任务描述
        context: 上下文信息

    Returns:
        执行结果
    """
    # 获取脚本目录
    agent_dir = Path(__file__).parent
    script_dir = agent_dir / "skills" / "anomaly-detection-core" / "scripts"

    # 选择主脚本
    script_file = script_dir / "run_anomaly_detection.py"

    if not script_file.exists():
        # 回退到简化版本
        script_file = script_dir / "run_anomaly_detection_simple.py"

    if not script_file.exists():
        return {
            "status": "failed",
            "error": f"Anomaly detection script not found",
            "timestamp": datetime.now().isoformat()
        }

    # 直接执行脚本
    try:
        result = subprocess.run(
            [sys.executable, str(script_file)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,  # 60秒超时
            cwd=str(agent_dir)
        )

        if result.returncode != 0:
            return {
                "status": "failed",
                "error": f"Script execution failed: {result.stderr}",
                "timestamp": datetime.now().isoformat()
            }

        # 解析脚本输出
        try:
            output_data = json.loads(result.stdout)
            return {
                "status": "completed",
                "result": output_data,
                "timestamp": datetime.now().isoformat()
            }
        except json.JSONDecodeError:
            # 如果输出不是JSON，尝试提取结果
            return {
                "status": "completed",
                "result": {"raw_output": result.stdout},
                "timestamp": datetime.now().isoformat()
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "error": "Script execution timed out",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def run_hermes_agent() -> Dict[str, Any]:
    """
    子智能体主入口点 - 直接执行版本
    """
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', 'unknown')

    logger.info(f"[DIRECT] 启动异常检测子智能体")
    logger.info(f"[DIRECT] SESSION_DIR: {session_dir}")

    # 读取任务
    task = load_task(session_dir)
    if not task:
        return {
            "status": "failed",
            "error": "Failed to load task",
            "task_id": "unknown",
            "timestamp": datetime.now().isoformat()
        }

    task_id = task.get('task_id', 'unknown')
    task_description = task.get('task', '')
    context = task.get('context', {})

    logger.info(f"[DIRECT] 任务: {task_description}")

    # 执行任务
    result = execute_anomaly_detection(task_description, context)
    result["task_id"] = task_id
    result["subagent"] = subagent_name

    # 写入结果
    if session_dir:
        write_result(session_dir, result, "anomaly_result.json")

    logger.info(f"[DIRECT] 任务完成: {result.get('status')}")
    return result


if __name__ == "__main__":
    result = run_hermes_agent()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("status") == "completed" else 1)
