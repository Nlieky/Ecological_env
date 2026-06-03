#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则推理核心技能包单元测试

测试范围：
1. 法规规则匹配
2. 工艺机理校验
3. 专家经验推理
4. 违规结论生成
5. 完整流程
6. 专利符合性
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加技能包路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.regulation_matcher import RegulationMatcher
from scripts.process_validator import ProcessValidator
from scripts.expert_reasoner import ExpertReasoner
from scripts.violation_generator import ViolationGenerator
from scripts import run_rule_reasoning


class TestRegulationMatcher(unittest.TestCase):
    """测试法规规则匹配模块"""

    def setUp(self):
        """创建测试数据"""
        self.matcher = RegulationMatcher()

        # 创建测试数据
        np.random.seed(42)
        n = 100

        timestamps = [datetime.now() + timedelta(minutes=i*5) for i in range(n)]

        self.test_data = pd.DataFrame({
            "times": timestamps,
            "COD": 50 + 10 * np.random.randn(n),
            "pH": 7.0 + 0.3 * np.random.randn(n),
            "NH3-N": 5 + 1 * np.random.randn(n)
        })

        # 模拟异常
        self.anomalies = [
            {"indicator": "COD", "pattern": "constant", "score": 0.9, "index": 25},
            {"indicator": "pH", "pattern": "constant", "score": 0.85, "index": 50}
        ]

    def test_matcher_initialization(self):
        """测试匹配器初始化"""
        self.assertEqual(self.matcher.name, "法规规则匹配器")
        self.assertEqual(self.matcher.version, "2.0.0")
        self.assertGreater(len(self.matcher.regulations), 0)

    def test_regulation_loading(self):
        """测试法规加载"""
        summary = self.matcher.get_regulation_summary()
        self.assertIn("total_regulations", summary)
        self.assertGreater(summary["total_regulations"], 0)

    def test_match_with_anomalies(self):
        """测试异常匹配"""
        results = self.matcher.match(self.anomalies, self.test_data)

        self.assertIn("matches", results)
        self.assertIn("violations", results)
        self.assertIn("compliance_status", results)

    def test_constant_pattern_violation(self):
        """测试恒定模式违规判定"""
        # 恒定模式应被识别为数据造假
        results = self.matcher.match(self.anomalies, self.test_data)

        # 应该有违规记录
        data_forgery_violations = [
            v for v in results["violations"]
            if v.get("violation_type") == "data_forgery"
        ]
        self.assertGreater(len(data_forgery_violations), 0)

    def test_compliance_status(self):
        """测试合规状态判定"""
        # 无异常时应合规
        results = self.matcher.match([], self.test_data)
        self.assertEqual(results["compliance_status"], "compliant")

        # 有异常时应不合规
        results = self.matcher.match(self.anomalies, self.test_data)
        self.assertEqual(results["compliance_status"], "non_compliant")


