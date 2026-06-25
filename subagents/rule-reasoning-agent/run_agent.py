"""
Rule Reasoning Agent - Session Mode Entry Point

This script enables session mode for the rule reasoning sub-agent.
"""

import os
import sys
from pathlib import Path

# Add parent directory to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the wrapper
from run_agent_wrapper import run_hermes_agent

if __name__ == "__main__":
    # Set sub-agent name if not already set
    if not os.environ.get("SUBAGENT_NAME"):
        os.environ["SUBAGENT_NAME"] = "rule-reasoning"

    # Run the agent
    result = run_hermes_agent()

    if result and result.get("status") == "completed":
        print("[Rule Reasoning] Task completed successfully")
        sys.exit(0)
    else:
        print("[Rule Reasoning] Task failed or returned error")
        sys.exit(1)
