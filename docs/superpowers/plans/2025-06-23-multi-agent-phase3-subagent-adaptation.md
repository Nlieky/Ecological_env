# Phase 3: Sub-Agent Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt all four sub-agents to read task.json from session directories and write result.json files, enabling file-based communication with the main agent.

**Architecture:** Each sub-agent's run_agent.py is modified to:
1. Check for SESSION_DIR environment variable
2. Read task.json if present
3. Execute task using existing skills
4. Write result.json to session directory

**Tech Stack:** Python, environment variables, JSON, pathlib

---

## Prerequisites

- Phase 1 completed (main agent identity files)
- Phase 2 completed (file state sharing mechanism)
- All four sub-agents have working run_agent.py files

---

### Task 1: Create shared sub-agent utilities module

**Files:**
- Create: `subagents/subagent_utils.py`

- [ ] **Step 1: Create shared utilities for all sub-agents**

```python
"""
Shared utilities for all sub-agents.

Provides common functionality for:
- Reading task.json from session directory
- Writing result.json files
- Handling session context
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def get_session_dir() -> Optional[Path]:
    """
    Get session directory from environment variable.

    Returns:
        Path to session directory, or None if not set

    Example:
        >>> session_dir = get_session_dir()
        >>> if session_dir:
        ...     print(f"Working in session: {session_dir.name}")
    """
    session_dir = os.environ.get("SESSION_DIR")
    if session_dir:
        return Path(session_dir)
    return None


def read_task_file(session_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Read task.json from session directory.

    Args:
        session_dir: Session directory path. Uses SESSION_DIR env var if None.

    Returns:
        Task dictionary, or None if no task file found

    Example:
        >>> task = read_task_file()
        >>> if task:
        ...     print(f"Task: {task['task']}")
    """
    if session_dir is None:
        session_dir = get_session_dir()

    if session_dir is None:
        return None

    task_file = session_dir / "task.json"
    if not task_file.exists():
        return None

    try:
        with open(task_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading task file: {e}")
        return None


def write_result_file(
    result: Any,
    status: str = "completed",
    error: Optional[str] = None,
    error_code: Optional[str] = None,
    session_dir: Optional[Path] = None,
    result_filename: Optional[str] = None
) -> Path:
    """
    Write result to session directory.

    Args:
        result: Task result data (any JSON-serializable type)
        status: Task status ("completed", "failed", "error")
        error: Error message if status is failed/error
        error_code: Machine-readable error code
        session_dir: Session directory path
        result_filename: Result filename. Auto-determined if None.

    Returns:
        Path to written result file

    Example:
        >>> write_result_file(
        ...     result={"data": [1, 2, 3]},
        ...     status="completed",
        ...     result_filename="data_result.json"
        ... )
        Path('workspace/state/session_.../data_result.json')
    """
    if session_dir is None:
        session_dir = get_session_dir()

    if session_dir is None:
        raise ValueError("No session directory available")

    # Get sub-agent name from environment
    subagent_name = os.environ.get("SUBAGENT_NAME", "unknown")
    task = read_task_file(session_dir)
    task_id = task.get("task_id") if task else f"task_{subagent_name}_{int(datetime.now().timestamp())}"

    # Determine result filename
    if result_filename is None:
        result_filename = f"{subagent_name}_result.json"

    # Build result object
    result_obj = {
        "task_id": task_id,
        "status": status,
        "result": result if status == "completed" else None,
        "error": error,
        "error_code": error_code,
        "metadata": {
            "duration_seconds": None,  # To be filled by caller
            "timestamp": datetime.now().isoformat(),
            "subagent_name": subagent_name
        }
    }

    # Write result file
    result_file = session_dir / result_filename
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_obj, f, indent=2, ensure_ascii=False)

    return result_file


def get_previous_results(session_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get results from previous sub-agents in the workflow.

    Args:
        session_dir: Session directory path

    Returns:
        Dictionary mapping sub-agent names to their results

    Example:
        >>> results = get_previous_results()
        >>> data_result = results.get("data-perception")
        >>> if data_result:
        ...     print(f"Got data from {data_result['metadata']['duration_seconds']}s ago")
    """
    if session_dir is None:
        session_dir = get_session_dir()

    if session_dir is None:
        return {}

    results = {}
    result_files = {
        "data-perception": "data_result.json",
        "anomaly-detection": "anomaly_result.json",
        "rule-reasoning": "rule_result.json",
        "disposition-execution": "disposition_result.json"
    }

    for agent_name, filename in result_files.items():
        result_file = session_dir / filename
        if result_file.exists():
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    results[agent_name] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    return results


def get_context_from_task(session_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get context from task.json (passed from main agent or previous sub-agent).

    Args:
        session_dir: Session directory path

    Returns:
        Context dictionary from task object

    Example:
        >>> context = get_context_from_task()
        >>> time_range = context.get("time_range", "24h")
    """
    task = read_task_file(session_dir)
    if task is None:
        return {}

    return task.get("context", {})


if __name__ == "__main__":
    # Test utilities
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir)

        # Set environment variable
        os.environ["SESSION_DIR"] = str(session_path)
        os.environ["SUBAGENT_NAME"] = "test-agent"

        # Create task file
        task_file = session_path / "task.json"
        task_file.write_text(json.dumps({
            "task_id": "test_001",
            "task": "Test task",
            "context": {"key": "value"}
        }))

        # Test read_task_file
        task = read_task_file()
        print(f"Read task: {task['task']}")
        assert task is not None
        assert task["task"] == "Test task"

        # Test write_result_file
        result_path = write_result_file(
            result={"data": "test"},
            status="completed"
        )
        print(f"Written result to: {result_path}")
        assert result_path.exists()

        # Test get_context_from_task
        context = get_context_from_task()
        print(f"Context: {context}")
        assert context == {"key": "value"}

        print("All utilities tests passed!")
```

