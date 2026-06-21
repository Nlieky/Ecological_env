#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鲁棒参数估计模块

功能：
1. 迭代鲁棒估计：先用鲁棒方法去掉明显异常，再用正常数据估计
2. 基于数据特征自适应选择方法
3. 支持多种鲁棒估计方法（MAD、IQR、迭代法）

参考项目：E:/project/PolutionMonitoring/anomaly_detection_analysis.py
"""

import logging
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RobustParameterEstimator:
    """
    鲁棒参数估计器

    核心思想：只用"正常"数据估计参数，避免异常值对参数估计的影响
    """

    def __init__(self):
        """初始化鲁棒参数估计器"""
        self.name = "鲁棒参数估计器"
        self.version = "1.0.0"
        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def analyze_distribution(self, data: pd.Series) -> Dict[str, Any]:
        """
        分析数据分布特征

        Args:
            data: 输入数据序列

        Returns:
            分布特征字典
        """
        data_clean = data.dropna()
        if len(data_clean) < 10:
            return {
                "is_normal": True,
                "skewness": 0,
                "kurtosis": 0,
                "recommendation": "sample_too_small"
            }

        # 基本统计
        mean_val = data_clean.mean()
        std_val = data_clean.std()
        median_val = data_clean.median()

        # 偏度和峰度
        skewness = stats.skew(data_clean)
        kurtosis = stats.kurtosis(data_clean)

        # 正态性检验（Shapiro-Wilk，只取前5000个样本）
        sample_size = min(5000, len(data_clean))
        _, p_value = stats.shapiro(data_clean.sample(sample_size))
        is_normal = p_value > 0.05

        # IQR
        q1 = data_clean.quantile(0.25)
        q3 = data_clean.quantile(0.75)
        iqr = q3 - q1

        # 推荐方法
        if is_normal and abs(skewness) < 0.5:
            recommendation = "zscore"  # 正态分布，适合均值-标准差方法
        else:
            recommendation = "iqr"  # 偏态分布，适合分位数方法

        return {
            "mean": mean_val,
            "median": median_val,
            "std": std_val,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "is_normal": is_normal,
            "p_value": p_value,
            "recommendation": recommendation,
            "sample_size": len(data_clean)
        }

    def iterative_robust_estimate(self, data: pd.Series,
                                  method: str = "mad",
                                  max_iterations: int = 1) -> Dict[str, Any]:
        """
        迭代鲁棒参数估计

        策略：
        1. 使用鲁棒方法（MAD或IQR）初步检测异常
        2. 去掉异常值
        3. 用剩余"正常"数据重新估计参数
        4. 可选：迭代多次

        注意：max_iterations=1 是默认值，避免过度过滤正常数据波动
        多次迭代可能导致将正常的日内波动误判为异常

        Args:
            data: 输入数据序列
            method: 初步检测方法 ("mad" 或 "iqr")
            max_iterations: 最大迭代次数（默认1，避免过度过滤）

        Returns:
            鲁棒估计参数字典
        """
        data_clean = data.dropna()
        if len(data_clean) < 10:
            # 数据量太小，返回基本统计
            return {
                "mean": data_clean.mean(),
                "std": data_clean.std(),
                "median": data_clean.median(),
                "method": "basic",
                "iterations": 0,
                "outliers_removed": 0
            }

        logger.info(f"[ROBUST] 开始迭代鲁棒估计，方法={method}，初始数据量={len(data_clean)}")

        current_data = data_clean.copy()
        total_removed = 0

        for iteration in range(max_iterations):
            # 使用鲁棒方法检测异常
            if method == "mad":
                median = current_data.median()
                mad = np.median(np.abs(current_data - median))
                sigma = 1.4826 * mad

                # 3倍MAD阈值
                lower_bound = median - 3 * sigma
                upper_bound = median + 3 * sigma

                normal_mask = (current_data >= lower_bound) & (current_data <= upper_bound)

            elif method == "iqr":
                q1 = current_data.quantile(0.25)
                q3 = current_data.quantile(0.75)
                iqr = q3 - q1

                # 3倍IQR阈值（保守）
                lower_bound = q1 - 3 * iqr
                upper_bound = q3 + 3 * iqr

                normal_mask = (current_data >= lower_bound) & (current_data <= upper_bound)
            else:
                raise ValueError(f"Unknown method: {method}")

            removed_count = (~normal_mask).sum()
            total_removed += removed_count

            # 如果没有异常点被移除，停止迭代
            if removed_count == 0:
                logger.info(f"[ROBUST] 迭代{iteration + 1}: 无异常点，停止迭代")
                break

            logger.info(f"[ROBUST] 迭代{iteration + 1}: 移除{removed_count}个异常点")

            # 更新数据为正常数据
            current_data = current_data[normal_mask]

            # 如果数据量太小，停止迭代
            if len(current_data) < 10:
                logger.warning(f"[ROBUST] 剩余数据量过小({len(current_data)})，停止迭代")
                break

        # 用"正常"数据估计参数
        clean_mean = current_data.mean()
        clean_std = current_data.std()
        clean_median = current_data.median()

        # 同时计算IQR
        clean_q1 = current_data.quantile(0.25)
        clean_q3 = current_data.quantile(0.75)
        clean_iqr = clean_q3 - clean_q1

        logger.info(f"[ROBUST] 迭代完成: 最终{len(current_data)}条正常数据，移除{total_removed}个异常点")

        return {
            "mean": clean_mean,
            "std": clean_std,
            "median": clean_median,
            "q1": clean_q1,
            "q3": clean_q3,
            "iqr": clean_iqr,
            "lower_bound_3sigma": clean_mean - 3 * clean_std,
            "upper_bound_3sigma": clean_mean + 3 * clean_std,
            "lower_bound_1.5iqr": clean_q1 - 1.5 * clean_iqr,
            "upper_bound_1.5iqr": clean_q3 + 1.5 * clean_iqr,
            "lower_bound_3iqr": clean_q1 - 3 * clean_iqr,
            "upper_bound_3iqr": clean_q3 + 3 * clean_iqr,
            "method": f"iterative_{method}",
            "iterations": iteration + 1,
            "outliers_removed": total_removed,
            "normal_data_count": len(current_data)
        }

    def mad_estimate(self, data: pd.Series, threshold: float = 3.0) -> Dict[str, Any]:
        """
        基于MAD的参数估计（Hampel Filter方法）

        Args:
            data: 输入数据序列
            threshold: 异常阈值（倍数）

        Returns:
            估计参数字典
        """
        data_clean = data.dropna()
        median = data_clean.median()
        mad = np.median(np.abs(data_clean - median))

        # MAD到标准差的转换因子（正态分布下）
        sigma = 1.4826 * mad

        return {
            "median": median,
            "mad": mad,
            "sigma": sigma,
            "lower_bound": median - threshold * sigma,
            "upper_bound": median + threshold * sigma,
            "method": "mad"
        }

    def percentile_based_estimate(self, data: pd.Series,
                                normal_percentile: float = 0.90) -> Dict[str, Any]:
        """
        基于百分位的参数估计

        只用中间X%的数据估计参数，避免极端值影响

        Args:
            data: 输入数据序列
            normal_percentile: 正常数据百分位范围（默认90%，即去掉前5%和后5%）

        Returns:
            估计参数字典
        """
        data_clean = data.dropna()

        # 计算百分位边界
        lower_percentile = (1 - normal_percentile) / 2
        upper_percentile = 1 - lower_percentile

        lower_bound = data_clean.quantile(lower_percentile)
        upper_bound = data_clean.quantile(upper_percentile)

        # 只用"正常"范围的数据
        normal_data = data_clean[(data_clean >= lower_bound) & (data_clean <= upper_bound)]

        if len(normal_data) < 10:
            # 正常数据太少，使用全部数据
            normal_data = data_clean

        mean = normal_data.mean()
        std = normal_data.std()
        median = normal_data.median()

        return {
            "mean": mean,
            "std": std,
            "median": median,
            "lower_percentile": lower_bound,
            "upper_percentile": upper_bound,
            "normal_data_count": len(normal_data),
            "normal_percentile": normal_percentile,
            "method": "percentile"
        }

    def recommend_method(self, data: pd.Series) -> str:
        """
        基于数据特征推荐最佳异常检测方法

        Args:
            data: 输入数据序列

        Returns:
            推荐的方法名称
        """
        dist = self.analyze_distribution(data)

        if dist.get("recommendation") == "sample_too_small":
            return "hampel"  # 数据量小时，Hampel更鲁棒

        # 根据数据特征推荐
        if dist["is_normal"] and abs(dist["skewness"]) < 0.5:
            # 正态分布，轻微偏态
            return "zscore_robust"  # 使用鲁棒估计的Z-score
        elif dist["skewness"] > 1 or dist["kurtosis"] > 3:
            # 高度偏态或尖峰
            return "iqr_conservative"  # 使用保守IQR
        else:
            # 一般情况
            return "hampel"  # Hampel Filter是通用鲁棒方法

    def get_adaptive_parameters(self, data: pd.Series,
                               method: Optional[str] = None) -> Dict[str, Any]:
        """
        获取自适应参数

        Args:
            data: 输入数据序列
            method: 指定方法（如果为None则自动推荐）

        Returns:
            自适应参数字典
        """
        if method is None:
            method = self.recommend_method(data)

        logger.info(f"[ROBUST] 使用方法: {method}")

        if method == "hampel":
            params = self.mad_estimate(data)
        elif method == "iqr_conservative":
            params = self.iterative_robust_estimate(data, method="iqr")
        elif method == "zscore_robust":
            params = self.iterative_robust_estimate(data, method="mad")
        elif method == "percentile":
            params = self.percentile_based_estimate(data)
        else:
            # 默认使用迭代MAD方法
            params = self.iterative_robust_estimate(data, method="mad")

        # 添加推荐方法
        params["recommended_method"] = method

        return params


# 便捷函数
def estimate_robust_parameters(data: pd.Series,
                              method: str = "auto") -> Dict[str, Any]:
    """
    便捷的鲁棒参数估计函数

    Args:
        data: 输入数据序列
        method: 估计方法 ("auto", "mad", "iqr", "iterative_mad", "iterative_iqr", "percentile")

    Returns:
        估计参数字典
    """
    estimator = RobustParameterEstimator()

    if method == "auto":
        return estimator.get_adaptive_parameters(data)
    elif method == "mad":
        return estimator.mad_estimate(data)
    elif method == "iqr":
        # 基本IQR参数
        data_clean = data.dropna()
        q1 = data_clean.quantile(0.25)
        q3 = data_clean.quantile(0.75)
        iqr = q3 - q1
        return {
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound_1.5iqr": q1 - 1.5 * iqr,
            "upper_bound_1.5iqr": q3 + 1.5 * iqr,
            "lower_bound_3iqr": q1 - 3 * iqr,
            "upper_bound_3iqr": q3 + 3 * iqr,
            "method": "iqr"
        }
    elif method == "iterative_mad":
        return estimator.iterative_robust_estimate(data, method="mad")
    elif method == "iterative_iqr":
        return estimator.iterative_robust_estimate(data, method="iqr")
    elif method == "percentile":
        return estimator.percentile_based_estimate(data)
    else:
        logger.warning(f"[ROBUST] 未知方法 {method}，使用默认auto")
        return estimator.get_adaptive_parameters(data)
