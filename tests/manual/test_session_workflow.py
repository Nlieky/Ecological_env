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
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from subagents.subagent_utils import (
    get_session_dir, read_task_file, write_result_file
)
from workspace.skills.orchestrator_core.scripts.create_session import create_session


def call_subagent_manual(subagent_name: str, task: str, session_dir: str, timeout: int = 300):
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
        print(f"Expected: {run_script}")
        return None

    # Write task.json
    task_obj = {
        "task_id": f"manual_test_{subagent_name}_{int(datetime.now().timestamp())}",
        "task": task,
        "context": get_context_from_session(session_dir),
        "output_format": "json",
        "timeout": timeout
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
        print(f"Working directory: {agent_path}")
        print(f"Script: {run_script}")

        result = subprocess.run(
            [sys.executable, str(run_script)],
            cwd=str(agent_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        print(f"\nExit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT (first 1000 chars):\n{result.stdout[:1000]}")
        if result.stderr:
            print(f"STDERR (first 500 chars):\n{result.stderr[:500]}")

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
            print(f"Files in session directory:")
            for f in Path(session_dir).glob("*"):
                print(f"  - {f.name}")

            return None

    except subprocess.TimeoutExpired:
        print(f"Error: {subagent_name} timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_context_from_session(session_dir):
    """Get context from previous agent results in session."""
    context = {}

    # Check for previous results
    result_files = {
        "data-perception": "data_result.json",
        "anomaly-detection": "anomaly_result.json",
        "rule-reasoning": "rule_result.json",
    }

    for agent, filename in result_files.items():
        result_file = Path(session_dir) / filename
        if result_file.exists():
            try:
                with open(result_file, "r") as f:
                    result = json.load(f)
                context[f"{agent}_result"] = result
                print(f"Found context from {agent}")
            except:
                pass

    return context


def main():
    """Run manual test workflow."""
    print("="*60)
    print("Multi-Agent Session Workflow Manual Test")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

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
        print("\n[OK] Data perception completed successfully")
    else:
        print("\n[FAIL] Data perception failed or returned no result")

    # Test 2: Anomaly detection
    print("\n" + "="*60)
    print("TEST 2: Anomaly Detection Agent")
    print("="*60)

    anomaly_result = call_subagent_manual(
        "anomaly-detection",
        "检测出水COD是否异常，识别突变点",
        session_dir
    )

    if anomaly_result and anomaly_result.get("status") == "completed":
        print("\n[OK] Anomaly detection completed successfully")
    else:
        print("\n[FAIL] Anomaly detection failed or returned no result")

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
        print("\n[OK] Rule reasoning completed successfully")
    else:
        print("\n[FAIL] Rule reasoning failed or returned no result")

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
        print("\n[OK] Disposition execution completed successfully")
    else:
        print("\n[FAIL] Disposition execution failed or returned no result")

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
