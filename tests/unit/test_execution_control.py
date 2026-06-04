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