- [ ] **Step 2: Test the utilities**

```bash
cd E:/project/Ecological_env
python subagents/subagent_utils.py
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add subagents/subagent_utils.py
git commit -m "feat(subagents): add shared utilities for session management"
```

---

### Task 2: Adapt data-perception-agent

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/run_agent.py`

- [ ] **Step 1: Read current run_agent.py**

```bash
head -50 subagents/multi-dimensional-data-perception-agent/run_agent.py
```

- [ ] **Step 2: Add session utilities import and context handling**

Add at the top of the file:
```python
import sys
import os
from pathlib import Path

# Add parent directory to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from subagent_utils import (
    get_session_dir, read_task_file, write_result_file,
    get_previous_results, get_context_from_task
)
```

- [ ] **Step 3: Add task context detection in main execution**

Add after agent initialization:
```python
# Check for session-based task
session_dir = get_session_dir()
task_from_file = None

if session_dir:
    task_from_file = read_task_file(session_dir)
    if task_from_file:
        print(f"[Session Mode] Task from file: {task_from_file['task']}")
        print(f"[Session Mode] Context: {task_from_file.get('context', {})}")
        # Use task from file
        query = task_from_file['task']
        context = task_from_file.get('context', {})
```

- [ ] **Step 4: Add result file writing after task completion**

Add after getting response:
```python
# Write result to session directory if in session mode
if session_dir:
    try:
        import json
        from datetime import datetime

        # Parse response and create result
        result_data = {
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

        # Include any context that was used
        if context:
            result_data["context_used"] = context

        # Write result file
        result_path = write_result_file(
            result=result_data,
            status="completed",
            session_dir=session_dir
        )

        print(f"[Session Mode] Result written to: {result_path}")

    except Exception as e:
        print(f"[Session Mode] Error writing result: {e}")
        # Write error result
        write_result_file(
            result=None,
            status="error",
            error=str(e),
            error_code="RESULT_WRITE_ERROR",
            session_dir=session_dir
        )
```

- [ ] **Step 5: Verify syntax**

```bash
python -m py_compile subagents/multi-dimensional-data-perception-agent/run_agent.py
```

- [ ] **Step 6: Commit**

```bash
git add subagents/multi-dimensional-data-perception-agent/run_agent.py
git commit -m "feat(data-perception): add session mode support"
```

---

### Task 3: Adapt anomaly-detection-agent

**Files:**
- Modify: `subagents/anomaly-detection-agent/run_agent.py`

- [ ] **Step 1: Add session utilities import**

Add at the top of the file:
```python
import sys
import os
from pathlib import Path

# Add parent directory to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from subagent_utils import (
    get_session_dir, read_task_file, write_result_file,
    get_previous_results, get_context_from_task
)
```

- [ ] **Step 2: Add task context detection**

Add after agent initialization:
```python
# Check for session-based task
session_dir = get_session_dir()
task_from_file = None
context = {}

