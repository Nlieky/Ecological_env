---
name: master-agent
description: 废水监测主智能体 - 负责全局协调和任务编排的多智能体协调系统
version: 2.0.0
license: MIT
---

# 主智能体 (Master Agent)

## 技能说明

废水监测主智能体是一个 Multi-Agent Orchestrator（多智能体编排器），负责协调 4 个子智能体完成废水监测领域的复杂任务。主智能体采用全 LLM 驱动模式，通过自然语言理解用户意图，智能编排子智能体协同工作。

## 核心能力

### 1. 语义解析与意图识别
- 理解自然语言指令
- 识别任务类型（违规检测、分析查询、历史回溯、预警响应）
- 提取关键参数和约束条件

### 2. 任务编排与调度
- 任务结构化：将自然语言需求转换为标准化任务
- 任务流生成：根据依赖关系生成执行流程（串行/并行/混合）
- 资源匹配：将任务分配到合适的子智能体
- 优先级计算：基于专利算法计算任务优先级

### 3. 动态协调执行
- 驱动子智能体按流程执行
- 监控执行状态和进度
- 处理异常和错误恢复
- 数据流传递和结果整合

### 4. 结果复用优化
- 判断历史结果是否可复用
- 避免重复计算，提高响应速度
- 三重判决机制（语义、参数、时效）

## 管理的子智能体

| 子智能体 | ID | 核心能力 |
|---------|-------|----------|
| 📊 多维数据感知智能体 | multi-dimensional-data-perception-agent | 多源数据获取、时序对齐、数据清洗、标准化 |
| 🔍 异常检测智能体 | anomaly-detection-agent | 统计异常检测、机器学习异常检测、模式识别 |
| ⚖️ 规则推理智能体 | rule-reasoning-agent | 法规匹配、工艺校验、专家推理、违规判定 |
| 🚨 研判预警与处置执行智能体 | disposition-execution-agent | 融合共识、预警分级、工单生成、行动执行 |

## 任务类型映射

### 违规检测任务
**协同智能体**：全部 4 个子智能体
```
数据感知 → 异常检测 → 规则推理 → 预警执行
```

### 分析查询任务
**协同智能体**：数据感知 + 异常检测
```
数据感知 → 异常检测 → 结果汇总
```

### 历史回溯任务
**协同智能体**：数据感知 + 规则推理
```
数据感知 → 规则推理 → 案例匹配
```

### 预警响应任务
**协同智能体**：仅预警执行智能体
```
接收预警 → 融合共识 → 工单推送
```

## 核心技能包

主智能体的编排能力由 `orchestrator-core` 技能包实现，包含：

### 任务编排层
- `task_structuring.py` - 任务结构化
- `task_flow_generation.py` - 任务流生成
- `resource_matching.py` - 资源匹配与调度决策
- `execution_control.py` - 执行控制

### 专项功能
- `cross_domain_analyzer.py` - 跨领域分析（双数据流）
- `result_reuse.py` - 结果复用判决
- `dynamic_orchestrator.py` - 动态编排器
- `result_interpretation.py` - 结果解释

## 专利算法

### 任务优先级计算
```
P = wp × priority + wt × wait_time + wd × critical_path
```

参数说明：
- `wp = 0.6` - 优先级权重
- `wt = 0.2` - 等待时间权重
- `wd = 0.2` - 关键路径权重
- 实时监测任务直接赋予最高优先级 P=10

### 结果复用三重判决
1. **语义判决**：查询意图与历史任务的语义相似度
2. **参数判决**：输入参数与历史任务的参数一致性
3. **时效判决**：历史结果的时间有效性

## 使用方式

### 直接调用执行控制
```python
from skills.orchestrator_core.scripts.execution_control import execute_task_flow_sync

# 执行任务流
report = execute_task_flow_sync(task_flow, allocations)
```

### 调用任务编排组件
```python
from skills.orchestrator_core.scripts.task_structuring import structure_task
from skills.orchestrator_core.scripts.resource_matching import match_task_to_agent

# 结构化任务
task = structure_task(task_request)

# 匹配子智能体
allocation = match_task_to_agent(task)
```

### 调用专项功能
```python
from skills.orchestrator_core.scripts.cross_domain_analyzer import CrossDomainAnalyzer
from skills.orchestrator_core.scripts.result_reuse import ResultReuseModule

# 双数据流分析
analyzer = CrossDomainAnalyzer()
result = analyzer.analyze_dual_stream(influent_data, effluent_data)

# 结果复用判决
reuse_module = ResultReuseModule()
decision = reuse_module.decide(query_intent)
```

## 参考文档

- [子智能体注册表](../shared/configs/agent_registry.yaml) - 子智能体配置和能力清单
- [核心技能包文档](skills/orchestrator-core/SKILL.md) - orchestrator-core 技能包详细说明
- [工作流模式库](skills/orchestrator-core/references/workflow_patterns.md)
- [决策规则库](skills/orchestrator-core/references/decision_rules.md)
- [升级上报流程](skills/orchestrator-core/references/escalation_protocols.md)

## 注意事项

1. **LLM 驱动模式**：主智能体完全由大模型驱动，所有决策都通过 LLM 进行
2. **脚本执行支持**：编排和协调操作通过脚本执行，提供计算支持
3. **子智能体自治**：各子智能体独立运行，主智能体只负责任务分配和结果整合
4. **错误恢复**：内置异常处理和降级策略，确保系统稳定性

## 版本信息

- **版本**: 2.0.0
- **创建日期**: 2026-05-15
- **架构**: 专利六层架构
- **位置**: `E:\project\Ecological_env\workspace\`
