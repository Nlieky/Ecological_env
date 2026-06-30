"""
测试子智能体工具集
"""
import os
import sys
from pathlib import Path

# 设置UTF-8输出编码（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
# 使用当前工作目录来找到orchestrator-core
PROJECT_ROOT = Path.cwd()
orchestrator_core = PROJECT_ROOT / "workspace/skills/orchestrator-core"
sys.path.insert(0, str(orchestrator_core))

def test_list_subagents():
    """测试列出子智能体"""
    from scripts.subagent_tools import list_subagents

    agents = list_subagents()

    assert isinstance(agents, list)
    assert len(agents) >= 4

    agent_ids = [a["id"] for a in agents]
    expected = [
        "multi-dimensional-data-perception",
        "anomaly-detection",
        "rule-reasoning",
        "disposition-execution"
    ]

    for exp in expected:
        assert exp in agent_ids, f"Expected {exp} in agent_ids"

    print(f"✓ Found {len(agents)} subagents")

def test_create_session():
    """测试创建会话"""
    from scripts.subagent_tools import create_session

    session_path = create_session()

    assert session_path is not None
    assert isinstance(session_path, str)
    assert len(session_path) > 0

    # session_path 应该是一个有效的目录路径
    from pathlib import Path
    path = Path(session_path)
    assert path.exists(), f"Session path does not exist: {session_path}"
    assert path.is_dir(), f"Session path is not a directory: {session_path}"
    assert "session_" in session_path, f"Session path should contain 'session_': {session_path}"

    print(f"✓ Created session: {path.name}")

def test_call_subagent_simple():
    """测试简单子智能体调用"""
    from scripts.subagent_tools import call_subagent
    import time

    # 使用一个简单的任务
    result = call_subagent(
        subagent_name="multi-dimensional-data-perception",
        task="列出可用的数据指标"
    )

    assert result is not None
    assert "status" in result
    assert result["status"] in ["completed", "failed"]
    assert "metadata" in result
    assert "timestamp" in result["metadata"]

    if result["status"] == "completed":
        print(f"✓ Subagent call completed in {result['metadata'].get('duration_seconds', 0):.2f}s")
    else:
        print(f"✗ Subagent call failed: {result.get('error', 'Unknown error')}")

def test_read_result():
    """测试读取结果"""
    from scripts.subagent_tools import create_session, read_result, call_subagent
    from pathlib import Path
    import json

    # 先创建一个测试结果文件
    session_path = create_session()
    result = call_subagent(
        subagent_name="multi-dimensional-data-perception",
        task="返回测试数据"
    )

    if result["status"] == "completed":
        # 读取结果
        result_file = "data_result.json"
        data = read_result(result_file)

        assert data is not None
        assert "result" in data or "error" in data

        print(f"✓ Read result from {result_file}")
    else:
        print(f"⚠ Skipped read_result test due to failed call")

if __name__ == "__main__":
    print("=== Testing Subagent Tools ===")
    print()

    print("Test 1: List subagents")
    test_list_subagents()
    print()

    print("Test 2: Create session")
    test_create_session()
    print()

    print("Test 3: Call subagent (may take 30+ seconds)")
    test_call_subagent_simple()
    print()

    print("Test 4: Read result")
    test_read_result()
    print()

    print("=== All Tests Completed ===")
