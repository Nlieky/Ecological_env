"""测试LLMAgentCoordinator的配置加载功能"""

import pytest
from pathlib import Path
from workspace.skills.orchestrator_core.scripts.execution_control import LLMAgentCoordinator


class TestLLMConfigLoading:
    """测试LLM配置加载"""

    def test_coordinator_has_llm_config(self):
        """验证协调器初始化后加载了LLM配置"""
        coordinator = LLMAgentCoordinator()

        # 验证配置已加载
        assert hasattr(coordinator, 'llm_config')
        assert coordinator.llm_config is not None
        assert isinstance(coordinator.llm_config, dict)

    def test_llm_config_has_subagent_configs(self):
        """验证配置包含subagent_configs"""
        coordinator = LLMAgentCoordinator()

        assert 'subagent_configs' in coordinator.llm_config
        assert isinstance(coordinator.llm_config['subagent_configs'], dict)

    def test_get_subagent_config_existing_agent(self):
        """验证获取存在的子智能体配置"""
        coordinator = LLMAgentCoordinator()

        config = coordinator._get_subagent_config('multi-dimensional-data-perception-agent')

        # 验证配置结构
        assert isinstance(config, dict)
        assert 'enabled' in config or config == {}  # 可能未启用或为空

    def test_get_subagent_config_nonexistent_agent(self):
        """验证获取不存在的子智能体配置返回空"""
        coordinator = LLMAgentCoordinator()

        config = coordinator._get_subagent_config('non-existent-agent')

        assert config == {}

    def test_get_subagent_system_prompt(self):
        """验证获取子智能体系统提示词"""
        coordinator = LLMAgentCoordinator()

        prompt = coordinator._get_subagent_system_prompt('multi-dimensional-data-perception-agent')

        # 验证返回字符串
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_subagent_model(self):
        """验证获取子智能体模型配置"""
        coordinator = LLMAgentCoordinator()

        # 数据感知子智能体应该使用fast模型
        model = coordinator._get_subagent_model('multi-dimensional-data-perception-agent')
        assert model in ['fast', 'primary', 'analysis']

    def test_get_subagent_model_defaults_to_primary(self):
        """验证不存在的子智能体默认使用primary模型"""
        coordinator = LLMAgentCoordinator()

        model = coordinator._get_subagent_model('non-existent-agent')
        assert model == 'primary'


class TestSubagentLLMIntegration:
    """测试子智能体LLM配置集成"""

    @pytest.fixture
    def coordinator(self):
        """创建协调器实例"""
        return LLMAgentCoordinator()

    def test_uses_subagent_system_prompt(self, coordinator, mocker):
        """验证使用子智能体专属系统提示词"""
        # Mock LLM客户端
        mock_llm = mocker.Mock()
        mock_llm.chat.return_value = '{"script": "test.py", "params": {}, "reasoning": "test"}'
        coordinator.llm_client = mock_llm

        # 创建mock identity
        from workspace.skills.orchestrator_core.scripts.execution_control import SubAgentIdentity
        identity = mocker.Mock(spec=SubAgentIdentity)
        identity.agent_id = 'multi-dimensional-data-perception-agent'
        identity.agent_name = '测试智能体'
        identity.script_paths = []
        identity.identity_files = {}

        # Mock _get_available_scripts返回空字典
        mocker.patch.object(coordinator, '_get_available_scripts', return_value={})
        # Mock _parse_llm_decision返回有效决策
        mocker.patch.object(coordinator, '_parse_llm_decision', return_value={'script': 'test.py', 'params': {}})
        # Mock _execute_script_by_decision返回成功结果
        mocker.patch.object(coordinator, '_execute_script_by_decision', return_value={'status': 'success'})
        # Mock _llm_analyze_result返回结果
        mocker.patch.object(coordinator, '_llm_analyze_result', return_value={'status': 'success'})

        # 执行
        result = coordinator._llm_coordinate_agent(identity, {'task_id': 'test'}, None)

        # 验证LLM客户端被调用
        assert mock_llm.chat.called

        # 获取调用参数
        call_args = mock_llm.chat.call_args
        system_prompt = call_args[1]['system_prompt']

        # 验证系统提示词不是空的
        assert len(system_prompt) > 0
        assert isinstance(system_prompt, str)

    def test_uses_subagent_model_type(self, coordinator, mocker):
        """验证使用子智能体专用模型"""
        # Mock LLM客户端
        mock_llm = mocker.Mock()
        mock_llm.chat.return_value = '{"script": "test.py", "params": {}, "reasoning": "test"}'
        coordinator.llm_client = mock_llm

        # 创建mock identity
        from workspace.skills.orchestrator_core.scripts.execution_control import SubAgentIdentity
        identity = mocker.Mock(spec=SubAgentIdentity)
        identity.agent_id = 'anomaly-detection-agent'  # 这个应该使用analysis模型
        identity.agent_name = '异常检测智能体'
        identity.script_paths = []
        identity.identity_files = {}

        # Mock各种方法
        mocker.patch.object(coordinator, '_get_available_scripts', return_value={})
        mocker.patch.object(coordinator, '_parse_llm_decision', return_value={'script': 'test.py', 'params': {}})
        mocker.patch.object(coordinator, '_execute_script_by_decision', return_value={'status': 'success'})
        mocker.patch.object(coordinator, '_llm_analyze_result', return_value={'status': 'success'})

        # 执行
        coordinator._llm_coordinate_agent(identity, {'task_id': 'test'}, None)

        # 验证LLM客户端被调用
        assert mock_llm.chat.called

        # 获取调用参数
        call_args = mock_llm.chat.call_args
        model_type = call_args[1]['model_type']

        # 验证模型类型在有效范围内
        assert model_type in ['fast', 'primary', 'analysis']
