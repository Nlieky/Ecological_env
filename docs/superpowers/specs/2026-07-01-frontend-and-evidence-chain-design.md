# 废水监测系统前端界面与证据链记录设计

**日期**: 2026-07-01
**版本**: v1.0
**状态**: 待用户审阅

---

## 1. 概述

本文档定义废水监测智能体系统的前端界面设计和证据链记录机制，借鉴 SxDevOps 项目的页面上下文和交互方式，适配废水监测业务场景。

### 1.1 设计目标

1. **前端界面**: 提供直观的监测大屏、AI 助手交互、事件中心等核心功能
2. **证据链记录**: 完整记录系统工作流程，支持查询、导出和审计

### 1.2 技术栈

- **前端**: Vue 3 + Vite + Element Plus + ECharts + Pinia + Vue Router
- **后端**: FastAPI + SQLAlchemy ORM（已存在）
- **借鉴来源**: SxDevOps 前端代码，定制化修改

---

## 2. 前端架构设计

### 2.1 目录结构

```
frontend/
├── src/
│   ├── views/              # 页面
│   │   ├── Dashboard.vue   # 监测大屏（4×4 厂区）
│   │   ├── AIOpsChat.vue   # AI 助手完整版
│   │   ├── EventCenter.vue # 事件中心
│   │   ├── Metrics.vue     # 查询指标
│   │   ├── Logs.vue        # 查看日志
│   │   ├── Trace.vue       # 链路追踪
│   │   └── Settings.vue    # 系统配置
│   ├── components/         # 组件
│   │   ├── aiops/          # AI 助手组件（借鉴 SxDevOps）
│   │   ├── dashboard/      # 监测大屏组件
│   │   │   ├── PlantCard.vue      # 厂区卡片
│   │   │   ├── PlantGrid.vue      # 4×4 网格
│   │   │   └── MetricDisplay.vue  # 指标显示
│   │   └── layout/         # 布局组件
│   ├── api/                # API 调用
│   ├── router/             # 路由
│   ├── stores/             # Pinia 状态
│   └── utils/              # 工具函数
```

### 2.2 页面布局

```
┌─────────────────────────────────────────────────────┐
│  [左侧导航] │          [中间内容区]            [AI] │
│            │                                    │
│  - AI助手  │                                    │
│  - 监测大屏│     [主要内容展示]                  │
│    - 指标 │                                    │
│    - 日志 │                                    │
│    - 链路 │                                    │
│    - 数据 │                                    │
│    - 告警 │                                    │
│  - 事件中心│                                    │
│  - 配置    │                                    │
└─────────────────────────────────────────────────────┘
```

### 2.3 路由结构

```javascript
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/chat', component: AIOpsChat },           // AI 助手
  { path: '/dashboard', component: Dashboard },      // 监测大屏
  { path: '/metrics', component: Metrics },          // 查询指标
  { path: '/logs', component: Logs },                // 查看日志
  { path: '/trace', component: Trace },              // 链路追踪
  { path: '/events', component: EventCenter },       // 事件中心
  { path: '/settings', component: Settings },       // 系统配置
]
```

---

## 3. 监测大屏设计

### 3.1 4×4 厂区框架

```
┌─────────────────────────────────────────────────────┐
│                    监测大屏                          │
├─────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│ │ 厂区 1  │ │ 厂区 2  │ │ 厂区 3  │ │ 厂区 4  │   │
│ │ (有数据) │ │ (占位)  │ │ (占位)  │ │ (占位)  │   │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│ │ (占位)  │ │ (占位)  │ │ (占位)  │ │ (占位)  │   │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│ │ (占位)  │ │ (占位)  │ │ (占位)  │ │ (占位)  │   │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│ │ (占位)  │ │ (占位)  │ │ (占位)  │ │ (占位)  │   │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────┘
```

### 3.2 厂区卡片组件

#### 有数据时显示

