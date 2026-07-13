# 健康检查API规范

> **状态**: 🚧 待完善
> **最后更新**: 2026-07-08

## 概述

定义系统健康检查接口，用于监控系统各组件状态。

## 接口定义

### 1. 系统健康检查

```
GET /api/health
```

**响应:**
```json
{
  "status": "ok",
  "timestamp": "2026-07-08T10:00:00Z",
  "components": {
    "backend": {"status": "healthy"},
    "hermes_api": {"status": "healthy", "url": "http://localhost:8642"},
    "llm": {"status": "healthy", "model": "LongCat-2.0"}
  }
}
```

### 2. 子智能体状态

```
GET /api/health/subagents
```

**响应:**
```json
{
  "subagents": [
    {"name": "multi-dimensional-data-perception-agent", "status": "ready"},
    {"name": "anomaly-detection-agent", "status": "ready"},
    {"name": "rule-reasoning-agent", "status": "ready"},
    {"name": "disposition-execution-agent", "status": "ready"}
  ]
}
```

### 3. 资源状态

```
GET /api/health/resources
```

**响应:**
```json
{
  "shared": {
    "operators": "available",
    "knowledge": "available",
    "data": "available"
  },
  "sessions": {
    "active": 0,
    "directory": "sessions/"
  }
}
```

## 健康状态定义

| 状态 | 描述 |
|------|------|
| `healthy` | 正常运行 |
| `degraded` | 部分功能受限 |
| `unhealthy` | 不可用 |
| `unknown` | 状态未知 |

---

**待完善**: 具体检查逻辑和阈值
