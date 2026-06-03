#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSTM自编码器 - 基于长短期记忆网络的自编码器异常检测

基于专利文档：使用LSTM自编码器进行时序数据的异常检测。
适用于长序列数据，能够捕捉时序依赖关系。

注意：此实现为简化版本，生产环境建议使用完整训练的模型。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LSTMAutoEncoder:
    """
    LSTM自编码器异常检测器

    使用LSTM自编码器进行时序数据的异常检测。
    通过重构误差判断异常。

    模型结构：
    - 编码器：LSTM层提取时序特征
    - 解码器：LSTM层重构原始序列
    - 异常判断：重构误差超过阈值

    注意：此实现为简化版本，使用统计方法模拟
    """

    def __init__(self, sequence_length: int = 10,
                 threshold: float = 2.0,
                 use_simple_model: bool = True):
        """
        初始化LSTM自编码器

        Args:
            sequence_length: 序列长度
            threshold: 异常阈值（标准差倍数）
            use_simple_model: 是否使用简化模型（无需深度学习库）
        """
        self.sequence_length = sequence_length
        self.threshold = threshold
        self.use_simple_model = use_simple_model
        self.name = "LSTM自编码器"
        self.is_fitted = False
        self.normal_stats = None

    def fit(self, data: pd.Series) -> None:
        """
        训练模型（简化版本：计算正常数据的统计特征）

        Args:
            data: 正常数据用于训练
        """
        data = data.dropna()
        if len(data) < self.sequence_length * 2:
            logger.warning("[LSTM-AE] 数据过少，无法训练")
            return

        # 简化版本：使用移动平均和标准差
        rolling_mean = data.rolling(window=self.sequence_length).mean()
        rolling_std = data.rolling(window=self.sequence_length).std()

        # 计算重构误差的统计特征
        reconstruction_error = np.abs(data - rolling_mean).dropna()

        self.normal_stats = {
            "mean": float(reconstruction_error.mean()),
            "std": float(reconstruction_error.std()),
            "q95": float(reconstruction_error.quantile(0.95)),
            "q99": float(reconstruction_error.quantile(0.99))
        }
        self.is_fitted = True

        logger.info(f"[LSTM-AE] 模型训练完成，阈值: {self.normal_stats['q99']:.4f}")

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测异常

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < self.sequence_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        # 如果模型未训练，先训练
        if not self.is_fitted:
            self.fit(data)

        # 计算重构误差
        rolling_mean = data.rolling(window=self.sequence_length).mean()
        reconstruction_error = np.abs(data - rolling_mean).fillna(0)

        # 根据阈值判断异常
        threshold_value = self.normal_stats["mean"] + self.threshold * self.normal_stats["std"]
        anomaly_mask = reconstruction_error > threshold_value

        # 计算异常分数
        anomaly_scores = (reconstruction_error - self.normal_stats["mean"]) / (self.normal_stats["std"] + 1e-10)

        details = {
            "threshold": float(threshold_value),
            "max_error": float(reconstruction_error.max()),
            "mean_error": float(reconstruction_error.mean()),
            "anomaly_count": int(anomaly_mask.sum()),
            "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask)),
            "anomaly_scores": anomaly_scores.tolist()
        }

        return anomaly_mask.values, details

    def detect_sequences(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测序列级别的异常

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        n = len(data)

        if n < self.sequence_length * 2:
            return np.zeros(n), {"error": "数据过少"}

        # 滑动窗口检测
        anomaly_scores = []
        for i in range(self.sequence_length, n):
            sequence = data.iloc[i - self.sequence_length:i]

            # 计算序列的统计特征
            seq_mean = sequence.mean()
            seq_std = sequence.std()
            seq_range = sequence.max() - sequence.min()

            # 简化的重构误差
            reconstruction_error = abs(sequence.iloc[-1] - seq_mean)

            # 归一化
            if seq_std > 0:
                score = reconstruction_error / seq_std
            else:
                score = 0

            anomaly_scores.append(score)

        anomaly_scores = np.array(anomaly_scores)

        # 基于阈值判断异常
        threshold_value = np.mean(anomaly_scores) + self.threshold * np.std(anomaly_scores)
        anomaly_mask_full = np.zeros(n, dtype=bool)
        anomaly_mask_full[self.sequence_length:] = anomaly_scores > threshold_value

        details = {
            "threshold": float(threshold_value),
            "max_score": float(anomaly_scores.max()),
            "mean_score": float(anomaly_scores.mean()),
            "anomaly_count": int(anomaly_mask_full.sum()),
            "anomaly_scores": anomaly_scores.tolist()
        }

        return anomaly_mask_full, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
