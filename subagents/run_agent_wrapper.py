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
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"[INFO] Loaded .env from {ENV_FILE}", file=sys.stderr, flush=True)
else:
    print(f"[WARNING] .env not found at {ENV_FILE}", file=sys.stderr, flush=True)

# Add Hermes framework to path
HERMES_PATH = os.environ.get('HERMES_PATH', 'D:/Hermes/hermes-agent')
if HERMES_PATH and Path(HERMES_PATH).exists():
    sys.path.insert(0, HERMES_PATH)
    print(f"[INFO] Added Hermes to path: {HERMES_PATH}", file=sys.stderr, flush=True)
else:
    print(f"[WARNING] Hermes path not found: {HERMES_PATH}", file=sys.stderr, flush=True)

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

        # === DEBUG: 打印环境信息 ===
        import sys
        print(f"[DEBUG] Current working directory: {os.getcwd()}", file=sys.stderr, flush=True)
        print(f"[DEBUG] HERMES_HOME: {os.environ.get('HERMES_HOME', 'not set')}", file=sys.stderr, flush=True)
        print(f"[DEBUG] SESSION_DIR: {session_dir}", file=sys.stderr, flush=True)

        agent = AIAgent(
            provider="custom",  # 使用自定义 LLM provider
            model=os.environ.get("LLM_MODEL", os.environ.get("MODEL", "ctgu-vlm")),
            base_url=os.environ.get("LLM_BASE_URL", os.environ.get("BASE_URL", "http://172.16.12.41:30000/v1")),
            api_key=os.environ.get("LLM_API_KEY", os.environ.get("API_KEY", "dummy")),  # 使用 .env 中的 LLM_API_KEY
            skip_context_files=False,  # 确保加载上下文文件
            load_soul_identity=True,     # 加载 SOUL.md
            skip_memory=False            # 加载 MEMORY.md
        )

        # === DEBUG: 检查上下文文件是否存在 ===
        cwd = Path(os.getcwd())
        context_files = {
            "HERMES.md": cwd / "HERMES.md",
            "AGENTS.md": cwd / "AGENTS.md",
            "SOUL.md": cwd / "SOUL.md",
            "MEMORY.md": cwd / "MEMORY.md"
        }
        for name, path in context_files.items():
            exists = "OK" if path.exists() else "FAIL"
            print(f"[DEBUG] {exists} {name}: {path}", file=sys.stderr, flush=True)

        # === DEBUG: 检查 agent 配置 ===
        print(f"[DEBUG] agent.skip_context_files: {getattr(agent, 'skip_context_files', 'N/A')}", file=sys.stderr, flush=True)
        print(f"[DEBUG] agent.load_soul_identity: {getattr(agent, 'load_soul_identity', 'N/A')}", file=sys.stderr, flush=True)
        print(f"[DEBUG] agent.skip_memory: {getattr(agent, 'skip_memory', 'N/A')}", file=sys.stderr, flush=True)

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

        # === DEBUG: 尝试获取系统提示词（如果存在） ===
        try:
            if hasattr(agent, '_cached_system_prompt'):
                sys_prompt = agent._cached_system_prompt
                print(f"[DEBUG] System prompt length: {len(sys_prompt) if sys_prompt else 0}", file=sys.stderr, flush=True)
                print(f"[DEBUG] Contains 'Anomaly Detection': {'Anomaly Detection' in sys_prompt if sys_prompt else False}", file=sys.stderr, flush=True)
                print(f"[DEBUG] Contains 'AGENTS.md': {'AGENTS.md' in sys_prompt if sys_prompt else False}", file=sys.stderr, flush=True)
                print(f"[DEBUG] Contains '异常检测': {'异常检测' in sys_prompt if sys_prompt else False}", file=sys.stderr, flush=True)
            else:
                print(f"[DEBUG] Agent has no _cached_system_prompt attribute", file=sys.stderr, flush=True)
                # 打印可用属性
                attrs = [attr for attr in dir(agent) if not attr.startswith('__')]
                print(f"[DEBUG] Agent attributes: {attrs[:20]}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[DEBUG] Error checking system prompt: {e}", file=sys.stderr, flush=True)

        response = agent.run_conversation(messages)

        # === DEBUG: 在运行后检查系统提示词 ===
        if hasattr(agent, '_cached_system_prompt'):
            sys_prompt = agent._cached_system_prompt
            print(f"[DEBUG] After run - System prompt length: {len(sys_prompt) if sys_prompt else 0}", file=sys.stderr, flush=True)
            if sys_prompt and len(sys_prompt) > 100:
                print(f"[DEBUG] Contains '异常检测': {'异常检测' in sys_prompt}", file=sys.stderr, flush=True)
                print(f"[DEBUG] Contains 'anomaly': {'anomaly' in sys_prompt.lower()}", file=sys.stderr, flush=True)
                # 打印前200字符看看内容
                print(f"[DEBUG] System prompt preview: {sys_prompt[:200]}...", file=sys.stderr, flush=True)
        else:
            print(f"[DEBUG] No _cached_system_prompt found after run", file=sys.stderr, flush=True)

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
        with open(result_file, "r", encoding='utf-8') as f:
            result_obj = json.load(f)
        result_obj["metadata"]["duration_seconds"] = round(duration, 2)
        with open(result_file, "w", encoding='utf-8') as f:
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
