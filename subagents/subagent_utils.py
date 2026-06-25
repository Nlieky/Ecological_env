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
from typing import Optional, Dict, Any, Union
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
        print(f"[Session Mode] Error reading task file: {e}")
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
        # Map subagent names to result filenames
        result_name_map = {
            "data-perception": "data_result.json",
            "multi-dimensional-data-perception": "data_result.json",
            "anomaly-detection": "anomaly_result.json",
            "anomaly": "anomaly_result.json",
            "rule-reasoning": "rule_result.json",
            "rule": "rule_result.json",
            "disposition-execution": "disposition_result.json",
            "disposition": "disposition_result.json"
        }
        result_filename = result_name_map.get(subagent_name, f"{subagent_name}_result.json")

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

    print(f"[Session Mode] Result written to: {result_file}")
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
                    print(f"[Session Mode] Loaded previous result from {agent_name}")
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

    context = task.get("context", {})
    if context:
        print(f"[Session Mode] Using context from task: {list(context.keys())}")

    return context


def setup_session_mode():
    """
    Setup session mode and return task information.

    Returns:
        Tuple of (session_dir, task_obj, context) or (None, None, {}) if not in session mode

    Example:
        >>> session_dir, task, context = setup_session_mode()
        >>> if session_dir:
        ...     print(f"Processing task: {task['task']}")
    """
    session_dir = get_session_dir()

    if session_dir is None:
        print("[INFO] Not in session mode - running in standalone mode")
        return None, None, {}

    print(f"[Session Mode] Working in session: {session_dir.name}")

    # Read task
    task = read_task_file(session_dir)
    if task:
        print(f"[Session Mode] Task from file: {task.get('task', 'No task description')}")

    # Get context
    context = get_context_from_task(session_dir)

    # Get previous results
    previous_results = get_previous_results(session_dir)
    if previous_results:
        context["previous_results"] = previous_results
        print(f"[Session Mode] Using previous results from: {list(previous_results.keys())}")

    return session_dir, task, context


if __name__ == "__main__":
    # Test utilities
    import tempfile
    import shutil

    print("Testing subagent utilities...")

    with tempfile.TemporaryDirectory() as tmpdir:
        session_path = Path(tmpdir)

        # Set environment variable
        os.environ["SESSION_DIR"] = str(session_path)
        os.environ["SUBAGENT_NAME"] = "data-perception"

        # Create task file
        task_file = session_path / "task.json"
        task_file.write_text(json.dumps({
            "task_id": "test_001",
            "task": "Test task",
            "context": {"key": "value"}
        }, ensure_ascii=False))

        # Test get_session_dir
        session = get_session_dir()
        print(f"[OK] get_session_dir: {session is not None}")

        # Test read_task_file
        task = read_task_file()
        print(f"[OK] read_task_file: {task is not None and task['task'] == 'Test task'}")

        # Test get_context_from_task
        context = get_context_from_task()
        print(f"[OK] get_context_from_task: {context == {'key': 'value'}}")

        # Test write_result_file
        result_path = write_result_file(
            result={"data": "test"},
            status="completed"
        )
        print(f"[OK] write_result_file: {result_path.exists()}")

        # Verify result file content
        with open(result_path, "r") as f:
            result_data = json.load(f)
        print(f"[OK] Result validation: {result_data['status'] == 'completed'}")

    print("\nAll utilities tests passed!")
