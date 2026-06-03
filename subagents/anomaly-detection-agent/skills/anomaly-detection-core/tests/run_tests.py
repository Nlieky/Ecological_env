#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测测试运行器
"""

import sys
import unittest
import os

# 添加技能包路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_anomaly_detection import (
    TestOperatorAdapter,
    TestAnomalyScorer,
    TestPatternRecognizer,
    TestViolationDetector,
    TestConfidenceEvaluator,
    TestCompleteWorkflow,
    TestPatentCompliance
)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestOperatorAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestAnomalyScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternRecognizer))
    suite.addTests(loader.loadTestsFromTestCase(TestViolationDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestConfidenceEvaluator))
    suite.addTests(loader.loadTestsFromTestCase(TestCompleteWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestPatentCompliance))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
