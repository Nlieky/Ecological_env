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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OperatorAdapter:
    """
    算子适配器

    支持的算子类型：
    1. 统计类：3σ原则、IQR方法、Grubbs检验
    2. 机器学习类：孤立森林、One-Class SVM
    3. 深度学习类：自编码器（可选）
    """

    def __init__(self):
        """初始化算子适配器"""
        self.name = "算子适配器"
        self.version = "2.0.0"

        # 注册算子
        self.operators = {
            # 统计类算子
            "zscore": self._zscore_anomaly,
            "iqr": self._iqr_anomaly,
            "grubbs": self._grubbs_anomaly,
            "moving_average": self._moving_average_anomaly,

            # 机器学习类算子
            "isolation_forest": self._isolation_forest_anomaly,
            "one_class_svm": self._one_class_svm_anomaly,

            # PyOD 算子
            "hbos": self._hbos_anomaly,
            "ecod": self._ecod_anomaly,
            "knn": self._knn_anomaly,
            "lof": self._lof_anomaly,
            "abod": self._abod_anomaly,
        }

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 已注册算子: {list(self.operators.keys())}")

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
                       threshold: float = 3.0) -> tuple:
        """Z-score异常检测"""
        z_scores = np.abs((series - series.mean()) / (series.std() + 1e-8))
        anomaly_mask = z_scores > threshold
        return z_scores.values, anomaly_mask.values

    def _iqr_anomaly(self, series: pd.Series,
                     multiplier: float = 1.5) -> tuple:
        """IQR异常检测"""
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        anomaly_mask = (series < lower_bound) | (series > upper_bound)

        # 计算异常分数（到最近边界的距离）
        scores = np.zeros_like(series)
        scores[series < lower_bound] = (lower_bound - series[series < lower_bound]) / (iqr + 1e-8)
        scores[series > upper_bound] = (series[series > upper_bound] - upper_bound) / (iqr + 1e-8)

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

    def get_available_operators(self) -> Dict[str, List[str]]:
        """获取可用算子分类"""
        return {
            "statistical": ["zscore", "iqr", "grubbs", "moving_average"],
            "machine_learning": ["isolation_forest", "one_class_svm"] if ML_AVAILABLE else [],
            "pyod": ["hbos", "knn", "lof"] if PYOD_AVAILABLE else [],
            "deep_learning": []  # 待实现
        }


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

        # 如果没有指定算子，使用默认算子
        if not operators:
            operators = ["zscore", "iqr", "isolation_forest"]

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
