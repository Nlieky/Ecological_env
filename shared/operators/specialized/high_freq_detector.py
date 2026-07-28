#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高频波动检测器 - 分钟级突升突降、异常归零。资料定义的高频波动异常特征。"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class HighFreqDetector:
    """高频波动:相邻点差分大且频繁(突升突降),或出现异常归零。"""

    def __init__(self, diff_threshold: float = 3.0, freq_ratio_threshold: float = 0.3,
                 min_length: int = 8):
        self.diff_threshold = diff_threshold
        self.freq_ratio_threshold = freq_ratio_threshold
        self.min_length = min_length
        self.name = "高频波动检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        data = data.dropna()
        if len(data) < self.min_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        values = data.values.astype(float)
        n = len(values)
        data_std = float(np.std(values))
        if data_std < 1e-9:
            return np.zeros(n), {"feature": "高频波动", "is_high_freq": False, "score": 0.0}

        diffs = np.abs(np.diff(values))
        normalized_diffs = diffs / data_std
        spike_mask = normalized_diffs > self.diff_threshold
        zero_mask = np.abs(values) < data_std * 0.05

        freq_ratio = float(spike_mask.sum() / n)
        zero_ratio = float(zero_mask.sum() / n)
        is_high_freq = (freq_ratio > self.freq_ratio_threshold) or (zero_ratio > 0.3)

        score = float(min(max(max(freq_ratio, zero_ratio), 0.0), 1.0)) if is_high_freq else 0.0

        anomaly_mask = np.zeros(n, dtype=bool)
        anomaly_mask[1:][spike_mask] = True
        anomaly_mask[zero_mask] = True

        details = {
            "feature": "高频波动",
            "is_high_freq": bool(is_high_freq),
            "score": score,
            "freq_ratio": freq_ratio,
            "zero_ratio": zero_ratio,
        }
        return anomaly_mask, details

    def __call__(self, data):
        return self.detect(data)
