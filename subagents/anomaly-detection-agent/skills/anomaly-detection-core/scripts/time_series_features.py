#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时序特征提取模块
功能：提取波动、趋势、突变特征

基于专利文档：时序特征提取模块
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeSeriesFeatureExtractor:
    """
    时序特征提取器

    提取的特征类型：
    1. 统计特征：均值、方差、偏度、峰度
    2. 波动特征：标准差、变异系数、波动范围
    3. 趋势特征：斜率、变化率、趋势强度
    4. 突变特征：突变点、突变幅度、突变频率
    """

    def __init__(self):
        """初始化时序特征提取器"""
        self.name = "时序特征提取器"
        self.version = "2.0.0"

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def extract(self, df: pd.DataFrame, indicators: List[str],
                window: int = 10) -> pd.DataFrame:
        """
        提取时序特征

        Args:
            df: 输入数据
            indicators: 指标列表
            window: 滑动窗口大小

        Returns:
            特征数据框
        """
        logger.info(f"[EXTRACT] 提取时序特征，窗口: {window}")

        features = []

        # 按时间窗口提取特征
        for i in range(window, len(df), window):
            window_data = df.iloc[i-window:i]

            window_features = {
                "times": df.iloc[i]["times"] if "times" in df.columns else i,
                "window_start": i - window,
                "window_end": i
            }

            # 对每个指标提取特征
            for indicator in indicators:
                if indicator not in df.columns:
                    continue

                series = window_data[indicator].dropna()

                if len(series) == 0:
                    continue

                # 统计特征
                indicator_features = self._extract_statistical_features(
                    series, indicator
                )

                # 波动特征
                indicator_features.update(self._extract_volatility_features(
                    series, indicator
                ))

                # 趋势特征
                indicator_features.update(self._extract_trend_features(
                    series, indicator
                ))

                # 突变特征
                indicator_features.update(self._extract_change_features(
                    series, indicator
                ))

                window_features.update(indicator_features)

            features.append(window_features)

        features_df = pd.DataFrame(features)

        logger.info(f"[EXTRACT] 提取完成: {len(features_df)} 个时间窗口")

        return features_df

    def _extract_statistical_features(self, series: pd.Series,
                                     prefix: str) -> Dict[str, float]:
        """提取统计特征"""
        features = {}

        try:
            features[f"{prefix}_mean"] = series.mean()
            features[f"{prefix}_std"] = series.std()
            features[f"{prefix}_min"] = series.min()
            features[f"{prefix}_max"] = series.max()
            features[f"{prefix}_median"] = series.median()

            # 偏度和峰度
            if len(series) > 3:
                features[f"{prefix}_skewness"] = stats.skew(series)
                features[f"{prefix}_kurtosis"] = stats.kurtosis(series)

        except Exception as e:
            logger.warning(f"[EXTRACT] 统计特征提取失败 {prefix}: {e}")

        return features

    def _extract_volatility_features(self, series: pd.Series,
                                     prefix: str) -> Dict[str, float]:
        """提取波动特征"""
        features = {}

        try:
            # 变异系数
            if series.mean() != 0:
                features[f"{prefix}_cv"] = series.std() / abs(series.mean())
            else:
                features[f"{prefix}_cv"] = 0

            # 波动范围
            features[f"{prefix}_range"] = series.max() - series.min()

            # 四分位距
            q75 = series.quantile(0.75)
            q25 = series.quantile(0.25)
            features[f"{prefix}_iqr"] = q75 - q25

        except Exception as e:
            logger.warning(f"[EXTRACT] 波动特征提取失败 {prefix}: {e}")

        return features

    def _extract_trend_features(self, series: pd.Series,
                               prefix: str) -> Dict[str, float]:
        """提取趋势特征"""
        features = {}

        try:
            # 线性趋势（斜率）
            x = np.arange(len(series))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, series.values)

            features[f"{prefix}_trend_slope"] = slope
            features[f"{prefix}_trend_r2"] = r_value ** 2
            features[f"{prefix}_trend_pvalue"] = p_value

            # 变化率
            if len(series) > 1:
                features[f"{prefix}_change_rate"] = (
                    (series.iloc[-1] - series.iloc[0]) / series.iloc[0]
                    if series.iloc[0] != 0 else 0
                )

        except Exception as e:
            logger.warning(f"[EXTRACT] 趋势特征提取失败 {prefix}: {e}")

        return features

    def _extract_change_features(self, series: pd.Series,
                                prefix: str) -> Dict[str, float]:
        """提取突变特征"""
        features = {}

        try:
            # 计算差分
            diff = series.diff().abs()

            # 突变阈值（3倍标准差）
            threshold = diff.mean() + 3 * diff.std()

            # 突变点数量
            change_points = (diff > threshold).sum()
            features[f"{prefix}_change_points"] = change_points

            # 突变幅度
            features[f"{prefix}_max_change"] = diff.max()
            features[f"{prefix}_mean_change"] = diff.mean()

            # 突变频率
            features[f"{prefix}_change_frequency"] = change_points / len(series)

        except Exception as e:
            logger.warning(f"[EXTRACT] 突变特征提取失败 {prefix}: {e}")

        return features


# 入口函数 - 执行控制模块调用
def main(data: Optional[Dict[str, Any]] = None,
         indicators: Optional[List[str]] = None,
         window: int = 30,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 时序特征提取

    Args:
        data: 数据字典（包含 values）
        indicators: 指标列表
        window: 滑动窗口大小
        **kwargs: 其他参数

    Returns:
        时序特征提取结果
    """
    if not data:
        return {
            "status": "error",
            "error": "No data provided",
            "features": []
        }

    try:
        import pandas as pd

        # 转换为数据框格式
        values = data.get("values", {})
        if not values:
            return {
                "status": "error",
                "error": "No values in data",
                "features": []
            }

        df = pd.DataFrame(values)

        # 如果没有指定指标，使用所有列
        if not indicators:
            indicators = list(df.columns)

        # 创建分析器并提取特征
        extractor = TimeSeriesFeatureExtractor()
        result_df = extractor.extract(df, indicators, window=window)

        return {
            "status": "success",
            "features": result_df.to_dict("records"),
            "feature_count": len(result_df),
            "indicators": indicators,
            "window_size": window
        }

    except Exception as e:
        logger.error(f"[EXTRACT] 时序特征提取失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "features": []
        }


def process(data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(data=data, **kwargs)
