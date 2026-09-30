# 废水虚假排放智能监测系统

> 一种多智能体协同的废水虚假排放智能监测方法及系统

## 📖 专利概述

本系统基于发明专利《一种多智能体协同的废水虚假排放智能监测方法及系统》实现，采用 **Hermes Agent 框架**构建覆盖多源数据接入、标准化治理、多维特征挖掘、时序异常识别、工艺机理校验、法规规则推理、专家经验复审的全链条、一体化废水虚假排放智能监测体系。

### 核心能力

- 🎯 **精准识别**：插瓶干扰、暗管偷排、清水稀释排放、数据篡改定值、虚假停产、工况造假等违规行为
- 🤖 **智能协同**：Hermes 主智能体全局调度 + 4 大子智能体专业执行
- 💬 **自然交互**：支持自然语言发起复杂分析查询，系统自动完成任务解析、算子调度、指标关系分析
- 🔄 **闭环优化**：基于监管反馈持续更新知识库、算法策略与判定规则

## 技术栈

| 组件 | 技术 |
|------|------|
| **底层框架** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) - LLM驱动智能体框架 |
| **后端** | FastAPI + Uvicorn |
| **Python** | 3.12.12 (uv 虚拟环境 `ecological_env`) |
| **LLM** | ctgu-vlm（本地部署 @ http://172.16.12.41:30000/v1，OpenAI 兼容 API；备用 LongCat-2.0） |
| **前端** | Vue 3 + Element Plus + Pinia + ECharts |
| **监控** | Prometheus + Grafana |

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 人机交互层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  FastAPI    │  │  Grafana看板 │                             │
│  │  API接口     │  │  可视化监控  │            │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ② 数据采集层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  数据流发送  │  │  数据传输     │  ← CSV/模拟流/实时API        │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ③ 主智能体层（Hermes 智能体）                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ SOUL.md  │ │ AGENTS.md│ │ MEMORY.md│ │ LLM驱动  │              │
│  │  身份    │ │  规范    │ │  记忆    │ │  调度    │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ④ 任务编排层（orchestrator-core）                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │智能路由  │ │结果聚合  │ │降级处理  │ │ 工作流   │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑤ 子智能体层（4 个专业子智能体）                                  │
│  ┌──────────────────┐ ┌──────────────────┐                      │
│  │多维数据感知子智能体│ │异常检测子智能体  │                       │
│  │多源数据/时序对齐 │ │5类异常/4类违规  │                        │
│  ├──────────────────┤ ├──────────────────┤                      │
│  │规则推理子智能体  │ │研判预警与处置执行  │                       │
│  │工艺机理/法规匹配│ │预警生成/处置协调  │                         │
│  └──────────────────┘ └──────────────────┘                      │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑥ 数据支撑层（三库一体）                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │算子库    │ │ 知识库    │ │ 数据库    │                         │
│  └──────────┘ └──────────┘ └──────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### 实际运行链路（2026-07-23）

上面是专利 6 层概念架构；**实际运行**是 3 个服务 + LLM 驱动多智能体 + 流式：

```
浏览器(5173) → 后端(8000) → 智能体服务(8642)
                              ↓ 主智能体（LLM，4 个编排工具，加载 7 个身份文件）
                              ↓ call_subagent → 共享 subagent_entry.py（subprocess）
                              ↓ 4 个子智能体（各自 LLM 会话，加载自己的 SOUL/AGENTS/MEMORY）
                              ↓   预加载 SKILL.md → terminal 跑 canonical 脚本 → 调 shared 算子/知识
                              ↓ 结果经 sessions/ 共享目录链式传递（data→anomaly→rule→disposition）
                              ↓ SSE 流式回前端（子智能体调用进度 + 回答逐字）
```

- 主智能体 + 4 子智能体**都是 LLM 驱动**（各自加载身份、LLM 选 skill 调脚本，脚本调 shared 三库干活）。
- **防瞎逛**：子智能体 SKILL.md 预加载进 prompt + 仅开 terminal 工具 + 低迭代上限。
- 一轮完整违规研判 ~2 分钟（LLM 驱动代价）；针对性查询（如只查异常）主智能体动态只调必要子智能体。

## 目录结构

