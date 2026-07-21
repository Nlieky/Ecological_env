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
        会话目录路径，如果未设置或目录不存在则尝试创建
    """
    from pathlib import Path as PathClass
    import json
    import sys
    
    session_dir = os.getenv('SESSION_DIR')

    # 验证环境变量中的会话目录是否存在
    if session_dir:
        session_path = PathClass(session_dir)
        if session_path.exists() and session_path.is_dir():
            # 目录存在，直接返回
            return session_dir
        else:
            # 目录不存在，清除环境变量并创建新会话
            print(f"[WARN] SESSION_DIR points to non-existent directory: {session_dir}", file=sys.stderr, flush=True)
            os.environ['SESSION_DIR'] = ''
            session_dir = None

    # 如果没有有效的 SESSION_DIR，创建新会话
    # 使用内联实现避免相对导入问题
    from datetime import datetime

    # 获取项目根目录
    current_dir = PathClass(__file__).parent.parent.parent.parent.parent
    sessions_dir = current_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}"
    session_path = sessions_dir / session_name
    session_path.mkdir(exist_ok=True)

    # 创建会话元数据文件
    metadata = {
        "session_id": session_name,
        "created_at": datetime.now().isoformat(),
        "status": "initialized"
    }

    metadata_path = session_path / "_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    session_dir = str(session_path.absolute())
    os.environ['SESSION_DIR'] = session_dir
    print(f"[INFO] Created new session: {session_dir}", file=sys.stderr, flush=True)
    return session_dir


def generate_task_id() -> str:
    """生成任务 ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    return f"task_{timestamp}_{unique_id}"


def call_subagent(**kwargs) -> Dict[str, Any]:
    """
    调用子智能体执行任务

    Args (通过关键字参数传递):
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
    # 从关键字参数中提取必需参数
    subagent_name = kwargs.get('subagent_name') or kwargs.get('name')
    task = kwargs.get('task')
    context = kwargs.get('context')

    # 验证必需参数
    if not subagent_name:
        return {
            "task_id": generate_task_id(),
            "status": "failed",
            "result": None,
            "error": "Missing required parameter: subagent_name (or name)",
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }

    if not task:
        return {
            "task_id": generate_task_id(),
            "status": "failed",
            "result": None,
            "error": "Missing required parameter: task",
            "metadata": {
                "subagent_name": subagent_name,
                "timestamp": datetime.now().isoformat()
            }
        }

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

    # 写入 task.json（使用内联实现避免相对导入问题）
    try:
        # 验证任务对象
        required_fields = ["task_id", "task"]
        for field in required_fields:
            if field not in task_obj:
                raise ValueError(f"Missing required field: {field}")

        # 写入 task.json
        task_file = Path(session_dir) / "task.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_obj, f, indent=2, ensure_ascii=False)
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

    # 显式添加 LLM 配置环境变量（确保子进程能访问 LLM 服务）
    # Hermes Agent 框架期望 OPENAI_API_KEY，所以我们需要同时设置两者
    llm_base_url = os.environ.get('LLM_BASE_URL', 'http://172.16.12.41:30000/v1')

    # 安全检查：API Key 必须从环境变量获取
    llm_api_key = os.environ.get('LLM_API_KEY')
    if not llm_api_key:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": "LLM_API_KEY 环境变量未设置",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    llm_model = os.environ.get('LLM_MODEL', 'ctgu-vlm')
    llm_provider = os.environ.get('LLM_PROVIDER', 'custom')

    # 设置 LLM_* 变量
    env['LLM_BASE_URL'] = llm_base_url
    env['LLM_API_KEY'] = llm_api_key
    env['LLM_MODEL'] = llm_model
    env['LLM_PROVIDER'] = llm_provider

    # 设置 Hermes Agent 期望的 OPENAI_* 变量
    env['OPENAI_API_KEY'] = llm_api_key
    env['OPENAI_BASE_URL'] = llm_base_url

    # 添加 PYTHONPATH 以确保子进程能找到项目模块
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{project_root}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = str(project_root)

    # 调用子智能体
    start_time = time.time()
    try:
        # 使用当前 Python 解释器确保子进程使用正确的环境
        python_exe = sys.executable
        print(f"[DEBUG] Using Python: {python_exe}", file=sys.stderr, flush=True)

        # 调用子智能体的 entry.py（统一入口点，避免命名冲突）
        # 子智能体自身是一次完整 AIAgent 会话（多轮 LLM），60s 远不够，给到 180s。
        subagent_timeout = int(os.getenv('SUBAGENT_TIMEOUT', '180'))
        result = subprocess.run(
            [python_exe, 'entry.py'],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # 替换无法解码的字符
            timeout=subagent_timeout,
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
            "error": f"Subagent timed out after {subagent_timeout} seconds",
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
