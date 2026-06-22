---
name: anomaly-detection-core
description: 时序数据异常点检测。**触发条件**：当用户查询提到"异常"、"不正常"、"突变"、"趋势"、"是否正常"、"检测异常"时调用。检测异常时间段、异常分数、异常点位置，不判定违规性质。使用统计算子（3σ、IQR、Grubbs）、ML算子（孤立森林、One-Class SVM）、深度学习（LSTM自编码器）。需要预处理后的数据（来自 data-perception）作为输入。输出异常点列表传递给 rule-reasoning 进行违规判定。
---

# 异常检测

## 职责范围

**此技能只负责检测异常点，不判定违规性质。**
- ✅ 检测异常时间段、异常分数、异常点位置
- ✅ 识别异常类型（constant、spike、trend、periodic、high-frequency）
- ❌ 不判定违规模式（违规判定由 rule-reasoning 负责）

## 前置条件

**必须有数据**：此技能需要来自 data-perception 的预处理数据。
如果用户查询包含数据需求但尚未调用 data-perception，**先调用 data-perception**。

## 调用参数

```json
{
  "task_id": "唯一任务ID（可选）",
  "query": "原始用户查询",
  "data": {
    "influent": [{"timestamp": "...", "pH": 7.2, "COD": 45.3, ...}, ...],
    "effluent": [...]
  },
  "requirements": {
    "indicators": ["需要检测的指标"],
    "detection_types": ["anomaly"],
    "operators": ["zscore", "iqr", "isolation_forest"]
  }
}
```

**参数推断规则**:
- `indicators`: 从用户查询提取，未指定则检测所有可用指标
- `operators`: 根据数据量自动选择（n<1000→IQR/3σ，1000≤n<10000→isolation_forest）

## 输出格式

```json
{
  "status": "success|error",
  "anomalies": [
    {
      "indicator": "COD",
      "timestamp": "2026-06-22 10:00:00",
      "type": "spike",
      "score": 0.85,
      "value": 85.3,
      "expected_range": [30, 50]
    }
  ],
  "summary": {
    "total_anomalies": 3,
    "by_indicator": {"COD": 2, "pH": 1},
    "by_type": {"spike": 2, "trend": 1}
  }
}
```

## 异常类型定义

| 类型 | 描述 | 检测依据 |
|------|------|----------|
| constant | 数值长时间不变 | 方差接近0 |
| spike | 相邻点剧烈变化 | 差分超过阈值 |
| trend | 均匀上升/下降 | 二阶导数接近0 |
| periodic | 非自然周期变化 | FFT 功率谱 |
| high-frequency | 高频波动 | 符号变化率高 |

## 算子选择策略

| 数据量 | 自相关性 | 推荐算子 |
|--------|---------|----------|
| n < 1000 | 弱 | IQR、3σ |
| 1000 ≤ n < 10000 | 强 | Isolation Forest |
| n ≥ 10000 | 强 | LSTM Autoencoder |

## 错误处理

| 错误情况 | LLM 处理方式 |
|---------|-------------|
| 数据为空 | 提示需要先获取数据，调用 data-perception |
| 数据量不足（<10条） | 提示数据太少，建议扩大时间范围 |
| 指标字段缺失 | 跳过该指标，说明可用指标 |

## 后续调用

此技能的输出（异常点列表）应传递给：
- **rule-reasoning** - 进行违规判定（当用户提到"违规"、"超标"、"瓶装"、"稀释"时）

## 详细文档

- [算子库参考](references/operators.md)
- [算子选择算法](references/operator-selection.md)
