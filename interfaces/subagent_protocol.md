# 子智能体通信协议

> **版本**: v1.1
> **最后更新**: 2026-07-30
> **目的**: 定义主智能体与子智能体之间的标准化通信协议（对齐当前实现）

---

## 协议概述

主智能体编排 4 个子智能体，靠 **`SESSION_DIR` 目录里的 `*_result.json` 文件**链式传递结果（不是 RPC）。每个子智能体是一次独立的 Hermes AIAgent 子进程（`subagent_entry.py` 共享入口），LLM 读自己的 SKILL.md 选脚本、用 terminal 跑 canonical 脚本处理数据、把结果写回 SESSION_DIR。

---

## 子智能体注册表

| 子智能体名称 | 目录路径 | 主要职责 | 结果文件 |
|-------------|---------|---------|---------|
| `multi-dimensional-data-perception` | `subagents/multi-dimensional-data-perception-agent/` | 数据获取（InfluxDB）、标记缺失、HRT 标注、生成 chartData | `data_result.json` |
| `anomaly-detection` | `subagents/anomaly-detection-agent/` | 异常识别（5 特征 + 孤立森林点位级）、置信度评估 | `anomaly_result.json` |
| `rule-reasoning` | `subagents/rule-reasoning-agent/` | 法规/工艺规则推理、违规判定、嫌疑等级 | `rule_reasoning_result.json` |
| `disposition-execution` | `subagents/disposition-execution-agent/` | 预警分级、工单生成、处置行动 | `disposition_result.json` |

---

## 通信流程

```
主智能体 call_subagent(name, task)
   │
   │  subprocess 启动 subagent_entry.py，设环境变量:
   │    HERMES_HOME=<该子智能体目录>   SESSION_DIR=<共享会话目录>
   │    SUBAGENT_NAME=<名字>           LLM_BASE_URL/KEY/MODEL=...
   │
   ↓
子智能体 AIAgent 会话（HERMES_HOME 作用域）
   │  skill_view 读自己的 SKILL.md → terminal 跑 canonical 脚本
   │  脚本读上一步的 *_result.json（链式）→ 调 shared 算子/知识 → 写自己的 *_result.json
   ↓
主智能体读回 *_result.json → 精简成 summary 回传给 LLM → 决定下一步
```

### 环境变量协议

子智能体子进程启动时由 `call_subagent.py` 注入：

| 变量名 | 必需 | 说明 |
|-------|-----|------|
| `HERMES_HOME` | ✅ | 该子智能体根目录（身份文件 + skills 从这里读） |
| `SESSION_DIR` | ✅ | 共享会话目录（task.json / *_result.json 中转） |
| `SUBAGENT_NAME` | ✅ | 子智能体名 |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | ✅ | LLM 配置（同时设 OPENAI_* 兼容 hermes） |
| `PYTHONPATH` | ✅ | 项目根（import shared.* 用） |

---

## 输入格式 (task.json)

`call_subagent.py` 写入 SESSION_DIR/task.json：

```json
{
  "task_id": "task_20260708143022_abc123",
  "task": "检测最近24小时出水COD异常情况",
  "context": {},
  "output_format": "json",
  "timeout": 300
}
```

> 注：实际子智能体靠 `SESSION_DIR/data_result.json` 链式拿上一步数据，`context` 多为空。`task` 字符串要短（<200 字符），太长会让子智能体 LLM 子进程崩溃。

---

## 输出格式 (*_result.json)

所有结果文件共享同一顶层信封：

```json
{
  "task_id": "task_...",
  "status": "completed",            // "completed" | "failed"
  "result": { ... },                // 各子智能体专有（见下）；失败时 {"error": "..."}
  "metadata": {
    "subagent": "anomaly-detection-agent",
    "timestamp": "2026-07-08T14:30:45.123456",
    "llm_driven": true
  }
}
```

> 主智能体**不读原始 result 文件**（`read_result` 已废弃），只看 `call_subagent` 回传的精简摘要（status + summary + 关键数字）。result 文件是子智能体之间链式传递用的。

---

## 各子智能体专有结果（result 字段）

### 1. data_result.json（数据感知）

```json
"result": {
  "influent": [{"timestamp":"2026-07-14 00:00:00","pH":7.43,"COD":68.03,"TN":16.78,"NH3-N":4.12,"TP":0.32,"SS":null,"flow_rate":477.67,"discharge_volume":1719.61}, ...],
  "effluent": [ ... ],
  "metadata": {
    "time_range": "2026-07-14 至 2026-07-14",
    "indicators": ["pH","COD","TN","NH3-N","TP","SS","flow_rate","discharge_volume"],
    "chart_indicators": ["pH","COD"],     // 用户指定的曲线指标（null=全部）
    "hrt_hours": 2,
    "missing_points": [],
    "data_source": "influxdb"
  },
  "chartData": [{"title":"进水水质趋势","option":{...echarts...}}, ...]
}
```

### 2. anomaly_result.json（异常检测）

```json
"result": {
  "anomalies": [
    {"indicator":"化学需氧量浓度（毫克/升）","data_type":"influent","timestamp":"2026-07-14 12:00:00","features":["高频波动"],"score":0.62,"value":501.93,"confidence":0.55}
  ],
  "summary": {"total_anomalies": 11, "by_data_type": {"influent":4,"effluent":7}, "by_indicator": {...}, "by_feature": {...}}
}
```

> 异常是**点位级**（孤立森林逐点判定），`timestamp` 是真实异常时刻。5 特征（平稳/突变/趋势/周期/高频波动）是序列级判断，挂在匹配的点位上。

### 3. rule_reasoning_result.json（规则推理）

```json
"result": {
  "has_violation": true,
  "suspicion_level": "low",          // none|low|medium|high
  "suspicion_level_cn": "低",
  "violation_types": ["暗管偷排"],   // 命中的违规类型
  "violation_type_names": [...],
  "patterns": [...]                  // 触发的违规模式
}
```

### 4. disposition_result.json（研判处置）

```json
"result": {
  "alert": {"level": "general", "level_cn": "一般", "disposition": "持续监控"},
  "work_order": {"id": "WO-...", "inspection_points": [...], "recommended_actions": [...], "legal_references": [...]},
  "fusion": {"fused_confidence": 0.42}
}
```

> 置置融合异常置信度 + 规则嫌疑为最终 fused_confidence，决定预警等级（严重/较重/一般）。

---

## 错误处理

失败时 `status: "failed"`，`result: {"error": "..."}`。常见错误：子智能体子进程超时（`SUBAGENT_TIMEOUT`）、LLM 后端不可用、数据缺失。主智能体应如实告知用户，不假装成功编数据。

---

## 性能

一轮完整 4 子智能体 pipeline 约 30-90s（每个子智能体 2-3 次工具调用）。单子智能体 `SUBAGENT_TIMEOUT=600s`。

---

## 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| v1.0 | 2026-07-08 | 初始理想化设计稿 |
| v1.1 | 2026-07-30 | 对齐实际实现：结果文件名（rule_reasoning_result.json）、status（completed/failed）、顶层信封结构、各子智能体真实 result 字段、通信改为文件链式传递说明 |
