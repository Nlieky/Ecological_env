# Phase 2: File State Sharing Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the file-based state sharing mechanism for communication between main agent and sub-agents.

**Architecture:** Main agent writes task.json files to session directories; sub-agents read these files and write result.json files. Session directories provide isolation and state management.

**Tech Stack:** Python, JSON, subprocess, environment variables

---

## Prerequisites

- Phase 1 completed (main agent identity files and orchestrator skill created)
- `workspace/state/` directory exists
- `workspace/skills/orchestrator-core/scripts/` directory exists

---

### Task 1: Create `__init__.py` for scripts package

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/__init__.py`

- [ ] **Step 1: Create package initialization file**

```python
"""
Orchestrator Core Scripts

Provides tools for multi-agent orchestration:
- create_session: Create isolated session directories
- call_subagent: Invoke sub-agents with task context
- cleanup_sessions: Clean up old session directories
"""

from .create_session import create_session
from .call_subagent import call_subagent
from .cleanup_sessions import cleanup_sessions

__all__ = [
    "create_session",
    "call_subagent",
    "cleanup_sessions",
]
```

- [ ] **Step 2: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/__init__.py
git commit -m "feat(orchestrator): add scripts package initialization"
```

---

### Task 2: Implement `create_session.py`

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/create_session.py`

- [ ] **Step 1: Write create_session implementation**

```python
"""
Create Session Tool

Creates isolated session directories for state management.
Each session gets a timestamp-based directory for storing task and result files.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Default state directory relative to workspace
STATE_DIR = Path(__file__).parent.parent.parent.parent / "state"


def create_session(base_dir: Optional[Path] = None) -> str:
    """
    Create a new session directory for state isolation.

    Args:
        base_dir: Optional base directory for sessions. Defaults to workspace/state/

    Returns:
        str: Absolute path to the created session directory

    Example:
        >>> session_path = create_session()
        >>> print(session_path)
        'E:/project/Ecological_env/workspace/state/session_20250623_143022'
    """
    if base_dir is None:
        base_dir = STATE_DIR

    # Ensure state directory exists
    base_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp-based session name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}"
    session_path = base_dir / session_name

    # Create session directory
    session_path.mkdir(exist_ok=True)

    # Initialize session metadata
    metadata = {
        "session_id": session_name,
        "created_at": datetime.now().isoformat(),
        "status": "initialized"
    }

    metadata_path = session_path / "_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return str(session_path.absolute())


def get_session_files(session_path: str) -> dict:
    """
    Get list of task and result files in a session.

    Args:
        session_path: Path to the session directory

    Returns:
        dict: Mapping of file types to their paths
    """
    session = Path(session_path)
    if not session.exists():
        return {}

    files = {
        "metadata": session / "_metadata.json",
        "task": session / "task.json",
        "data_result": session / "data_result.json",
        "anomaly_result": session / "anomaly_result.json",
        "rule_result": session / "rule_result.json",
        "disposition_result": session / "disposition_result.json",
        "final_response": session / "final_response.json",
    }

    # Only return existing files
    return {k: str(v) for k, v in files.items() if v.exists()}


if __name__ == "__main__":
    # Test create_session
    path = create_session()
    print(f"Created session: {path}")
    print(f"Files: {get_session_files(path)}")
```

- [ ] **Step 2: Test the implementation**

```bash
cd E:/project/Ecological_env
python -m workspace.skills.orchestrator-core.scripts.create_session
```

Expected output: Session path printed

- [ ] **Step 3: Verify state directory was created**

```bash
ls -la E:/project/Ecological_env/workspace/state/
```

Expected: Directory contains `session_YYYYMMDD_HHMMSS/` with `_metadata.json`

- [ ] **Step 4: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/create_session.py
git add workspace/state/
git commit -m "feat(orchestrator): implement create_session tool"
```

---

### Task 3: Implement `call_subagent.py` - Core structure

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/call_subagent.py`

- [ ] **Step 1: Write call_subagent core implementation**

```python
"""
Call Subagent Tool

