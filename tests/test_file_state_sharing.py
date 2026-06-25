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
