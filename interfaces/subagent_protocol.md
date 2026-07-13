# 子智能体通信协议

> **版本**: v1.0
> **最后更新**: 2026-07-08
> **目的**: 定义主智能体与子智能体之间的标准化通信协议

---

## 协议概述

本协议定义了废水监测系统中主智能体与4个子智能体之间的通信标准，确保：
- **输入输出格式统一**
- **数据流向清晰可追踪**
- **错误处理标准化**
- **性能可监控**

---

## 子智能体注册表

| 子智能体名称 | 目录路径 | 主要职责 | 结果文件 |
|-------------|---------|---------|---------|
| `multi-dimensional-data-perception` | `subagents/multi-dimensional-data-perception-agent/` | 多源数据获取、时序对齐、数据质量控制 | `data_result.json` |
| `anomaly-detection` | `subagents/anomaly-detection-agent/` | 异常识别、违规检测、置信度评估 | `anomaly_result.json` |
| `rule-reasoning` | `subagents/rule-reasoning-agent/` | 法规匹配、工艺校验、合规判定 | `rule_result.json` |
| `disposition-execution` | `subagents/disposition-execution-agent/` | 预警分类、工单生成、处置协调 | `disposition_result.json` |

---

## 通信流程

```
┌─────────────┐
│ 主智能体    │
└──────┬──────┘
       │
       │ 1. 写入 task.json
       ├──────────────────────┐
       │                      ↓
       │              ┌───────────────┐
       │              │ SESSION_DIR   │
       │              │ ├── task.json │
       │              │ └── result.json│
       │              └───────┬───────┘
       │                      │
       │ 2. 启动子进程        │
       │                      │
       │              ┌───────↓───────┐
       │              │ 子智能体进程  │
       │              │ (HERMES_HOME)│
       │              └───────┬───────┘
       │                      │
       │ 3. 读取 result.json  │
       ├──────────────────────┘
       │
       ↓
┌─────────────┐
│ 整合结果    │
└─────────────┘
```

### 环境变量协议

子智能体进程启动时必须设置以下环境变量：

| 变量名 | 必需 | 说明 | 示例值 |
|-------|-----|------|--------|
| `HERMES_HOME` | ✅ | 子智能体的根目录 | `E:/project/Ecological_env/subagents/anomaly-detection-agent` |
| `SESSION_DIR` | ✅ | 会话目录路径 | `E:/project/Ecological_env/sessions/session_20260708_143022` |
| `SUBAGENT_NAME` | ✅ | 子智能体名称 | `anomaly-detection` |
| `LLM_BASE_URL` | ✅ | LLM API 地址 | `https://api.longcat.chat/openai/v1` |
| `LLM_API_KEY` | ✅ | LLM API 密钥 | `ak_xxx` |
| `LLM_MODEL` | ✅ | 模型名称 | `LongCat-2.0` |
| `LLM_PROVIDER` | ✅ | 提供商 | `custom` |

---

## 输入格式 (task.json)

### 标准任务结构

