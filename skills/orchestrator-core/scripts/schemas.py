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
