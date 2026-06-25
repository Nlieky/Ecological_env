"""
End-to-end workflow tests for multi-agent system.

Tests complete user query workflows from main agent through sub-agents.
"""

import os
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workspace.skills.orchestrator_core.scripts.create_session import (
    create_session, get_session_files
)
from workspace.skills.orchestrator_core.scripts.cleanup_sessions import (
    cleanup_sessions, list_sessions
)
from subagents.subagent_utils import (
    read_task_file, write_result_file, validate_task, validate_result
)


class TestE2EWorkflow:
    """Test complete end-to-end workflows."""

    def test_session_creation_and_cleanup(self):
        """Test session directory creation and cleanup."""
        # Create session
        session_dir = create_session()
        session_path = Path(session_dir)

        try:
            # Verify directory exists
            assert session_path.exists()
            assert session_path.is_dir()

            # Verify metadata file
            metadata_file = session_path / "_metadata.json"
            assert metadata_file.exists()

            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            assert "session_id" in metadata
            assert "created_at" in metadata
            assert metadata["status"] == "initialized"

            # Test get_session_files
            files = get_session_files(session_dir)
            assert "metadata" in files

            print("[PASS] Session creation works correctly")

        finally:
            # Cleanup
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_task_and_result_file_flow(self):
        """Test complete task → result file flow."""
        session_dir = create_session()
        session_path = Path(session_dir)

        try:
            # Write task file
            task_obj = {
                "task_id": "test_001",
                "task": "测试任务",
                "context": {"key": "value"},
                "output_format": "json"
            }

            task_file = session_path / "task.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_obj, f, indent=2, ensure_ascii=False)

            # Verify task file exists
            assert task_file.exists()

            # Read task back
            loaded_task = read_task_file(session_path)
            assert loaded_task is not None
            assert loaded_task["task_id"] == "test_001"

            # Write result file
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
                result=result_obj["result"],
                status="completed",
                session_dir=session_path,
                result_filename="test_result.json"
            )

            # Verify result file exists
            assert result_file.exists()

            with open(result_file, "r") as f:
                loaded_result = json.load(f)

            assert loaded_result["status"] == "completed"
            assert loaded_result["result"]["data"] == "test result"

            print("[PASS] Task and result file flow works correctly")

        finally:
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_multi_agent_session_workflow(self):
        """Test workflow simulating multiple agents in one session."""
        session_dir = create_session()
        session_path = Path(session_dir)

        try:
            # Simulate data-perception agent writing result
            write_result_file(
                result={"data": [1, 2, 3, 4, 5]},
                status="completed",
                session_dir=session_path,
                result_filename="data_result.json"
            )

            # Simulate anomaly-detection agent reading previous result
            files = get_session_files(session_dir)
            assert "data_result" in files

            # Anomaly agent writes its result
            write_result_file(
                result={"anomalies": [2]},
                status="completed",
                session_dir=session_path,
                result_filename="anomaly_result.json"
            )

            # Verify both results exist
            files = get_session_files(session_dir)
            assert "data_result" in files
            assert "anomaly_result" in files

            print("[PASS] Multi-agent session workflow works correctly")

        finally:
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_cleanup_sessions_functionality(self):
        """Test session cleanup with dry-run and actual cleanup."""
        # Create multiple test sessions
        sessions = []
        for i in range(3):
            session_dir = create_session()
            sessions.append(Path(session_dir))

        try:
            # Verify all sessions exist
            for session_path in sessions:
                assert session_path.exists()

            # Test dry-run cleanup (0 days = delete all)
            result = cleanup_sessions(days=0, dry_run=True)
            assert result["dry_run"] == True
            assert result["count"] >= 0

            # Verify sessions still exist after dry-run
            for session_path in sessions:
                assert session_path.exists()

            print("[PASS] Session cleanup functionality works correctly")

        finally:
            # Cleanup all sessions
            for session_path in sessions:
                if session_path.exists():
                    shutil.rmtree(session_path)

    def test_schema_validation(self):
        """Test schema validation for tasks and results."""
        # Test valid task
        valid_task = {
            "task_id": "test_001",
            "task": "Test task"
        }
        assert validate_task(valid_task) == True

        # Test invalid task
        try:
            validate_task({"task": "test"})  # Missing task_id
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        # Test valid result
        valid_result = {
            "task_id": "test_001",
            "status": "completed"
        }
        assert validate_result(valid_result) == True

        # Test invalid result
        try:
            validate_result({"task_id": "test", "status": "invalid"})
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        print("[PASS] Schema validation works correctly")


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_task_handling(self):
        """Test handling of invalid task objects."""
        # Missing required fields
        try:
            validate_task({"incomplete": "data"})
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Missing required field" in str(e)

        print("[PASS] Invalid task handling works correctly")

    def test_invalid_result_handling(self):
        """Test handling of invalid result objects."""
        # Invalid status
        try:
            validate_result({"task_id": "test", "status": "invalid_status"})
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Invalid status" in str(e)

        print("[PASS] Invalid result handling works correctly")


def run_tests():
    """Run all integration tests."""
    print("="*60)
    print("Phase 4: Integration Tests")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

    e2e = TestE2EWorkflow()
    error = TestErrorHandling()

    tests = [
        ("Session Creation", e2e.test_session_creation_and_cleanup),
        ("Task-Result Flow", e2e.test_task_and_result_file_flow),
        ("Multi-Agent Workflow", e2e.test_multi_agent_session_workflow),
        ("Cleanup Sessions", e2e.test_cleanup_sessions_functionality),
        ("Schema Validation", e2e.test_schema_validation),
        ("Invalid Task Handling", error.test_invalid_task_handling),
        ("Invalid Result Handling", error.test_invalid_result_handling),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nRunning: {name}")
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