```
┌─────────────────────┐
│  🏭 废水处理厂 A区   │
├─────────────────────┤
│ pH:     7.2  ✓     │
│ COD:    45   ✓     │
│ 氨氮:   8.5  ✓     │
│ 总氮:   15   ✓     │
│ 总磷:   0.8  ✓     │
│ 流量:   120  ✓     │
├─────────────────────┤
│ 更新: 10:23:45      │
│ 状态: 正常运行       │
└─────────────────────┘
```

#### 占位卡片

```
┌─────────────────────┐
│                     │
│      🏭             │
│   [待接入厂区]      │
│                     │
└─────────────────────┘
```

### 3.3 数据指标

每个厂区显示 6 个实时指标：

| 指标 | 说明 | 状态判断 |
|------|------|----------|
| pH | 酸碱度 | 6-9 正常 |
| COD | 化学需氧量 | <50 正常 |
| 氨氮 (NH3-N) | 氨氮含量 | <15 正常 |
| 总氮 (TN) | 总氮含量 | <20 正常 |
| 总磷 (TP) | 总磷含量 | <1 正常 |
| 流量 | 废水流量 | >0 正常 |

状态标识：
- ✓ 正常（绿色）
- ⚠️ 超标（橙色）
- ❌ 离线（灰色）

### 3.4 数据更新机制

- **后端**: WebSocket 推送实时数据
- **前端**: Pinia store 管理状态
- **更新频率**: 每分钟推送一次

### 3.5 Grafana 集成

监测大屏支持嵌入 Grafana iframe 展示详细图表：

```vue
<iframe
  :src="grafanaUrl"
  width="100%"
  height="400px"
  frameborder="0">
</iframe>
```

---

## 4. AI 助手设计

### 4.1 双入口

| 入口 | 位置 | 功能 |
|------|------|------|
| **完整版** | 左侧导航"AI助手" | 完整对话界面，多会话管理 |
| **浮窗版** | 右下角浮窗 | 快速咨询，页面上下文带入 |

### 4.2 完整版界面

```
┌─────────────────────────────────────────────────────┐
│  🤖 废水监测智能助手                    [新对话] [历史] │
├──────────────────────┬──────────────────────────────┤
│                      │                              │
│  对话区               │         侧边栏（可折叠）      │
│                      │                              │
│  ┌─────────────────┐ │  📋 当前会话证据链           │
│  │ 用户: 最近异常？ │ │  ┌─────────────────────┐   │
│  └─────────────────┘ │  │ • 数据来源: 进水口  │   │
│                      │  │ • 算子: 孤立森林     │   │
│  ┌─────────────────┐ │  │ • 规则: pH-COD协同  │   │
│  │ 助手: 检测到... │ │  └─────────────────────┘   │
│  └─────────────────┘ │                              │
│  [带 ECharts 图表]   │  📊 异常点标注               │
│                      │  ┌─────────────────────┐   │
│                      │  │  [可交互的 ECharts] │   │
│                      │  └─────────────────────┘   │
├──────────────────────┴──────────────────────────────┤
│  [输入框]                                    [发送] │
└─────────────────────────────────────────────────────┘
```

### 4.3 浮窗版界面

```
┌───────────────────────────┐
│  🤖          [─] [□] [×]   │
├───────────────────────────┤
│                           │
│  对话历史（最近3条）       │
│                           │
│  ─────────────────────    │
│                           │
│  [输入框]           [发送] │
└───────────────────────────┘
```

### 4.4 ECharts 异常标注

```
┌─────────────────────────────────┐
│  COD 浓度趋势                    │
│  ─────────────────────────       │
│  │                              │
│  │    ╭──╮                      │  ← LLM 检测的异常段
│  │   ╱    ╲                     │
│  │  │      │                    │
│  ──┴───────┴────────────────     │
│         ↑                       │
│      [点击查看详情]              │
└─────────────────────────────────┘
```

### 4.5 页面上下文带入

