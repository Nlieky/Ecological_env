#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指标相关性分析模块
功能：计算多指标关联关系

基于专利文档：指标相关性分析模块
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import correlate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    相关性分析器

    支持的相关性分析方法：
    1. Pearson相关系数（线性相关）
    2. Spearman相关系数（单调相关）
    3. Kendall相关系数（秩相关）
    4. 交叉相关（滞后相关）
    """

    def __init__(self):
        """初始化相关性分析器"""
        self.name = "相关性分析器"
        self.version = "2.0.0"

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def analyze(self, df: pd.DataFrame, indicators: List[str]) -> Dict[str, Any]:
        """
        分析指标相关性

        Args:
            df: 输入数据
            indicators: 指标列表

        Returns:
            相关性分析结果
        """
        logger.info(f"[CORRELATION] 分析指标相关性")

        results = {
            "pairs": [],
            "matrix": {},
            "summary": {
                "total_pairs": 0,
                "high_correlation": 0,
                "moderate_correlation": 0,
                "low_correlation": 0
            }
        }

        # 获取有效指标
        valid_indicators = [col for col in indicators if col in df.columns]

        # 计算所有指标对的相关性
        for i, ind1 in enumerate(valid_indicators):
            for j, ind2 in enumerate(valid_indicators):
                if i >= j:  # 避免重复计算
                    continue

                pair_result = self._analyze_pair(
                    df, ind1, ind2
                )
                results["pairs"].append(pair_result)

                # 更新统计
                abs_corr = abs(pair_result["pearson"])
                if abs_corr > 0.7:
                    results["summary"]["high_correlation"] += 1
                elif abs_corr > 0.3:
                    results["summary"]["moderate_correlation"] += 1
                else:
                    results["summary"]["low_correlation"] += 1

        results["summary"]["total_pairs"] = len(results["pairs"])

        # 计算相关矩阵
        results["matrix"]["pearson"] = self._compute_correlation_matrix(
            df, valid_indicators, "pearson"
        )
        results["matrix"]["spearman"] = self._compute_correlation_matrix(
            df, valid_indicators, "spearman"
        )

        logger.info(f"[CORRELATION] 分析完成: {results['summary']['total_pairs']} 对指标")

        return results

    def _analyze_pair(self, df: pd.DataFrame, ind1: str, ind2: str) -> Dict[str, Any]:
        """分析单个指标对"""
        series1 = df[ind1].dropna()
        series2 = df[ind2].dropna()

        # 对齐长度
        min_len = min(len(series1), len(series2))
        series1 = series1.iloc[:min_len]
        series2 = series2.iloc[:min_len]

        result = {
            "indicator1": ind1,
            "indicator2": ind2,
            "pearson": 0.0,
            "spearman": 0.0,
            "kendall": 0.0,
            "p_value": 1.0,
            "lag_correlation": {},
            "interpretation": ""
        }

        try:
            # Pearson相关系数
            pearson_corr, pearson_p = stats.pearsonr(series1, series2)
            result["pearson"] = round(pearson_corr, 4)
            result["p_value"] = round(pearson_p, 4)

            # Spearman相关系数
            spearman_corr, spearman_p = stats.spearmanr(series1, series2)
            result["spearman"] = round(spearman_corr, 4)

            # Kendall相关系数
            kendall_corr, kendall_p = stats.kendalltau(series1, series2)
            result["kendall"] = round(kendall_corr, 4)

            # 滞后相关（最多±10个周期）
            lag_corrs = []
            for lag in range(-10, 11):
                if lag == 0:
                    continue

                if lag > 0:
                    s1 = series1.iloc[lag:]
                    s2 = series2.iloc[:-lag]
                else:
                    s1 = series1.iloc[:lag]
                    s2 = series2.iloc[-lag:]

                if len(s1) > 0 and len(s2) > 0:
                    corr, _ = stats.pearsonr(s1, s2)
                    lag_corrs.append({"lag": lag, "correlation": corr})

            # 找到最大滞后的相关性
            if lag_corrs:
                max_lag_corr = max(lag_corrs, key=lambda x: abs(x["correlation"]))
                result["lag_correlation"] = max_lag_corr

            # 解释
            result["interpretation"] = self._interpret_correlation(
                result["pearson"], result["p_value"]
            )

        except Exception as e:
            logger.warning(f"[CORRELATION] 指标对分析失败 {ind1}-{ind2}: {e}")

        return result

    def _compute_correlation_matrix(self, df: pd.DataFrame,
                                   indicators: List[str],
                                   method: str = "pearson") -> pd.DataFrame:
        """计算相关矩阵"""
        data = df[indicators].dropna()

        if method == "pearson":
            matrix = data.corr(method="pearson")
        elif method == "spearman":
            matrix = data.corr(method="spearman")
        else:
            matrix = data.corr(method="kendall")

        return matrix.round(4)

    def _interpret_correlation(self, corr: float, p_value: float) -> str:
        """解释相关性"""
        if p_value > 0.05:
            return "不显著"

        abs_corr = abs(corr)
        if abs_corr > 0.8:
            direction = "正" if corr > 0 else "负"
            return f"强{direction}相关"
        elif abs_corr > 0.5:
            direction = "正" if corr > 0 else "负"
            return f"中等{direction}相关"
        elif abs_corr > 0.3:
            direction = "正" if corr > 0 else "负"
            return f"弱{direction}相关"
        else:
            return "几乎无关"


# 入口函数 - 执行控制模块调用
def main(data: Optional[Dict[str, Any]] = None,
         indicators: Optional[List[str]] = None,
         task: Optional[Dict[str, Any]] = None,
         influent: Optional[Dict[str, Any]] = None,
         effluent: Optional[Dict[str, Any]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 相关性分析

    Args:
        data: 数据字典（包含 values）
        indicators: 指标列表
        task: 任务字典
        influent: 进水数据
        effluent: 出水数据
        **kwargs: 其他参数

    Returns:
        相关性分析结果
    """
    # 如果没有提供 data，从 influent/effluent 构建
    if not data:
        data = {}
        values = {}

        # 合并进水和出水数据
        if influent:
            for key, val in influent.items():
                if key not in ["timestamp", "监测时间", "timestamp"]:
                    values[f"influent_{key}"] = [float(val) if isinstance(val, (int, float)) else 0.0]

        if effluent:
            for key, val in effluent.items():
                if key not in ["timestamp", "监测时间", "timestamp"]:
                    values[f"effluent_{key}"] = [float(val) if isinstance(val, (int, float)) else 0.0]

        data["values"] = values

    # 如果没有提供指标列表，从数据中提取
    if not indicators:
        indicators = list(data.get("values", {}).keys())

    # 创建数据框
    df_data = data.get("values", {})
    if df_data:
        # 转换为数据框格式
        df = pd.DataFrame(df_data)

        # 创建分析器并分析
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(df, indicators)

        # 转换矩阵为字典格式
        result["matrix"] = {
            "pearson": result["matrix"]["pearson"].to_dict() if hasattr(result["matrix"]["pearson"], 'to_dict') else {},
            "spearman": result["matrix"]["spearman"].to_dict() if hasattr(result["matrix"]["spearman"], 'to_dict') else {}
        }

        result["status"] = "success"
    else:
        result = {
            "status": "error",
            "error": "No data provided",
            "pairs": [],
            "summary": {"total_pairs": 0}
        }

    return result


def process(data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(data=data, **kwargs)
