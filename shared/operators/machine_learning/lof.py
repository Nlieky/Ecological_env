#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
局部异常因子 (LOF) 异常检测器

使用局部异常因子进行异常检测。
LOF 通过比较数据点与其邻居的局部密度来识别异常。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class LOFDetector:
    """
    局部异常因子异常检测器

    LOF 通过计算数据点的局部可达密度与其邻居的局部可达密度之比来识别异常。
    LOF > 1 表示异常，值越大表示越异常。

    参数：
    - n_neighbors: 邻居数量
    - contamination: 预期异常比例
    """

    def __init__(self, n_neighbors: int = 20, contamination: float = 0.1):
        """
        初始化 LOF 检测器

        Args:
            n_neighbors: 邻居数量
            contamination: 预期异常比例
        """
        self.n_neighbors = n_neighbors
        self.contamination = contamination
        self.name = "局部异常因子"
        self.is_fitted = False

        # 尝试导入 sklearn
        try:
            from sklearn.neighbors import LocalOutlierFactor
            self.sklearn_available = True
            self.model = LocalOutlierFactor(
                n_neighbors=n_neighbors,
                contamination=contamination,
                novelty=True
            )
        except ImportError:
            self.sklearn_available = False
            logger.warning("[LOF] sklearn 不可用，使用简化版本")

    def fit(self, data: pd.Series) -> None:
        """
        训练模型

        Args:
            data: 训练数据
        """
        data = data.dropna()
        if len(data) < self.n_neighbors * 2:
            logger.warning("[LOF] 数据过少，无法训练")
            return

        if self.sklearn_available:
            # sklearn 实现
            X = data.values.reshape(-1, 1)
            self.model.fit(X)
            self.is_fitted = True
            logger.info("[LOF] 模型训练完成")
        else:
            # 简化版本：计算统计特征
            self.data_median = data.median()
            self.data_mad = np.median(np.abs(data - self.data_median))  # 中位数绝对偏差
            self.is_fitted = True
            logger.info("[LOF] 简化模型训练完成")

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
            scores = self.model.score_samples(X)  # LOF 分数的负数

            # -1 表示异常
            anomaly_mask = predictions == -1

            details = {
                "anomaly_count": int(anomaly_mask.sum()),
                "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask)),
                "mean_lof": float(-scores.mean()),  # 转换为正值
                "max_lof": float(-scores.max()),
                "n_neighbors": self.n_neighbors
            }
        else:
            # 简化版本：使用修正 Z-score
            modified_z_scores = 0.6745 * (data - self.data_median) / self.data_mad
            anomaly_mask = np.abs(modified_z_scores) > 3.5

            details = {
                "anomaly_count": int(anomaly_mask.sum()),
                "anomaly_rate": float(anomaly_mask.sum() / len(data)),
                "median": float(self.data_median),
                "mad": float(self.data_mad),
                "max_modified_z": float(np.abs(modified_z_scores).max())
            }

        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
