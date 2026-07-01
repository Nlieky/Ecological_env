# 废水虚假排放智能监测系统

> 一种多智能体协同的废水虚假排放智能监测方法及系统

##  📖 专利概述

本系统基于发明专利《一种多智能体协同的废水虚假排放智能监测方法及系统》实现，采用**六层标准化架构**构建覆盖多源数据接入、标准化治理、多维特征挖掘、时序异常识别、工艺机理校验、法规规则推理、专家经验复审的全链条、一体化废水虚假排放智能监测体系。

### 核心能力

- 🎯 **精准识别**：插瓶干扰、暗管偷排、清水稀释排放、数据篡改定值、虚假停产、工况造假等违规行为
- 🤖 **智能协同**：主智能体全局调度 + 任务编排层统一约束 + 四大子智能体专业执行
- 💬 **自然交互**：支持自然语言发起复杂分析查询，系统自动完成任务解析、算子调度、指标关系分析
- 🔄 **闭环优化**：基于监管反馈持续更新知识库、算法策略与判定规则

## 技术栈

| 组件 | 技术 |
|------|------|
| **底层框架** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) - LLM驱动智能体框架 |
| **后端** | FastAPI + Uvicorn |
| **Python** | 3.12.12 (uv 虚拟环境 `ecological_env`) |
| **LLM** | ctgu-vlm (OpenAI 兼容 API) |
| **监控** | Prometheus + Grafana |

##  架构

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 人机交互层                                                    │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  API接口     │  │  Grafana看板 │             │
│  │  实时数据流   │  │  可视化监控  │            │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ② 监管平台数据采集层                                             │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  数据采集适配 │  │  数据传输     │  ← CSV/模拟流/实时API        │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ③ 主智能体层（全局决策中枢）                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ NLU意图  │ │ 任务分解 │ │结果复用  │ │ LLM调度  │              │
│  │  识别    │ │   DAG    │ │三重判决  │ │          │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ④ 任务编排层                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │任务结构化 │ │任务流生成 │ │ 资源匹配  │ │ 执行控制 │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑤ 子智能体层（能力执行单元）                                     │
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
│  ⑥ 数据与支撑层                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │时序数据库│ │知识库    │ │模型算子库│ │迭代更新  │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

##  目录结构

```
Ecological_env/                    # 项目主目录
│
├── backend/                       # FastAPI 后端
│   ├── main.py                    # 主应用（端口 8000）
│   ├── api/
│   │   ├── client.py              # Hermes API 客户端
│   │   └── routes/                # API 路由
│   │       ├── health.py          # 健康检查
│   │       ├── hermes.py          # Hermes 系统信息
│   │       └── query.py           # 查询接口
│   ├── core/
│   │   └── config.py              # 配置加载
│   └── metrics/
│       └── definitions.py         # Prometheus 指标
│
├── simple_http_wrapper.py         # 简单 HTTP 包装器（端口 5000）
│
├── workspace/                     # 主智能体工作区
│   ├── SOUL.md                    # 主智能体个性和决策树
│   ├── AGENTS.md                  # 工作区规范
│   ├── MEMORY.md                  # 全局长期记忆
│   └── skills/
│       └── orchestrator-core/     # 编排器核心技能
│           ├── scripts/
│           │   ├── dynamic_orchestrator.py
│           │   ├── call_subagent.py
│           │   ├── subagent_tools.py
│           │   ├── create_session.py
│           │   └── cleanup_sessions.py
│
├── subagents/                     # 四个子智能体
│   ├── multi-dimensional-data-perception-agent/  # 多维数据感知
│   ├── anomaly-detection-agent/    # 异常检测
│   ├── rule-reasoning-agent/       # 规则推理
│   └── disposition-execution-agent/ # 研判预警与处置
│
├── shared/                        # 全局共享资源
│   ├── configs/                   # 配置
│   │   ├── llm_client.py          # LLM 客户端
│   │   └── llm_config.yaml        # LLM 配置
│   ├── knowledge/                 # 知识库
│   │   ├── regulations/            # 法规库
│   │   ├── process_knowledge/     # 工艺知识库
│   │   ├── violation_patterns/    # 违规模式库
│   │   └── expert_experience/      # 专家经验库
│   ├── operators/                 # 算子库
│   │   ├── statistical/           # 统计算子
│   │   ├── ml/                    # 机器学习算子
│   │   └── deep_learning/         # 深度学习算子
│   └── data/                      # 数据
│
├── stream/                        # 数据流发送器
│   └── dual_data_stream.py        # 双数据流发送器
│
├── grafana/                       # Grafana 配置
│   └── dashboards/
│
├── prometheus/                    # Prometheus 配置
│
├── data/                          # 原始数据
│   ├── pollution_water_in.csv     # 进水数据
│   └── pollution_water_out.csv    # 出水数据
│
├── tests/                         # 测试
│   ├── integration/               # 集成测试
│   └── unit/                      # 单元测试
│
├── scripts/                       # 工具脚本
│   ├── start_backend.bat          # Windows 启动脚本
│   ├── start_backend.sh           # Linux 启动脚本
│   └── verify_all_subagents.py    # 验证脚本
│
├── .env                           # 环境变量配置
├── .hermes/                       # Hermes 框架配置
│   └── config.yaml
├── requirements.txt                # Python 依赖
├── CLAUDE.md                      # 项目技术文档
├── CHANGELOG.md                   # 变更日志
└── README.md                      # 项目说明
```

