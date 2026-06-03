#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
变点检测器 - 检测数据中的突变点

基于专利文档：变点检测器用于检测数据分布中的突然变化点，
这可能是设备故障、人为篡改或其他异常情况的特征。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from scipy import stats

logger = logging.getLogger(__name__)


class ChangePointDetector:
    """
    变点检测器

    检测数据中的突变点，用于识别数据分布的突然变化。

    检测方法：
    1. 均值变点检测：使用CUSUM方法
    2. 方差变点检测：检测方差变化
    3. 分布变点检测：使用Kolmogorov-Smirnov检验
    """

    def __init__(self, window_size: int = 20, threshold: float = 3.0):
        """
        初始化变点检测器

        Args:
            window_size: 滑动窗口大小
            threshold: 检测阈值（标准差倍数）
        """
        self.window_size = window_size
        self.threshold = threshold
        self.name = "变点检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测数据中的变点

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < self.window_size * 2:
            return np.zeros(len(data)), {"error": "数据过少"}

        n = len(data)
        anomaly_mask = np.zeros(n, dtype=bool)
        change_points = []

        # 滑动窗口检测
        for i in range(self.window_size, n - self.window_size):
            # 前窗口和后窗口
            window_before = data.iloc[i - self.window_size:i]
            window_after = data.iloc[i:i + self.window_size]

            # 均值差异
            mean_before = window_before.mean()
            mean_after = window_after.mean()
            mean_diff = abs(mean_after - mean_before)

            # 标准差（用于归一化）
            pooled_std = np.sqrt(
                (window_before.std() ** 2 + window_after.std() ** 2) / 2
            )

            if pooled_std > 0:
                # 归一化差异
                normalized_diff = mean_diff / pooled_std

                # 判断是否为变点
                if normalized_diff > self.threshold:
                    anomaly_mask[i] = True
                    change_points.append({
                        "index": int(i),
                        "position": data.index[i],
                        "mean_diff": float(mean_diff),
                        "normalized_diff": float(normalized_diff),
                        "before_mean": float(mean_before),
                        "after_mean": float(mean_after)
                    })

        details = {
            "change_point_count": len(change_points),
            "change_points": change_points,
            "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask))
        }

        return anomaly_mask, details

    def detect_distribution_change(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        使用KS检验检测分布变化

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < self.window_size * 2:
            return np.zeros(len(data)), {"error": "数据过少"}

        n = len(data)
        anomaly_mask = np.zeros(n, dtype=bool)
        change_points = []

        for i in range(self.window_size, n - self.window_size):
            window_before = data.iloc[i - self.window_size:i]
            window_after = data.iloc[i:i + self.window_size]

            # Kolmogorov-Smirnov检验
            ks_statistic, p_value = stats.ks_2samp(window_before, window_after)

            # 显著的分布变化
            if p_value < 0.01:  # 1% 显著性水平
                anomaly_mask[i] = True
                change_points.append({
                    "index": int(i),
                    "position": data.index[i],
                    "ks_statistic": float(ks_statistic),
                    "p_value": float(p_value)
                })

        details = {
            "change_point_count": len(change_points),
            "change_points": change_points,
            "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask))
        }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
