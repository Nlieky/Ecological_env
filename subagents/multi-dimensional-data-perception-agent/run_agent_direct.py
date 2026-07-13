#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子智能体直接执行器 - 绕过 LLM，直接调用算子

这是高性能版本，子智能体直接调用算子脚本处理数据，
而不通过 LLM。LLM 只在主智能体层做语义理解和决策。
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


def write_result(session_dir: str, result: Dict[str, Any], filename: str = "data_result.json") -> bool:
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


def execute_data_task(task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行数据任务 - 直接调用算子脚本

    Args:
        task_description: 任务描述
        context: 上下文信息

    Returns:
        执行结果
    """
    # 获取脚本目录
    agent_dir = Path(__file__).parent
    script_dir = agent_dir / "skills" / "data-perception-core" / "scripts"

    # 根据任务描述选择脚本
    if "24小时" in task_description or "24h" in task_description or "24 h" in task_description:
        script_file = script_dir / "fetch_24h_data.py"
    elif "异常" in task_description:
        script_file = script_dir / "fetch_24h_data.py"  # 先获取数据，异常检测由其他子智能体处理
    else:
        # 默认获取最近24小时数据
        script_file = script_dir / "fetch_24h_data.py"

    if not script_file.exists():
        return {
            "status": "failed",
            "error": f"Script not found: {script_file}",
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

    不使用 AIAgent，直接调用算子处理数据。
    """
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', 'unknown')

    logger.info(f"[DIRECT] 启动子智能体: {subagent_name}")
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
    result = execute_data_task(task_description, context)
    result["task_id"] = task_id
    result["subagent"] = subagent_name

    # 写入结果
    if session_dir:
        write_result(session_dir, result, "data_result.json")

    logger.info(f"[DIRECT] 任务完成: {result.get('status')}")
    return result


if __name__ == "__main__":
    result = run_hermes_agent()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 返回适当的退出码
    sys.exit(0 if result.get("status") == "completed" else 1)
