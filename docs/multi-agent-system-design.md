# 多智能体系统架构设计

## 概述

本文档定义了废水监测系统的多智能体架构，使用 Hermes Agent 框架实现主智能体协调多个专业子智能体完成监测分析任务。

## 架构原则

1. **真正的多智能体系统**：每个智能体（主、子）都有独立的身份、记忆、技能
2. **LLM 驱动的动态编排**：主智能体的 LLM 根据任务动态决策，不是写死的 if-else 逻辑
3. **文件状态共享通信**：通过共享文件实现主智能体和子智能体之间的通信
4. **职责分离**：工具只负责信息传递，LLM 负责编排决策

## 系统架构

```
用户查询 → Hermes API Server (8642) → 主智能体 (workspace/)
    ↓
主智能体 LLM 加载上下文:
  - SOUL.md: 主智能体身份
  - AGENTS.md: 工作规范  
  - MEMORY.md: 全局记忆
  - orchestrator-core/SKILL.md: 编排知识
    ↓
LLM 动态决策: 需要哪些子智能体？什么顺序？
    ↓
调用 call_subagent 工具执行决策
    ↓
子智能体 (subagents/*-agent/)
  - 读取 task.json
  - 加载自己的 SOUL.md/AGENTS.md/MEMORY.md
  - 调用自己的 skills/
  - 写入 result.json
    ↓
主智能体读取结果，继续后续步骤或整合回答
```

## 目录结构

```
E:\project\Ecological_env\
│
├── workspace/                          # 主智能体
│   ├── SOUL.md                        # 主智能体身份
│   ├── AGENTS.md                      # 工作规范
│   ├── MEMORY.md                      # 全局记忆
│   ├── config.yaml                    # 配置
│   │
│   ├── state/                         # 会话状态目录
│   │   └── session_YYYYMMDD_HHMMSS/  # 单次会话
│   │       ├── task.json
│   │       ├── data_result.json
│   │       ├── anomaly_result.json
│   │       ├── rule_result.json
│   │       ├── disposition_result.json
│   │       └── final_response.json
│   │
│   └── skills/                        # 主智能体技能
│       └── orchestrator-core/
│           ├── SKILL.md
│           └── scripts/
│               ├── __init__.py
│               ├── create_session.py
│               ├── call_subagent.py
│               └── cleanup_sessions.py
│
└── subagents/                         # 子智能体
    ├── multi-dimensional-data-perception-agent/
    │   ├── SOUL.md
    │   ├── AGENTS.md
    │   ├── MEMORY.md
    │   └── skills/
    ├── anomaly-detection-agent/
    ├── rule-reasoning-agent/
    └── disposition-execution-agent/
```

## 文件状态共享格式

### task.json（主智能体写入）

```json
{
  "task_id": "task_data_001",
  "task": "获取最近24小时进水和出水数据",
  "context": {
    "time_range": "24h",
    "indicators": ["COD", "TN", "TP", "pH"],
    "previous_result": null
  },
  "output_format": "json",
  "timeout": 300
}
```

### xxx_result.json（子智能体写入）

```json
{
  "task_id": "task_data_001",
  "status": "completed",
  "result": { },
  "error": null,
  "metadata": {
    "duration_seconds": 2.3,
    "timestamp": "2025-06-23T14:30:25"
  }
}
```

### 错误状态

```json
{
  "task_id": "task_data_001",
  "status": "failed",
  "error": "数据库连接超时",
  "error_code": "DB_TIMEOUT",
  "retry_count": 2
}
```

## 子智能体列表

### 1. 数据感知专家 (multi-dimensional-data-perception)
- **位置**: `../subagents/multi-dimensional-data-perception-agent`
- **能力**: 获取、清洗、标准化多维时序数据
- **触发**: 数据查询、指标获取、进水出水分析
- **输出**: 预处理后的数据

### 2. 异常检测专家 (anomaly-detection)
- **位置**: `../subagents/anomaly-detection-agent`
- **能力**: 检测时序异常和违规模式
- **触发**: 异常检测、突变分析、趋势判断
- **依赖**: 需要数据感知专家的输出
- **输出**: 异常点列表、违规事件