class TestProcessValidator(unittest.TestCase):
    """测试工艺机理校验模块"""

    def setUp(self):
        """创建测试数据"""
        self.validator = ProcessValidator()

        # 创建测试数据
        np.random.seed(42)
        n = 100

        timestamps = [datetime.now() + timedelta(minutes=i) for i in range(n)]

        self.test_data = pd.DataFrame({
            "times": timestamps,
            "COD": 50 + 10 * np.random.randn(n),
            "pH": 7.0 + 0.3 * np.random.randn(n),
            "NH3-N": 5 + 1 * np.random.randn(n),
            "TN": 15 + 2 * np.random.randn(n)
        })

        # 模拟异常
        self.anomalies = [
            {"indicator": "COD", "pattern": "constant", "score": 0.9},
            {"indicator": "pH", "pattern": "constant", "score": 0.85}
        ]

        # 模拟相关性结果
        self.correlation_results = {
            "pairs": [
                {"indicator1": "pH", "indicator2": "COD", "pearson": 0.3},
                {"indicator1": "NH3-N", "indicator2": "TN", "pearson": 0.7}
            ]
        }

        self.trend_results = {}

    def test_validator_initialization(self):
        """测试校验器初始化"""
        self.assertEqual(self.validator.name, "工艺机理校验器")
        self.assertEqual(self.validator.version, "2.1.0")
        self.assertIn("nitrogen_conversion_params", self.validator.__dict__)

    def test_process_knowledge_loading(self):
        """测试工艺知识加载"""
        summary = self.validator.get_mechanism_summary()
        self.assertIn("total_rules", summary)
        self.assertIn("rule_categories", summary)

    def test_validate_with_anomalies(self):
        """测试异常校验"""
        results = self.validator.validate(
            self.anomalies, self.correlation_results, self.trend_results, self.test_data
        )

        self.assertIn("violations", results)
        self.assertIn("warnings", results)
        self.assertIn("violations_count", results)
        self.assertIn("mechanism_compliance", results)

    def test_nitrogen_conversion_validation(self):
        """测试氨氮-总氮转化规则（专利要求）"""
        # 创建氨氮>总氮的异常数据
        data = pd.DataFrame({
            "NH3-N": [10, 12, 15, 18, 20],
            "TN": [8, 10, 12, 14, 16]  # 氨氮大于总氮
        })

        results = self.validator.validate(
            self.anomalies, self.correlation_results, self.trend_results, data
        )

        # 应该检测到氨氮浓度超过总氮的违规
        nitrogen_violations = [
            v for v in results["violations"]
            if v.get("type") == "nitrogen_conversion_violation"
        ]
        self.assertGreater(len(nitrogen_violations), 0)

    def test_patent_params(self):
        """测试专利参数"""
        # 氨氮-总氮最小相关系数应为0.3
        self.assertEqual(
            self.validator.nitrogen_conversion_params["min_correlation"], 0.3
        )

        # 氨氮-总氮比值范围
        self.assertEqual(
            self.validator.nitrogen_conversion_params["nh3_tn_ratio_min"], 0.2
        )
        self.assertEqual(
            self.validator.nitrogen_conversion_params["nh3_tn_ratio_max"], 0.6
        )


class TestExpertReasoner(unittest.TestCase):
    """测试专家经验推理模块"""

    def setUp(self):
        """创建测试数据"""
        self.reasoner = ExpertReasoner()

        # 模拟异常
        self.anomalies = [
            {"indicator": "COD", "pattern": "constant", "score": 0.9, "severity": "high"},
            {"indicator": "pH", "pattern": "constant", "score": 0.85, "severity": "high"}
        ]

        # 模拟法规匹配结果
        self.regulation_matches = {
            "violations": [
                {"regulation": "水污染防治法", "article": "第二十三条"}
            ],
            "matches": [],
            "compliance_status": "non_compliant"
        }

        # 模拟工艺校验结果
        self.process_validation = {
            "violations": [
                {"type": "correlation_violation", "severity": "high"}
            ],
            "violations_count": 1,
            "mechanism_compliance": "non_compliant"
        }

    def test_reasoner_initialization(self):
        """测试推理器初始化"""
        self.assertEqual(self.reasoner.name, "专家经验推理器")
        self.assertEqual(self.reasoner.version, "2.0.0")
        self.assertIn("expert_rules", self.reasoner.__dict__)
        self.assertIn("case_library", self.reasoner.__dict__)

    def test_expert_rules_loading(self):
        """测试专家规则加载"""
        self.assertIn("forgery_patterns", self.reasoner.expert_rules)
        self.assertIn("violation_combinations", self.reasoner.expert_rules)

        # 检查违规模式
        patterns = self.reasoner.expert_rules["forgery_patterns"]
        self.assertIn("bottle_interference", patterns)
        self.assertIn("data_dilution", patterns)

    def test_case_library_loading(self):
        """测试案例库加载"""
        self.assertGreater(len(self.reasoner.case_library), 0)

        # 检查案例结构
        for case in self.reasoner.case_library:
            self.assertIn("case_id", case)
            self.assertIn("name", case)
            self.assertIn("features", case)

    def test_reason_with_anomalies(self):
        """测试异常推理"""
        results = self.reasoner.reason(
            self.anomalies, self.regulation_matches, self.process_validation
        )

        self.assertIn("matched_patterns", results)
        self.assertIn("suspicion_level", results)
        self.assertIn("confidence", results)
        self.assertIn("reasoning_path", results)
        self.assertIn("matched_cases", results)

    def test_suspicion_level_determination(self):
        """测试嫌疑等级判定"""
        results = self.reasoner.reason(
            self.anomalies, self.regulation_matches, self.process_validation
        )

        # 嫌疑等级应为有效值
        self.assertIn(results["suspicion_level"], ["low", "medium", "high", "critical"])

    def test_pattern_matching(self):
        """测试模式匹配"""
        results = self.reasoner.reason(
            self.anomalies, self.regulation_matches, self.process_validation
        )

        # 多指标恒定应匹配插瓶干扰模式
        matched = results["matched_patterns"]
        self.assertGreater(len(matched), 0)

    def test_case_matching(self):
        """测试案例匹配"""
        results = self.reasoner.reason(
            self.anomalies, self.regulation_matches, self.process_validation
        )

        # 应该有匹配的案例
        matched_cases = results["matched_cases"]
        # 匹配可能为空（取决于特征），但不应报错
        self.assertIsInstance(matched_cases, list)


