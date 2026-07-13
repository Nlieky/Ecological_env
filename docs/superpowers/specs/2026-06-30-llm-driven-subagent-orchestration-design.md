# LLM 驱动的子智能体编排设计

> **创建日期**: 2026-06-30
> **状态**: 待审核
> **优先级**: 高

## 目标

实现 LLM 驱动的子智能体编排机制，让主智能体通过 LLM 理解任务并动态调用子智能体，每个子智能体加载自己的身份文件并完成任务。

## 背景

### 当前状态

- 子智能体能够加载自己的身份文件（SOUL.md、AGENTS.md、MEMORY.md）- 已验证 ✅
- Hermes 框架的 `delegate_task` 创建的内部子智能体**不加载**身份文件 - 已确认 ❌
- 需要自己实现子智能体调用机制

### 核心需求

1. **主智能体**通过 LLM 读取自己的身份文件，理解任务并动态决策
2. **子智能体**能够加载自己的身份文件，理解自己的职责
3. **LLM 驱动**的编排过程，而非固定逻辑
4. **最小化固定逻辑**，只有绝对必要的机制才用固定代码

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│               主智能体 (Hermes AIAgent)                       │
│  位置: workspace/                                             │
│  • 加载 workspace/SOUL.md, AGENTS.md, MEMORY.md             │
│  • 通过 LLM 理解任务和决策                                   │
│  • 拥有以下工具供 LLM 调用：                                │
│  • 从 shared/ 只读 (未来可能开放写权限)                       │
└──────────────────────────┬──────────────────────────────────┘
                           ↓ LLM 决策调用
┌─────────────────────────────────────────────────────────────┐
│       主智能体工具集 (subagent_tools.py)                     │
│  位置: workspace/skills/orchestrator-core/scripts/           │
│  • call_subagent()      - 调用子智能体                       │
│  • read_result()        - 读取子智能体结果                   │
│  • list_subagents()     - 列出可用子智能体                   │
│  • create_session()     - 创建会话目录                       │
└──────────────────────────┬──────────────────────────────────┘
                           ↓ Subprocess 调用
┌─────────────────────────────────────────────────────────────┐
│                    子智能体 (Hermes AIAgent 实例)              │
│  • anomaly-detection-agent          │
│  • rule-reasoning-agent             │
│  • disposition-execution-agent      │
│  • multi-dimensional-data-perception-agent  │
│  • 加载自己的 SOUL.md, AGENTS.md                             │
│  • 从 shared/ 只读                                           │
│  • 结果写入 sessions/ 通信仓库                              │
└─────────────────────────────────────────────────────────────┘
                    ↓                           ↓
┌───────────────────────────┐   ┌───────────────────────────┐
│   全局共享资源 (shared/)   │   │   通信仓库 (sessions/)    │
│  • operators/  # 算子库     │   │  • task.json              │
│  • data/       # 数据库     │   │  • data_result.json       │
│  • knowledge/  # 知识库     │   │  • anomaly_result.json    │
│  ⚠️ 主智能体/子智能体只能读取 │   │  • rule_result.json        │
└───────────────────────────┘   │  • disposition_result.json │
                               └───────────────────────────┘
```

### 目录结构

```
Ecological_env/
├── workspace/                    # 主智能体
│   ├── SOUL.md                  # 主智能体身份文件
│   ├── AGENTS.md                # 主智能体规则
│   ├── MEMORY.md                # 主智能体记忆
│   └── skills/
│       └── orchestrator-core/
│           └── scripts/
│               ├── create_session.py
│               ├── call_subagent.py
│               ├── subagent_tools.py  # 工具定义
│               └── cleanup_sessions.py
│
├── subagents/                   # 子智能体
│   ├── anomaly-detection-agent/
│   │   ├── SOUL.md              # 子智能体身份文件
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   └── run_agent.py
│   ├── rule-reasoning-agent/
│   ├── disposition-execution-agent/
│   └── multi-dimensional-data-perception-agent/
│
├── shared/                       # 全局共享资源（只读）
│   ├── operators/               # 算子库
│   ├── data/                    # 数据库
│   └── knowledge/               # 知识库
│
└── sessions/                    # 通信仓库（读写）
    └── {session_id}/
        ├── task.json
        ├── data_result.json
        ├── anomaly_result.json
        ├── rule_result.json
        └── disposition_result.json
```

---

## 工具定义

### subagent_tools.py

**位置**: `workspace/skills/orchestrator-core/scripts/subagent_tools.py`

```python
"""
主智能体工具集 - 子智能体调用工具

供主智能体通过 LLM 调用，实现动态子智能体编排。
"""

