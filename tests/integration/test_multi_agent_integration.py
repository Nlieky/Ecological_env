# tests/integration/test_multi_agent_integration.py
"""多智能体架构集成测试

测试主智能体、子智能体管理器、调用工具的完整集成流程
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加scripts目录到路径
scripts_dir = Path(__file__).parents[2] / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def mock_subagent():
    """模拟子智能体"""
    mock = MagicMock()
    mock.run_conversation = MagicMock(return_value={
        "final_response": "Test subagent response"
    })
    return mock


@pytest.fixture
def temp_project_structure(tmp_path):
    """创建临时项目结构"""
    # 创建主智能体工作区
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("# 主智能体SOUL")

    # 创建子智能体工作区
    subagents = {
        "multi-dimensional-data-perception-agent": "多维数据感知",
        "anomaly-detection-agent": "异常检测",
        "rule-reasoning-agent": "规则推理",
        "disposition-execution-agent": "研判预警"
    }

    for name, desc in subagents.items():
        subagent_path = tmp_path / "subagents" / name
        subagent_path.mkdir(parents=True)
        (subagent_path / "SOUL.md").write_text(f"# {desc}子智能体")

    return tmp_path


@pytest.mark.integration
def test_full_integration_flow(temp_project_structure, mock_subagent):
    """测试完整的集成流程"""
    # Patch run_agent.AIAgent where it's imported in subagent_manager
    with patch('run_agent.AIAgent', return_value=mock_subagent, create=True):
        # 导入模块（使用临时项目结构）
        import subagent_tools

        # Reset global manager
        subagent_tools._subagent_manager = None
        subagent_tools.get_subagent_manager().project_root = temp_project_structure

        # 1. 初始化子智能体
        init_result = subagent_tools.initialize_subagents()
        assert init_result["success"] is True
        assert init_result["count"] == 4

        # 2. 查看可用子智能体
        list_result = subagent_tools.list_available_subagents()
        assert list_result["success"] is True
        assert len(list_result["subagents"]) == 4

        # 3. 调用子智能体
        call_result = subagent_tools.call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测异常"
        )
        assert call_result["success"] is True
        assert "result" in call_result

        # 4. 关闭子智能体
        shutdown_result = subagent_tools.shutdown_subagents()
        assert shutdown_result["success"] is True


@pytest.mark.integration
def test_multi_subagent_call_sequence(temp_project_structure, mock_subagent):
    """测试顺序调用多个子智能体"""
    with patch('run_agent.AIAgent', return_value=mock_subagent, create=True):
        import subagent_tools

        # Reset global manager
        subagent_tools._subagent_manager = None
        subagent_tools.get_subagent_manager().project_root = temp_project_structure

        # 初始化
        subagent_tools.initialize_subagents()

        # 按顺序调用多个子智能体
        sequence = [
            ("multi-dimensional-data-perception-agent", "获取数据"),
            ("anomaly-detection-agent", "检测异常"),
            ("rule-reasoning-agent", "规则验证"),
        ]

        for name, task in sequence:
            result = subagent_tools.call_subagent(name, task)
            assert result["success"] is True
            print(f"{name}: {result['result']}")


@pytest.mark.integration
def test_subagent_error_handling(temp_project_structure):
    """测试子智能体错误处理"""
    # Create a mock subagent that raises an error
    mock_failing_subagent = MagicMock()
    mock_failing_subagent.run_conversation = MagicMock(side_effect=Exception("Test error"))

    with patch('run_agent.AIAgent', return_value=mock_failing_subagent, create=True):
        import subagent_tools

        # Reset global manager
        subagent_tools._subagent_manager = None
        subagent_tools.get_subagent_manager().project_root = temp_project_structure

        # 初始化
        subagent_tools.initialize_subagents()

        # 调用失败的子智能体
        result = subagent_tools.call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测异常"
        )

        assert result["success"] is False
        assert "error" in result
