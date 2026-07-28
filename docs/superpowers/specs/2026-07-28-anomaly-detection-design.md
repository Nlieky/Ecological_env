# 异常检测子智能体优化设计

> 2026-07-28 · brainstorm 产出 · 子智能体优化系列(2/4)
> 依据:用户参考资料(docs/参考资料2.txt)定义的异常特征 + 评分 + 可信度

## 背景

异常检测子智能体(`anomaly-detection`)存在三个问题:
1. **AGENTS.md 说"从 `shared/operators/` 调算子,禁止本地重实现",但 `run_anomaly_detection_simple.py` 自己实现了 zscore/iqr/isolation_forest**(违背三库一体,算子库白放)
2. **算法简单**:只做单指标 1D 点检测,没有时序模式(恒定/平滑/趋势/周期)的深度检测
3. **specialized 算子越界**:`constant/smoothness/forgery` 自己输出 `violation_type`(判违规模式),违背"异常检测不判违规"

本设计重新定位:**异常检测调算子库算子,检出 5 类异常特征 + 异常分数 + 可信度,不判违规模式**(违规判定在规则推理)。

## 设计原则

1. **调算子库**(兑现三库一体):从 `shared/operators/` 调用,不在脚本里重写
2. **检出特征,不判违规**:异常检测输出"异常点 + 异常特征 + 异常分数 + 可信度";违规模式(插瓶/拟合/稀释/逃避)+ 嫌疑等级在**规则推理**(查知识库的工艺规则 + 违规模式特征库)
3. **异常 ≠ 违规**:指标未超法规阈值时仅属异常,是否违规由规则推理定

## 异常特征(5 类,数据层,依据资料)

| 异常特征 | 定义 | 算子 |
|---|---|---|
| **平稳异常** | 时间窗内标准差/变异系数低于阈值 | `constant_detector`(改造) |
| **突变异常** | 相邻时间点变化幅度超阈值 | `change_point_detector`(现有) |
| **趋势异常** | 单向均匀上升/下降,二阶导≈0 | `trend_detector`(**新写**) |
| **周期异常** | 傅里叶变换检测到显著周期性成分 | `periodicity_detector`(**从 forgery 拆出**) |
| **高频波动异常** | 分钟级突升突降、异常归零 | `high_freq_detector`(**新写**) |

## 评分 + 可信度(资料定义)

- **异常分数**:
  - 孤立森林:分数 a∈[0,1],阈值 **0.5**(a≥0.5 标异常)
  - LSTM 自编码器:重构误差,阈值 **95% 分位数**
- **模式相似度**:异常点匹配 5 类异常特征的相似度,≥0.7 算匹配该特征
- **可信度公式**:`confidence = 0.6 × 异常分数 + 0.4 × 模式相似度`,取值 [0,1]

## 输出契约(`anomaly_result.json`)

```json
{
  "anomalies": [
    {
      "timestamp": "2026-07-14 12:00:00",
      "indicator": "pH",
      "data_type": "effluent",
      "features": ["突变", "平稳"],
      "pattern_similarity": 0.85,
      "score": 0.72,
      "confidence": 0.768,
      "value": 7.5,
      "expected_range": [7.3, 7.6]
    }
  ],
  "summary": {
    "total_anomalies": 1,
    "by_feature": {"突变": 1, "平稳": 1},
    "by_indicator": {"pH": 1}
  }
}
```

**不含 `violation_type`** —— 违规模式由规则推理查知识库判定。

下游影响:
- 规则推理:读 `anomaly_result.anomalies[].features`(异常特征组合),查工艺规则 + 违规模式特征库判违规模式
- 证据链:异常检测 evidence=`{kind:anomaly, count, top:[...]}`(现有,不变)
- 报告可视化:`build_chart` 用 `anomaly_result.anomalies` 在曲线标 markPoint

## 改动清单

| 文件 | 改动 |
|---|---|
| **`run_anomaly_detection_simple.py`** | 删自实现的 zscore/iqr/IF,**改成调 `shared/operators/`**(5 特征算子 + isolation_forest + lstm_autoencoder);评分/可信度按资料公式;输出 `features` + `confidence` |
| **`shared/operators/specialized/constant_detector.py`** | 去 `violation_type`,只输出 `{is_constant, std, score}` |
| **`shared/operators/specialized/change_point_detector.py`** | 确认输出突变特征 + 分数(去违规判定,如有) |
| **`shared/operators/specialized/forgery_detector.py`** | 拆出周期检测 → 新建 `periodicity_detector`;聚类/分布部分先留(后续按业务) |
| **新建 `shared/operators/specialized/trend_detector.py`** | 趋势异常(单向均匀升降,二阶导≈0) |
| **新建 `shared/operators/specialized/high_freq_detector.py`** | 高频波动(分钟级突升突降/归零) |
| **`SOUL.md` / `AGENTS.md`** | 对齐:调算子库(非自实现)、5 类异常特征、不判违规、skill_view 机制(去过时表述) |

## 错误处理

- LLM 没跑脚本 → `failed` → 主智能体重试(全局去自愈,见数据感知 spec)
- 算子库缺算子 → 用现有,缺的标注 TODO(初版不阻塞)
- 某指标数据不足(<算子最小要求)→ 跳过该算子,记录
- LSTM 算子数据不足/失败 → 降级用孤立森林(单评分器)

## 测试

- 算子单元:5 类特征检测器各测(平稳/突变/趋势/周期/高频)+ isolation_forest/lstm 评分
- `run_anomaly_detection_simple.py` 集成:输入 data_result → 输出 anomalies 含 features + confidence
- 端到端:`smoke_test.py` 覆盖(异常检测产出 anomaly_result,features + confidence 非空)

## 决策记录

- **5 类异常特征**:按资料定义(平稳/突变/趋势/周期/高频波动),数据层;不含"关联"(用户说现实可能没有,后续按业务补)
- **调算子库不自己写**:兑现三库一体,旧版本 specialized 改造用(去 violation_type)
- **不判违规模式**:异常≠违规,违规模式 + 嫌疑等级在规则推理(查知识库:工艺规则 pH-COD 协同/氨氮-总氮/质量平衡/多指标同步突降 + 违规模式特征库)
- **可信度公式**:`0.6×异常分数 + 0.4×模式相似度`(资料定义)
- **算子增量**:初版 5 类 + 2 评分器,后续按实际业务补充算子

## 范围

本 spec 仅异常检测子智能体(5 类特征 + 评分 + 可信度)。**违规模式判定、工艺规则、嫌疑等级**属规则推理子智能体(资料已定义,后续 brainstorm)。数据感知见系列(1/4)。