从监测大屏、事件中心等页面打开 AI 助手时，自动携带上下文：

```javascript
// 页面上下文示例
{
  page: 'dashboard',
  plantId: 'plant_a',
  timeRange: ['2026-07-01 09:00', '2026-07-01 10:00'],
  suggestedQuestions: [
    '分析 A 厂最近1小时异常情况',
    '当前 COD 指标正常吗？'
  ]
}
```

---

## 5. 事件中心设计

### 5.1 事件中心界面

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 事件中心                        [导出报告] [刷新]             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🔍 [搜索框]    时间: [▼]   类型: [▼]   厂区: [▼]   严重: [▼]   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 时间          │ 类型    │ 厂区  │ 严重  │ 状态  │ 操作   │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ 2026-07-01 10:23 │ COD超标 │ A区   │ 高    │ 待处理│ [详情]│  │
│  │ 2026-07-01 09:45 │ pH异常  │ A区   │ 中    │ 处理中│ [详情]│  │
│  │ 2026-06-30 23:15 │ 流量异常│ A区   │ 低    │ 已解决│ [详情]│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│                    [< 1 2 3 4 5 >]                               │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 告警详情弹窗

```
┌────────────────────────────────────────────────────────────┐
│  📋 告警详情                                  [关闭]         │
├────────────────────────────────────────────────────────────┤
│  基本信息                                                     │
│  ─────────────────────────────────────────────────────────  │
│  时间: 2026-07-01 10:23:45                                   │
│  类型: COD超标                                               │
│  厂区: 废水处理厂 A区                                        │
│  严重程度: ⚠️ 高                                             │
│  当前状态: 待处理                                            │
│                                                               │
│  证据链                                                       │
│  ─────────────────────────────────────────────────────────  │
│  📊 数据快照                                                 │
│     COD: 125 mg/L (超标 2.5倍)                              │
│     pH: 7.2, 氨氮: 8.5 mg/L                                 │
│                                                               │
│  🔧 算子调用                                                 │
│     • statistical.trend_detector: 检测到上升趋势             │
│     • ml.isolation_forest: 异常置信度 0.92                  │
│                                                               │
│  ⚖️ 规则匹配                                                 │
│     • pH-COD协同规则: 不符合（pH正常但COD异常）             │
│     • 违规模式: 符合"疑似偷排"模式                           │
│                                                               │
│  🤖 LLM推理过程                                               │
│     主智能体决策: 多维数据感知 → 异常检测 → 规则推理         │
│     结论: 数据支持COD超标违规判定                            │
│                                                               │
│  操作                                                         │
│  ─────────────────────────────────────────────────────────  │
│  [标记已解决]  [生成工单]  [导出证据]                       │
└────────────────────────────────────────────────────────────┘
```

### 5.3 状态流转

```
待确认 → 待处理 → 处理中 → 已解决
         ↘ 已忽略
```

### 5.4 搜索过滤条件

| 字段 | 类型 | 选项 |
|------|------|------|
| 时间 | 日期范围 | 最近1小时/今天/最近7天/自定义 |
| 类型 | 下拉 | COD超标/pH异常/氨氮异常/流量异常/全部 |
| 厂区 | 下拉 | A区/B区/全部 |
| 严重程度 | 下拉 | 高/中/低/全部 |
| 状态 | 下拉 | 待处理/处理中/已解决/已忽略/全部 |

### 5.5 导出功能

支持导出为：
- Excel 格式（.xlsx）
- PDF 格式（带证据链详情）
- JSON 格式（原始数据）

---

## 6. 证据链记录设计

### 6.1 日志表结构

#### 6.1.1 API 调用日志表 (api_call_logs)

```python
class APICallLog(Base):
    """API 调用日志"""
    __tablename__ = 'api_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    method = Column(String(10))              # GET/POST/PUT/DELETE
    path = Column(String(255), index=True)   # /api/query
    user_id = Column(String(64), index=True) # 用户ID
    request_params = Column(JSON)            # 请求参数
    response_status = Column(Integer)         # 200/400/500
    latency_ms = Column(Float)               # 耗时
    error_message = Column(Text, nullable=True)
```

