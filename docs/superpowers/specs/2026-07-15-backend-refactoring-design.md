# 后端重构设计文档

**日期**: 2026-07-15
**状态**: 待审批
**作者**: Claude Code
**目标**: 清理旧版 Hermes API Server 依赖，使用自定义 AIAgent

## 问题背景

当前后端存在架构混乱问题：

1. **双重系统并存**
   - `query.py` 直接导入原生 Hermes Agent 的 AIAgent
   - `hermes.py` 使用 HermesAPIClient 通过 HTTP 调用 Hermes API Server
   - 造成混乱和维护困难

2. **未使用正确的 AIAgent 版本**
   - 项目已有自定义 AIAgent：`shared/framework/hermes_agent/run_agent.py`
   - 扩展了身份文件读取支持（7个文件）
   - 但 `query.py` 仍在使用原生版本：`D:\Hermes\hermes-agent\run_agent.py`

3. **冗余的服务层**
   - Hermes API Server (端口 8642) 完全没有必要
   - AIAgent 可以直接导入使用
   - 增加了不必要的复杂度和延迟

## 目标架构

### 新架构

```
前端 (Vue 3)
    ↓ HTTP POST /api/query
FastAPI (backend/)
    ↓ 调用
AgentService (新建)
    ↓ 使用
AIAgent (shared/framework/hermes_agent)
    ↓ 加载
7个主智能体身份文件 + 4个子智能体
    ↓ 返回
QueryResponse
```

### 核心原则

1. **单一职责**：每个模块只做一件事
2. **清晰分层**：API → 服务 → 智能体
3. **无外部依赖**：不依赖额外的 HTTP 服务
4. **使用自定义版本**：使用 `shared/framework/hermes_agent` 而非原生 hermes-agent

## 组件设计

### 1. AgentService (新建)

**位置**: `backend/services/agent_service.py`

**职责**:
- 封装智能体调用逻辑
- 管理 AIAgent 实例缓存
- 处理会话状态

**核心方法**:
```python
class AgentService:
    def __init__(self):
        self.agent_cache = {}
        self.project_dir = Path("E:/project/Ecological_env").resolve()

    def get_agent(self, session_id: str) -> AIAgent:
        """获取或创建智能体实例，确保在正确的工作目录"""

    def process_query(self, query: str, session_id: str) -> QueryResponse:
        """处理查询并返回完整响应"""
```

**AIAgent 配置**:
```python
from shared.framework.hermes_agent.run_agent import AIAgent

agent = AIAgent(
    base_url=base_url,           # 从环境变量读取
    api_key=api_key,
    model=model,
    provider=provider,
    load_soul_identity=True,      # 加载 workspace/SOUL.md
    skip_context_files=False,     # 加载 AGENTS.md、MEMORY.md 等
    enabled_toolsets=["orchestrator", "skills", "terminal"],
    max_iterations=10,
    session_id=session_id,
)
```

### 2. QueryRoute (重构)

**位置**: `backend/api/routes/query.py`

**变更**:
- 移除直接的 AIAgent 创建代码
- 使用 AgentService 处理业务逻辑
- 只负责 HTTP 接口层

**简化后**:
```python
@router.post("/query")
async def execute_query(request: QueryRequest):
    service = AgentService()
    return await service.process_query(request.query, request.session_id)
```

### 3. 身份文件加载

自定义 AIAgent 通过 `identity_loader.py` 加载7个身份文件：

1. `IDENTITY.md` - 身份卡片
2. `SOUL.md` - 身份和个性
3. `AGENTS.md` - 工作区规范
4. `MEMORY.md` - 长期记忆
5. `USER.md` - 用户信息
6. `TOOLS.md` - 工具配置
7. `HEARTBEAT.md` - 周期性任务

### 4. 删除的组件

| 文件 | 原因 |
|------|------|
| `backend/api/client.py` | HermesAPIClient 不再需要 |
| `backend/api/routes/hermes.py` | 依赖 HermesAPIClient，功能合并到 query.py |
| `start_hermes_server.*` | Hermes API Server 不再需要 |
| `.hermes/` 目录 | Hermes API Server 配置，不再需要 |

