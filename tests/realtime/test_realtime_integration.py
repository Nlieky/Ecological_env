#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时分析集成测试

测试场景：
1. 正常数据 - 无告警
2. 恒定值异常（插瓶干扰）- 检测到
3. 法规超标（COD超标）- 检测到
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from realtime_analyzer import create_realtime_analyzer, VIOLATION_PATTERNS, REGULATORY_LIMITS


def test_normal_data():
    """测试正常数据"""
    print("=" * 60)
    print("测试1: 正常数据")
    print("=" * 60)

    analyzer = create_realtime_analyzer(window_size=10)

    # 发送10条有自然波动的正常数据（避免触发恒定值和造假检测）
    import random
    random.seed(42)

    for i in range(10):
        # 添加更大的自然波动（标准差约1-2，使CV>0.05）
        noise_ph = random.uniform(-0.5, 0.5)
        noise_cod = random.uniform(-8, 8)
        noise_tn = random.uniform(-2, 2)
        noise_an = random.uniform(-1, 1)
        noise_tp = random.uniform(-0.15, 0.15)

        # 基础值也加入趋势变化
        trend = i * 0.5

        influent = {
            "pH值": 7.0 + noise_ph + trend * 0.05,
            "化学需氧量浓度（毫克/升）": 100 + noise_cod + trend,
            "总氮浓度（毫克/升）": 15 + noise_tn + trend * 0.3,
            "氨氮浓度（毫克/升）": 5 + noise_an + trend * 0.1,
            "总磷浓度（毫克/升）": 2 + noise_tp + trend * 0.02
        }
        effluent = {
            "pH值": 7.5 + noise_ph + trend * 0.05,  # pH 6-9 OK
            "化学需氧量浓度（毫克/升）": 35 + noise_cod * 0.5 + trend * 0.3,  # <=50 OK
            "总氮浓度（毫克/升）": 8 + noise_tn * 0.5 + trend * 0.1,  # <=15 OK
            "氨氮浓度（毫克/升）": 2 + noise_an * 0.5 + trend * 0.05,  # <=5 OK
            "总磷浓度（毫克/升）": 0.3 + noise_tp * 0.5 + trend * 0.01  # <=0.5 OK
        }

        result = analyzer.process_new_data(influent, effluent)

    stats = analyzer.get_statistics()

    print(f"窗口大小: {stats['window_size']}")
    print(f"告警计数: {stats['alert_counts']}")
    print(f"是否检测到异常: {result.has_anomaly}")
    print(f"是否检测到违规: {result.has_violation}")

    if result.has_violation:
        print(f"  违规: {[v.pattern_name for v in result.violations]}")
    else:
        print("  结果: 正常数据，未检测到违规")

    # 只检查是否有违规类型的告警（不包括法规超标，因为数据本身可能在正常范围内）
    violation_types = [v.pattern_type for v in result.violations]
    has_fraud_alert = any(vt in ["bottle_interference", "data_fabrication", "dilution_discharge", "bypass_discharge"]
                          for vt in violation_types)

    return not has_fraud_alert


def test_constant_value_anomaly():
    """测试恒定值异常（插瓶干扰）"""
    print("\n" + "=" * 60)
    print("测试2: 恒定值异常（插瓶干扰）")
    print("=" * 60)

    analyzer = create_realtime_analyzer(window_size=15)

    # 发送15条完全恒定的数据（插瓶干扰特征）
    for i in range(15):
        influent = {
            "pH值": 7.2,
            "化学需氧量浓度（毫克/升）": 45.0,
            "总氮浓度（毫克/升）": 10.0,
            "氨氮浓度（毫克/升）": 3.0,
            "总磷浓度（毫克/升）": 0.5
        }
        effluent = {
            "pH值": 7.5,
            "化学需氧量浓度（毫克/升）": 45.0,
            "总氮浓度（毫克/升）": 8.0,
            "氨氮浓度（毫克/升）": 2.0,
            "总磷浓度（毫克/升）": 0.4
        }

        result = analyzer.process_new_data(influent, effluent)

    # 检查窗口统计
    stats = analyzer.get_statistics()
    print(f"窗口大小: {len(analyzer.window)}")
    print(f"统计信息:")
    for name, stat in stats.get('statistics', {}).items():
        print(f"  {name}: mean={stat['mean']:.2f}, std={stat['std']:.4f}")

    print(f"\n是否检测到异常: {result.has_anomaly}")
    print(f"是否检测到违规: {result.has_violation}")

    if result.has_anomaly:
        for a in result.anomalies:
            print(f"  [异常] {a.indicator}: {a.message}")

    if result.has_violation:
        for v in result.violations:
            print(f"\n  [违规] {v.pattern_name} (级别: {v.level})")
            print(f"         疑似度: {v.suspicion:.2f}")
            print(f"         证据: {v.evidence}")

    # 检查是否检测到插瓶干扰或数据造假
    violation_types = [v.pattern_type for v in result.violations]
    detected = "bottle_interference" in violation_types or "data_fabrication" in violation_types

    print(f"\n结果: {'检测到插瓶干扰' if detected else '未检测到'}")
    return detected


