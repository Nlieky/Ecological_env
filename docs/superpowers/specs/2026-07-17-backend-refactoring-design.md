# 后端FastAPI模块化重构设计

## 设计目标

重构现有的后端FastAPI(8000)系统，使其重新定位为专业的数据服务层，与Agent服务(8642)形成清晰的职责分离。

## 新架构定位

### 职责分离原则

```
Agent服务(8642) - 智能对话层
├── 智能对话和意图理解
├── 子智能体协调和工具调用
├── 会话管理
└── 决策推理

后端FastAPI(8000) - 数据服务层
├── 实时监测数据服务
├── 历史数据查询和聚合
├── 对话历史持久化
├── 系统监控和告警
└── 报表导出和集成
```

### 架构流向

```
前端应用
    ↓
    ├── 智能对话查询 → Agent服务(8642)
    └── 数据查询/导出 → 后端FastAPI(8000)
```

## 整体架构设计

### 模块化架构

```
后端FastAPI(8000)
├── 数据服务层
│   ├── 实时监测数据
│   ├── 历史数据查询
│   └── 数据质量监控
├── 持久化层
│   ├── 对话历史存储
│   ├── 决策过程记录
│   └── 子智能体调用日志
├── 监控告警层
│   ├── 系统健康监控
│   ├── 数据异常告警
│   └── 性能监控
└── 集成导出层
    ├── 外部系统集成
    └── 报表导出
```

### 核心设计原则

1. **职责分离** - Agent服务负责智能对话，后端负责数据服务
2. **RESTful设计** - 清晰的资源路径和HTTP方法语义
3. **混合持久化** - Agent使用JSON文件，后端使用SQL数据库
4. **模块化结构** - 每个模块独立、可测试、可维护
5. **接口标准化** - 统一的请求/响应格式

## API接口设计

### 1. 数据服务层接口

#### 实时监测数据
```
GET /api/v1/monitoring/realtime
```
**功能**: 获取最新的监测数据
**响应**:
```json
{
  "success": true,
  "data": {
    "timestamp": "2026-07-17T15:30:00Z",
    "influent": {"pH": 7.2, "COD": 150.5, "TN": 25.3, "TP": 3.1},
    "effluent": {"pH": 6.8, "COD": 35.2, "TN": 8.5, "TP": 0.3},
    "flow_rate": 120.5,
    "quality_score": 0.95
  },
  "metadata": {
    "timestamp": "2026-07-17T15:30:00Z",
    "data_source": "monitoring_system"
  }
}
```

#### 数据质量监控
```
GET /api/v1/monitoring/quality
```
**功能**: 获取数据质量统计
**参数**: `time_range=24h` (可选)
**响应**:
```json
{
  "success": true,
  "data": {
    "completeness_rate": 0.98,
    "missing_data_count": 15,
    "anomaly_count": 3,
    "last_update": "2026-07-17T15:25:00Z"
  }
}
```

#### 历史数据查询
```
GET /api/v1/data/history
```
**功能**: 查询历史监测数据
**参数**:
- `time_range`: 时间范围（如 `24h`, `7d`, `30d`）
- `indicators`: 指标列表（如 `pH,COD,TN,TP`）
- `aggregation`: 聚合方式（`raw`, `hourly`, `daily`）
- `page`: 页码
- `page_size`: 每页数量

**响应**:
```json
{
  "success": true,
  "data": {
    "records": [
      {"timestamp": "2026-07-17T14:00:00Z", "pH": 7.1, "COD": 145.2},
      {"timestamp": "2026-07-17T15:00:00Z", "pH": 7.3, "COD": 148.8}
    ],
    "summary": {
      "avg_pH": 7.2,
      "max_COD": 150.5,
      "min_TN": 8.2
    }
  },
  "metadata": {
    "total_count": 168,
    "page": 1,
    "page_size": 50,
    "timestamp": "2026-07-17T15:30:00Z"
  }
}
```

#### 聚合数据统计
```
GET /api/v1/data/aggregated
```
**功能**: 获取聚合统计数据
**参数**: `period=daily&metrics=avg,max,min`

### 2. 持久化层接口

#### 对话历史列表
```
GET /api/v1/conversations
```
**功能**: 获取对话历史列表
**参数**: `page=1&page_size=20&status=active`

**响应**:
```json
{
  "success": true,
  "data": {
    "conversations": [
      {
        "id": "conv_12345",
        "title": "关于COD异常的咨询",
        "started_at": "2026-07-17T10:00:00Z",
        "message_count": 15,
        "status": "completed"
      }
    ]
  },
  "metadata": {
    "total_count": 45,
    "page": 1
  }
}
```

#### 对话详情
```
GET /api/v1/conversations/{id}
```
**功能**: 获取指定对话的详细内容

#### 创建对话
```
POST /api/v1/conversations
```
**功能**: 创建新的对话记录