### 5. 保留的组件

| 文件 | 说明 |
|------|------|
| `backend/api/routes/realtime.py` | Mock 实时数据，以后连接真实数据源 |
| `backend/api/routes/events.py` | Mock 事件管理，以后连接真实数据源 |
| `backend/api/routes/tracing.py` | Mock 链路追踪，以后连接真实数据源 |
| `backend/api/routes/logs.py` | 日志查询接口 |
| `backend/api/routes/health.py` | 健康检查 |

## 数据流设计

### 完整查询流程

```
前端
    ↓ HTTP POST /api/query { query, session_id? }
FastAPI (query.py)
    ↓ 验证请求
AgentService.get_agent(session_id)
    ↓ 检查缓存
    ↓ 创建新实例（如需要）
AIAgent.__init__(load_soul_identity=True, skip_context_files=False)
    ↓ identity_loader.py 加载7个文件
    ↓ 加载技能 (workspace/skills/)
    ↓ 加载工具 (enabled_toolsets)
    ↓ 返回 AIAgent 实例
AgentService.process_query()
    ↓ 调用
AIAgent.run_conversation(user_message=query)
    ↓ LLM 推理 + 工具调用
    ↓ 返回 Dict[str, Any]
    ↓ 提取字段
QueryResponse {
    content: final_response,
    session_id: session_id,
    timestamp: ISO8601,
    chartData: chart? (可选)
}
    ↓ JSON 序列化
前端
```

### 错误处理

**层级1 - AgentService**:
```python
try:
    agent = get_agent(session_id)
    response = agent.run_conversation(...)
except ImportError as e:
    raise AgentInitializationError(f"AIAgent 导入失败: {e}")
except Exception as e:
    raise AgentProcessingError(f"智能体调用失败: {e}")
```

**层级2 - FastAPI**:
```python
try:
    result = await service.process_query(...)
except AgentError as e:
    raise HTTPException(status_code=500, detail=e.message)
```

## 实施计划

### 阶段1：创建新服务层
1. 创建 `backend/services/__init__.py`
2. 创建 `backend/services/agent_service.py`
3. 实现 AgentService 类
4. 使用 `from shared.framework.hermes_agent.run_agent import AIAgent`

### 阶段2：重构 query.py
5. 修改导入路径
6. 移除直接的 AIAgent 创建代码
7. 使用 AgentService 处理请求
8. 保持响应格式不变

### 阶段3：清理旧代码
9. 删除 `backend/api/client.py`
10. 删除 `backend/api/routes/hermes.py`
11. 清理 `backend/main.py` 中的相关引用
12. 删除 `scripts/start_hermes_server.*`
13. 清理 `.hermes/` 目录（如无其他用途）
14. 清理环境变量中的 HERMES_API_URL、HERMES_API_KEY

### 阶段4：验证
15. 启动后端服务
16. 测试 `POST /api/query` 接口
17. 验证7个身份文件正确加载
18. 验证子智能体调用正常
19. 对比测试前后的响应时间

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 自定义 AIAgent 导入失败 | 中 | 高 | 添加 try-except 和详细错误日志 |
| 身份文件路径错误 | 低 | 中 | 添加存在性检查和警告 |
| 旧代码残留影响 | 低 | 中 | 完整搜索清理并测试 |
| 前端兼容性问题 | 低 | 中 | 保持响应格式不变 |

## 验收标准

1. ✅ `/api/query` 接口正常工作
2. ✅ 使用自定义 AIAgent（`shared/framework/hermes_agent`）
3. ✅ 7个身份文件正确加载
4. ✅ 子智能体调用正常
5. ✅ 无 Hermes API Server 进程运行
6. ✅ 无 `backend/api/client.py` 引用
7. ✅ 响应时间无显著增加

## 后续工作

1. **连接真实数据源**: 替换 realtime.py、events.py 的 Mock 数据
2. **前端优化**: 确保前端正确显示最终答案而非执行步骤
3. **性能优化**: 根据实际使用情况调整缓存策略
4. **监控增强**: 添加更详细的日志和指标

---

**设计完成时间**: 2026-07-15
**预计实施时间**: 1-2小时
**优先级**: 高
