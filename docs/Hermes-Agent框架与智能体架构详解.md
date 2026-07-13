# Hermes Agent 框架与智能体架构详解

> **废水虚假排放智能监测系统** - 技术架构文档  
> **版本**: v2.1.0  
> **最后更新**: 2026-07-07

---

## 目录

1. [Hermes Agent 框架概述](#一hermes-agent-框架概述)
2. [核心概念](#二核心概念)
3. [项目技术栈](#三项目技术栈)
4. [智能体架构](#四智能体架构)
5. [Hermes 在项目中的具体实现](#五hermes-在项目中的具体实现)
6. [数据流转流程](#六数据流转流程)
7. [关键特点](#七关键特点)

---

## 一、Hermes Agent 框架概述

**Hermes Agent** 是一个 LLM 驱动的智能体框架，来自 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) 项目。它提供了构建多智能体系统的完整基础设施。

### 核心能力

| 能力 | 说明 |
|------|------|
| **统一的智能体接口** | 提供标准的 `AIAgent` 类用于创建和运行智能体 |
| **身份文件系统** | 通过 SOUL.md、AGENTS.md、MEMORY.md、IDENTITY.md 定义智能体 |
| **技能系统** | 可扩展的技能插件，LLM 根据技能描述决定何时使用 |
| **OpenAI 兼容 API** | 支持自定义 LLM 服务，无需修改代码 |
| **会话管理** | 跨会话记忆和上下文保持 |

---

## 二、核心概念

### 2.1 AIAgent 类

Hermes 的核心是 `AIAgent` 类，它封装了与 LLM 的交互和智能体的所有功能。

```python
from run_agent import AIAgent

agent = AIAgent(
    base_url="https://api.longcat.chat/openai/v1",  # LLM 服务地址
    api_key="ak_xxx",                                # API 密钥
    model="LongCat-2.0",                            # 模型名称
    load_soul_identity=True,                         # 加载 SOUL.md
    skip_context_files=False,                        # 加载上下文文件
    skip_memory=False,                               # 加载 MEMORY.md
    enabled_toolsets=["skills", "terminal"]         # 启用的工具集
)

response = agent.run_conversation([{"role": "user", "content": "你好"}])
```

#### AIAgent 关键参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_url` | LLM API 地址 | - |
| `api_key` | API 密钥 | - |
| `model` | 模型名称 | - |
| `load_soul_identity` | 是否加载 SOUL.md | `True` |
| `skip_context_files` | 是否跳过上下文文件 | `False` |
| `skip_memory` | 是否跳过记忆文件 | `False` |
| `enabled_toolsets` | 启用的工具集 | `["skills"]` |
| `session_id` | 会话 ID | 自动生成 |
| `max_iterations` | 最大迭代次数 | `10` |

### 2.2 身份文件系统

每个智能体通过身份文件定义自己的个性和行为。

| 文件 | 作用 | 在项目中的位置 |
|------|------|----------------|
| **SOUL.md** | 个性、语气、角色定义 | `workspace/SOUL.md`<br>`subagents/*/SOUL.md` |
| **AGENTS.md** | 工作规则、任务指令 | `workspace/AGENTS.md`<br>`subagents/*/AGENTS.md` |
| **MEMORY.md** | 长期记忆 | `workspace/memory/*.md` |
| **IDENTITY.md** | 身份卡 | `workspace/IDENTITY.md` |
| **USER.md** | 用户配置 | `workspace/USER.md` |
| **TOOLS.md** | 工具使用规范 | `workspace/TOOLS.md` |

#### SOUL.md 示例（主智能体）

```markdown
## Your Role as Master Agent

You are the **Master Agent** (主智能体) of the wastewater fraud detection monitoring system.

## 子智能体调用决策树

当用户查询包含以下需求时，按决策树调用子智能体：

用户查询
    ↓
[1] 需要数据吗？
    ├─ 提到"数据"、"指标"、"监测"
    └─ YES → 调用 data-perception
    └─ NO → 跳过
    ↓
[2] 需要异常检测吗？
    ├─ 提到"异常"、"不正常"
    └─ YES → 调用 anomaly-detection
    └─ NO → 跳过
    ↓
[3] 需要违规判定吗？
    └─ YES → 调用 rule-reasoning
    └─ NO → 跳过
```

### 2.3 技能系统

技能是 `.md` 文件，描述特定功能，LLM 根据内容决定何时使用。

```
workspace/skills/
├── orchestrator-core/          # 核心编排技能
│   ├── SKILL.md               # 技能描述
│   └── scripts/
│       ├── call_subagent.py   # 调用子智能体
│       ├── dynamic_orchestrator.py
│       └── subagent_tools.py
└── ...其他技能

subagents/*/skills/
└── **-core/
    ├── SKILL.md               # 子智能体核心技能
    └── scripts/               # 技能脚本
```

#### SKILL.md 示例

```yaml
---
name: anomaly-detection-core
description: 检测时序数据异常和违规模式。触发条件：当用户查询提到"异常"、"不正常"、"突变"、"违规"时调用。
---

## 功能说明
使用多种算子检测时序数据异常，支持统计方法、机器学习和深度学习算法。

## 使用场景
- 异常检测
- 违规模式识别
- 数据质量评估
```

---

## 三、项目技术栈

### 3.1 整体技术栈

| 组件 | 技术 |
|------|------|
| **底层框架** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) |
| **后端** | FastAPI + Uvicorn |
| **Python** | 3.12.12 (uv 虚拟环境 `ecological_env`) |
| **LLM** | LongCat-2.0 (美团，OpenAI 兼容 API) |
| **数据库** | PostgreSQL (业务数据) |
| **监控** | influxdb+Prometheus + Grafana |
| **前端** | Vue.js + Element-UI |
| **部署** | Docker + Kubernetes |

### 3.2 LLM 配置

```bash
# .env 文件配置
LLM_BASE_URL=https://api.longcat.chat/openai/v1
LLM_API_KEY=ak_xxx
LLM_MODEL=LongCat-2.0
```

### 3.3 目录结构

```
Ecological_env/
├── .hermes/                    # Hermes 配置
│   └── config.yaml            # 框架主配置
├── backend/                    # FastAPI 后端
│   ├── main.py                # 应用入口
│   ├── api/
│   │   ├── client.py         # Hermes API 客户端
│   │   └── routes/           # API 路由
│   └── database/             # 数据库配置
├── workspace/                # 主智能体工作区
│   ├── SOUL.md               # 主智能体个性
│   ├── AGENTS.md             # 工作规则
│   ├── MEMORY.md             # 长期记忆
│   └── skills/               # 主智能体技能
│       └── orchestrator-core/
├── subagents/                # 子智能体
│   ├── multi-dimensional-data-perception-agent/
│   ├── anomaly-detection-agent/
│   ├── rule-reasoning-agent/
│   └── disposition-execution-agent/
└── shared/                   # 三库一体
    ├── operators/            # 算子库
    ├── knowledge/            # 知识库
    └── data/                 # 数据库
```

---

## 四、智能体架构

### 4.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                      废水监测系统智能体架构                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FastAPI 后端                                                 │   │
│  │  ├─ /api/query → HermesAPIClient.chat_completion()          │   │
│  │  └─ 代理用户请求到主智能体                                    │   │
│  └────────────────────────────┬───────────────────────────────────┘   │
│                               │                                        │
│                               ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  主智能体 (Master Agent) - workspace/                         │   │
│  │  ├─ SOUL.md: 定义协调规则和子智能体调用决策树                 │   │
│  │  ├─ AGENTS.md: 工作规则                                       │   │
│  │  ├─ orchestrator-core 技能                                    │   │
│  │  │   ├─ create_session()                                    │   │
│  │  │   └─ call_subagent()  ← 调用子智能体的工具                  │   │
│  │  └─ LLM 决定调用哪些子智能体                                   │   │
│  └────────────────────────────┬───────────────────────────────────┘   │
│                                │                                        │
│            ┌───────────────────┼───────────────────┬───────────────┐    │
│            ▼                   ▼                   ▼               ▼    │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  │ data-perception   │ │ anomaly-detection│ │ rule-reasoning   │ │ disposition     │
│  │ 多维数据感知       │ │ 异常检测          │ │ 规则推理          │ │ execution       │
│  │                  │ │                  │ │                  │ │ 研判处置         │
│  │ 获取、清洗、      │ │ 统计/ML/DL       │ │ 法规匹配、        │ │                  │
│  │ 标准化数据        │ │ 异常检测         │ │ 工艺校验          │ │ 预警分级、       │
│  │                  │ │                  │ │                  │ │ 工单生成         │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘
│         │                     │                     │                     │        │
│         │    各自加载各自的 SOUL.md + AGENTS.md                          │        │
│         │    通过 subprocess 调用                                         │        │
│         │    通过 SESSION_DIR 共享 task.json / result.json               │        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  三库一体 (shared/)                                           │   │
│  │  ├─ operators/  (异常检测算子)                                  │   │
│  │  │   ├─ statistical/  (统计算子)                                │   │
│  │  │   ├─ ml/           (机器学习算子)                             │   │
│  │  │   └─ deep_learning/(深度学习算子)                            │   │
│  │  ├─ knowledge/  (知识库)                                        │   │
│  │  │   ├─ regulations/   (法规库)                                │   │
│  │  │   ├─ process_knowledge/ (工艺知识)                          │   │
│  │  │   └─ violation_patterns/(违规模式)                           │   │
│  │  └─ data/  (时序数据)                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 四个子智能体

| 子智能体 | 职责 | 技能位置 | 输出 |
|----------|------|----------|------|
| **multi-dimensional-data-perception** | 多维数据感知 | 获取、清洗、标准化时序数据 | `data_result.json` |
| **anomaly-detection** | 异常检测 | 统计/ML/DL 算子检测异常 | `anomaly_result.json` |
| **rule-reasoning** | 规则推理 | 法规匹配、工艺校验 | `rule_result.json` |
| **disposition-execution** | 研判处置 | 预警分级、工单生成 | `disposition_result.json` |

### 4.3 子智能体协作关系

```
data-perception (第一步)
    ↓ processed_data
anomaly-detection (第二步)
    ↓ anomalies
rule-reasoning (第三步)
    ↓ conclusion
disposition-execution (第四步，可选)
    ↓ work_order
```

**重要**: 子智能体可以并行调用（当互不依赖时），也可以串行调用（当存在依赖时）。

---

## 五、Hermes 在项目中的具体实现

### 5.1 配置文件 `.hermes/config.yaml`

```yaml
hermes:
  version: "1.0"

# LLM 配置
model:
  provider: custom                    # 自定义 LLM 服务
  base_url_env: LLM_BASE_URL         # 从环境变量读取
  api_key_env: LLM_API_KEY            # 从环境变量读取
  model_env: LLM_MODEL                # 从环境变量读取
  # 默认值（如果环境变量未设置）
  base_url: "https://api.longcat.chat/openai/v1"
  model: "LongCat-2.0"                # 美团 LongCat 模型
  temperature: 0.7
  max_tokens: 4096

# 工具配置 - 4个子智能体作为工具
tools:
  enabled:
    - multi_dimensional_data_perception
    - anomaly_detection
    - rule_reasoning
    - disposition_execution

# 子智能体配置
delegation:
  max_concurrent_children: 4
  subagent_auto_approve: false        # 安全模式，需要人工确认
  timeout: 300                        # 子智能体超时时间（秒）

# 技能配置
skills:
  external_dirs:
    - subagents/multi-dimensional-data-perception-agent/skills
    - subagents/anomaly-detection-agent/skills
    - subagents/rule-reasoning-agent/skills
    - subagents/disposition-execution-agent/skills
```

### 5.2 主智能体调用子智能体

**文件**: `workspace/skills/orchestrator-core/scripts/call_subagent.py`

```python
def call_subagent(subagent_name: str, task: str, context: dict) -> dict:
    """
    调用子智能体执行任务
    
    Args:
        subagent_name: 子智能体名称
        task: 任务描述
        context: 上下文信息
    
    Returns:
        子智能体的执行结果
    """
    # 1. 获取/创建会话目录
    session_dir = get_session_dir()
    
    # 2. 写入 task.json
    task_obj = {
        "task_id": task_id,
        "task": task,
        "context": context,
        "output_format": "json",
        "timeout": 300
    }
    task_file = Path(session_dir) / "task.json"
    json.dump(task_obj, task_file)
    
    # 3. 通过 subprocess 启动子智能体
    env = os.environ.copy()
    env['HERMES_HOME'] = str(subagent_path)
    env['SESSION_DIR'] = session_dir
    env['SUBAGENT_NAME'] = subagent_name
    
    subprocess.run(
        [python_exe, 'run_agent.py'],
        env=env,
        cwd=subagent_path,
        timeout=300
    )
    
    # 4. 读取 result.json
    result_file = Path(session_dir) / result_file_name
    return json.load(result_file)
```

### 5.3 子智能体接收任务

**文件**: `subagents/anomaly-detection-agent/run_agent.py`

```python
def run_subagent():
    """子智能体主入口"""
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME')
    
    # 1. 读取 task.json
    task = load_task(session_dir)
    
    # 2. 初始化 AIAgent
    agent = AIAgent(
        base_url=os.environ.get("LLM_BASE_URL"),
        api_key=os.environ.get("LLM_API_KEY"),
        model=os.environ.get("LLM_MODEL"),
        load_soul_identity=True,        # 加载自己的 SOUL.md
        enabled_toolsets=["skills", "terminal"]
    )
    
    # 3. 执行任务
    response = agent.run_conversation(build_user_message(task))
    
    # 4. 写入 result.json
    write_result(session_dir, response)
```

### 5.4 后端集成

**文件**: `backend/api/client.py`

```python
class HermesAPIClient:
    """Hermes API 客户端"""

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用对话接口（OpenAI 兼容）
        
        Args:
            messages: 消息列表
            session_id: 会话ID（可选）
        
        Returns:
            完整的 Hermes 响应
        """
        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages
        }
        
        if session_id:
            payload["session_id"] = session_id
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload
            )
            return response.json()
```

---

## 六、数据流转流程

### 6.1 完整查询流程

```
用户查询: "最近24小时出水COD异常吗？"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. FastAPI /api/query 接收请求                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. HermesAPIClient.chat_completion()                        │
│    ├─ 构建消息: [{"role": "user", "content": "..."}]        │
│    └─ 调用 Hermes API                                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 主智能体 AIAgent.run_conversation()                      │
│    ├─ 加载 SOUL.md（个性、决策规则）                          │
│    ├─ 加载 AGENTS.md（工作规则）                              │
│    ├─ LLM 意图识别 → "需要数据和异常检测"                     │
│    └─ 决定调用哪些子智能体                                    │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 调用 orchestrator-core 技能的 call_subagent()             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 【子智能体1】data-perception 获取数据                      │
│    ├─ 写入 task.json                                         │
│    ├─ subprocess 启动                                        │
│    ├─ AIAgent 处理 → 加载自己的 SOUL.md                      │
│    └─ 写入 data_result.json                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. 【子智能体2】anomaly-detection 检测异常                    │
│    ├─ 读取前一个结果作为 context                              │
│    ├─ 写入 task.json                                         │
│    ├─ subprocess 启动                                        │
│    ├─ AIAgent 处理 → 使用多种算子检测                         │
│    └─ 写入 anomaly_result.json                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. 主智能体整合结果                                           │
│    ├─ 读取所有 result.json                                   │
│    ├─ LLM 生成自然语言分析                                    │
│    └─ 构建最终响应                                            │
└─────────────────────────────────────────────────────────────┘
    ↓
返回自然语言分析结果
```

### 6.2 会话目录结构

```
sessions/
└── session_20260707_153045/
    ├── _metadata.json              # 会话元数据
    ├── task.json                   # 主智能体写入的任务
    ├── data_result.json            # 数据感知子智能体输出
    ├── anomaly_result.json         # 异常检测子智能体输出
    └── llm_result.json             # LLM 分析结果
```

---

## 七、关键特点

### 7.1 架构特点

| 特点 | 说明 | 体现位置 |
|------|------|----------|
| **LLM 驱动** | 所有调度决策由 LLM 做，非硬编码 | `SOUL.md` 中的决策树 |
| **身份隔离** | 每个智能体有独立的身份文件 | 各自的 `SOUL.md`、`AGENTS.md` |
| **子进程隔离** | 子智能体通过 subprocess 启动 | `call_subagent.py` |
| **文件共享** | 通过 SESSION_DIR 共享状态 | `task.json` / `result.json` |
| **OpenAI 兼容** | 使用标准接口接入自定义 LLM | `config.yaml` 中的 custom provider |

### 7.2 设计原则

#### 原则1: 三库一体 - 全局资源共享

```
数据库、算子库、知识库必须放在全局 shared/ 目录，供所有子智能体调用

三库结构：
├── shared/data/         - 时序监测数据库
├── shared/operators/    - 异常检测模型算子库
│   ├── statistical/     - 统计算子
│   ├── ml/              - 机器学习算子
│   └── deep_learning/   - 深度学习算子
└── shared/knowledge/    - 废水排放知识库
    ├── regulations/     - 法规库
    ├── process_knowledge/ - 工艺知识库
    └── violation_patterns/ - 违规模式库
```

#### 原则2: LLM 驱动主智能体 - 智能调度框架

```
❌ 禁止：为了告警目的随便调用脚本，跳过 LLM 推理
❌ 禁止：在子智能体内部重复实现全局资源
✅ 必须：使用 LLM 进行意图识别和子智能体调度
✅ 必须：LLM 调用失败时抛出明确的错误提示
```

### 7.3 违规检测模式

系统检测 4 类违规模式：

| 违规类型 | 检测规则 |
|----------|----------|
| **插瓶干扰** | 恒定≥2h，值80-100%限值，标准差<0.1 |
| **人工拟合** | R²>0.99，标准差异常低 |
| **稀释排放** | 多指标同步下降≥50%，去除率>95% |
| **恶意逃避** | 数据缺失率>20%，夜间空白 |

---

## 附录

### A. 环境配置

```bash
# .env 文件完整配置
LLM_BASE_URL=https://api.longcat.chat/openai/v1
LLM_API_KEY=ak_xxx
LLM_MODEL=LongCat-2.0

# FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Prometheus
PROMETHEUS_PORT=9090
ENABLE_PROMETHEUS=true

# Hermes API Server
API_SERVER_PORT=8642
API_SERVER_KEY=sk-hermes-api-key
```

### B. 启动命令

```bash
# 启动后端服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Hermes API Server
python -m hermes_api_server

# 运行子智能体（独立模式）
cd subagents/anomaly-detection-agent
python run_agent.py
```

### C. 相关文档

- [技术架构设计](./technical-design.md)
- [CLAUDE.md](../../CLAUDE.md)
- [README.md](../../README.md)

---

**文档维护**: 本文档应随项目架构变化及时更新。