### 3. 规则推理专家 (rule-reasoning)
- **位置**: `../subagents/rule-reasoning-agent`
- **能力**: 基于法规标准进行违规判定
- **触发**: 合规判断、超标分析、违规原因
- **依赖**: 需要异常检测专家的输出
- **输出**: 合规结论、违规依据

### 4. 处置执行专家 (disposition-execution)
- **位置**: `../subagents/disposition-execution-agent`
- **能力**: 生成预警分级和处置工单
- **触发**: 工单生成、处置建议、预警通知
- **依赖**: 需要规则推理专家的输出
- **输出**: 工单详情、处置建议

## 工具定义

### create_session()

创建新的会话目录。

**返回**: 会话目录路径字符串

**实现要点**:
- 生成时间戳格式的目录名
- 在 `workspace/state/` 下创建目录
- 返回绝对路径供后续使用

### call_subagent(subagent_name, task, context)

调用子智能体执行任务。

**参数**:
- `subagent_name`: 子智能体名称
- `task`: 任务描述字符串
- `context`: 上下文信息字典（可选）

**返回**: 子智能体返回的结果字典

**实现流程**:
1. 写入 task.json 到当前会话目录
2. 设置 HERMES_HOME 环境变量指向子智能体目录
3. 设置 SESSION_DIR 环境变量指向当前会话目录
4. subprocess 调用 `hermes run`
5. 等待子智能体完成
6. 读取对应的 result.json 文件
7. 解析并返回结果

### cleanup_sessions(days)

清理指定天数前的会话目录。

**参数**:
- `days`: 保留最近几天的会话（默认 7）

**返回**: 清理的会话数量

## 错误处理与重试

### 错误分类

**可重试错误**:
- NETWORK_TIMEOUT: 网络超时
- API_RATE_LIMIT: API 限流
- DB_CONNECTION_ERROR: 数据库连接错误
- SERVICE_UNAVAILABLE: 服务不可用

**不可重试错误**:
- INVALID_PARAM: 参数错误
- PERMISSION_DENIED: 权限拒绝
- DATA_NOT_FOUND: 数据不存在
- FORMAT_ERROR: 格式错误

### LLM 驱动的重试

1. 子智能体失败，call_subagent 返回错误信息
2. LLM 分析错误类型
3. LLM 决定是否重试：
   - 可重试错误 → 重试（最多 3 次）
   - 不可重试错误 → 向用户报告
4. 必要时调整参数后重试

## 完整工作流程示例

### 查询：最近24小时出水COD异常吗？

1. **用户查询** → Hermes API Server → 主智能体

2. **主智能体 LLM 加载上下文**:
   - SOUL.md: 理解自己的角色
   - AGENTS.md: 了解工作规范
   - MEMORY.md: 获取全局记忆
   - orchestrator-core/SKILL.md: 学习编排知识

3. **LLM 决策**:
   - "用户问异常，需要数据和异常检测"
   - "不需要规则推理和处置"
   - 决策: data-perception → anomaly-detection

4. **调用 create_session()** → 创建 `session_20250623_143022/`

5. **调用 call_subagent("data-perception", "获取数据")**:
   - 写入 task.json
   - 设置环境变量
   - subprocess 调用数据感知子智能体
   - 读取 data_result.json

6. **调用 call_subagent("anomaly-detection", "检测异常", context=data_result)**:
   - 更新 task.json（包含 context）
   - subprocess 调用异常检测子智能体
   - 读取 anomaly_result.json

7. **LLM 整合结果**，生成最终响应返回用户

## 扩展性设计

### 添加新的监测对象

未来扩展到废气、噪声等监测对象时：

1. 在 `subagents/` 下创建新的子智能体目录
2. 配置新的 SOUL.md、AGENTS.md、MEMORY.md
3. 开发相应的专业技能
4. 在 orchestrator-core/SKILL.md 中添加新子智能体的描述
5. 主智能体 LLM 自动学会调用新子智能体

### 添加新的子智能体技能

每个子智能体的技能是独立开发的：
- 数据感知子智能体可以添加新的数据源技能
- 异常检测子智能体可以添加新的检测算法
- 不影响其他子智能体或主智能体

## 实施要点

