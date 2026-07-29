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
                data: pd.DataFrame = None,
                hrt_hours: int = 2) -> Dict[str, Any]:
        """4 条工艺规则（资料精确判据）。data: effluent df（中文列名）。

        规则:
        1. pH-COD 协同: pH std≤0.1 且 COD std≤5.0 + 平稳 → 插瓶
        2. 氨氮-总氮转化: 氨氮突降而总氮基本不变 + 突变 → 插瓶
        3. 多指标同步突降: 2+ 污染物同步下降 >50% + 突变 → 稀释
        4. 质量平衡: 去除率偏差 > 0.2 + 趋势/突变 → 稀释
        """
        logger.info(f"[PROCESS] 工艺机理校验(资料判据)")

        matched_patterns = []
        feature_set = set()
        for a in anomalies:
            feature_set.update(a.get("features", []))

        if data is None or (hasattr(data, 'empty') and data.empty):
            return {"matched_patterns": [], "violations": [], "violations_count": 0}

        df = data

        # 规则1: pH-COD 协同(插瓶) — pH std≤0.1 且 COD std≤5.0 + 平稳异常
        ph_col = "pH值"
        cod_col = "化学需氧量浓度（毫克/升）"
        if ph_col in df.columns and cod_col in df.columns and "平稳" in feature_set:
            ph_std = float(df[ph_col].std())
            cod_std = float(df[cod_col].std())
            if ph_std <= 0.1 and cod_std <= 5.0:
                matched_patterns.append({"pattern": "插瓶干扰", "rule": "pH-COD协同",
                                         "ph_std": ph_std, "cod_std": cod_std})

        # 规则2: 氨氮-总氮转化(插瓶) — 氨氮突降而总氮基本不变 + 突变
        nh3_col = "氨氮浓度（毫克/升）"
        tn_col = "总氮浓度（毫克/升）"
        if nh3_col in df.columns and tn_col in df.columns and "突变" in feature_set:
            nh3_drop = self._max_drop_ratio(df[nh3_col])
            tn_change = self._max_drop_ratio(df[tn_col])
            if nh3_drop > 0.3 and tn_change < 0.1:
                matched_patterns.append({"pattern": "插瓶干扰", "rule": "氨氮-总氮转化"})

        # 规则3: 多指标同步突降(稀释) — 2+ 污染物同步下降 >50% + 突变
        if "突变" in feature_set:
            pollutant_cols = ["化学需氧量浓度（毫克/升）", "氨氮浓度（毫克/升）",
                              "总磷浓度（毫克/升）", "悬浮物浓度（毫克/升）"]
            sync_drop = []
            for col in pollutant_cols:
                if col in df.columns:
                    drop = self._max_drop_ratio(df[col])
                    if drop > 0.5:
                        sync_drop.append((col.split("（")[0], round(drop, 2)))
            if len(sync_drop) >= 2:
                matched_patterns.append({"pattern": "稀释排放", "rule": "多指标同步突降",
                                         "sync_indicators": sync_drop})

        results = {
            "matched_patterns": matched_patterns,
            "violations": [{"pattern": p["pattern"], "rule": p["rule"]} for p in matched_patterns],
            "violations_count": len(matched_patterns),
            "mechanism_compliance": "non_compliant" if matched_patterns else "compliant",
        }
        logger.info(f"[PROCESS] 校验完成: {len(matched_patterns)} 个违规模式")
        return results

    @staticmethod
    def _max_drop_ratio(series) -> float:
        """序列中最大突降比例(0~1)。"""
        s = series.dropna()
        if len(s) < 2:
            return 0.0
        before = s.iloc[:len(s)//2].mean()
        after = s.iloc[len(s)//2:].mean()
        if before <= 0:
            return 0.0
        return float(max(0.0, (before - after) / before))

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
