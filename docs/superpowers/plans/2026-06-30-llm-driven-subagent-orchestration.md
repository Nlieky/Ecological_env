# LLM 驱动的子智能体编排实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 实现主智能体通过 LLM 驱动的方式动态调用子智能体，每个子智能体加载自己的身份文件并完成任务。

**架构:** 主智能体通过工具集（subagent_tools.py）调用子智能体，子智能体通过 subprocess 启动并加载自己的身份文件，通过 sessions/ 目录通信。

**技术栈:** Python 3.8+, Hermes Agent 框架, subprocess, JSON

---

## 文件结构

```
workspace/skills/orchestrator-core/scripts/
├── subagent_tools.py       # 新建 - 主智能体工具集
├── call_subagent.py        # 现有 - 子智能体调用（已存在）
├── create_session.py       # 现有 - 会话管理（已存在）
├── cleanup_sessions.py     # 现有 - 会话清理（已存在）
└── schemas.py             # 现有 - 数据模式（已存在）

subagents/
├── anomaly-detection-agent/
├── rule-reasoning-agent/
├── disposition-execution-agent/
└── multi-dimensional-data-perception-agent/
    └── run_agent_wrapper.py   # 修改 - 添加 .env 加载

sessions/
└── {session_id}/
    ├── task.json
    └── *_result.json
```

---

## 任务分解

### Task 1: 修复子智能体的 .env 加载问题

**问题确认:** 在之前的验证中，发现 `run_agent_wrapper.py` 没有加载 `.env` 文件，导致环境变量不可用。

**文件:**
- Modify: `subagents/*/run_agent_wrapper.py` (如果存在)
- 或者确保每个子智能体的入口点加载 `.env`

首先检查哪些子智能体需要这个修复：

- [ ] **Step 1: 检查子智能体入口点**

```bash
cd e:/project/Ecological_env/subagents
for dir in */; do
    echo "=== $dir ==="
    if [ -f "${dir}run_agent.py" ]; then
        echo "Has run_agent.py"
    fi
    if [ -f "${dir}run_agent_wrapper.py" ]; then
        echo "Has run_agent_wrapper.py"
    fi
done
```

- [ ] **Step 2: 修复 run_agent_wrapper.py 的 .env 加载**

在 `subagents/run_agent_wrapper.py` 开头添加（已修复）：

```python
from dotenv import load_dotenv

# 加载 .env 从项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"[INFO] Loaded .env from {ENV_FILE}", file=sys.stderr, flush=True)
```

- [ ] **Step 3: 验证 .env 加载**

```bash
cd e:/project/Ecological_env/subagents/anomaly-detection-agent
python -c "
from dotenv import load_dotenv
from pathlib import Path
PROJECT_ROOT = Path.cwd().parent.parent
load_dotenv(PROJECT_ROOT / '.env')
import os
print(f'LLM_API_KEY: {os.environ.get(\"LLM_API_KEY\", \"NOT_SET\")[:10]}...')
"
```

- [ ] **Step 4: 提交修复**

```bash
git add subagents/run_agent_wrapper.py
git commit -m "fix: add .env loading to subagent wrapper"
```

---

### Task 2: 创建 subagent_tools.py 工具定义文件

**文件:**
- Create: `workspace/skills/orchestrator-core/scripts/subagent_tools.py`

- [ ] **Step 1: 创建工具定义文件**