from typing import Dict, Any, List, Optional


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    调用子智能体执行任务
    
    Args:
        subagent_name: 子智能体名称 (如 "anomaly-detection")
        task: 任务描述
        context: 上一个子智能体的结果（可选）
    
    Returns:
        {
            "task_id": str,
            "status": "completed" | "failed",
            "result": dict | None,
            "error": str | None,
            "metadata": {
                "duration_seconds": float,
                "timestamp": str,
                "subagent_name": str
            }
        }
    
    Raises:
        ValueError: 未知子智能体名称
        IOError: 会话目录创建失败
    """
    from .call_subagent import call_subagent as _call_subagent
    return _call_subagent(subagent_name, task, context)


def read_result(result_file: str) -> Dict[str, Any]:
    """
    读取子智能体结果文件
    
    Args:
        result_file: 结果文件路径（相对于 sessions/{session_id}/）
    
    Returns:
        结果数据字典
    """
    import json
    from pathlib import Path
    from .create_session import get_session_dir
    
    session_dir = get_session_dir()
    result_path = Path(session_dir) / result_file
    
    if not result_path.exists():
        return {"error": f"Result file not found: {result_file}"}
    
    with open(result_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_subagents() -> List[Dict[str, str]]:
    """
    列出所有可用的子智能体
    
    Returns:
        [
            {"id": "anomaly-detection", "name": "异常检测子智能体", "path": "..."},
            {"id": "rule-reasoning", "name": "规则推理子智能体", "path": "..."},
            ...
        ]
    """
    from .call_subagent import SUBAGENT_PATHS, SUBAGENT_FILE_NAMES
    
    agents = []
    for agent_id, path in SUBAGENT_PATHS.items():
        # 只返回完整名称的子智能体
        if "-" in agent_id:  # 排除简化名称
            agents.append({
                "id": agent_id,
                "name": agent_id.replace("-", " ").title(),
                "path": path
            })
    return agents


def create_session() -> str:
    """
    创建新的会话目录
    
    Returns:
        session_id: 会话ID（用于通信）
    """
    from .create_session import create_session as _create_session
    return _create_session()
```

---

## 执行流程（LLM 驱动）

### 完整流程

```
1. 用户请求
   "检测最近一周的pH值异常情况"
   ↓
2. 主智能体启动
   • 加载 workspace/SOUL.md（身份）
   • 加载 workspace/AGENTS.md（规则）
   • 加载 workspace/MEMORY.md（记忆）
   ↓
3. LLM 理解任务
   • 分析用户意图
   • 识别需要的子智能体
   • 规划调用顺序
   ↓
4. LLM 决策并调用工具
   create_session() → 获取 session_id
   ↓
5. LLM 调用子智能体
   call_subagent("multi-dimensional-data-perception", "获取最近一周的pH值数据")
   ↓
6. 子智能体执行
   • 加载自己的 SOUL.md
   • 读取 shared/data/ 中的数据
   • 执行数据处理
   • 写入 sessions/{session_id}/data_result.json
   ↓
7. LLM 读取结果
   read_result("data_result.json")
   ↓
8. LLM 分析并决策下一步
   "数据已准备好，现在需要检测异常"
   ↓
9. LLM 调用下一个子智能体
   call_subagent("anomaly-detection", "检测pH值异常", context=data_result)
   ↓
10. 重复 5-9，直到所有子智能体完成
   ↓
11. LLM 整合结果，返回用户
```

### 错误处理流程（LLM 驱动）

```
子智能体返回错误
   ↓
LLM 分析错误
   • 是数据问题吗？ → 调用数据感知子智能体重新获取
   • 是参数问题吗？ → 修正参数后重试
   • 是子智能体问题吗？ → 跳过该子智能体，继续执行
   ↓
LLM 决策处理方式
   • 重试
   • 跳过
   • 终止并返回错误
```

---

## 数据结构

### task.json

```json
{
  "task_id": "task_20260630_123456_abc123",
  "task": "检测最近一周的pH值异常情况",
  "context": {
    "previous_result": {...}
  },
  "output_format": "json",
  "timeout": 300
}
```

### anomaly_result.json

```json
{
  "status": "completed",
  "result": {
    "anomalies": [
      {
        "indicator": "pH值",
        "time": "2026-06-29T14:30:00Z",
        "value": 8.5,
        "pattern": "spike",
        "severity": "high"
      }
    ]
  },
  "metadata": {
    "duration_seconds": 2.5,
    "timestamp": "2026-06-30T12:35:00Z",
    "subagent_name": "anomaly-detection"
  }
}
```

### 错误响应

```json
{
  "status": "failed",
  "result": null,
  "error": "Subagent process failed: ...",
  "metadata": {
    "duration_seconds": 0.5,
    "timestamp": "2026-06-30T12:35:00Z",
    "stdout": "...",
    "stderr": "..."
  }
}
```

---

## 约束条件

### 只读约束
- 主智能体和子智能体**只能读取** `shared/` 目录
- 不能对 `shared/` 进行任何写操作
- 未来可能对主智能体开放写权限

### 通信约束
- 主智能体和子智能体通过 `sessions/` 目录通信
- 主智能体写入 `task.json`，子智能体读取
- 子智能体写入 `xxx_result.json`，主智能体读取

### 子智能体独立性
- 每个子智能体是独立的 Hermes AIAgent 实例
- 每个子智能体有自己的身份文件
- 子智能体之间不直接通信，只通过主智能体协调

---

## 子智能体列表

| ID | 名称 | 目录 | 结果文件 |
|----|------|------|----------|
| multi-dimensional-data-perception | 多维数据感知子智能体 | subagents/multi-dimensional-data-perception-agent/ | data_result.json |
| anomaly-detection | 异常检测子智能体 | subagents/anomaly-detection-agent/ | anomaly_result.json |
| rule-reasoning | 规则推理子智能体 | subagents/rule-reasoning-agent/ | rule_result.json |
| disposition-execution | 研判预警与处置执行子智能体 | subagents/disposition-execution-agent/ | disposition_result.json |

---

## 实现计划

### 阶段 1：工具实现
- [ ] 实现 `subagent_tools.py` 工具定义
- [ ] 确保 `call_subagent.py` 正确调用子智能体
- [ ] 确保 `create_session.py` 正确创建会话目录

### 阶段 2：测试验证
- [ ] 测试主智能体加载身份文件
- [ ] 测试子智能体加载身份文件
- [ ] 测试完整调用流程
- [ ] 测试错误处理流程

### 阶段 3：集成优化
- [ ] 优化 LLM 提示词
- [ ] 添加日志和监控
- [ ] 性能优化

---

## 参考资料

- Hermes Agent 框架: https://github.com/NousResearch/hermes-agent
- 项目 README: `README.md`
- 项目架构: `docs/architecture.md`
