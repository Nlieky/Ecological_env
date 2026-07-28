#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周期检测器 - FFT 检测显著周期性成分。从 forgery_detector 拆出(原 forgery 混了周期/聚类/分布)。"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class PeriodicityDetector:
    """周期检测:FFT 检测序列中的强周期分量。"""

    def __init__(self, periodicity_threshold: float = 0.8, min_length: int = 30):
        self.periodicity_threshold = periodicity_threshold
        self.min_length = min_length
        self.name = "周期检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        data = data.dropna()
        if len(data) < self.min_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        values = data.values.astype(float)
        n = len(values)
        detrended = values - np.mean(values)
        fft_result = np.fft.fft(detrended)
        power = np.abs(fft_result[:n // 2])
        power = power / (power.sum() + 1e-10)
        max_power = float(power.max())

        is_periodic = max_power > self.periodicity_threshold
        score = float(min(max(max_power, 0.0), 1.0)) if is_periodic else 0.0

        anomaly_mask = np.ones(n, dtype=bool) if is_periodic else np.zeros(n, dtype=bool)
        details = {
            "feature": "周期",
            "is_periodic": bool(is_periodic),
            "score": score,
            "max_power": max_power,
        }
        return anomaly_mask, details

    def __call__(self, data):
        return self.detect(data)
