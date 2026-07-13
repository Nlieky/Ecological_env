#!/usr/bin/env python3
"""测试异常检测子智能体身份文件加载"""

import os
import sys
from pathlib import Path

# 设置环境变量
AGENT_DIR = Path(__file__).parent.resolve()
os.environ['HERMES_HOME'] = str(AGENT_DIR)
os.environ['SESSION_DIR'] = str(AGENT_DIR / "sessions" / "test_session")
os.environ['SUBAGENT_NAME'] = "anomaly-detection"
os.environ['LLM_BASE_URL'] = "https://api.longcat.chat/openai/v1"
os.environ['LLM_API_KEY'] = "ak_28r4aS8Fw0uw8779ib5pn5nJ3A33S"
os.environ['LLM_MODEL'] = "LongCat-2.0"

# 创建会话目录和任务文件
session_dir = Path(os.environ['SESSION_DIR'])
session_dir.mkdir(parents=True, exist_ok=True)

task_file = session_dir / "task.json"
with open(task_file, 'w', encoding='utf-8') as f:
    f.write('{"task_id": "test_001", "task": "检测最近24小时的异常数据"}')

print(f"[TEST] HERMES_HOME: {os.environ['HERMES_HOME']}")
print(f"[TEST] SESSION_DIR: {os.environ['SESSION_DIR']}")
print(f"[TEST] Task file: {task_file}")

# 导入并运行子智能体
from agent_main import run_hermes_agent

result = run_hermes_agent()

print(f"[TEST] Result status: {result.get('status')}")
if result.get('status') == 'completed':
    print("[TEST] SUCCESS - 身份文件加载测试通过")
else:
    print(f"[TEST] FAILED - {result.get('error', 'Unknown error')}")