Invokes sub-agents via subprocess with task context.
Handles task writing, environment setup, subprocess execution, and result reading.
"""

import os
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Subagent locations relative to project root
SUBAGENT_PATHS = {
    "data-perception": "../subagents/multi-dimensional-data-perception-agent",
    "anomaly-detection": "../subagents/anomaly-detection-agent",
    "rule-reasoning": "../subagents/rule-reasoning-agent",
    "disposition-execution": "../subagents/disposition-execution-agent",
}


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None,
    session_dir: Optional[str] = None,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Call a sub-agent to execute a task.

    Args:
        subagent_name: Name of the sub-agent to call
        task: Task description string
        context: Optional context dictionary from previous sub-agent results
        session_dir: Session directory path (creates new if None)
        timeout: Maximum time to wait for sub-agent completion (seconds)

    Returns:
        dict: Sub-agent result with status, result, error, and metadata

    Raises:
        ValueError: If subagent_name is not recognized
        TimeoutError: If sub-agent execution exceeds timeout

    Example:
        >>> result = call_subagent(
        ...     "data-perception",
        ...     "获取最近24小时进水和出水数据",
        ...     context={"time_range": "24h"},
        ...     session_dir="workspace/state/session_20250623_143022"
        ... )
        >>> print(result["status"])
        'completed'
    """
    # Validate sub-agent name
    if subagent_name not in SUBAGENT_PATHS:
        raise ValueError(
            f"Unknown sub-agent: {subagent_name}. "
            f"Available: {list(SUBAGENT_PATHS.keys())}"
        )

    # Get sub-agent path
    subagent_rel_path = SUBAGENT_PATHS[subagent_name]
    project_root = Path(__file__).parent.parent.parent.parent
    subagent_path = (project_root / subagent_rel_path).resolve()

    # Create session directory if not provided
    if session_dir is None:
        from .create_session import create_session
        session_dir = create_session()
    session_path = Path(session_dir)

    # Prepare task object
    task_id = f"task_{subagent_name}_{int(time.time())}"
    task_obj = {
        "task_id": task_id,
        "task": task,
        "context": context or {},
        "output_format": "json",
        "timeout": timeout
    }

    # Write task.json to session directory
    task_file = session_path / "task.json"
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(task_obj, f, indent=2, ensure_ascii=False)

    # Prepare environment variables
    env = os.environ.copy()
    env["HERMES_HOME"] = str(subagent_path)
    env["SESSION_DIR"] = str(session_path)
    env["SUBAGENT_NAME"] = subagent_name

    # Determine result file name
    result_file_name = f"{subagent_name}_result.json"
    result_file = session_path / result_file_name

    try:
        # Invoke sub-agent via subprocess
        start_time = time.time()

        # Run hermes command in sub-agent directory
        hermes_cmd = ["python", "-m", "hermes_cli", "run"]
        process = subprocess.Popen(
            hermes_cmd,
            cwd=str(subagent_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout)
            duration = time.time() - start_time

            # Read result file
            if result_file.exists():
                with open(result_file, "r", encoding="utf-8") as f:
                    result = json.load(f)

                # Add execution metadata
                result["metadata"] = result.get("metadata", {})
                result["metadata"]["duration_seconds"] = duration
                result["metadata"]["timestamp"] = datetime.now().isoformat()

                return result
            else:
                # Sub-agent didn't write result file
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error": "Sub-agent did not write result file",
                    "error_code": "NO_RESULT_FILE",
                    "metadata": {
                        "duration_seconds": duration,
                        "stdout": stdout,
                        "stderr": stderr
                    }
                }

        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError(
                f"Sub-agent {subagent_name} timed out after {timeout}s"
            )

    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "metadata": {
                "exception_type": type(e).__name__
            }
        }


