#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势与滞后分析模块
功能：分析时序变化规律与滞后关系

基于专利文档：趋势与滞后分析模块
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import correlate, correlation_lags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    趋势与滞后分析器

    功能：
    1. 趋势识别（上升、下降、平稳）
    2. 趋势强度评估
    3. 滞后关系分析
    4. 因果推断
    """

    def __init__(self):
        """初始化趋势分析器"""
        self.name = "趋势分析器"
        self.version = "2.0.0"

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def analyze(self, df: pd.DataFrame, indicators: List[str]) -> Dict[str, Any]:
        """
        分析趋势与滞后关系

        Args:
            df: 输入数据
            indicators: 指标列表

        Returns:
            趋势分析结果
        """
        logger.info(f"[TREND] 分析趋势与滞后关系")

        results = {
            "trends": {},
            "lag_relationships": [],
            "summary": {
                "rising": 0,
                "falling": 0,
                "stable": 0
            }
        }

        valid_indicators = [col for col in indicators if col in df.columns]

        # 分析各指标趋势
        for indicator in valid_indicators:
            trend_result = self._analyze_indicator_trend(df, indicator)
            results["trends"][indicator] = trend_result

            # 更新统计
            if trend_result["direction"] == "rising":
                results["summary"]["rising"] += 1
            elif trend_result["direction"] == "falling":
                results["summary"]["falling"] += 1
            else:
                results["summary"]["stable"] += 1

        # 分析指标间的滞后关系
        for i, ind1 in enumerate(valid_indicators):
            for j, ind2 in enumerate(valid_indicators):
                if i >= j:
                    continue

                lag_result = self._analyze_lag_relationship(df, ind1, ind2)
                if lag_result["lag_hours"] > 0:
                    results["lag_relationships"].append(lag_result)

        logger.info(f"[TREND] 分析完成")

        return results

    def _analyze_indicator_trend(self, df: pd.DataFrame,
                                indicator: str) -> Dict[str, Any]:
        """分析单个指标的趋势"""
        series = df[indicator].dropna()

        if len(series) < 3:
            return {
                "indicator": indicator,
                "direction": "unknown",
                "strength": 0.0,
                "confidence": 0.0
            }

        result = {"indicator": indicator}

        try:
            # 线性回归分析
            x = np.arange(len(series))
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                x, series.values
            )

            # 判断趋势方向
            if p_value < 0.05:  # 显著性检验
                if slope > 0:
                    result["direction"] = "rising"
                else:
                    result["direction"] = "falling"
            else:
                result["direction"] = "stable"

            # 趋势强度（R²）
            result["strength"] = round(r_value ** 2, 4)
            result["confidence"] = round(1 - p_value, 4)

            # 趋势斜率
            result["slope"] = round(slope, 6)

            # Mann-Kendall趋势检验
            mk_result = self._mann_kendall_test(series.values)
            result["mann_kendall"] = mk_result

        except Exception as e:
            logger.warning(f"[TREND] 趋势分析失败 {indicator}: {e}")
            result.update({
                "direction": "unknown",
                "strength": 0.0,
                "confidence": 0.0
            })

        return result

    def _analyze_lag_relationship(self, df: pd.DataFrame,
                                  ind1: str, ind2: str) -> Dict[str, Any]:
        """分析两个指标间的滞后关系"""
        series1 = df[ind1].dropna().values
        series2 = df[ind2].dropna().values

        result = {
            "indicator1": ind1,
            "indicator2": ind2,
            "lag_hours": 0.0,
            "correlation": 0.0,
            "direction": ""
        }

        try:
            # 标准化
            s1 = (series1 - np.mean(series1)) / (np.std(series1) + 1e-8)
            s2 = (series2 - np.mean(series2)) / (np.std(series2) + 1e-8)

            # 互相关分析
            correlation = correlate(s1, s2, mode='full')
            lags = correlation_lags(len(s1), len(s2))

            # 找到最大相关性
            max_idx = np.argmax(np.abs(correlation))
            max_lag = lags[max_idx]
            max_corr = correlation[max_idx] / max(len(s1), len(s2))

            # 转换为小时（假设5分钟间隔）
            result["lag_hours"] = round(abs(max_lag) * 5 / 60, 2)
            result["lag_steps"] = int(max_lag)
            result["correlation"] = round(max_corr, 4)

            # 判断方向
            if max_lag > 0:
                result["direction"] = f"{ind1} 领先 {ind2}"
            elif max_lag < 0:
                result["direction"] = f"{ind2} 领先 {ind1}"
            else:
                result["direction"] = "同步"

        except Exception as e:
            logger.warning(f"[TREND] 滞后分析失败 {ind1}-{ind2}: {e}")

        return result

    def _mann_kendall_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Mann-Kendall趋势检验"""
        n = len(data)

        # 计算S统计量
        S = 0
        for i in range(n - 1):
            for j in range(i + 1, n):
                if data[j] > data[i]:
                    S += 1
                elif data[j] < data[i]:
                    S -= 1

        # 计算方差
        var_S = n * (n - 1) * (2 * n + 5) / 18

        # 计算Z统计量
        if S > 0:
            Z = (S - 1) / np.sqrt(var_S)
        elif S < 0:
            Z = (S + 1) / np.sqrt(var_S)
        else:
            Z = 0

        # 计算p值（双尾检验）
        p_value = 2 * (1 - stats.norm.cdf(abs(Z)))

        # 判断趋势
        if p_value < 0.05:
            if Z > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
        else:
            trend = "no_trend"

        return {
            "S": S,
            "Z": round(Z, 4),
            "p_value": round(p_value, 4),
            "trend": trend
        }

    def detect_change_points(self, series: pd.Series,
                            min_size: int = 10) -> List[Dict[str, Any]]:
        """
        检测变点（突变点）

        Args:
            series: 时间序列
            min_size: 最小分段大小

        Returns:
            变点列表
        """
        change_points = []

        try:
            from ruptures import Pelt
            import ruptures as rpt

            # 使用PELT算法检测变点
            algo = Pelt(model="rbf").fit(series.values)
            result = algo.predict(pen=10)

            # 过滤太靠近的变点
            filtered_points = []
            for i, point in enumerate(result[:-1]):
                if i == 0 or point - filtered_points[-1]["index"] >= min_size:
                    filtered_points.append({
                        "index": point,
                        "value": series.iloc[point] if point < len(series) else None
                    })

            change_points = filtered_points

        except ImportError:
            logger.warning("[TREND] ruptures库未安装，使用简单变点检测")
            # 简单变点检测：基于均值变化
            mean_val = series.mean()
            std_val = series.std()

            for i in range(min_size, len(series) - min_size):
                before_mean = series.iloc[:i].mean()
                after_mean = series.iloc[i:].mean()

                if abs(after_mean - before_mean) > 2 * std_val:
                    change_points.append({
                        "index": i,
                        "value": series.iloc[i]
                    })
        except Exception as e:
            logger.warning(f"[TREND] 变点检测失败: {e}")

        return change_points


# 入口函数 - 执行控制模块调用
def main(data: Optional[Dict[str, Any]] = None,
         indicators: Optional[List[str]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 趋势与滞后分析

    Args:
        data: 数据字典（包含 values）
        indicators: 指标列表
        **kwargs: 其他参数

    Returns:
        趋势与滞后分析结果
    """
    if not data:
        return {
            "status": "error",
            "error": "No data provided",
            "trends": {},
            "lag_relationships": []
        }

    try:
        import pandas as pd

        # 转换为数据框格式
        values = data.get("values", {})
        if not values:
            return {
                "status": "error",
                "error": "No values in data",
                "trends": {},
                "lag_relationships": []
            }

        df = pd.DataFrame(values)

        # 如果没有指定指标，使用所有列
        if not indicators:
            indicators = list(df.columns)

        # 创建分析器并分析
        analyzer = TrendAnalyzer()
        result = analyzer.analyze(df, indicators)

        result["status"] = "success"
        result["indicators"] = indicators

        return result

    except Exception as e:
        logger.error(f"[TREND] 趋势分析失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "trends": {},
            "lag_relationships": []
        }


def process(data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(data=data, **kwargs)