```
Ecological_env/                    # 项目主目录
│
├── backend/                       # FastAPI 后端
│   ├── main.py                    # 主应用（端口 8000）
│   ├── api/                       # API 模块
│   │   ├── routes/                # API 路由
│   │   │   ├── health.py          # 健康检查
│   │   │   ├── hermes.py          # Hermes 系统信息
│   │   │   ├── query.py           # 查询接口
│   │   │   ├── logs.py            # 日志查询
│   │   │   ├── realtime.py        # 实时数据
│   │   │   ├── events.py          # 事件查询
│   │   │   └── tracing.py         # 链路追踪
│   │   └── client.py              # Hermes API 客户端
│   ├── core/                      # 核心配置
│   ├── database/                  # 数据库模块
│   ├── metrics/                   # Prometheus 指标
│   └── utils/                     # 工具函数
│
├── frontend/                      # Vue 3 前端
│   ├── src/                       # 源代码
│   │   ├── api/                    # API 客户端
│   │   ├── stores/                 # 状态管理
│   │   ├── views/                  # 页面视图
│   │   └── components/             # 组件
│   └── package.json               # 前端依赖
│
├── workspace/                     # Hermes 主智能体身份工作区
│   ├── SOUL.md                    # 主智能体身份和个性
│   ├── AGENTS.md                  # 工作区规范
│   ├── MEMORY.md                  # 全局长期记忆
│   ├── USER.md                    # 用户信息
│   ├── IDENTITY.md                # 身份卡片
│   ├── HEARTBEAT.md               # 周期性任务
│   ├── TOOLS.md                   # 工具配置
├── skills/                        # 主智能体技能包（项目根，HERMES_HOME 作用域）
│   ├── orchestrator-core/         # 编排器核心技能与调用接缝
│   └── action-command-core/       # 前端动作与轻量检测技能
│
├── subagents/                     # 4 个子智能体
│   ├── multi-dimensional-data-perception-agent/  # 多维数据感知
│   │   ├── SOUL.md               # 子智能体身份和个性
│   │   ├── AGENTS.md             # 子智能体规范
│   │   ├── MEMORY.md             # 子智能体专业记忆
│   │   └── skills/               # 子智能体技能包
│   │       └── data-perception-core/
│   ├── anomaly-detection-agent/   # 异常检测
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   └── skills/
│   │       └── anomaly-detection-core/
│   ├── rule-reasoning-agent/      # 规则推理
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   └── skills/
│   │       └── rule-reasoning-core/
│   └── disposition-execution-agent/ # 研判预警与处置
│       ├── SOUL.md
│       ├── AGENTS.md
│       ├── MEMORY.md
│       └── skills/
│           └── disposition-execution-core/
│
├── shared/                        # 全局共享资源（三库一体）
│   ├── operators/                 # 算子库
│   │   ├── statistical/          # 统计算子
│   │   ├── machine_learning/     # 机器学习算子
│   │   ├── deep_learning/        # 深度学习算子
│   │   └── specialized/          # 专用检测算子
│   ├── knowledge/                 # 知识库
│   │   ├── regulations/          # 法规库
│   │   ├── process_knowledge/    # 工艺知识库
│   │   ├── violation_patterns/   # 违规模式库
│   │   └── expert_experience/    # 专家经验库
│   ├── data/                      # 数据库
│   │   ├── real-time/            # 实时数据
│   │   ├── historical/           # 历史数据
│   │   └── static/               # 静态数据
│   ├── cache/                     # 缓存层
│   ├── configs/                   # 配置层
│   └── outputs/                   # 输出层
│
├── interfaces/                   # 标准化接口定义
│   ├── subagent_protocol.md      # 子智能体通信协议
│   ├── input_schema.json         # 输入格式
│   ├── output_schema.json        # 输出格式
│   ├── error_codes.md            # 错误码定义
│   └── health_check_api.md       # 健康检查接口
│
├── scripts/                      # 全局工具脚本
│   ├── start_backend.bat         # 后端启动（Windows）
│   ├── start_backend.sh          # 后端启动（Linux/Mac）
│   ├── test_*.py                 # 测试脚本
│   │   ├── test_identity_content.py      # 主智能体身份文件测试
│   │   ├── test_master_conversation.py   # 主智能体对话测试
│   │   ├── test_subagent_identity_content.py  # 子智能体身份文件测试
│   │   └── test_master_calls_subagent.py  # 主智能体调用子智能体测试
│   ├── verify_*.py                # 验证脚本
│   └── cleanup_subagents.py       # 子智能体目录清理
│
├── tests/                        # 测试目录
│   ├── unit/                      # 单元测试
│   ├── integration/               # 集成测试
│   ├── reports/                  # 测试报告
│   └── test_*.py                 # 测试脚本
│
├── docs/                         # 项目文档
│   ├── architecture/             # 架构文档
│   └── superpowers-guide.md      # Superpowers 指南
│
├── grafana/                      # Grafana 配置
├── prometheus/                   # Prometheus 配置
├── stream/                       # 数据流发送器
├── sessions/                     # 会话目录
├── memory/                       # 主智能体会话日志
├── logs/                         # 日志系统
│
├── .env                          # 环境变量（不提交）
├── .env.example                  # 环境变量模板
├── requirements.txt              # Python 依赖
├── pyproject.toml                # 项目配置
├── uv.lock                       # uv 锁定文件
├── CHANGELOG.md                  # 变更日志
├── CLAUDE.md                     # 项目技术文档
├── MEMORY.md                     # 项目记忆索引
└── README.md                     # 本文件
```

## 快速开始

### 环境配置

