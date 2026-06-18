# 废水虚假排放智能监测系统

> 一种多智能体协同的废水虚假排放智能监测方法及系统

## 📖 专利概述

本系统基于发明专利《一种多智能体协同的废水虚假排放智能监测方法及系统》实现，采用**六层标准化架构**构建覆盖多源数据接入、标准化治理、多维特征挖掘、时序异常识别、工艺机理校验、法规规则推理、专家经验复审、自然语言交互应答的全链条、一体化废水虚假排放智能监测体系。

### 核心能力

- 🎯 **精准识别**：插瓶干扰、暗管偷排、清水稀释排放、数据篡改定值、虚假停产、工况造假等违规行为
- 🤖 **智能协同**：主智能体全局调度 + 任务编排层统一约束 + 四大子智能体专业执行
- 💬 **自然交互**：支持自然语言发起复杂分析查询，系统自动完成任务解析、算子调度、指标关系分析
- 📊 **可视化分析**：Web界面展示时序图表、异常点标注、Grafana监控仪表板
- 🔄 **闭环优化**：基于监管反馈持续更新知识库、算法策略与判定规则

## 🌟 最新功能（v2.2.0）

### Web智能查询界面 ⭐

**自然语言查询**
- 支持中英文自然语言输入
- 自动解析查询意图和时间范围
- LLM驱动的主智能体和子智能体协同分析
- 自动生成自然语言监测报告

**可视化图表**
- 多指标时序图表（pH、COD、TN、NH3-N、TP）
- 异常点自动红色标注
- 交互式tooltip显示异常详情
- 图例点击切换指标显示

**Grafana集成**
- 实时监控面板嵌入Grafana仪表板
- 一键跳转到完整仪表板
- 支持进水/出水指标实时对比

**快速开始**
```bash
# 启动查询接口
cd middleware
python query_interface.py

# 访问Web界面
http://localhost:8080

# 示例查询
- "检测最近一周数据异常情况"
- "analyze pH COD anomalies in past 24 hours"
```

## 技术栈

