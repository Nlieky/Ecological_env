# 异常检测子智能体 - 专业记忆

## 异常类型（5 类，对齐真实脚本）

| 类型 | 标识 | 特征 |
|------|------|------|
| 边界异常 | `boundary` | 时序首尾异常点 |
| 恒定值异常 | `constant` | 数值长时间不变（>2h），波动 < 正常的 1/10 |
| 突变异常 | `spike` | 突然跳变（>3σ），短时恢复 |
| 趋势异常 | `trend` | 持续上升 / 下降 |
| 点异常 | `point` | 单点偏离正常范围 |

## 算子库（全局 `shared/operators/`）

### 统计类
- Z-score、IQR、3σ、Grubbs

### 机器学习
- 孤立森林（IsolationForest）、One-Class SVM、LOF、HBOS

### 深度学习
- LSTM 自编码器、变分自编码器（VAE）

### 专用
- constant_detector（恒定）、change_point_detector（突变）、smoothness_detector（平滑）、forgery_detector（伪造）

## 检测策略

- **算子选择**：新数据源先用统计类；有历史用 ML；复杂模式用 DL；组合用多算子投票
- **投票机制**：至少 2 个算子一致才算异常
- **综合评分**：各算子分数的均值

## 置信度评估

- 多算子结果一致性（votes）
- 与历史模式相似度
- 检测结果稳定性

## 误报控制

- 结合工艺知识过滤（如设备正常稳定运行 ≠ 恒定异常）
- 合理阈值 + 时间窗口减少瞬时干扰
- 考虑工况变化

## 输出契约

`anomaly_result.json`：`anomalies`（含 data_type/indicator/timestamp/type/score/value/votes/expected_range）+ `summary`。**只产出异常，不判定违规**——违规交给 `rule-reasoning`。