def test_regulatory_exceedance():
    """测试法规超标"""
    print("\n" + "=" * 60)
    print("测试3: 法规超标（COD>50mg/L）")
    print("=" * 60)

    analyzer = create_realtime_analyzer(window_size=5)

    # 先发送几条正常数据建立基线
    for i in range(5):
        influent = {"化学需氧量浓度（毫克/升）": 100.0}
        effluent = {"化学需氧量浓度（毫克/升）": 45.0}
        analyzer.process_new_data(influent, effluent)

    # 发送超标数据
    influent = {"化学需氧量浓度（毫克/升）": 100.0}
    effluent = {"化学需氧量浓度（毫克/升）": 75.0}  # 超过50mg/L限值

    result = analyzer.process_new_data(influent, effluent)

    print(f"是否检测到异常: {result.has_anomaly}")
    print(f"是否检测到违规: {result.has_violation}")

    if result.has_anomaly:
        for a in result.anomalies:
            print(f"\n  [异常] {a.indicator}: {a.message}")

    if result.has_violation:
        for v in result.violations:
            print(f"\n  [违规] {v.pattern_name} (级别: {v.level})")
            print(f"         证据: {v.evidence}")

    # 检查是否检测到法规超标
    violation_types = [v.pattern_type for v in result.violations]
    detected = "regulatory_exceedance" in violation_types

    print(f"\n结果: {'检测到法规超标' if detected else '未检测到'}")
    return detected


def test_ph_regulatory_exceedance():
    """测试pH法规超标"""
    print("\n" + "=" * 60)
    print("测试4: pH法规超标（pH<6或>9）")
    print("=" * 60)

    analyzer = create_realtime_analyzer(window_size=5)

    # 发送pH过低的数据
    influent = {"pH值": 5.5, "化学需氧量浓度（毫克/升）": 100.0}
    effluent = {"pH值": 5.2, "化学需氧量浓度（毫克/升）": 45.0}  # pH<6

    result = analyzer.process_new_data(influent, effluent)

    print(f"是否检测到异常: {result.has_anomaly}")
    print(f"是否检测到违规: {result.has_violation}")

    if result.has_anomaly:
        for a in result.anomalies:
            print(f"  [异常] {a.indicator}: {a.message}")

    # 发送pH过高的数据
    influent = {"pH值": 7.0}
    effluent = {"pH值": 9.5}  # pH>9

    result = analyzer.process_new_data(influent, effluent)

    if result.has_anomaly:
        for a in result.anomalies:
            print(f"  [异常] {a.indicator}: {a.message}")

    return result.has_anomaly


def print_regulatory_limits():
    """打印法规限值"""
    print("\n" + "=" * 60)
    print("法规限值参考")
    print("=" * 60)
    for indicator, limits in REGULATORY_LIMITS.items():
        if 'min' in limits and 'max' in limits:
            print(f"  {indicator}: {limits['min']} - {limits['max']} {limits.get('unit', '')}")
        elif 'max' in limits:
            print(f"  {indicator}: <= {limits['max']} {limits.get('unit', '')}")


def print_violation_patterns():
    """打印违规模式"""
    print("\n" + "=" * 60)
    print("违规模式定义")
    print("=" * 60)
    for pattern_type, pattern_info in VIOLATION_PATTERNS.items():
        print(f"  {pattern_type}: {pattern_info['name']}")
        print(f"    描述: {pattern_info['description']}")
        print(f"    特征: {', '.join(pattern_info['indicators'])}")


if __name__ == "__main__":
    print("\n实时分析引擎集成测试")
    print("=" * 60)

    print_regulatory_limits()
    print_violation_patterns()

    results = []

    results.append(("正常数据", test_normal_data()))
    results.append(("恒定值异常", test_constant_value_anomaly()))
    results.append(("法规超标(COD)", test_regulatory_exceedance()))
    results.append(("法规超标(pH)", test_ph_regulatory_exceedance()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n所有测试通过！")
        sys.exit(0)
    else:
        print(f"\n有 {total - passed} 个测试失败")
        sys.exit(1)