**底层框架**: [Hermes Agent](https://github.com/NousResearch/hermes-agent) - LLM驱动智能体框架

## 📁 项目目录结构

```
Ecological_env/                    # 📁 项目主目录
│
├── middleware/                     # 📁【Flask中间件 & Web界面】⭐
│   ├── query_interface.py          # 🌐 Web查询接口（LLM驱动）⭐
│   ├── app_orchestrator.py         # 🚀 实时监控服务
│   ├── historical_data_fetcher.py # 📊 历史数据获取器 ⭐
│   ├── static/                     # 📁 Web前端资源 ⭐
│   │   ├── index.html              # 📄 主页面（查询、监控、分析）
│   │   ├── css/                     # 📁 样式文件
│   │   ├── js/                      # 📁 JavaScript模块
│   │   │   ├── app.js              # 📄 应用逻辑
│   │   │   ├── charts.js           # 📄 Chart.js图表 ⭐
│   │   │   └── monitoring.js       # 📄 监控面板
│   │   └── monitoring/             # 📁 监控相关资源
│   ├── .env                        # 🔑 LLM API配置
│   └── .env.example                # 📄 环境变量模板
│
├── workspace/                     # 📁【主智能体配置区】
│   ├── AGENTS.md                  # 📄 工作区规范
│   ├── SOUL.md                    # 📄 主智能体个性和语气
│   ├── MEMORY.md                  # 📄 主智能体全局长期记忆
│   ├── IDENTITY.md                # 📄 主智能体身份卡片
│   ├── USER.md                    # 📄 用户信息
│   ├── TOOLS.md                   # 📄 工具配置笔记
│   └── skills/                     # 📁【主智能体核心技能包】
│       └── orchestrator-core/      # 📦 编排器核心 ⭐
│           ├── SKILL.md
│           └── scripts/            # 📁 任务编排脚本
│               ├── dynamic_orchestrator.py  # 🔄 动态编排器
│               ├── execution_control.py      # ⚙️ 执行控制（LLM驱动）
│               └── execution_engine.py      # 🚀 执行引擎
│
├── subagents/                     # 📁【子智能体独立工作区】
│   ├── multi-dimensional-data-perception-agent/  # 📦 多维数据感知 📊
│   │   ├── AGENTS.md               # 📄 专属任务指令
│   │   ├── SOUL.md                 # 📄 角色个性
│   │   ├── MEMORY.md               # 📄 专业记忆
│   │   └── skills/
│   │       └── data-perception-core/scripts/
│   │           ├── data_acquisition.py    # 多源数据获取
│   │           ├── data_cleaning.py        # 数据清洗
│   │           ├── time_alignment.py       # 时序对齐
│   │           ├── standardization.py      # 标准化
│   │           └── data_decomposition.py    # 数据分解
│   │
│   ├── anomaly-detection-agent/    # 📦 异常检测 🔍
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   ├── MEMORY.md
│   │   └── skills/
│   │       └── anomaly-detection-core/scripts/
│   │           ├── operator_adapter.py     # 算子适配
│   │           ├── anomaly_scorer.py       # 异常评分
│   │           ├── pattern_recognizer.py     # 5类异常识别 ⭐
│   │           ├── violation_detector.py    # 4类违规检测 ⭐
│   │           └── confidence_evaluator.py  # 置信度评估
│   │
│   ├── rule-reasoning-agent/       # 📦 规则推理 ⚖️
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   ├── MEMORY.md
│   │   └── skills/
│   │       └── rule-reasoning-core/scripts/
│   │           ├── regulation_matcher.py    # 法规匹配
│   │           ├── process_validator.py     # 工艺校验
│   │           └── expert_reasoner.py       # 专家推理
│   │
│   └── disposition-execution-agent/  # 📦 研判预警与处置 🚨
│       ├── AGENTS.md
│       ├── SOUL.md
│       ├── MEMORY.md
│       └── skills/
│           └── disposition-execution-core/scripts/
│               ├── alert_classifier.py        # 告警分类
│               ├── consensus_engine.py         # 融合共识 ⭐
│               └── work_order_generator.py    # 工单生成
│
├── shared/                         # 📁【全局共享资源】
│   ├── configs/                    # ⚙️ 配置层
│   │   ├── llm_config.yaml         # LLM配置
│   │   ├── llm_client.py           # LLM客户端
│   │   ├── agent_registry.yaml     # 智能体注册表
│   │   ├── consensus_config.yaml   # 共识引擎配置 ⭐
│   │   └── rule_config.yaml        # 违规检测配置 ⭐
│   ├── knowledge/                  # 📚 知识库层
│   │   ├── regulations/            # 法规库
│   │   ├── process_knowledge/      # 工艺知识库
│   │   ├── violation_patterns/     # 违规模式库
│   │   └── expert_experience/      # 专家经验库
│   ├── operators/                  # 🔧 算子库
│   │   ├── statistical/            # 统计算子
│   │   ├── ml/                     # 机器学习算子
│   │   └── deep_learning/          # 深度学习算子
│   └── data/                       # 📊 数据层
│       └── real-time/              # 实时数据
│
├── stream/                         # 📁【数据流发送器】
│   └── dual_data_stream.py         # 🌊 双数据流发送器
│
├── grafana/                        # 📁【Grafana配置】
│   ├── dashboards/
│   │   └── stream_01.json          # 📊 监控仪表板 ⭐
│   └── prometheus.yml              # ⚙️ Prometheus配置
│
├── data/                           # 📁【原始数据】
│   ├── pollution_water_in.csv      # 进水数据
│   └── pollution_water_out.csv     # 出水数据
│
├── tests/                          # 📁【测试目录】
│   ├── test_four_layer_architecture.py  # 架构测试
│   ├── test_master_agent.py             # 主智能体测试
│   ├── integration/                     # 集成测试
│   ├── realtime/                       # 实时测试
│   └── unit/                           # 单元测试
│
├── docs/                           # 📁【项目文档】
│   ├── user-guide/                 # 📖 用户指南
│   ├── 专利.txt                    # 📄 专利全文
│   └── 任务目标.md                 # 📋 项目目标
│
├── logs/                           # 📁【日志系统】
│   └── middleware.log              # 📝 中间件日志
│
├── CHANGELOG.md                    # 📝 变更日志
├── CLAUDE.md                       # 📄 Claude配置文档
├── README.md                       # 📖 项目说明
└── requirements.txt                # 📦 Python依赖
```

## 🏗️ 系统架构

### 专利六层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 人机交互层                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Web查询界面 │  │  API接口     │  │  Grafana看板 │          │
│  │  自然语言交互 │  │  实时数据流   │  │  可视化监控  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ② 监管平台数据采集层                                           │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  数据采集适配 │  │  数据传输    │  ← CSV/模拟流/实时API        │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ③ 主智能体层（全局决策中枢）                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ NLU意图  │ │ 任务分解 │ │结果复用  │ │ LLM调度  │          │
│  │  识别    │ │   DAG    │ │三重判决⭐│ │          │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ④ 任务编排层                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │任务结构化│ │任务流生成│ │ 资源匹配 │ │ 执行控制 │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑤ 子智能体层（能力执行单元）                                    │
│  ┌──────────────────┐ ┌──────────────────┐                      │
│  │多维数据感知子智能体│ │异常检测子智能体  │                      │
│  │多源数据/时序对齐 │ │5类异常/4类违规⭐ │                      │
│  ├──────────────────┤ ├──────────────────┤                      │
│  │规则推理子智能体  │ │研判预警与处置执行  │                      │
│  │工艺机理/法规匹配│ │预警生成/处置协调  │                      │
│  └──────────────────┘ └──────────────────┘                      │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑥ 数据与支撑层                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │时序数据库│ │知识库    │ │模型算子库│ │迭代更新  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### Web智能查询（推荐）

```bash
# 1. 配置LLM API
cd middleware
cp .env.example .env
# 编辑 .env 文件，添加 ANTHROPIC_API_KEY

# 2. 启动查询接口
python query_interface.py

# 3. 访问Web界面
http://localhost:8080

# 4. 输入自然语言查询
- "检测最近一周数据异常情况"
- "analyze pH COD anomalies in past 24 hours"
- "查看昨天总氮和总磷的趋势"
```

### 实时监控模式

```bash
# Terminal 1: 启动监控服务
cd middleware
python app_orchestrator.py

# Terminal 2: 启动数据流
python stream/dual_data_stream.py

# Terminal 3: 访问监控面板
http://localhost:8080
# 点击"实时监控"标签查看Grafana仪表板
```

### 系统组件

| 组件 | 文件 | 端口 | 说明 |
|------|------|------|------|
| Web查询接口 | middleware/query_interface.py | 5001 | 自然语言查询服务 |
| 监控服务 | middleware/app_orchestrator.py | 5000 | 实时监控服务 |
| 数据流发送器 | stream/dual_data_stream.py | - | 发送进水+出水数据 |
| Prometheus | grafana/prometheus.yml | 9090 | 指标采集 |
| Grafana | grafana/dashboards/ | 3000 | 数据可视化 |

## 🧠 LLM驱动策略

### 双层LLM驱动架构

**主智能体层（第一层）**
- 意图识别：理解用户查询的真实意图
- 任务分解：将复杂查询分解为可执行的子任务序列
- 调度决策：决定哪些子智能体参与及执行顺序
- 结果聚合：汇总分析结果，生成综合响应

**子智能体层（第二层）**
- 脚本选择：根据任务选择合适的处理脚本
- 结果分析：解释脚本执行结果并生成结构化报告

### LLM模型选择

| 模型 | 用途 | 速度 |
|------|------|------|
| **Haiku** | 意图解析、数据处理 | 快速 |
| **Sonnet** | 推理、判定、报告生成 | 标准 |
| **Opus** | 异常检测、复杂计算 | 深度分析 |

### Web查询的LLM调用流程

```
用户输入："检测最近一周数据异常情况"
    ↓
【Haiku】解析意图：提取时间范围、分析类型、监测指标
    ↓
获取历史数据（288条进水+出水数据）
    ↓
【Sonnet】协调子智能体：
  1. multi-dimensional-data-perception-agent → 数据预处理
  2. anomaly-detection-agent → 异常检测
    ↓
【Sonnet】生成自然语言报告
    ↓
返回：时序数据 + 异常详情 + 分析报告
```

## 📊 Web界面功能

### 查询面板
- 📝 自然语言输入框
- 📊 实时状态显示和进度提示
- 📋 结果摘要（数据概况、异常情况）
- 📈 时序图表可视化

### 监控面板
- 📺 Grafana仪表板嵌入
- 🔄 实时数据展示
- 📊 进水/出水指标对比
- 🔗 备选跳转按钮

### 分析报告面板
- 📉 多指标时序图表（Chart.js）
- 📍 异常点红色标注
- 💡 交互式tooltip详情
- 🎨 图例点击切换显示

## 📊 Prometheus指标

### 进水指标
```
wastewater_influent_ph              # 进水pH值
wastewater_influent_cod             # 进水化学需氧量(mg/L)
wastewater_influent_tn              # 进水总氮(mg/L)
wastewater_influent_an              # 进水氨氮(mg/L)
wastewater_influent_tp              # 进水总磷(mg/L)
wastewater_influent_flow_rate       # 进水流量(升/秒)
```

### 出水指标
```
wastewater_effluent_ph              # 出水pH值
wastewater_effluent_cod             # 出水化学需氧量(mg/L)
wastewater_effluent_tn              # 出水总氮(mg/L)
wastewater_effluent_an              # 出水氨氮(mg/L)
wastewater_effluent_tp              # 出水总磷(mg/L)
wastewater_effluent_flow_rate       # 出水流量(升/秒)
```

### 计数器
```
wastewater_data_processed_total     # 数据处理总数
wastewater_anomaly_detected_total   # 异常检测总数
```

## 🎯 专利核心特性

### 1. 分析结果复用机制 ⭐
- 数据匹配判决（Jaccard相似系数 M ≥ 0.7）
- 新鲜度判决（Δt ≤ W_task）
- 语义匹配判决（编辑距离 S ≥ 0.8）

### 2. 双驱动运行模式
- **主动监测模式**：按周期自动识别违规
- **查询响应模式**：响应灵活查询需求 ⭐

### 3. 违规判定双层逻辑
**数据层**：平稳、突变、趋势、周期、高频波动
**业务层**：插瓶干扰、人工拟合、稀释排放、恶意逃避

### 4. 工艺机理校验
- pH-COD协同规则
- 质量平衡规则
- 氨氮-总氮转化规则

## 📖 相关文档

- [变更日志](CHANGELOG.md) - 版本更新记录
- [Claude配置](CLAUDE.md) - 项目技术文档
- [用户指南](docs/user-guide/) - 详细使用说明
- [专利全文](docs/专利.txt) - 发明内容

## 🎯 专利实现完成度

### 已实现功能（95%）

#### Web智能查询系统 ⭐（v2.2.0新增）
- ✅ 自然语言查询接口
- ✅ LLM驱动的意图解析和任务协调
- ✅ 历史数据获取器
- ✅ 多指标时序图表可视化
- ✅ 异常点自动标注
- ✅ Grafana仪表板集成

#### 主智能体层
- ✅ 双层LLM驱动协调
- ✅ 结果复用三重判决

#### 异常检测子智能体
- ✅ 5类异常特征检测
- ✅ 4类违规模式检测

#### 规则推理子智能体
- ✅ 工艺机理校验
- ✅ 法规规则匹配

### 待实现功能（5%）
- ⏳ 专家经验库扩充
- ⏳ 迭代更新接口

---

**版本**：v2.2.0（Web智能查询版）
**最后更新**：2026-06-05
**状态**：✅ 核心专利功能已实现 + ✅ Web智能查询系统
**项目完成度**：95%
