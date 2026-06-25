"""
调用子智能体工具

通过 subprocess 调用子智能体执行任务，通过文件状态共享传递任务和结果。
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import time


# 子智能体路径映射（完整名称和简化名称）
SUBAGENT_PATHS = {
    # 完整名称
    "multi-dimensional-data-perception": "../subagents/multi-dimensional-data-perception-agent",
    "anomaly-detection": "../subagents/anomaly-detection-agent",
    "rule-reasoning": "../subagents/rule-reasoning-agent",
    "disposition-execution": "../subagents/disposition-execution-agent",
    # 简化名称（向后兼容）
    "data-perception": "../subagents/multi-dimensional-data-perception-agent",
    "anomaly": "../subagents/anomaly-detection-agent",
    "rule": "../subagents/rule-reasoning-agent",
    "disposition": "../subagents/disposition-execution-agent"
}

# 结果文件名映射（完整名称和简化名称）
RESULT_FILE_NAMES = {
    # 完整名称映射
    "multi-dimensional-data-perception": "data_result.json",
    "anomaly-detection": "anomaly_result.json",
    "rule-reasoning": "rule_result.json",
    "disposition-execution": "disposition_result.json",
    # 简化名称映射
    "data-perception": "data_result.json",
    "anomaly": "anomaly_result.json",
    "rule": "rule_result.json",
    "disposition": "disposition_result.json"
}


def get_session_dir() -> Optional[str]:
    """
    获取当前会话目录

    Returns:
        会话目录路径，如果未设置则尝试创建
    """
    session_dir = os.getenv('SESSION_DIR')
    if not session_dir:
        # 如果没有设置 SESSION_DIR，尝试创建新会话
        from .create_session import create_session
        session_dir = create_session()
        os.environ['SESSION_DIR'] = session_dir
    return session_dir


def generate_task_id() -> str:
    """生成任务 ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    return f"task_{timestamp}_{unique_id}"


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    调用子智能体执行任务

    Args:
        subagent_name: 子智能体名称（必须是 SUBAGENT_PATHS 中的键）
        task: 任务描述
        context: 上下文信息（可选）

    Returns:
        子智能体的执行结果
        {
            "task_id": str,
            "status": "completed" | "failed",
            "result": dict | None,
            "error": str | None,
            "metadata": dict
        }
    """
    # 验证子智能体名称
    if subagent_name not in SUBAGENT_PATHS:
        return {
            "task_id": generate_task_id(),
            "status": "failed",
            "result": None,
            "error": f"Unknown subagent: {subagent_name}",
            "metadata": {
                "subagent_name": subagent_name,
                "timestamp": datetime.now().isoformat()
            }
        }

    # 获取会话目录
    session_dir = get_session_dir()
    if not session_dir:
        return {
            "task_id": generate_task_id(),
            "status": "failed",
            "result": None,
            "error": "Failed to get or create session directory",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    # 生成任务 ID
    task_id = generate_task_id()

    # 构建任务对象
    task_obj = {
        "task_id": task_id,
        "task": task,
        "context": context or {},
        "output_format": "json",
        "timeout": 300
    }

    # 写入 task.json（使用 schema 验证）
    try:
        from .schemas import write_task_file
        task_file = write_task_file(Path(session_dir), task_obj)
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to write task.json: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    # 获取子智能体路径
    subagent_rel_path = SUBAGENT_PATHS[subagent_name]
    current_dir = Path(__file__).parent.parent.parent.parent
    subagent_path = (current_dir / subagent_rel_path).resolve()

    if not subagent_path.exists():
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Subagent directory not found: {subagent_path}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    # 设置环境变量
    env = os.environ.copy()
    env['HERMES_HOME'] = str(subagent_path)
    env['SESSION_DIR'] = session_dir
    env['SUBAGENT_NAME'] = subagent_name

    # 调用子智能体
    start_time = time.time()
    try:
        # 调用子智能体的 run_agent.py
        result = subprocess.run(
            ['python', 'run_agent.py'],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            cwd=str(subagent_path)
        )

        duration = time.time() - start_time

        if result.returncode != 0:
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": f"Subagent process failed: {result.stderr}",
                "metadata": {
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat(),
                    "stdout": result.stdout[:500] if result.stdout else "",
                    "stderr": result.stderr[:500] if result.stderr else ""
                }
            }

    except subprocess.TimeoutExpired:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": "Subagent timed out after 300 seconds",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to call subagent: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    # 读取结果文件
    result_file_name = RESULT_FILE_NAMES.get(subagent_name, f"{subagent_name}_result.json")
    result_file = Path(session_dir) / result_file_name

    if not result_file.exists():
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Result file not found: {result_file_name}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        # 验证任务 ID 匹配
        if result_data.get('task_id') != task_id:
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": f"Task ID mismatch: expected {task_id}, got {result_data.get('task_id')}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            }

        return result_data

    except json.JSONDecodeError as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to parse result JSON: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to read result file: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }


def main():
    """测试入口"""
    print("Testing call_subagent...")

    # 测试调用数据感知子智能体
    result = call_subagent(
        "multi-dimensional-data-perception",
        "获取最近24小时进水和出水数据"
    )

    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
