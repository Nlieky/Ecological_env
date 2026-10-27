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
from subagent_registry import (
    known_subagent_names,
    prepare_result_target,
    resolve_subagent,
)


def _project_root() -> Path:
    """标记法找项目根(含 shared/ + workspace/)，位置无关——迁移后不会因目录深度算错。"""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "shared").is_dir() and (parent / "workspace").is_dir():
            return parent
    return p.parents[3]  # 兜底


def _param(key, env_key, default):
    """DB 优先读参数(backend 参数中心)；backend 不可导入时走 env——
    call_subagent 在 agent 服务进程内跑(tool_registration 已把项目根加进 sys.path)，
    正常都能导入。"""
    try:
        from backend.services.agent_params import get_param
        return get_param(key, env_key=env_key, default=default)
    except Exception:
        return os.getenv(env_key, str(default))


# 子智能体路径映射（完整名称和简化名称）
SUBAGENT_PATHS = {name: resolve_subagent(name).directory for name in known_subagent_names()}
RESULT_FILE_NAMES = {name: resolve_subagent(name).result_file for name in known_subagent_names()}


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
    current_dir = _project_root()
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
    try:
        subagent_spec = resolve_subagent(subagent_name)
    except ValueError:
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

    # A carried result is context only. Once this stage is requested, remove its
    # previous output before any later preflight can fail, so callers cannot
    # mistake an old file for this invocation's result.
    prepare_result_target(session_dir, subagent_spec.result_file)

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

    # 获取子智能体路径——SUBAGENT_PATHS 形如 "../subagents/X"(旧 workspace 相对约定)，
    # 去掉前导 ../ 后从项目根解析，与脚本自身位置无关
    subagent_path = (_project_root() / subagent_spec.directory).resolve()

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
    env['SUBAGENT_NAME'] = subagent_spec.name

    # 显式添加 LLM 配置环境变量（确保子进程能访问 LLM 服务）
    # Hermes Agent 框架期望 OPENAI_API_KEY，所以我们需要同时设置两者
    llm_base_url = os.environ.get('LLM_BASE_URL', 'http://172.xx.xx.xx:30000/v1')

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
    project_root = _project_root()
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

        # 调用共享的 subagent_entry.py（一份标准化入口，靠 HERMES_HOME/SUBAGENT_NAME 环境变量
        # 区分是哪个子智能体；不再每个子智能体目录各放一份 entry.py）。
        # 子智能体自身是一次完整 AIAgent 会话（多轮 LLM），ctgu-vlm 单次调用又慢，
        # 实测异常检测子智能体曾 >300s。默认 600s（可由 SUBAGENT_TIMEOUT 覆盖）。
        subagent_timeout = int(_param("subagent_timeout", "SUBAGENT_TIMEOUT", 600))
        shared_entry = Path(__file__).parent / "subagent_entry.py"
        result = subprocess.run(
            [python_exe, str(shared_entry)],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # 替换无法解码的字符
            timeout=subagent_timeout,
            cwd=str(subagent_path)
        )

        duration = time.time() - start_time

        # 可观测性：把子智能体 subprocess 的【完整 stdout+stderr】落盘到固定目录
        # sessions/_subagent_traces/<task_id>_<subagent>.log（不依赖 session 路由——
        # 此前写到 session 目录，失败时 session 串了就找不到，导致失败是黑盒）。
        # 无论成败都写，便于看清 LLM 敲了啥命令、脚本回了啥/为何报错。
        try:
            trace_dir = Path(session_dir).resolve().parent / "_subagent_traces"
            trace_dir.mkdir(parents=True, exist_ok=True)
            trace_file = trace_dir / f"{task_id}_{subagent_name}.log"
            trace_file.write_text(
                f"=== {subagent_name} | task_id={task_id} | duration={duration:.1f}s | "
                f"returncode={result.returncode} ===\n"
                f"--- STDOUT ---\n{result.stdout or '(空)'}\n"
                f"--- STDERR ---\n{result.stderr or '(空)'}\n",
                encoding='utf-8', errors='replace')
        except Exception:
            pass

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
            "error": (f"子智能体 [{subagent_name}] 超时（>{subagent_timeout}s）——"
                      f"该环节卡死。排查: sessions/_subagent_traces/{task_id}_{subagent_name}.log"),
            "metadata": {"timestamp": datetime.now().isoformat(),
                         "subagent": subagent_name,
                         "timeout_seconds": subagent_timeout}
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
    result_file_name = subagent_spec.result_file
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

        # 不再校验 task_id：subprocess.run 是同步的，结果文件必然属于本次调用。
        # 旧的跨进程 task_id 校验会和子智能体脚本自带的 task_id 格式（如 task_YYYYMMDD_HHMMSS，
        # 无 uuid）打架，偶发 "Task ID mismatch" 白耗 ~90s 并触发 LLM 无谓重试。
        # entry.py 已在写回时强制对齐 task_id，这里直接采用结果即可。
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
