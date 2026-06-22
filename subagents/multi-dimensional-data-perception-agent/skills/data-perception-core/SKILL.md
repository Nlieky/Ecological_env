---
name: data-perception-core
description: 获取并预处理多维时序数据。**触发条件**：当用户查询提到"进水"、"出水"、"监测数据"、"数据"、"指标"或时间范围（"最近N小时"、"今天"、"昨天"）时调用。自动完成数据获取（CSV）、时间对齐（进水-出水2小时滞后）、数据清洗、字段标准化（中文字段名→英文）。支持指标：pH、COD、TN、NH3-N、TP、SS、流量。这是数据分析的第一步，输出预处理数据给 anomaly-detection、correlation-analysis、trend-analysis 等后续技能使用。
---

# 多维数据感知

## 调用参数

传递给此技能的参数格式：

```json
{
  "task_id": "唯一任务ID（可选）",
  "query": "原始用户查询",
  "requirements": {
    "data_source": "influent|effluent|both",
    "indicators": ["pH", "COD", ...],
    "time_range": {
      "hours_back": 数字,
      "start": "ISO时间戳",
      "end": "ISO时间戳"
    }
  }
}
```

**参数推断规则**:
- `data_source`: "出水"→"effluent"，"进水"→"influent"，未指定→"both"
- `indicators`: 从查询中提取，未指定则使用默认["pH", "COD"]
- `time_range`: "最近24小时"→{"hours_back": 24}

## 输出格式

```json
{
  "status": "success|error",
  "processed_data": {
    "influent": [{"timestamp": "...", "pH": 7.2, "COD": 45.3, ...}, ...],
    "effluent": [...]
  },
  "quality_report": {
    "completeness": 0.95,
    "anomaly_rate": 0.02,
    "missing_count": 10,
    "time_range_actual": {"start": "...", "end": "..."}
  }
}
```

## 内部处理流程

此技能**自动完成**以下步骤（无需 LLM 预处理）：
1. **数据获取** - 调用 historical_data_fetcher 从 CSV 获取数据
2. **时间对齐** - 补偿进水-出水2小时处理滞后
3. **数据清洗** - 处理缺失值、异常值（超出物理范围的值）
4. **字段标准化** - 中文字段名转英文（"pH值"→"pH"）

## 错误处理

| 错误情况 | LLM 处理方式 |
|---------|-------------|
| 数据文件不存在 | 向用户说明数据不可用，询问其他时间范围 |
| 时间范围无数据 | 返回最近数据，说明实际时间范围 |
| 字段缺失 | 跳过该指标，说明可用指标 |
| 数据质量差（异常率>50%） | 提示传感器可能有问题，建议检查传感器 |

## 后续调用

此技能的输出（`processed_data`）应传递给：
- **anomaly-detection** - 异常检测
- **correlation-analysis** - 相关性分析
- **trend-analysis** - 趋势分析

## 详细文档

- [数据获取 API](references/data-acquisition.md)
- [配置参数](references/configuration.md)
- [质量阈值](references/quality-thresholds.md)
