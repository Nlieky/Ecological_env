# 异常检测算子库参考文档

## 一、算子分类

### 1.1 统计类算子

| 算子 | 原理 | 适用场景 | 参数 |
|------|------|----------|------|
| 3σ方法 | 假设数据服从正态分布，超出μ±3σ判定为异常 | 单峰分布、无明显偏态 | threshold=3 |
| IQR方法 | 基于四分位距，不受极端值影响 | 有偏分布、含异常值 | multiplier=1.5 |
| Grubbs检验 | 依次检测最大/最小值是否异常 | 少量异常值 | alpha=0.05 |
| 移动平均 | 基于滑动窗口的局部异常 | 时序数据 | window=5 |

### 1.2 机器学习类算子

| 算子 | 原理 | 适用场景 | 参数 |
|------|------|----------|------|
| 孤立森林 | 随机划分特征空间，孤立点异常分数高 | 高维数据、复杂分布 | contamination=0.1 |
| One-Class SVM | 寻找包含大部分数据的最小超球 | 非线性分布 | nu=0.1 |

### 1.3 深度学习类算子

| 算子 | 原理 | 适用场景 | 参数 |
|------|------|----------|------|
| LSTM自编码器 | 学习时序模式，重构误差高的为异常 | 长序列、有模式 | epochs=50 |
| VAE | 变分自编码器 | 复杂分布 | latent_dim=8 |

## 二、算子选择策略（专利要求）

```
输入：特征向量
    ↓
判断样本量n和自相关性
    ↓
┌─────────────────────────────────────────────────┐
│ n < 1000 且自相关弱 → IQR或3σ                   │
│ 1000 ≤ n < 10000 且自相关强 → 孤立森林          │
│ n ≥ 10000 且自相关强 → LSTM自编码器             │
│ 检测到显著周期 → 季节性分解+异常检测            │
│ 特征维度 > 50 → 多变量异常检测                  │
└─────────────────────────────────────────────────┘
```

## 三、专利参数要求

| 参数 | 要求值 | 说明 |
|------|--------|------|
| 孤立森林污染率 | 0.1 | 取值范围[0.05, 0.20] |
| 异常分数阈值 | 0.5 | s≥0.5标记为异常 |
| LSTM重构误差阈值 | 95%分位数 | reconstruction_error≥P95 |
| IQR系数 | 1.5 | Q1-1.5×IQR 到 Q3+1.5×IQR |
| 3σ阈值 | 3 | μ±3σ |

## 四、算子接口

```python
def operator_detect(series: pd.Series, **params) -> tuple:
    """
    算子检测接口

    Returns:
        (scores, anomaly_mask)
        - scores: 异常分数数组
        - anomaly_mask: 布尔数组，True表示异常
    """
```

## 五、参考实现

### 5.1 孤立森林

```python
from sklearn.ensemble import IsolationForest

X = series.values.reshape(-1, 1)
iso_forest = IsolationForest(
    contamination=0.1,  # 专利要求值
    n_estimators=100,
    random_state=42
)
iso_forest.fit(X)

# 预测
predictions = iso_forest.predict(X)  # -1表示异常
anomaly_mask = predictions == -1

# 异常分数
scores = -iso_forest.score_samples(X)  # 转换为正数
```

### 5.2 IQR方法

```python
Q1 = series.quantile(0.25)
Q3 = series.quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR  # 专利系数
upper_bound = Q3 + 1.5 * IQR

anomaly_mask = (series < lower_bound) | (series > upper_bound)
```

## 六、性能对比

| 算子 | 检测准确率 | 误报率 | 计算时间 |
|------|-----------|--------|----------|
| IQR | 75-85% | 10-15% | 低 |
| 3σ | 70-80% | 15-20% | 低 |
| 孤立森林 | 85-95% | 5-10% | 中 |
| One-Class SVM | 80-90% | 8-12% | 中 |
| LSTM-AE | 90-98% | 2-5% | 高 |
