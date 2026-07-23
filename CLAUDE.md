# 废水监测系统 - Claude AI助手配置

> **重要架构更新（2026-07-14）**
>
> 本项目基于 **Hermes Agent 框架**实现多智能体架构：
> - 主智能体和 4 个子智能体身份文件已完善
> - 子智能体目录结构已简化（只保留 3 个身份文件 + skills/）
> - 主智能体调用子智能体功能已验证通过

## 核心架构原则

### LLM驱动主智能体框架

本项目采用Hermes Agent框架（NousResearch/hermes-agent）实现LLM驱动的智能体架构：

- **主智能体**（workspace/）：使用Hermes AIAgent类，负责意图识别、任务编排、对话管理
- **4个子智能体**（subagents/）：**确定性脚本执行器**——`entry.py` 直接跑 canonical 脚本（不经 LLM 会话），通过 subprocess 启动
- **三库一体**（shared/）：operators（算子库）、data（数据库）、knowledge（知识库）统一在shared/目录

### 子智能体调用规范

主智能体通过**编排工具**调用子智能体（`tool_registration.py` 把 4 个编排工具灌进 `agent.tools`，并精简为只留这 4 个）：
- **调用方式**：主智能体 LLM 调 `call_subagent(subagent_name, task)` → `call_subagent.py` subprocess 跑子智能体 `entry.py`
- **LLM 驱动**：主智能体按 `workspace/AGENTS.md` 顶部的"编排铁律"决定调哪些子智能体、什么顺序
- **确定性执行**：子智能体 `entry.py` **直接跑 canonical 脚本**（get_data / run_anomaly_detection_simple / run_rule_reasoning / run_disposition），**不经 LLM 会话**（早期 LLM 会话会让 ctgu-vlm 用 terminal/execute_code 瞎逛几十轮、极慢；2026-07-23 改为脚本直跑，4 个合计 ~25s）
- **通信机制**：通过共享 `sessions/<session>/` 目录传 task.json + 各 `*_result.json`（链式：规则读异常结果、处置读规则结果）
- **身份文件**：主智能体加载 7 个身份文件；子智能体脚本直跑、不经 LLM，运行时不实际加载身份文件

### Hermes框架特性

- **记忆机制**：跨会话记忆，让项目越来越清晰
- **身份文件支持**：SOUL.md（个性）、AGENTS.md（规则）、MEMORY.md（记忆）、USER.md（用户配置）
- **OpenAI 兼容接口**：支持 LongCat-2.0 模型（美团）

---

## Project Overview

Wastewater false discharge monitoring system based on a patent architecture using 6 layers: human-computer interaction, data collection, master agent, task orchestration, sub-agent, and data support layers. The system uses a Large Language Model (LLM) as a core coordinator that reads master/sub-agent identity files and calls pre-developed scripts from four sub-agents.

**当前状态**：后端 API 完成；前端框架完成(Phase 0-3A)，部分页面待填充(Phase B)；智能体 pipeline 已跑通(2026-07-23)。

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
# 主智能体身份文件测试
python scripts/test_identity_content.py

# 主智能体对话测试
python scripts/test_master_conversation.py

# 子智能体身份文件测试
python scripts/test_subagent_identity_content.py

# 主智能体调用子智能体测试
python scripts/test_master_calls_subagent.py
```

### 测试结果

- 身份文件内容验证：**56/56 通过**
- 主智能体对话：**测试通过**
- 子智能体调用：**3/3 通过**

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
# .env 文件配置（当前实际使用：本地部署的 ctgu-vlm）
LLM_BASE_URL=http://172.16.12.41:30000/v1
LLM_API_KEY=sk-xxx  # 由部署方提供
LLM_MODEL=ctgu-vlm

# 备用：美团 LongCat-2.0（OpenAI 兼容 API，已在 .env 中注释保留）
# LLM_BASE_URL=https://api.longcat.chat/openai/v1
# LLM_MODEL=LongCat-2.0
```

**注意**：ctgu-vlm 与 LongCat-2.0 均为 OpenAI 兼容 API，不是 Anthropic Claude API。实际生效配置以 `.env` 为准，本文件仅作文档说明。

### Identity Files

**Master Agent** (workspace/, 7 个身份文件，启动时全加载):
- IDENTITY.md: Identity card
- SOUL.md: Personality and tone
- AGENTS.md: Workspace rules, conventions（含"编排铁律"）
- MEMORY.md: Long-term memory
- USER.md: User information
- TOOLS.md: Environment-specific notes
- HEARTBEAT.md: Periodic tasks

**Sub-Agents** (subagents/{agent}/):
- SOUL.md: Identity and personality
- AGENTS.md: Usage instructions and responsibilities
- MEMORY.md: Professional long-term memory