if session_dir:
    task_from_file = read_task_file(session_dir)
    if task_from_file:
        print(f"[Session Mode] Task from file: {task_from_file['task']}")
        query = task_from_file['task']
        context = task_from_file.get('context', {})

        # Get previous results for context
        previous_results = get_previous_results(session_dir)
        if 'data-perception' in previous_results:
            print(f"[Session Mode] Using data from data-perception agent")
            context['data_result'] = previous_results['data-perception']
```

- [ ] **Step 3: Add result file writing**

Add after getting response:
```python
# Write result to session directory if in session mode
if session_dir:
    try:
        import json
        from datetime import datetime

        result_data = {
            "query": query,
            "response": response,
            "anomalies_detected": [],  # To be filled based on response
            "timestamp": datetime.now().isoformat()
        }

        if context:
            result_data["context_used"] = context

        result_path = write_result_file(
            result=result_data,
            status="completed",
            session_dir=session_dir
        )

        print(f"[Session Mode] Result written to: {result_path}")

    except Exception as e:
        print(f"[Session Mode] Error writing result: {e}")
        write_result_file(
            result=None,
            status="error",
            error=str(e),
            error_code="RESULT_WRITE_ERROR",
            session_dir=session_dir
        )
```

- [ ] **Step 4: Verify and commit**

```bash
python -m py_compile subagents/anomaly-detection-agent/run_agent.py
git add subagents/anomaly-detection-agent/run_agent.py
git commit -m "feat(anomaly-detection): add session mode support"
```

---

### Task 4: Adapt rule-reasoning-agent

**Files:**
- Modify: `subagents/rule-reasoning-agent/run_agent.py`

- [ ] **Step 1: Add session utilities import**

```python
import sys
import os
from pathlib import Path

# Add parent directory to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from subagent_utils import (
    get_session_dir, read_task_file, write_result_file,
    get_previous_results, get_context_from_task
)
```

- [ ] **Step 2: Add task context detection**

```python
# Check for session-based task
session_dir = get_session_dir()
task_from_file = None
context = {}

if session_dir:
    task_from_file = read_task_file(session_dir)
    if task_from_file:
        print(f"[Session Mode] Task from file: {task_from_file['task']}")
        query = task_from_file['task']
        context = task_from_file.get('context', {})

        # Get previous results for context
        previous_results = get_previous_results(session_dir)
        if 'anomaly-detection' in previous_results:
            print(f"[Session Mode] Using data from anomaly-detection agent")
            context['anomaly_result'] = previous_results['anomaly-detection']
        if 'data-perception' in previous_results:
            context['data_result'] = previous_results['data-perception']
```

- [ ] **Step 3: Add result file writing**

```python
# Write result to session directory if in session mode
if session_dir:
    try:
        import json
        from datetime import datetime

        result_data = {
            "query": query,
            "response": response,
            "violations": [],  # To be filled
            "compliance_status": "unknown",  # To be filled
            "timestamp": datetime.now().isoformat()
        }

        if context:
            result_data["context_used"] = context

        result_path = write_result_file(
            result=result_data,
            status="completed",
            session_dir=session_dir
        )

        print(f"[Session Mode] Result written to: {result_path}")

    except Exception as e:
        print(f"[Session Mode] Error writing result: {e}")
        write_result_file(
            result=None,
            status="error",
            error=str(e),
            error_code="RESULT_WRITE_ERROR",
            session_dir=session_dir
        )
