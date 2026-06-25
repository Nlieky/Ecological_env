"""
Error scenario tests for multi-agent system.

Tests various error conditions and recovery mechanisms.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workspace.skills.orchestrator_core.scripts.create_session import create_session
from workspace.skills.orchestrator_core.scripts.call_subagent import call_subagent, SUBAGENT_PATHS
from subagents.subagent_utils import (
    read_task_file, write_result_file, validate_task, validate_result
)


class TestErrorScenarios:
    """Test various error scenarios."""

    def test_malformed_task_json(self):
        """Test handling of malformed task.json file."""
        print("\nTest: Malformed task.json handling")
        session_dir = create_session()
        session_path = Path(session_dir)

        try:
            # Write malformed JSON
            task_file = session_path / "task.json"
            task_file.write_text("{invalid json content")

            # This should handle the error gracefully
            result = read_task_file(session_path)

            # Should return None or handle error
            assert result is None, "Malformed JSON should return None"

            print("[PASS] Malformed task.json handled correctly")

        finally:
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_missing_task_fields(self):
        """Test handling of task with missing required fields."""
        print("\nTest: Missing task fields handling")
        session_dir = create_session()
        session_path = Path(session_dir)

        try:
            # Write task with missing fields
            task_file = session_path / "task.json"
            task_file.write_text(json.dumps({"task": "test"}))  # Missing task_id

            # Try to validate
            try:
                validate_task({"task": "test"})
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "Missing required field" in str(e)

            print("[PASS] Missing task fields handled correctly")

        finally:
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_invalid_subagent_name(self):
        """Test handling of invalid sub-agent name."""
        print("\nTest: Invalid sub-agent name handling")

        try:
            # This should raise ValueError
            result = call_subagent(
                "non-existent-agent",
                "Test task",
                session_dir=None
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown sub-agent" in str(e)
            print(f"[PASS] Invalid sub-agent name handled: {e}")

    def test_invalid_result_status(self):
        """Test handling of invalid result status."""
        print("\nTest: Invalid result status handling")

        try:
            validate_result({"task_id": "test", "status": "invalid_status"})
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid status" in str(e)
            print(f"[PASS] Invalid result status handled: {e}")

    def test_empty_session_cleanup(self):
        """Test cleanup when no sessions exist."""
        print("\nTest: Empty session cleanup")

        # Point to non-existent state directory
        from workspace.skills.orchestrator_core.scripts import cleanup_sessions as cm
        original_state_dir = cm.STATE_DIR

        try:
            # Use temp directory
            cm.STATE_DIR = Path(tempfile.mkdtemp()) / "state"
            result = cm.cleanup_sessions(days=0, dry_run=True)

            assert result["count"] == 0
            assert result["dry_run"] == True

            print("[PASS] Empty session cleanup handled correctly")

        finally:
            cm.STATE_DIR = original_state_dir
            shutil.rmtree(cm.STATE_DIR.parent.parent)

    def test_concurrent_session_access(self):
        """Test handling concurrent access to same session."""
        print("\nTest: Concurrent session access")
        import threading

        session_dir = create_session()
        session_path = Path(session_dir)

        try:
            errors = []

            def write_task(thread_id):
                try:
                    task_file = session_path / "task.json"
                    task_data = {
                        "task_id": f"task_{thread_id}",
                        "task": f"Concurrent test {thread_id}",
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(task_file, "w") as f:
                        json.dump(task_data, f)
                except Exception as e:
                    errors.append(e)

            # Create multiple threads writing to same file
            threads = []
            for i in range(5):
                t = threading.Thread(target=write_task, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join()

            # One write should have succeeded
            task_file = session_path / "task.json"
            assert task_file.exists()

            # File should be valid JSON
            with open(task_file, "r") as f:
                data = json.load(f)
            assert "task_id" in data

            print("[PASS] Concurrent session access handled correctly")

        finally:
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_recovery_after_failure(self):
        """Test system recovery after partial failure."""
        print("\nTest: Recovery after partial failure")

        # Create session that will "fail"
        session1 = create_session()
        session1_path = Path(session1)

        # Corrupt the session by writing invalid metadata
        metadata_file = session1_path / "_metadata.json"
        metadata_file.write_text("invalid")

        # Create new session - should succeed
        session2 = create_session()
        session2_path = Path(session2)

        try:
            # Verify new session is valid
            assert session2_path.exists()

            metadata_file2 = session2_path / "_metadata.json"
            assert metadata_file2.exists()

            with open(metadata_file2, "r") as f:
                metadata = json.load(f)

            assert "session_id" in metadata

            print("[PASS] Recovery after failure handled correctly")

        finally:
            # Cleanup both
            if session1_path.exists():
                shutil.rmtree(session1_path)
            if session2_path.exists():
                shutil.rmtree(session2_path)


def run_tests():
    """Run all error scenario tests."""
    print("="*60)
    print("Phase 4: Error Scenario Tests")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

    test_suite = TestErrorScenarios()

    tests = [
        test_suite.test_malformed_task_json,
        test_suite.test_missing_task_fields,
        test_suite.test_invalid_subagent_name,
        test_suite.test_invalid_result_status,
        test_suite.test_empty_session_cleanup,
        test_suite.test_concurrent_session_access,
        test_suite.test_recovery_after_failure,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
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
