"""
直接测试会话共享机制
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 动态导入
import importlib.util

# 导入 call_subagent
spec = importlib.util.spec_from_file_location(
    "call_subagent",
    project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "call_subagent.py"
)
call_subagent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(call_subagent_module)

call_subagent = call_subagent_module.call_subagent

# 创建测试会话目录
with tempfile.TemporaryDirectory() as temp_dir:
    print(f"测试会话目录: {temp_dir}")

    # 设置环境变量
    os.environ['SESSION_DIR'] = temp_dir

    # 创建 task.json
    task_obj = {
        "task_id": "test_001",
        "task": "检测异常",
        "context": {},
        "output_format": "json",
        "timeout": 300
    }

    task_file = Path(temp_dir) / "task.json"
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task_obj, f, ensure_ascii=False)

    print(f"已创建任务文件: {task_file}")

    # 调用子智能体
    print("\n调用异常检测子智能体...")
    result = call_subagent('anomaly-detection', '检测异常', {})

    print(f"返回状态: {result.get('status')}")
    print(f"任务ID: {result.get('task_id')}")

    # 检查结果文件
    print(f"\n检查会话目录中的文件:")
    for file in Path(temp_dir).iterdir():
        print(f"  - {file.name}")

    # 检查期望的结果文件
    result_files = [
        "anomaly_result.json",
        "data_result.json",
        "result.json"
    ]

    for filename in result_files:
        result_file = Path(temp_dir) / filename
        if result_file.exists():
            print(f"\n[FOUND] {filename}")
            with open(result_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            print(f"内容: {json.dumps(content, indent=2, ensure_ascii=False)[:200]}...")
        else:
            print(f"\n[NOT FOUND] {filename}")

    # 检查子智能体自己的 sessions 目录
    agent_sessions = project_root / "subagents" / "anomaly-detection-agent" / "sessions"
    if agent_sessions.exists():
        print(f"\n检查子智能体的 sessions 目录: {agent_sessions}")
        recent_files = sorted(agent_sessions.glob("**/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for file in recent_files:
            print(f"  - {file.relative_to(agent_sessions)}")
