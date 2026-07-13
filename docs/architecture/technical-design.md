# 废水监测系统 - 完整技术架构设计文档

> **项目名称**: 废水虚假排放智能监测系统
> **版本**: 2.0
> **创建日期**: 2024-06-23
> **架构类型**: 现代后端 + Hermes 智能体 + 混合监控栈

---

## 一、系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         废水监测系统技术栈                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐      │
│  │                        前端层                                    │    │
│  │                                                                  │    │
│  │  React + Ant Design Pro                                          │    │
│  │  ├─ 业务功能：查询、工单、告警管理                                │    │
│  │  └─ 数据可视化：Grafana iframe 嵌入                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                │                                        │
│                                ▼                                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                        后端层                                    │    │
│  │                                                                  │    │
│  │  FastAPI                                                         │    │
│  │  ├─ API 接口服务                                                 │    │
│  │  ├─ 数据持久化                                                   │    │
│  │  ├─ Prometheus 监控暴露                                          │    │
│  │  └─ Hermes 集成                                                 │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                │                                        │
│                                ▼                                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      智能体层                                    │    │
│  │                                                                  │    │
│  │  Hermes 框架                                                     │    │
│  │  ├─ 主智能体：意图识别、任务分解                                 │    │
│  │  ├─ 子智能体 1：数据感知 (multi-dimensional-data-perception)     │    │
│  │  ├─ 子智能体 2：异常检测 (anomaly-detection)                       │    │
│  │  ├─ 子智能体 3：规则推理 (rule-reasoning)                          │    │
│  │  └─ 子智能体 4：处置执行 (disposition-execution)                   │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      数据层                                      │    │
│  │                                                                  │    │
│  │  PostgreSQL              InfluxDB               Prometheus      │    │
│  │  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐  │    │
│  │  │ 业务数据       │       │ 工业时序数据   │       │ 系统监控指标   │  │    │
│  │  │ • 用户        │       │ • pH/COD      │       │ • API/QPS     │  │    │
│  │  │ • 工单        │       │ • 流量/液位     │       │ • 响应时间     │  │    │
│  │  │ • 告警记录     │       │ • 溶解氧/余氯   │       │ • CPU/内存    │  │    │
│  │  │ • 查询历史     │       │ (Push 模式)    │       │ (Pull 模式)    │  │    │
│  │  └──────────────┘       └──────────────┘       └──────────────┘  │    │
│  │                                                                  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      可视化层                                    │    │
│  │                                                                  │    │
│  │  Grafana                                                         │    │
│  │  ├─ 数据源 1：InfluxDB（工业数据可视化）                         │    │
│  │  ├─ 数据源 2：Prometheus（系统监控可视化）                       │    │
│  │  └─ 前端嵌入：iframe 集成到 React 页面                           │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      告警层                                      │    │
│  │                                                                  │    │
│  │  业务告警              系统告警                                   │    │
│  │  ┌──────────────┐       ┌──────────────┐                       │    │
│  │  │ Hermes       │       │ Alertmanager  │                       │    │
│  │  │ 智能体分析    │       │ 指标阈值       │                       │    │
│  │  └──────────────┘       └──────────────┘                       │    │
│  │         │                       │                               │    │
│  │         └───────────┬───────────┘                               │    │
│  │                     ▼                                          │    │
│  │          飞书/钉钉/邮件/SMS                                    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      部署层                                      │    │
│  │                                                                  │    │
│  │  Docker Compose + 云服务器（阿里云 ECS / 腾讯云 CVM）             │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 关键架构原则

| 原则 | 说明 |
|------|------|
| **职责分离** | 前端、后端、智能体、数据库各司其职 |
| **现代后端** | FastAPI 只做接口转发，不做智能体编排决策 |
| **LLM 驱动** | 所有智能体调度由 Hermes LLM 决策 |
| **混合监控** | InfluxDB 负责工业数据，Prometheus 负责系统服务 |
| **可视化复用** | 直接嵌入 Grafana，不自建图表 |

