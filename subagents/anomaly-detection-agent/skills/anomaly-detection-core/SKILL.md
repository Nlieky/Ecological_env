---
name: anomaly-detection-core
description: 异常检测——调算子库检测 5 类异常特征（平稳/突变/趋势/周期/高频波动），输出异常分数与可信度。当任务涉及"异常"、"不正常"、"突变"、"波动"、"是否正常"、"检测"时使用。务必使用——异常检测是违规研判的数据基础，没有特征检出后续规则推理无法判定违规。
---

# 异常检测技能

## 你做什么

你调用一个脚本（`run_anomaly_detection_simple.py`），它从 `data_result.json`（数据感知产出）读取数据，用算子库检测 5 类异常特征。脚本自动完成所有工作：
- 从 `SESSION_DIR/data_result.json` 链式读取上游数据（不需要传参数）
- 调用 5 类特征算子（constant / change_point / trend / periodicity / high_freq）
- 用孤立森林算异常分数（a≥0.5 标异常）
- 算可信度（0.6×异常分数 + 0.4×模式相似度）
- 生成 chartData（供前端标异常点）

**你的工作就是：调脚本 → 确认完成。**

## 怎么调

```bash
python "$HERMES_HOME/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py"
```

不需要传参数。脚本自动从 SESSION_DIR 读 `data_result.json`（数据感知写的），按上游的时间范围检测。

### 好 vs 差

```
✅ 好：python "...run_anomaly_detection_simple.py"
   → 脚本自动读 data_result，按上游时间范围检测

❌ 差：python "...run_anomaly_detection_simple.py" --hours 24
   → 主智能体说"7月14日"，数据感知取了14日，你却自己加 --hours 24 覆盖了时间范围
```

## 执行流程

1. 调脚本（无参数）
2. 响应："✅ 脚本执行完成"

## 5 类异常特征

脚本检测这 5 类（数据层，依据参考资料）：

| 特征 | 什么意思 | 算子 |
|------|---------|------|
| 平稳 | 标准差极低，数值几乎不变 | constant_detector |
| 突变 | 相邻时间点变化幅度大 | change_point_detector |
| 趋势 | 单向均匀上升或下降 | trend_detector |
| 周期 | FFT 检测到人为周期性 | periodicity_detector |
| 高频波动 | 频繁突升突降或归零 | high_freq_detector |

**你不判定这些特征意味着什么违规**——那是规则推理的活。你只检出特征 + 分数 + 可信度。

## 为什么只调脚本、不做别的

**不解析 JSON / 不生成报告**：你的结果（`anomaly_result.json`）由下游规则推理直接读文件，由主智能体整合报告。你解析了也没人看。

**不手写文件**：结果只能由脚本产出（含正确的 features/score/confidence/chartData 格式）。你手写会破坏格式，规则推理读不了。

**不自己实现算子**：算子库在 `shared/operators/`，脚本已经调好了。你在脚本里自己写 Z-score/IQR 会违背三库一体，且结果格式不对。

**不判定违规**：你只输出异常特征（平稳/突变/趋势/周期/高频）。这些特征组合意味着什么违规（插瓶/稀释/拟合/逃避），由规则推理查知识库判定。

## 脚本输出

保存到 `anomaly_result.json`（SESSION_DIR 或子智能体默认目录），包含：
- `anomalies`：异常列表（每个含 indicator/timestamp/**features**/score/**confidence**/value）
- `summary`：按特征/指标统计
- `chartData`：可视化（曲线 + 异常 markPoint）

下游规则推理链式消费此文件。
