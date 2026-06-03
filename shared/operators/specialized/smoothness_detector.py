#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平滑度检测器 - 检测人工拟合

基于专利文档：平滑度检测器用于检测数据是否过于平滑，
这通常是"人工拟合"违规模式的特征。

人工拟合：人为篡改数据使曲线过于平滑，缺乏自然波动。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class SmoothnessDetector:
    """
    平滑度检测器

    检测数据是否过于平滑，用于识别人工拟合违规。

    检测方法：
    1. 一阶差分标准差：过于平滑的数据差分很小
    2. 二阶差分检测：检测曲率变化
    3. 自相关检测：过于平滑的数据有强自相关性
    """

    def __init__(self, diff_std_threshold: float = 0.1,
                 autocorr_threshold: float = 0.9,
                 change_rate_threshold: float = 0.05):
        """
        初始化平滑度检测器

        Args:
            diff_std_threshold: 一阶差分标准差阈值
            autocorr_threshold: 自相关系数阈值
            change_rate_threshold: 变化率阈值
        """
        self.diff_std_threshold = diff_std_threshold
        self.autocorr_threshold = autocorr_threshold
        self.change_rate_threshold = change_rate_threshold
        self.name = "平滑度检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测数据中的过度平滑

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < 20:
            return np.zeros(len(data)), {"error": "数据过少"}

        # 计算一阶差分
        diff1 = data.diff().dropna()

        # 计算二阶差分
        diff2 = diff1.diff().dropna()

        # 1. 一阶差分标准差检测
        diff1_std = diff1.std()
        diff1_mean = abs(diff1.mean())
        is_smooth_diff1 = diff1_std < self.diff_std_threshold

        # 2. 二阶差分标准差检测
        diff2_std = diff2.std()
        is_smooth_diff2 = diff2_std < self.diff_std_threshold * 0.5

        # 3. 自相关检测（滞后1）
        try:
            autocorr = data.autocorr(lag=1)
            if pd.isna(autocorr):
                autocorr = 0
        except:
            autocorr = 0

        is_smooth_autocorr = abs(autocorr) > self.autocorr_threshold

        # 4. 变化率检测
        change_rate = (data.max() - data.min()) / data.mean() if data.mean() != 0 else float('inf')
        is_smooth_change_rate = change_rate < self.change_rate_threshold

        # 综合判断
        smooth_indicators = sum([
            is_smooth_diff1,
            is_smooth_diff2,
            is_smooth_autocorr,
            is_smooth_change_rate
        ])

        # 至少3个指标表明平滑
        is_too_smooth = smooth_indicators >= 3

        if is_too_smooth:
            anomaly_mask = np.ones(len(data), dtype=bool)
            violation_type = "人工拟合"
            confidence = smooth_indicators / 4.0
        else:
            anomaly_mask = np.zeros(len(data), dtype=bool)
            violation_type = None
            confidence = smooth_indicators / 4.0

        details = {
            "violation_type": violation_type if is_too_smooth else None,
            "confidence": float(confidence),
            "diff1_std": float(diff1_std),
            "diff2_std": float(diff2_std),
            "autocorr": float(autocorr),
            "change_rate": float(change_rate),
            "is_smooth_diff1": bool(is_smooth_diff1),
            "is_smooth_diff2": bool(is_smooth_diff2),
            "is_smooth_autocorr": bool(is_smooth_autocorr),
            "is_smooth_change_rate": bool(is_smooth_change_rate),
            "smooth_indicators": smooth_indicators
        }

        return anomaly_mask, details

    def detect_local_smoothness(self, data: pd.Series, window_size: int = 10) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测局部平滑度（滑动窗口）

        Args:
            data: 输入数据序列
            window_size: 窗口大小

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < window_size * 2:
            return np.zeros(len(data)), {"error": "数据过少"}

        n = len(data)
        anomaly_mask = np.zeros(n, dtype=bool)
        smooth_windows = []

        for i in range(window_size, n - window_size + 1):
            window = data.iloc[i - window_size:i + window_size]

            # 局部标准差
            local_std = window.std()
            local_mean = window.mean()
            local_cv = local_std / local_mean if local_mean != 0 else float('inf')

            # 局部平滑判断
            if local_cv < self.diff_std_threshold:
                anomaly_mask[i - window_size:i + window_size] = True
                smooth_windows.append({
                    "center": int(i),
                    "local_std": float(local_std),
                    "local_cv": float(local_cv)
                })

        details = {
            "smooth_window_count": len(smooth_windows),
            "smooth_windows": smooth_windows
        }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
