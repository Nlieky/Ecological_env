#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算子调用与适配模块
功能：集成统计类、机器学习类、深度学习类三类异常检测算子

基于专利文档：算子调用与适配模块
"""

import logging
from typing import Dict, Any, List, Callable, Optional
import pandas as pd
import numpy as np
from scipy import stats

# 尝试导入机器学习库
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# 尝试导入 PyOD 库
try:
    from pyod.models.hbos import HBOS
    from pyod.models.ecod import ECOD
    from pyod.models.knn import KNN
    from pyod.models.lof import LOF
    from pyod.models.abod import ABOD
    PYOD_AVAILABLE = True
except ImportError:
    PYOD_AVAILABLE = False

# 尝试导入可视化库
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# 尝试导入深度学习库
try:
    import torch
    import torch.nn as nn
    torch.manual_seed(42)
    DEEP_LEARNING_AVAILABLE = True
except ImportError:
    DEEP_LEARNING_AVAILABLE = False

# 尝试导入特征分析模块
try:
    from .correlation_analysis import CorrelationAnalyzer
    from .trend_analysis import TrendAnalyzer
    from .robust_estimator import RobustParameterEstimator
    FEATURE_ANALYSIS_AVAILABLE = True
    ROBUST_ESTIMATOR_AVAILABLE = True
except ImportError:
    try:
        from correlation_analysis import CorrelationAnalyzer
        from trend_analysis import TrendAnalyzer
        from robust_estimator import RobustParameterEstimator
        FEATURE_ANALYSIS_AVAILABLE = True
        ROBUST_ESTIMATOR_AVAILABLE = True
    except ImportError:
        FEATURE_ANALYSIS_AVAILABLE = False
        ROBUST_ESTIMATOR_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OperatorAdapter:
    """
    算子适配器

    支持的算子类型：
    1. 统计类：3σ原则、IQR方法、Grubbs检验
    2. 机器学习类：孤立森林、One-Class SVM
    3. 深度学习类：自编码器（可选）

    新增功能：基于意图的动态算子选择
    """

    def __init__(self, enable_intent_mapping: bool = True):
        """
        初始化算子适配器

        Args:
            enable_intent_mapping: 是否启用意图映射功能（默认True）
        """
        self.name = "算子适配器"
        self.version = "2.1.0"
        self.enable_intent_mapping = enable_intent_mapping

        # 注册算子
        self.operators = {
            # 统计类算子
            "fixed_threshold": self._fixed_threshold_anomaly,  # 固定阈值法
            "zscore": self._zscore_anomaly,
            "iqr": self._iqr_anomaly,
            "iqr_conservative": self._iqr_conservative_anomaly,  # 鲁棒IQR（3×IQR）
            "hampel": self._hampel_anomaly,  # Hampel Filter（基于MAD）
            "grubbs": self._grubbs_anomaly,
            "moving_average": self._moving_average_anomaly,
            "ewm_anomaly": self._ewm_anomaly_anomaly,  # 指数加权移动平均
            "gradient_detection": self._gradient_detection_anomaly,  # 梯度检测

            # 机器学习类算子
            "isolation_forest": self._isolation_forest_anomaly,
            "one_class_svm": self._one_class_svm_anomaly,
        }

        # PyOD 算子（如果可用）
        if PYOD_AVAILABLE:
            self.operators.update({
                "hbos": self._hbos_anomaly,
                "ecod": self._ecod_anomaly,
                "knn": self._knn_anomaly,
                "lof": self._lof_anomaly,
                "abod": self._abod_anomaly,
            })
            logger.info(f"[INIT] PyOD 算子已注册: hbos, ecod, knn, lof, abod")

        # 深度学习算子（如果可用）
        if DEEP_LEARNING_AVAILABLE:
            self.operators.update({
                "vae": self._vae_anomaly,
            })
            logger.info(f"[INIT] 深度学习算子已注册: vae")

        # 特征分析算子（如果可用）
        if FEATURE_ANALYSIS_AVAILABLE:
            self.operators.update({
                "correlation_pearson": self._correlation_pearson,
                "correlation_spearman": self._correlation_spearman,
                "trend_linear": self._trend_linear,
                "trend_mann_kendall": self._trend_mann_kendall,
            })
            logger.info(f"[INIT] 特征分析算子已注册: correlation_pearson, correlation_spearman, trend_linear, trend_mann_kendall")

            # 初始化特征分析器
            self.correlation_analyzer = CorrelationAnalyzer()
            self.trend_analyzer = TrendAnalyzer()
        else:
            self.correlation_analyzer = None
            self.trend_analyzer = None

        # 初始化鲁棒参数估计器（如果可用）
        if ROBUST_ESTIMATOR_AVAILABLE:
            self.robust_estimator = RobustParameterEstimator()
            logger.info(f"[INIT] 鲁棒参数估计器已启用")
        else:
            self.robust_estimator = None
            logger.warning(f"[INIT] 鲁棒参数估计器不可用")

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 已注册算子: {list(self.operators.keys())}")

        # 初始化意图映射器（如果启用）
        self.intent_mapper = None
        if self.enable_intent_mapping:
            try:
                # 尝试相对导入
                from .operator_mapping import IntentOperatorMapper
                self.intent_mapper = IntentOperatorMapper()
                logger.info("[INIT] 意图映射器已启用")
            except ImportError:
                try:
                    # 尝试绝对导入
                    from operator_mapping import IntentOperatorMapper
                    self.intent_mapper = IntentOperatorMapper()
                    logger.info("[INIT] 意图映射器已启用")
                except ImportError as e:
                    logger.warning(f"[INIT] 意图映射器导入失败: {e}")
                    self.enable_intent_mapping = False

    def select_operators_by_intent(
        self,
        intent: Dict[str, Any],
        data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        基于意图选择算子

        Args:
            intent: 查询意图字典
                {
                    "analysis_types": ["anomaly", "correlation"],
                    "indicators": ["COD", "pH"]
                }
            data: 输入数据（用于数据特征适配）

        Returns:
            算子选择结果
                {
                    "selected_operators": ["zscore", "iqr"],
                    "fallback_operators": ["isolation_forest"],
                    "reason": "...",
                    "intent_type": "single_anomaly"
                }
        """
        if not self.enable_intent_mapping or self.intent_mapper is None:
            logger.warning("[ADAPTER] 意图映射未启用，返回默认算子")
            return {
                "selected_operators": ["zscore", "iqr", "isolation_forest"],
                "fallback_operators": [],
                "reason": "意图映射未启用，使用默认算子",
                "intent_type": "default"
            }

        # 获取实际可用的算子列表
        available_operators = list(self.operators.keys())

        # 调用意图映射器选择算子
        selection_result = self.intent_mapper.select_operators_by_intent(
            intent=intent,
            data=data,
            available_operators=available_operators
        )

        logger.info(f"[ADAPTER] 意图映射选择算子: {selection_result['selected_operators']}")

        return selection_result

    def apply_operators(self, df: pd.DataFrame, indicators: List[str],
                       operator_names: List[str]) -> Dict[str, Any]:
        """
        应用多个算子进行异常检测

        Args:
            df: 输入数据
            indicators: 指标列表
            operator_names: 算子名称列表

        Returns:
            各算子的检测结果
        """
        logger.info(f"[ADAPTER] 应用算子: {operator_names}")

        results = {}

        for operator_name in operator_names:
            if operator_name not in self.operators:
                logger.warning(f"[ADAPTER] 未知算子: {operator_name}")
                continue

            operator_func = self.operators[operator_name]

            # 判断是否为特征分析算子
            is_feature_operator = operator_name.startswith("correlation_") or operator_name.startswith("trend_")

            if is_feature_operator:
                # 特征分析算子：处理整个DataFrame
                try:
                    feature_result, success = operator_func(df, indicators)
                    if success:
                        results[operator_name] = feature_result
                        logger.info(f"[ADAPTER] {operator_name} 分析完成")
                    else:
                        results[operator_name] = {"error": "特征分析失败"}
                        logger.warning(f"[ADAPTER] {operator_name} 分析失败")
                except Exception as e:
                    logger.warning(f"[ADAPTER] 算子 {operator_name} 执行失败: {e}")
                    results[operator_name] = {"error": str(e)}
            else:
                # 普通异常检测算子：逐指标处理
                operator_result = {}
                for indicator in indicators:
                    if indicator not in df.columns:
                        continue

                    try:
                        anomaly_scores, anomaly_mask = operator_func(
                            df[indicator].dropna()
                        )

                        operator_result[indicator] = {
                            "scores": anomaly_scores.tolist(),
                            "anomalies": anomaly_mask.tolist(),
                            "anomaly_count": int(anomaly_mask.sum()),
                            "anomaly_rate": float(anomaly_mask.sum() / len(anomaly_mask))
                        }

                    except Exception as e:
                        logger.warning(f"[ADAPTER] 算子 {operator_name} 处理 {indicator} 失败: {e}")
                        operator_result[indicator] = {"error": str(e)}

                results[operator_name] = operator_result

        return results

    # ========== 统计类算子 ==========

    def _zscore_anomaly(self, series: pd.Series,
                       threshold: float = 3.0,
                       use_robust: bool = True) -> tuple:
        """
        Z-score异常检测（支持鲁棒参数估计）

        Args:
            series: 输入数据序列
            threshold: 异常阈值（倍数）
            use_robust: 是否使用鲁棒参数估计（默认True）
        """
        if use_robust and self.robust_estimator is not None:
            # 使用迭代鲁棒估计
            params = self.robust_estimator.iterative_robust_estimate(series, method="mad")
            mean = params["mean"]
            std = params["std"]
        else:
            # 使用传统方法
            mean = series.mean()
            std = series.std()

        z_scores = np.abs((series - mean) / (std + 1e-8))
        anomaly_mask = z_scores > threshold

        return z_scores.values, anomaly_mask.values

    def _iqr_anomaly(self, series: pd.Series,
                     multiplier: float = 1.5,
                     use_robust: bool = False) -> tuple:
        """
        IQR异常检测（支持鲁棒参数估计）

        Args:
            series: 输入数据序列
            multiplier: IQR倍数（1.5=标准，3=保守）
            use_robust: 是否使用鲁棒参数估计（默认False，因为IQR本身就很鲁棒）
        """
        if use_robust and self.robust_estimator is not None:
            # 使用迭代鲁棒估计
            params = self.robust_estimator.iterative_robust_estimate(series, method="iqr")
            q1 = params["q1"]
            q3 = params["q3"]
            iqr = params["iqr"]
        else:
            # 使用传统方法
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        anomaly_mask = (series < lower_bound) | (series > upper_bound)

        # 计算异常分数（到最近边界的距离）
        scores = np.zeros_like(series)
        valid_iqr = iqr > 1e-8
        if valid_iqr:
            scores[series < lower_bound] = (lower_bound - series[series < lower_bound]) / iqr
            scores[series > upper_bound] = (series[series > upper_bound] - upper_bound) / iqr

        return scores, anomaly_mask.values

    def _grubbs_anomaly(self, series: pd.Series,
                       alpha: float = 0.05) -> tuple:
        """Grubbs检验异常检测"""
        n = len(series)
        mean = series.mean()
        std = series.std()

        # Grubbs临界值
        from scipy.stats import t
        t_dist = t.ppf(1 - alpha / (2 * n), n - 2)
        G_critical = (n - 1) / np.sqrt(n) * np.sqrt(t_dist ** 2 / (n - 2 + t_dist ** 2))

        # 计算G统计量
        G = np.abs((series - mean) / (std + 1e-8))

        anomaly_mask = G > G_critical

        return G.values, anomaly_mask.values

    def _moving_average_anomaly(self, series: pd.Series,
                                window: int = 5,
                                threshold: float = 2.0) -> tuple:
        """移动平均异常检测"""
        moving_avg = series.rolling(window=window, center=True).mean()
        moving_std = series.rolling(window=window, center=True).std()

        # 计算Z-score
        z_scores = np.abs((series - moving_avg) / (moving_std + 1e-8))

        anomaly_mask = z_scores > threshold

        return z_scores.fillna(0).values, anomaly_mask.fillna(False).values

    def _fixed_threshold_anomaly(self, series: pd.Series,
                                 lower_threshold: float = None,
                                 upper_threshold: float = None) -> tuple:
        """固定阈值法异常检测（基于排放标准）

        用于基于环保排放标准的硬性阈值检测。
        当指标值超过排放标准限值时判定为异常。

        Args:
            series: 输入数据序列
            lower_threshold: 下限阈值（默认None，表示不检测下限）
            upper_threshold: 上限阈值（默认None，表示不检测上限）

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        n = len(series)
        scores = np.zeros(n)
        anomaly_mask = np.zeros(n, dtype=bool)

        if lower_threshold is None and upper_threshold is None:
            logger.warning("[ADAPTER] fixed_threshold: 未指定阈值，返回全零")
            return scores, anomaly_mask

        for i, value in enumerate(series.values):
            if pd.isna(value):
                continue

            is_anomaly = False
            score = 0.0

            # 检查下限
            if lower_threshold is not None and value < lower_threshold:
                is_anomaly = True
                # 分数表示超出下限的程度
                if lower_threshold > 0:
                    score = (lower_threshold - value) / abs(lower_threshold)
                else:
                    score = 1.0

            # 检查上限
            elif upper_threshold is not None and value > upper_threshold:
                is_anomaly = True
                # 分数表示超出上限的程度
                if upper_threshold > 0:
                    score = (value - upper_threshold) / abs(upper_threshold)
                else:
                    score = 1.0

            scores[i] = score
            anomaly_mask[i] = is_anomaly

        return scores, anomaly_mask

    def _ewm_anomaly_anomaly(self, series: pd.Series,
                              alpha: float = 0.3,
                              threshold: float = 3.0) -> tuple:
        """指数加权移动平均异常检测（EWMA）

        对近期数据赋予更高权重，比简单移动平均更敏感。
        适用于需要快速响应的异常检测场景。

        Args:
            series: 输入数据序列
            alpha: 平滑系数（0-1之间，越小越平滑，默认0.3）
            threshold: 异常阈值（默认3倍标准差）

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        # 计算指数加权移动平均
        ewm_mean = series.ewm(alpha=alpha, adjust=False).mean()

        # 计算指数加权标准差
        ewm_std = series.ewm(alpha=alpha, adjust=False).std()

        # 计算Z-score
        z_scores = np.abs((series - ewm_mean) / (ewm_std + 1e-8))

        anomaly_mask = z_scores > threshold

        return z_scores.fillna(0).values, anomaly_mask.fillna(False).values

    def _gradient_detection_anomaly(self, series: pd.Series,
                                    threshold: float = 3.0) -> tuple:
        """梯度检测异常（突变检测）

        通过检测相邻数据点之间的变化率（梯度）来发现突变异常。
        适用于检测传感器故障、数据采集错误等导致的突然跳变。

        Args:
            series: 输入数据序列
            threshold: 异常阈值（默认3倍标准差）

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        # 计算一阶差分（梯度）
        gradients = series.diff().abs()

        # 计算梯度的统计量
        grad_mean = gradients.mean()
        grad_std = gradients.std()

        # 计算Z-score
        z_scores = np.zeros_like(gradients)
        valid_mask = (grad_std > 1e-8) & (~np.isnan(gradients))

        if valid_mask.sum() > 0:
            z_scores[valid_mask] = np.abs((gradients[valid_mask] - grad_mean) / (grad_std + 1e-8))

        anomaly_mask = z_scores > threshold

        # 梯度检测：第一个数据点没有梯度，设为正常
        # 使用numpy索引而不是iloc
        if len(anomaly_mask) > 0:
            anomaly_mask[0] = False

        return z_scores, anomaly_mask.astype(bool).astype(float).values

    def _hampel_anomaly(self, series: pd.Series,
                        threshold: float = 3.0) -> tuple:
        """Hampel Filter异常检测（基于中位数绝对偏差MAD）

        相比传统Z-score的优势：
        - 使用中位数代替均值，对异常值不敏感
        - 使用MAD代替标准差，更加鲁棒
        - MAD到sigma的转换因子：1.4826（正态分布下）

        Args:
            series: 输入数据序列
            threshold: 异常阈值（默认3倍MAD，对应3σ）

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        # 计算中位数
        median = series.median()

        # 计算MAD（中位数绝对偏差）
        mad = np.median(np.abs(series - median))

        # MAD到标准差的转换因子（正态分布下）
        sigma = 1.4826 * mad

        # 计算修正的Z-score（基于中位数和MAD）
        if sigma > 1e-8:
            modified_z_scores = (series - median) / sigma
        else:
            modified_z_scores = pd.Series([0.0] * len(series), index=series.index)

        # 异常判定
        anomaly_mask = np.abs(modified_z_scores) > threshold

        # 分数使用绝对值
        scores = np.abs(modified_z_scores.values)

        return scores, anomaly_mask.values

    def _iqr_conservative_anomaly(self, series: pd.Series,
                                  multiplier: float = 3.0) -> tuple:
        """保守的IQR异常检测（使用3×IQR阈值）

        相比标准IQR（1.5×IQR）的优势：
        - 减少误报，只检测极端异常值
        - 适合工业过程数据，容忍正常波动
        - 可与标准IQR组合使用，提供两级检测

        Args:
            series: 输入数据序列
            multiplier: IQR倍数（默认3.0，保守阈值）

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        anomaly_mask = (series < lower_bound) | (series > upper_bound)

        # 计算异常分数（到最近边界的距离，归一化到IQR）
        scores = np.zeros_like(series)
        valid_iqr = iqr > 1e-8

        if valid_iqr:
            scores[series < lower_bound] = (lower_bound - series[series < lower_bound]) / iqr
            scores[series > upper_bound] = (series[series > upper_bound] - upper_bound) / iqr

        return scores, anomaly_mask.values

    # ========== 机器学习类算子 ==========

    def _isolation_forest_anomaly(self, series: pd.Series,
                                  contamination: float = 0.1) -> tuple:
        """孤立森林异常检测"""
        if not ML_AVAILABLE:
            logger.warning("[ADAPTER] sklearn不可用，使用统计方法替代")
            return self._zscore_anomaly(series)

        # 重塑数据
        X = series.values.reshape(-1, 1)

        # 训练模型
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        iso_forest.fit(X)

        # 预测（-1表示异常）
        predictions = iso_forest.predict(X)
        anomaly_mask = predictions == -1

        # 计算异常分数
        scores = iso_forest.score_samples(X)
        scores = -scores  # 转换为正数（越高越异常）

        return scores, anomaly_mask

    def _one_class_svm_anomaly(self, series: pd.Series,
                               nu: float = 0.1) -> tuple:
        """One-Class SVM异常检测"""
        if not ML_AVAILABLE:
            logger.warning("[ADAPTER] sklearn不可用，使用统计方法替代")
            return self._zscore_anomaly(series)

        # 重塑数据
        X = series.values.reshape(-1, 1)

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 训练模型
        svm = OneClassSVM(nu=nu, kernel="rbf")
        svm.fit(X_scaled)

        # 预测（-1表示异常）
        predictions = svm.predict(X_scaled)
        anomaly_mask = predictions == -1

        # 计算到决策边界的距离
        scores = -svm.decision_function(X_scaled)
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)

        return scores, anomaly_mask

    # ========== PyOD 算子 ==========

    def _hbos_anomaly(self, series: pd.Series,
                      n_bins: int = 10,
                      contamination: float = 0.1) -> tuple:
        """HBOS (Histogram-based Outlier Score) 异常检测

        Args:
            series: 输入数据序列
            n_bins: 直方图箱数
            contamination: 异常比例

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        if not PYOD_AVAILABLE:
            logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
            return self._zscore_anomaly(series)

        # 数据预处理
        X = series.values.reshape(-1, 1)
        n_samples = len(X)

        # 边界检查
        if n_samples < 2:
            logger.warning("[ADAPTER] 数据量不足，返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        # 移除 NaN
        valid_mask = ~np.isnan(X.flatten())
        if valid_mask.sum() < 2:
            logger.warning("[ADAPTER] 有效数据不足，返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        X_valid = X[valid_mask].reshape(-1, 1)

        try:
            # 创建并训练 HBOS 模型
            detector = HBOS(n_bins=n_bins, contamination=contamination)
            detector.fit(X_valid)

            # 预测
            scores = detector.decision_function(X_valid)
            predictions = detector.predict(X_valid)

            # 构建完整结果（包含 NaN 位置）
            full_scores = np.zeros(n_samples)
            full_mask = np.zeros(n_samples, dtype=bool)

            full_scores[valid_mask] = scores
            full_mask[valid_mask] = (predictions == 1)

            return full_scores, full_mask

        except Exception as e:
            logger.warning(f"[ADAPTER] HBOS 检测失败: {e}，使用 zscore 替代")
            return self._zscore_anomaly(series)

    def _ecod_anomaly(self, series: pd.Series,
                      contamination: float = 0.1) -> tuple:
        """ECOD (Empirical Cumulative Distribution) 异常检测

        Args:
            series: 输入数据序列
            contamination: 异常比例

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        if not PYOD_AVAILABLE:
            logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
            return self._zscore_anomaly(series)

        # 数据预处理
        X = series.values.reshape(-1, 1)
        n_samples = len(X)

        # 边界检查
        if n_samples < 2:
            logger.warning("[ADAPTER] 数据量不足，返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        # 移除 NaN
        valid_mask = ~np.isnan(X.flatten())
        if valid_mask.sum() < 2:
            logger.warning("[ADAPTER] 有效数据不足，返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        X_valid = X[valid_mask].reshape(-1, 1)

        try:
            # 创建并训练 ECOD 模型
            detector = ECOD(contamination=contamination)
            detector.fit(X_valid)

            # 预测
            scores = detector.decision_function(X_valid)
            predictions = detector.predict(X_valid)

            # 构建完整结果（包含 NaN 位置）
            full_scores = np.zeros(n_samples)
            full_mask = np.zeros(n_samples, dtype=bool)

            full_scores[valid_mask] = scores
            full_mask[valid_mask] = (predictions == 1)

            return full_scores, full_mask

        except Exception as e:
            logger.warning(f"[ADAPTER] ECOD 检测失败: {e}，使用 zscore 替代")
            return self._zscore_anomaly(series)

    def _knn_anomaly(self, series: pd.Series,
                     n_neighbors: int = 5,
                     contamination: float = 0.1) -> tuple:
        """KNN (K-Nearest Neighbors) 异常检测

        Args:
            series: 输入数据序列
            n_neighbors: 近邻数量
            contamination: 异常比例

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        if not PYOD_AVAILABLE:
            logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
            return self._zscore_anomaly(series)

        # 数据预处理
        X = series.values.reshape(-1, 1)
        n_samples = len(X)

        # 边界检查
        if n_samples < n_neighbors + 1:
            logger.warning(f"[ADAPTER] 数据量不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        # 移除 NaN
        valid_mask = ~np.isnan(X.flatten())
        if valid_mask.sum() < n_neighbors + 1:
            logger.warning(f"[ADAPTER] 有效数据不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        X_valid = X[valid_mask].reshape(-1, 1)

        try:
            # 创建并训练 KNN 模型
            detector = KNN(n_neighbors=n_neighbors, contamination=contamination)
            detector.fit(X_valid)

            # 预测
            scores = detector.decision_function(X_valid)
            predictions = detector.predict(X_valid)

            # 构建完整结果（包含 NaN 位置）
            full_scores = np.zeros(n_samples)
            full_mask = np.zeros(n_samples, dtype=bool)

            full_scores[valid_mask] = scores
            full_mask[valid_mask] = (predictions == 1)

            return full_scores, full_mask

        except Exception as e:
            logger.warning(f"[ADAPTER] KNN 检测失败: {e}，使用 zscore 替代")
            return self._zscore_anomaly(series)

    def _lof_anomaly(self, series: pd.Series,
                     n_neighbors: int = 20,
                     contamination: float = 0.1) -> tuple:
        """LOF (Local Outlier Factor) 异常检测

        Args:
            series: 输入数据序列
            n_neighbors: 近邻数量
            contamination: 异常比例

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        if not PYOD_AVAILABLE:
            logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
            return self._zscore_anomaly(series)

        # 数据预处理
        X = series.values.reshape(-1, 1)
        n_samples = len(X)

        # 边界检查
        if n_samples < n_neighbors + 1:
            logger.warning(f"[ADAPTER] 数据量不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        # 移除 NaN
        valid_mask = ~np.isnan(X.flatten())
        if valid_mask.sum() < n_neighbors + 1:
            logger.warning(f"[ADAPTER] 有效数据不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        X_valid = X[valid_mask].reshape(-1, 1)

        try:
            # 创建并训练 LOF 模型
            detector = LOF(n_neighbors=n_neighbors, contamination=contamination)
            detector.fit(X_valid)

            # 预测
            scores = detector.decision_function(X_valid)
            predictions = detector.predict(X_valid)

            # 构建完整结果（包含 NaN 位置）
            full_scores = np.zeros(n_samples)
            full_mask = np.zeros(n_samples, dtype=bool)

            full_scores[valid_mask] = scores
            full_mask[valid_mask] = (predictions == 1)

            return full_scores, full_mask

        except Exception as e:
            logger.warning(f"[ADAPTER] LOF 检测失败: {e}，使用 zscore 替代")
            return self._zscore_anomaly(series)

    def _abod_anomaly(self, series: pd.Series,
                      contamination: float = 0.1) -> tuple:
        """ABOD (Angle-Based Outlier Detection) 异常检测

        Args:
            series: 输入数据序列
            contamination: 异常比例

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        if not PYOD_AVAILABLE:
            logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
            return self._zscore_anomaly(series)

        # 数据预处理
        X = series.values.reshape(-1, 1)
        n_samples = len(X)

        # 边界检查 - ABOD 需要至少 5 个样本
        if n_samples < 5:
            logger.warning("[ADAPTER] 数据量不足（ABOD 需要至少 5 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        # 移除 NaN
        valid_mask = ~np.isnan(X.flatten())
        if valid_mask.sum() < 5:
            logger.warning("[ADAPTER] 有效数据不足（ABOD 需要至少 5 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        X_valid = X[valid_mask].reshape(-1, 1)

        try:
            # 创建并训练 ABOD 模型
            detector = ABOD(contamination=contamination)
            detector.fit(X_valid)

            # 预测
            scores = detector.decision_function(X_valid)
            predictions = detector.predict(X_valid)

            # 构建完整结果（包含 NaN 位置）
            full_scores = np.zeros(n_samples)
            full_mask = np.zeros(n_samples, dtype=bool)

            full_scores[valid_mask] = scores
            full_mask[valid_mask] = (predictions == 1)

            return full_scores, full_mask

        except Exception as e:
            logger.warning(f"[ADAPTER] ABOD 检测失败: {e}，使用 zscore 替代")
            return self._zscore_anomaly(series)

    # ========== 深度学习类算子 ==========

    def _vae_anomaly(self, series: pd.Series,
                     latent_dim: int = 8,
                     epochs: int = 50,
                     batch_size: int = 32,
                     contamination: float = 0.1) -> tuple:
        """VAE (Variational Autoencoder) 异常检测

        使用变分自编码器进行异常检测。通过训练VAE重构正常数据，
        重构误差较大的样本被标记为异常。

        Args:
            series: 输入数据序列
            latent_dim: 潜在空间维度
            epochs: 训练轮数
            batch_size: 批次大小
            contamination: 异常比例阈值

        Returns:
            (scores, anomaly_mask): 异常分数和异常掩码
        """
        if not DEEP_LEARNING_AVAILABLE:
            logger.warning("[ADAPTER] 深度学习库不可用，使用 zscore 替代")
            return self._zscore_anomaly(series)

        # 数据预处理
        X = series.values.reshape(-1, 1)
        n_samples = len(X)

        # 边界检查
        if n_samples < 20:
            logger.warning("[ADAPTER] 数据量不足（VAE 建议至少 20 个样本），返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        # 移除 NaN
        valid_mask = ~np.isnan(X.flatten())
        if valid_mask.sum() < 20:
            logger.warning("[ADAPTER] 有效数据不足，返回全零分数")
            return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

        X_valid = X[valid_mask]

        try:
            # 标准化数据
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_valid)

            # 转换为torch张量
            X_tensor = torch.FloatTensor(X_scaled).reshape(-1, 1)

            # 定义VAE模型
            class VAE(nn.Module):
                def __init__(self, input_dim=1, latent_dim=latent_dim):
                    super(VAE, self).__init__()
                    # 编码器
                    self.encoder = nn.Sequential(
                        nn.Linear(input_dim, 32),
                        nn.ReLU(),
                        nn.Linear(32, latent_dim * 2)  # 均值和方差
                    )
                    # 解码器
                    self.decoder = nn.Sequential(
                        nn.Linear(latent_dim, 32),
                        nn.ReLU(),
                        nn.Linear(32, input_dim)
                    )

                def reparameterize(self, mu, logvar):
                    std = torch.exp(0.5 * logvar)
                    eps = torch.randn_like(std)
                    return mu + eps * std

                def forward(self, x):
                    # 编码
                    h = self.encoder(x)
                    mu, logvar = h.chunk(2, dim=-1)
                    z = self.reparameterize(mu, logvar)
                    # 解码
                    reconstructed = self.decoder(z)
                    return reconstructed, mu, logvar

            # 初始化模型
            model = VAE(input_dim=1, latent_dim=latent_dim)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

            # 训练VAE
            model.train()
            for epoch in range(epochs):
                optimizer.zero_grad()

                # 前向传播
                reconstructed, mu, logvar = model(X_tensor)

                # 计算损失：重构损失 + KL散度
                recon_loss = nn.functional.mse_loss(reconstructed, X_tensor)
                kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                loss = recon_loss + 0.001 * kl_loss

                # 反向传播
                loss.backward()
                optimizer.step()

            # 计算重构误差作为异常分数
            model.eval()
            with torch.no_grad():
                reconstructed, _, _ = model(X_tensor)
                reconstruction_errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1)

            # 转换为numpy数组
            errors = reconstruction_errors.numpy()

            # 根据contamination确定阈值
            threshold = np.percentile(errors, (1 - contamination) * 100)

            # 构建完整结果（包含 NaN 位置）
            full_scores = np.zeros(n_samples)
            full_mask = np.zeros(n_samples, dtype=bool)

            full_scores[valid_mask] = errors
            full_mask[valid_mask] = errors > threshold

            return full_scores, full_mask

        except Exception as e:
            logger.warning(f"[ADAPTER] VAE 检测失败: {e}，使用 zscore 替代")
            return self._zscore_anomaly(series)

    def plot_anomalies(self,
                       series: pd.Series,
                       anomaly_mask: np.ndarray,
                       operator_name: str,
                       indicator_name: str,
                       save_path: Optional[str] = None) -> str:
        """绘制异常检测结果可视化

        Args:
            series: 原始数据序列
            anomaly_mask: 异常掩码（True=异常）
            operator_name: 算子名称
            indicator_name: 指标名称
            save_path: 保存路径（可选）

        Returns:
            图片保存路径或 base64 编码
        """
        if not MATPLOTLIB_AVAILABLE:
            return "[ERROR] matplotlib 不可用，无法生成可视化"

        try:
            # 创建图形
            fig, ax = plt.subplots(figsize=(12, 4))

            # 绘制原始数据曲线
            ax.plot(series.values, 'b-', label='数据', alpha=0.7)

            # 标记异常点
            anomaly_indices = np.where(anomaly_mask)[0]
            if len(anomaly_indices) > 0:
                ax.scatter(anomaly_indices, series.values[anomaly_indices],
                          c='red', s=50, label='异常', zorder=5)

            # 设置标题和标签
            ax.set_title(f'异常检测结果 - {operator_name} | {indicator_name}')
            ax.set_xlabel('时间步')
            ax.set_ylabel('数值')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # 保存或返回
            if save_path:
                plt.savefig(save_path, dpi=100, bbox_inches='tight')
                plt.close(fig)
                return save_path
            else:
                # 返回 base64 编码
                import io
                import base64
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)
                return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.error(f"[ADAPTER] 可视化生成失败: {e}")
            return f"[ERROR] 可视化生成失败: {str(e)}"

    # ========== 特征分析算子 ==========

    def _correlation_pearson(self, df: pd.DataFrame, indicators: List[str] = None) -> tuple:
        """Pearson相关性分析算子

        Args:
            df: 输入数据（注意：这里是完整DataFrame）
            indicators: 指标列表（注意：这里是为了兼容接口，实际从df.columns获取）

        Returns:
            (correlation_result, True): 相关性结果和成功标志
        """
        if not FEATURE_ANALYSIS_AVAILABLE or self.correlation_analyzer is None:
            logger.warning("[ADAPTER] CorrelationAnalyzer 不可用")
            return {}, False

        try:
            # 获取数值型指标
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            valid_indicators = [col for col in numeric_cols if col not in ["times", "timestamp", "time"]]

            if len(valid_indicators) < 2:
                logger.warning("[ADAPTER] 相关性分析需要至少2个指标")
                return {}, False

            # 调用相关性分析器（Pearson是默认方法）
            result = self.correlation_analyzer.analyze(df, valid_indicators)

            # 添加方法标识
            result["method"] = "pearson"

            return result, True

        except Exception as e:
            logger.warning(f"[ADAPTER] Pearson相关性分析失败: {e}")
            return {}, False

    def _correlation_spearman(self, df: pd.DataFrame, indicators: List[str] = None) -> tuple:
        """Spearman相关性分析算子

        注意：当前实现与Pearson相同，因为CorrelationAnalyzer.analyze默认使用Pearson
        TODO: 后续可扩展为支持Spearman方法

        Args:
            df: 输入数据
            indicators: 指标列表（可选）

        Returns:
            (correlation_result, True): 相关性结果和成功标志
        """
        if not FEATURE_ANALYSIS_AVAILABLE or self.correlation_analyzer is None:
            logger.warning("[ADAPTER] CorrelationAnalyzer 不可用")
            return {}, False

        try:
            # 获取数值型指标
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            valid_indicators = [col for col in numeric_cols if col not in ["times", "timestamp", "time"]]

            if len(valid_indicators) < 2:
                logger.warning("[ADAPTER] 相关性分析需要至少2个指标")
                return {}, False

            # 调用相关性分析器
            result = self.correlation_analyzer.analyze(df, valid_indicators)

            # 添加方法标识
            result["method"] = "spearman"
            result["note"] = "当前使用Pearson方法，Spearman支持待实现"

            return result, True

        except Exception as e:
            logger.warning(f"[ADAPTER] Spearman相关性分析失败: {e}")
            return {}, False

    def _trend_linear(self, df: pd.DataFrame, indicators: List[str] = None) -> tuple:
        """线性趋势分析算子

        Args:
            df: 输入数据
            indicators: 指标列表（可选）

        Returns:
            (trend_result, True): 趋势分析结果和成功标志
        """
        if not FEATURE_ANALYSIS_AVAILABLE or self.trend_analyzer is None:
            logger.warning("[ADAPTER] TrendAnalyzer 不可用")
            return {}, False

        try:
            # 获取数值型指标
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            valid_indicators = [col for col in numeric_cols if col not in ["times", "timestamp", "time"]]

            if not valid_indicators:
                logger.warning("[ADAPTER] 没有有效指标进行趋势分析")
                return {}, False

            # 调用趋势分析器
            result = self.trend_analyzer.analyze(df, valid_indicators)

            # 添加方法标识
            result["method"] = "linear"

            return result, True

        except Exception as e:
            logger.warning(f"[ADAPTER] 线性趋势分析失败: {e}")
            return {}, False

    def _trend_mann_kendall(self, df: pd.DataFrame, indicators: List[str] = None) -> tuple:
        """Mann-Kendall趋势检验算子

        注意：当前实现与linear相同，因为TrendAnalyzer.analyze默认使用线性方法
        TODO: 后续可扩展为支持Mann-Kendall方法

        Args:
            df: 输入数据
            indicators: 指标列表（可选）

        Returns:
            (trend_result, True): 趋势检验结果和成功标志
        """
        if not FEATURE_ANALYSIS_AVAILABLE or self.trend_analyzer is None:
            logger.warning("[ADAPTER] TrendAnalyzer 不可用")
            return {}, False

        try:
            # 获取数值型指标
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            valid_indicators = [col for col in numeric_cols if col not in ["times", "timestamp", "time"]]

            if not valid_indicators:
                logger.warning("[ADAPTER] 没有有效指标进行趋势检验")
                return {}, False

            # 调用趋势分析器
            result = self.trend_analyzer.analyze(df, valid_indicators)

            # 添加方法标识
            result["method"] = "mann_kendall"
            result["note"] = "当前使用线性方法，Mann-Kendall支持待实现"

            return result, True

        except Exception as e:
            logger.warning(f"[ADAPTER] Mann-Kendall趋势检验失败: {e}")
            return {}, False

    def get_available_operators(self) -> Dict[str, List[str]]:
        """获取可用算子分类"""
        result = {
            "statistical": [
                "fixed_threshold",
                "zscore",
                "iqr",
                "iqr_conservative",
                "hampel",
                "grubbs",
                "moving_average",
                "ewm_anomaly",
                "gradient_detection"
            ],
            "machine_learning": ["isolation_forest", "one_class_svm"] if ML_AVAILABLE else []
        }

        # 添加 PyOD 算子
        if PYOD_AVAILABLE:
            result["pyod"] = ["hbos", "ecod", "knn", "lof", "abod"]
        else:
            result["pyod"] = []

        # 添加深度学习算子
        if DEEP_LEARNING_AVAILABLE:
            result["deep_learning"] = ["vae"]
        else:
            result["deep_learning"] = []

        # 添加特征分析算子
        if FEATURE_ANALYSIS_AVAILABLE:
            result["feature_analysis"] = ["correlation_pearson", "correlation_spearman", "trend_linear", "trend_mann_kendall"]
        else:
            result["feature_analysis"] = []

        return result


# 入口函数 - 执行控制模块调用
def main(data: Optional[Dict[str, Any]] = None,
         indicators: Optional[List[str]] = None,
         operators: Optional[List[str]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 算子调用与适配

    Args:
        data: 数据字典（包含 values）
        indicators: 指标列表
        operators: 算子名称列表
        **kwargs: 其他参数

    Returns:
        算子检测结果
    """
    if not data:
        return {
            "status": "error",
            "error": "No data provided",
            "operator_results": {}
        }

    try:
        import pandas as pd

        # 转换为数据框格式
        values = data.get("values", {})
        if not values:
            return {
                "status": "error",
                "error": "No values in data",
                "operator_results": {}
            }

        df = pd.DataFrame(values)

        # 如果没有指定指标，使用所有列
        if not indicators:
            indicators = list(df.columns)

        # 如果没有指定算子，使用默认算子（优先使用鲁棒方法）
        if not operators:
            operators = ["hampel", "iqr_conservative", "zscore", "gradient_detection", "ewm_anomaly"]

        # 创建适配器并应用算子
        adapter = OperatorAdapter()
        results = adapter.apply_operators(df, indicators, operators)

        return {
            "status": "success",
            "operator_results": results,
            "available_operators": adapter.get_available_operators(),
            "indicators": indicators,
            "operators_used": operators
        }

    except Exception as e:
        logger.error(f"[ADAPTER] 算子检测失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "operator_results": {}
        }


def process(data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(data=data, **kwargs)