---

## 二、前端技术栈

### 2.1 技术选型

```
框架: React 18
UI组件库: Ant Design 5
后台模板: Ant Design Pro
构建工具: Vite
状态管理: Zustand / Redux Toolkit
HTTP客户端: Axios
实时通信: WebSocket (可选，初期用 HTTP 轮询)
数据可视化: Grafana iframe 嵌入（不使用 ECharts）
```

### 2.2 前端职责

```
✅ 前端负责：
- 业务功能页面（查询、工单、告警管理）
- 用户认证和权限
- API 调用和数据展示
- Grafana iframe 嵌入和样式集成

❌ 前端不做：
- 数据可视化图表（用 Grafana）
- 实时数据推送（用 Grafana 自动刷新）
- 复杂的数据分析（后端处理）
```

### 2.3 页面结构

```
前端页面路由规划：

/                           → 首页（概览仪表板）
/monitoring                 → 数据监控（Grafana iframe）
/query                      → 查询分析（React 自建）
/alerts                     → 告警管理（React 自建）
/workorders                 → 工单系统（React 自建）
/settings                   → 系统设置（React 自建）
```

### 2.4 Grafana 嵌入实现

```jsx
// components/MonitoringDashboard.jsx
import React, { useEffect, useState } from 'react';

const MonitoringDashboard = () => {
  const [grafanaUrl, setGrafanaUrl] = useState('');
  
  useEffect(() => {
    const dashboardId = 'your-dashboard-id';
    const theme = 'light';
    const kiosk = 'tv';
    const token = localStorage.getItem('grafana_token');
    
    setGrafanaUrl(
      `https://your-grafana.com/d-solo/${dashboardId}?` +
      `theme=${theme}&kiosk=${kiosk}&auth=${token}`
    );
  }, []);
  
  return (
    <div className="monitoring-container">
      <iframe
        src={grafanaUrl}
        className="grafana-iframe"
        title="Grafana Dashboard"
        frameBorder="0"
      />
    </div>
  );
};

export default MonitoringDashboard;
```

---

## 三、后端技术栈

### 3.1 技术选型

```
框架: FastAPI 0.109+
Python: 3.12+
异步: asyncio + aiohttp
数据验证: Pydantic v2
API文档: FastAPI 自动生成 OpenAPI
监控集成: prometheus-fastapi-instrumentator
```

### 3.2 后端职责

```
✅ 后端负责：
- HTTP API 接口定义
- 请求/响应格式转换
- 参数验证（Pydantic）
- 数据持久化（PostgreSQL）
- Prometheus 监控暴露
- Hermes 智能体集成（简单调用）

❌ 后端不做：
- 智能体编排决策（Hermes LLM 决策）
- 子智能体调度（Hermes delegate_task）
- 任务分解（Hermes 处理）
```

### 3.3 FastAPI 项目结构

```
backend/
├── __init__.py
├── main.py                 # FastAPI 入口
├── api/                    # API 路由
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── query.py        # 查询接口
│   │   ├── alerts.py       # 告警接口
│   │   ├── workorders.py   # 工单接口
│   │   └── health.py       # 健康检查
│   └── dependencies.py     # 依赖注入
├── core/                   # 核心配置
│   ├── __init__.py
│   ├── config.py           # 配置加载
│   ├── security.py         # 认证
│   └── hermes.py           # Hermes 集成
├── models/                 # Pydantic 数据模型
│   ├── __init__.py
│   ├── query.py
│   ├── alert.py
│   └── workorder.py
├── services/               # 业务服务
│   ├── __init__.py
│   ├── query_service.py
│   ├── alert_service.py
│   └── workorder_service.py
├── db/                     # 数据库
│   ├── __init__.py
│   ├── session.py
│   └── models.py           # SQLAlchemy 模型
└── metrics/                # Prometheus 指标
    ├── __init__.py
    └── collector.py
