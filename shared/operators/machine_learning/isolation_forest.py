#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
孤立森林异常检测器

使用孤立森林算法进行异常检测。
孤立森林通过随机划分特征空间来隔离异常点。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """
    孤立森林异常检测器

    使用孤立森林算法进行无监督异常检测。
    异常点更容易被孤立（路径长度更短）。

    参数：
    - n_estimators: 树的数量
    - contamination: 异常比例
    - max_samples: 每棵树的样本数
    """

    def __init__(self, n_estimators: int = 100,
                 contamination: float = 0.1,
                 max_samples: int = 'auto'):
        """
        初始化孤立森林检测器

        Args:
            n_estimators: 树的数量
            contamination: 预期异常比例
            max_samples: 每棵树的样本数
        """
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.name = "孤立森林"
        self.is_fitted = False

        # 尝试导入 sklearn
        try:
            from sklearn.ensemble import IsolationForest
            self.sklearn_available = True
            self.model = IsolationForest(
                n_estimators=n_estimators,
                contamination=contamination,
                max_samples=max_samples,
                random_state=42
            )
        except ImportError:
            self.sklearn_available = False
            logger.warning("[IF] sklearn 不可用，使用简化版本")

    def fit(self, data: pd.Series) -> None:
        """
        训练模型

        Args:
            data: 训练数据
        """
        data = data.dropna()
        if len(data) < 10:
            logger.warning("[IF] 数据过少，无法训练")
            return

        if self.sklearn_available:
            # sklearn 实现
            X = data.values.reshape(-1, 1)
            self.model.fit(X)
            self.is_fitted = True
            logger.info("[IF] 模型训练完成")
        else:
            # 简化版本：使用统计方法
            self.data_mean = data.mean()
            self.data_std = data.std()
            self.q25 = data.quantile(0.25)
            self.q75 = data.quantile(0.75)
            self.iqr = self.q75 - self.q25
            self.is_fitted = True
            logger.info("[IF] 简化模型训练完成")

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
                "contamination": self.contamination
            }
        else:
            # 简化版本：使用 IQR 方法
            lower_bound = self.q25 - 1.5 * self.iqr
            upper_bound = self.q75 + 1.5 * self.iqr

            anomaly_mask = (data < lower_bound) | (data > upper_bound)

            details = {
                "anomaly_count": int(anomaly_mask.sum()),
                "anomaly_rate": float(anomaly_mask.sum() / len(data)),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "iqr": float(self.iqr)
            }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