```bash
# 确保使用 Python 3.12
python --version  # 3.12.12

# 使用 uv 创建虚拟环境（如果尚未创建）
uv venv ecological_env
source ecological_env/Scripts/activate  # Windows
# 或 source ecological_env/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 配置 LLM API

编辑 `.env` 文件，配置 LLM 服务：

```bash
# LLM API 配置（当前实际使用：本地部署的 ctgu-vlm）
LLM_BASE_URL=http://172.16.12.41:30000/v1
LLM_API_KEY=sk-xxx  # 由部署方提供
LLM_MODEL=ctgu-vlm
# 备用：美团 LongCat-2.0（OpenAI 兼容 API，已在 .env 注释保留）
```

### 启动服务（按顺序；InfluxDB 是数据层，必须先起）

**⓪ InfluxDB（数据层，端口 8086）：**

```bash
# 首次或更新报表：把真实 xls 放到 shared/data/real-time/，再导入到 InfluxDB（幂等覆盖）
ecological_env/Scripts/python.exe shared/data/import_to_influxdb.py
# 启动 InfluxDB（Windows 示例：D:\influxdb2-2.7.12-windows\influxd.exe）
<influxdb 安装目录>/influxd
```

**① 智能体服务（Hermes 主智能体，端口 8642）：**

```bash
python scripts/start_agent.py
```

**② 后端（FastAPI，端口 8000）：**

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**③ 前端（Vite 开发服务器，端口 5173）：**

```bash
cd frontend && npm install && npm run dev
```

访问：
- **前端界面**：`http://localhost:5173`（默认进 AI 助手页 /chat）
- 后端 API 文档：`http://localhost:8000/docs`
- 智能体服务健康检查：`http://localhost:8642/health`

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/hermes/system` | GET | Hermes 系统信息 |
| `/api/hermes/skills` | GET | 加载的技能列表 |
| `/api/query` | POST | 自然语言查询（阻塞，等完整结果） |
| `/api/query/stream` | POST | **流式查询**（SSE：实时返回子智能体调用进度 + 最终回答逐字） |
| `/api/logs` | GET | 日志查询 |
| `/metrics` | GET | Prometheus 指标 |

### 示例查询

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "检测最近一周数据异常情况"}'
```

## 子智能体

### 1. 多维数据感知子智能体
- 多源数据获取（CSV、API、数据库）
- 时序对齐处理
- 数据质量控制
- 字段标准化

### 2. 异常检测子智能体
- 5类异常识别：平稳、突变、趋势、周期、高频波动
- 4类违规检测：插瓶干扰、人工拟合、稀释排放、恶意逃避
- 置信度评估

### 3. 规则推理子智能体
- 法规规则匹配
- 工艺机理校验
- 专家推理

### 4. 研判预警与处置执行子智能体
- 融合共识算法
- 三级预警分类
- 工单生成

## 违规检测类型

| 类型 | 描述 | 检测方法 |
|-----|------|----------|
| 插瓶干扰 | 恒定或接近恒定值 | 方差检测 |
| 人工拟合 | 曲线过于平滑 | 波动性分析 |
| 稀释排放 | 流量突增且污染物成比例下降 | 相关性分析 |
| 恶意逃避 | 规避检测的模式 | 模式识别 |

## 监控

### Prometheus 指标

```bash
# 访问 Prometheus 指标
curl http://localhost:8000/metrics
```

### Grafana 仪表板

导入 `grafana/dashboards/` 中的仪表板配置。

## 文档

- [变更日志](CHANGELOG.md)
- [项目技术文档](CLAUDE.md)
- [Hermes 框架详解](docs/Hermes-Agent框架与智能体架构详解.md)

## 测试

### 演示前冒烟测试（一键跑通全链路，推荐演示前必跑）

```bash
ecological_env/Scripts/python.exe scripts/smoke_test.py
```

发标准查询，自动断言：服务健康 + 主智能体调用了子智能体 + 审计按 `turn_id` 落库且一致 + `output_result` 含结构化 evidence（异常/违规/预警/数据条数）。**演示前跑一遍，确认今天改的东西没回归。**

### 单元/集成测试

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

### 测试覆盖

| 测试项目 | 覆盖内容 | 状态 |
|---------|---------|------|
| 身份文件内容 | SOUL.md, AGENTS.md, MEMORY.md | ✅ 56/56 通过 |
| 主智能体对话 | LLM 集成、工具加载、问题回答 | ✅ 测试通过 |
| 子智能体调用 | 初始化、通信、结果汇总 | ✅ 3/3 通过 |

## 项目完成度

| 模块 | 状态 |
|------|------|
| Hermes 框架集成 | ✅ 100% |
| 主智能体 | ✅ 100% |
| 4 个子智能体 | ✅ 100% |
| 子智能体调用 | ✅ 100% |
| FastAPI 后端 | ✅ 100% |
| shared/ 资源库 | ✅ 100% |
| 数据流发送器 | ✅ 100% |
| 监控配置 | ✅ 100% |
| 前端界面 | ✅ 已开发（Phase 0-3A：AI 助手页含**流式问答 + 决策路径面板**、监测大屏、日志、链路追踪等；Phase B 部分占位页待填充） |
| 智能体 pipeline | ✅ 跑通（LLM 驱动主智能体 + 4 子智能体，端到端流式 + 进度反馈） |

**整体完成度：~95%**（智能体 + 三层链路 + 流式均已跑通；前端部分占位页待填充）

---

**版本**：v2.4.0
**最后更新**：2026-07-28
**Python**：3.12.12
**LLM**：ctgu-vlm（本地部署，OpenAI 兼容 API）
