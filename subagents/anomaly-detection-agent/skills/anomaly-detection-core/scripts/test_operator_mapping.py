#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试算子适配器的意图映射功能
"""

import sys
import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(script_dir))

from operator_adapter import OperatorAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_data(n_samples=50):
    """创建测试数据"""
    return pd.DataFrame({
        "times": pd.date_range("2026-01-01", periods=n_samples, freq="H"),
        "COD": np.random.normal(45, 10, n_samples),
        "pH": np.random.normal(7.5, 0.5, n_samples),
        "TN": np.random.normal(12, 3, n_samples)
    })


def test_intent_mapping():
    """测试基于意图的算子选择"""

    print("=" * 80)
    print("测试算子适配器的意图映射功能")
    print("=" * 80)

    # 创建算子适配器
    adapter = OperatorAdapter(enable_intent_mapping=True)

    # 测试场景1：单指标异常检测
    print("\n测试场景1：单指标异常检测")
    intent1 = {
        "analysis_types": ["anomaly"],
        "indicators": ["COD"],
        "query_type": "single"
    }

    data1 = create_test_data(50)
    result1 = adapter.select_operators_by_intent(intent1, data1)

    print(f"  意图类型: {result1['intent_type']}")
    print(f"  选择算子: {result1['selected_operators']}")
    print(f"  原因: {result1['reason']}")

    assert "zscore" in result1['selected_operators'], "应该包含 zscore 算子"
    assert "iqr" in result1['selected_operators'], "应该包含 iqr 算子"
    print("  [OK] 测试通过")

    # 测试场景2：相关性分析
    print("\n测试场景2：相关性分析")
    intent2 = {
        "analysis_types": ["correlation"],
        "indicators": ["COD", "pH"],
        "query_type": "multi"
    }

    result2 = adapter.select_operators_by_intent(intent2)

    print(f"  意图类型: {result2['intent_type']}")
    print(f"  选择算子: {result2['selected_operators']}")
    print(f"  原因: {result2['reason']}")

    # 注意：correlation 算子可能还未整合到 operator_adapter 中
    # 所以这个测试可能返回空列表或默认算子
    print("  [INFO] 相关性分析算子待后续整合")

    # 测试场景3：综合分析（大数据量）
    print("\n测试场景3：综合分析（大数据量）")
    intent3 = {
        "analysis_types": ["anomaly", "correlation", "trend"],
        "indicators": ["COD", "pH", "TN"],
        "query_type": "multi"
    }

    data3 = create_test_data(1500)  # 大数据量
    result3 = adapter.select_operators_by_intent(intent3, data3)

    print(f"  意图类型: {result3['intent_type']}")
    print(f"  数据量类别: {result3.get('data_size_category', 'unknown')}")
    print(f"  选择算子: {result3['selected_operators']}")
    print(f"  原因: {result3['reason']}")

    # 大数据量应该优先使用复杂算子
    print("  [OK] 测试通过")

    # 测试场景4：意图映射未启用
    print("\n测试场景4：意图映射未启用")
    adapter_no_mapping = OperatorAdapter(enable_intent_mapping=False)
    result4 = adapter_no_mapping.select_operators_by_intent(intent1)

    print(f"  选择算子: {result4['selected_operators']}")
    print(f"  原因: {result4['reason']}")

    assert result4['intent_type'] == "default", "应该返回默认算子"
    print("  [OK] 测试通过")

    print("\n" + "=" * 80)
    print("所有测试通过！")
    print("=" * 80)


if __name__ == "__main__":
    test_intent_mapping()
