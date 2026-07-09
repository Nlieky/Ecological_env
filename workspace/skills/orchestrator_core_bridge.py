"""
桥接模块：将 orchestrator-core 目录桥接为 orchestrator_core

解决 Python 模块名不支持连字符的问题。
通过直接从 scripts 子模块导入并重新导出。
"""
import sys
from pathlib import Path

# 添加 scripts 目录到 Python 路径
scripts_dir = Path(__file__).parent / "orchestrator-core" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# 直接从 scripts 导入函数
# 使用相对路径导入，避免模块名问题
import importlib.util

# 加载 call_subagent 模块
call_subagent_path = scripts_dir / "call_subagent.py"
spec = importlib.util.spec_from_file_location("call_subagent_impl", call_subagent_path)
call_subagent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(call_subagent_module)

# 导出函数
call_subagent = call_subagent_module.call_subagent
SUBAGENT_PATHS = call_subagent_module.SUBAGENT_PATHS
RESULT_FILE_NAMES = call_subagent_module.RESULT_FILE_NAMES
generate_task_id = call_subagent_module.generate_task_id
get_session_dir = call_subagent_module.get_session_dir

# 加载 schemas 模块
schemas_path = scripts_dir / "schemas.py"
spec = importlib.util.spec_from_file_location("schemas_impl", schemas_path)
schemas_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schemas_module)

write_task_file = schemas_module.write_task_file

# 加载 create_session 模块
create_session_path = scripts_dir / "create_session.py"
spec = importlib.util.spec_from_file_location("create_session_impl", create_session_path)
create_session_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_session_module)

create_session = create_session_module.create_session

# 导出列表
__all__ = [
    "call_subagent",
    "read_result",
    "list_subagents",
    "create_session",
    "SUBAGENT_PATHS",
    "RESULT_FILE_NAMES",
    "write_task_file"
]


def read_result(result_file: str):
    """读取子智能体结果文件"""
    import json
    import os
    from pathlib import Path

    # 优先使用环境变量中的 SESSION_DIR
    session_dir = os.getenv('SESSION_DIR')
    if not session_dir:
        # 回退到 get_session_dir()
        session_dir = get_session_dir()

    if not session_dir:
        return {"error": "No session directory available"}

    result_path = Path(session_dir) / result_file

    if not result_path.exists():
        return {"error": f"Result file not found: {result_file}"}

    with open(result_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_subagents():
    """列出所有可用的子智能体"""
    agents = []
    for agent_id, path in SUBAGENT_PATHS.items():
        # 只返回完整名称的子智能体（包含 - 的）
        if "-" in agent_id:
            agents.append({
                "id": agent_id,
                "name": agent_id.replace("-", " ").replace("_", " ").title(),
                "path": path
            })
    return agents
