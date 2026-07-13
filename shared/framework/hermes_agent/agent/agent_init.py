"""Simplified implementation of :meth:`AIAgent.__init__` for local framework.

This is a simplified version of agent_init.py that removes complex dependencies
and focuses on the core functionality needed for the wastewater monitoring system.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from hermes_constants import get_hermes_home

# Use the same logger name as run_agent so tests patching ``run_agent.logger``
# capture our warnings.
logger = logging.getLogger("run_agent")


def init_agent(
    agent: "AIAgent",
    base_url: str = None,
    api_key: str = None,
    provider: str = None,
    api_mode: str = None,
    model: str = "",
    max_iterations: int = 90,
    tool_delay: float = 1.0,
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
    save_trajectories: bool = False,
    verbose_logging: bool = False,
    quiet_mode: bool = False,
    tool_progress_mode: str = "all",
    ephemeral_system_prompt: str = None,
    log_prefix_chars: int = 100,
    log_prefix: str = "",
    session_id: str = None,
    tool_progress_callback: callable = None,
    tool_start_callback: callable = None,
    tool_complete_callback: callable = None,
    thinking_callback: callable = None,
    reasoning_callback: callable = None,
    clarify_callback: callable = None,
    step_callback: callable = None,
    stream_delta_callback: callable = None,
    interim_assistant_callback: callable = None,
    tool_gen_callback: callable = None,
    status_callback: callable = None,
    notice_callback: callable = None,
    notice_clear_callback: callable = None,
    max_tokens: int = None,
    reasoning_config: Dict[str, Any] = None,
    service_tier: str = None,
    request_overrides: Dict[str, Any] = None,
    prefill_messages: List[Dict[str, Any]] = None,
    platform: str = None,
    user_id: str = None,
    user_id_alt: str = None,
    user_name: str = None,
    chat_id: str = None,
    chat_name: str = None,
    chat_type: str = None,
    thread_id: str = None,
    gateway_session_key: str = None,
    skip_context_files: bool = False,
    load_soul_identity: bool = False,
    skip_memory: bool = False,
    session_db=None,
    parent_session_id: str = None,
    iteration_budget: "IterationBudget" = None,
    fallback_model: Dict[str, Any] = None,
    credential_pool=None,
    checkpoints_enabled: bool = False,
    checkpoint_max_snapshots: int = 20,
    checkpoint_max_total_size_mb: int = 500,
    checkpoint_max_file_size_mb: int = 10,
    pass_session_id: bool = False,
    identity_path: str | Path = None,
    **kwargs  # Accept any additional parameters without error
):
    """Initialize AIAgent with simplified configuration.

    This is a simplified version that focuses on core functionality needed
    for the wastewater monitoring system.
    """
    # Basic configuration
    agent.base_url = base_url or os.environ.get("LLM_BASE_URL", "")
    agent.api_key = api_key or os.environ.get("LLM_API_KEY", "")
    agent.model = model or os.environ.get("LLM_MODEL", "gpt-4")
    agent.max_iterations = max_iterations
    agent.tool_delay = tool_delay
    agent.enabled_toolsets = enabled_toolsets or []
    agent.disabled_toolsets = disabled_toolsets or []
    agent.save_trajectories = save_trajectories
    agent.verbose_logging = verbose_logging
    agent.quiet_mode = quiet_mode
    agent.tool_progress_mode = tool_progress_mode
    agent.ephemeral_system_prompt = ephemeral_system_prompt
    agent.log_prefix_chars = log_prefix_chars
    agent.log_prefix = log_prefix
    agent.max_tokens = max_tokens
    agent.reasoning_config = reasoning_config or {}
    agent.service_tier = service_tier
    agent.request_overrides = request_overrides or {}

    # Callbacks
    agent.tool_progress_callback = tool_progress_callback
    agent.tool_start_callback = tool_start_callback
    agent.tool_complete_callback = tool_complete_callback
    agent.thinking_callback = thinking_callback
    agent.reasoning_callback = reasoning_callback
    agent.clarify_callback = clarify_callback
    agent.step_callback = step_callback
    agent.stream_delta_callback = stream_delta_callback
    agent.interim_assistant_callback = interim_assistant_callback
    agent.tool_gen_callback = tool_gen_callback
    agent.status_callback = status_callback
    agent.notice_callback = notice_callback
    agent.notice_clear_callback = notice_clear_callback

    # Session metadata
    agent.session_id = session_id or str(uuid.uuid4())
    agent.platform = platform or "cli"
    agent.user_id = user_id
    agent.user_id_alt = user_id_alt
    agent.user_name = user_name
    agent.chat_id = chat_id
    agent.chat_name = chat_name
    agent.chat_type = chat_type
    agent.thread_id = thread_id
    agent.gateway_session_key = gateway_session_key
    agent.parent_session_id = parent_session_id
    agent.pass_session_id = pass_session_id

    # Feature flags
    agent.skip_context_files = skip_context_files
    agent.load_soul_identity = load_soul_identity
    agent.skip_memory = skip_memory
    agent.checkpoints_enabled = checkpoints_enabled
    agent.checkpoint_max_snapshots = checkpoint_max_snapshots
    agent.checkpoint_max_total_size_mb = checkpoint_max_total_size_mb
    agent.checkpoint_max_file_size_mb = checkpoint_max_file_size_mb

    # Runtime state
    agent.provider = provider or "openai"
    agent.api_mode = api_mode or "chat"
    agent.iteration_budget = iteration_budget
    agent.fallback_model = fallback_model or {}
    agent.credential_pool = credential_pool
    agent.session_db = session_db
    agent.prefill_messages = prefill_messages or []

    # Internal state
    agent.conversation_start_time = time.time()
    agent.turn_count = 0
    agent.iteration = 0
    agent.total_tokens_used = 0
    agent.total_cost_estimate = 0.0

    # Message history
    agent.messages = []
    agent.system_prompt = ""
    agent.tools = []

    # Context management
    agent.context_files = []
    agent.context_compressor = None
    agent.memory_manager = None

    # Initialize Hermes home directory
    agent.hermes_home = get_hermes_home()

    # Process identity_path parameter
    from pathlib import Path
    try:
        from agent.identity_loader import resolve_identity_path
    except ImportError:
        # Fallback for when running as a module
        from shared.framework.hermes_agent.agent.identity_loader import resolve_identity_path

    # Determine project root
    if hasattr(agent, '_project_root'):
        project_root = Path(agent._project_root)
    else:
        # Default to current working directory's parent
        project_root = Path.cwd()

    # Resolve identity_path to absolute path
    if identity_path:
        agent._identity_path = resolve_identity_path(identity_path, project_root)
    else:
        agent._identity_path = None

    logger.debug(f"Agent initialized: session_id={agent.session_id}, model={agent.model}, identity_path={agent._identity_path}")


__all__ = ["init_agent"]