```python
"""
主智能体工具集 - 子智能体调用工具

供主智能体通过 LLM 调用，实现动态子智能体编排。
"""

from typing import Dict, Any, List, Optional


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    调用子智能体执行任务
    
    Args:
        subagent_name: 子智能体名称 (如 "anomaly-detection")
        task: 任务描述
        context: 上一个子智能体的结果（可选）
    
    Returns:
        {
            "task_id": str,
            "status": "completed" | "failed",
            "result": dict | None,
            "error": str | None,
            "metadata": {
                "duration_seconds": float,
                "timestamp": str,
                "subagent_name": str
            }
        }
    
    Raises:
        ValueError: 未知子智能体名称
        IOError: 会话目录创建失败
    """
    from .call_subagent import call_subagent as _call_subagent
    return _call_subagent(subagent_name, task, context)


def read_result(result_file: str) -> Dict[str, Any]:
    """
    读取子智能体结果文件
    
    Args:
        result_file: 结果文件路径（相对于 sessions/{session_id}/）
    
    Returns:
        结果数据字典
    """
    import json
    from pathlib import Path
    from .create_session import get_session_dir
    
    session_dir = get_session_dir()
    result_path = Path(session_dir) / result_file
    
    if not result_path.exists():
        return {"error": f"Result file not found: {result_file}"}
    
    with open(result_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_subagents() -> List[Dict[str, str]]:
    """
    列出所有可用的子智能体
    
    Returns:
        [
            {"id": "anomaly-detection", "name": "异常检测子智能体", "path": "..."},
            {"id": "rule-reasoning", "name": "规则推理子智能体", "path": "..."},
            ...
        ]
    """
    from .call_subagent import SUBAGENT_PATHS
    
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


def create_session() -> str:
    """
    创建新的会话目录
    
    Returns:
        session_id: 会话ID（用于通信）
    """
    from .create_session import create_session as _create_session
    return _create_session()
```

- [ ] **Step 2: 验证文件创建成功**

```bash
python -c "import sys; sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts'); from subagent_tools import call_subagent; print('Import OK')"
```

- [ ] **Step 3: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/subagent_tools.py
git commit -m "feat: add subagent tools for LLM-driven orchestration"
```

---

### Task 3: 确保 call_subagent.py 正确工作

**文件:**
- Review: `workspace/skills/orchestrator-core/scripts/call_subagent.py`
- Review: `workspace/skills/orchestrator-core/scripts/create_session.py`
- Review: `workspace/skills/orchestrator-core/scripts/schemas.py`

- [ ] **Step 1: 检查现有 call_subagent.py 是否完整**

检查以下功能是否存在：
- `SUBAGENT_PATHS` - 子智能体路径映射
- `RESULT_FILE_NAMES` - 结果文件名映射
- `call_subagent()` 函数
- `get_session_dir()` 函数

```bash
grep -n "def call_subagent" workspace/skills/orchestrator-core/scripts/call_subagent.py
grep -n "SUBAGENT_PATHS" workspace/skills/orchestrator-core/scripts/call_subagent.py
```

- [ ] **Step 2: 检查 create_session.py 是否完整**

```bash
grep -n "def create_session" workspace/skills/orchestrator-core/scripts/create_session.py
grep -n "def get_session_dir" workspace/skills/orchestrator-core/scripts/create_session.py
```

- [ ] **Step 3: 检查 schemas.py 是否有 write_task_file 函数**

```bash
grep -n "def write_task_file" workspace/skills/orchestrator-core/scripts/schemas.py
```

- [ ] **Step 4: 如果缺少任何功能，补充缺失的代码**

（根据检查结果，如果缺少则补充）

---

### Task 4: 创建 __init__.py 导出工具

**文件:**
- Modify: `workspace/skills/orchestrator-core/scripts/__init__.py`

- [ ] **Step 1: 更新 __init__.py 导出工具**

```python
"""
Orchestrator Core Scripts

主智能体编排器核心脚本。
"""

from .subagent_tools import (
    call_subagent,
    read_result,
    list_subagents,
    create_session
)

__all__ = [
    "call_subagent",
    "read_result", 
    "list_subagents",
    "create_session"
]
```

- [ ] **Step 2: 验证导入**

```bash
python -c "
from workspace.skills.orchestrator_core.scripts import call_subagent, read_result, list_subagents, create_session
print('All imports OK')
"
```

- [ ] **Step 3: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/__init__.py
git commit -m "feat: export subagent tools from __init__.py"
```

---

### Task 5: 测试子智能体调用

**文件:**
- Create: `tests/integration/test_subagent_tools.py`