```

### 3.4 FastAPI 主入口

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from backend.core.config import settings
from backend.api.routes import query, alerts, workorders, health
from backend.core.hermes import init_hermes_agent

app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="基于 Hermes 智能体的废水虚假排放监测系统",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(query.router, prefix="/api", tags=["查询"])
app.include_router(alerts.router, prefix="/api", tags=["告警"])
app.include_router(workorders.router, prefix="/api", tags=["工单"])

# Prometheus 监控
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Hermes 智能体
agent = init_hermes_agent()

@app.on_event("startup")
async def startup():
    """启动时初始化"""
    await agent.initialize()

@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    await agent.cleanup()
```

### 3.5 Hermes 集成示例

```python
# backend/core/hermes.py
from run_agent import AIAgent
from backend.core.config import settings

def init_hermes_agent() -> AIAgent:
    """初始化 Hermes 智能体"""
    return AIAgent(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        load_soul_identity=True,
        enabled_toolsets=["delegation"]  # delegate_task 工具
    )

# 依赖注入
async def get_hermes_agent():
    return agent
```

```python
# backend/api/routes/query.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.core.hermes import get_hermes_agent

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None

class QueryResponse(BaseModel):
    result: str
    session_id: str
    timestamp: str

@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    agent = Depends(get_hermes_agent)
):
    """执行查询 - 由 Hermes LLM 决定调用哪些子智能体"""
    messages = [{"role": "user", "content": request.query}]
    
    response = await agent.run_conversation(messages)
    
    return QueryResponse(
        result=response.content,
        session_id=response.session_id,
        timestamp=response.timestamp
    )
```

---

## 四、智能体技术栈

### 4.1 Hermes 框架配置

```yaml
# .hermes/config.yaml
hermes:
  version: "1.0"

model:
  provider: custom
  base_url_env: LLM_BASE_URL
  api_key_env: LLM_API_KEY
  model_env: LLM_MODEL
  base_url: "http://172.16.12.41:30000/v1"
  model: "ctgu-vlm"
  temperature: 0.7
  max_tokens: 4096

tools:
  enabled:
    - multi_dimensional_data_perception
    - anomaly_detection
    - rule_reasoning
    - disposition_execution

delegation:
  max_concurrent_children: 4
  subagent_auto_approve: false
  timeout: 300

skills:
  external_dirs:
    - subagents/multi-dimensional-data-perception-agent/skills
    - subagents/anomaly-detection-agent/skills
    - subagents/rule-reasoning-agent/skills
    - subagents/disposition-execution-agent/skills
```

### 4.2 子智能体 SKILL.md 格式

```yaml
---
name: data-perception-core
description: 获取并预处理多维时序数据。触发条件：当用户查询提到"进水"、"出水"、"监测数据"、"数据"、"指标"或时间范围（"最近N小时"、"今天"、"昨天"）时调用。
---

## 功能说明
获取多维时序数据，支持时间范围过滤和指标选择。

## 使用场景
- 查询进水/出水数据
- 时间范围查询
- 指标筛选
```

### 4.3 主智能体 SOUL.md 配置

```markdown
## 子智能体调用

当你需要处理废水监测数据时，使用 delegate_task 工具调用以下子智能体：

1. **multi-dimensional-data-perception** - 多维数据感知
   - 功能: 获取多维时序数据，分解、清洗、标准化

2. **anomaly-detection** - 异常检测
   - 功能: 使用多种算子检测时序数据异常

3. **rule-reasoning** - 规则推理
   - 功能: 基于法规和工艺知识进行规则推理

4. **disposition-execution** - 研判预警与处置执行
   - 功能: 融合异常检测和规则推理结果，生成处置工单
```

---

## 五、数据库技术栈

### 5.1 PostgreSQL（业务数据）

```
用途: 业务数据存储
连接: postgresql://user:password@localhost:5432/ecological_env
ORM: SQLAlchemy 2.0
迁移工具: Alembic

存储内容:
- 用户信息
- 告警工单记录
- 历史查询记录
- 系统配置
```