class TestViolationGenerator(unittest.TestCase):
    """测试违规结论生成模块"""

    def setUp(self):
        """创建测试数据"""
        self.generator = ViolationGenerator()

        # 模拟异常
        self.anomalies = [
            {"indicator": "COD", "pattern": "constant", "score": 0.9, "severity": "high"},
            {"indicator": "pH", "pattern": "constant", "score": 0.85, "severity": "high"}
        ]

        # 模拟各模块结果
        self.regulation_matches = {
            "violations": [
                {"regulation": "水污染防治法", "article": "第二十三条"}
            ]
        }

        self.process_validation = {
            "violations": [
                {"type": "correlation_violation", "description": "pH与COD相关性过低"}
            ],
            "violations_count": 1
        }

        self.expert_reasoning = {
            "matched_patterns": [
                {"name": "插瓶干扰", "suspicion_level": "high"}
            ],
            "suspicion_level": "high",
            "confidence": 0.85
        }

    def test_generator_initialization(self):
        """测试生成器初始化"""
        self.assertEqual(self.generator.name, "违规结论生成器")
        self.assertEqual(self.generator.version, "2.0.0")

    def test_generate_violation_conclusion(self):
        """测试违规结论生成"""
        result = self.generator.generate(
            self.anomalies,
            self.regulation_matches,
            self.process_validation,
            self.expert_reasoning
        )

        self.assertIn("conclusion_type", result)
        self.assertIn("suspicion_level", result)
        self.assertIn("judgment", result)
        self.assertIn("evidence_points", result)
        self.assertIn("penalty_suggestion", result)
        self.assertIn("summary", result)
        self.assertIn("report", result)

    def test_conclusion_type_determination(self):
        """测试结论类型判定"""
        # 有违规的情况
        result = self.generator.generate(
            self.anomalies,
            self.regulation_matches,
            self.process_validation,
            self.expert_reasoning
        )
        self.assertIn(result["conclusion_type"],
                     ["violation_detected", "suspicion_detected", "normal"])

    def test_evidence_points_generation(self):
        """测试取证要点生成"""
        result = self.generator.generate(
            self.anomalies,
            self.regulation_matches,
            self.process_validation,
            self.expert_reasoning
        )

        evidence = result["evidence_points"]
        self.assertIsInstance(evidence, list)
        self.assertGreater(len(evidence), 0)

    def test_penalty_suggestion(self):
        """测试处罚建议生成"""
        result = self.generator.generate(
            self.anomalies,
            self.regulation_matches,
            self.process_validation,
            self.expert_reasoning
        )

        penalty = result["penalty_suggestion"]
        self.assertIsInstance(penalty, str)
        self.assertGreater(len(penalty), 0)

    def test_full_report_generation(self):
        """测试完整报告生成"""
        result = self.generator.generate(
            self.anomalies,
            self.regulation_matches,
            self.process_validation,
            self.expert_reasoning
        )

        report = result["report"]
        self.assertIn("废水虚假排放监测报告", report)
        self.assertIn("判定结果", report)
        self.assertIn("取证要点", report)


