#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常评分计算模块
功能：综合多算子结果计算异常分数

基于专利文档：异常评分计算模块
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyScorer:
    """
    异常评分计算器

    功能：
    1. 综合多个算子的检测结果
    2. 计算统一的异常分数
    3. 定位异常时刻
    """

    def __init__(self):
        """初始化异常评分计算器"""
        self.name = "异常评分计算器"
        self.version = "2.0.0"

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def calculate_scores(self, data: pd.DataFrame,
                        operator_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算异常分数

        Args:
            data: 输入数据
            operator_results: 算子检测结果

        Returns:
            异常分数结果
        """
        logger.info(f"[SCORER] 计算异常分数")

        # 获取所有指标
        indicators = set()
        for operator_result in operator_results.values():
            for indicator in operator_result.keys():
                if "error" not in operator_result[indicator]:
                    indicators.add(indicator)

        results = {
            "scores": {},
            "thresholds": {},
            "anomaly_moments": []
        }

        for indicator in indicators:
            indicator_scores = self._calculate_indicator_scores(
                indicator, operator_results
            )

            results["scores"][indicator] = indicator_scores["scores"]
            results["thresholds"][indicator] = indicator_scores["threshold"]

            # 定位异常时刻
            if len(data) > 0:
                anomalies = np.where(indicator_scores["anomalies"])[0]
                for idx in anomalies:
                    if idx < len(data):
                        moment = {
                            "indicator": indicator,
                            "index": int(idx),
                            "score": float(indicator_scores["scores"][idx]),
                            "times": data.iloc[idx].get("timestamp", data.iloc[idx].get("times", str(idx)))
                        }
                        results["anomaly_moments"].append(moment)

        # 按分数排序
        results["anomaly_moments"].sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"[SCORER] 评分完成: {len(results['anomaly_moments'])} 处异常")

        return results

    def _calculate_indicator_scores(self, indicator: str,
                                   operator_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算单个指标的异常分数"""
        # 收集各算子的分数
        all_scores = []
        all_anomalies = []

        for operator_name, operator_result in operator_results.items():
            if indicator not in operator_result:
                continue

            result = operator_result[indicator]
            if "error" in result:
                continue

            scores = result.get("scores", [])
            anomalies = result.get("anomalies", [])

            if scores:
                all_scores.append(scores)
            if len(anomalies) > 0:
                all_anomalies.append(anomalies)

        if not all_scores:
            return {
                "scores": np.array([]),
                "anomalies": np.array([], dtype=bool),
                "threshold": 0.0
            }

        # 统一长度
        min_len = min(len(s) for s in all_scores)
        all_scores = [s[:min_len] for s in all_scores]
        all_anomalies = [a[:min_len] for a in all_anomalies]

        # 归一化分数
        normalized_scores = []
        epsilon = 1e-10  # 防止除零

        for scores in all_scores:
            score_min = np.min(scores)
            score_max = np.max(scores)
            score_range = score_max - score_min

            if score_range > epsilon:
                # 正常情况：标准min-max归一化
                norm = (scores - score_min) / score_range
            else:
                # 所有分数相同的情况：赋予中性值
                # 当算子返回统一分数时，表示该算子无法区分差异
                # 赋予0.5作为中性值，让多算子投票机制决定最终结果
                norm = np.full_like(scores, 0.5, dtype=float)
                logger.info(f"[SCORER] 指标分数无变化 (统一值={score_max:.3f})，赋予中性值0.5")

            normalized_scores.append(norm)

        # 综合分数（加权平均）
        weights = np.ones(len(normalized_scores)) / len(normalized_scores)
        combined_scores = np.average(normalized_scores, axis=0, weights=weights)

        # 综合异常判定（至少两个算子认为是异常）
        combined_anomalies = np.sum(all_anomalies, axis=0) >= 1

        # 计算自适应阈值
        # 如果有异常点，使用较低的百分位数；否则使用较高的百分位数
        if combined_anomalies.sum() > 0:
            # 有异常点：使用60分位数（更敏感）
            threshold = np.percentile(combined_scores, 60)
        else:
            # 没有异常点：使用80分位数（更保守）
            threshold = np.percentile(combined_scores, 80)

        # 确保阈值不会太高（防止过滤掉所有异常）
        threshold = min(threshold, 0.6)

        logger.info(f"[SCORER] 计算阈值: {threshold:.3f}, 异常点数: {combined_anomalies.sum()}")

        return {
            "scores": combined_scores,
            "anomalies": combined_anomalies,
            "threshold": float(threshold)
        }

    def calculate_global_score(self, indicator_scores: Dict[str, np.ndarray],
                              weights: Dict[str, float] = None) -> np.ndarray:
        """
        计算全局异常分数

        Args:
            indicator_scores: 各指标异常分数
            weights: 权重

        Returns:
            全局异常分数
        """
        if not indicator_scores:
            return np.array([])

        # 统一长度
        min_len = min(len(scores) for scores in indicator_scores.values())
        aligned_scores = {k: v[:min_len] for k, v in indicator_scores.items()}

        # 默认权重（均等）
        if weights is None:
            weights = {k: 1.0 / len(aligned_scores) for k in aligned_scores.keys()}

        # 加权平均
        global_scores = np.zeros(min_len)
        for indicator, scores in aligned_scores.items():
            global_scores += weights.get(indicator, 0) * scores

        return global_scores