### 5.2 InfluxDB（工业时序数据）

```
用途: 工业现场监测数据存储
版本: InfluxDB v2.x
端口: 8086
组织: ecological-env
存储桶: monitoring-data

数据来源:
- 现场网关 Push 数据
- Telegraf 采集（Modbus/OPC/MQTT）

存储内容:
- pH 值
- COD 浓度
- 总氮 (TN)
- 氨氮 (NH3-N)
- 总磷 (TP)
- 流量
- 溶解氧
- 液位
- 余氯

采样频率: 5分钟
```

### 5.3 Prometheus（系统监控指标）

```
用途: 系统服务监控
端口: 9090
采集方式: Pull

监控内容:
- API QPS
- API 响应时间
- API 错误率
- Hermes 智能体调用次数
- LLM Token 使用量
- CPU/内存/磁盘使用率
```

---

## 六、监控技术栈

### 6.1 混合监控架构

```
┌─────────────────────────────────────────────────────────────┐
│                    监控数据双轨并行                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  【业务数据轨道】              【系统服务轨道】                │
│  InfluxDB + Telegraf         Prometheus + Exporters          │
│  ┌───────────────────┐       ┌───────────────────┐          │
│  │  工业现场数据       │       │  软件服务指标       │          │
│  │                   │       │                   │          │
│  │ • pH 传感器       │       │ • API QPS         │          │
│  │ • COD 传感器      │       │ • API 延迟         │          │
│  │ • 流量传感器       │       │ • API 错误率        │          │
│  │ • 溶解氧传感器     │       │ • Hermes 调用     │          │
│  │ • 液位传感器       │       │ • LLM Token       │          │
│  │ • 余氯传感器       │       │ • CPU 使用率        │          │
│  │                   │       │                   │          │
│  │ 采集方式: Push    │       │ 采集方式: Pull     │          │
│  │ 采集频率: 5分钟   │       │ 采集频率: 15秒     │          │
│  └───────────────────┘       └───────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Telegraf 配置（工业数据采集）

```toml
# telegraf.conf
[[inputs.modbus]]
  name = "plc_sensors"
  slave_id = 1
  register = "holding"
  addresses = [0, 1, 2, 3, 4]
  name_override = "water_quality"

[[outputs.influxdb_v2]]
  urls = ["https://cloud-server.com:8086"]
  token = "${INFLUXDB_TOKEN}"
  organization = "ecological-env"
  bucket = "monitoring-data"
```

### 6.3 Prometheus 配置（系统监控）

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

### 6.4 Grafana 配置（双数据源）

```json
{
  "apiVersion": 1,
  "datasources": [
    {
      "name": "InfluxDB",
      "type": "influxdb",
      "url": "http://influxdb:8086",
      "access": "proxy",
      "jsonData": {
        "version": "Flux",
        "organization": "ecological-env",
        "defaultBucket": "monitoring-data"
      }
    },
    {
      "name": "Prometheus",
      "type": "prometheus",
      "url": "http://prometheus:9090",
      "access": "proxy"
    }
  ]
}
```

---

## 七、告警系统

### 7.1 告警分层

```
┌─────────────────────────────────────────────────────────────┐
│                      告警分层                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  【业务告警】              【系统告警】                        │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  Hermes 智能体   │     │ Alertmanager    │               │
│  │                 │     │                 │               │
│  │ • COD 超标      │     │ • API 故障       │               │
│  │ • pH 异常       │     │ • 服务宕机       │               │
│  │ • 违规排放检测   │     │ • 内存溢出       │               │
│  │ • 工艺异常       │     │ • 磁盘满         │               │
│  └─────────────────┘     └─────────────────┘               │
│         │                       │                             │
│         └───────────┬───────────┘                             │
│                     ▼                                         │
│          ┌─────────────────┐                                  │
│          │  通知渠道        │                                  │
│          │ • 飞书           │                                  │
│          │ • 钉钉           │                                  │
│          │ • 邮件           │                                  │
│          └─────────────────┘                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Prometheus Alertmanager 配置

