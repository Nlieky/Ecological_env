#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常模式识别模块
功能：识别异常点位、异常时段、异常模式

基于专利文档：异常模式识别模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import welch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatternRecognizer:
    """
    异常模式识别器（专利5类异常特征）

    识别的异常模式（专利要求）：
    1. 恒定异常（平稳异常）：指标长时间保持不变
    2. 突变异常：指标突然大幅变化
    3. 趋势异常：指标呈现异常趋势
    4. 周期异常：数据呈现不自然的周期性（新增）
    5. 高频波动异常：数据出现快速波动（新增）
    """

    def __init__(self):
        """初始化异常模式识别器"""
        self.name = "异常模式识别器"
        self.version = "2.1.0"  # 专利增强版：5类异常特征

        # 模式定义（专利5类异常特征）
        self.patterns = {
            "constant": "恒定异常（平稳异常）",
            "spike": "突变异常",
            "trend": "趋势异常",
            "periodic": "周期异常",        # 新增
            "high_freq_volatility": "高频波动异常"  # 新增
        }

        # 专利参数配置
        self.periodic_params = {
            "window_size": 48,           # 周期检测窗口
            "power_ratio_threshold": 5   # 功率谱比值阈值
        }

        self.high_freq_params = {
            "window_size": 20,           # 高频波动检测窗口
            "sign_change_ratio": 0.6     # 符号变化比例阈值
        }

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 支持5类专利异常特征识别")

    def recognize_patterns(self, data: pd.DataFrame,
                          anomaly_scores: Dict[str, Any],
                          threshold: float) -> Dict[str, Any]:
        """
        识别异常模式

        Args:
            data: 输入数据
            anomaly_scores: 异常分数
            threshold: 异常阈值

        Returns:
            异常模式结果
        """
        logger.info(f"[PATTERN] 识别异常模式")

        results = {
            "anomalies": [],
            "patterns": {},
            "summary": {
                "total_anomalies": 0,
                "pattern_counts": {}
            }
        }

        # 获取异常时刻
        anomaly_moments = anomaly_scores.get("anomaly_moments", [])

        for moment in anomaly_moments:
            if moment["score"] < threshold:
                continue

            # 识别异常模式
            pattern = self._identify_pattern(data, moment)

            anomaly = {
                "indicator": moment["indicator"],
                "times": moment["times"],
                "score": moment["score"],
                "pattern": pattern,
                "severity": self._calculate_severity(moment["score"])
            }

            results["anomalies"].append(anomaly)

            # 统计模式
            results["patterns"][pattern] = results["patterns"].get(pattern, 0) + 1

        results["summary"]["total_anomalies"] = len(results["anomalies"])
        results["summary"]["pattern_counts"] = results["patterns"]

        logger.info(f"[PATTERN] 识别完成: {len(results['anomalies'])} 处异常")

        return results

    def _identify_pattern(self, data: pd.DataFrame,
                         moment: Dict[str, Any]) -> str:
        """
        识别异常模式（专利5类异常特征）

        检测顺序：
        1. 恒定异常（平稳异常）
        2. 突变异常
        3. 趋势异常
        4. 周期异常（专利新增）
        5. 高频波动异常（专利新增）
        """
        indicator = moment["indicator"]
        index = moment["index"]

        if indicator not in data.columns:
            return "unknown"

        series = data[indicator].dropna()

        if index >= len(series):
            return "unknown"

        # 1. 检查恒定异常（平稳异常）
        if self._is_constant_pattern(series, index):
            return "constant"

        # 2. 检查突变异常
        if self._is_spike_pattern(series, index):
            return "spike"

        # 3. 检查趋势异常
        if self._is_trend_pattern(series, index):
            return "trend"

        # 4. 检查周期异常（专利新增）
        if self._is_periodic_pattern(series, index):
            return "periodic"

        # 5. 检查高频波动异常（专利新增）
        if self._is_high_frequency_volatility(series, index):
            return "high_freq_volatility"

        # 默认未知
        return "unknown"

    def _is_constant_pattern(self, series: pd.Series, index: int,
                            window: int = 10) -> bool:
        """检查是否为恒定异常"""
        start = max(0, index - window)
        end = min(len(series), index + window + 1)

        window_data = series.iloc[start:end]

        # 计算标准差
        if window_data.std() < 0.01 * (abs(window_data.mean()) + 1):
            return True

        return False

    def _is_spike_pattern(self, series: pd.Series, index: int,
                         window: int = 5) -> bool:
        """检查是否为突变异常"""
        start = max(0, index - window)
        end = min(len(series), index + window + 1)

        window_data = series.iloc[start:end]
        center_value = series.iloc[index] if index < len(series) else None

        if center_value is None:
            return False

        # 计算与邻域的差异
        neighbors = window_data[window_data != center_value]

        if len(neighbors) == 0:
            return False

        mean_neighbor = neighbors.mean()
        std_neighbor = neighbors.std()

        # 如果中心值远大于邻域均值
        if abs(center_value - mean_neighbor) > 3 * std_neighbor:
            return True

        return False

    def _is_trend_pattern(self, series: pd.Series, index: int,
                         window: int = 20) -> bool:
        """检查是否为趋势异常"""
        start = max(0, index - window)
        end = min(len(series), index + window + 1)

        window_data = series.iloc[start:end].reset_index(drop=True)

        if len(window_data) < window:
            return False

        # 线性回归
        x = np.arange(len(window_data))
        z = np.polyfit(x, window_data, 1)
        slope = z[0]

        # 检查斜率是否异常
        threshold = 3 * series.std() / len(series)

        if abs(slope) > threshold:
            return True

        return False

    def _is_volatility_pattern(self, series: pd.Series, index: int,
                              window: int = 20) -> bool:
        """检查是否为波动异常"""
        start = max(0, index - window)
        end = min(len(series), index + window + 1)

        window_data = series.iloc[start:end]

        # 计算变异系数
        cv = window_data.std() / (abs(window_data.mean()) + 1e-8)

        # 检查是否异常高波动
        overall_cv = series.std() / (abs(series.mean()) + 1e-8)

        if cv > 2 * overall_cv:
            return True

        return False

    def _calculate_severity(self, score: float) -> str:
        """计算异常严重程度"""
        if score > 0.9:
            return "critical"
        elif score > 0.7:
            return "high"
        elif score > 0.5:
            return "medium"
        else:
            return "low"

    def _is_periodic_pattern(self, series: pd.Series, index: int,
                             window: int = None) -> bool:
        """
        检查周期异常（专利核心算法）

        周期异常特征：数据呈现不自然的周期性变化
        例如每N小时出现相同的峰值模式

        使用FFT（快速傅里叶变换）检测周期性

        Args:
            series: 时序数据
            index: 异常点索引
            window: 检测窗口大小

        Returns:
            是否为周期异常
        """
        window = window or self.periodic_params["window_size"]
        start = max(0, index - window)
        end = min(len(series), index + window + 1)

        window_data = series.iloc[start:end]

        if len(window_data) < window // 2:
            return False

        try:
            # 去除趋势
            detrended = window_data - window_data.mean()

            # FFT变换
            fft_vals = fft(detrended.values)
            fft_freq = fftfreq(len(detrended))

            # 获取功率谱
            power = np.abs(fft_vals) ** 2

            # 排除DC分量（频率为0的分量）
            positive_freq_idx = np.where(fft_freq > 0)[0]

            if len(positive_freq_idx) == 0:
                return False

            # 最大功率与平均功率的比值
            max_power = power[positive_freq_idx].max()
            avg_power = power[positive_freq_idx].mean()

            if avg_power < 1e-10:
                return False

            power_ratio = max_power / avg_power

            # 周期性异常判定：功率比过高表示强周期性
            if power_ratio > self.periodic_params["power_ratio_threshold"]:
                # 进一步检查周期是否合理（不自然）
                dominant_freq_idx = positive_freq_idx[np.argmax(power[positive_freq_idx])]
                dominant_freq = fft_freq[dominant_freq_idx]

                if dominant_freq != 0:
                    period_hours = 1 / abs(dominant_freq)

                    # 如果周期是整小时数（如6h、12h、24h）且数据变化很小
                    # 可能是人工周期采样
                    common_periods = [6, 8, 12, 24]
                    if period_hours in common_periods:
                        if detrended.std() < 0.1 * series.std():
                            logger.info(f"[PATTERN] 检测到周期异常: 周期={period_hours:.1f}h, 功率比={power_ratio:.1f}")
                            return True

            return False

        except Exception as e:
            logger.warning(f"[PATTERN] 周期检测失败: {e}")
            return False

    def _is_high_frequency_volatility(self, series: pd.Series, index: int,
                                      window: int = None) -> bool:
        """
        检查高频波动异常（专利核心算法）

        高频波动异常特征：数据出现不自然的快速波动
        可能是设备故障或数据传输问题

        判断逻辑：
        1. 平均变化幅度小（不是突变）
        2. 但变化频繁（标准差相对均值较大）
        3. 波动方向频繁变化

        Args:
            series: 时序数据
            index: 异常点索引
            window: 检测窗口大小

        Returns:
            是否为高频波动异常
        """
        window = window or self.high_freq_params["window_size"]
        start = max(0, index - window)
        end = min(len(series), index + window + 1)

        window_data = series.iloc[start:end]

        if len(window_data) < 10:
            return False

        # 计算一阶差分
        diffs = window_data.diff().abs().dropna()

        if len(diffs) == 0:
            return False

        # 1. 平均变化幅度
        diff_mean = diffs.mean()

        # 2. 差分标准差
        diff_std = diffs.std()

        # 3. 整体数据标准差
        series_std = series.std()

        # 高频波动判定条件：
        # a. 平均变化幅度小（不是突变）- 小于整体标准差的10%
        # b. 但变化频繁（标准差相对均值较大）- 标准差是均值的2倍以上
        condition_a = diff_mean < series_std * 0.1
        condition_b = diff_std > diff_mean * 2 if diff_mean > 1e-10 else False

        if condition_a and condition_b:
            # 4. 检查波动方向是否频繁变化
            # 计算差分符号变化次数
            sign_changes = 0
            for i in range(1, len(diffs)):
                if (diffs.iloc[i] - diffs.iloc[i-1]) * diffs.iloc[i-1] < 0:
                    sign_changes += 1

            # 符号变化比例
            sign_change_ratio = sign_changes / len(diffs) if len(diffs) > 0 else 0

            if sign_change_ratio > self.high_freq_params["sign_change_ratio"]:
                logger.info(f"[PATTERN] 检测到高频波动异常: 符号变化比={sign_change_ratio:.2f}")
                return True

        return False

    def detect_continuous_anomalies(self, anomalies: List[Dict[str, Any]],
                                   max_gap: int = 5) -> List[Dict[str, Any]]:
        """
        检测连续异常时段

        Args:
            anomalies: 异常列表
            max_gap: 最大间隔（分钟）

        Returns:
            连续异常时段列表
        """
        if not anomalies:
            return []

        # 按时间排序
        sorted_anomalies = sorted(
            anomalies,
            key=lambda x: pd.to_datetime(x["times"]) if isinstance(x["times"], str) else x["times"]
        )

        continuous_periods = []
        current_period = None

        for anomaly in sorted_anomalies:
            anomaly_time = pd.to_datetime(anomaly["times"]) if isinstance(anomaly["times"], str) else anomaly["times"]

            if current_period is None:
                current_period = {
                    "start": anomaly_time,
                    "end": anomaly_time,
                    "anomalies": [anomaly],
                    "pattern": anomaly["pattern"]
                }
            else:
                time_gap = (anomaly_time - current_period["end"]).total_seconds() / 60

                if time_gap <= max_gap:
                    # 合并到当前时段
                    current_period["end"] = anomaly_time
                    current_period["anomalies"].append(anomaly)
                else:
                    # 结束当前时段，开始新时段
                    continuous_periods.append(current_period)
                    current_period = {
                        "start": anomaly_time,
                        "end": anomaly_time,
                        "anomalies": [anomaly],
                        "pattern": anomaly["pattern"]
                    }

        if current_period:
            continuous_periods.append(current_period)

        return continuous_periods
