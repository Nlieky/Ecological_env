#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子智能体LLM配置端到端集成测试"""

import sys
import os
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent

# 添加orchestrator-core路径
orchestrator_scripts = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(orchestrator_scripts))

# 添加shared路径
shared_path = project_root / "shared" / "configs"
sys.path.insert(0, str(shared_path))

import pytest
from workspace.skills.orchestrator_core.scripts.execution_control import LLMAgentCoordinator
from shared.configs.llm_client import get_llm_client


class TestEndToEndSubagentLLM:
    """端到端测试子智能体LLM配置"""

    @pytest.fixture
    def llm_client(self):
        """创建LLM客户端"""
        try:
            return get_llm_client()
        except Exception:
            pytest.skip("无法初始化LLM客户端")

    @pytest.fixture
    def coordinator(self, llm_client):
        """创建协调器"""
        return LLMAgentCoordinator(llm_client=llm_client, project_root=project_root)

    def test_data_perception_agent_uses_fast_model(self, coordinator):
        """验证数据感知子智能体使用fast模型"""
        model = coordinator._get_subagent_model('multi-dimensional-data-perception-agent')
        assert model == 'fast', f"预期fast模型，实际使用{model}"

    def test_anomaly_detection_agent_uses_analysis_model(self, coordinator):
        """验证异常检测子智能体使用analysis模型"""
        model = coordinator._get_subagent_model('anomaly-detection-agent')
        assert model == 'analysis', f"预期analysis模型，实际使用{model}"

    def test_rule_reasoning_agent_uses_primary_model(self, coordinator):
        """验证规则推理子智能体使用primary模型"""
        model = coordinator._get_subagent_model('rule-reasoning-agent')
        assert model == 'primary', f"预期primary模型，实际使用{model}"

    def test_disposition_execution_agent_uses_primary_model(self, coordinator):
        """验证研判预警与处置执行子智能体使用primary模型"""
        model = coordinator._get_subagent_model('disposition-execution-agent')
        assert model == 'primary', f"预期primary模型，实际使用{model}"

    def test_all_agents_have_system_prompts(self, coordinator):
        """验证所有子智能体都有system_prompt配置"""
        agent_ids = coordinator.get_all_agents()

        for agent_id in agent_ids:
            prompt = coordinator._get_subagent_system_prompt(agent_id)
            assert len(prompt) > 0, f"{agent_id} 的system_prompt为空"
            assert isinstance(prompt, str), f"{agent_id} 的system_prompt不是字符串"

    def test_coordinate_agent_execution_with_llm_config(self, coordinator, mocker):
        """测试coordinate_agent_execution使用LLM配置"""
        # 只测试LLM可用的情况
        if coordinator.llm_client is None:
            pytest.skip("LLM客户端不可用")

        # Mock identity loader返回有效identity
        from workspace.skills.orchestrator_core.scripts.execution_control import SubAgentIdentity
        mock_identity = mocker.Mock(spec=SubAgentIdentity)
        mock_identity.agent_id = 'multi-dimensional-data-perception-agent'
        mock_identity.agent_name = '多维数据感知子智能体'
        mock_identity.script_paths = []
        mock_identity.identity_files = {}

        mocker.patch.object(coordinator.identity_loader, 'load_agent_identity', return_value=mock_identity)

        # Mock各种方法避免实际执行
        mocker.patch.object(coordinator, '_get_available_scripts', return_value={'__init__.py': {'path': 'test', 'description': 'test'}})
        mocker.patch.object(coordinator, '_parse_llm_decision', return_value={'script': '__init__.py', 'params': {}})
        mocker.patch.object(coordinator, '_execute_script_by_decision', return_value={'status': 'success', 'processed_data': {}})
        mocker.patch.object(coordinator, '_llm_analyze_result', return_value={'status': 'success'})

        # 执行
        result = coordinator.coordinate_agent_execution(
            agent_id='multi-dimensional-data-perception-agent',
            task={'task_id': 'test-task', 'description': '测试任务', 'metadata': {'data_count': 100}}
        )

        # 验证结果
        assert result is not None
        assert 'status' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
