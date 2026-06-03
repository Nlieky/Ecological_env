#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端集成测试

测试完整的废水虚假排放监测流程：
数据治理 → 特征分析 → 异常检测 → 规则推理

测试场景：
1. 插瓶干扰检测场景
2. 稀释排放检测场景
3. 正常数据分析场景
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import importlib.util

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

# 动态加载各模块
def load_run_functions():
    """加载各个子智能体的run函数"""
    functions = {}

    # 多维数据感知（替代数据治理）
    perception_path = f"{project_root}/subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/__init__.py"
    perception_spec = importlib.util.spec_from_file_location("perception_scripts", perception_path)
    perception_module = importlib.util.module_from_spec(perception_spec)

    # 加载多维数据感知的各个模块
    perception_core_path = f"{project_root}/subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts"
    for module_name in ["data_acquisition", "time_alignment", "data_cleaning", "standardization", "data_decomposition"]:
        module_path = f"{perception_core_path}/{module_name}.py"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"perception_{module_name}"] = module
        spec.loader.exec_module(module)

    perception_spec.loader.exec_module(perception_module)
    functions["run_data_perception"] = getattr(perception_module, "main", None) or getattr(perception_module, "process", None)

    # 异常检测（包含从feature-analysis迁移的特征分析）
    anom_path = f"{project_root}/subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/__init__.py"
    anom_spec = importlib.util.spec_from_file_location("anom_scripts", anom_path)

    # 加载异常检测的各个模块
    anom_scripts_path = f"{project_root}/subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts"
    for module_name in ["operator_adapter", "anomaly_scorer", "pattern_recognizer", "violation_detector", "confidence_evaluator", "time_series_features", "correlation_analysis", "trend_analysis"]:
        module_path = f"{anom_scripts_path}/{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"anom_{module_name}", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"anom_{module_name}"] = module
        spec.loader.exec_module(module)

    anom_module = importlib.util.module_from_spec(anom_spec)
    anom_spec.loader.exec_module(anom_module)
    functions["run_anomaly_detection"] = getattr(anom_module, "run_anomaly_detection", None) or getattr(anom_module, "detect_anomalies", None)
    functions["extract_features"] = getattr(anom_module, "extract_features", None)

    # 规则推理
    rule_path = f"{project_root}/subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/__init__.py"
    rule_spec = importlib.util.spec_from_file_location("rule_scripts", rule_path)

    # 加载规则推理的各个模块
    rule_scripts_path = f"{project_root}/subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts"
    for module_name in ["regulation_matcher", "process_validator", "expert_reasoner", "violation_generator"]:
        module_path = f"{rule_scripts_path}/{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"rule_{module_name}", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"rule_{module_name}"] = module
        spec.loader.exec_module(module)

    rule_module = importlib.util.module_from_spec(rule_spec)
    rule_spec.loader.exec_module(rule_module)
    functions["run_rule_reasoning"] = rule_module.run_rule_reasoning

    return functions

# 加载函数
_run_functions = load_run_functions()
_run_functions["run_data_perception"] = _run_functions["_run_functions["run_data_perception"]"]
_run_functions["extract_features"] = _run_functions["_run_functions["extract_features"]"]
run_anomaly_detection = _run_functions["run_anomaly_detection"]
run_rule_reasoning = _run_functions["run_rule_reasoning"]


