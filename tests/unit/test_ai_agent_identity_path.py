# tests/unit/test_ai_agent_identity_path.py
"""测试AIAgent的identity_path参数"""

import os
import sys
from pathlib import Path
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = Path(tempfile.mkdtemp())
    # Create test identity files
    (temp_dir / "IDENTITY.md").write_text("# Test Identity\n\nThis is a test identity file.")
    (temp_dir / "SOUL.md").write_text("# Test SOUL\n\nThis is a test SOUL file.")
    (temp_dir / "AGENTS.md").write_text("# Test AGENTS\n\nThis is a test AGENTS file.")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """设置必需的环境变量"""
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    return monkeypatch


def test_agent_init_accepts_identity_path(temp_workspace, mock_env_vars):
    """测试agent_init.init_agent接受identity_path参数"""
    # Import directly from the local file to avoid system Hermes
    from shared.framework.hermes_agent.agent.agent_init import init_agent

    # Create a mock agent object
    class MockAgent:
        pass

    agent = MockAgent()

    # Call init_agent with identity_path
    init_agent(
        agent,
        base_url="https://api.example.com",
        api_key="test_key",
        model="gpt-4",
        identity_path=str(temp_workspace),
        load_soul_identity=True,
        skip_context_files=True,
    )

    # Verify identity_path is stored on the agent
    assert hasattr(agent, '_identity_path')
    assert agent._identity_path == temp_workspace


def test_agent_init_without_identity_path(mock_env_vars):
    """测试agent_init.init_agent不使用identity_path参数时默认为None"""
    from shared.framework.hermes_agent.agent.agent_init import init_agent

    class MockAgent:
        pass

    agent = MockAgent()

    init_agent(
        agent,
        base_url="https://api.example.com",
        api_key="test_key",
        model="gpt-4",
        load_soul_identity=False,
        skip_context_files=True,
    )

    assert hasattr(agent, '_identity_path')
    assert agent._identity_path is None


def test_agent_init_identity_path_relative(temp_workspace, mock_env_vars):
    """测试agent_init.init_agent使用相对路径时解析为绝对路径"""
    from shared.framework.hermes_agent.agent.agent_init import init_agent

    class MockAgent:
        pass

    agent = MockAgent()

    # Change to parent directory of temp_workspace to test relative path
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_workspace.parent)

        init_agent(
            agent,
            base_url="https://api.example.com",
            api_key="test_key",
            model="gpt-4",
            identity_path=temp_workspace.name,  # Relative path
            load_soul_identity=True,
            skip_context_files=True,
        )

        # Verify identity_path is resolved to absolute path
        assert agent._identity_path.is_absolute()
        assert agent._identity_path == temp_workspace
    finally:
        os.chdir(original_cwd)


def test_agent_init_identity_path_with_path_object(temp_workspace, mock_env_vars):
    """测试agent_init.init_agent接受Path对象作为identity_path"""
    from shared.framework.hermes_agent.agent.agent_init import init_agent

    class MockAgent:
        pass

    agent = MockAgent()

    init_agent(
        agent,
        base_url="https://api.example.com",
        api_key="test_key",
        model="gpt-4",
        identity_path=temp_workspace,  # Pass Path object directly
        load_soul_identity=True,
        skip_context_files=True,
    )

    assert agent._identity_path == temp_workspace


def test_system_prompt_uses_identity_path(temp_workspace, mock_env_vars):
    """测试system_prompt.build_system_prompt_parts使用identity_path"""
    from shared.framework.hermes_agent.agent.system_prompt import build_system_prompt_parts
    from shared.framework.hermes_agent.agent.agent_init import init_agent

    class MockAgent:
        def __init__(self):
            self.load_soul_identity = True
            self.skip_context_files = True
            self.valid_tool_names = []
            self._task_completion_guidance = True
            self._tool_use_enforcement = "auto"
            self.model = "gpt-4"
            self.provider = "openai"
            self.api_mode = "chat"
            self.platform = "cli"
            self.pass_session_id = False
            self.session_id = "test-session"
            self._memory_store = None
            self._memory_enabled = False
            self._user_profile_enabled = False
            self._memory_manager = None
            self._environment_probe = False
            self._kanban_worker_guidance = None
            self._codex_reasoning_replay_enabled = True

    agent = MockAgent()

    # Set identity_path directly (simulating what init_agent does)
    agent._identity_path = temp_workspace

    # Build system prompt parts
    parts = build_system_prompt_parts(agent)

    # Verify that identity files were loaded
    assert "stable" in parts
    assert parts["stable"]
    # Check for content from our test files
    assert "Test Identity" in parts["stable"] or "IDENTITY.md" in parts["stable"]


def test_resolve_identity_path():
    """测试identity_loader.resolve_identity_path函数"""
    from shared.framework.hermes_agent.agent.identity_loader import resolve_identity_path

    # Test with absolute path
    result = resolve_identity_path("/absolute/path/to/workspace", Path("/project"))
    assert result == Path("/absolute/path/to/workspace")

    # Test with relative path
    result = resolve_identity_path("workspace", Path("/project"))
    assert result == Path("/project/workspace")

    # Test with None (should default to workspace)
    result = resolve_identity_path(None, Path("/project"))
    assert result == Path("/project/workspace")