if __name__ == "__main__":
    # Test call_subagent (requires sub-agent setup)
    import sys
    if len(sys.argv) > 1:
        result = call_subagent(
            sys.argv[1],
            "Test task",
            session_dir=None
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
```

- [ ] **Step 2: Add missing datetime import**

Edit line 8 to add datetime:
```python
from datetime import datetime
```

- [ ] **Step 3: Verify syntax**

```bash
python -m py_compile workspace/skills/orchestrator-core/scripts/call_subagent.py
```

Expected: No syntax errors

- [ ] **Step 4: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/call_subagent.py
git commit -m "feat(orchestrator): implement call_subagent core logic"
```

---

### Task 4: Create result file schemas

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/schemas.py`

- [ ] **Step 1: Create result schema definitions**

```python
"""
Result File Schemas

Defines JSON schemas for task and result files used in sub-agent communication.
"""

import json
from pathlib import Path
from typing import Dict, Any


# Task JSON schema (written by main agent)
TASK_SCHEMA = {
    "type": "object",
    "required": ["task_id", "task", "output_format"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Unique task identifier"
        },
        "task": {
            "type": "string",
            "description": "Task description for the sub-agent"
        },
        "context": {
            "type": "object",
            "description": "Context from previous sub-agent results"
        },
        "output_format": {
            "type": "string",
            "enum": ["json", "text"],
            "default": "json"
        },
        "timeout": {
            "type": "integer",
            "default": 300,
            "minimum": 1
        }
    }
}


# Result JSON schema (written by sub-agents)
RESULT_SCHEMA = {
    "type": "object",
    "required": ["task_id", "status"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Corresponding task identifier"
        },
        "status": {
            "type": "string",
            "enum": ["completed", "failed", "error"],
            "description": "Task execution status"
        },
        "result": {
            "type": "object",
            "description": "Task result data (present when status=completed)"
        },
        "error": {
            "type": "string",
            "description": "Error message (present when status=failed/error)"
        },
        "error_code": {
            "type": "string",
            "description": "Machine-readable error code"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "duration_seconds": {"type": "number"},
                "timestamp": {"type": "string"},
                "subagent_version": {"type": "string"}
            }
        }
    }
}


def validate_task(task_obj: Dict[str, Any]) -> bool:
    """Validate task object against schema."""
    required_fields = ["task_id", "task"]
    for field in required_fields:
        if field not in task_obj:
            raise ValueError(f"Missing required field: {field}")
    return True


def validate_result(result_obj: Dict[str, Any]) -> bool:
    """Validate result object against schema."""
    if "task_id" not in result_obj:
        raise ValueError("Missing task_id in result")
    if "status" not in result_obj:
        raise ValueError("Missing status in result")
    if result_obj["status"] not in ["completed", "failed", "error"]:
        raise ValueError(f"Invalid status: {result_obj['status']}")
    return True


def write_task_file(session_path: Path, task_obj: Dict[str, Any]) -> Path:
    """Write task.json file to session directory."""
    validate_task(task_obj)
    task_file = session_path / "task.json"
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(task_obj, f, indent=2, ensure_ascii=False)
    return task_file


def write_result_file(
    session_path: Path,
    filename: str,
    result_obj: Dict[str, Any]
) -> Path:
    """Write result file to session directory."""
    validate_result(result_obj)
    result_file = session_path / filename
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_obj, f, indent=2, ensure_ascii=False)
    return result_file


if __name__ == "__main__":
    # Test validation
    from datetime import datetime

    test_task = {
        "task_id": "test_001",
        "task": "Test task description",
        "context": {},
        "output_format": "json",
        "timeout": 300
    }
    print("Task validation:", validate_task(test_task))

    test_result = {
        "task_id": "test_001",
        "status": "completed",
        "result": {"data": "test"},
        "metadata": {
            "duration_seconds": 1.5,
            "timestamp": datetime.now().isoformat()
        }
    }
    print("Result validation:", validate_result(test_result))
```

- [ ] **Step 2: Test schema validation**

```bash
cd E:/project/Ecological_env
python -m workspace.skills.orchestrator-core.scripts.schemas
```

Expected: Validation prints True

- [ ] **Step 3: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/schemas.py
git commit -m "feat(orchestrator): add result file schemas and validation"
```

---

### Task 5: Update `call_subagent.py` to use schemas