注意：子智能体目录保留 3 个身份文件（SOUL.md, AGENTS.md, MEMORY.md）作文档；但 2026-07-23 起子智能体改为**脚本直跑、不经 LLM 会话**，运行时不实际加载这些身份文件。

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
- **LLM**: ctgu-vlm (本地部署 @ http://172.16.12.41:30000/v1，OpenAI 兼容 API；备用 LongCat-2.0 美团)
- **后端端口**: 8000 (FastAPI), 5000 (简单包装器)
- **Hermes API**: 8642

---

## Notes

- Path resolution uses multiple strategies to find workspace/ and subagents/ directories dynamically
- IntentResult is a dataclass - access attributes via dot notation, not `.get()` method
- Prometheus metrics expose influent/effluent pH, COD, TN, AN, TP, flow rate, and counters for data processed, anomalies detected, and alerts
- **实时数据为历史数据模拟**：当前无真实传感器接入，`/api/v1/monitoring/realtime` 等接口返回的是 `data/*.csv` 历史数据的最新行（截至 2024-12-31），用于打通"采集→主智能体→子智能体→报告"全链路。接入真实数据源后，替换 `backend/services/monitoring_data_loader.py` 的取数逻辑即可，上下游接口不变。
- **对话历史持久化**：`/api/query` 在拿到 Agent 响应后，会把用户提问 + Agent 回答写入 `conversations` / `conversation_messages` 表（以 `session_id` 作为 `conversation_id`，同一 session 的多轮问答追加到同一条对话）。前端可通过 `/api/v1/conversations` 及 `/api/v1/conversations/{id}`（含 messages）读取真实问答。Hermes 框架自身另有 session DB（`_persist_session`）与 `workspace/MEMORY.md`（长期领域知识），与本表的对话历史是分离的存储。
- **前端界面**：已开发（Phase 0-3A 框架完成：AI 助手页 / 监测大屏 / 日志 / 链路追踪等；Phase B 部分占位页待填充）。AI 助手页支持流式（见下）。
- **流式+进度反馈 + 服务/后端非阻塞（2026-07-23）**：
  - **非阻塞**：agent 服务(`scripts/start_agent.py`)与后端(`backend/api/routes/query.py`)都修了事件循环阻塞——`/query`、`/api/query` 由 `async def` 改 `sync def`（FastAPI 自动丢线程池，事件循环畅通；查询中 `/health` 从冻结→~2s）。agent 服务加 `threading.Lock` 串行化 master_agent + 300s 锁超时；`HERMES_TOTAL_TIMEOUT` 2400→300s。
  - **流式端点**（SSE-over-POST，查询带 body 故前端用 `fetch` 读流而非 EventSource）：`POST /query/stream`(agent 服务，`scripts/start_agent.py`) → `/api/query/stream`(后端 `httpx` 流式透传) → 前端 `queryService.executeStream` 消费。事件 `data:{json}`：`progress`(子智能体 start/done+摘要，如"14个异常")、`delta`(最终回答逐字)、`done`、`error`。进度经 `tool_registration.py` 模块级队列挂钩 `call_subagent`（靠锁串行保证安全；工具在 ThreadPoolExecutor 线程跑，故用模块全局而非 contextvar）；逐字经 `run_conversation(stream_callback=)`。**保留**阻塞 `/query` 向后兼容。
  - 前端 AI 助手页(`AIOpsChatView`/`ChatMessage`)：流式中实时显示「⏳ 正在调用 X 子智能体…」+ 回答逐字（流式时原始文本+光标，完成后转 markdown），不再是 30-60s 静态转圈。
- **Hermes 框架本地化现状（2026-07-23，已清理 + 修通）**：三层干净结构。
  - ① **原生引擎** `shared/framework/hermes-agent/`（vendored upstream v0.16.0，editable 安装，gitignore，`scripts/vendor_hermes.py --src D:\Hermes\hermes-agent` 复现）。`agent/`(conversation_loop/system_prompt/tools 等)、顶层 `run_agent`/`hermes_constants` 都解析到这里——这是真正在跑的引擎。
  - ② **定制层** `shared/framework/hermes_agent/`（下划线，7 个活文件）：薄壳 AIAgent(`run_agent.py`，forward `run_conversation` 到原生 loop) + `agent_init.py` + **`identity_loader.py`（唯一真定制：读全部身份文件，原生只读 SOUL.md）** + process_bootstrap.py/utils.py。早期 ~1 万行的死代码 fork（slim conversation_loop、下划线 system_prompt/prompt_builder/hermes_constants/runtime_cwd）已于 2026-07-23 删除。
  - ③ **overlays** `shared/framework/hermes-overlays/`（3 个，全功能必需）：`agent_init.py` + `run_agent.py`（身份定制，转发到下划线 agent_init）、`tools/orchestrator_tool.py`（编排桥）。orchestrator 工具运行时由 `tool_registration.py` 以 `override=True` 注册（correct schema + bridge），覆盖 vendored 自带的损坏版。
  - **身份加载（2026-07-23 修好，之前是坏的）**：原生 system_prompt 只读 SOUL.md；通过 `vendor_hermes.py` 的 PATCH 给原生 `agent/system_prompt.py` 接了 20 行——按 `_identity_path`(主智能体) / `HERMES_HOME`(子智能体) 加载目录里全部身份文件。主智能体读 7 个。（子智能体现为脚本直跑、不经 LLM，不实际加载身份。）
  - **主智能体工具精简（2026-07-23）**：`tool_registration.py` 注册 4 个编排工具后，把 `agent.tools` 过滤成只剩这 4 个（call_subagent/list_subagents/create_session/read_result），移除 skill_view/skill_manage/memory/terminal 等会让主智能体跑偏的工具——砍后编排可靠性 3/3。
  - **确定性子智能体（2026-07-23）**：`subagents/*/entry.py` 直接跑 canonical 脚本（get_data / run_anomaly_detection_simple / run_rule_reasoning / run_disposition），**不经 LLM 会话**（早期 LLM 会话让 ctgu-vlm 瞎逛几十轮、极慢）。4 个合计 ~25s，结果经 `sessions/` 共享目录链式传递。
  - **超时**：`shared/framework/hermes_agent/agent/conversation_loop.py` 的 total/tool/llm_timeout 改 env 驱动（`HERMES_TOTAL_TIMEOUT` 等，默认 2400/300/120）；`call_subagent.py` 的 `SUBAGENT_TIMEOUT` 默认 600s。
  - **仍待办（不影响运行）**：下划线 `run_agent.py`(5358行)/`agent_init.py`(1763行) 仍是从原生拷的大 fork，瘦身 = 切原生 AIAgent（要改 start_agent.py + entry.py 的 import，有风险，单独工作流）。
