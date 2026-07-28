#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恒定检测器 - 检测插瓶干扰

基于专利文档：恒定检测器用于检测数据是否保持恒定或接近恒定，
这通常是"插瓶干扰"违规模式的特征。

插瓶干扰：将探头插入装有标准液的瓶中，导致读数恒定。
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ConstantDetector:
    """
    恒定检测器

    检测数据是否保持恒定或接近恒定，用于识别插瓶干扰违规。

    检测方法：
    1. 标准差检测：标准差接近0
    2. 变异系数检测：CV < 阈值
    3. 唯一值计数：唯一值数量过少
    """

    def __init__(self, std_threshold: float = 0.01, cv_threshold: float = 0.01,
                 unique_ratio_threshold: float = 0.05):
        """
        初始化恒定检测器

        Args:
            std_threshold: 标准差阈值，低于此值视为恒定
            cv_threshold: 变异系数阈值，低于此值视为恒定
            unique_ratio_threshold: 唯一值比例阈值，低于此值视为恒定
        """
        self.std_threshold = std_threshold
        self.cv_threshold = cv_threshold
        self.unique_ratio_threshold = unique_ratio_threshold
        self.name = "恒定检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测数据中的恒定模式

        Args:
            data: 输入数据序列

        Returns:
            (anomaly_mask, details): 异常掩码和详细信息
        """
        data = data.dropna()
        if len(data) < 10:
            return np.zeros(len(data)), {"error": "数据过少"}

        # 计算统计量
        data_std = data.std()
        data_mean = data.mean()
        data_cv = data_std / data_mean if data_mean != 0 else float('inf')
        unique_count = data.nunique()
        unique_ratio = unique_count / len(data)

        # 恒定判断
        is_constant_std = data_std < self.std_threshold
        is_constant_cv = data_cv < self.cv_threshold
        is_constant_unique = unique_ratio < self.unique_ratio_threshold

        # 综合判断
        is_constant = is_constant_std or is_constant_cv or is_constant_unique

        if is_constant:
            anomaly_mask = np.ones(len(data), dtype=bool)
            score = max(
                1.0 - data_std / self.std_threshold if self.std_threshold > 0 else 0,
                1.0 - data_cv / self.cv_threshold if self.cv_threshold > 0 and data_cv != float('inf') else 0,
                1.0 - unique_ratio / self.unique_ratio_threshold if self.unique_ratio_threshold > 0 else 0,
            )
            score = float(min(max(score, 0.0), 1.0))
        else:
            anomaly_mask = np.zeros(len(data), dtype=bool)
            score = 0.0

        details = {
            "feature": "平稳",
            "is_constant": bool(is_constant),
            "score": score,
            "std": float(data_std),
            "cv": float(data_cv),
            "unique_count": int(unique_count),
            "unique_ratio": float(unique_ratio),
        }
        # 不输出 violation_type —— 违规模式判定是规则推理的活
        return anomaly_mask, details

    def __call__(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        """便捷调用接口"""
        return self.detect(data)