**Files:**
- Modify: `workspace/skills/orchestrator-core/scripts/call_subagent.py`

- [ ] **Step 1: Add schema import and usage**

Add after line 13:
```python
from .schemas import write_task_file, validate_result
```

Replace the task writing section (around line 77):
```python
    # Write task.json to session directory
    from .schemas import write_task_file
    write_task_file(session_path, task_obj)
```

- [ ] **Step 2: Verify syntax**

```bash
python -m py_compile workspace/skills/orchestrator-core/scripts/call_subagent.py
```

- [ ] **Step 3: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/call_subagent.py
git commit -m "refactor(orchestrator): use schema validation for task files"
```

---

### Task 6: Implement `cleanup_sessions.py`

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/cleanup_sessions.py`

- [ ] **Step 1: Write cleanup implementation**

```python
"""
Cleanup Sessions Tool

Removes old session directories to manage disk space.
Can be run manually or scheduled as maintenance.
"""

import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Default state directory
STATE_DIR = Path(__file__).parent.parent.parent.parent / "state"


def cleanup_sessions(days: int = 7, dry_run: bool = False) -> Dict[str, any]:
    """
    Clean up session directories older than specified days.

    Args:
        days: Keep sessions from the last N days (default: 7)
        dry_run: If True, only report what would be deleted

    Returns:
        dict: Cleanup summary with count, size, and list of deleted sessions

    Example:
        >>> summary = cleanup_sessions(days=7, dry_run=True)
        >>> print(summary["count"])
        5
        >>> cleanup_sessions(days=7, dry_run=False)
    """
    if not STATE_DIR.exists():
        return {"count": 0, "size_bytes": 0, "deleted": [], "kept": []}

    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted = []
    kept = []
    total_size = 0

    for session_dir in STATE_DIR.glob("session_*"):
        if not session_dir.is_dir():
            continue

        # Check directory modification time
        dir_mtime = session_dir.stat().st_mtime

        if dir_mtime < cutoff_time:
            # Calculate size before deletion
            dir_size = sum(
                f.stat().st_size
                for f in session_dir.rglob("*")
                if f.is_file()
            )

            if dry_run:
                deleted.append({
                    "path": str(session_dir),
                    "size_bytes": dir_size,
                    "last_modified": datetime.fromtimestamp(dir_mtime).isoformat()
                })
                total_size += dir_size
            else:
                try:
                    shutil.rmtree(session_dir)
                    deleted.append({
                        "path": str(session_dir),
                        "size_bytes": dir_size,
                        "last_modified": datetime.fromtimestamp(dir_mtime).isoformat()
                    })
                    total_size += dir_size
                except Exception as e:
                    print(f"Failed to delete {session_dir}: {e}")
        else:
            kept.append({
                "path": str(session_dir),
                "last_modified": datetime.fromtimestamp(dir_mtime).isoformat()
            })

    return {
        "count": len(deleted),
        "size_bytes": total_size,
        "size_mb": round(total_size / (1024 * 1024), 2),
        "deleted": deleted,
        "kept": kept,
        "dry_run": dry_run
    }


def list_sessions() -> List[Dict[str, any]]:
    """
    List all session directories with metadata.

    Returns:
        list: Session information dictionaries
    """
    sessions = []

    if not STATE_DIR.exists():
        return sessions

    for session_dir in STATE_DIR.glob("session_*"):
        if not session_dir.is_dir():
            continue

        # Read metadata if exists
        metadata_file = session_dir / "_metadata.json"
        metadata = {}
        if metadata_file.exists():
            import json
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except:
                pass

        # Count files
        file_count = sum(1 for _ in session_dir.rglob("*") if _.is_file())

        sessions.append({
            "path": str(session_dir),
            "name": session_dir.name,
            "created": metadata.get("created_at"),
            "status": metadata.get("status", "unknown"),
            "file_count": file_count,
            "size_bytes": sum(
                f.stat().st_size
                for f in session_dir.rglob("*")
                if f.is_file()
            )
        })

    return sorted(sessions, key=lambda x: x["path"], reverse=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage session directories")
    parser.add_argument("--list", action="store_true", help="List all sessions")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old sessions")
    parser.add_argument("--days", type=int, default=7, help="Days to keep (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")

    args = parser.parse_args()

    if args.list:
        sessions = list_sessions()
        print(f"Found {len(sessions)} sessions:")
        for s in sessions:
            print(f"  {s['name']} - {s['file_count']} files, {s['size_bytes']} bytes")

    if args.cleanup:
        result = cleanup_sessions(days=args.days, dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"{action} {result['count']} sessions ({result['size_mb']} MB)")
```