#### 6.1.2 主智能体决策日志表 (master_agent_decision_logs)

```python
class MasterAgentDecisionLog(Base):
    """主智能体决策日志"""
    __tablename__ = 'master_agent_decision_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    session_id = Column(String(64), index=True)  # 会话ID
    user_query = Column(Text)                     # 用户查询
    intent = Column(String(64))                   # 意图识别结果
    decision_path = Column(JSON)                   # 决策路径
    subagents_called = Column(JSON)               # 调用的子智能体列表
    reasoning_summary = Column(Text)               # 推理摘要
    total_latency_ms = Column(Float)               # 总耗时
```

#### 6.1.3 子智能体执行日志表 (sub_agent_execution_logs)

```python
class SubAgentExecutionLog(Base):
    """子智能体执行日志"""
    __tablename__ = 'sub_agent_execution_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    session_id = Column(String(64), index=True)
    subagent_name = Column(String(64), index=True) # 子智能体名称
    input_params = Column(JSON)                     # 输入参数
    output_result = Column(JSON)                    # 输出结果
    execution_time_ms = Column(Float)              # 执行耗时
    status = Column(String(20))                     # success/failed
    error_message = Column(Text, nullable=True)
```

#### 6.1.4 算子调用日志表 (operator_call_logs)

```python
class OperatorCallLog(Base):
    """算子调用日志"""
    __tablename__ = 'operator_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    session_id = Column(String(64), index=True)
    subagent_name = Column(String(64))              # 调用该算子的子智能体
    operator_name = Column(String(128), index=True)  # 算子名称
    category = Column(String(32))                   # statistical/ml/deep_learning
    input_params = Column(JSON)                      # 输入参数
    output_result = Column(JSON)                    # 输出结果
    execution_time_ms = Column(Float)
    status = Column(String(20))
```

#### 6.1.5 LLM 调用日志表 (llm_call_logs)

```python
class LLMCallLog(Base):
    """LLM 调用日志"""
    __tablename__ = 'llm_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    session_id = Column(String(64), index=True)
    provider = Column(String(64))                   # ctgu-vlm
    model = Column(String(64))                     # 具体模型名
    purpose = Column(String(32))                    # intent_planning/response_formatting
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    estimated_cost = Column(Float, nullable=True)   # 预估成本
    latency_ms = Column(Float)
    request_summary = Column(JSON)                   # 简化的请求内容
    status = Column(String(20))
```

#### 6.1.6 系统错误日志表 (system_error_logs)

```python
class SystemErrorLog(Base):
    """系统错误日志"""
    __tablename__ = 'system_error_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    level = Column(String(20), index=True)          # ERROR/CRITICAL/WARNING
    module = Column(String(64), index=True)          # backend/api/subagent_xxx
    error_type = Column(String(64))                 # Exception类型
    error_message = Column(Text)
    stack_trace = Column(Text)
    context = Column(JSON)                          # 额外上下文
```

### 6.2 日志查询 API

```python
# backend/api/routes/logs.py

@router.get("/api/logs")
async def query_logs(
    log_type: LogType,          # api/master/subagent/operator/llm/error
    start_time: datetime,
    end_time: datetime,
    page: int = 1,
    page_size: int = 50,
    filters: dict = {}
):
    """统一日志查询接口"""

@router.get("/api/logs/trace/{session_id}")
async def get_session_trace(session_id: str):
    """获取完整会话的证据链"""

@router.get("/api/logs/export")
async def export_logs(
    log_type: LogType,
    start_time: datetime,
    end_time: datetime,
    format: str = "xlsx"
):
    """导出日志"""
```

