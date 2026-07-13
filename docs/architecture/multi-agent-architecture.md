# 多智能体架构说明

## 概述

本文档说明废水监测系统的多智能体架构实现。

## 架构设计

系统采用同进程+逻辑隔离的多智能体架构：

```
┌──────────────────────────────────────────────────┐
│               单一进程                            │
│                                                   │
│  ┌────────────┐                                  │
│  │ 主智能体   │                                  │
│  │ AIAgent    │                                  │
│  └──────┬─────┘                                  │
│         │                                        │
│         ├──→ call_subagent                       │
│         │                                        │
│         ▼                                        │
│  ┌────────────────────────────────┐            │
│  │   SubagentManager              │            │
│  │   管理4个子智能体实例            │            │
│  └────────────┬───────────────────┘            │
│               │                                 │
│    ┌──────────┼──────────┬──────────┐          │
│    ▼          ▼          ▼          ▼          │
│ ┌─────┐  ┌─────┐   ┌─────┐   ┌─────┐        │
│ │数据  │  │异常  │   │规则  │   │预警  │        │
│ │感知  │  │检测  │   │推理  │   │处置  │        │
│ └─────┘  └─────┘   └─────┘   └─────┘        │
└──────────────────────────────────────────────────┘
```

## 核心组件

### 1. AIAgent（扩展版）

基于Hermes Agent框架的AIAgent，增加了`identity_path`参数支持。

**关键特性：**
- 支持从自定义路径加载身份文件
- 支持7个身份文件（IDENTITY.md, SOUL.md, AGENTS.md, MEMORY.md, USER.md, TOOLS.md, HEARTBEAT.md）
- 完整的工具调用系统
- 会话管理

### 2. SubagentManager

子智能体实例管理器，负责：
- 创建所有子智能体实例
- 管理子智能体生命周期
- 提供子智能体查询接口

### 3. call_subagent工具

主智能体调用子智能体的工具接口：
- `call_subagent(subagent_name, task, context)`
- 返回子智能体的执行结果

### 4. orchestrator-core技能

主智能体的核心编排技能，定义在`workspace/skills/orchestrator-core/SKILL.md`。

## 使用方法

### 创建主智能体

```python
from run_agent import AIAgent

master_agent = AIAgent(
    model="gpt-4",
    identity_path="workspace",
    load_soul_identity=True
)
```

### 创建子智能体管理器

```python
from scripts.subagent_manager import SubagentManager

manager = SubagentManager(project_root="/path/to/project")
manager.create_subagents(
    model="gpt-4",
    base_url="https://api.example.com",
    api_key="your-api-key"
)
```

### 调用子智能体

```python
from scripts.subagent_tools import call_subagent

result = call_subagent(
    subagent_name="anomaly-detection-agent",
    task="检测数据异常"
)

if result["success"]:
    print(result["result"])
else:
    print(f"Error: {result['error']}")
```

## 目录结构

```
项目根目录/
├── workspace/                      # 主智能体工作区
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── AGENTS.md
│   ├── MEMORY.md
│   ├── USER.md
│   ├── TOOLS.md
│   ├── HEARTBEAT.md
│   └── skills/
│       └── orchestrator-core/
│           ├── SKILL.md
│           └── scripts/
│               ├── subagent_manager.py
│               └── subagent_tools.py
│
├── subagents/                      # 子智能体工作区
│   ├── multi-dimensional-data-perception-agent/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   └── skills/
│   ├── anomaly-detection-agent/
│   ├── rule-reasoning-agent/
│   └── disposition-execution-agent/
│
├── shared/framework/hermes_agent/  # Hermes框架（已修改）
│   ├── agent/
│   │   ├── identity_loader.py      # 新增：身份文件加载器
│   │   ├── agent_init.py           # 修改：支持identity_path
│   │   ├── prompt_builder.py       # 修改：支持identity_path
│   │   └── system_prompt.py        # 修改：支持identity_path
│   └── run_agent.py                # 修改：支持identity_path
│
└── tests/                          # 测试
    ├── unit/
    │   ├── test_identity_loader.py
    │   ├── test_ai_agent_identity_path.py
    │   ├── test_subagent_manager.py
    │   └── test_subagent_tools.py
    └── integration/
        └── test_multi_agent_integration.py
```

## API参考

### AIAgent参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| identity_path | str\|Path | None | 身份文件目录路径 |
| model | str | "" | LLM模型名称 |
| base_url | str | 从环境变量 | API基础URL |
| api_key | str | 从环境变量 | API密钥 |
| load_soul_identity | bool | False | 是否加载身份文件 |

### SubagentManager方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| create_subagents | model, base_url, api_key | None | 创建所有子智能体 |
| get_subagent | name | AIAgent\|None | 获取子智能体实例 |
| list_subagents | - | list[str] | 列出所有子智能体名称 |
| is_subagent_available | name | bool | 检查子智能体是否可用 |
| shutdown | - | None | 关闭所有子智能体 |

### call_subagent工具

| 工具 | 参数 | 返回值 |
|------|------|--------|
| call_subagent | subagent_name, task, context | {success, result, error} |
| initialize_subagents | model, base_url, api_key | {success, count, subagents} |
| list_available_subagents | - | {success, subagents} |
| get_subagent_info | subagent_name | {success, available, description} |
| shutdown_subagents | - | {success, error} |

## 开发指南

### 添加新的子智能体

1. 创建子智能体目录和身份文件
2. 在`SubagentManager.SUBAGENT_CONFIGS`中添加配置
3. 在`orchestrator-core/SKILL.md`中更新职责描述
4. 编写相应测试

### 调试技巧

1. 使用`list_available_subagents`检查子智能体状态
2. 查看日志输出了解调用流程
3. 使用单元测试验证组件功能
4. 使用集成测试验证完整流程

## 参考资料

- 设计文档：`docs/superpowers/specs/2026-07-13-多智能体底层架构设计.md`
- 实现计划：`docs/superpowers/plans/2026-07-13-multi-agent-architecture.md`
- Hermes Agent文档：https://github.com/NousResearch/hermes-agent
