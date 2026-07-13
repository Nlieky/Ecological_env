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
| **LLM** | LongCat-2.0 (美团，OpenAI 兼容 API) |
| **监控** | Prometheus + Grafana |

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 人机交互层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  FastAPI    │  │  Grafana看板 │             │
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
├── workspace/                     # Hermes 主智能体工作区
│   ├── SOUL.md                    # 主智能体身份和个性
│   ├── AGENTS.md                  # 工作区规范
│   ├── MEMORY.md                  # 全局长期记忆
│   ├── USER.md                    # 用户信息
│   ├── IDENTITY.md                # 身份卡片
│   ├── HEARTBEAT.md               # 周期性任务
│   ├── TOOLS.md                   # 工具配置
│   └── skills/                    # 主智能体技能包
│       └── orchestrator-core/     # 编排器核心技能
│           ├── SKILL.md
│           ├── scripts/           # 实现脚本
│           ├── references/        # 参考文档
│           └── assets/            # 资源文件
│
├── subagents/                     # 4 个子智能体
│   ├── multi-dimensional-data-perception-agent/  # 多维数据感知
│   │   ├── SOUL.md               # 子智能体身份
│   │   ├── AGENTS.md             # 子智能体规范
│   │   ├── MEMORY.md             # 子智能体记忆
│   │   ├── skills/               # 子智能体技能
│   │   └── run_agent_wrapper.py  # 运行包装器
│   ├── anomaly-detection-agent/   # 异常检测
│   ├── rule-reasoning-agent/      # 规则推理
│   └── disposition-execution-agent/ # 研判预警与处置
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
│   ├── start_hermes_server.bat   # Hermes 服务器启动（Windows）
│   ├── start_hermes_server.sh    # Hermes 服务器启动（Linux/Mac）
│   ├── start_backend.bat         # 后端启动（Windows）
│   ├── start_backend.sh          # 后端启动（Linux/Mac）
│   ├── spawn_subagent.py         # 启动子智能体
│   ├── register_subagent.py      # 注册子智能体
│   ├── sync_memory.py            # 同步记忆
│   ├── health_monitor.py         # 健康监控
│   ├── cache_manager.py          # 缓存管理
│   ├── data_validator.py         # 数据验证
│   └── backup_restore.sh         # 备份恢复
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
# LLM API 配置
LLM_BASE_URL=https://api.longcat.chat/openai/v1
LLM_API_KEY=ak_xxx  # 从美团获取
LLM_MODEL=LongCat-2.0

# FastAPI 配置
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
```

### 启动服务

**启动 Hermes API Server：**

```bash
# Windows
scripts\start_hermes_server.bat

# Linux/Mac
bash scripts/start_hermes_server.sh
```

**启动后端：**

```bash
# Windows
scripts\start_backend.bat

# Linux/Mac
bash scripts/start_backend.sh
```

**启动前端：**

```bash
cd frontend
npm install
npm run dev
```

访问：
- 后端 API：`http://localhost:8000/docs`
- 前端界面：`http://localhost:3000`
- Hermes API：`http://localhost:8642`

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/hermes/system` | GET | Hermes 系统信息 |
| `/api/hermes/skills` | GET | 加载的技能列表 |
| `/api/query` | POST | 自然语言查询 |
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

## 项目完成度

| 模块 | 状态 |
|------|------|
| Hermes 框架集成 | ✅ 100% |
| 主智能体 | ✅ 100% |
| 4 个子智能体 | ✅ 95% |
| FastAPI 后端 | ✅ 100% |
| shared/ 资源库 | ✅ 100% |
| 数据流发送器 | ✅ 100% |
| 监控配置 | ✅ 100% |
| 前端界面 | ⏳ 部分实现 |

**整体完成度：~80%**（前端界面继续开发中）

---

**版本**：v2.1.1  
**最后更新**：2026-07-08  
**Python**：3.12.12  
**LLM**：LongCat-2.0 (美团，OpenAI 兼容 API)
