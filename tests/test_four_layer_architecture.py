#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四层架构集成测试

测试基于专利的四层架构：
1. 主智能体层（全局决策中枢）
2. 任务编排层（结构化执行枢纽）
3. 子智能体层（能力执行单元）
4. 数据与支撑层（底层支撑）
"""

import sys
import logging
import unittest
from datetime import datetime

# 添加项目路径
sys.path.append("E:/project/Ecological_env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestFourLayerArchitecture(unittest.TestCase):
    """四层架构测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("四层架构集成测试开始")
        logger.info("=" * 60)

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        elapsed = (datetime.now() - cls.start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"四层架构集成测试完成，耗时: {elapsed:.2f}秒")
        logger.info("=" * 60)

    def test_layer1_master_agent_modules(self):
        """测试主智能体层 - 六大功能模块"""
        from workspace.skills.master_agent_core.scripts.nlu_module import NLUModule
        from workspace.skills.master_agent_core.scripts.task_decomposition import TaskDecompositionModule
        from workspace.skills.master_agent_core.scripts.result_reuse import ResultReuseModule
        from workspace.skills.master_agent_core.scripts.scheduling_decision import SchedulingDecisionModule
        from workspace.skills.master_agent_core.scripts.result_interpretation import ResultInterpretationModule
        from workspace.skills.master_agent_core.scripts.adaptive_optimization import AdaptiveOptimizationModule

        # 测试模块初始化
        nlu = NLUModule()
        self.assertEqual(nlu.name, "自然语言理解模块")
        self.assertEqual(nlu.version, "2.0.0")

        decomposition = TaskDecompositionModule()
        self.assertEqual(decomposition.name, "任务分解模块")

        reuse = ResultReuseModule()
        self.assertEqual(reuse.name, "结果复用判决模块")

        scheduling = SchedulingDecisionModule()
        self.assertEqual(scheduling.name, "调度决策模块")

        interpretation = ResultInterpretationModule()
        self.assertEqual(interpretation.name, "结果解释模块")

        optimization = AdaptiveOptimizationModule()
        self.assertEqual(optimization.name, "自适应优化模块")

        logger.info("[TEST] 主智能体层六大模块初始化通过")

    def test_layer2_task_orchestration_modules(self):
        """测试任务编排层 - 四个功能模块"""
        from workspace.skills.master_agent_core.scripts.task_structuring import TaskStructuringModule
        from workspace.skills.master_agent_core.scripts.task_flow_generation import TaskFlowGenerationModule
        from workspace.skills.master_agent_core.scripts.resource_matching import ResourceMatchingModule
        from workspace.skills.master_agent_core.scripts.execution_control import ExecutionControlModule

        # 测试模块初始化
        structuring = TaskStructuringModule()
        self.assertEqual(structuring.name, "任务结构化模块")

        flow_gen = TaskFlowGenerationModule()
        self.assertEqual(flow_gen.name, "任务流生成模块")

        matching = ResourceMatchingModule()
        self.assertEqual(matching.name, "资源匹配模块")

        control = ExecutionControlModule()
        self.assertEqual(control.name, "执行控制模块")

        logger.info("[TEST] 任务编排层四个模块初始化通过")

    def test_layer3_subagent_structure(self):
        """测试子智能体层 - 四类标准子智能体"""
        import os
        from pathlib import Path

        # 检查四类子智能体目录
        subagents = [
            "multi-dimensional-data-perception-agent",
            "disposition-execution-agent",
            "anomaly-detection-agent",
            "rule-reasoning-agent"
        ]

        base_path = Path("E:/project/Ecological_env/subagents")

        for agent in subagents:
            agent_path = base_path / agent
            self.assertTrue(agent_path.exists(), f"子智能体目录不存在: {agent}")

            # 检查必需文件
            self.assertTrue((agent_path / "SOUL.md").exists(), f"SOUL.md不存在: {agent}")
            self.assertTrue((agent_path / "AGENTS.md").exists(), f"AGENTS.md不存在: {agent}")
            self.assertTrue((agent_path / "MEMORY.md").exists(), f"MEMORY.md不存在: {agent}")

        logger.info("[TEST] 四类标准子智能体结构验证通过")

    def test_layer4_data_support_structure(self):
        """测试数据与支撑层 - 底层支撑结构"""
        import os
        from pathlib import Path

        # 检查数据层
        data_path = Path("E:/project/Ecological_env/data")
        self.assertTrue(data_path.exists())
        # 检查数据文件存在
        self.assertTrue((data_path / "pollution_water_in.csv").exists())
        self.assertTrue((data_path / "pollution_water_out.csv").exists())

        # 检查模型层（算子库）
        models_path = Path("E:/project/Ecological_env/shared/models")
        self.assertTrue(models_path.exists())
        for subdir in ["statistical", "machine-learning", "deep-learning"]:
            self.assertTrue((models_path / subdir).exists())

        # 检查配置层
        configs_path = Path("E:/project/Ecological_env/shared/configs")
        self.assertTrue(configs_path.exists())
        self.assertTrue((configs_path / "subagent_registry.json").exists())
        self.assertTrue((configs_path / "system_config.yaml").exists())

        # 检查缓存层
        cache_path = Path("E:/project/Ecological_env/shared/cache")
        self.assertTrue(cache_path.exists())

        logger.info("[TEST] 数据与支撑层结构验证通过")

    def test_nlu_module_parsing(self):
        """测试自然语言理解模块 - 查询解析"""
        from workspace.skills.master_agent_core.scripts.nlu_module import NLUModule

        nlu = NLUModule()

        test_queries = [
            ("分析最近出水的pH和COD有没有异常", "analysis_query"),
            ("查询过去一天的监测数据", "history_query"),
            ("现在系统运行状态怎么样", "status_query"),
            ("生成一份月度报告", "report_generation")
        ]

        for query, expected_intent in test_queries:
            intent = nlu.parse(query)
            self.assertEqual(intent.intent_type, expected_intent)
            self.assertGreater(intent.confidence, 0.5)

        logger.info("[TEST] 自然语言理解模块解析测试通过")

    def test_task_decomposition(self):
        """测试任务分解模块"""
        from workspace.skills.master_agent_core.scripts.nlu_module import NLUModule
        from workspace.skills.master_agent_core.scripts.task_decomposition import TaskDecompositionModule

        nlu = NLUModule()
        decomposition = TaskDecompositionModule()

        query = "分析最近出水的pH和COD有没有异常"
        intent = nlu.parse(query)

        atomic_tasks = decomposition.decompose(intent)

        # 标准流程应该生成4个原子任务
        self.assertEqual(len(atomic_tasks), 4)

        # 检查任务类型顺序
        task_types = [t.task_type for t in atomic_tasks]
        expected_order = ["data_governance", "feature_analysis", "anomaly_detection", "rule_reasoning"]
        self.assertEqual(task_types, expected_order)

        logger.info("[TEST] 任务分解模块测试通过")

    def test_result_reuse_decision(self):
        """测试结果复用判决模块"""
        from workspace.skills.master_agent_core.scripts.nlu_module import NLUModule
        from workspace.skills.master_agent_core.scripts.result_reuse import ResultReuseModule

        nlu = NLUModule()
        reuse = ResultReuseModule()

        query = "分析最近出水的pH和COD"
        intent = nlu.parse(query)

        # 第一次查询应该不复用
        decision1 = reuse.decide(intent)
        self.assertFalse(decision1.can_reuse)
        self.assertEqual(decision1.decision_type, "recompute")

        # 缓存结果
        mock_result = {"summary": "测试结果"}
        reuse.cache_result(intent, mock_result)

        # 第二次相同查询应该复用
        decision2 = reuse.decide(intent)
        self.assertTrue(decision2.can_reuse)
        self.assertEqual(decision2.decision_type, "reuse")
        self.assertIsNotNone(decision2.cached_result)

        logger.info("[TEST] 结果复用判决模块测试通过")

    def test_task_flow_generation(self):
        """测试任务流生成模块"""
        from workspace.skills.master_agent_core.scripts.task_structuring import TaskStructuringModule, StructuredTask
        from workspace.skills.master_agent_core.scripts.task_flow_generation import TaskFlowGenerationModule, ExecutionMode

        structuring = TaskStructuringModule()
        flow_gen = TaskFlowGenerationModule()

        # 创建测试任务
        tasks = []
        for i, task_type in enumerate(["data_governance", "feature_analysis", "anomaly_detection", "rule_reasoning"]):
            task = StructuredTask(
                task_id=f"test_{task_type}",
                task_type=task_type,
                operation="execute",
                input_data={"test": "data"}
            )
            tasks.append(task)

        # 生成任务流
        flow = flow_gen.generate_flow(tasks, ExecutionMode.SEQUENTIAL)

        self.assertEqual(len(flow), 4)
        self.assertEqual(flow.execution_mode, ExecutionMode.SEQUENTIAL)
        self.assertEqual(len(flow.execution_order), 4)

        logger.info("[TEST] 任务流生成模块测试通过")

    def test_scheduling_decision(self):
        """测试调度决策模块"""
        from workspace.skills.master_agent_core.scripts.nlu_module import NLUModule
        from workspace.skills.master_agent_core.scripts.task_decomposition import TaskDecompositionModule
        from workspace.skills.master_agent_core.scripts.result_reuse import ResultReuseModule, ReuseDecision
        from workspace.skills.master_agent_core.scripts.scheduling_decision import SchedulingDecisionModule

        nlu = NLUModule()
        decomposition = TaskDecompositionModule()
        reuse = ResultReuseModule()
        scheduling = SchedulingDecisionModule()

        query = "分析最近出水的pH和COD"
        intent = nlu.parse(query)
        atomic_tasks = decomposition.decompose(intent)
        reuse_decision = ReuseDecision(can_reuse=False, decision_type="recompute")

        instruction = scheduling.generate_schedule(atomic_tasks, reuse_decision, intent)

        self.assertIsNotNone(instruction.schedule_id)
        self.assertEqual(instruction.reuse_decision, "recompute")
        self.assertIsNotNone(instruction.execution_mode)

        logger.info("[TEST] 调度决策模块测试通过")

    def test_result_interpretation(self):
        """测试结果解释模块"""
        from workspace.skills.master_agent_core.scripts.nlu_module import NLUModule
        from workspace.skills.master_agent_core.scripts.result_interpretation import ResultInterpretationModule

        nlu = NLUModule()
        interpretation = ResultInterpretationModule()

        query = "分析最近出水的pH和COD"
        intent = nlu.parse(query)

        # 模拟执行结果
        mock_results = {
            "summary": "监测数据正常",
            "anomalies": [],
            "violations": []
        }

        result = interpretation.interpret(mock_results, intent)

        self.assertIn("response", result)
        self.assertIn("summary", result)
        self.assertEqual(result["status"], "success")  # 修正这里

        logger.info("[TEST] 结果解释模块测试通过")

    def test_adaptive_optimization(self):
        """测试自适应优化模块"""
        from workspace.skills.master_agent_core.scripts.adaptive_optimization import AdaptiveOptimizationModule, Feedback

        optimization = AdaptiveOptimizationModule()

        feedback = Feedback(
            task_id="test_task",
            feedback_type="false_positive",
            content="这是一个误报",
            timestamp=datetime.now().isoformat(),
            user_id="test_user"
        )

        actions = optimization.process_feedback(feedback)

        self.assertGreater(len(actions), 0)

        # 应用优化
        success = optimization.apply_optimizations(actions)
        self.assertTrue(success)

        # 检查统计
        summary = optimization.get_optimization_summary()
        self.assertEqual(summary["total_feedback"], 1)

        logger.info("[TEST] 自适应优化模块测试通过")

    def test_master_agent_layer_integration(self):
        """测试主智能体层集成"""
        from workspace.skills.master_agent_core.scripts.master_agent_layer import MasterAgentLayer

        master = MasterAgentLayer()

        # 测试状态获取
        status = master.get_status()
        self.assertIn("name", status)
        self.assertIn("version", status)
        self.assertIn("modules", status)

        logger.info("[TEST] 主智能体层集成测试通过")

    def test_task_orchestration_layer_integration(self):
        """测试任务编排层集成"""
        from workspace.skills.master_agent_core.scripts.task_orchestration_layer import TaskOrchestrationLayer

        orchestration = TaskOrchestrationLayer()

        # 测试状态获取
        status = orchestration.get_status()
        self.assertIn("name", status)
        self.assertIn("version", status)
        self.assertIn("modules", status)

        logger.info("[TEST] 任务编排层集成测试通过")

    def test_standard_workflow_execution(self):
        """测试标准工作流执行（模拟）"""
        from workspace.skills.master_agent_core.scripts.task_orchestration_layer import TaskOrchestrationLayer

        orchestration = TaskOrchestrationLayer()

        # 创建测试输入
        test_input = {
            "monitoring_point": "outlet_001",
            "indicators": ["pH", "COD"],
            "time_range": {
                "start": "2026-05-07T00:00:00Z",
                "end": "2026-05-07T01:00:00Z"
            }
        }

        # 生成标准流程
        flow = orchestration.task_flow_generation.generate_standard_flow(test_input)

        self.assertEqual(len(flow), 4)  # 四层标准流程

        # 检查执行顺序
        expected_order = ["data_governance", "feature_analysis", "anomaly_detection", "rule_reasoning"]
        actual_order = [flow.tasks[i].task_type for i in range(len(flow))]
        self.assertEqual(actual_order, expected_order)

        logger.info("[TEST] 标准工作流执行测试通过")


