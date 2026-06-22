---
name: disposition-execution-core
description: 预警分级和处置执行。**触发条件**：当用户查询提到"预警"、"工单"、"通知"、"处置"、"生成预警"、"创建工单"时调用。根据违规结论（来自 rule-reasoning）进行三级预警分级（一般、中度、严重），融合多源检测结果（动态权重适应），生成标准化工单（含证据、法律引用、检查要点），多渠道执行（监管平台推送、飞书通知、本地归档）。支持场景：default（平衡权重）、critical（违规权重高）、normal（异常权重高）。
---

# 预警分级和处置执行

## 职责范围

- 预警分级（一般/中度/严重）
- 多源结果融合（异常检测 + 规则推理）
- 标准化工单生成（证据、法律引用、检查要点）
- 多渠道执行（监管平台、飞书、本地归档）

## 前置条件

**建议先有违规结论**：此技能最好使用来自 rule-reasoning 的违规结论。
如果用户要求"预警"但尚未进行违规判定，**先调用 anomaly-detection 和 rule-reasoning**。

## 调用参数

```json
{
  "task_id": "唯一任务ID",
  "query": "原始用户查询",
  "anomaly_result": {
    "anomalies": [...],
    "summary": "检测到3个异常点"
  },
  "violation_result": {
    "conclusion": {
      "suspicion_level": "high",
      "evidence_points": [...],
      "legal_references": [...]
    }
  },
  "requirements": {
    "alert_scene": "default|critical|normal",
    "execution_channels": ["FeishuPush", "LocalArchive"]
  }
}
```

**参数推断规则**:
- `alert_scene`: 可疑度"高"→"critical"，未指定→"default"
- `execution_channels`: 未指定则根据预警级别自动选择

## 输出格式

```json
{
  "status": "success|error",
  "alert": {
    "level": "serious|moderate|general",
    "reasoning": "高可疑度 + 多个违规模式"
  },
  "fused_result": {
    "conclusion": "综合判定：严重预警",
    "confidence": 0.88,
    "weights_used": {
      "anomaly_sources": 0.6,
      "violation_sources": 0.4
    }
  },
  "work_order": {
    "order_id": "WO_20260622_001",
    "alert_level": "serious",
    "violation_type": "dilution_discharge",
    "evidence": {...},
    "inspection_points": [...],
    "legal_references": [...],
    "timestamp": "2026-06-22 10:00:00"
  },
  "execution_status": {
    "FeishuPush": "success",
    "LocalArchive": "success"
  }
}
```

## 预警分级规则

| 输入条件 | 预警级别 |
|---------|---------|
| 高可疑度 + 多个违规模式 | 严重 |
| 中可疑度 + 单个违规模式 | 中度 |
| 低可疑度 + 无违规模式 | 一般 |

## 融合策略

| 场景 | 异常权重 | 违规权重 |
|------|---------|---------|
| default（默认） | 0.6 | 0.4 |
| critical（关键） | 0.4 | 0.6 |
| normal（正常） | 0.7 | 0.3 |

## 执行渠道选择

| 预警级别 | 执行渠道 |
|---------|---------|
| 严重 | 全部渠道 |
| 中度 | 飞书 + 本地归档 |
| 一般 | 本地归档 |

## 错误处理

| 错误情况 | LLM 处理方式 |
|---------|-------------|
| 缺少违规结论 | 提示需要先进行违规判定 |
| 融合失败 | 使用默认权重，记录警告 |
| 执行失败 | 记录失败渠道，继续其他渠道 |

## 详细文档

- [融合配置](../../shared/configs/consensus_config.yaml)
- [工单模板](references/work-order-template.md)