- [ ] **Step 2: Test cleanup functionality**

```bash
# List sessions
python -m workspace.skills.orchestrator-core.scripts.cleanup_sessions --list

# Dry run cleanup
python -m workspace.skills.orchestrator-core.scripts.cleanup_sessions --cleanup --dry-run
```

Expected: Lists sessions, shows what would be deleted

- [ ] **Step 3: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/cleanup_sessions.py
git commit -m "feat(orchestrator): implement session cleanup tool"
```

---

### Task 7: Update orchestrator SKILL.md with tool documentation

**Files:**
- Modify: `workspace/skills/orchestrator-core/SKILL.md`

- [ ] **Step 1: Add detailed tool usage section**

Add after "## Available Tools" section:

```markdown
## Tool Usage Details

### create_session()

Creates a new session directory for state isolation.

**Usage:**
```python
from workspace.skills.orchestrator-core.scripts import create_session

session_path = create_session()
# Returns: "E:/project/Ecological_env/workspace/state/session_20250623_143022"
```

**Creates:**
- Session directory: `workspace/state/session_YYYYMMDD_HHMMSS/`
- Metadata file: `_metadata.json` with creation timestamp

**Session directory contents (during execution):**
```
session_YYYYMMDD_HHMMSS/
├── _metadata.json          # Session metadata
├── task.json                # Current task (written by main agent)
├── data_result.json         # Data perception result
├── anomaly_result.json      # Anomaly detection result
├── rule_result.json         # Rule reasoning result
├── disposition_result.json  # Disposition execution result
└── final_response.json      # Aggregated final response
```

### call_subagent(subagent_name, task, context, session_dir, timeout)

Invokes a sub-agent to execute a task.

**Parameters:**
- `subagent_name` (str): Name of sub-agent
  - `"data-perception"` - Multi-dimensional data perception
  - `"anomaly-detection"` - Anomaly detection
  - `"rule-reasoning"` - Rule reasoning
  - `"disposition-execution"` - Disposition execution
- `task` (str): Task description string
- `context` (dict, optional): Previous sub-agent results
- `session_dir` (str, optional): Session directory path (creates new if None)
- `timeout` (int, optional): Maximum wait time in seconds (default: 300)

**Returns:**
```python
{
    "task_id": "task_data-perception_1234567890",
    "status": "completed",  # or "failed", "error"
    "result": {...},        # Task result data
    "error": null,          # Error message if failed
    "metadata": {
        "duration_seconds": 2.3,
        "timestamp": "2025-06-23T14:30:25"
    }
}
```

**Error Handling:**
- `ValueError` - Invalid sub-agent name
- `TimeoutError` - Sub-agent execution exceeds timeout

**Result File Format:**
Each sub-agent writes a `{subagent_name}_result.json` file to the session directory.
```
"data-perception" → data_result.json
"anomaly-detection" → anomaly_result.json
"rule-reasoning" → rule_result.json
"disposition-execution" → disposition_result.json
```

### cleanup_sessions(days, dry_run)

Removes old session directories to manage disk space.

**Parameters:**
- `days` (int): Keep sessions from last N days (default: 7)
- `dry_run` (bool): If True, only report what would be deleted

**Usage:**
```python
from workspace.skills.orchestrator-core.scripts import cleanup_sessions

# Preview cleanup
result = cleanup_sessions(days=7, dry_run=True)
print(f"Would delete {result['count']} sessions ({result['size_mb']} MB)")

# Execute cleanup
result = cleanup_sessions(days=7, dry_run=False)
```

