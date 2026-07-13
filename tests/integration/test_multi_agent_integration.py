# tests/integration/test_multi_agent_integration.py
"""多智能体架构集成测试

测试主智能体、子智能体管理器、调用工具的完整集成流程
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, create_autospec
import sys
import os

# 添加scripts目录到路径
scripts_dir = Path(__file__).parents[2] / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(scripts_dir))

# 在导入前设置mock
def mock_aiagent_factory(**kwargs):
    """工厂函数创建模拟AIAgent"""
    # 接受所有 kwargs 但忽略它们（因为这是 mock）
    mock = MagicMock()
    mock.run_conversation = MagicMock(return_value={
        "final_response": "Test subagent response"
    })
    return mock

# 伪造的 run_agent 模块
class FakeAIAgent:
    """伪造的AIAgent类"""
    def __init__(self, **kwargs):
        # 接受所有参数但什么都不做
        pass

    def run_conversation(self, prompt):
        return {"final_response": "Test subagent response"}

    def shutdown(self):
        pass

# 创建伪造的 run_agent 模块
fake_run_agent = MagicMock()
fake_run_agent.AIAgent = FakeAIAgent


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
def test_full_integration_flow(temp_project_structure):
    """测试完整的集成流程"""
    # 使用 sys.modules 注入来 mock run_agent 模块
    import sys
    original_run_agent = sys.modules.get('run_agent')

    try:
        # 注入伪造的 run_agent 模块
        sys.modules['run_agent'] = fake_run_agent

        # 导入模块（现在会使用伪造的模块）
        import subagent_manager as subagent_manager_module

        # 1. 创建SubagentManager实例
        manager = subagent_manager_module.SubagentManager(project_root=temp_project_structure)

        # 2. 初始化子智能体
        manager.create_subagents()
        assert len(manager.subagents) == 4

        # 3. 验证子智能体可用
        subagent_names = manager.list_subagents()
        assert len(subagent_names) == 4

        # 4. 获取子智能体实例
        subagent = manager.get_subagent("anomaly-detection-agent")
        assert subagent is not None

        # 5. 调用子智能体
        result = subagent.run_conversation("检测异常")
        assert result["final_response"] == "Test subagent response"

        # 6. 关闭子智能体
        manager.shutdown()
        assert len(manager.subagents) == 0
    finally:
        # 恢复原始模块
        if original_run_agent is not None:
            sys.modules['run_agent'] = original_run_agent
        elif 'run_agent' in sys.modules:
            del sys.modules['run_agent']


@pytest.mark.integration
def test_multi_subagent_call_sequence(temp_project_structure):
    """测试顺序调用多个子智能体"""
    import sys
    original_run_agent = sys.modules.get('run_agent')

    try:
        # 注入伪造的 run_agent 模块
        sys.modules['run_agent'] = fake_run_agent

        # 重新导入模块
        import subagent_manager as subagent_manager_module

        # 创建SubagentManager实例
        manager = subagent_manager_module.SubagentManager(project_root=temp_project_structure)

        # 初始化
        manager.create_subagents()

        # 按顺序调用多个子智能体
        sequence = [
            ("multi-dimensional-data-perception-agent", "获取数据"),
            ("anomaly-detection-agent", "检测异常"),
            ("rule-reasoning-agent", "规则验证"),
        ]

        for name, task in sequence:
            subagent = manager.get_subagent(name)
            assert subagent is not None
            result = subagent.run_conversation(task)
            assert result["final_response"] == "Test subagent response"
            print(f"{name}: {result['final_response']}")
    finally:
        # 恢复原始模块
        if original_run_agent is not None:
            sys.modules['run_agent'] = original_run_agent
        elif 'run_agent' in sys.modules:
            del sys.modules['run_agent']


@pytest.mark.integration
def test_subagent_error_handling(temp_project_structure):
    """测试子智能体错误处理"""
    import sys
    original_run_agent = sys.modules.get('run_agent')

    try:
        # 创建会抛出异常的伪造 AIAgent
        class FailingAIAgent:
            def __init__(self, **kwargs):
                pass

            def run_conversation(self, prompt):
                raise Exception("Test error")

        failing_run_agent = MagicMock()
        failing_run_agent.AIAgent = FailingAIAgent

        # 注入伪造的 run_agent 模块
        sys.modules['run_agent'] = failing_run_agent

        # 重新导入模块
        import subagent_manager as subagent_manager_module

        # 创建SubagentManager实例
        manager = subagent_manager_module.SubagentManager(project_root=temp_project_structure)

        # 初始化
        manager.create_subagents()

        # 获取子智能体
        subagent = manager.get_subagent("anomaly-detection-agent")
        assert subagent is not None

        # 调用会抛出异常
        with pytest.raises(Exception, match="Test error"):
            subagent.run_conversation("检测异常")
    finally:
        # 恢复原始模块
        if original_run_agent is not None:
            sys.modules['run_agent'] = original_run_agent
        elif 'run_agent' in sys.modules:
            del sys.modules['run_agent']
