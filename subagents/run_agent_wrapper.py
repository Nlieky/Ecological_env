"""
Run Agent Wrapper for Sub-Agents

This wrapper script enables session mode for Hermes-based sub-agents.
It reads task.json from SESSION_DIR, calls the Hermes agent, and writes result.json.

Usage:
    Set environment variables:
    - SESSION_DIR: Path to session directory
    - SUBAGENT_NAME: Name of sub-agent (e.g., data-perception)

    Then run: python run_agent.py
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from subagent_utils import (
    get_session_dir, read_task_file, write_result_file,
    get_context_from_task, get_previous_results, setup_session_mode
)


def run_hermes_agent():
    """
    Run the Hermes agent with appropriate configuration.

    This function initializes the Hermes AIAgent and runs a conversation
    based on the task from task.json (if in session mode) or interactive input.
    """
    try:
        # Try to import Hermes agent
        from run_agent import AIAgent
    except ImportError:
        print("[ERROR] Hermes AIAgent not found. Make sure Hermes is installed.")
        return None

    # Check if we're in session mode
    session_dir, task, context = setup_session_mode()

    if session_dir and task:
        # Session mode: run with task from file
        return run_session_task(AIAgent, task, context, session_dir)
    else:
        # Interactive mode: run normal Hermes agent
        return run_interactive(AIAgent)


def run_session_task(AIAgent, task, context, session_dir):
    """
    Run Hermes agent in session mode with task from file.

    Args:
        AIAgent: Hermes AIAgent class
        task: Task dictionary from task.json
        context: Context dictionary
        session_dir: Session directory path

    Returns:
        Result dictionary
    """
    print(f"\n[Session Mode] Running task: {task.get('task', 'No description')}")

    try:
        # Initialize agent
        # Note: You may need to adjust these parameters based on your Hermes setup
        agent = AIAgent(
            model=os.environ.get("MODEL", "claude-sonnet-4-20250514"),
            base_url=os.environ.get("BASE_URL", "http://localhost:11434/v1")
        )

        # Build messages from task
        task_description = task.get("task", "")

        # Add context to the prompt
        if context:
            context_str = "\n\nContext from previous agents:\n" + json.dumps(context, indent=2, ensure_ascii=False)
            task_description += context_str

        messages = [
            {"role": "user", "content": task_description}
        ]

        # Run conversation
        start_time = time.time()

        print(f"[Session Mode] Calling Hermes agent...")
        response = agent.run_conversation(messages)

        duration = time.time() - start_time

        # Prepare result
        result_data = {
            "response": response,
            "task_description": task_description,
            "context_used": list(context.keys()) if context else []
        }

        # Write result file
        result_file = write_result_file(
            result=result_data,
            status="completed",
            session_dir=session_dir
        )

        # Update duration
        with open(result_file, "r") as f:
            result_obj = json.load(f)
        result_obj["metadata"]["duration_seconds"] = round(duration, 2)
        with open(result_file, "w") as f:
            json.dump(result_obj, f, indent=2, ensure_ascii=False)

        print(f"[Session Mode] Task completed in {duration:.2f}s")
        print(f"[Session Mode] Result written to {result_file}")

        return result_obj

    except Exception as e:
        print(f"[Session Mode] Error: {e}")
        import traceback
        traceback.print_exc()

        # Write error result
        write_result_file(
            result=None,
            status="error",
            error=str(e),
            error_code="AGENT_ERROR",
            session_dir=session_dir
        )

        return {
            "status": "error",
            "error": str(e)
        }


def run_interactive(AIAgent):
    """
    Run Hermes agent in interactive mode (no session).

    Args:
        AIAgent: Hermes AIAgent class

    Returns:
        None
    """
    print("[INFO] Running in interactive mode (no session)")
    print("[INFO] Use Hermes CLI directly: python -m hermes_cli chat")


if __name__ == "__main__":
    # Check for environment variables
    session_dir = os.environ.get("SESSION_DIR")
    subagent_name = os.environ.get("SUBAGENT_NAME")

    if session_dir:
        print(f"[INFO] Session Mode: {subagent_name}")
        print(f"[INFO] Session Directory: {session_dir}")

    # Run agent
    result = run_hermes_agent()

    if result:
        print(f"\n[Session Mode] Final Status: {result.get('status', 'unknown')}")
    else:
        print("\n[Session Mode] No result returned")
