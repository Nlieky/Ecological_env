#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
变分自编码器 (VAE) - 基于变分推断的自编码器异常检测

使用变分自编码器进行时序数据的异常检测。
VAE能够学习数据的潜在分布，通过重构概率判断异常。

注意：此实现为简化版本，生产环境建议使用完整训练的模型。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class VariationalAutoEncoder:
    """
    变分自编码器异常检测器

    使用变分自编码器进行数据的异常检测。
    通过重构概率和潜在分布判断异常。

    模型结构：
    - 编码器：将数据映射到潜在分布
    - 解码器：从潜在分布重构数据
    - 异常判断：重构概率低于阈值

    注意：此实现为简化版本，使用统计方法模拟
    """

    def __init__(self, latent_dim: int = 8,
                 threshold_percentile: float = 95,
                 use_simple_model: bool = True):
        """
        初始化变分自编码器

        Args:
            latent_dim: 潜在维度
            threshold_percentile: 异常阈值百分位数
            use_simple_model: 是否使用简化模型
        """
        self.latent_dim = latent_dim
        self.threshold_percentile = threshold_percentile
        self.use_simple_model = use_simple_model
        self.name = "变分自编码器"
        self.is_fitted = False
        self.threshold = None

    def fit(self, data: pd.Series) -> None:
        """
        训练模型（简化版本：学习正常数据的分布）

        Args:
            data: 正常数据用于训练
        """
        data = data.dropna()
        if len(data) < 50:
            logger.warning("[VAE] 数据过少，无法训练")
            return

        # 简化版本：使用分位数学习数据分布
        self.data_min = data.min()
        self.data_max = data.max()
        self.data_mean = data.mean()
        self.data_std = data.std()

        # 计算重构误差的分布
        rolling_mean = data.rolling(window=5).mean()
        reconstruction_errors = np.abs(data - rolling_mean).dropna()

        # 设置阈值
        self.threshold = np.percentile(reconstruction_errors, self.threshold_percentile)
        self.is_fitted = True

        logger.info(f"[VAE] 模型训练完成，阈值: {self.threshold:.4f}")

    def encode(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        编码数据到潜在空间

        Args:
            data: 输入数据

        Returns:
            (z_mean, z_log_var): 潜在分布的均值和方差
        """
        # 简化版本：使用标准化作为编码
        if self.data_std > 0:
            normalized = (data - self.data_mean) / self.data_std
        else:
            normalized = data - self.data_mean

        # 模拟潜在分布
        z_mean = normalized[:self.latent_dim] if len(normalized) >= self.latent_dim else np.pad(normalized, (0, self.latent_dim - len(normalized)))
        z_log_var = np.zeros_like(z_mean) - 1  # 对数方差

        return z_mean, z_log_var

    def decode(self, z_mean: np.ndarray, z_log_var: np.ndarray) -> np.ndarray:
        """
        从潜在空间解码数据

        Args:
            z_mean: 潜在分布均值
            z_log_var: 潜在分布对数方差

        Returns:
            重构数据
        """
        # 简化版本：使用逆标准化
        reconstructed = z_mean[0]  # 取第一个维度

        if self.data_std > 0:
            reconstructed = reconstructed * self.data_std + self.data_mean
        else:
            reconstructed = reconstructed + self.data_mean

        return np.array([reconstructed])

    def reconstruct(self, data: pd.Series) -> np.ndarray:
        """
        重构数据

        Args:
            data: 输入数据

        Returns:
            重构数据
        """
        data_values = data.values

        # 简化版本：使用移动平均作为重构
        reconstructed = data.rolling(window=5, center=True).mean()
        reconstructed = reconstructed.bfill().ffill()

        return reconstructed.values

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测异常

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < 10:
            return np.zeros(len(data)), {"error": "数据过少"}

        # 如果模型未训练，先训练
        if not self.is_fitted:
            self.fit(data)

        # 重构数据
        reconstructed = self.reconstruct(data)

        # 计算重构误差
        reconstruction_error = np.abs(data.values - reconstructed)

        # 计算异常分数（考虑概率）
        # 简化版本：使用标准化误差
        if self.data_std > 0:
            anomaly_scores = reconstruction_error / self.data_std
        else:
            anomaly_scores = reconstruction_error

        # 基于阈值判断异常
        anomaly_mask = reconstruction_error > self.threshold

        # 计算重构概率（简化版本）
        max_error = reconstruction_error.max()
        if max_error > 0:
            reconstruction_prob = 1 - (reconstruction_error / max_error)
        else:
            reconstruction_prob = np.ones_like(reconstruction_error)

        details = {
            "threshold": float(self.threshold),
            "max_error": float(reconstruction_error.max()),
            "mean_error": float(reconstruction_error.mean()),
            "anomaly_count": int(anomaly_mask.sum()),
            "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask)),
            "anomaly_scores": anomaly_scores.tolist(),
            "reconstruction_prob": reconstruction_prob.tolist()
        }

        return anomaly_mask, details

    def detect_with_probability(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        基于重构概率检测异常

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < 10:
            return np.zeros(len(data)), {"error": "数据过少"}

        # 如果模型未训练，先训练
        if not self.is_fitted:
            self.fit(data)

        # 编码-解码
        reconstructed = self.reconstruct(data)

        # 计算重构误差和概率
        reconstruction_error = np.abs(data.values - reconstructed)

        # 计算概率（基于正态分布假设）
        if self.data_std > 0:
            from scipy.stats import norm
            # 假设重构误差服从正态分布
            error_mean = reconstruction_error.mean()
            error_std = reconstruction_error.std() + 1e-10

            # 计算累积概率
            reconstruction_prob = norm.cdf(reconstruction_error, error_mean, error_std)

            # 低概率区域视为异常
            anomaly_mask = reconstruction_prob < 0.05
        else:
            reconstruction_prob = np.ones_like(reconstruction_error)
            anomaly_mask = np.zeros_like(reconstruction_error, dtype=bool)

        details = {
            "threshold": float(self.threshold),
            "min_prob": float(reconstruction_prob.min()),
            "mean_prob": float(reconstruction_prob.mean()),
            "anomaly_count": int(anomaly_mask.sum()),
            "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask)),
            "reconstruction_prob": reconstruction_prob.tolist()
        }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