```yaml
# alertmanager.yml
receivers:
  - name: 'feishu'
    webhook_configs:
      - url: 'https://open.feishu.cn/open-apis/bot/v2/hook/xxx'

  - name: 'email'
    email_configs:
      - to: 'admin@example.com'
```

---

## 八、部署架构

### 8.1 docker-compose.yml

```yaml
version: '3.8'

services:
  # InfluxDB - 工业时序数据
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword
      - DOCKER_INFLUXDB_INIT_ORG=ecological-env
      - DOCKER_INFLUXDB_INIT_BUCKET=monitoring-data
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=my-super-secret-token
    volumes:
      - influxdb-data:/var/lib/influxdb2

  # PostgreSQL - 业务数据
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=ecological_env
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data

  # Prometheus - 系统监控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # Grafana - 可视化
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning

  # FastAPI 后端
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecological_env
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=my-super-secret-token
      - INFLUXDB_ORG=ecological-env
      - INFLUXDB_BUCKET=monitoring-data
      - LLM_BASE_URL=http://172.16.12.41:30000/v1
      - LLM_API_KEY=sk-4e9a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f
      - LLM_MODEL=ctgu-vlm
    depends_on:
      - postgres
      - influxdb
      - prometheus

volumes:
  influxdb-data:
  postgres-data:
  prometheus-data:
  grafana-data:
```

### 8.2 云服务器部署

```
推荐配置：
- CPU: 4核
- 内存: 8GB
- 磁盘: 100GB SSD
- 带宽: 10Mbps（按流量计费）

云服务商：
- 阿里云 ECS
- 腾讯云 CVM
- 华为云 ECS
```

---

## 九、环境变量配置

### 9.1 .env 文件

```bash
# ==================== FastAPI 配置 ====================
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_DEBUG=false

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecological_env

# ==================== InfluxDB 配置 ====================
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=my-super-secret-token
INFLUXDB_ORG=ecological-env
INFLUXDB_BUCKET=monitoring-data

# ==================== Prometheus 配置 ====================
PROMETHEUS_PORT=9090

# ==================== Grafana 配置 ====================
GRAFANA_URL=http://grafana:3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# ==================== LLM 配置 ====================
LLM_BASE_URL=http://172.16.12.41:30000/v1
LLM_API_KEY=sk-4e9a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f
LLM_MODEL=ctgu-vlm

# ==================== CORS 配置 ====================
CORS_ORIGINS=*

# ==================== 飞书集成配置 ====================
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_url_here
FEISHU_ENABLED=true

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
```

---

## 十、开发优先级

### 第一阶段：后端 API + Hermes 集成
```
1. FastAPI 项目搭建
2. PostgreSQL 数据库模型
3. Hermes 智能体集成
4. 基础 API 接口
```

### 第二阶段：监控系统
```
1. InfluxDB 部署
2. Prometheus 集成
3. Grafana 配置
4. Telegraf 数据采集（模拟）
```

### 第三阶段：前端开发
```
1. React + Ant Design Pro 搭建
2. API 集成
3. Grafana iframe 嵌入
4. 业务功能页面
```

### 第四阶段：部署和优化
```
1. Docker Compose 编排
2. 云服务器部署
3. 性能优化
4. 安全加固
```

---

## 十一、关键依赖版本

```
Python: 3.12+
FastAPI: 0.109+
Pydantic: 2.5+
SQLAlchemy: 2.0+
Alembic: 1.13+
Prometheus: latest
InfluxDB: 2.7
Grafana: latest
React: 18
Ant Design: 5
Vite: 5
```

---

**文档结束**

本文档记录了废水监测系统的完整技术架构设计。任何架构变更都应更新本文档。