##  快速开始

### 环境配置

```bash
# 确保使用 Python 3.12
python --version  # 3.12.12

# 创建虚拟环境（如果尚未创建）
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
LLM_BASE_URL=http://172.16.12.41:30000/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=ctgu-vlm

# FastAPI 配置
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8001
```

### 启动服务

**方式 1: FastAPI Backend（推荐）**

```bash
# Windows
scripts\start_backend.bat

# Linux/Mac
bash scripts/start_backend.sh

# 或手动启动（确保使用虚拟环境的 Python 3.12.12）
ecological_env\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

访问 API 文档：`http://localhost:8001/docs`

**方式 2: Simple HTTP Wrapper**

```bash
python simple_http_wrapper.py
```

访问：`http://localhost:5000`

### 可用的 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/hermes/system` | GET | Hermes 系统信息 |
| `/api/hermes/skills` | GET | 加载的技能列表 |
| `/api/query` | POST | 自然语言查询 |
| `/metrics` | GET | Prometheus 指标 |

### 示例查询

```bash
curl -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "检测最近一周数据异常情况"}'
```

##  子智能体

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

##  监控

### Prometheus 指标

```bash
# 访问 Prometheus 指标
curl http://localhost:8001/metrics
```

### Grafana 仪表板

```bash
# 启动 Grafana（需单独安装）
# 导入 grafana/dashboards/ 中的仪表板配置
```

##  日志系统

系统会自动记录以下类型的日志：

- **API 调用日志**: 记录所有 API 请求
- **主智能体决策日志**: 记录意图识别、子智能体调用链
- **子智能体执行日志**: 记录子智能体的输入输出
- **算子调用日志**: 记录算子调用的参数和结果
- **LLM 调用日志**: 记录 LLM 调用的 Token 消耗
- **系统错误日志**: 记录系统异常

### 查询日志

```bash
# API 接口
curl "http://localhost:8001/api/logs?log_type=api&page=1&page_size=50"
```

### 会话证据链

通过 session_id 可以查询完整会话的证据链：

```bash
curl "http://localhost:8001/api/logs/trace/{session_id}"
```

### 数据库维护

```bash
# 查看日志统计
ecological_env\Scripts\python.exe -m backend.database.maintain_db stats

# 清理旧日志（90 天前）
ecological_env\Scripts\python.exe -m backend.database.maintain_db clean --days 90
```

##  专利核心特性

### 1. 分析结果复用机制
- 数据匹配判决（Jaccard 相似系数 M ≥ 0.7）
- 新鲜度判决（Δt ≤ W_task）
- 语义匹配判决（编辑距离 S ≥ 0.8）

### 2. 双驱动运行模式
- **主动监测模式**：按周期自动识别违规
- **查询响应模式**：响应灵活查询需求

### 3. 违规判定双层逻辑
**数据层**：平稳、突变、趋势、周期、高频波动
**业务层**：插瓶干扰、人工拟合、稀释排放、恶意逃避

### 4. 工艺机理校验
- pH-COD 协同规则
- 质量平衡规则
- 氨氮-总氮转化规则

##  相关文档

- [变更日志](CHANGELOG.md) - 版本更新记录
- [Claude 配置](CLAUDE.md) - 项目技术文档
- [专利全文](docs/专利.txt) - 发明内容

##  项目完成度

| 模块 | 状态 |
|------|------|
| 主智能体 | ✅ 100% |
| 四个子智能体 | ✅ 95% |
| FastAPI 后端 | ✅ 100% |
| shared/ 资源库 | ✅ 100% |
| 数据流发送器 | ✅ 100% |
| 测试套件 | ✅ 80% |
| **前端界面** | ⏳ **未实现** |

**整体完成度：~70%**（前端界面尚未开发）

---

**版本**：v2.1.0
**最后更新**：2026-06-30
**Python**：3.12.12
**LLM**：ctgu-vlm (OpenAI 兼容 API)
