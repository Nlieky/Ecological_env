#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-Class SVM 异常检测器

使用支持向量机进行单类分类异常检测。
One-Class SVM 学习正常数据的边界，超出边界的为异常。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class OneClassSVMDetector:
    """
    One-Class SVM 异常检测器

    使用支持向量机进行单类分类，检测超出正常边界的异常点。

    参数：
    - nu: 异常比例上限
    - kernel: 核函数类型
    - gamma: 核系数
    """

    def __init__(self, nu: float = 0.1, kernel: str = 'rbf', gamma: str = 'scale'):
        """
        初始化 One-Class SVM 检测器

        Args:
            nu: 异常比例上限 (0, 1]
            kernel: 核函数类型 ('rbf', 'linear', 'poly')
            gamma: 核系数 ('scale', 'auto', 或 float)
        """
        self.nu = nu
        self.kernel = kernel
        self.gamma = gamma
        self.name = "One-Class SVM"
        self.is_fitted = False

        # 尝试导入 sklearn
        try:
            from sklearn.svm import OneClassSVM
            self.sklearn_available = True
            self.model = OneClassSVM(nu=nu, kernel=kernel, gamma=gamma)
        except ImportError:
            self.sklearn_available = False
            logger.warning("[SVM] sklearn 不可用，使用简化版本")

    def fit(self, data: pd.Series) -> None:
        """
        训练模型

        Args:
            data: 训练数据
        """
        data = data.dropna()
        if len(data) < 10:
            logger.warning("[SVM] 数据过少，无法训练")
            return

        if self.sklearn_available:
            # sklearn 实现
            X = data.values.reshape(-1, 1)
            self.model.fit(X)
            self.is_fitted = True
            logger.info("[SVM] 模型训练完成")
        else:
            # 简化版本：使用统计方法
            self.data_mean = data.mean()
            self.data_std = data.std()
            self.is_fitted = True
            logger.info("[SVM] 简化模型训练完成")

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

        if self.sklearn_available:
            # sklearn 实现
            X = data.values.reshape(-1, 1)
            predictions = self.model.predict(X)
            scores = self.model.score_samples(X)

            # -1 表示异常
            anomaly_mask = predictions == -1

            details = {
                "anomaly_count": int(anomaly_mask.sum()),
                "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask)),
                "mean_score": float(scores.mean()),
                "min_score": float(scores.min()),
                "nu": self.nu
            }
        else:
            # 简化版本：使用标准差方法
            threshold = self.data_mean + 2 * self.data_std
            anomaly_mask = data > threshold

            details = {
                "anomaly_count": int(anomaly_mask.sum()),
                "anomaly_rate": float(anomaly_mask.sum() / len(data)),
                "threshold": float(threshold),
                "mean": float(self.data_mean),
                "std": float(self.data_std)
            }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