class TestInterfaceCompatibility(unittest.TestCase):
    """接口兼容性测试"""

    def test_subagent_protocol_compliance(self):
        """测试子智能体协议合规性"""
        import json
        from pathlib import Path

        protocol_file = Path("E:/project/Ecological_env/interfaces/subagent_protocol.md")
        self.assertTrue(protocol_file.exists())

        # 检查输入输出模式文件
        input_schema = Path("E:/project/Ecological_env/interfaces/input_schema.json")
        output_schema = Path("E:/project/Ecological_env/interfaces/output_schema.json")

        self.assertTrue(input_schema.exists())
        self.assertTrue(output_schema.exists())

        # 验证JSON格式
        with open(input_schema, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertIn("$schema", data)

        with open(output_schema, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertIn("$schema", data)

        logger.info("[TEST] 子智能体协议合规性测试通过")

    def test_registry_compliance(self):
        """测试注册表合规性"""
        import json
        from pathlib import Path

        registry_file = Path("E:/project/Ecological_env/shared/configs/subagent_registry.json")

        self.assertTrue(registry_file.exists())

        with open(registry_file, 'r', encoding='utf-8') as f:
            registry = json.load(f)

        # 检查注册表结构
        self.assertIn("registry", registry)
        self.assertIn("agents", registry["registry"])

        # 检查四类子智能体
        agent_ids = [agent["id"] for agent in registry["registry"]["agents"]]
        expected_agents = [
            "multi-dimensional-data-perception-agent",
            "feature-analysis-agent",
            "anomaly-detection-agent",
            "rule-reasoning-agent"
        ]

        for expected_agent in expected_agents:
            self.assertIn(expected_agent, agent_ids)

        logger.info("[TEST] 注册表合规性测试通过")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestFourLayerArchitecture))
    suite.addTests(loader.loadTestsFromTestCase(TestInterfaceCompatibility))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
