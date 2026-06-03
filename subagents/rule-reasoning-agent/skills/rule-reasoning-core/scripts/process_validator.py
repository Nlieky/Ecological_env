#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工艺机理校验模块
功能：调用工艺知识库进行物理化学合理性判断

基于专利文档：工艺机理校验模块
"""

import logging
from typing import Dict, Any, List
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessValidator:
    """
    工艺机理校验器（专利增强版）

    校验的机理规则：
    1. 生化反应联动规则（污染物降解与pH、DO的关系）
    2. 物料平衡规则（进水、出水、污泥之间的关系）
    3. 相关性规则（指标间的协同关系）
    4. 氨氮-总氮转化规则（专利新增）
    """

    def __init__(self):
        """初始化工艺机理校验器"""
        self.name = "工艺机理校验器"
        self.version = "2.1.0"  # 专利增强版

        # 工艺知识库
        self.process_knowledge = self._load_process_knowledge()

        # 专利参数：氨氮-总氮转化规则
        self.nitrogen_conversion_params = {
            "min_correlation": 0.3,       # 氨氮-总氮最小相关系数
            "nh3_tn_ratio_min": 0.2,      # 出水氨氮/总氮比值下限
            "nh3_tn_ratio_max": 0.6,      # 出水氨氮/总氮比值上限
            "nh3_removal_min": 0.7,       # 氨氮最小去除率（70%）
            "nh3_removal_max": 0.95,      # 氨氮最大去除率（95%）
            "tn_removal_min": 0.6,        # 总氮最小去除率（60%）
            "tn_removal_max": 0.85        # 总氮最大去除率（85%）
        }

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 支持氨氮-总氮转化规则校验")

    def _load_process_knowledge(self) -> Dict[str, Any]:
        """加载工艺知识库"""
        return {
            "biochemical_rules": {
                "ph_cod_relation": {
                    "rule": "COD降解过程会产生有机酸，导致pH下降",
                    "expected": "COD下降时，pH应同步下降或保持稳定",
                    "violation": "COD下降但pH上升，违背生化机理"
                },
                "do_nitrogen_relation": {
                    "rule": "硝化反应需要消耗溶解氧，反硝化释放氮气",
                    "expected": "硝化过程中DO应保持较高水平",
                    "violation": "硝化反应活跃但DO偏低，违背机理"
                },
                "removal_efficiency": {
                    "rule": "污染物去除率应在合理范围内",
                    "expected": "COD去除率40-90%，TN去除率30-80%",
                    "violation": "去除率超出合理范围，违背工艺机理"
                }
            },
            "mass_balance_rules": {
                "influent_effluent": {
                    "rule": "出水污染物浓度应低于进水",
                    "violation": "出水浓度高于进水，系统异常"
                },
                "removal_rate": {
                    "rule": "去除率应为正值",
                    "violation": "负去除率表示系统增富集，异常"
                }
            },
            "correlation_rules": {
                "ph_cod_correlation": {
                    "rule": "pH与COD应保持正相关或稳定关系",
                    "min_correlation": 0.3,
                    "violation": "相关性过低，数据可能造假"
                }
            },
            "nitrogen_conversion_rules": {
                "nh3_tn_correlation": {
                    "rule": "氨氮是总氮的组成部分，两者应正相关",
                    "expected": "氨氮与总氮相关系数≥0.3",
                    "violation": "相关性过低，违背氮转化机理"
                },
                "nh3_tn_ratio": {
                    "rule": "出水氨氮/总氮比值应在合理范围",
                    "expected": "比值20%-40%（硝化反硝化后）",
                    "violation": "比值异常，违背氮转化规律"
                },
                "nh3_concentration_limit": {
                    "rule": "氨氮浓度不应超过总氮",
                    "expected": "氨氮 <= 总氮",
                    "violation": "氨氮大于总氮，数据错误或造假"
                },
                "removal_efficiency": {
                    "rule": "氮去除率应在合理范围",
                    "expected": "氨氮去除率70-95%，总氮去除率60-85%",
                    "violation": "去除率异常，违背工艺能力"
                }
            }
        }

    def validate(self, anomalies: List[Dict[str, Any]],
                correlation_results: Dict[str, Any],
                trend_results: Dict[str, Any],
                data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        进行工艺机理校验（专利增强版）

        Args:
            anomalies: 异常列表
            correlation_results: 相关性结果
            trend_results: 趋势结果
            data: 原始监测数据（用于氮转化规则校验）

        Returns:
            校验结果
        """
        logger.info(f"[PROCESS] 工艺机理校验")

        results = {
            "violations": [],
            "warnings": [],
            "violations_count": 0,
            "mechanism_compliance": "unknown"
        }

        # 1. 校验生化反应规则
        bio_violations = self._validate_biochemical_rules(
            correlation_results, trend_results
        )
        results["violations"].extend(bio_violations)

        # 2. 校验物料平衡规则
        mass_violations = self._validate_mass_balance_rules(anomalies)
        results["violations"].extend(mass_violations)

        # 3. 校验相关性规则
        corr_violations = self._validate_correlation_rules(correlation_results)
        results["violations"].extend(corr_violations)

        # 4. 检测特定的异常模式
        pattern_violations = self._detect_pattern_violations(anomalies)
        results["violations"].extend(pattern_violations)

        # 5. 校验氨氮-总氮转化规则（专利新增）
        if data is not None:
            nitrogen_violations = self._validate_nitrogen_conversion_rules(
                correlation_results, data
            )
            results["violations"].extend(nitrogen_violations)

        results["violations_count"] = len(results["violations"])

        # 确定机理合规状态
        if results["violations_count"] == 0:
            results["mechanism_compliance"] = "compliant"
        elif results["violations_count"] <= 2:
            results["mechanism_compliance"] = "warning"
        else:
            results["mechanism_compliance"] = "non_compliant"

        logger.info(f"[PROCESS] 校验完成: {results['violations_count']} 处违背")

        return results

    def _validate_biochemical_rules(self, correlation_results: Dict[str, Any],
                                  trend_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """校验生化反应规则"""
        violations = []

        # 检查pH-COD关系
        if "pairs" in correlation_results:
            for pair in correlation_results["pairs"]:
                ind1 = pair.get("indicator1", "")
                ind2 = pair.get("indicator2", "")

                if ("pH" in [ind1, ind2] and "COD" in [ind1, ind2]):
                    correlation = pair.get("pearson", 0)

                    if correlation < -0.5:
                        violations.append({
                            "type": "biochemical_violation",
                            "rule": "ph_cod_relation",
                            "description": "pH与COD负相关，违背生化机理",
                            "severity": "high",
                            "evidence": f"相关系数: {correlation:.3f}"
                        })

        return violations

    def _validate_mass_balance_rules(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """校验物料平衡规则"""
        violations = []

        # 检查恒定值异常（可能的数据造假）
        for anomaly in anomalies:
            if anomaly.get("pattern") == "constant":
                violations.append({
                    "type": "mass_balance_violation",
                    "rule": "constant_value",
                    "description": f"{anomaly.get('indicator', '')}长时间恒定，违背工艺波动规律",
                    "severity": "high",
                    "evidence": "数据人为固定，疑似插瓶干扰"
                })

        return violations

    def _validate_correlation_rules(self, correlation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """校验相关性规则"""
        violations = []

        if "pairs" in correlation_results:
            for pair in correlation_results["pairs"]:
                ind1 = pair.get("indicator1", "")
                ind2 = pair.get("indicator2", "")
                correlation = pair.get("pearson", 0)

                # pH和COD应该有一定的相关性
                if ("pH" in [ind1, ind2] and "COD" in [ind1, ind2]):
                    if abs(correlation) < 0.1:
                        violations.append({
                            "type": "correlation_violation",
                            "rule": "ph_cod_correlation",
                            "description": "pH与COD相关性过低，数据可能造假",
                            "severity": "medium",
                            "evidence": f"相关系数: {correlation:.3f}"
                        })

        return violations

    def _detect_pattern_violations(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测特定的异常模式违规"""
        violations = []

        # 统计各指标的异常模式
        pattern_counts = {}
        for anomaly in anomalies:
            indicator = anomaly.get("indicator", "")
            pattern = anomaly.get("pattern", "")

            key = f"{indicator}_{pattern}"
            pattern_counts[key] = pattern_counts.get(key, 0) + 1

        # 检测高频异常模式
        for key, count in pattern_counts.items():
            if count >= 3:
                parts = key.split("_", 1)
                if len(parts) == 2:
                    indicator, pattern = parts

                    violation_types = {
                        "constant": "恒定值异常",
                        "spike": "突变异常",
                        "trend": "趋势异常"
                    }

                    if pattern in violation_types:
                        violations.append({
                            "type": "pattern_violation",
                            "rule": f"{pattern}_pattern",
                            "description": f"{indicator}出现{count}次{violation_types[pattern]}",
                            "severity": "high",
                            "evidence": f"模式: {pattern}, 频次: {count}"
                        })

        return violations

    def _validate_nitrogen_conversion_rules(self, correlation_results: Dict[str, Any],
                                           data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        校验氨氮-总氮转化规则（专利核心算法）

        工艺机理：
        - NH3-N（氨氮）是TN（总氮）的组成部分
        - 正常情况下：NH3-N <= TN
        - 硝化反应：NH3-N -> NO3-N（氨氮转化为硝态氮）
        - 反硝化反应：NO3-N -> N2（硝态氮转化为氮气）

        校验规则：
        1. 氨氮与总氮应正相关
        2. 氨氮浓度不应超过总氮
        3. 出水氨氮/总氮比值应在合理范围（20-40%）
        4. 氮去除率应在合理范围

        Args:
            correlation_results: 相关性分析结果
            data: 原始监测数据

        Returns:
            违规列表
        """
        violations = []

        # 检查数据中是否有氨氮和总氮指标
        nh3_indicators = ["NH3-N", "氨氮", "AN", "NH3"]
        tn_indicators = ["TN", "总氮"]

        nh3_col = None
        tn_col = None

        for col in data.columns:
            if any(nh3 in col.upper() for nh3 in nh3_indicators):
                nh3_col = col
            if any(tn in col.upper() for tn in tn_indicators):
                tn_col = col

        # 规则1：氨氮与总氮相关性校验
        if "pairs" in correlation_results:
            for pair in correlation_results["pairs"]:
                ind1 = pair.get("indicator1", "")
                ind2 = pair.get("indicator2", "")

                # 检查是否是氨氮-总氮对
                is_nh3_pair = any(nh3 in ind1.upper() or nh3 in ind2.upper() for nh3 in nh3_indicators)
                is_tn_pair = any(tn in ind1.upper() or tn in ind2.upper() for tn in tn_indicators)

                if is_nh3_pair and is_tn_pair:
                    correlation = pair.get("pearson", 0)

                    if correlation < self.nitrogen_conversion_params["min_correlation"]:
                        violations.append({
                            "type": "nitrogen_conversion_violation",
                            "rule": "nh3_tn_correlation",
                            "description": "氨氮与总氮相关性过低，违背氮转化机理",
                            "severity": "high",
                            "evidence": f"相关系数: {correlation:.3f}, 期望: ≥{self.nitrogen_conversion_params['min_correlation']}"
                        })

        # 规则2：氨氮浓度不应超过总氮
        if nh3_col and tn_col:
            try:
                nh3_data = data[nh3_col].dropna()
                tn_data = data[tn_col].dropna()

                if len(nh3_data) > 0 and len(tn_data) > 0:
                    # 检查是否有氨氮大于总氮的情况
                    max_nh3 = nh3_data.max()
                    min_tn = tn_data.min()

                    if max_nh3 > min_tn:
                        # 进一步检查具体数据点
                        violation_count = 0
                        for i in range(min(len(nh3_data), len(tn_data))):
                            if nh3_data.iloc[i] > tn_data.iloc[i]:
                                violation_count += 1

                        if violation_count > len(nh3_data) * 0.1:  # 超过10%的数据点违规
                            violations.append({
                                "type": "nitrogen_conversion_violation",
                                "rule": "nh3_concentration_limit",
                                "description": f"氨氮浓度超过总氮，数据错误或造假",
                                "severity": "critical",
                                "evidence": f"违规点数: {violation_count}/{len(nh3_data)}"
                            })

                    # 规则3：出水氨氮/总氮比值校验
                    if len(nh3_data) >= 10 and len(tn_data) >= 10:
                        # 计算最近10个点的比值
                        recent_nh3 = nh3_data.iloc[-10:].mean()
                        recent_tn = tn_data.iloc[-10:].mean()

                        if recent_tn > 0:
                            ratio = recent_nh3 / recent_tn

                            ratio_min = self.nitrogen_conversion_params["nh3_tn_ratio_min"]
                            ratio_max = self.nitrogen_conversion_params["nh3_tn_ratio_max"]

                            if ratio < ratio_min or ratio > ratio_max:
                                violations.append({
                                    "type": "nitrogen_conversion_violation",
                                    "rule": "nh3_tn_ratio",
                                    "description": f"出水氨氮/总氮比值({ratio:.1%})异常，违背氮转化规律",
                                    "severity": "high",
                                    "evidence": f"比值: {ratio:.1%}, 正常范围: {ratio_min:.0%}-{ratio_max:.0%}"
                                })

            except Exception as e:
                logger.warning(f"[PROCESS] 氨氮-总氮浓度校验失败: {e}")

        return violations

    def get_mechanism_summary(self) -> Dict[str, Any]:
        """获取机理规则摘要"""
        return {
            "total_rules": sum(len(rules) for rules in self.process_knowledge.values()),
            "rule_categories": list(self.process_knowledge.keys())
        }