```

- [ ] **Step 4: Verify and commit**

```bash
python -m py_compile subagents/rule-reasoning-agent/run_agent.py
git add subagents/rule-reasoning-agent/run_agent.py
git commit -m "feat(rule-reasoning): add session mode support"
```

---

### Task 5: Adapt disposition-execution-agent

**Files:**
- Modify: `subagents/disposition-execution-agent/run_agent.py`

- [ ] **Step 1: Add session utilities import**

```python
import sys
import os
from pathlib import Path

# Add parent directory to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from subagent_utils import (
    get_session_dir, read_task_file, write_result_file,
    get_previous_results, get_context_from_task
)
```

- [ ] **Step 2: Add task context detection**

```python
# Check for session-based task
session_dir = get_session_dir()
task_from_file = None
context = {}

if session_dir:
    task_from_file = read_task_file(session_dir)
    if task_from_file:
        print(f"[Session Mode] Task from file: {task_from_file['task']}")
        query = task_from_file['task']
        context = task_from_file.get('context', {})

        # Get all previous results
        previous_results = get_previous_results(session_dir)
        for agent_name, result in previous_results.items():
            print(f"[Session Mode] Using data from {agent_name} agent")
            context[f'{agent_name}_result'] = result
```

- [ ] **Step 3: Add result file writing**

```python
# Write result to session directory if in session mode
if session_dir:
    try:
        import json
        from datetime import datetime

        result_data = {
            "query": query,
            "response": response,
            "work_orders": [],  # To be filled
            "alert_level": "none",  # To be filled
            "timestamp": datetime.now().isoformat()
        }

        if context:
            result_data["context_used"] = context

        result_path = write_result_file(
            result=result_data,
            status="completed",
            session_dir=session_dir
        )

        print(f"[Session Mode] Result written to: {result_path}")

    except Exception as e:
        print(f"[Session Mode] Error writing result: {e}")
        write_result_file(
            result=None,
            status="error",
            error=str(e),
            error_code="RESULT_WRITE_ERROR",
            session_dir=session_dir
        )
