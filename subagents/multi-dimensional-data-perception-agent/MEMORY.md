# 多维数据感知子智能体 - 专业记忆

## 数据源

| 数据 | 来源 |
|------|------|
| 进水/出水 | InfluxDB 2.7（bucket=`monitoring-data`, org=`ecological_env`） |
| 数据源切换 | `.env` 的 `MONITORING_DATA_SOURCE`（influxdb / csv 回退） |

## 监测指标

pH、COD、TN、NH3-N（氨氮）、TP（总磷）、SS（悬浮物）、flow_rate（流量）、discharge_volume（排放量）

## 数据理念（监控）

- **异常值和缺失值是监控对象**，绝不清洗/插值/标准化
- 缺失 = 数据质量问题（客观标记 `missing_points`），不是要补的数
- 标准化交给下游异常检测按算法需要自己做
- **零分析**：只取数 + 标记缺失 + 标注 HRT，不判定任何异常

## 水力停留时间 (HRT)

- **取值：2 小时**（当前工艺领域常量）
- 标注进 `metadata.hrt_hours`，供下游（规则推理）按需做进水出水时间对齐
- **数据感知本身不做对齐**——进/出水各自忠实取

## 输出契约

`data_result.json`：`influent`（原始记录）+ `effluent`（原始记录）+ `metadata`（time_range / indicators / **hrt_hours** / **missing_points** / data_source）+ `chartData`（可视化）

下游 `anomaly-detection` 链式消费此文件。
