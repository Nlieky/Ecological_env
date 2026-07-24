# 多维数据感知子智能体 - 专业记忆

## 数据源

| 数据 | 路径 |
|------|------|
| 进水 | `data/pollution_water_in.csv` |
| 出水 | `data/pollution_water_out.csv` |

## 监测指标

- pH（酸碱度，正常 6–9）
- COD（化学需氧量，mg/L）
- TN（总氮，mg/L）
- NH3-N（氨氮，mg/L）
- TP（总磷，mg/L）
- SS（悬浮物，mg/L）

## 时间对齐

- **水力停留时间：2 小时**
- 出水 effluent(t) ↔ 进水 influent(t−2h)
- 对比进出水必须按 2h 滞后对齐，否则破坏因果

## 数据质量

- 完整性：缺失率 < 5%
- 准确性：异常值比例 < 1%
- 一致性：进出水逻辑自洽
- 时效性：延迟 < 5 分钟
- 插值：线性插值，不超过 3 个连续缺失点

### 异常值经验阈值
- pH：超出 [0, 14] 为异常
- COD：负值或 > 1000 mg/L 可疑
- 流量：负值为异常

## 大范围查询防截断

- 时间范围 >48h 时，原始数据可能超 127K 字符被截断
- 只要统计 → `get_data.py --summary-only`（输出 `summary_result.json`，~2KB）
- 要原始数据 → 拆成多个 ≤24h 窗口

## 输出契约

`data_result.json`：`influent` + `effluent` + `metadata`。下游 `anomaly-detection` 依赖此文件。