#### 决策记录查询
```
GET /api/v1/decisions
```
**功能**: 查询主智能体的决策记录
**参数**: `conversation_id=xxx&time_range=24h`

#### 子智能体调用日志
```
GET /api/v1/subagent-calls
```
**功能**: 查询子智能体调用记录
**参数**: `conversation_id=xxx&subagent_name=anomaly-detection`

### 3. 监控告警层接口

#### 系统健康状态
```
GET /api/v1/monitoring/health
```
**功能**: 获取系统健康状态

**响应**:
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy",
    "components": {
      "database": {"status": "healthy", "latency_ms": 5},
      "agent_service": {"status": "healthy", "url": "http://localhost:8642"},
      "data_sources": {"status": "healthy", "last_update": "2026-07-17T15:28:00Z"}
    },
    "uptime_seconds": 86400
  }
}
```

#### 告警列表
```
GET /api/v1/monitoring/alerts
```
**功能**: 获取告警列表
**参数**: `status=active&severity=high`

#### 确认告警
```
POST /api/v1/monitoring/alerts/{id}/ack
```
**功能**: 确认告警

#### 性能指标
```
GET /api/v1/monitoring/metrics
```
**功能**: 获取系统性能指标

### 4. 集成导出层接口

#### 数据接入
```
POST /api/v1/integrations/ingest
```
**功能**: 接收外部系统数据

#### 报表导出
```
GET /api/v1/reports/export
```
**功能**: 导出报表
**参数**:
- `format`: 导出格式（`excel`, `csv`, `pdf`）
- `date_range`: 日期范围
- `template`: 报表模板

#### 报表模板
```
GET /api/v1/reports/templates
```
**功能**: 获取可用报表模板列表

## 数据库模型设计

### 新增数据表

#### 1. 对话历史表 (conversations)

```sql
CREATE TABLE conversations (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    title VARCHAR(200),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    message_count INT DEFAULT 0,
    status ENUM('active', 'completed', 'error'),
    metadata JSON,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
);
```

#### 2. 消息记录表 (conversation_messages)

```sql
CREATE TABLE conversation_messages (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50),
    role ENUM('user', 'assistant', 'tool'),
    content TEXT,
    tool_call_info JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_timestamp (timestamp)
);
```

#### 3. 决策记录表 (master_decisions)

```sql
CREATE TABLE master_decisions (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50),
    user_query TEXT,
    intent VARCHAR(100),
    decision_path JSON,
    subagents_called JSON,
    reasoning_summary TEXT,
    total_latency_ms INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_timestamp (timestamp)
);
```

#### 4. 子智能体调用表 (subagent_calls)

```sql
CREATE TABLE subagent_calls (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50),
    subagent_name VARCHAR(50),
    task_description TEXT,
    input_params JSON,
    output_result JSON,
    status ENUM('success', 'error', 'timeout'),
    execution_time_ms INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_subagent_name (subagent_name),
    INDEX idx_timestamp (timestamp)
);
```

### 保留现有表

- `logs` - 系统日志表
- `events` - 事件表

## 模块结构设计

### 目录结构

```
backend/
├── main.py                          # FastAPI应用入口
├── core/
│   └── config.py                   # 配置管理
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── data/                   # 数据服务接口
│       │   ├── realtime.py
│       │   ├── history.py
│       │   └── quality.py
│       ├── conversations/           # 持久化接口
│       │   ├── conversations.py
│       │   ├── decisions.py
│       │   └── subagent_calls.py
│       ├── monitoring/             # 监控告警接口
│       │   ├── health.py
│       │   ├── alerts.py
│       │   └── metrics.py
│       └── integrations/           # 集成导出接口
│           ├── ingest.py
│           └── export.py
├── services/                       # 业务逻辑层
│   ├── data_service.py            # 数据服务
│   ├── conversation_service.py     # 对话服务
│   ├── monitoring_service.py       # 监控服务
│   └── export_service.py          # 导出服务
├── models/                         # 数据模型
│   ├── conversation.py
│   ├── monitoring.py
│   └── export.py
├── database/                       # 数据库层
│   ├── base.py
│   ├── session.py
│   └── init_db.py
├── middleware/                     # 中间件
│   └── logging_middleware.py
├── utils/                          # 工具函数
│   └── loggers.py
└── tests/                          # 测试
    └── api/
```

### 模块职责

**路由层** (`api/v1/`)
- HTTP请求/响应处理
- 参数验证
- 路由定义

**服务层** (`services/`)
- 业务逻辑实现
- 数据处理
- 外部服务调用

**模型层** (`models/`)
- Pydantic数据模型
- 请求/响应验证
- 序列化

**数据库层** (`database/`)
- ORM模型定义
- 数据库会话管理
- 数据库初始化

## 错误处理机制

### 统一错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "DATA_SOURCE_UNAVAILABLE",
    "message": "数据源暂时不可用",
    "details": {
      "source": "monitoring_system",
      "retry_after": 30
    }
  },
  "timestamp": "2026-07-17T15:30:00Z"
}
```

