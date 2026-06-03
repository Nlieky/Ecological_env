#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主智能体核心技能包 - 脚本模块

说明：此模块包含主智能体任务编排所需的脚本支持文件。
脚本由主智能体（大模型）在需要时调用，不独立运行。

模块列表：
- task_structuring: 任务结构化
- task_flow_generation: 任务流生成
- resource_matching: 资源匹配
- execution_control: 执行控制
- cross_domain_analyzer: 跨领域分析
- result_reuse: 结果复用判决
"""

__version__ = "2.0.0"

# 任务编排层模块
from .task_structuring import (
    TaskStructuringModule,
    StructuredTask,
    TaskCategory,
    TaskPriority,
    structure_task,
    structure_batch_tasks
)

from .task_flow_generation import (
    TaskFlowGenerationModule,
    TaskFlow,
    TaskNode,
    ExecutionStage,
    ExecutionMode,
    create_task_flow,
    get_ready_tasks
)

from .resource_matching import (
    ResourceMatchingModule,
    ResourceAllocation,
    AgentCapability,
    AgentStatus,
    match_task_to_agent,
    batch_match_tasks,
    get_available_agents
)

from .execution_control import (
    ExecutionControlModule,
    ExecutionResult,
    ExecutionReport,
    ExecutionStatus,
    execute_single_task_sync,
    execute_task_flow_sync
)

# 专项功能模块
from .cross_domain_analyzer import (
    CrossDomainAnalyzer,
    StreamData,
    CorrelationResult,
    DualStreamAnalysisResult
)

from .result_reuse import (
    ResultReuseModule,
    ReuseDecision,
    ParsedIntent
)

__all__ = [
    # 任务编排层
    "TaskStructuringModule",
    "StructuredTask",
    "TaskCategory",
    "TaskPriority",
    "structure_task",
    "structure_batch_tasks",

    "TaskFlowGenerationModule",
    "TaskFlow",
    "TaskNode",
    "ExecutionStage",
    "ExecutionMode",
    "create_task_flow",
    "get_ready_tasks",

    "ResourceMatchingModule",
    "ResourceAllocation",
    "AgentCapability",
    "AgentStatus",
    "match_task_to_agent",
    "batch_match_tasks",
    "get_available_agents",

    "ExecutionControlModule",
    "ExecutionResult",
    "ExecutionReport",
    "ExecutionStatus",
    "execute_single_task_sync",
    "execute_task_flow_sync",

    # 专项功能
    "CrossDomainAnalyzer",
    "StreamData",
    "CorrelationResult",
    "DualStreamAnalysisResult",

    "ResultReuseModule",
    "ReuseDecision",
    "ParsedIntent",
]