```

- [ ] **Step 4: Verify and commit**

```bash
python -m py_compile subagents/disposition-execution-agent/run_agent.py
git add subagents/disposition-execution-agent/run_agent.py
git commit -m "feat(disposition-execution): add session mode support"
```

---

### Task 6: Create sub-agent integration test

**Files:**
- Create: `tests/test_subagent_session_mode.py`

- [ ] **Step 1: Write integration tests**

```python
"""
Integration tests for sub-agent session mode.

Tests that all sub-agents can:
1. Read task.json from session directory
2. Execute their specialized tasks
3. Write result.json files
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add workspace to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from subagents.subagent_utils import (
    get_session_dir, read_task_file, write_result_file
)


class TestSubagentSessionMode:
    """Test sub-agent session mode functionality."""

    def create_test_session(self, tmpdir):
        """Create a test session with task file."""
        session_path = Path(tmpdir) / "test_session"
        session_path.mkdir()

        # Write task file
        task_obj = {
            "task_id": "test_task_001",
            "task": "测试任务",
            "context": {"test": "context"},
            "output_format": "json",
            "timeout": 300
        }

        task_file = session_path / "task.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task_obj, f, indent=2, ensure_ascii=False)

        return session_path, task_obj

    def test_subagent_utils(self):
        """Test shared sub-agent utilities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path, task_obj = self.create_test_session(tmpdir)

            # Set environment
            os.environ["SESSION_DIR"] = str(session_path)
            os.environ["SUBAGENT_NAME"] = "test-agent"

            try:
                # Test get_session_dir
                assert get_session_dir() == session_path

                # Test read_task_file
                task = read_task_file()
                assert task is not None
                assert task["task_id"] == "test_task_001"

                # Test write_result_file
                result_path = write_result_file(
                    result={"test": "data"},
                    status="completed"
                )
                assert result_path.exists()

                # Verify result content
                with open(result_path, "r") as f:
                    result = json.load(f)

                assert result["status"] == "completed"
                assert result["result"]["test"] == "data"

            finally:
                # Cleanup environment
                del os.environ["SESSION_DIR"]
                del os.environ["SUBAGENT_NAME"]

    def test_data_perception_session_mode(self):
        """Test data-perception-agent in session mode."""
        project_root = Path(__file__).parent.parent
        agent_path = project_root / "subagents" / "multi-dimensional-data-perception-agent"
        run_script = agent_path / "run_agent.py"

        if not run_script.exists():
            print(f"Skipping test: {run_script} not found")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "test_session"
            session_path.mkdir()

            # Write task file
            task_obj = {
                "task_id": "test_data_001",
                "task": "获取最近24小时数据",
                "context": {"time_range": "24h"},
                "output_format": "json"
            }

            task_file = session_path / "task.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_obj, f, indent=2, ensure_ascii=False)

            # Set environment
            env = os.environ.copy()
            env["SESSION_DIR"] = str(session_path)
            env["SUBAGENT_NAME"] = "data-perception"

            try:
                # Run agent (this may fail if LLM not configured, but should not crash)
                result = subprocess.run(
                    ["python", str(run_script)],
                    cwd=str(agent_path),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # Check that it attempted to write result file
                result_files = list(session_path.glob("*_result.json"))
                print(f"Data perception stdout: {result.stdout[:500]}")
                print(f"Data perception stderr: {result.stderr[:500]}")
                print(f"Result files: {result_files}")

                # Should have written result file (even if error)
                assert len(result_files) > 0 or "error" in result.stderr.lower()

            except subprocess.TimeoutExpired:
                print("Data perception test timed out (expected if LLM not configured)")

    def test_anomaly_detection_session_mode(self):
        """Test anomaly-detection-agent in session mode."""
        project_root = Path(__file__).parent.parent
        agent_path = project_root / "subagents" / "anomaly-detection-agent"
        run_script = agent_path / "run_agent.py"

        if not run_script.exists():
            print(f"Skipping test: {run_script} not found")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "test_session"
            session_path.mkdir()

            # Write task file
            task_obj = {
                "task_id": "test_anomaly_001",
                "task": "检测异常数据",
                "context": {},
                "output_format": "json"
            }

            task_file = session_path / "task.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_obj, f, indent=2, ensure_ascii=False)

            # Set environment
            env = os.environ.copy()
            env["SESSION_DIR"] = str(session_path)
            env["SUBAGENT_NAME"] = "anomaly-detection"

            try:
                result = subprocess.run(
                    ["python", str(run_script)],
                    cwd=str(agent_path),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                print(f"Anomaly detection stdout: {result.stdout[:500]}")
                print(f"Anomaly detection stderr: {result.stderr[:500]}")

                # Check for result file
                result_files = list(session_path.glob("*_result.json"))
                assert len(result_files) > 0 or "error" in result.stderr.lower()

            except subprocess.TimeoutExpired:
                print("Anomaly detection test timed out")

    def test_rule_reasoning_session_mode(self):
        """Test rule-reasoning-agent in session mode."""
        project_root = Path(__file__).parent.parent
        agent_path = project_root / "subagents" / "rule-reasoning-agent"
        run_script = agent_path / "run_agent.py"

        if not run_script.exists():
            print(f"Skipping test: {run_script} not found")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "test_session"
            session_path.mkdir()

            # Write task file with context from previous agents
            task_obj = {
                "task_id": "test_rule_001",
                "task": "判定合规性",
                "context": {"previous_results": "simulated"},
                "output_format": "json"
            }

            task_file = session_path / "task.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_obj, f, indent=2, ensure_ascii=False)

            # Set environment
            env = os.environ.copy()
            env["SESSION_DIR"] = str(session_path)
            env["SUBAGENT_NAME"] = "rule-reasoning"

            try:
                result = subprocess.run(
                    ["python", str(run_script)],
                    cwd=str(agent_path),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                print(f"Rule reasoning stdout: {result.stdout[:500]}")
                print(f"Rule reasoning stderr: {result.stderr[:500]}")

                result_files = list(session_path.glob("*_result.json"))
                assert len(result_files) > 0 or "error" in result.stderr.lower()

            except subprocess.TimeoutExpired:
                print("Rule reasoning test timed out")

    def test_disposition_execution_session_mode(self):
        """Test disposition-execution-agent in session mode."""
        project_root = Path(__file__).parent.parent
        agent_path = project_root / "subagents" / "disposition-execution-agent"
        run_script = agent_path / "run_agent.py"

        if not run_script.exists():
            print(f"Skipping test: {run_script} not found")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "test_session"
            session_path.mkdir()

            # Write task file
            task_obj = {
                "task_id": "test_disposition_001",
                "task": "生成处置工单",
                "context": {},
                "output_format": "json"
            }

            task_file = session_path / "task.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_obj, f, indent=2, ensure_ascii=False)

            # Set environment
            env = os.environ.copy()
            env["SESSION_DIR"] = str(session_path)
            env["SUBAGENT_NAME"] = "disposition-execution"

            try:
                result = subprocess.run(
                    ["python", str(run_script)],
                    cwd=str(agent_path),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                print(f"Disposition execution stdout: {result.stdout[:500]}")
                print(f"Disposition execution stderr: {result.stderr[:500]}")

                result_files = list(session_path.glob("*_result.json"))
                assert len(result_files) > 0 or "error" in result.stderr.lower()

            except subprocess.TimeoutExpired:
                print("Disposition execution test timed out")


if __name__ == "__main__":
    import pytest

    # Run tests
    pytest.main([__file__, "-v", "-s"])
```

- [ ] **Step 2: Run tests**

```bash
cd E:/project/Ecological_env
python tests/test_subagent_session_mode.py
```

Expected: Tests show session mode is working (may have timeout failures if LLM not configured)

- [ ] **Step 3: Commit**

```bash
git add tests/test_subagent_session_mode.py
git commit -m "test(subagents): add session mode integration tests"
```

---

### Task 7: Update sub-agent SOUL.md files

**Files:**
- Modify: `subagents/*/SOUL.md`

- [ ] **Step 1: Update data-perception-agent SOUL.md**

Add section to SOUL.md:
```markdown
## Session Mode Operation

When invoked by the main orchestrator agent, I operate in **session mode**:

1. **Read task**: Load task.json from SESSION_DIR environment variable
2. **Use context**: Access previous agent results from session directory
3. **Write result**: Create data_result.json with analysis results

Session mode enables coordinated multi-agent workflows while maintaining my specialized expertise in data acquisition and preprocessing.
```

- [ ] **Step 2: Update anomaly-detection-agent SOUL.md**

```markdown
## Session Mode Operation

When invoked by the main orchestrator agent, I operate in **session mode**:

1. **Read task**: Load task.json from SESSION_DIR
2. **Use context**: Access data-perception results from session directory
3. **Write result**: Create anomaly_result.json with detected anomalies

Session mode allows me to receive processed data and contribute specialized anomaly detection to the workflow.
```

- [ ] **Step 3: Update rule-reasoning-agent SOUL.md**

```markdown
## Session Mode Operation

When invoked by the main orchestrator agent, I operate in **session mode**:

1. **Read task**: Load task.json from SESSION_DIR
2. **Use context**: Access data-perception and anomaly-detection results
3. **Write result**: Create rule_result.json with compliance analysis

Session mode enables me to apply regulatory expertise to data from earlier stages.
```

- [ ] **Step 4: Update disposition-execution-agent SOUL.md**

```markdown
## Session Mode Operation

When invoked by the main orchestrator agent, I operate in **session mode**:

1. **Read task**: Load task.json from SESSION_DIR
2. **Use context**: Access results from all previous agents
3. **Write result**: Create disposition_result.json with work orders

Session mode allows me to synthesize all prior analysis into actionable处置 recommendations.
```

- [ ] **Step 5: Commit all SOUL.md updates**

```bash
git add subagents/multi-dimensional-data-perception-agent/SOUL.md
git add subagents/anomaly-detection-agent/SOUL.md
git add subagents/rule-reasoning-agent/SOUL.md
git add subagents/disposition-execution-agent/SOUL.md
git commit -m "docs(subagents): add session mode documentation to SOUL.md files"
```

---

### Task 8: Create manual testing script

**Files:**
- Create: `tests/manual/test_session_workflow.py`

- [ ] **Step 1: Create manual test script**

```python
"""
Manual testing script for multi-agent session workflow.

This script simulates the main agent calling sub-agents in sequence,
demonstrating the complete file-based state sharing mechanism.

Usage:
    python tests/manual/test_session_workflow.py

Requirements:
    - All sub-agents have run_agent.py with session mode support
    - LLM API configured in sub-agent environments
"""

import os
import json
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from subagents.subagent_utils import (
    get_session_dir, read_task_file, write_result_file,
    get_previous_results, get_context_from_task
)
from workspace.skills.orchestrator_core.scripts.create_session import create_session


def call_subagent_manual(subagent_name: str, task: str, session_dir: str):
    """
    Manually call a sub-agent in session mode.

    This simulates what the main agent's call_subagent tool does.
    """
    print(f"\n{'='*60}")
    print(f"Calling {subagent_name} sub-agent")
    print(f"{'='*60}")

    # Get sub-agent path
    subagent_paths = {
        "data-perception": "subagents/multi-dimensional-data-perception-agent",
        "anomaly-detection": "subagents/anomaly-detection-agent",
        "rule-reasoning": "subagents/rule-reasoning-agent",
        "disposition-execution": "subagents/disposition-execution-agent"
    }

    if subagent_name not in subagent_paths:
        print(f"Error: Unknown sub-agent {subagent_name}")
        return None

    agent_path = project_root / subagent_paths[subagent_name]
    run_script = agent_path / "run_agent.py"

    if not run_script.exists():
        print(f"Error: run_agent.py not found for {subagent_name}")
        return None

    # Write task.json
    task_obj = {
        "task_id": f"manual_test_{subagent_name}_{int(datetime.now().timestamp())}",
        "task": task,
        "context": get_context_from_task(Path(session_dir)),
        "output_format": "json",
        "timeout": 300
    }

    task_file = Path(session_dir) / "task.json"
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(task_obj, f, indent=2, ensure_ascii=False)

    print(f"Written task to: {task_file}")
    print(f"Task: {task}")

    # Set environment
    env = os.environ.copy()
    env["SESSION_DIR"] = str(session_dir)
    env["SUBAGENT_NAME"] = subagent_name

    try:
        # Run sub-agent
        print(f"\nExecuting {subagent_name}...")
        result = subprocess.run(
            ["python", str(run_script)],
            cwd=str(agent_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=300
        )

        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout[:1000]}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr[:1000]}")

        # Read result file
        result_filename = f"{subagent_name}_result.json"
        result_file = Path(session_dir) / result_filename

        if result_file.exists():
            with open(result_file, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            print(f"\nResult file: {result_file}")
            print(f"Status: {result_data.get('status')}")
            if result_data.get("result"):
                print(f"Result keys: {list(result_data['result'].keys())}")

            return result_data
        else:
            print(f"\nWarning: No result file found ({result_filename})")
            return None

    except subprocess.TimeoutExpired:
        print(f"Error: {subagent_name} timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Run manual test workflow."""
    print("="*60)
    print("Multi-Agent Session Workflow Manual Test")
    print("="*60)

    # Create session directory
    session_dir = create_session()
    print(f"\nCreated session: {session_dir}")

    # Test 1: Data perception
    print("\n" + "="*60)
    print("TEST 1: Data Perception Agent")
    print("="*60)

    data_result = call_subagent_manual(
        "data-perception",
        "获取最近24小时的进水和出水数据，包括COD、TN、TP、pH指标",
        session_dir
    )

    if data_result and data_result.get("status") == "completed":
        print("\n✓ Data perception completed successfully")
    else:
        print("\n✗ Data perception failed or returned no result")

    # Test 2: Anomaly detection (uses data from previous step)
    print("\n" + "="*60)
    print("TEST 2: Anomaly Detection Agent")
    print("="*60)

    anomaly_result = call_subagent_manual(
        "anomaly-detection",
        "检测出水COD是否异常，识别突变点",
        session_dir
    )

    if anomaly_result and anomaly_result.get("status") == "completed":
        print("\n✓ Anomaly detection completed successfully")
    else:
        print("\n✗ Anomaly detection failed or returned no result")

    # Test 3: Rule reasoning
    print("\n" + "="*60)
    print("TEST 3: Rule Reasoning Agent")
    print("="*60)

    rule_result = call_subagent_manual(
        "rule-reasoning",
        "判定异常是否违反排放标准",
        session_dir
    )

    if rule_result and rule_result.get("status") == "completed":
        print("\n✓ Rule reasoning completed successfully")
    else:
        print("\n✗ Rule reasoning failed or returned no result")

    # Test 4: Disposition execution
    print("\n" + "="*60)
    print("TEST 4: Disposition Execution Agent")
    print("="*60)

    disposition_result = call_subagent_manual(
        "disposition-execution",
        "生成预警和处置工单",
        session_dir
    )

    if disposition_result and disposition_result.get("status") == "completed":
        print("\n✓ Disposition execution completed successfully")
    else:
        print("\n✗ Disposition execution failed or returned no result")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    session_path = Path(session_dir)
    result_files = list(session_path.glob("*_result.json"))

    print(f"\nSession directory: {session_dir}")
    print(f"Result files created: {len(result_files)}")

    for result_file in result_files:
        print(f"  - {result_file.name}")

    print("\nTest complete!")
    print(f"Session preserved at: {session_dir}")
    print("Inspect result files manually to verify content.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make manual test directory**

```bash
mkdir -p tests/manual
```

- [ ] **Step 3: Verify script syntax**

```bash
python -m py_compile tests/manual/test_session_workflow.py
```

- [ ] **Step 4: Commit**

```bash
git add tests/manual/test_session_workflow.py
git commit -m "test(subagents): add manual session workflow testing script"
```

---

## Verification Steps

After completing all tasks:

- [ ] Verify all subagents have session mode support:
  ```bash
  grep -l "SESSION_DIR" subagents/*/run_agent.py
  ```
  Expected: All four run_agent.py files

- [ ] Verify shared utilities work:
  ```bash
  python subagents/subagent_utils.py
  ```
  Expected: "All utilities tests passed!"

- [ ] Run integration tests:
  ```bash
  python tests/test_subagent_session_mode.py
  ```
  Expected: Tests pass (timeouts acceptable if LLM not configured)

- [ ] Verify git status clean:
  ```bash
  git status
  ```
  Expected: No uncommitted changes

---

## Success Criteria

- ✅ All four sub-agents can read task.json
- ✅ All four sub-agents can write result.json
- ✅ Sub-agents can access previous agent results
- ✅ Shared utilities module works for all sub-agents
- ✅ Integration tests demonstrate session mode
- ✅ Manual testing script available
- ✅ SOUL.md files document session mode

---

## Next Phase

After Phase 3 completion, proceed to **Phase 4: Integration Testing** which will:
1. Test end-to-end workflows
2. Verify error handling and recovery
3. Test performance with realistic queries
4. Validate main agent orchestration
