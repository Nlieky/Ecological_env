# tests/unit/test_subagent_manager.py
"""测试子智能体管理器"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from subagent_manager import SubagentManager


@pytest.fixture
def mock_ai_agent():
    """模拟AIAgent类"""
    mock_agent = MagicMock()
    mock_agent.shutdown = MagicMock()
    return mock_agent


@pytest.fixture
def temp_project_root(tmp_path):
    """创建临时项目根目录"""
    # 创建子智能体目录
    for subagent in ["multi-dimensional-data-perception-agent", "anomaly-detection-agent",
                     "rule-reasoning-agent", "disposition-execution-agent"]:
        subagent_path = tmp_path / "subagents" / subagent
        subagent_path.mkdir(parents=True)
        (subagent_path / "SOUL.md").write_text(f"# {subagent} SOUL")
    return tmp_path


def test_subagent_manager_init():
    """测试SubagentManager初始化"""
    manager = SubagentManager()
    assert manager.project_root == Path.cwd()
    assert manager.subagents == {}
    assert manager._initialized is False


def test_subagent_manager_init_with_project_root(tmp_path):
    """测试SubagentManager使用自定义项目根目录"""
    manager = SubagentManager(project_root=tmp_path)
    assert manager.project_root == tmp_path


def test_subagent_manager_create_subagents(temp_project_root, mock_ai_agent):
    """测试创建子智能体"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)

        manager.create_subagents(
            model="gpt-4",
            base_url="https://api.example.com",
            api_key="test_key"
        )

        # 验证所有子智能体都被创建
        assert len(manager.subagents) == 4
        assert manager._initialized is True

        # 验证所有预期的子智能体都存在
        expected_subagents = [
            "multi-dimensional-data-perception-agent",
            "anomaly-detection-agent",
            "rule-reasoning-agent",
            "disposition-execution-agent"
        ]
        for name in expected_subagents:
            assert name in manager.subagents


def test_subagent_manager_get_subagent(temp_project_root, mock_ai_agent):
    """测试获取子智能体"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        # 获取存在的子智能体
        subagent = manager.get_subagent("anomaly-detection-agent")
        assert subagent is not None
        assert subagent == mock_ai_agent

        # 获取不存在的子智能体
        subagent = manager.get_subagent("non-existent-agent")
        assert subagent is None


def test_subagent_manager_get_all_subagents(temp_project_root, mock_ai_agent):
    """测试获取所有子智能体"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        all_subagents = manager.get_all_subagents()

        assert len(all_subagents) == 4
        # 验证返回的是副本
        all_subagents.clear()
        assert len(manager.subagents) == 4


def test_subagent_manager_list_subagents(temp_project_root, mock_ai_agent):
    """测试列出所有子智能体名称"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        subagent_names = manager.list_subagents()

        assert len(subagent_names) == 4
        assert "anomaly-detection-agent" in subagent_names
        assert "rule-reasoning-agent" in subagent_names


def test_subagent_manager_is_subagent_available(temp_project_root, mock_ai_agent):
    """测试检查子智能体是否可用"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        assert manager.is_subagent_available("anomaly-detection-agent") is True
        assert manager.is_subagent_available("non-existent-agent") is False


def test_subagent_manager_shutdown(temp_project_root, mock_ai_agent):
    """测试关闭子智能体管理器"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        manager.shutdown()

        # 验证所有子智能体被清理
        assert len(manager.subagents) == 0
        assert manager._initialized is False

        # 验证每个子智能体的shutdown方法被调用
        assert mock_ai_agent.shutdown.call_count == 4


def test_subagent_manager_double_initialize(temp_project_root, mock_ai_agent):
    """测试重复初始化"""
    with patch('run_agent.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)

        # 第一次初始化
        manager.create_subagents()
        assert len(manager.subagents) == 4

        # 第二次初始化（应该跳过）
        manager.create_subagents()
        assert len(manager.subagents) == 4  # 数量不变
