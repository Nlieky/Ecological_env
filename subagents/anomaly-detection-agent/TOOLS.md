# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your* specifics — the stuff that's unique to your setup.

## Operator Library

### Statistical Operators

| 算子 | 适用场景 | 参数 | 路径 |
|------|---------|------|------|
| IQR | 对称分布数据 | k=1.5 | shared/operators/statistical/iqr.py |
| Z-score | 正态分布数据 | threshold=3 | shared/operators/statistical/zscore.py |
| Grubbs | 单个离群值 | alpha=0.05 | shared/operators/statistical/grubbs.py |

### ML Operators

| 算子 | 适用场景 | 参数 | 路径 |
|------|---------|------|------|
| Isolation Forest | 高维数据 | contamination=0.1 | shared/operators/ml/isolation_forest.py |
| One-Class SVM | 非线性数据 | nu=0.05 | shared/operators/ml/one_class_svm.py |
| LOF | 局部密度异常 | n_neighbors=20 | shared/operators/ml/lof.py |

### DL Operators

| 算子 | 适用场景 | 参数 | 路径 |
|------|---------|------|------|
| LSTM-AE | 时序异常 | sequence_length=24 | shared/operators/deep_learning/lstm_autoencoder.py |
| VAE | 生成异常 | latent_dim=8 | shared/operators/deep_learning/vae.py |

## Anomaly Detection Thresholds

### Anomaly Types

| 异常类型 | 检测方法 | 阈值 |
|---------|---------|------|
| 平稳异常 | 标准差检测 | std < 0.1 |
| 突变异常 | 变化率检测 | change_rate > 3σ |
| 趋势异常 | 线性回归斜率 | \|slope\| > 0.05 |
| 周期异常 | FFT频谱分析 | 异常频率分量 |
| 高频波动 | 方差检测 | variance > threshold |

### Violation Detection Thresholds

| 违规类型 | 判定条件 | 置信度阈值 |
|---------|---------|-----------|
| 插瓶干扰 | 恒定≥2h, 值80-100%, std<0.1 | ≥0.9 高风险 |
| 稀释排放 | 降幅≥50%, 去除率>95% | ≥0.8 高风险 |
| 人工拟合 | R²>0.99, 低方差 | ≥0.6 中风险 |
| 恶意逃避 | 缺失率>20%, 规律性 | ≥0.7 中风险 |

## Confidence Evaluation

| 方法 | 权重 | 说明 |
|------|------|------|
| 算子一致性 | 0.4 | 多算子投票一致性 |
| 历史模式对比 | 0.3 | 与历史异常相似度 |
| 检测稳定性 | 0.3 | 时间窗口内稳定性 |

## Related

- [Agent workspace](/concepts/agent-workspace)
