# 状态管理规范

## 版本信息

- **版本**: v1.0
- **创建日期**: 2026-05-15
- **适用范围**: 主智能体层、任务编排层、子智能体层

## 一、概述

### 1.1 目的

定义废水虚假排放智能监测系统中各层的状态管理规范，确保：

1. 状态数据结构统一
2. 状态持久化机制一致
3. 状态恢复流程标准化
4. 状态同步协议清晰

### 1.2 适用范围

本规范适用于以下三层的所有组件：

- **主智能体层** (MasterAgentLayer)
- **任务编排层** (TaskOrchestrationLayer)
- **子智能体层** (DataGovernanceAgent, FeatureAnalysisAgent, AnomalyDetectionAgent, RuleReasoningAgent)

## 二、状态数据结构

### 2.1 主智能体状态

```yaml
master_agent_state:
  # 基本信息
  version: "2.1.0"                      # 状态版本
  timestamp: "2026-05-15T10:30:00Z"     # 状态时间戳
  state_id: "unique-state-id"           # 状态唯一标识

  # 运行状态
  health_status: "healthy"              # 健康状态: healthy, degraded, unhealthy
  uptime: 3600                          # 运行时长（秒）
  last_heartbeat: "2026-05-15T10:30:00Z"

  # 任务管理
  active_tasks:                          # 活跃任务列表
    - task_id: "task-001"
      task_type: "analysis_query"
      status: "running"
      start_time: "2026-05-15T10:25:00Z"

  # 缓存统计
  cache_stats:
    total_cached: 150                    # 总缓存条目
    hit_count: 120                       # 命中次数
    miss_count: 30                       # 未命中次数
    hit_rate: 0.8                        # 命中率

  # 结果复用统计
  reuse_stats:
    total_decisions: 200                 # 总决策次数
    reused_count: 150                    # 复用次数
    recompute_count: 50                  # 重新计算次数
    reuse_rate: 0.75                     # 复用率
```

### 2.2 任务编排层状态

```yaml
orchestration_state:
  # 基本信息
  version: "2.1.0"
  timestamp: "2026-05-15T10:30:00Z"
  state_id: "orch-state-001"

  # 工作流状态
  active_workflows:                      # 活跃工作流
    - workflow_id: "wf-001"
      status: "running"
      total_tasks: 5
      completed_tasks: 2
      failed_tasks: 0

  # 资源分配状态
  resource_allocation:
    data_governance_agent:
      status: "idle"
      current_task: null
      last_task_time: "2026-05-15T10:28:00Z"
    feature_analysis_agent:
      status: "busy"
      current_task: "task-002"
      progress: 0.6
```

### 2.3 子智能体状态

```yaml
subagent_state:
  # 基本信息
  agent_id: "data-governance-agent"      # 子智能体ID
  agent_type: "data_governance"          # 智能体类型
  version: "2.0.0"
  timestamp: "2026-05-15T10:30:00Z"

  # 运行状态
  status: "idle"                         # idle, busy, error, maintenance
  health: "healthy"                      # healthy, degraded, error

  # 心跳信息
  last_heartbeat: "2026-05-15T10:30:00Z"
  heartbeat_interval: 30                 # 心跳间隔（秒）

  # 任务信息
  current_task:
    task_id: null
    start_time: null
    progress: null

  # 性能统计
  performance:
    total_tasks_processed: 1250
    average_processing_time: 2.5         # 平均处理时间（秒）
    success_rate: 0.98                   # 成功率
    error_count: 25
```

## 三、状态持久化

### 3.1 持久化格式

状态数据以JSON格式持久化到文件：

```json
{
  "state_type": "master_agent",
  "version": "2.1.0",
  "timestamp": "2026-05-15T10:30:00Z",
  "data": {
    "health_status": "healthy",
    "active_tasks": [],
    "cache_stats": {
      "total_cached": 150,
      "hit_rate": 0.8
    }
  }
}
```

### 3.2 持久化路径

