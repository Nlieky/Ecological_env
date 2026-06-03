"""
基于机器学习的异常检测算子
Machine Learning-Based Anomaly Detection Operators

特点：需要训练/拟合，可处理复杂模式

包含：
- 距离学习类 (1个)
- 密度学习类 (2个)
- 集成学习类 (1个)
- 支持向量类 (1个)
- 集成类 (2个)
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


# ========================================================================
# 距离学习类算子 (1个)
# ========================================================================

def knn_distance(x, k=5, threshold_pct=95):
    """
    算子17: KNN距离
    适用: 单变量时序，检测离群点
    参数:
      k - 近邻数
      threshold_pct - 距离分位数阈值
    """
    values = x.values.reshape(-1, 1)
    n = len(values)
    distances = []

    for i in range(n):
        dists = np.abs(values - values[i])
        dists = np.sort(dists.flatten())[1:k+1]  # 排除自己
        distances.append(dists.mean())

    distances = np.array(distances)
    threshold = np.percentile(distances, threshold_pct)
    return distances > threshold


# ========================================================================
# 密度学习类算子 (2个)
# ========================================================================

def lof_detection(data, n_neighbors=20, contamination=0.05):
    """
    算子18: LOF (Local Outlier Factor)
    适用: 多变量，局部密度异常
    参数:
      n_neighbors - 近邻数
      contamination - 异常比例
    """
    from sklearn.neighbors import LocalOutlierFactor

    if isinstance(data, pd.Series):
        data = data.to_frame()

    clf = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination
    )
    predictions = clf.fit_predict(data.dropna())
    return predictions == -1


def kde_anomaly(x, threshold_quantile=0.01):
    """
    算子19: 核密度估计 (KDE)
    适用: 任意分布，低概率即异常
    参数:
      threshold_quantile - 密度分位数阈值
    """
    from scipy.stats import gaussian_kde

    data = x.dropna()
    kde = gaussian_kde(data)
    densities = kde(data)
    threshold = np.percentile(densities, threshold_quantile * 100)
    return densities <= threshold


# ========================================================================
# 集成学习类算子 (1个)
# ========================================================================

def isolation_forest(data, contamination=0.05, random_state=42):
    """
    算子20: 孤立森林 (Isolation Forest)
    适用: 高维数据，无分布假设
    参数:
      contamination - 异常比例
      random_state - 随机种子
    """
    from sklearn.ensemble import IsolationForest

    if isinstance(data, pd.Series):
        data = data.to_frame()

    clf = IsolationForest(
        contamination=contamination,
        random_state=random_state
    )
    predictions = clf.fit_predict(data.dropna())
    return predictions == -1


# ========================================================================
# 支持向量类算子 (1个)
# ========================================================================

def one_class_svm(data, nu=0.05, kernel='rbf'):
    """
    算子21: 单类SVM (One-Class SVM)
    适用: 学习正常数据边界
    参数:
      nu - 异常比例上界
      kernel - 核函数类型
    """
    from sklearn.svm import OneClassSVM

    if isinstance(data, pd.Series):
        data = data.to_frame()

    clf = OneClassSVM(nu=nu, kernel=kernel)
    predictions = clf.fit_predict(data.dropna())
    return predictions == -1


# ========================================================================
# 集成类算子 (2个)
# ========================================================================

def voting_ensemble(x, methods, min_votes=2):
    """
    算子22: 投票集成
    适用: 综合多个算子结果
    参数:
      methods - 算子列表
      min_votes - 最少投票数
    """
    results = []
    for method in methods:
        try:
            result = method(x)
            results.append(result.values if isinstance(result, pd.Series) else result)
        except:
            continue

    if not results:
        return pd.Series([False] * len(x), index=x.index)

    votes = np.sum(results, axis=0)
    return votes >= min_votes


def weighted_score(x, methods, weights=None):
    """
    算子23: 加权评分
    适用: 综合异常分数
    参数:
      methods - 算子列表
      weights - 权重，None时均权
    """
    if weights is None:
        weights = [1] * len(methods)

    scores = []
    for method, weight in zip(methods, weights):
        try:
            result = method(x)
            score = result.astype(int) * weight
            scores.append(score.values if isinstance(score, pd.Series) else score)
        except:
            continue

    if not scores:
        return pd.Series([0] * len(x), index=x.index)

    total_score = np.sum(scores, axis=0)
    return total_score


# ========================================================================
# 算子注册
# ========================================================================

ML_OPERATORS = {
    # 距离学习类
    'knn_distance': knn_distance,

    # 密度学习类
    'lof_detection': lof_detection,
    'kde_anomaly': kde_anomaly,

    # 集成学习类
    'isolation_forest': isolation_forest,

    # 支持向量类
    'one_class_svm': one_class_svm,

    # 集成类
    'voting_ensemble': voting_ensemble,
    'weighted_score': weighted_score,
}


def get_operator(name):
    """获取指定算子"""
    return ML_OPERATORS.get(name)


def list_operators():
    """列出所有算子"""
    return list(ML_OPERATORS.keys())


if __name__ == "__main__":
    print("机器学习算子 - 共", len(ML_OPERATORS), "个")
    for name in ML_OPERATORS.keys():
        print(f"  - {name}")
