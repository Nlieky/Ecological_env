#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直方图离群值评分 (HBOS) 异常检测器

使用直方图方法进行异常检测。
HBOS 通过构建数据直方图来计算异常分数，计算效率高。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List

logger = logging.getLogger(__name__)


class HBOSDetector:
    """
    直方图离群值评分异常检测器

    HBOS 通过构建数据直方图来计算异常分数。
    数据落在低频区间的分数更高。

    参数：
    - n_bins: 直方图箱数
    - alpha: 平滑参数 (0, 1]
    - contamination: 预期异常比例
    """

    def __init__(self, n_bins: int = 10, alpha: float = 0.5,
                 contamination: float = 0.1):
        """
        初始化 HBOS 检测器

        Args:
            n_bins: 直方图箱数
            alpha: 平滑参数，避免零频率
            contamination: 预期异常比例
        """
        self.n_bins = n_bins
        self.alpha = alpha
        self.contamination = contamination
        self.name = "直方图离群值评分"
        self.is_fitted = False
        self.bin_edges = None
        self.hist = None

    def fit(self, data: pd.Series) -> None:
        """
        训练模型（构建直方图）

        Args:
            data: 训练数据
        """
        data = data.dropna()
        if len(data) < self.n_bins * 2:
            logger.warning("[HBOS] 数据过少，减少箱数")
            self.n_bins = max(5, len(data) // 2)

        # 构建直方图
        hist, bin_edges = np.histogram(data, bins=self.n_bins)

        # 平滑处理（避免零频率）
        self.hist = hist + self.alpha
        self.bin_edges = bin_edges

        # 计算每个箱的密度
        total_count = self.hist.sum()
        self.densities = self.hist / total_count

        # 计算阈值
        self.threshold = np.percentile(self._compute_scores(data), (1 - self.contamination) * 100)

        self.is_fitted = True
        logger.info("[HBOS] 模型训练完成")

    def _compute_scores(self, data: np.ndarray) -> np.ndarray:
        """
        计算异常分数

        Args:
            data: 输入数据

        Returns:
            异常分数
        """
        scores = np.zeros(len(data))

        for i, value in enumerate(data):
            # 找到数据所在的箱
            bin_idx = np.digitize(value, self.bin_edges) - 1
            bin_idx = np.clip(bin_idx, 0, len(self.densities) - 1)

            # 异常分数 = log(1/密度)
            density = self.densities[bin_idx]
            scores[i] = np.log(1 / density) if density > 0 else 10

        return scores

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测异常

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < 5:
            return np.zeros(len(data)), {"error": "数据过少"}

        # 如果模型未训练，先训练
        if not self.is_fitted:
            self.fit(data)

        # 计算异常分数
        scores = self._compute_scores(data.values)

        # 基于阈值判断异常
        anomaly_mask = scores > self.threshold

        details = {
            "anomaly_count": int(anomaly_mask.sum()),
            "anomaly_rate": float(anomaly_mask.sum() / len(data)),
            "mean_score": float(scores.mean()),
            "max_score": float(scores.max()),
            "threshold": float(self.threshold),
            "n_bins": self.n_bins
        }

        return anomaly_mask, details

    def detect_multi_dimensional(self, df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        多维数据检测

        Args:
            df: 输入数据框

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        if df.isnull().any().any():
            df = df.dropna()

        if len(df) < 10:
            return np.zeros(len(df)), {"error": "数据过少"}

        scores_list = []

        for column in df.columns:
            # 为每个维度构建直方图
            data = df[column].values
            hist, bin_edges = np.histogram(data, bins=self.n_bins)
            hist = hist + self.alpha
            densities = hist / hist.sum()

            # 计算该维度的分数
            scores = np.zeros(len(data))
            for i, value in enumerate(data):
                bin_idx = np.digitize(value, bin_edges) - 1
                bin_idx = np.clip(bin_idx, 0, len(densities) - 1)
                density = densities[bin_idx]
                scores[i] = np.log(1 / density) if density > 0 else 10

            scores_list.append(scores)

        # 综合分数（各维度分数之和）
        combined_scores = np.sum(scores_list, axis=0)

        # 计算阈值
        threshold = np.percentile(combined_scores, (1 - self.contamination) * 100)
        anomaly_mask = combined_scores > threshold

        details = {
            "anomaly_count": int(anomaly_mask.sum()),
            "anomaly_rate": float(anomaly_mask.sum() / len(df)),
            "mean_score": float(combined_scores.mean()),
            "max_score": float(combined_scores.max()),
            "threshold": float(threshold),
            "dimensions": list(df.columns)
        }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
