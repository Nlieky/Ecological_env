# Hermes 真正的多智能体系统实现方案

## 目标架构

```
用户查询
  ↓
FastAPI (8000)
  ↓
Hermes API Server (8642)
  ↓
主智能体 (workspace/)
  ├─ orchestrator-core skill (编排器)
  └─ delegate_task 工具
      ↓
  子智能体1 (multi-dimensional-data-perception-agent/)
  ├─ SOUL.md (数据感知专家个性)
  ├─ AGENTS.md (数据感知任务指令)
  ├─ MEMORY.md (数据感知专业记忆)
  └─ skills/ (数据感知专业技能)
      ├─ data_acquisition
      ├─ data_cleaning
      ├─ time_alignment
      ├─ standardization
      └─ data_decomposition
  ↓
  返回结果给主智能体
  ↓
主智能体整合 → 用户
```

## 关键区别

| 方面 | 主智能体 | 子智能体 |
|------|---------|---------|
| **位置** | workspace/ | subagents/xxx-agent/ |
| **身份** | 综合协调者 | 领域专家 |
| **技能** | orchestrator-core (编排) | 领域专业技能 (多个) |
| **记忆** | 全局对话记忆 | 专业领域记忆 |
| **调用方式** | 被用户调用 | 被 delegate_task 调用 |

## 在 Hermes 中的实现

### 方式 1：使用 delegate_task 工具（推荐）

主智能体通过 `delegate_task` 调用子智能体：

```yaml
# workspace/SOUL.md 中添加
## 子智能体调用

当你需要处理废水监测数据时，使用 delegate_task 工具调用以下子智能体：

1. **multi-dimensional-data-perception** - 多维数据感知
   - 工作区: ../subagents/multi-dimensional-data-perception-agent
   - 功能: 获取多维时序数据，分解、清洗、标准化

2. **anomaly-detection** - 异常检测
   - 工作区: ../subagents/anomaly-detection-agent
   - 功能: 使用多种算子检测时序数据异常

3. **rule-reasoning** - 规则推理
   - 工作区: ../subagents/rule-reasoning-agent
   - 功能: 基于法规和工艺知识进行规则推理

4. **disposition-execution** - 研判预警与处置
   - 工作区: ../subagents/disposition-execution-agent
   - 功能: 融合异常检测和规则推理结果，生成处置工单
```

### 方式 2：创建子智能体调用技能

在 workspace/skills/ 中创建一个 orchestrator 技能，该技能负责调用子智能体：

```python
# workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py
from hermes_cli.tools import delegate_task

def orchestrate(query):
    """编排子智能体处理"""
    # 1. 数据获取
    data_result = delegate_task(
        agent_workspace="../subagents/multi-dimensional-data-perception-agent",
        task="获取当前进水和出水数据"
    )

    # 2. 异常检测
    anomaly_result = delegate_task(
        agent_workspace="../subagents/anomaly-detection-agent",
        task=f"检测以下数据中的异常: {data_result}"
    )

    # 3. 规则推理
    rule_result = delegate_task(
        agent_workspace="../subagents/rule-reasoning-agent",
        task=f"根据标准判断以下数据是否合规: {anomaly_result}"
    )

    # 4. 生成处置方案
    disposition_result = delegate_task(
        agent_workspace="../subagents/disposition-execution-agent",
        task=f"基于以下分析结果生成处置工单: {rule_result}"
    )

    return {
        "data": data_result,
        "anomalies": anomaly_result,
        "compliance": rule_result,
        "disposition": disposition_result
    }
```

## 配置文件

### workspace/config.yaml

```yaml
# 主智能体配置
model:
  base_url: "http://172.16.12.41:30000/v1"
  default: "ctgu-vlm"
  provider: "openai-api"

# 技能配置（主智能体的编排技能）
skills:
  external_dirs:
    - skills/orchestrator-core

# 子智能体配置（用于 delegate_task）
delegation:
  # 子智能体相对于主智能体的路径
  base_path: ../subagents
  max_iterations: 50
  child_timeout_seconds: 600
```

### 子智能体配置

每个子智能体目录需要有：
- `SOUL.md` - 子智能体身份
- `AGENTS.md` - 任务规范
- `MEMORY.md` - 专业记忆
- `config.yaml` - 子智能体配置（可选）
- `skills/` - 该子智能体的专业技能

## 工作流程

1. **用户发送查询** → FastAPI
2. **FastAPI 调用** → Hermes API Server
3. **Hermes 加载主智能体** → workspace/SOUL.md, AGENTS.md
4. **LLM 分析查询** → 决定需要哪些子智能体
5. **主智能体调用 orchestrator 技能**
6. **Orchestrator 使用 delegate_task** → 依次调用 4 个子智能体
7. **每个子智能体加载自己的 SOUL/AGENTS/MEMORY**
8. **每个子智能体调用自己的专业技能**
9. **结果逐层返回** → 主智能体整合 → 用户

## 优势

- ✓ 保持原有多智能体架构
- ✓ 每个子智能体有独立的身份和记忆
- ✓ 子智能体可以独立开发和测试
- ✓ 符合真正的多智能体系统设计
- ✓ 与另一个项目的框架一致