| 层级 | 持久化路径 | 文件名格式 |
|------|-----------|-----------|
| 主智能体 | `shared/state/master_agent/` | `state_{YYYYMMDD}.json` |
| 任务编排层 | `shared/state/orchestration/` | `state_{YYYYMMDD}.json` |
| 子智能体 | `shared/state/subagents/{agent_id}/` | `state_{YYYYMMDD}.json` |

### 3.3 持久化策略

1. **定期持久化**：每5分钟自动保存一次
2. **关键事件持久化**：重要状态变化时立即保存
3. **优雅关闭**：系统关闭时保存最终状态
4. **轮转清理**：保留最近30天的状态文件

## 四、状态恢复

### 4.1 恢复流程

```
系统启动
    ↓
检查状态文件是否存在
    ↓
┌─ 存在 ─────────────┐
│                     ↓
│              验证状态版本兼容性
│                     ↓
│              加载状态数据
│                     ↓
│              恢复运行时状态
│                     ↓
│              验证状态完整性
│                     ↓
│              标记恢复完成
└─────────────────────┘
    ↓
系统就绪
```

### 4.2 恢复验证

恢复后必须验证以下内容：

1. **版本兼容性**：状态版本与软件版本兼容
2. **数据完整性**：必需字段都存在
3. **业务一致性**：缓存数据与实际数据一致
4. **资源可用性**：引用的资源仍然可用

## 五、状态同步

### 5.1 同步协议

主智能体与子智能体之间通过心跳包同步状态：

```json
{
  "message_type": "heartbeat",
  "sender": "data-governance-agent",
  "timestamp": "2026-05-15T10:30:00Z",
  "state": {
    "status": "idle",
    "health": "healthy"
  }
}
```

### 5.2 同步频率

| 智能体类型 | 心跳间隔 | 超时阈值 |
|-----------|---------|---------|
| 主智能体 | - | - |
| 任务编排层 | 30秒 | 90秒 |
| 子智能体 | 30秒 | 90秒 |

### 5.3 异常处理

当检测到子智能体心跳超时时：

1. 标记子智能体状态为 `unavailable`
2. 停止向该子智能体分配新任务
3. 尝试重新连接（最多3次）
4. 如仍失败，触发告警

## 六、状态查询接口

### 6.1 主智能体状态查询

```python
def get_master_agent_state() -> Dict[str, Any]:
    """获取主智能体状态"""
    return {
        "health_status": "healthy",
        "active_tasks": [],
        "cache_stats": {...},
        "reuse_stats": {...}
    }
```

### 6.2 子智能体状态查询

```python
def get_subagent_state(agent_id: str) -> Dict[str, Any]:
    """获取指定子智能体状态"""
    return {
        "agent_id": agent_id,
        "status": "idle",
        "health": "healthy",
        "performance": {...}
    }
```

### 6.3 全局状态查询

```python
def get_system_state() -> Dict[str, Any]:
    """获取全局系统状态"""
    return {
        "master_agent": get_master_agent_state(),
        "orchestration": get_orchestration_state(),
        "subagents": {
            "data-governance-agent": get_subagent_state("data-governance-agent"),
            "feature-analysis-agent": get_subagent_state("feature-analysis-agent"),
            "anomaly-detection-agent": get_subagent_state("anomaly-detection-agent"),
            "rule-reasoning-agent": get_subagent_state("rule-reasoning-agent")
        }
    }
```

## 七、状态转换

### 7.1 主智能体状态转换

```
初始化 → 运行中 → 降级 → 恢复
           ↓         ↓
         停止     错误
```

### 7.2 子智能体状态转换

```
空闲 → 忙碌 → 空闲
  ↓     ↓
错误  恢复
```

## 八、附录

### 8.1 状态文件示例

见 `shared/state/examples/` 目录：

- `master_agent_state_example.json`
- `orchestration_state_example.json`
- `subagent_state_example.json`

### 8.2 相关文档

- [子智能体通信协议](subagent_protocol.md)
- [错误码定义](error_codes.md)