class TestCompleteWorkflow(unittest.TestCase):
    """测试完整工作流"""

    def setUp(self):
        """创建测试数据"""
        np.random.seed(42)
        n = 100

        timestamps = [datetime.now() + timedelta(minutes=i*5) for i in range(n)]

        self.test_data = pd.DataFrame({
            "times": timestamps,
            "COD": [45] * n,  # COD恒定
            "pH": [7.5] * n,   # pH恒定
            "NH3-N": 5 + 1 * np.random.randn(n),
            "TN": 15 + 2 * np.random.randn(n)
        })

        # 异常
        self.anomalies = [
            {"indicator": "COD", "pattern": "constant", "score": 0.95, "index": i}
            for i in range(n)
        ]
        self.anomalies.extend([
            {"indicator": "pH", "pattern": "constant", "score": 0.9, "index": i}
            for i in range(n)
        ])

        self.correlation_results = {
            "pairs": [
                {"indicator1": "pH", "indicator2": "COD", "pearson": -0.8}
            ]
        }

        self.trend_results = {}

    def test_run_rule_reasoning(self):
        """测试完整规则推理流程"""
        task = {
            "task_id": "test_001",
            "data": self.test_data,
            "anomalies": self.anomalies[:10],  # 取部分异常
            "correlation_results": self.correlation_results,
            "trend_results": self.trend_results,
            "config": {}
        }

        result = run_rule_reasoning(task)

        # 检查结果格式
        self.assertEqual(result["task_id"], "test_001")
        self.assertEqual(result["agent"], "rule-reasoning-agent")
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)

        # 检查子结果
        sub_result = result["result"]
        self.assertIn("regulation_check", sub_result)
        self.assertIn("process_validation", sub_result)
        self.assertIn("expert_reasoning", sub_result)
        self.assertIn("violation_conclusion", sub_result)


class TestPatentCompliance(unittest.TestCase):
    """专利符合性测试"""

    def test_regulation_matcher_patent_compliance(self):
        """测试法规规则匹配模块专利符合性"""
        matcher = RegulationMatcher()

        # 应支持《水污染防治法》和HJ 915-2017
        self.assertIn("prevention_law", matcher.regulations)
        self.assertIn("discharge_standard", matcher.regulations)

    def test_process_validator_patent_compliance(self):
        """测试工艺机理校验模块专利符合性"""
        validator = ProcessValidator()

        # 应包含氨氮-总氮转化规则
        self.assertIn("nitrogen_conversion_rules", validator.process_knowledge)

        # 相关系数阈值应为0.3
        self.assertEqual(
            validator.nitrogen_conversion_params["min_correlation"], 0.3
        )

    def test_expert_reasoner_patent_compliance(self):
        """测试专家经验推理模块专利符合性"""
        reasoner = ExpertReasoner()

        # 应有案例库
        self.assertGreater(len(reasoner.case_library), 0)

        # 应支持典型违规模式识别
        patterns = reasoner.expert_rules["forgery_patterns"]
        self.assertIn("bottle_interference", patterns)  # 插瓶干扰
        self.assertIn("data_dilution", patterns)        # 稀释排放

    def test_suspicion_level_rules(self):
        """测试嫌疑等级判定规则（专利要求）"""
        # 高风险：模式数≥2且机理违背
        # 中风险：模式数=1且机理违背
        # 低风险：仅模式匹配无机理违背

        # 这里只验证规则存在，具体逻辑在运行时测试中验证
        generator = ViolationGenerator()

        # 检查判定方法存在
        self.assertTrue(hasattr(generator, "_determine_conclusion_type"))
        self.assertTrue(hasattr(generator, "_determine_suspicion_level"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