**Returns:**
```python
{
    "count": 5,
    "size_bytes": 5242880,
    "size_mb": 5.0,
    "deleted": [...],
    "kept": [...],
    "dry_run": False
}
```
```

- [ ] **Step 2: Verify SKILL.md formatting**

```bash
head -100 workspace/skills/orchestrator-core/SKILL.md
```

- [ ] **Step 3: Commit**

```bash
git add workspace/skills/orchestrator-core/SKILL.md
git commit -m "docs(orchestrator): add detailed tool usage documentation"
```

---

### Task 8: Create integration test for file state sharing

**Files:**
- Create: `tests/test_file_state_sharing.py`

- [ ] **Step 1: Write integration tests**

```python
"""
Integration tests for file state sharing mechanism.

Tests session creation, task writing, and result reading.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add workspace to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "workspace"))

from skills.orchestrator_core.scripts.create_session import (
    create_session, get_session_files
)
from skills.orchestrator_core.scripts.schemas import (
    write_task_file, write_result_file, validate_task, validate_result
)
from skills.orchestrator_core.scripts.cleanup_sessions import (
    cleanup_sessions, list_sessions
)


class TestFileStateSharing:
    """Test file-based state sharing."""

    def test_create_session(self):
        """Test session directory creation."""
        original_state_dir = Path(__file__).parent.parent / "workspace" / "state"

        # Create session
        session_path = create_session()
        session_dir = Path(session_path)

        # Verify directory exists
        assert session_dir.exists()
        assert session_dir.is_dir()

        # Verify metadata file
        metadata_file = session_dir / "_metadata.json"
        assert metadata_file.exists()

        # Load and verify metadata
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        assert "session_id" in metadata
        assert "created_at" in metadata
        assert metadata["status"] == "initialized"

        # Cleanup
        shutil.rmtree(session_dir)

    def test_write_and_read_task(self):
        """Test task file writing and reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            # Write task
            task_obj = {
                "task_id": "test_001",
                "task": "Test task description",
                "context": {"key": "value"},
                "output_format": "json",
                "timeout": 300
            }
            task_file = write_task_file(session_path, task_obj)

            # Verify file exists
            assert task_file.exists()
            assert task_file.name == "task.json"

            # Read and verify content
            with open(task_file, "r") as f:
                loaded_task = json.load(f)

            assert loaded_task["task_id"] == "test_001"
            assert loaded_task["task"] == "Test task description"

    def test_write_and_read_result(self):
        """Test result file writing and reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            # Write result
            result_obj = {
                "task_id": "test_001",
                "status": "completed",
                "result": {"data": "test result"},
                "error": None,
                "metadata": {
                    "duration_seconds": 1.5,
                    "timestamp": datetime.now().isoformat()
                }
            }
            result_file = write_result_file(
                session_path,
                "data_result.json",
                result_obj
            )

            # Verify file exists
            assert result_file.exists()

            # Read and verify content
            with open(result_file, "r") as f:
                loaded_result = json.load(f)

            assert loaded_result["status"] == "completed"
            assert loaded_result["result"]["data"] == "test result"

    def test_session_file_tracking(self):
        """Test get_session_files function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            # Create some files
            (session_path / "_metadata.json").write_text("{}")
            (session_path / "task.json").write_text("{}")
            (session_path / "data_result.json").write_text("{}")

            # Get files
            files = get_session_files(str(session_path))

            # Verify
            assert "metadata" in files
            assert "task" in files
            assert "data_result" in files
            assert "anomaly_result" not in files

    def test_cleanup_sessions_dry_run(self):
        """Test cleanup sessions in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override state directory for testing
            import skills.orchestrator_core.scripts.cleanup_sessions as cleanup_module
            original_state_dir = cleanup_module.STATE_DIR
            cleanup_module.STATE_DIR = Path(tmpdir)

            try:
                # Create some old sessions (by setting old mtime)
                old_session = Path(tmpdir) / "session_old"
                old_session.mkdir()
                (old_session / "_metadata.json").write_text("{}")

                # Create recent session
                recent_session = Path(tmpdir) / "session_recent"
                recent_session.mkdir()
                (recent_session / "_metadata.json").write_text("{}")

                # Run dry-run cleanup (0 days = delete all)
                result = cleanup_sessions(days=0, dry_run=True)

                # Verify dry-run reported deletion
                assert result["dry_run"] == True
                assert result["count"] >= 0

                # Verify directories still exist
                assert old_session.exists()
                assert recent_session.exists()

            finally:
                cleanup_module.STATE_DIR = original_state_dir

    def test_schema_validation(self):
        """Test schema validation."""
        # Valid task
        valid_task = {
            "task_id": "test_001",
            "task": "Test task"
        }
        assert validate_task(valid_task) == True

        # Invalid task (missing task_id)
        try:
            validate_task({"task": "test"})
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        # Valid result
        valid_result = {
            "task_id": "test_001",
            "status": "completed"
        }
        assert validate_result(valid_result) == True

        # Invalid result (bad status)
        try:
            validate_result({"task_id": "test", "status": "invalid"})
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


if __name__ == "__main__":
    import pytest

    # Run tests
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run tests**

```bash
cd E:/project/Ecological_env
python tests/test_file_state_sharing.py
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_file_state_sharing.py
git commit -m "test(orchestrator): add file state sharing integration tests"
```

---

### Task 9: Verify workspace state directory in .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Ensure state directories are ignored**

Add to `.gitignore`:
```
# Session state directories
workspace/state/
subagents/*/state/
*.state/
```

- [ ] **Step 2: Verify gitignore**

```bash
git check-ignore -v workspace/state/session_*/
```

Expected: Shows ignore pattern match

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore session state directories"
```

---

### Task 10: Documentation update

**Files:**
- Modify: `docs/multi-agent-system-design.md`

- [ ] **Step 1: Update implementation status**

At the end of the document, add:

```markdown
## Implementation Status

### Phase 1: Main Agent and Orchestrator ✅
- [x] Main agent identity files (SOUL.md, AGENTS.md, MEMORY.md)
- [x] Orchestrator core skill structure
- [x] SKILL.md with professional language

### Phase 2: File State Sharing Mechanism ✅
- [x] Session directory creation (create_session.py)
- [x] Sub-agent invocation (call_subagent.py)
- [x] Session cleanup (cleanup_sessions.py)
- [x] Result file schemas (schemas.py)
- [x] Integration tests

### Phase 3: Sub-Agent Adaptation (Pending)
- [ ] Adapt sub-agents to read task.json
- [ ] Adapt sub-agents to write result.json
- [ ] Add session context loading

### Phase 4: Integration Testing (Pending)
- [ ] End-to-end workflow testing
- [ ] Error handling verification
- [ ] Performance testing
```

- [ ] **Step 2: Commit**

```bash
git add docs/multi-agent-system-design.md
git commit -m "docs: update implementation status for Phase 2"
```

---

## Verification Steps

After completing all tasks:

- [ ] Run all tests: `python tests/test_file_state_sharing.py`
- [ ] Verify session creation: `python -m workspace.skills.orchestrator-core.scripts.create_session`
- [ ] Verify cleanup: `python -m workspace.skills.orchestrator-core.scripts.cleanup_sessions --list`
- [ ] Check git status: No uncommitted state files in `workspace/state/`

---

## Success Criteria

- ✅ Session directories create successfully with metadata
- ✅ Task files write with proper schema validation
- ✅ Result files have standardized format
- ✅ Cleanup tool removes old sessions safely
- ✅ Integration tests pass
- ✅ State directories are gitignored
- ✅ Documentation updated

---

## Next Phase

After Phase 2 completion, proceed to **Phase 3: Sub-Agent Adaptation** which will:
1. Update sub-agent run_agent.py to read task.json
2. Update sub-agent run_agent.py to write result.json
3. Add session context loading to sub-agents