1. **主智能体配置**:
   - `workspace/config.yaml` 只加载 orchestrator-core 技能
   - 设置 HERMES_HOME 环境变量指向 workspace/

2. **子智能体独立性**:
   - 每个子智能体有独立的 HERMES_HOME
   - 子智能体通过环境变量知道会话目录

3. **文件状态管理**:
   - 主智能体负责创建会话目录和写入 task.json
   - 子智能体负责读取 task.json 和写入 result.json
   - 定期清理旧会话

4. **LLM 决策机制**:
   - orchestrator-core/SKILL.md 提供编排知识
   - LLM 根据任务内容和知识动态决策
   - 不写死调用逻辑

## 成功标准

- [ ] 主智能体能正确加载所有上下文文件
- [ ] LLM 能根据查询动态选择子智能体
- [ ] 子智能体能正确读取 task.json 并写入 result.json
- [ ] 文件状态共享机制正常工作
- [ ] 错误处理和重试机制正常工作
- [ ] 会话目录正确创建和清理
- [ ] 端到端查询流程完整运行

## 参考资料

- LangGraph Multi-Agent Workflows: https://www.langchain.com/blog/langgraph-multi-agent-workflows
- How and When to Build Multi-Agent Systems: https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems
- Hermes Agent Framework Documentation

---

## 实施状态

### Phase 1: 主智能体和编排器 ✅

- [x] 主智能体 SOUL.md - 已更新文件状态共享架构说明
- [x] 主智能体 AGENTS.md - 已更新子智能体调用方式
- [x] 主智能体 MEMORY.md - 已添加调用方式说明
- [x] workspace/config.yaml - 已验证配置正确
- [x] orchestrator-core/SKILL.md - 已验证格式正确
- [x] orchestrator-core/scripts/__init__.py - 已创建包初始化
- [x] create_session 工具 - 已实现会话创建功能
- [x] call_subagent 工具 - 已实现子智能体调用功能
- [x] cleanup_sessions 工具 - 已实现会话清理功能
- [x] 集成测试 - 已验证所有文件存在

**Phase 1 完成时间**: 2026-06-24

### Phase 2: 文件状态共享机制 ✅

- [x] create_session.py - 已增强添加 get_session_files 函数
- [x] call_subagent.py - 已添加简化名称映射（data-perception 等）
- [x] schemas.py - 已创建任务和结果文件模式验证
- [x] call_subagent.py - 已更新使用 schema 验证
- [x] SKILL.md - 已添加详细工具使用文档
- [x] tests/test_file_state_sharing.py - 已创建集成测试
- [x] .gitignore - 已添加 state 目录忽略规则
- [x] 设计文档 - 已更新实施状态

**Phase 2 完成时间**: 2025-06-25
**下一步**: Phase 3 - 子智能体适配

### Phase 3: 子智能体适配 ✅

- [x] 创建 subagents/subagent_utils.py 共享工具模块
- [x] 适配 data-perception-agent 的 run_agent.py
- [x] 适配 anomaly-detection-agent 的 run_agent.py
- [x] 适配 rule-reasoning-agent 的 run_agent.py
- [x] 适配 disposition-execution-agent 的 run_agent.py
- [x] 更新所有子智能体 SOUL.md 文档
- [x] 创建手动测试脚本

**Phase 3 完成时间**: 2025-06-25

### Phase 4: 集成测试 ✅

- [x] 创建端到端工作流测试 (tests/integration/test_e2e_workflow.py)
- [x] 创建性能基准测试 (tests/performance/test_benchmarks.py)
- [x] 创建错误场景测试 (tests/integration/test_error_scenarios.py)
- [x] 创建测试套件运行器 (tests/run_all_tests.py)
- [x] 更新测试结果文档 (docs/test_results.md)

**Phase 4 完成时间**: 2026-06-25

**测试覆盖**:
- 7个端到端工作流测试
- 7个错误场景测试
- 4个性能基准测试
- 完整的手动测试脚本

**运行方式**:
```bash
# 运行所有测试
python tests/run_all_tests.py

# 运行单个测试模块
python tests/integration/test_e2e_workflow.py
python tests/integration/test_error_scenarios.py
python tests/performance/test_benchmarks.py
```
