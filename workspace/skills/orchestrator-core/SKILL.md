---
name: orchestrator-core
description: 主智能体核心技能包，用于处理需要任务编排和多子智能体协同的复杂任务。当主智能体接收到需要跨子智能体协调、双数据流分析、结果复用判决等任务时，调用此技能。核心脚本支持：1) 任务结构化-将调度决策转换为标准化任务格式，2) 任务流生成-根据依赖关系生成执行流程，3) 资源匹配-将任务匹配到合适的子智能体，4) 执行控制-驱动子智能体按流程执行，5) 跨领域分析-协调双数据流分析，6) 结果复用判决-判断是否可复用历史结果。适用场景：复杂分析查询、双数据流对比分析、违规检测全流程、报告生成等。
license: MIT
---

# 主智能体核心技能包 (orchestrator-core)

## 技能说明

本技能包是主智能体的核心编排能力实现，由主智能体（大模型）在需要时调用。脚本文件不独立运行，而是作为大模型处理任务时的计算支持工具。

## 何时调用此技能

主智能体在以下情况下应调用此技能：

| 场景 | 说明 |
|------|------|
| 复杂分析查询 | 需要多个子智能体协同的异常分析、违规检测 |
| 双数据流分析 | 需要对比进水和出水数据的联合分析 |
| 结果复用判决 | 需要判断历史结果是否可以复用 |
| 报告生成 | 需要汇总多个子智能体结果生成报告 |
| 任务编排 | 需要生成结构化的执行流程 |

## 可用脚本

### 任务编排层脚本

#### 1. 任务结构化 (task_structuring.py)

**功能**：将主智能体的调度决策转换为标准化的任务格式

**何时调用**：当主智能体需要将自然形式的任务需求转换为结构化任务时

```python
from scripts.task_structuring import structure_task, structure_batch_tasks

# 单个任务结构化
task_request = {
    "task_name": "获取出水口监测数据",
    "category": "data_acquisition",
    "description": "获取最近24小时出水口pH、COD、氨氮监测数据",
    "priority": "high",
    "input_params": [
        {"name": "monitoring_point", "value": "出水口", "required": True},
        {"name": "indicators", "value": ["pH", "COD", "NH3-N"], "required": True}
    ]
}
structured_task = structure_task(task_request)
```

#### 2. 任务流生成 (task_flow_generation.py)

**功能**：根据结构化任务生成执行流程，确定并行/串行执行模式

**何时调用**：当主智能体需要根据任务依赖关系生成可执行的流程时

```python
from scripts.task_flow_generation import create_task_flow, get_ready_tasks

# 创建任务流
flow = create_task_flow(structured_tasks)
# 获取当前可执行的任务
ready_tasks = get_ready_tasks(flow)
```

#### 3. 资源匹配与调度决策 (resource_matching.py)

**功能**：将任务匹配到合适的子智能体，检查资源可用性，并根据专利算法计算任务优先级

**何时调用**：当主智能体需要确定哪个子智能体应该执行某个任务时，或需要确定任务执行顺序时

```python
from scripts.resource_matching import match_task_to_agent, get_available_agents
from scripts.resource_matching import calculate_task_priority, generate_scheduling_strategy

# 匹配任务到子智能体
allocation = match_task_to_agent(structured_task)
# 获取当前可用的子智能体
available = get_available_agents()

# 计算任务优先级（专利算法）
decision = calculate_task_priority(
    task=structured_task,
    wait_time_seconds=1800,  # 等待时间（秒）
    is_critical_path=True,    # 是否在关键路径上
    trigger_source="natural_language"  # 或 "realtime_monitoring"
)

# 生成全局调度策略
strategy = generate_scheduling_strategy(
    tasks=task_list,
    task_waiting_times={"task_001": 600, "task_002": 1800},
    critical_path_tasks=["task_001", "task_003"]
)
```

**专利优先级计算公式**：
```
P = wp × priority + wt × wait_time + wd × critical_path
```
- wp = 0.6（优先级权重）
- wt = 0.2（等待时间权重）
- wd = 0.2（关键路径权重）
- 实时监测任务直接赋予最高优先级 P=10

#### 4. 执行控制 (execution_control.py)

**功能**：驱动子智能体按流程执行任务，监控执行状态

**何时调用**：当主智能体需要实际执行任务流或单个任务时

```python
from scripts.execution_control import execute_task_flow_sync

# 执行完整任务流
report = execute_task_flow_sync(flow, allocations)
```

### 专项功能脚本

#### 5. 跨领域分析 (cross_domain_analyzer.py)

**功能**：协调双数据流（进水+出水）的联合分析

**何时调用**：当需要对比分析进水和出水数据，检测数据异常时

```python
from scripts.cross_domain_analyzer import CrossDomainAnalyzer

analyzer = CrossDomainAnalyzer()
result = analyzer.analyze_dual_stream(influent_data, effluent_data)
correlation = analyzer.calculate_correlation(influent_data, effluent_data)
```

#### 6. 结果复用判决 (result_reuse.py)

**功能**：判断历史结果是否可以复用，避免重复计算

**何时调用**：当主智能体接收到查询时，先判断是否有可复用的历史结果

```python
from scripts.result_reuse import ResultReuseModule

reuse_module = ResultReuseModule()
decision = reuse_module.decide(query_intent)
if decision.can_reuse:
    return decision.cached_result
```

## 子智能体列表

| 子智能体ID | 名称 | 核心能力 |
|-----------|------|----------|
| data-governance-agent | 数据治理子智能体 | 多源数据获取、时序对齐、数据清洗、标准化 |
| feature-analysis-agent | 特征与关系分析子智能体 | 时序特征提取、相关性分析、趋势分析、特征融合 |
| anomaly-detection-agent | 异常检测子智能体 | 算子适配、异常评分、模式识别、违规检测 |
| rule-reasoning-agent | 规则推理子智能体 | 法规匹配、工艺校验、专家推理、违规结论 |

## 标准工作流示例

### 分析查询工作流

```
1. 主智能体接收查询 → 解析意图
2. 调用结果复用判决 → 判断是否可复用
3. 如果不可复用：
   a. 任务结构化 → 创建结构化任务
   b. 任务流生成 → 生成执行流程
   c. 资源匹配 → 分配子智能体
   d. 执行控制 → 驱动执行
4. 汇总结果 → 返回用户
```

### 双数据流分析工作流

```
1. 主智能体接收双数据流分析请求
2. 调用跨领域分析脚本
3. 返回对比分析结果
```

## 参考文档

- [子智能体注册表](references/subagent_manifest.json) - 4个子智能体的配置和能力清单
- [工作流模式库](references/workflow_patterns.md) - 常见任务的工作流模板
- [决策规则库](references/decision_rules.md) - 路由和判定的决策规则
- [升级上报流程](references/escalation_protocols.md) - 高风险问题的处理流程
- [历史案例库](references/historical_cases.md) - 典型案例参考

## 版本信息

- **版本**: 2.0.0
- **创建日期**: 2026-05-15
- **架构**: 专利六层架构
- **说明**: 主智能体 = E:\project\Ecological_env\workspace\ 整个目录
