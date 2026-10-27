# 废水虚假排放智能监测系统

> LLM 多智能体协同的废水虚假排放智能监测平台

## 📖 系统概述

本系统采用 **Hermes Agent 框架**构建覆盖多源数据接入、标准化治理、多维特征挖掘、时序异常识别、工艺机理校验、法规规则推理、专家经验复审的全链条、一体化废水虚假排放智能监测体系。

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
| **LLM** | 通过 `.env` 配置的 OpenAI 兼容 API；地址、密钥和模型由部署环境提供 |
| **前端** | Vue 3 + Element Plus + Pinia + ECharts |
| **业务时序数据** | InfluxDB 2.x；真实历史数据和模拟数据分桶隔离 |
| **系统监控** | Prometheus / Grafana 当前搁置，预留给未来系统运行指标监测 |

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 人机交互层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  FastAPI    │  │  系统页面     │                             │
│  │  API接口     │  │  页面助手     │            │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ② 数据采集层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  报表导入    │  │  数据传输     │  ← 历史报表 / 可选模拟流       │
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

### 当前运行链路

上面是六层概念架构；**实际运行**由前端、FastAPI、Agent 三个应用服务和 InfluxDB 数据服务组成：

```
浏览器(5173) → FastAPI 后端(8000) → Hermes 智能体服务(8642)
      ↓ 页面助手候选操作与上下文                  ↓ 主智能体 + Skills
      └──────── InfluxDB(8086) 业务时序数据查询 ──┘
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
- 废水业务数据当前来自监管平台下载的历史报表；系统尚未接入监管平台实时数据 API。页面会标明来源和数据新鲜度。
- `monitoring-real` 与 `monitoring-simulation` 分别存储真实历史数据和模拟数据，业务查询按来源隔离。
- InfluxDB 是废水业务时序数据源。Prometheus / Grafana 配置仍保留，但当前不作为业务数据源或运行依赖。

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
│   ├── test_*.py                 # 测试辅助脚本
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
├── requirements.txt              # Python 运行与测试依赖
├── pyproject.toml                # 项目配置
├── uv.lock                       # uv 锁定文件
├── CHANGELOG.md                  # 变更日志
├── CLAUDE.md                     # 项目技术文档
├── MEMORY.md                     # 项目记忆索引
└── README.md                     # 本文件
```

## 快速开始

### 环境配置（Windows PowerShell）

```powershell
# Python 3.12 和 Node.js 20+；首次克隆后执行
py -3.12 -m venv ecological_env
.\ecological_env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 配置本机环境。真实密钥只写入 .env，不要提交 .env。
Copy-Item .env.example .env

# 按前端 lockfile 安装依赖
Set-Location frontend
npm ci
Set-Location ..
```

Linux/macOS 请将虚拟环境激活命令替换为 `source ecological_env/bin/activate`；前端也在 `frontend/` 目录执行 `npm ci`。

### 配置 LLM API

编辑 `.env`，填写可访问的 OpenAI 兼容 LLM 地址、API 密钥和模型名，并配置 InfluxDB 地址、组织、token 与 bucket。`.env.example` 只提供字段说明和占位值，不包含可用凭据。

业务数据默认模式为 `BUSINESS_DATA_MODE=historical`，来源时区默认为 `Asia/Shanghai`，陈旧阈值默认为 6 小时。接入监管平台持续 API 后，再按实际接入方式调整模式。

### 启动服务（各服务在独立终端运行）

**⓪ InfluxDB（数据层，端口 8086）：**

```bash
# 先安装并启动 InfluxDB 2.x，创建 .env 中配置的组织、token 和 bucket。
# 如需导入监管平台下载的 Excel 报表，将文件放到 shared/data/real-time/ 后执行：
python shared/data/import_to_influxdb.py
```

不要把监管报表或 `.env` 上传到 GitHub。模拟器是可选工具，需要生成测试数据时再单独启动 `python shared/data/data_simulator.py --tick 10`。

**① 智能体服务（Hermes 主智能体，端口 8642）：**

```bash
python scripts/start_agent.py
```

**② 后端（FastAPI，端口 8000）：**

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**③ 前端（Vite 开发服务器，端口 5173）：**

```powershell
Set-Location frontend
npm run dev
```

访问：
- **前端界面**：`http://localhost:5173/dashboard`
- 后端 API 文档：`http://localhost:8000/docs`
- 智能体服务健康检查：`http://localhost:8642/health`
- InfluxDB 健康检查：`http://localhost:8086/health`

### Docker 部署（可选）

```bash
# 前置：已完成上文的 .env 配置（LLM 三项必填）。
# 如需在容器里导入监管报表，先把 xls 放到 shared/data/real-time/（会在构建时进入镜像）；
# 不放也能起服务，只是 InfluxDB 里没有业务数据（influxdb-init 容器会报"没有 .xls 文件"后退出，属预期）。
docker compose up -d --build
```

访问：前端 `http://localhost:8080`（nginx 托管 + `/api` 反代），后端 `http://localhost:8000/docs`。
InfluxDB 首启自动建 org/bucket（`monitoring-real`）并导入报表；容器内通过服务名互访（LLM 地址仍按 `.env` 填，需容器网络可达）。

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/hermes/system` | GET | Hermes 系统信息 |
| `/api/hermes/skills` | GET | 加载的技能列表 |
| `/api/query` | POST | 自然语言查询（阻塞，等完整结果） |
| `/api/query/stream` | POST | **流式查询**（SSE：实时返回子智能体调用进度 + 最终回答逐字） |
| `/api/logs` | GET | 日志查询 |
| `/metrics` | GET | 遗留 Prometheus 指标端点；废水 gauge 基于历史 CSV 推进，不代表实时业务数据 |

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

## 监控与数据源

废水业务数据通过 InfluxDB 查询。当前项目未启用 Prometheus 和 Grafana；仓库中的相关配置用于未来系统运行指标监测，不用于废水业务数据。

后端仍保留遗留 `/metrics` 端点和历史 CSV 驱动的废水 gauge 更新器；它们不是实时业务证据，也不应用于运行状态判断。Prometheus / Grafana 当前搁置。新环境模板设置 `PROMETHEUS_ENABLED=0`；如本机 `.env` 有旧配置，也请设为 `0`，避免后端启动 Prometheus 子进程。

监管平台下载数据按 `DATA_TIMEZONE` 解释并写入真实数据 bucket。系统呈现来源、最近采样时间和新鲜度；历史数据不会被标记为实时 API 数据。

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
# 后端和系统测试
python -m pytest

# 前端单元测试、类型检查与构建
cd frontend
npm test
npm run type-check
npm run build
```

真实 LLM 集成验证需要先启动 InfluxDB、Agent 和 Backend，并配置有效的 `.env`。普通 `pytest` 和前端单元测试不依赖监管平台实时 API。

## 当前边界

- 管理端、事件中心、监测大屏、指标查询和 AI 助手等页面已纳入系统；具体可用能力以当前实现和测试为准，本文不再标注过时的完成百分比。
- 真实业务数据仍依赖人工下载监管平台报表；实时监管 API 尚未接入。
- 全局助手可理解页面上下文并准备受限操作；事件写入默认关闭，启用前需完成部署侧权限与审核配置。
- Prometheus / Grafana 相关能力暂缓，后续用于系统运行指标监测。

**最后更新**：2026-10-26 · **Python**：3.12+ · **前端**：Node.js 20+，npm lockfile
