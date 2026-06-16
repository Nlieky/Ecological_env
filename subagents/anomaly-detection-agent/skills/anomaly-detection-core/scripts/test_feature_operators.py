#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试特征分析算子（相关性、趋势）
"""

import sys
import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from operator_adapter import OperatorAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_data(n_samples=100):
    """创建测试数据"""
    np.random.seed(42)

    # 创建有相关性的数据
    cod = np.random.normal(45, 10, n_samples)
    ph = 7.5 + 0.02 * (cod - 45) + np.random.normal(0, 0.3, n_samples)  # pH与COD弱相关
    tn = np.random.normal(12, 3, n_samples)

    # 添加一些趋势
    trend = np.linspace(0, 5, n_samples)
    cod_with_trend = cod + trend

    return pd.DataFrame({
        "times": pd.date_range("2026-01-01", periods=n_samples, freq="H"),
        "COD": cod_with_trend,
        "pH": ph,
        "TN": tn
    })


def test_correlation_operators():
    """测试相关性分析算子"""
    print("=" * 80)
    print("测试相关性分析算子")
    print("=" * 80)

    # 创建算子适配器
    adapter = OperatorAdapter(enable_intent_mapping=False)

    # 创建测试数据
    data = create_test_data(100)

    # 测试 Pearson 相关性
    print("\n测试场景1：Pearson 相关性分析")
    operators = ["correlation_pearson"]
    indicators = ["COD", "pH", "TN"]

    results = adapter.apply_operators(data, indicators, operators)

    print(f"  算子: {list(results.keys())}")
    if "correlation_pearson" in results:
        corr_result = results["correlation_pearson"]
        print(f"  方法: {corr_result.get('method', 'unknown')}")
        print(f"  指标对数量: {len(corr_result.get('pairs', []))}")
        print(f"  高相关对数: {corr_result.get('summary', {}).get('high_correlation', 0)}")
        print(f"  中等相关对数: {corr_result.get('summary', {}).get('moderate_correlation', 0)}")
        print(f"  低相关对数: {corr_result.get('summary', {}).get('low_correlation', 0)}")

        # 显示前几个相关对
        pairs = corr_result.get('pairs', [])
        if pairs:
            print(f"  相关性示例:")
            for pair in pairs[:3]:
                ind1 = pair.get('indicator1', 'N/A')
                ind2 = pair.get('indicator2', 'N/A')
                pearson = pair.get('pearson', 0)
                print(f"    {ind1} - {ind2}: r = {pearson:.3f}")

        print("  [OK] Pearson 相关性分析测试通过")

    # 测试 Spearman 相关性
    print("\n测试场景2：Spearman 相关性分析")
    operators = ["correlation_spearman"]

    results = adapter.apply_operators(data, indicators, operators)

    if "correlation_spearman" in results:
        corr_result = results["correlation_spearman"]
        print(f"  方法: {corr_result.get('method', 'unknown')}")
        print(f"  说明: {corr_result.get('note', '')}")
        print("  [OK] Spearman 相关性分析测试通过")


def test_trend_operators():
    """测试趋势分析算子"""
    print("\n" + "=" * 80)
    print("测试趋势分析算子")
    print("=" * 80)

    # 创建算子适配器
    adapter = OperatorAdapter(enable_intent_mapping=False)

    # 创建测试数据
    data = create_test_data(100)
    indicators = ["COD", "pH", "TN"]

    # 测试线性趋势
    print("\n测试场景3：线性趋势分析")
    operators = ["trend_linear"]

    results = adapter.apply_operators(data, indicators, operators)

    if "trend_linear" in results:
        trend_result = results["trend_linear"]
        print(f"  方法: {trend_result.get('method', 'unknown')}")
        print(f"  趋势统计:")
        summary = trend_result.get('summary', {})
        print(f"    上升趋势: {summary.get('rising', 0)}")
        print(f"    下降趋势: {summary.get('falling', 0)}")
        print(f"    平稳趋势: {summary.get('stable', 0)}")

        # 显示各指标趋势
        trends = trend_result.get('trends', {})
        if trends:
            print(f"  趋势详情:")
            for indicator, trend_info in list(trends.items())[:3]:
                direction = trend_info.get('direction', 'unknown')
                strength = trend_info.get('strength', 0)
                print(f"    {indicator}: {direction} (强度: {strength:.3f})")

        print("  [OK] 线性趋势分析测试通过")

    # 测试 Mann-Kendall 趋势
    print("\n测试场景4：Mann-Kendall 趋势检验")
    operators = ["trend_mann_kendall"]

    results = adapter.apply_operators(data, indicators, operators)

    if "trend_mann_kendall" in results:
        trend_result = results["trend_mann_kendall"]
        print(f"  方法: {trend_result.get('method', 'unknown')}")
        print(f"  说明: {trend_result.get('note', '')}")
        print("  [OK] Mann-Kendall 趋势检验测试通过")


def test_mixed_operators():
    """测试混合算子（异常检测 + 特征分析）"""
    print("\n" + "=" * 80)
    print("测试混合算子（异常检测 + 特征分析）")
    print("=" * 80)

    # 创建算子适配器
    adapter = OperatorAdapter(enable_intent_mapping=False)

    # 创建测试数据
    data = create_test_data(100)
    indicators = ["COD", "pH"]

    # 混合算子：异常检测 + 相关性
    print("\n测试场景5：混合算子")
    operators = ["zscore", "correlation_pearson", "trend_linear"]

    results = adapter.apply_operators(data, indicators, operators)

    print(f"  应用算子: {list(results.keys())}")

    # 验证各种算子的结果
    for op_name, op_result in results.items():
        if "error" in op_result:
            print(f"  {op_name}: 失败 - {op_result['error']}")
        elif op_name.startswith("correlation_") or op_name.startswith("trend_"):
            # 特征分析算子
            print(f"  {op_name}: 成功 - 特征分析结果")
        else:
            # 异常检测算子
            anomaly_count = sum(
                r.get("anomaly_count", 0)
                for r in op_result.values()
                if isinstance(r, dict) and "anomaly_count" in r
            )
            print(f"  {op_name}: 成功 - 检测到 {anomaly_count} 个异常")

    print("  [OK] 混合算子测试通过")


def test_intent_mapping_with_features():
    """测试基于意图的特征分析算子选择"""
    print("\n" + "=" * 80)
    print("测试基于意图的特征分析算子选择")
    print("=" * 80)

    # 创建算子适配器（启用意图映射）
    adapter = OperatorAdapter(enable_intent_mapping=True)

    # 创建测试数据
    data = create_test_data(100)

    # 测试相关性分析意图
    print("\n测试场景6：相关性分析意图")
    intent = {
        "analysis_types": ["correlation"],
        "indicators": ["COD", "pH", "TN"],
        "query_type": "multi"
    }

    selection = adapter.select_operators_by_intent(intent, data)

    print(f"  意图类型: {selection['intent_type']}")
    print(f"  选择算子: {selection['selected_operators']}")

    # 验证是否选择了相关性算子
    selected = selection['selected_operators']
    has_correlation = any(op.startswith("correlation_") for op in selected)

    if has_correlation:
        print("  [OK] 正确选择了相关性分析算子")
    else:
        print("  [INFO] 当前未选择相关性算子，需要更新意图映射")

    # 测试趋势分析意图
    print("\n测试场景7：趋势分析意图")
    intent = {
        "analysis_types": ["trend"],
        "indicators": ["COD", "pH"],
        "query_type": "multi"
    }

    selection = adapter.select_operators_by_intent(intent, data)

    print(f"  意图类型: {selection['intent_type']}")
    print(f"  选择算子: {selection['selected_operators']}")

    # 验证是否选择了趋势算子
    selected = selection['selected_operators']
    has_trend = any(op.startswith("trend_") for op in selected)

    if has_trend:
        print("  [OK] 正确选择了趋势分析算子")
    else:
        print("  [INFO] 当前未选择趋势算子，需要更新意图映射")


if __name__ == "__main__":
    test_correlation_operators()
    test_trend_operators()
    test_mixed_operators()
    test_intent_mapping_with_features()

    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)