```json
{
  "task_id": "task_20260708143022_abc123",
  "task": "检测最近24小时出水COD异常情况",
  "context": {
    "time_range": {
      "start": "2026-07-07T14:30:00Z",
      "end": "2026-07-08T14:30:00Z"
    },
    "data_sources": ["influent", "effluent"],
    "parameters": {
      "metrics": ["COD", "TN", "TP", "pH", "AN"],
      "threshold_method": "statistical"
    },
    "previous_results": {
      "data_result.json": {
        "status": "completed",
        "task_id": "task_xxx"
      }
    }
  },
  "output_format": "json",
  "timeout": 300
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|-----|------|------|------|
| `task_id` | string | ✅ | 全局唯一任务标识，格式：`task_{timestamp}_{random}` |
| `task` | string | ✅ | 自然语言任务描述 |
| `context` | object | ❌ | 额外上下文信息 |
| `context.time_range` | object | ❌ | 时间范围 |
| `context.data_sources` | array | ❌ | 数据来源列表 |
| `context.parameters` | object | ❌ | 算法参数 |
| `context.previous_results` | object | ❌ | 前序子智能体结果（用于依赖链） |
| `output_format` | string | ✅ | 输出格式，固定为 `json` |
| `timeout` | number | ✅ | 超时时间（秒） |

---

## 输出格式 (result.json)

### 标准结果结构

```json
{
  "task_id": "task_20260708143022_abc123",
  "status": "completed",
  "subagent": "anomaly-detection",
  "result": {
    "anomalies": [...],
    "violations": [...],
    "confidence": 0.87
  },
  "metadata": {
    "started_at": "2026-07-08T14:30:22Z",
    "completed_at": "2026-07-08T14:30:45Z",
    "duration_ms": 23000,
    "model": "LongCat-2.0",
    "llm_calls": 3,
    "tokens_used": 1250
  },
  "error": null
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|-----|------|------|------|
| `task_id` | string | ✅ | 必须与输入 task_id 匹配 |
| `status` | string | ✅ | 状态：`completed` \| `failed` \| `timeout` |
| `subagent` | string | ✅ | 子智能体名称 |
| `result` | object | ❌ | 具体结果数据（status=completed时必需） |
| `metadata` | object | ✅ | 执行元数据 |
| `metadata.started_at` | string | ✅ | 开始时间（ISO 8601） |
| `metadata.completed_at` | string | ✅ | 完成时间（ISO 8601） |
| `metadata.duration_ms` | number | ✅ | 执行耗时（毫秒） |
| `metadata.model` | string | ✅ | 使用的模型 |
| `metadata.llm_calls` | number | ✅ | LLM 调用次数 |
| `metadata.tokens_used` | number | ✅ | Token 消耗量 |
| `error` | string/null | ❌ | 错误信息（status=failed/timeout时必需） |

---

## 各子智能体专用结果格式

### 1. multi-dimensional-data-perception (data_result.json)

```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "subagent": "multi-dimensional-data-perception",
  "result": {
    "data_summary": {
      "records_count": 1440,
      "time_range": {
        "start": "2026-07-07T14:30:00Z",
        "end": "2026-07-08T14:30:00Z"
      },
      "sources": ["influent", "effluent"]
    },
    "processed_data": {
      "influent": {
        "COD": {"avg": 120.5, "min": 98, "max": 145, "std": 12.3},
        "TN": {"avg": 25.2, "min": 20, "max": 31, "std": 3.1},
        "TP": {"avg": 3.1, "min": 2.5, "max": 4.2, "std": 0.4},
        "pH": {"avg": 7.2, "min": 6.8, "max": 7.6, "std": 0.2},
        "AN": {"avg": 18.5, "min": 15, "max": 22, "std": 2.0},
        "flow_rate": {"avg": 450, "min": 400, "max": 500, "std": 25}
      },
      "effluent": {
        "COD": {"avg": 42.3, "min": 35, "max": 52, "std": 5.1},
        "TN": {"avg": 11.8, "min": 9, "max": 15, "std": 1.8},
        "TP": {"avg": 0.38, "min": 0.25, "max": 0.52, "std": 0.08},
        "pH": {"avg": 7.0, "min": 6.7, "max": 7.3, "std": 0.15},
        "AN": {"avg": 4.2, "min": 3, "max": 6, "std": 0.8},
        "flow_rate": {"avg": 445, "min": 395, "max": 495, "std": 24}
      }
    },
    "quality_metrics": {
      "completeness": "98.5%",
      "missing_records": 21,
      "outlier_count": 3
    }
  },
  "metadata": { ... },
  "error": null
}
```

### 2. anomaly-detection (anomaly_result.json)

```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "subagent": "anomaly-detection",
  "result": {
    "anomalies": [
      {
        "type": "spike",
        "metric": "COD",
        "location": "effluent",
        "timestamp": "2026-07-08T10:15:00Z",
        "value": 52.3,
        "threshold": 50,
        "severity": "high",
        "confidence": 0.92
      },
      {
        "type": "trend",
        "metric": "TN",
        "location": "effluent",
        "time_range": {
          "start": "2026-07-08T08:00:00Z",
          "end": "2026-07-08T14:30:00Z"
        },
        "trend": "increasing",
        "rate": 0.8,
        "severity": "medium",
        "confidence": 0.78
      }
    ],
    "violations": [
      {
        "violation_type": "COD超限",
        "standard": "一级A标准",
        "threshold": 50,
        "actual": 52.3,
        "exceed_ratio": 0.046,
        "duration_minutes": 30,
        "confidence": 0.89
      }
    ],
    "overall_assessment": {
      "status": "abnormal",
      "anomaly_count": 5,
      "violation_count": 1,
      "confidence": 0.87
    }
  },
  "metadata": { ... },
  "error": null
}
```

### 3. rule-reasoning (rule_result.json)

```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "subagent": "rule-reasoning",
  "result": {
    "compliance_status": "non_compliant",
    "applicable_standards": [
      {
        "name": "城镇污水处理厂污染物排放标准（GB 18918-2002）",
        "level": "一级A标准",
        "items": [
          {"parameter": "COD", "limit": 50, "unit": "mg/L"},
          {"parameter": "TN", "limit": 15, "unit": "mg/L"},
          {"parameter": "TP", "limit": 0.5, "unit": "mg/L"},
          {"parameter": "AN", "limit": 5, "unit": "mg/L"},
          {"parameter": "pH", "limit": "6-9", "unit": ""}
        ]
      }
    ],
    "reasoning_chain": [
      {
        "step": 1,
        "rule": "COD限值检查",
        "input": {"parameter": "COD", "value": 52.3},
        "rule_reference": "GB 18918-2002 一级A标准",
        "conclusion": "COD浓度52.3mg/L超过一级A标准限值50mg/L",
        "confidence": 0.95
      },
      {
        "step": 2,
        "rule": "工艺机理校验",
        "input": {
          "pH": 7.0,
          "COD": 52.3,
          "TN": 12.5
        },
        "rule_reference": "pH-COD协同关系",
        "conclusion": "pH正常范围内，COD异常升高符合典型超标特征",
        "confidence": 0.82
      }
    ],
    "final_conclusion": {
      "compliance": "non_compliant",
      "primary_violation": "COD超限",
      "confidence": 0.87,
      "requires_alert": true
    }
  },
  "metadata": { ... },
  "error": null
}
```

### 4. disposition-execution (disposition_result.json)

```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "subagent": "disposition-execution",
  "result": {
    "alert_level": "urgent",
    "alert_classification": {
      "level": 2,
      "name": "橙色预警",
      "criteria": "主要污染物超标，需立即处置"
    },
    "work_order": {
      "id": "WO-20260708-001",
      "title": "出水COD超限紧急处置",
      "priority": "high",
      "created_at": "2026-07-08T14:31:00Z",
      "assigned_to": "运营班组",
      "deadline": "2026-07-08T16:00:00Z",
      "actions": [
        {"id": 1, "action": "调整曝气量", "target": "提高DO浓度", "priority": "高"},
        {"id": 2, "action": "加强污泥回流", "target": "提高生化效率", "priority": "高"},
        {"id": 3, "action": "检查进水水质", "target": "排除冲击负荷", "priority": "中"}
      ],
      "estimated_resolution_time": "2小时"
    },
    "notification": {
      "channels": ["feishu", "sms"],
      "recipients": ["运营主管", "技术负责人"],
      "message": "【紧急预警】出水COD超限，已生成工单WO-20260708-001，请立即处置"
    }
  },
  "metadata": { ... },
  "error": null
}
```

---

## 错误处理协议

### 错误响应格式

```json
{
  "task_id": "task_xxx",
  "status": "failed",
  "subagent": "anomaly-detection",
  "result": null,
  "metadata": { ... },
  "error": {
    "code": "DATA_UNAVAILABLE",
    "message": "无法获取指定时间范围的数据",
    "details": {
      "time_range": "2026-07-07 to 2026-07-08",
      "available_range": "2026-07-01 to 2026-07-06"
    }
  }
}
```

### 标准错误代码

| 错误代码 | 说明 | 处理建议 |
|---------|------|----------|
| `TASK_INVALID` | task.json 格式错误或缺少必需字段 | 检查输入格式 |
| `DATA_UNAVAILABLE` | 无法获取所需数据 | 检查数据源或时间范围 |
| `LLM_ERROR` | LLM 调用失败 | 检查API配置或重试 |
| `TIMEOUT` | 执行超时 | 增加timeout或优化任务 |
| `INTERNAL_ERROR` | 子智能体内部错误 | 查看详细错误日志 |

---

## 性能监控协议

每个子智能体执行必须记录以下性能指标：

| 指标 | 说明 | 目标值 |
|-----|------|--------|
| `duration_ms` | 总执行时间 | < 30秒 |
| `llm_calls` | LLM调用次数 | 最小化 |
| `tokens_used` | Token消耗量 | 最小化 |
| `memory_mb` | 内存峰值 | < 500MB |

---

## 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| v1.0 | 2026-07-08 | 初始版本，定义基础协议 |
