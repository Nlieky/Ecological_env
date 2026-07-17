# 后端 API 文档 (v1)

> 后端 FastAPI 作为**数据服务层**，提供核心数据查询与对话历史持久化能力，
> 与独立运行的 Agent 服务（端口 8642）形成清晰职责分离。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API 版本**: v1（前缀 `/api/v1`）
- **数据格式**: JSON
- **认证**: 暂无（后续添加）

## 统一响应格式

所有 v1 端点返回统一的 `StandardResponse` 结构：

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "metadata": { ... }
}
```

失败时 `success` 为 `false`，并在 `error` 中返回错误码与消息：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "CONVERSATION_NOT_FOUND",
    "message": "对话 xxx 不存在"
  },
  "metadata": null
}
```

---

## 核心端点

### 1. 实时监测数据

#### 获取实时数据

```bash
GET /api/v1/monitoring/realtime
```

返回最新的进水、出水监测数据，包括 pH、COD、TN、TP 等指标。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "timestamp": "2026-07-17T15:30:00",
    "influent": { "pH": 7.2, "COD": 150.5, "TN": 25.3, "TP": 3.1 },
    "effluent": { "pH": 6.8, "COD": 35.2, "TN": 8.5, "TP": 0.3 },
    "flow_rate": 120.5,
    "quality_score": 0.95
  },
  "metadata": { "timestamp": "2026-07-17T15:30:00", "data_source": "monitoring_system" }
}
```

#### 获取数据质量

```bash
GET /api/v1/monitoring/quality?time_range=24h
```

| 参数        | 类型   | 默认  | 说明                 |
| ----------- | ------ | ----- | -------------------- |
| `time_range` | string | `24h` | 时间范围（24h/7d/30d）|

**响应示例：**

```json
{
  "success": true,
  "data": {
    "completeness_rate": 0.98,
    "missing_data_count": 15,
    "anomaly_count": 3,
    "last_update": "2026-07-17T15:30:00"
  }
}
```

---

### 2. 历史数据查询

#### 查询历史数据

```bash
GET /api/v1/data/history?time_range=24h&indicators=pH,COD&aggregation=raw&page=1&page_size=50
```

| 参数           | 类型   | 默认   | 说明                          |
| -------------- | ------ | ------ | ----------------------------- |
| `time_range`   | string | `24h`  | 时间范围（24h/7d/30d）         |
| `indicators`   | string | null   | 指标列表（逗号分隔）           |
| `aggregation`  | string | `raw`  | 聚合方式（raw/hourly/daily）   |
| `page`         | int    | `1`    | 页码（≥1）                     |
| `page_size`    | int    | `50`   | 每页数量（1–100）              |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "records": [
      { "timestamp": "2026-07-17T14:00:00Z", "pH": 7.1, "COD": 145.2 },
      { "timestamp": "2026-07-17T15:00:00Z", "pH": 7.3, "COD": 148.8 }
    ],
    "summary": { "avg_pH": 7.2, "max_COD": 150.5, "min_TN": 8.2 },
    "total_count": 2,
    "page": 1,
    "page_size": 50
  }
}
```

#### 获取聚合统计

```bash
GET /api/v1/data/aggregated?period=daily&metrics=avg,max,min
```

| 参数      | 类型   | 默认          | 说明                       |
| --------- | ------ | ------------- | -------------------------- |
| `period`  | string | `daily`       | 统计周期（daily/weekly...）|
| `metrics` | string | `avg,max,min` | 统计指标（逗号分隔）        |

---

### 3. 对话历史

#### 获取对话列表

```bash
GET /api/v1/conversations?page=1&page_size=20&status=active
```

| 参数        | 类型   | 默认  | 说明                |
| ----------- | ------ | ----- | ------------------- |
| `page`      | int    | `1`   | 页码（≥1）           |
| `page_size` | int    | `20`  | 每页数量（1–100）    |
| `status`    | string | null  | 状态过滤（active/completed/error）|

> 列表按 `started_at` 倒序返回（最新对话在前）。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "conversations": [
      {
        "id": "conv_3b6357f15fb0",
        "title": "测试对话",
        "started_at": "2026-07-17T15:30:00",
        "message_count": 0,
        "status": "active"
      }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 20
  },
  "metadata": { "total_count": 1, "page": 1, "page_size": 20 }
}
```

#### 创建对话

```bash
POST /api/v1/conversations
Content-Type: application/json

{
  "title": "新对话",
  "user_id": "user_123"
}
```

| 字段       | 类型   | 必填 | 说明       |
| ---------- | ------ | ---- | ---------- |
| `title`    | string | 否   | 对话标题   |
| `user_id`  | string | 否   | 用户 ID    |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "conv_05a8c8c3edea",
    "user_id": "user_123",
    "title": "新对话",
    "status": "active",
    "started_at": "2026-07-17T15:30:00"
  },
  "metadata": { "timestamp": "2026-07-17T15:30:00" }
}
```

#### 获取对话详情

```bash
GET /api/v1/conversations/{conversation_id}
```

获取指定对话的详细信息。对话不存在时返回 `success: false`（HTTP 仍为 200），错误码 `CONVERSATION_NOT_FOUND`。

---

## 错误码

| 错误码                     | 说明             |
| -------------------------- | ---------------- |
| `VALIDATION_ERROR`         | 参数验证失败     |
| `DATA_SOURCE_UNAVAILABLE`  | 数据源不可用     |
| `RESOURCE_NOT_FOUND`       | 资源不存在       |
| `EXTERNAL_SERVICE_ERROR`   | 外部服务错误     |
| `DATABASE_ERROR`           | 数据库错误       |
| `RATE_LIMIT_EXCEEDED`      | 超过速率限制     |

业务级错误（如对话不存在、数据查询异常）通过 `StandardResponse.error` 返回，HTTP 状态码为 200；
系统级异常由全局异常处理器统一处理，返回 HTTP 5xx 并附带 `BackendException` 错误体。

---

## 交互式文档

启动后端服务后，可访问自动生成的交互式 API 文档进行在线调试：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