- [ ] **Step 1: 创建集成测试文件**

```python
"""
测试子智能体工具集
"""
import os
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "workspace/skills/orchestrator-core/scripts"))

def test_list_subagents():
    """测试列出子智能体"""
    from subagent_tools import list_subagents
    
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
    from subagent_tools import create_session
    import re
    
    session_id = create_session()
    
    assert session_id is not None
    assert isinstance(session_id, str)
    assert len(session_id) > 0
    
    # session_id 格式应该是 session_YYYYMMDD_HHMMSS_xxxxxxxx
    assert re.match(r"session_\d{8}_\d{6}_[a-f0-9]{8}", session_id), f"Invalid session_id format: {session_id}"
    
    print(f"✓ Created session: {session_id}")

def test_call_subagent_simple():
    """测试简单子智能体调用"""
    from subagent_tools import call_subagent
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
    from subagent_tools import create_session, read_result
    import json
    
    # 先创建一个测试结果文件
    from subagent_tools import call_subagent
    
    session_id = create_session()
    result = call_subagent(
        subagent_name="multi-dimensional-data-perception",
        task="返回测试数据"
    )
    
    if result["status"] == "completed":
        # 读取结果
        from pathlib import Path
        import os
        
        session_dir = os.environ.get("SESSION_DIR")
        if session_dir:
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
```

- [ ] **Step 2: 运行测试**

```bash
cd e:/project/Ecological_env
python tests/integration/test_subagent_tools.py
```

预期输出：看到每个测试的 ✓ 标记

- [ ] **Step 3: 提交测试文件**

```bash
git add tests/integration/test_subagent_tools.py
git commit -m "test: add subagent tools integration tests"
```

---

### Task 6: 确保 sessions 目录存在

**文件:**
- Create: `sessions/.gitkeep`

- [ ] **Step 1: 创建 sessions 目录**

```bash
mkdir -p sessions
echo "# This directory stores communication files between master agent and subagents" > sessions/.gitkeep
```

- [ ] **Step 2: 提交**

```bash
git add sessions/.gitkeep
git commit -m "chore: add sessions directory for agent communication"
```

---

### Task 7: 更新 SKILL.md 文档

**文件:**
- Modify: `workspace/skills/orchestrator-core/SKILL.md`

- [ ] **Step 1: 检查 SKILL.md 当前内容**

```bash
head -50 workspace/skills/orchestrator-core/SKILL.md
```

- [ ] **Step 2: 添加工具集说明**

在 SKILL.md 中添加：

```markdown
## 工具集

主智能体可以通过以下工具调用子智能体：

### call_subagent(subagent_name, task, context)
调用指定的子智能体执行任务。

### read_result(result_file)
读取子智能体的执行结果。

### list_subagents()
列出所有可用的子智能体。

### create_session()
创建新的会话目录。

## 调用流程

1. 用户请求 → 主智能体加载身份文件
2. LLM 理解任务并规划
3. create_session() 创建会话
4. call_subagent() 调用子智能体
5. read_result() 读取结果
6. LLM 整合并返回用户
```

- [ ] **Step 3: 提交**

```bash
git add workspace/skills/orchestrator-core/SKILL.md
git commit -m "docs: add tools documentation to SKILL.md"
```

---

## 验证清单

完成所有任务后，运行以下验证：

- [ ] 验证子智能体能加载身份文件
- [ ] 验证主智能体能通过工具集调用子智能体
- [ ] 验证 sessions 目录正确创建和清理
- [ ] 验证错误处理机制正常工作

```bash
# 完整验证
cd e:/project/Ecological_env
python tests/integration/test_subagent_tools.py
```

---

## 预期结果

完成后，主智能体将能够：

1. 通过 LLM 理解任务
2. 使用 `subagent_tools.py` 工具集动态调用子智能体
3. 每个子智能体加载自己的身份文件（SOUL.md、AGENTS.md）
4. 通过 sessions/ 目录进行通信
5. LLM 整合结果并返回用户
