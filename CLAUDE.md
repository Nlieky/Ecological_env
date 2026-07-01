# 废水监测系统 - Claude AI助手配置

> **重要架构更新（2026-06-30）**
>
> 本项目已迁移到**Hermes Agent框架**作为底层智能体框架。

## 核心架构原则

### LLM驱动主智能体框架

本项目采用Hermes Agent框架（NousResearch/hermes-agent）实现LLM驱动的智能体架构：

- **主智能体**（workspace/）：使用Hermes AIAgent类，负责意图识别、任务编排、对话管理
- **4个子智能体**（subagents/）：每个都是独立的Hermes AIAgent实例，通过subprocess启动
- **三库一体**（shared/）：operators（算子库）、data（数据库）、knowledge（知识库）统一在shared/目录

### 子智能体调用规范

主智能体通过**自定义工具集**调用子智能体：
- **调用方式**：通过 `workspace/skills/orchestrator-core/scripts/subagent_tools.py` 工具集
- **LLM 驱动**：主智能体通过 LLM 理解任务并动态决定调用哪些子智能体
- **上下文隔离**：每个子智能体通过 subprocess 启动，获得独立的会话目录
- **通信机制**：通过 `sessions/` 目录共享 task.json 和 result.json
- **身份文件加载**：每个子智能体加载自己的 SOUL.md、AGENTS.md、MEMORY.md

### Hermes框架特性

- **记忆机制**：跨会话记忆，让项目越来越清晰
- **身份文件支持**：SOUL.md（个性）、AGENTS.md（规则）、MEMORY.md（记忆）、USER.md（用户配置）
- **OpenAI 兼容接口**：支持 ctgu-vlm 模型

---

## Project Overview

Wastewater false discharge monitoring system based on a patent architecture using 6 layers: human-computer interaction, data collection, master agent, task orchestration, sub-agent, and data support layers. The system uses a Large Language Model (LLM) as a core coordinator that reads master/sub-agent identity files and calls pre-developed scripts from four sub-agents.

**当前状态**：后端API已完成，前端界面尚未开发。

---

## 核心架构原则（必须遵守）

### 原则1: 三库一体 - 全局资源共享

**数据库、算子库、知识库必须放在全局 `shared/` 目录，供所有子智能体调用**。

**三库结构**：
- **时序监测数据库** (`shared/data/`, `shared/knowledge/`):
  - 实时数据存储
  - 历史数据归档
  - 数据质量管控

- **异常检测模型算子库** (`shared/operators/`):
  - `statistical/`: 统计算子
  - `ml/`: 机器学习算子（孤立森林、One-Class SVM、LOF、HBOS）
  - `deep_learning/`: 深度学习算子（LSTM自编码器、变分自编码器）

- **废水排放知识库** (`shared/knowledge/`):
  - `regulations/`: 法规库
  - `process_knowledge/`: 工艺知识库
  - `violation_patterns/`: 违规模式库
  - `expert_experience/`: 专家经验库

**重要约束**：
- ❌ **禁止**在子智能体内部 (`subagents/*/scripts/`) 重复实现算子逻辑
- ✅ 子智能体**必须**通过接口调用 `shared/operators/` 中的算子
- ✅ 新增算子**必须**添加到 `shared/operators/` 对应分类目录

### 原则2: LLM驱动主智能体 - 智能调度框架

**主智能体必须使用 LLM 进行意图识别、逻辑推理，然后合理调用子智能体**。

**标准调用流程**：
```
1. 主智能体加载身份文件 (IDENTITY.md, AGENTS.md, SOUL.md, MEMORY.md)
      ↓
2. LLM 意图识别：理解用户查询或数据信号的真实意图
      ↓
3. LLM 逻辑推理：基于意图规划执行策略
      ↓
4. 主智能体调用子智能体（按需选择）：
   - 多维数据感知子智能体 (multi-dimensional-data-perception-agent)
   - 异常检测子智能体 (anomaly-detection-agent)
   - 规则推理子智能体 (rule-reasoning-agent)
   - 研判预警与处置执行子智能体 (disposition-execution-agent)
      ↓
5. 子智能体调用全局资源：
   - 从 shared/operators/ 调用算子
   - 从 shared/knowledge/ 调用知识
   - 从 shared/data/ 获取数据
      ↓
6. 主智能体汇总结果，生成自然语言报告
```

**重要约束**：
- ❌ **禁止**为了告警目的随便调用脚本，跳过 LLM 推理
- ❌ **禁止**在子智能体内部重复实现全局资源
- ❌ **禁止** LLM 调用失败时静默回退到规则模式
- ✅ **必须**使用 LLM 进行意图识别和子智能体调度
- ✅ LLM 调用失败**必须**抛出明确的错误提示
- ✅ 实现智能重试（最多3次，指数退避）

---

## Common Commands

### 启动后端服务（推荐）

```bash
# FastAPI Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 或使用启动脚本
scripts\start_backend.bat      # Windows
bash scripts/start_backend.sh   # Linux/Mac
```

访问 API 文档：`http://localhost:8000/docs`

### 简单 HTTP 包装器

```bash
python simple_http_wrapper.py
```

访问：`http://localhost:5000`

### 配置

```bash
# 设置环境变量
cp .env.example .env
# 编辑 .env 设置 LLM_API_KEY 等
```

### 测试