### 6.3 日志展示界面

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 系统日志           [类型: ▼] [时间: ▼] [搜索] [导出]        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Tab: [API调用] [主智能体] [子智能体] [算子] [LLM] [错误]         │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 时间          │ 模块        │ 内容             │ 耗时   │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ 2026-07-01 10:23 │ API         │ POST /api/query   │ 1250ms│  │
│  │ 2026-07-01 10:23 │ 主智能体    │ 意图: 异常检测    │ 880ms │  │
│  │ 2026-07-01 10:23 │ 子智能体    │ anomaly_detection│ 450ms │  │
│  │ 2026-07-01 10:23 │ 算子        │ isolation_forest │ 120ms │  │
│  │ 2026-07-01 10:23 │ LLM         │ ctgu-vlm         │ 550ms │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  [时间范围选择器]                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 证据链关联

通过 `session_id` 关联一次完整查询的所有日志：

```
API 调用 → 主智能体决策 → 子智能体执行 → 算子调用 → LLM 调用
```

点击任意日志，可展开查看完整的证据链。

---

## 7. 数据库设计

### 7.1 表关系

```
api_call_logs
master_agent_decision_logs (session_id 关联)
    ├── sub_agent_execution_logs (session_id 关联)
    │   └── operator_call_logs (session_id 关联)
    └── llm_call_logs (session_id 关联)

system_error_logs (独立)
```

### 7.2 索引设计

所有表在 `timestamp` 和 `session_id` 上建立索引，支持高效查询。

---

## 8. API 接口设计

### 8.1 前端所需后端接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/realtime/data` | GET/WS | 获取实时监测数据 |
| `/api/query` | POST | AI 查询接口（已存在） |
| `/api/events` | GET | 获取告警事件列表 |
| `/api/events/{id}` | GET | 获取告警详情 |
| `/api/events/{id}/status` | PUT | 更新告警状态 |
| `/api/logs` | GET | 查询系统日志 |
| `/api/logs/trace/{session_id}` | GET | 获取会话证据链 |
| `/api/logs/export` | GET | 导出日志 |

### 8.2 WebSocket 接口

```
ws://localhost:8001/ws/realtime
```

推送实时监测数据更新。

---

## 9. 实现优先级

### Phase 1: 核心功能（第一版）

1. 监测大屏基础框架
   - 4×4 厂区布局
   - 单个厂区数据显示
   - 实时数据更新

2. AI 助手基础功能
   - 对话界面
   - ECharts 图表展示
   - 异常点标注

3. 事件中心基础功能
   - 告警列表
   - 告警详情
   - 状态更新

### Phase 2: 增强功能（第二版）

1. 监测大屏增强
   - Grafana 集成
   - 多厂区支持

2. AI 助手增强
   - 页面上下文带入
   - 多会话管理

3. 事件中心增强
   - 高级搜索过滤
   - 导出报告

### Phase 3: 日志系统（第三版）

1. 日志表创建
2. 日志记录中间件
3. 日志查询接口
4. 日志展示界面

---

## 10. 借鉴来源

本设计借鉴了 [SxDevOps](https://github.com/aiyiyi121/sxdevops) 项目的以下内容：

- 前端布局结构（左侧导航 + 中间内容 + 右下角浮窗）
- AI 助手交互模式
- 事件中心设计
- 日志记录数据模型结构

针对废水监测业务做了以下定制：

- 厂区监测大屏（4×4 布局）
- 水质指标展示（pH、COD、氨氮等）
- 异常点 ECharts 标注
- 告警事件中心

---

## 附录

### A. 相关文档

- [CLAUDE.md](../../CLAUDE.md) - 项目技术文档
- [README.md](../../README.md) - 项目说明

### B. 技术参考

- [SxDevOps GitHub](https://github.com/aiyiyi121/sxdevops)
- [Vue 3 官方文档](https://vuejs.org/)
- [Element Plus 官方文档](https://element-plus.org/)
- [ECharts 官方文档](https://echarts.apache.org/)

### C. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-01 | v1.0 | 初始版本 |
