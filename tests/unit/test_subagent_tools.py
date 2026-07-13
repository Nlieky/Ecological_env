# tests/unit/test_subagent_tools.py
"""测试子智能体调用工具"""

import sys
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent.parent.parent / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(scripts_dir))

import pytest
from unittest.mock import Mock, patch, MagicMock
from subagent_tools import (
    call_subagent,
    initialize_subagents,
    list_available_subagents,
    get_subagent_info,
    shutdown_subagents,
    get_subagent_manager
)
from subagent_manager import SubagentManager


@pytest.fixture
def mock_subagent_manager():
    """模拟子智能体管理器"""
    mock_manager = MagicMock()
    mock_manager.subagents = {}
    mock_manager._initialized = False
    mock_manager.is_subagent_available = MagicMock(return_value=True)
    mock_manager.get_subagent = MagicMock()
    mock_manager.list_subagents = MagicMock(return_value=[])
    mock_manager.create_subagents = MagicMock()
    mock_manager.shutdown = MagicMock()
    return mock_manager


@pytest.fixture
def mock_ai_agent():
    """模拟AIAgent实例"""
    mock_agent = MagicMock()
    mock_agent.run_conversation = MagicMock(return_value={
        "final_response": "Test response from subagent"
    })
    return mock_agent


def test_initialize_subagents(mock_subagent_manager):
    """测试初始化子智能体"""
    with patch('subagent_tools.get_subagent_manager') as mock_get_manager:
        mock_get_manager.return_value = mock_subagent_manager
        result = initialize_subagents(
            model="gpt-4",
            base_url="https://api.example.com",
            api_key="test_key"
        )

        assert result["success"] is True
        assert mock_subagent_manager.create_subagents.called


def test_initialize_subagents_error(mock_subagent_manager):
    """测试初始化子智能体失败"""
    mock_subagent_manager.create_subagents.side_effect = Exception("Init failed")

    with patch('subagent_tools.get_subagent_manager') as mock_get_manager:
        mock_get_manager.return_value = mock_subagent_manager
        result = initialize_subagents()

        assert result["success"] is False
        assert "error" in result


def test_call_subagent_success(mock_subagent_manager, mock_ai_agent):
    """测试成功调用子智能体"""
    mock_subagent_manager.is_subagent_available.return_value = True
    mock_subagent_manager.get_subagent.return_value = mock_ai_agent

    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测数据异常"
        )

        assert result["success"] is True
        assert result["result"] == "Test response from subagent"
        assert mock_ai_agent.run_conversation.called


def test_call_subagent_not_available(mock_subagent_manager):
    """测试调用不存在的子智能体"""
    mock_subagent_manager.is_subagent_available.return_value = False

    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = call_subagent(
            subagent_name="non-existent-agent",
            task="执行任务"
        )

        assert result["success"] is False
        assert "不存在" in result["error"]


def test_call_subagent_with_context(mock_subagent_manager, mock_ai_agent):
    """测试带上下文调用子智能体"""
    mock_subagent_manager.is_subagent_available.return_value = True
    mock_subagent_manager.get_subagent.return_value = mock_ai_agent

    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        context = {"data_source": "sensor-001", "time_range": "2024-01-01"}
        result = call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测异常",
            context=context
        )

        assert result["success"] is True
        # 验证上下文被包含在任务中
        call_args = mock_ai_agent.run_conversation.call_args
        assert "上下文信息" in call_args[0][0]


def test_list_available_subagents(mock_subagent_manager):
    """测试列出可用子智能体"""
    mock_subagent_manager.list_subagents.return_value = [
        "multi-dimensional-data-perception-agent",
        "anomaly-detection-agent"
    ]

    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = list_available_subagents()

        assert result["success"] is True
        assert len(result["subagents"]) == 2


def test_get_subagent_info(mock_subagent_manager):
    """测试获取子智能体信息"""
    mock_subagent_manager.is_subagent_available.return_value = True

    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        # Use a real subagent name that exists in SUBAGENT_CONFIGS
        result = get_subagent_info("anomaly-detection-agent")

        assert result["success"] is True
        assert result["available"] is True
        assert "description" in result


def test_get_subagent_info_unknown():
    """测试获取未知子智能体信息"""
    with patch('subagent_tools.get_subagent_manager') as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.is_subagent_available.return_value = False
        mock_get_manager.return_value = mock_manager

        # Test with a subagent name that doesn't exist in SUBAGENT_CONFIGS
        result = get_subagent_info("unknown-agent")

        assert result["success"] is False
        assert "未知" in result["error"]


def test_shutdown_subagents(mock_subagent_manager):
    """测试关闭子智能体"""
    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = shutdown_subagents()

        assert result["success"] is True
        assert mock_subagent_manager.shutdown.called


def test_shutdown_subagents_error(mock_subagent_manager):
    """测试关闭子智能体失败"""
    mock_subagent_manager.shutdown.side_effect = Exception("Shutdown failed")

    with patch('subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = shutdown_subagents()

        assert result["success"] is False
        assert "error" in result