```bash
# 运行集成测试
python tests/integration/test_full_pipeline.py

# 验证子智能体
python scripts/verify_all_subagents.py
```

### 监控

```bash
# 访问 Prometheus 指标
curl http://localhost:8000/metrics

# 健康检查
curl http://localhost:8000/api/health
```

---

## Architecture Overview

### 实际系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 人机交互层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  FastAPI    │  │  Grafana看板 │                             │
│  │  API接口    │  │  可视化监控  │                              │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ② 数据采集层                                                    │
│  ┌──────────────┐                                             │
│  │ dual_data_stream.py │                                        │
│  └──────────────┘                                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ③ 主智能体层                                                    │
│  workspace/SOUL.md + AGENTS.md + MEMORY.md                      │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ④ 任务编排层                                                    │
│  workspace/skills/orchestrator-core/                            │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑤ 子智能体层                                                    │
│  4个子智能体（各自独立身份文件）                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑥ 数据支撑层                                                    │
│  shared/（三库一体）                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Sub-Agents

1. **multi-dimensional-data-perception-agent** 📊: "多维数据感知子智能体" - Multi-Dimensional Data Processor, Vibe: 严谨、可靠、多源整合
2. **anomaly-detection-agent** 🔍: "异常检测子智能体" - Anomaly Detector, Vibe: 警惕、全面、谦逊
3. **rule-reasoning-agent** ⚖️: "规则推理子智能体" - Knowledge Reasoner, Vibe: 博学、精准、公正
4. **disposition-execution-agent** 🚨: "研判预警与处置执行子智能体" - Action Executor, Vibe: 高效、规范、执行力强

---

## LLM Integration

### Client Configuration

- LLM client wrapper: `shared/configs/llm_client.py`
- Environment variables: `.env` (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL)
- Non-sensitive config: `shared/configs/llm_config.yaml`

### LLM Configuration

```bash
# .env 文件配置
LLM_BASE_URL=http://172.16.12.41:30000/v1
LLM_API_KEY=sk-4e9a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f
LLM_MODEL=ctgu-vlm
```

**注意**：ctgu-vlm 是 OpenAI 兼容 API，不是 Anthropic Claude API。

### Identity Files

**Master Agent** (workspace/):
- IDENTITY.md: Identity card
- AGENTS.md: Workspace rules, conventions
- SOUL.md: Personality and tone
- MEMORY.md: Long-term memory
- USER.md: User information
- TOOLS.md: Environment-specific notes

**Sub-Agents** (subagents/{agent}/):
- IDENTITY.md: Identity card
- AGENTS.md: Sub-agent specific task instructions
- SOUL.md: Sub-agent's role and personality
- TOOLS.md: Sub-agent specific tool conventions
- MEMORY.md: Professional long-term memory

---

## Data Flow

### 实时监测流程
```
stream/dual_data_stream.py → FastAPI /api/dual-stream
    ↓
Task Receiving & Parsing (master agent identity loaded)
    ↓
LLM coordinates 4 sub-agents (each loads its own identity):
    1. multi-dimensional-data-perception-agent
    2. anomaly-detection-agent
    3. rule-reasoning-agent
    4. disposition-execution-agent
    ↓
Result Interpretation (knowledge base loaded)
    ↓
Natural language report + alerts
```

---

## Key Files

### 后端
- `backend/main.py`: FastAPI 主应用
- `backend/api/client.py`: Hermes API 客户端
- `backend/api/routes/`: API 路由定义

### 日志系统
- `backend/database/`: SQLAlchemy 数据库配置
  - `base.py`: 数据库引擎和基类
  - `session.py`: 会话管理
  - `init_db.py`: 初始化脚本
  - `maintain_db.py`: 维护脚本
- `backend/models/logging.py`: 日志数据模型
- `backend/api/routes/logs.py`: 日志查询接口
- `backend/middleware/logging_middleware.py`: API 调用日志中间件
- `backend/utils/loggers.py`: 日志记录工具函数

### 核心模块
- `stream/dual_data_stream.py`: 双数据流发送器
- `workspace/skills/orchestrator-core/scripts/`: 核心编排模块
- `shared/configs/llm_client.py`: LLM 客户端
- `shared/knowledge/`: 知识库
- `shared/operators/`: 异常检测算子

### 配置
- `.env`: 环境变量配置
- `.hermes/config.yaml`: Hermes 框架配置
- `requirements.txt`: Python 依赖

---

## Violation Detection

The system detects 4 types of violations:
1. **插瓶干扰** (bottle interference): Constant or near-constant values
2. **人工拟合** (artificial fitting): Too-smooth curves, low variance
3. **稀释排放** (dilution discharge): Sudden flow increase with proportional pollutant decrease
4. **恶意逃避** (malicious evasion): Patterns designed to avoid detection

---

## Environment

- **Python**: 3.12.12
- **虚拟环境**: `ecological_env` (通过 uv 创建)
- **LLM**: ctgu-vlm (OpenAI 兼容 API)
- **后端端口**: 8000 (FastAPI), 5000 (简单包装器)
- **Hermes API**: 8642

---

## Notes

- Path resolution uses multiple strategies to find workspace/ and subagents/ directories dynamically
- IntentResult is a dataclass - access attributes via dot notation, not `.get()` method
- Prometheus metrics expose influent/effluent pH, COD, TN, AN, TP, flow rate, and counters for data processed, anomalies detected, and alerts
- **前端界面尚未开发**，当前只有后端 API
