"""
基于统计学的异常检测算子
Statistical-Based Anomaly Detection Operators

特点：无需训练，计算快速，可解释性强

包含：
- 统计量类 (6个)
- 统计检验类 (2个)
- 时序统计类 (6个)
- 多变量统计类 (3个)
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.covariance import MinCovDet
import warnings
warnings.filterwarnings('ignore')


# ========================================================================
# 统计量类算子 (6个)
# ========================================================================

def fixed_threshold(x, lower_bound, upper_bound):
    """
    算子1: 固定阈值法
    适用: 基于排放标准的硬性阈值检测
    参数: lower_bound, upper_bound
    """
    anomalies = (x < lower_bound) | (x > upper_bound)
    return anomalies


def z_score(x, threshold=3):
    """
    算子2: Z-Score / 3σ法
    适用: 近正态分布数据
    参数: threshold - σ倍数，默认3
    """
    mean = x.mean()
    std = x.std()
    z = np.abs((x - mean) / std)
    return z > threshold


def iqr_outlier(x, k=1.5):
    """
    算子3: IQR / 箱线图法
    适用: 非正态分布，偏态数据
    参数: k - IQR倍数，默认1.5(标准)，3.0(保守)
    """
    q1 = x.quantile(0.25)
    q3 = x.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - k * iqr
    upper = q3 + k * iqr
    return (x < lower) | (x > upper)


def modified_z_score(x, threshold=3.5):
    """
    算子4: 修正Z-Score
    适用: 非正态分布，抗异常值
    参数: threshold - 默认3.5
    优势: 用中位数和MAD代替均值和标准差
    """
    median = x.median()
    mad = np.median(np.abs(x - median))
    sigma = 1.4826 * mad
    modified_z = np.abs((x - median) / sigma) if sigma > 0 else np.zeros_like(x)
    return modified_z > threshold


def percentile_method(x, lower_pct=0.5, upper_pct=99.5):
    """
    算子5: 分位数法
    适用: 任意分布
    参数: lower_pct, upper_pct - 分位数阈值
    """
    lower = x.quantile(lower_pct / 100)
    upper = x.quantile(upper_pct / 100)
    return (x < lower) | (x > upper)


# ========================================================================
# 统计检验类算子 (2个)
# ========================================================================

def grubbs_test(x, alpha=0.05):
    """
    算子6: Grubbs检验
    适用: 检测单个极端异常值
    参数: alpha - 显著性水平
    注意: 每次只能检测一个异常值
    """
    mean = x.mean()
    std = x.std()
    n = len(x)
    t_crit = stats.t.ppf(1 - alpha/(2*n), n-2)
    g_crit = (n-1) * np.sqrt(t_crit**2 / (n*(n-2 + t_crit**2)))
    g_stat = np.abs(x - mean).max() / std
    return (np.abs(x - mean) / std) > g_crit


def ese_test(x, alpha=0.05):
    """
    算子7: ESD检验 (Extreme Studentized Deviate)
    适用: 检测多个异常值
    参数: alpha - 显著性水平
    """
    n = len(x)
    max_outliers = min(10, n // 10)
    outliers = np.zeros_like(x, dtype=bool)

    for _ in range(max_outliers):
        mean = x[~outliers].mean()
        std = x[~outliers].std()
        if std == 0:
            break
        t_crit = stats.t.ppf(1 - alpha/(2*n), n-2)
        g_crit = (n-1) * np.sqrt(t_crit**2 / (n*(n-2 + t_crit**2)))
        g_stat = np.abs(x - mean) / std
        new_outlier = g_stat.argmax()
        if g_stat.iloc[new_outlier] > g_crit:
            outliers[new_outlier] = True
        else:
            break
    return outliers


# ========================================================================
# 时序统计类算子 (6个)
# ========================================================================

def hampel_filter(x, window_size=24, threshold=3):
    """
    算子8: Hampel滤波器
    适用: 时序数据，抗噪能力强
    参数:
      window_size - 滑动窗口大小，建议24(1天)或48(2天)
      threshold - MAD倍数阈值，默认3
    """
    n = len(x)
    anomalies = np.zeros(n, dtype=bool)
    half_window = window_size // 2

    for i in range(half_window, n - half_window):
        window = x.iloc[i - half_window:i + half_window + 1]
        median = window.median()
        mad = np.median(np.abs(window - median))
        if mad > 0:
            z = 0.6745 * (x.iloc[i] - median) / mad
            if np.abs(z) > threshold:
                anomalies[i] = True
    return anomalies


def moving_average(x, window=24, k=3):
    """
    算子9: 移动平均偏差
    适用: 时序趋势异常检测
    参数:
      window - 移动窗口，默认24小时
      k - 标准差倍数
    """
    ma = x.rolling(window=window, center=True).mean()
    std = x.rolling(window=window, center=True).std()
    return np.abs(x - ma) > k * std


def ewm_anomaly(x, span=24, k=3):
    """
    算子10: 指数加权移动平均 (EWMA)
    适用: 时序数据，对近期数据更敏感
    参数:
      span - 跨度，默认24
      k - 标准差倍数
    """
    ewm_mean = x.ewm(span=span).mean()
    ewm_std = x.ewm(span=span).std()
    return np.abs(x - ewm_mean) > k * ewm_std


def gradient_detection(x, gradient_threshold=None, method='diff'):
    """
    算子11: 梯度检测
    适用: 突变异常检测
    参数:
      gradient_threshold - 梯度阈值，None时自动计算
      method - 'diff'(一阶差分) 或 'pct_change'(变化率)
    """
    if method == 'diff':
        grad = x.diff()
    else:
        grad = x.pct_change()

    if gradient_threshold is None:
        grad_valid = grad.dropna()
        mad = np.median(np.abs(grad_valid - grad_valid.median()))
        gradient_threshold = 3 * 1.4826 * mad

    return np.abs(grad) > gradient_threshold


def derivative_detection(x, window=5, k=3):
    """
    算子12: 二阶导数检测
    适用: 检测拐点、波动异常
    参数:
      window - 平滑窗口
      k - 标准差倍数
    """
    first_diff = x.diff()
    second_diff = first_diff.diff()
    rolling_std = second_diff.rolling(window=window).std()
    mean = second_diff.rolling(window=window).mean()
    return np.abs(second_diff - mean) > k * rolling_std


def burst_detection(x, window=24, threshold_pct=0.5):
    """
    算子13: 突发检测
    适用: 检测数据突发变化
    参数:
      window - 检测窗口
      threshold_pct - 突发阈值比例
    """
    rolling_mean = x.rolling(window=window).mean()
    rolling_std = x.rolling(window=window).std()
    threshold = rolling_mean + threshold_pct * rolling_std
    return x > threshold


# ========================================================================
# 多变量统计类算子 (3个)
# ========================================================================

def mahalanobis_distance(data, threshold_quantile=0.99):
    """
    算子14: 马氏距离
    适用: 多变量数据，考虑变量协方差
    参数:
      threshold_quantile - 距离分位数阈值
    """
    if isinstance(data, pd.Series):
        data = data.to_frame()

    mcd = MinCovDet().fit(data.dropna())
    mean = mcd.location_
    cov = mcd.covariance_

    inv_cov = np.linalg.inv(cov)
    distances = []

    for _, row in data.dropna().iterrows():
        diff = row.values - mean
        dist = np.sqrt(diff @ inv_cov @ diff.T)
        distances.append(dist)

    distances = np.array(distances)
    threshold = np.percentile(distances, threshold_quantile * 100)
    return distances > threshold


def pca_hotelling_t2(data, n_components=None, threshold_quantile=0.99):
    """
    算子15: PCA + Hotelling T²
    适用: 多变量，工业过程监控
    参数:
      n_components - 主成分数量，None时自动选择
      threshold_quantile - T²统计量分位数阈值
    """
    if isinstance(data, pd.Series):
        data = data.to_frame()

    data_clean = data.dropna()
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_clean)

    if n_components is None:
        pca = PCA()
        pca.fit(data_scaled)
        n_components = np.where(pca.explained_variance_ratio_.cumsum() > 0.9)[0][0] + 1

    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(data_scaled)

    lambda_inv = np.diag(1 / pca.explained_variance_)
    t2 = np.array([s @ lambda_inv @ s.T for s in scores])

    threshold = np.percentile(t2, threshold_quantile * 100)
    return t2 > threshold


def spe_detection(data, n_components=None, threshold_quantile=0.99):
    """
    算子16: PCA + SPE (Q统计量)
    适用: PCA残差检测
    参数:
      n_components - 主成分数量
      threshold_quantile - SPE分位数阈值
    """
    if isinstance(data, pd.Series):
        data = data.to_frame()

    data_clean = data.dropna()
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_clean)

    if n_components is None:
        pca = PCA()
        pca.fit(data_scaled)
        n_components = np.where(pca.explained_variance_ratio_.cumsum() > 0.9)[0][0] + 1

    pca = PCA(n_components=n_components)
    pca.fit(data_scaled)

    scores = pca.transform(data_scaled)
    reconstructed = pca.inverse_transform(scores)
    spe = np.sum((data_scaled - reconstructed) ** 2, axis=1)

    threshold = np.percentile(spe, threshold_quantile * 100)
    return spe > threshold


# ========================================================================
# 算子注册
# ========================================================================

STATISTICAL_OPERATORS = {
    # 统计量类
    'fixed_threshold': fixed_threshold,
    'z_score': z_score,
    'iqr_outlier': iqr_outlier,
    'modified_z_score': modified_z_score,
    'percentile': percentile_method,

    # 统计检验类
    'grubbs_test': grubbs_test,
    'ese_test': ese_test,

    # 时序统计类
    'hampel_filter': hampel_filter,
    'moving_avg': moving_average,
    'ewm_anomaly': ewm_anomaly,
    'gradient_detection': gradient_detection,
    'derivative_detection': derivative_detection,
    'burst_detection': burst_detection,

    # 多变量统计类
    'mahalanobis_distance': mahalanobis_distance,
    'pca_hotelling_t2': pca_hotelling_t2,
    'spe_detection': spe_detection,
}


def get_operator(name):
    """获取指定算子"""
    return STATISTICAL_OPERATORS.get(name)


def list_operators():
    """列出所有算子"""
    return list(STATISTICAL_OPERATORS.keys())


if __name__ == "__main__":
    print("统计学算子 - 共", len(STATISTICAL_OPERATORS), "个")
    for name in STATISTICAL_OPERATORS.keys():
        print(f"  - {name}")
