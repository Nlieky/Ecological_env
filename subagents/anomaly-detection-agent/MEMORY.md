# 异常检测子智能体 - 专业记忆

## 异常特征（5 类，数据层，依据参考资料）

| 特征 | 定义 | 算子 |
|------|------|------|
| 平稳 | 标准差/变异系数低于阈值 | `constant_detector` |
| 突变 | 相邻点变化幅度超阈值 | `change_point_detector` |
| 趋势 | 单向均匀升降，二阶导≈0 | `trend_detector` |
| 周期 | FFT 检测显著周期性 | `periodicity_detector` |
| 高频波动 | 分钟级突升突降/归零 | `high_freq_detector` |

## 评分 + 可信度（参考资料定义）

- **异常分数**：孤立森林 a∈[0,1]，阈值 **0.5**
- **模式相似度**：匹配 5 类特征的相似度，≥0.7 算匹配
- **可信度公式**：`confidence = 0.6×异常分数 + 0.4×模式相似度`

## 算子库（`shared/operators/`，禁止本地重实现）

| 类别 | 算子 |
|------|------|
| specialized | constant / change_point / trend / high_freq / periodicity |
| machine_learning | isolation_forest / lof / hbos / one_class_svm |
| deep_learning | lstm_autoencoder（初版降级用孤立森林）/ variational_autoencoder |

## 关键约束

- **不输出 violation_type** — 违规模式判定是规则推理的活
- **算子去 violation_type** — constant/periodicity 等算子只输出特征 + score，不判违规

## 输出契约

`anomaly_result.json`：`anomalies`（含 data_type/indicator/timestamp/**features**/score/**confidence**/pattern_similarity/value/expected_range）+ `summary`（by_feature/by_indicator）+ `chartData`
