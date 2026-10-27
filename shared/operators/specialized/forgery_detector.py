#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
造假检测器 - 检测恶意逃避

造假检测器用于检测恶意逃避检测的违规模式，
这类数据看起来正常但包含了精心设计的规避模式。

恶意逃避：数据被人为设计以逃避标准异常检测，但具有特定的统计特征。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from scipy import stats

logger = logging.getLogger(__name__)


class ForgeryDetector:
    """
    造假检测器

    检测恶意逃避检测的违规模式。

    检测方法：
    1. 周期性检测：检测人为周期性
    2. 数值聚类检测：检测数值集中在特定范围
    3. 时序模式检测：检测异常的时序模式
    4. 统计分布检测：检测非自然分布
    """

    def __init__(self, periodicity_threshold: float = 0.8,
                 cluster_threshold: float = 0.3):
        """
        初始化造假检测器

        Args:
            periodicity_threshold: 周期性检测阈值
            cluster_threshold: 聚类检测阈值
        """
        self.periodicity_threshold = periodicity_threshold
        self.cluster_threshold = cluster_threshold
        self.name = "造假检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测数据中的造假模式

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < 30:
            return np.zeros(len(data)), {"error": "数据过少"}

        n = len(data)
        anomaly_mask = np.zeros(n, dtype=bool)
        forgery_indicators = []

        # 1. 周期性检测
        is_periodic, periodicity_info = self._detect_periodicity(data)
        if is_periodic:
            forgery_indicators.append("周期性")
            anomaly_mask = anomaly_mask | np.ones(n, dtype=bool)

        # 2. 数值聚类检测
        is_clustered, cluster_info = self._detect_clustering(data)
        if is_clustered:
            forgery_indicators.append("数值聚类")
            anomaly_mask = anomaly_mask | np.ones(n, dtype=bool)

        # 3. 统计分布检测
        is_unnatural, distribution_info = self._detect_unnatural_distribution(data)
        if is_unnatural:
            forgery_indicators.append("非自然分布")
            anomaly_mask = anomaly_mask | np.ones(n, dtype=bool)

        # 4. 时序模式检测
        has_pattern, pattern_info = self._detect_temporal_patterns(data)
        if has_pattern:
            forgery_indicators.append("时序模式")
            anomaly_mask = anomaly_mask | np.ones(n, dtype=bool)

        # 判断是否为造假
        is_forgery = len(forgery_indicators) >= 2

        if is_forgery:
            violation_type = "恶意逃避"
            confidence = len(forgery_indicators) / 4.0
        else:
            violation_type = None
            confidence = 0.0

        details = {
            "violation_type": violation_type if is_forgery else None,
            "confidence": float(confidence),
            "forgery_indicators": forgery_indicators,
            "indicator_count": len(forgery_indicators),
            "periodicity_info": periodicity_info,
            "cluster_info": cluster_info,
            "distribution_info": distribution_info,
            "pattern_info": pattern_info
        }

        return anomaly_mask, details

    def _detect_periodicity(self, data: pd.Series) -> Tuple[bool, Dict[str, Any]]:
        """检测周期性"""
        # 使用FFT检测周期性
        values = data.values
        n = len(values)

        # 去趋势
        detrended = values - np.mean(values)

        # FFT
        fft_result = np.fft.fft(detrended)
        power = np.abs(fft_result[:n//2])

        # 归一化功率谱
        power = power / (power.sum() + 1e-10)

        # 检测强周期分量
        max_power = power.max()
        is_periodic = max_power > self.periodicity_threshold

        info = {
            "max_power": float(max_power),
            "is_periodic": bool(is_periodic)
        }

        return is_periodic, info

    def _detect_clustering(self, data: pd.Series) -> Tuple[bool, Dict[str, Any]]:
        """检测数值聚类"""
        values = data.values

        # 计算唯一值比例
        unique_count = len(np.unique(values))
        unique_ratio = unique_count / len(values)

        # 计算数值范围
        value_range = values.max() - values.min()
        if value_range == 0:
            return False, {"error": "值范围为零"}

        # 分箱检测
        bins = 20
        hist, _ = np.histogram(values, bins=bins)
        max_bin_count = hist.max()
        max_bin_ratio = max_bin_count / len(values)

        # 检测聚类
        is_clustered = (unique_ratio < self.cluster_threshold) or (max_bin_ratio > 0.3)

        info = {
            "unique_count": int(unique_count),
            "unique_ratio": float(unique_ratio),
            "max_bin_ratio": float(max_bin_ratio),
            "is_clustered": bool(is_clustered)
        }

        return is_clustered, info

    def _detect_unnatural_distribution(self, data: pd.Series) -> Tuple[bool, Dict[str, Any]]:
        """检测非自然分布"""
        values = data.values

        # 正态性检验
        try:
            _, p_value = stats.normaltest(values)
            is_not_normal = p_value < 0.001  # 非常显著地非正态
        except:
            is_not_normal = False
            p_value = 1.0

        # 偏度和峰度
        skewness = stats.skew(values)
        kurtosis = stats.kurtosis(values)

        # 检测极端偏度或峰度
        is_extreme = (abs(skewness) > 2) or (abs(kurtosis) > 5)

        is_unnatural = is_not_normal and is_extreme

        info = {
            "normaltest_p_value": float(p_value),
            "skewness": float(skewness),
            "kurtosis": float(kurtosis),
            "is_not_normal": bool(is_not_normal),
            "is_extreme": bool(is_extreme),
            "is_unnatural": bool(is_unnatural)
        }

        return is_unnatural, info

    def _detect_temporal_patterns(self, data: pd.Series) -> Tuple[bool, Dict[str, Any]]:
        """检测时序模式"""
        values = data.values
        n = len(values)

        # 检测重复序列
        if n < 10:
            return False, {"error": "数据过少"}

        # 滑动窗口检测重复
        window_size = min(10, n // 3)
        pattern_found = False
        pattern_count = 0

        for i in range(n - 2 * window_size):
            pattern1 = values[i:i + window_size]
            pattern2 = values[i + window_size:i + 2 * window_size]

            # 计算相似度
            correlation = np.corrcoef(pattern1, pattern2)[0, 1]

            if not np.isnan(correlation) and abs(correlation) > 0.95:
                pattern_count += 1

        # 如果发现多个重复模式
        has_pattern = pattern_count > n * 0.1

        info = {
            "pattern_count": int(pattern_count),
            "has_pattern": bool(has_pattern)
        }

        return has_pattern, info

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