### 自定义异常类

```python
class BackendException(Exception):
    """基础异常类"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

class DataUnavailableException(BackendException):
    """数据不可用异常"""
    pass

class ValidationException(BackendException):
    """数据验证异常"""
    pass

class ExternalServiceException(BackendException):
    """外部服务异常"""
    pass

class ResourceNotFoundException(BackendException):
    """资源不存在异常"""
    pass
```

### 错误码定义

| 错误码 | 说明 |
|--------|------|
| `VALIDATION_ERROR` | 参数验证失败 |
| `DATA_SOURCE_UNAVAILABLE` | 数据源不可用 |
| `RESOURCE_NOT_FOUND` | 资源不存在 |
| `EXTERNAL_SERVICE_ERROR` | 外部服务错误 |
| `DATABASE_ERROR` | 数据库错误 |
| `RATE_LIMIT_EXCEEDED` | 超过速率限制 |

## 实现优先级

### Phase 1: 核心数据服务（优先）

**目标**: 实现基本的数据查询和对话历史持久化功能

**包含**:
- 实时监测数据接口
- 历史数据查询接口
- 对话历史持久化
- 基础错误处理

**时间估计**: 2-3周

### Phase 2: 监控告警（次要）

**目标**: 实现系统监控和告警功能

**包含**:
- 系统健康监控
- 告警管理
- 性能指标收集
- 数据异常告警

**时间估计**: 1-2周

### Phase 3: 集成导出（可选）

**目标**: 实现报表导出和外部系统集成

**包含**:
- 报表导出功能
- 多格式支持（Excel, CSV, PDF）
- 外部数据接入
- API集成

**时间估计**: 1-2周

## 技术决策

### 1. 数据库迁移

使用Alembic管理数据库版本和迁移：
```bash
alembic revision --autogenerate -m "Add conversations tables"
alembic upgrade head
```

### 2. API版本控制

使用路径前缀进行版本控制：
- 当前版本: `/api/v1/`
- 未来版本: `/api/v2/`

### 3. 异步处理

对于耗时操作（如大数据导出），使用后台任务：
```python
from fastapi import BackgroundTasks

@router.post("/api/v1/reports/export")
async def export_report(background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_large_report, report_id)
    return {"report_id": report_id, "status": "processing"}
```

### 4. 缓存策略

- **实时数据**: 缓存30秒
- **历史数据**: 缓存5分钟
- **对话历史**: 缓存1小时
- **报表数据**: 缓存15分钟

### 5. 与Agent服务集成

后端定期从Agent服务获取对话历史并存储到数据库：
```python
async def sync_conversation_from_agent(conversation_id: str):
    response = requests.get(f"{AGENT_SERVICE_URL}/conversations/{conversation_id}")
    # 存储到数据库
```

## 兼容性考虑

### 向后兼容

- 保留现有的健康检查端点 `/api/health`
- 保留现有的查询端点 `/api/query` (作为转发功能)
- 逐步迁移到新的API路径

### 数据迁移

- 现有日志表保持不变
- 新增表结构使用Alembic迁移
- 提供数据迁移脚本

## 测试策略

### 单元测试

- 每个服务层函数的单元测试
- 数据库操作的单元测试
- 异常处理的测试

### 集成测试

- API端点的集成测试
- 与Agent服务的集成测试
- 数据库操作的集成测试

### 性能测试

- 响应时间测试
- 并发请求测试
- 大数据量查询测试

## 部署考虑

### 环境变量

```env
# FastAPI配置
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Agent服务配置
AGENT_SERVICE_URL=http://localhost:8642
AGENT_TIMEOUT=300

# 数据库配置
DATABASE_URL=sqlite:///./backend/logs/ecological_logs.db

# 缓存配置
CACHE_TTL_REALTIME=30
CACHE_TTL_HISTORY=300
```

### Docker支持

提供Dockerfile和docker-compose.yml用于容器化部署。

## 文档要求

### API文档

- 使用FastAPI自动生成的OpenAPI文档
- 在 `/docs` 和 `/redoc` 端点提供

### 开发文档

- 模块设计说明
- 接口使用示例
- 部署指南

## 成功标准

### 功能标准

- ✅ 所有API端点正常工作
- ✅ 对话历史正确持久化
- ✅ 实时数据查询响应时间 <1秒
- ✅ 历史数据查询响应时间 <3秒

### 质量标准

- ✅ 所有核心功能有单元测试
- ✅ 代码覆盖率 >80%
- ✅ 无已知的严重bug
- ✅ API文档完整准确

### 性能标准

- ✅ 支持至少100个并发请求
- ✅ 平均响应时间 <2秒
- ✅ 系统可用性 >99%

---

**设计完成时间**: 2026-07-17
**设计版本**: 1.0
**状态**: 待用户审查批准
