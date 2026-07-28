#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""趋势检测器 - 检测单向均匀上升/下降(二阶导≈0)。资料定义的趋势异常特征。"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class TrendDetector:
    """趋势检测器:序列呈单向均匀升降(线性,二阶导接近 0)。"""

    def __init__(self, min_slope_ratio: float = 0.1, min_length: int = 10):
        self.min_slope_ratio = min_slope_ratio
        self.min_length = min_length
        self.name = "趋势检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        data = data.dropna()
        if len(data) < self.min_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        values = data.values.astype(float)
        n = len(values)
        x = np.arange(n)

        slope, intercept = np.polyfit(x, values, 1)
        fitted = slope * x + intercept
        residuals = values - fitted

        data_std = float(np.std(values))
        slope_ratio = abs(slope) / (data_std + 1e-9) if data_std > 1e-9 else 0.0

        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((values - values.mean()) ** 2)) + 1e-9
        r_squared = 1 - ss_res / ss_tot

        is_trend = r_squared > 0.8 and slope_ratio > self.min_slope_ratio
        score = float(min(max(r_squared * min(slope_ratio, 1.0), 0.0), 1.0)) if is_trend else 0.0
        direction = "上升" if slope > 0 else "下降"

        anomaly_mask = np.ones(n, dtype=bool) if is_trend else np.zeros(n, dtype=bool)
        details = {
            "feature": "趋势",
            "is_trend": bool(is_trend),
            "score": score,
            "slope": float(slope),
            "direction": direction,
            "r_squared": float(r_squared),
        }
        return anomaly_mask, details

    def __call__(self, data):
        return self.detect(data)
