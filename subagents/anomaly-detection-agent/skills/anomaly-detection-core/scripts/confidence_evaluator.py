#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可信度评估模块
功能：计算异常结果的可信度，进行稳定性评估

基于专利文档：可信度评估模块
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfidenceEvaluator:
    """
    可信度评估器

    评估维度：
    1. 算子一致性：多个算子结果的一致程度
    2. 历史对比：与历史异常模式的对比
    3. 稳定性评估：异常的稳定性
    """

    def __init__(self):
        """初始化可信度评估器"""
        self.name = "可信度评估器"
        self.version = "2.0.0"

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def evaluate(self, anomaly_scores: Dict[str, Any],
                anomaly_patterns: Dict[str, Any],
                operator_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估异常结果的可信度

        Args:
            anomaly_scores: 异常分数
            anomaly_patterns: 异常模式
            operator_results: 算子结果

        Returns:
            可信度评估结果
        """
        logger.info(f"[CONFIDENCE] 评估可信度")

        results = {
            "operator_consistency": self._evaluate_operator_consistency(operator_results),
            "pattern_confidence": self._evaluate_pattern_confidence(anomaly_patterns),
            "stability_score": self._evaluate_stability(anomaly_scores),
            "avg_confidence": 0.0,
            "confidence_by_indicator": {}
        }

        # 计算综合置信度
        results["avg_confidence"] = (
            results["operator_consistency"]["score"] * 0.4 +
            results["pattern_confidence"]["score"] * 0.3 +
            results["stability_score"]["score"] * 0.3
        )

        # 按指标计算置信度
        results["confidence_by_indicator"] = self._calculate_indicator_confidence(
            anomaly_scores, operator_results
        )

        logger.info(f"[CONFIDENCE] 评估完成，平均置信度: {results['avg_confidence']:.2%}")

        return results

    def _evaluate_operator_consistency(self,
                                      operator_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估算子一致性"""
        # 获取所有算子和指标
        operators = list(operator_results.keys())
        indicators = set()

        for operator_result in operator_results.values():
            for indicator in operator_result.keys():
                if "error" not in operator_result[indicator]:
                    indicators.add(indicator)

        consistency_scores = {}

        for indicator in indicators:
            # 获取各算子的异常判定
            anomaly_decisions = []
            for operator in operators:
                if indicator in operator_results[operator]:
                    result = operator_results[operator][indicator]
                    if "anomalies" in result:
                        anomaly_decisions.append(result["anomalies"])

            if len(anomaly_decisions) < 2:
                consistency_scores[indicator] = 0.0
                continue

            # 统一长度
            min_len = min(len(d) for d in anomaly_decisions)
            anomaly_decisions = [d[:min_len] for d in anomaly_decisions]

            # 计算一致性（使用Krippendorff's alpha的简化版本）
            total_agreements = 0
            total_pairs = 0

            for i in range(len(anomaly_decisions)):
                for j in range(i + 1, len(anomaly_decisions)):
                    decisions1 = np.array(anomaly_decisions[i])
                    decisions2 = np.array(anomaly_decisions[j])

                    agreement = np.mean(decisions1 == decisions2)
                    total_agreements += agreement
                    total_pairs += 1

            consistency = total_agreements / total_pairs if total_pairs > 0 else 0
            consistency_scores[indicator] = consistency

        # 平均一致性
        avg_consistency = np.mean(list(consistency_scores.values())) if consistency_scores else 0

        return {
            "score": float(avg_consistency),
            "by_indicator": consistency_scores
        }

    def _evaluate_pattern_confidence(self,
                                    anomaly_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """评估模式置信度"""
        patterns = anomaly_patterns.get("patterns", {})
        total_anomalies = anomaly_patterns.get("summary", {}).get("total_anomalies", 0)

        if total_anomalies == 0:
            return {
                "score": 0.0,
                "dominant_pattern": None,
                "pattern_distribution": {}
            }

        # 计算模式分布
        pattern_distribution = {
            pattern: count / total_anomalies
            for pattern, count in patterns.items()
        }

        # 识别主导模式
        dominant_pattern = max(pattern_distribution.items(), key=lambda x: x[1])[0] if pattern_distribution else None

        # 计算置信度（基于模式集中度）
        if dominant_pattern:
            confidence = pattern_distribution.get(dominant_pattern, 0)
        else:
            confidence = 0

        return {
            "score": float(confidence),
            "dominant_pattern": dominant_pattern,
            "pattern_distribution": pattern_distribution
        }

    def _evaluate_stability(self, anomaly_scores: Dict[str, Any]) -> Dict[str, Any]:
        """评估异常稳定性"""
        anomaly_moments = anomaly_scores.get("anomaly_moments", [])

        if not anomaly_moments:
            return {"score": 0.0, "stable_count": 0}

        # 按指标分组
        indicator_anomalies = {}
        for moment in anomaly_moments:
            indicator = moment["indicator"]
            if indicator not in indicator_anomalies:
                indicator_anomalies[indicator] = []
            indicator_anomalies[indicator].append(moment)

        # 计算稳定性（异常分数的方差）
        stability_scores = {}

        for indicator, moments in indicator_anomalies.items():
            scores = [m["score"] for m in moments]

            if len(scores) > 1:
                # 分数越集中，稳定性越高
                score_std = np.std(scores)
                stability = 1 / (1 + score_std)
            else:
                stability = 0.5  # 单个异常点，中等稳定性

            stability_scores[indicator] = stability

        avg_stability = np.mean(list(stability_scores.values())) if stability_scores else 0

        return {
            "score": float(avg_stability),
            "stable_count": sum(1 for s in stability_scores.values() if s > 0.5),
            "by_indicator": stability_scores
        }

    def _calculate_indicator_confidence(self,
                                       anomaly_scores: Dict[str, Any],
                                       operator_results: Dict[str, Any]) -> Dict[str, float]:
        """计算各指标的置信度"""
        indicator_confidence = {}

        # 获取异常时刻
        anomaly_moments = anomaly_scores.get("anomaly_moments", [])

        for moment in anomaly_moments:
            indicator = moment["indicator"]

            if indicator not in indicator_confidence:
                indicator_confidence[indicator] = []

            # 基于分数的基础置信度
            base_confidence = min(1.0, moment["score"])

            # 调整因子
            adjustment = 1.0

            # 如果多个算子都检测到，提高置信度
            operator_count = 0
            for operator_result in operator_results.values():
                if indicator in operator_result:
                    if "anomalies" in operator_result[indicator]:
                        operator_count += 1

            if operator_count > 1:
                adjustment *= (1 + 0.1 * operator_count)

            indicator_confidence[indicator].append(base_confidence * adjustment)

        # 计算平均置信度
        avg_confidence = {
            indicator: float(np.mean(confidences))
            for indicator, confidences in indicator_confidence.items()
        }

        return avg_confidence

    def generate_confidence_report(self, confidence_results: Dict[str, Any]) -> str:
        """生成置信度报告"""
        report_lines = [
            "=== 可信度评估报告 ===",
            f"综合置信度: {confidence_results['avg_confidence']:.2%}",
            "",
            "1. 算子一致性:",
            f"   一性得分: {confidence_results['operator_consistency']['score']:.2%}",
            "",
            "2. 模式置信度:",
            f"   主导模式: {confidence_results['pattern_confidence']['dominant_pattern']}",
            f"   模式得分: {confidence_results['pattern_confidence']['score']:.2%}",
            "",
            "3. 稳定性评估:",
            f"   稳定性得分: {confidence_results['stability_score']['score']:.2%}",
            f"   稳定异常数: {confidence_results['stability_score']['stable_count']}",
            "",
            "4. 各指标置信度:"
        ]

        for indicator, confidence in confidence_results.get("confidence_by_indicator", {}).items():
            report_lines.append(f"   {indicator}: {confidence:.2%}")

        return "\n".join(report_lines)