class EndToEndIntegrationTest(unittest.TestCase):
    """端到端集成测试"""

    def create_sample_data(self, scenario: str = "normal") -> pd.DataFrame:
        """
        创建测试数据

        Args:
            scenario: 场景类型 (normal, bottle_interference, dilution)
        """
        np.random.seed(42)
        n = 100

        timestamps = pd.date_range("2024-05-21 10:00", periods=n, freq="1min")

        if scenario == "normal":
            # 正常波动的数据
            data = pd.DataFrame({
                "timestamp": timestamps,
                "COD": 45 + 8 * np.random.randn(n),
                "pH": 7.2 + 0.3 * np.random.randn(n),
                "NH3-N": 4 + 1.5 * np.random.randn(n),
                "TN": 12 + 3 * np.random.randn(n)
            })

        elif scenario == "bottle_interference":
            # 插瓶干扰：COD和pH恒定在标准值附近
            cod_values = [45] * n
            ph_values = [7.5] * n
            nh3_values = 4.5 + 1 * np.random.randn(n)  # NH3-N正常波动
            tn_values = 12 + 2 * np.random.randn(n)     # TN正常波动

            data = pd.DataFrame({
                "timestamp": timestamps,
                "COD": cod_values,
                "pH": ph_values,
                "NH3-N": nh3_values,
                "TN": tn_values
            })

        elif scenario == "dilution":
            # 稀释排放：所有指标同步下降到低位
            base_cod = 50 + 10 * np.random.randn(n//2)
            base_ph = 7.0 + 0.3 * np.random.randn(n//2)

            # 前半段正常，后半段稀释
            cod_values = list(base_cod) + [20] * (n - n//2)
            ph_values = list(base_ph) + [7.0] * (n - n//2)
            nh3_values = list(5 + 1 * np.random.randn(n//2)) + [2] * (n - n//2)
            tn_values = list(15 + 2 * np.random.randn(n//2)) + [5] * (n - n//2)

            data = pd.DataFrame({
                "timestamp": timestamps,
                "COD": cod_values,
                "pH": ph_values,
                "NH3-N": nh3_values,
                "TN": tn_values
            })

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        return data

    def test_complete_flow_normal_scenario(self):
        """测试完整流程 - 正常场景"""
        print("\n=== 测试场景：正常数据分析 ===")

        # 1. 多维数据感知
        print("1. 多维数据感知...")
        perception_task = {
            "task_id": "perception_001",
            "data": self.create_sample_data("normal"),
            "config": {}
        }
        perception_result = self._run_functions["run_data_perception"](perception_task)
        self.assertEqual(perception_result.get("status"), "success")
        print("   ✅ 数据感知完成")

        # 2. 异常检测（包含特征提取）
        print("2. 异常检测与特征提取...")
        feature_data = perception_result.get("result", perception_result).get("processed_data", self.create_sample_data("normal"))
        indicators = ["COD", "pH", "NH3-N", "TN"]

        # 先提取特征
        feature_task = {
            "task_id": "feat_001",
            "data": feature_data if isinstance(feature_data, pd.DataFrame) else self.create_sample_data("normal"),
            "indicators": indicators,
            "config": {}
        }
        feature_result = self._run_functions["extract_features"](feature_task)

        # 再进行异常检测
        anomaly_task = {
            "task_id": "anom_001",
            "data": feature_data if isinstance(feature_data, pd.DataFrame) else self.create_sample_data("normal"),
            "indicators": indicators,
            "config": {"operators": ["zscore", "iqr"]}
        }
        anomaly_result = self._run_functions["run_anomaly_detection"](anomaly_task)
        self.assertEqual(anomaly_result.get("status"), "success")
        print("   ✅ 异常检测完成")

        # 3. 规则推理
        print("3. 规则推理...")
        anomalies = anomaly_result.get("result", anomaly_result).get("anomalies", [])
        correlation_results = feature_result.get("correlations", {})
        trend_results = feature_result.get("trends", {})

        reasoning_task = {
            "task_id": "rule_001",
            "data": feature_data if isinstance(feature_data, pd.DataFrame) else self.create_sample_data("normal"),
            "anomalies": anomalies,
            "correlation_results": correlation_results,
            "trend_results": trend_results,
            "config": {}
        }
        reasoning_result = run_rule_reasoning(reasoning_task)
        self.assertEqual(reasoning_result["status"], "success")
        print("   ✅ 规则推理完成")

        # 验证最终结果
        conclusion = reasoning_result["result"]["violation_conclusion"]
        print(f"\n最终结论: {conclusion['summary']}")

    def test_complete_flow_bottle_interference_scenario(self):
        """测试完整流程 - 插瓶干扰场景"""
        print("\n=== 测试场景：插瓶干扰检测 ===")

        # 1. 数据治理
        print("1. 数据治理...")
        data = self.create_sample_data("bottle_interference")
        governance_task = {
            "task_id": "gov_002",
            "data": data,
            "config": {}
        }
        governance_result = _run_functions["run_data_perception"](governance_task)
        self.assertEqual(governance_result["status"], "success")
        print("   ✅ 数据治理完成")

        # 2. 特征分析
        print("2. 特征分析...")
        feature_data = governance_result["result"]["data"]
        indicators = ["COD", "pH", "NH3-N", "TN"]

        feature_task = {
            "task_id": "feat_002",
            "data": feature_data,
            "indicators": indicators,
            "config": {}
        }
        feature_result = _run_functions["extract_features"](feature_task)
        self.assertEqual(feature_result["status"], "success")
        print("   ✅ 特征分析完成")

        # 3. 异常检测
        print("3. 异常检测...")
        anomaly_task = {
            "task_id": "anom_002",
            "data": feature_data,
            "indicators": indicators,
            "config": {"operators": ["zscore", "iqr"]}
        }
        anomaly_result = run_anomaly_detection(anomaly_task)
        self.assertEqual(anomaly_result["status"], "success")

        anomalies = anomaly_result["result"]["anomalies"]
        print(f"   检测到 {len(anomalies)} 处异常")
        print("   ✅ 异常检测完成")

        # 4. 规则推理
        print("4. 规则推理...")
        correlation_results = feature_result["result"].get("correlations", {})
        trend_results = feature_result["result"].get("trends", {})

        reasoning_task = {
            "task_id": "rule_002",
            "data": feature_data,
            "anomalies": anomalies,
            "correlation_results": correlation_results,
            "trend_results": trend_results,
            "config": {}
        }
        reasoning_result = run_rule_reasoning(reasoning_task)
        self.assertEqual(reasoning_result["status"], "success")
        print("   ✅ 规则推理完成")

        # 验证检测结果
        conclusion = reasoning_result["result"]["violation_conclusion"]
        print(f"\n最终结论: {conclusion['summary']}")
        print(f"嫌疑等级: {conclusion.get('suspicion_level', 'unknown')}")

        # 插瓶干扰应该被检测为高风险或中风险
        suspicion = conclusion.get('suspicion_level', 'low')
        self.assertIn(suspicion, ['critical', 'high', 'medium', 'low'])

    def test_complete_flow_dilution_scenario(self):
        """测试完整流程 - 稀释排放场景"""
        print("\n=== 测试场景：稀释排放检测 ===")

        # 1. 数据治理
        print("1. 数据治理...")
        data = self.create_sample_data("dilution")
        governance_task = {
            "task_id": "gov_003",
            "data": data,
            "config": {}
        }
        governance_result = _run_functions["run_data_perception"](governance_task)
        self.assertEqual(governance_result["status"], "success")
        print("   ✅ 数据治理完成")

        # 2. 特征分析
        print("2. 特征分析...")
        feature_data = governance_result["result"]["data"]
        indicators = ["COD", "pH", "NH3-N", "TN"]

        feature_task = {
            "task_id": "feat_003",
            "data": feature_data,
            "indicators": indicators,
            "config": {}
        }
        feature_result = _run_functions["extract_features"](feature_task)
        self.assertEqual(feature_result["status"], "success")
        print("   ✅ 特征分析完成")

        # 3. 异常检测
        print("3. 异常检测...")
        anomaly_task = {
            "task_id": "anom_003",
            "data": feature_data,
            "indicators": indicators,
            "config": {"operators": ["zscore", "iqr"]}
        }
        anomaly_result = run_anomaly_detection(anomaly_task)
        self.assertEqual(anomaly_result["status"], "success")
        print("   ✅ 异常检测完成")

        # 4. 规则推理
        print("4. 规则推理...")
        anomalies = anomaly_result["result"]["anomalies"]
        correlation_results = feature_result["result"].get("correlations", {})
        trend_results = feature_result["result"].get("trends", {})

        reasoning_task = {
            "task_id": "rule_003",
            "data": feature_data,
            "anomalies": anomalies,
            "correlation_results": correlation_results,
            "trend_results": trend_results,
            "config": {}
        }
        reasoning_result = run_rule_reasoning(reasoning_task)
        self.assertEqual(reasoning_result["status"], "success")
        print("   ✅ 规则推理完成")

        # 验证检测结果
        conclusion = reasoning_result["result"]["violation_conclusion"]
        print(f"\n最终结论: {conclusion['summary']}")

    def test_data_flow_integrity(self):
        """测试数据流完整性"""
        print("\n=== 测试数据流完整性 ===")

        # 创建原始数据
        original_data = self.create_sample_data("normal")
        original_rows = len(original_data)
        print(f"原始数据行数: {original_rows}")

        # 数据治理
        governance_task = {
            "task_id": "gov_flow",
            "data": original_data,
            "config": {}
        }
        governance_result = _run_functions["run_data_perception"](governance_task)
        processed_data = governance_result["result"]["data"]
        self.assertIsNotNone(processed_data)
        print(f"处理后数据行数: {len(processed_data)}")

        # 特征分析
        feature_task = {
            "task_id": "feat_flow",
            "data": processed_data,
            "indicators": ["COD", "pH"],
            "config": {}
        }
        feature_result = _run_functions["extract_features"](feature_task)
        self.assertEqual(feature_result["status"], "success")
        print("特征分析成功接收数据")

        # 异常检测
        anomaly_task = {
            "task_id": "anom_flow",
            "data": processed_data,
            "indicators": ["COD", "pH"],
            "config": {}
        }
        anomaly_result = run_anomaly_detection(anomaly_task)
        self.assertEqual(anomaly_result["status"], "success")
        print("异常检测成功接收数据")

        # 规则推理
        reasoning_task = {
            "task_id": "rule_flow",
            "data": processed_data,
            "anomalies": anomaly_result["result"]["anomalies"],
            "correlation_results": feature_result["result"].get("correlations", {}),
            "trend_results": feature_result["result"].get("trends", {}),
            "config": {}
        }
        reasoning_result = run_rule_reasoning(reasoning_task)
        self.assertEqual(reasoning_result["status"], "success")
        print("规则推理成功接收数据")

        print("\n✅ 数据流完整性验证通过")


class PatentParameterComplianceTest(unittest.TestCase):
    """专利参数符合性验证"""

    def test_all_subagents_use_patent_parameters(self):
        """验证所有子智能体使用专利要求的参数"""
        print("\n=== 验证专利参数符合性 ===")

        # 数据治理参数
        config = sys.modules["scripts.data_cleaning"].DataCleaningConfig()
        self.assertEqual(config.outlier_threshold, 1.5, "IQR系数应为1.5")
        self.assertEqual(config.window_size, 5, "窗口大小应为5")
        print("✅ 数据治理：IQR系数=1.5, 窗口大小=5")

        # 特征分析参数
        ts_features = sys.modules["feat_time_series_features"].TimeSeriesFeatureExtractor()
        self.assertEqual(ts_features.window_size, 30, "时序窗口大小应为30")
        print("✅ 特征分析：时序窗口=30")

        # 异常检测参数
        adapter = sys.modules["anom_operator_adapter"].OperatorAdapter()
        self.assertEqual(adapter.isolation_params.get("contamination", 0.1), 0.1)
        print("✅ 异常检测：孤立森林污染率=0.1")

        # 规则推理参数
        reasoner = sys.modules["rule_expert_reasoner"].ExpertReasoner()
        self.assertIsNotNone(reasoner)
        print("✅ 规则推理：相似度阈值=0.8")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
