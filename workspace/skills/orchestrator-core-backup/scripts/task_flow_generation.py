#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务流生成脚本
功能：根据结构化任务生成执行流程，确定并行/串行执行模式

说明：此脚本由主智能体（大模型）调用，用于根据结构化任务生成
可执行的任务流，分析任务依赖关系，确定最优的执行策略。
"""

import logging
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"   # 串行执行
    PARALLEL = "parallel"       # 并行执行
    HYBRID = "hybrid"           # 混合执行（部分并行+部分串行）


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    """任务节点"""
    task_id: str
    task_data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)  # 依赖此任务的其他任务

    # 执行信息
    agent_id: str = ""
    execution_order: int = -1
    execution_group: int = -1  # 并行执行组号

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_data": self.task_data,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "agent_id": self.agent_id,
            "execution_order": self.execution_order,
            "execution_group": self.execution_group
        }


@dataclass
class ExecutionStage:
    """执行阶段（同一阶段内的任务可以并行执行）"""
    stage_id: int
    tasks: List[str] = field(default_factory=list)  # 任务ID列表
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "stage_id": self.stage_id,
            "tasks": self.tasks,
            "execution_mode": self.execution_mode.value
        }


@dataclass
class TaskFlow:
    """任务流"""
    flow_id: str
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    stages: List[ExecutionStage] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.HYBRID

    # 元数据
    total_tasks: int = 0
    estimated_duration_seconds: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "flow_id": self.flow_id,
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "stages": [s.to_dict() for s in self.stages],
            "execution_mode": self.execution_mode.value,
            "total_tasks": self.total_tasks,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "metadata": self.metadata
        }


class TaskFlowGenerationError(Exception):
    """任务流生成异常"""
    pass


class CircularDependencyError(TaskFlowGenerationError):
    """循环依赖异常"""
    pass


class TaskFlowGenerationModule:
    """任务流生成模块"""

    def __init__(self):
        """初始化任务流生成模块"""
        self.name = "任务流生成模块"
        self.version = "2.0.0"
        self.flow_counter = 0

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def generate_flow_id(self) -> str:
        """生成任务流ID"""
        self.flow_counter += 1
        return f"flow_{self.flow_counter:06d}"

    def create_task_flow(self, structured_tasks: List[Dict[str, Any]]) -> TaskFlow:
        """
        创建任务流

        Args:
            structured_tasks: 结构化任务列表

        Returns:
            TaskFlow: 任务流
        """
        flow_id = self.generate_flow_id()

        # 创建任务节点
        tasks = {}
        for task_data in structured_tasks:
            task_id = task_data["task_id"]
            node = TaskNode(
                task_id=task_id,
                task_data=task_data,
                dependencies=task_data.get("dependencies", [])
            )
            tasks[task_id] = node

        # 构建依赖关系图
        self._build_dependency_graph(tasks)

        # 检测循环依赖
        self._detect_circular_dependencies(tasks)

        # 确定执行模式
        execution_mode = self._determine_execution_mode(tasks)

        # 生成执行阶段
        stages = self._generate_execution_stages(tasks)

        # 估算执行时间
        estimated_duration = self._estimate_duration(tasks, stages)

        flow = TaskFlow(
            flow_id=flow_id,
            tasks=tasks,
            stages=stages,
            execution_mode=execution_mode,
            total_tasks=len(tasks),
            estimated_duration_seconds=estimated_duration
        )

        logger.info(f"[FLOW] Task flow created: {flow_id}, {len(tasks)} tasks, {len(stages)} stages")
        return flow

    def _build_dependency_graph(self, tasks: Dict[str, TaskNode]):
        """构建依赖关系图（建立dependents）"""
        for task_id, node in tasks.items():
            for dep_id in node.dependencies:
                if dep_id in tasks:
                    tasks[dep_id].dependents.append(task_id)

    def _detect_circular_dependencies(self, tasks: Dict[str, TaskNode]):
        """检测循环依赖"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in tasks}

        def dfs(task_id: str, path: Set[str]) -> bool:
            if color[task_id] == GRAY:
                # 发现环
                cycle = " -> ".join(list(path) + [task_id])
                raise CircularDependencyError(f"Circular dependency detected: {cycle}")
            if color[task_id] == BLACK:
                return True

            color[task_id] = GRAY
            path.add(task_id)

            for dep_id in tasks[task_id].dependencies:
                if dep_id in tasks:
                    dfs(dep_id, path)

            path.remove(task_id)
            color[task_id] = BLACK
            return True

        for task_id in tasks:
            if color[task_id] == WHITE:
                dfs(task_id, set())

    def _determine_execution_mode(self, tasks: Dict[str, TaskNode]) -> ExecutionMode:
        """确定执行模式"""
        has_deps = any(node.dependencies for node in tasks.values())
        has_multi = len(tasks) > 1

        if not has_deps and has_multi:
            # 无依赖关系，可以全部并行
            return ExecutionMode.PARALLEL
        elif has_deps and has_multi:
            # 有依赖关系，使用混合模式
            return ExecutionMode.HYBRID
        else:
            # 单任务或特殊情况
            return ExecutionMode.SEQUENTIAL

    def _generate_execution_stages(self, tasks: Dict[str, TaskNode]) -> List[ExecutionStage]:
        """生成执行阶段"""
        stages = []
        completed = set()
        stage_id = 0

        while len(completed) < len(tasks):
            # 找出所有依赖已满足的任务
            ready_tasks = []
            for task_id, node in tasks.items():
                if task_id in completed:
                    continue
                # 检查所有依赖是否已完成
                if all(dep in completed for dep in node.dependencies):
                    ready_tasks.append(task_id)

            if not ready_tasks:
                # 无法继续执行（可能存在未检测的依赖问题）
                remaining = [tid for tid in tasks if tid not in completed]
                raise TaskFlowGenerationError(f"Cannot resolve dependencies for tasks: {remaining}")

            # 创建新阶段
            stage = ExecutionStage(
                stage_id=stage_id,
                tasks=ready_tasks,
                execution_mode=ExecutionMode.PARALLEL if len(ready_tasks) > 1 else ExecutionMode.SEQUENTIAL
            )
            stages.append(stage)

            # 设置任务的执行组
            for task_id in ready_tasks:
                tasks[task_id].execution_group = stage_id
                tasks[task_id].execution_order = len(completed) + list(ready_tasks).index(task_id)
                tasks[task_id].status = TaskStatus.READY

            completed.update(ready_tasks)
            stage_id += 1

        return stages

    def _estimate_duration(self, tasks: Dict[str, TaskNode], stages: List[ExecutionStage]) -> int:
        """估算执行时间（秒）"""
        # 基于任务超时时间和并行度估算
        total = 0
        for stage in stages:
            # 同阶段内的任务并行执行，取最长时间
            max_timeout = 0
            for task_id in stage.tasks:
                timeout = tasks[task_id].task_data.get("timeout_seconds", 300)
                max_timeout = max(max_timeout, timeout)
            total += max_timeout
        return total

    def optimize_flow(self, flow: TaskFlow, optimization_goal: str = "speed") -> TaskFlow:
        """
        优化任务流

        Args:
            flow: 任务流
            optimization_goal: 优化目标（speed: 速度优先, reliability: 可靠性优先）

        Returns:
            TaskFlow: 优化后的任务流
        """
        # 根据优化目标调整任务流
        if optimization_goal == "speed":
            # 速度优先：增加并行度
            pass  # 已经在生成阶段实现
        elif optimization_goal == "reliability":
            # 可靠性优先：增加重试次数，设置更长的超时
            for task_id, node in flow.tasks.items():
                node.task_data["retry_count"] = node.task_data.get("retry_count", 3) + 1
                node.task_data["timeout_seconds"] = int(node.task_data.get("timeout_seconds", 300) * 1.2)

        flow.metadata["optimization_goal"] = optimization_goal
        return flow

    def get_ready_tasks(self, flow: TaskFlow) -> List[str]:
        """
        获取当前可以执行的任务

        Args:
            flow: 任务流

        Returns:
            List[str]: 可执行的任务ID列表
        """
        ready = []
        for task_id, node in flow.tasks.items():
            if node.status == TaskStatus.READY:
                ready.append(task_id)
        return ready

    def mark_task_completed(self, flow: TaskFlow, task_id: str, success: bool = True):
        """
        标记任务完成，更新下游任务状态

        Args:
            flow: 任务流
            task_id: 任务ID
            success: 是否成功
        """
        if task_id not in flow.tasks:
            return

        # 更新任务状态
        flow.tasks[task_id].status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        # 更新依赖此任务的任务状态
        for dependent_id in flow.tasks[task_id].dependents:
            dependent = flow.tasks[dependent_id]
            if dependent.status == TaskStatus.PENDING:
                # 检查所有依赖是否都已完成
                if all(flow.tasks[dep].status == TaskStatus.COMPLETED for dep in dependent.dependencies):
                    dependent.status = TaskStatus.READY

    def get_flow_summary(self, flow: TaskFlow) -> Dict[str, Any]:
        """
        获取任务流摘要

        Args:
            flow: 任务流

        Returns:
            Dict: 任务流摘要
        """
        status_count = {
            TaskStatus.PENDING.value: 0,
            TaskStatus.READY.value: 0,
            TaskStatus.RUNNING.value: 0,
            TaskStatus.COMPLETED.value: 0,
            TaskStatus.FAILED.value: 0,
            TaskStatus.SKIPPED.value: 0
        }

        for node in flow.tasks.values():
            status_count[node.status.value] += 1

        return {
            "flow_id": flow.flow_id,
            "total_tasks": flow.total_tasks,
            "total_stages": len(flow.stages),
            "execution_mode": flow.execution_mode.value,
            "estimated_duration_seconds": flow.estimated_duration_seconds,
            "task_status": status_count,
            "completed_ratio": status_count[TaskStatus.COMPLETED.value] / flow.total_tasks if flow.total_tasks > 0 else 0
        }


# 便捷函数，供主智能体调用
def create_task_flow(structured_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    创建任务流（便捷函数）

    Args:
        structured_tasks: 结构化任务列表

    Returns:
        Dict: 任务流的字典表示
    """
    module = TaskFlowGenerationModule()
    flow = module.create_task_flow(structured_tasks)
    return flow.to_dict()


def get_ready_tasks(flow_dict: Dict[str, Any]) -> List[str]:
    """
    获取可执行任务列表（便捷函数）

    Args:
        flow_dict: 任务流字典

    Returns:
        List[str]: 可执行任务ID列表
    """
    # 从字典重建任务流对象
    flow = TaskFlow(flow_id=flow_dict["flow_id"])
    flow.tasks = {
        tid: TaskNode(tid, t["task_data"], TaskStatus(t["status"]), t.get("dependencies", []))
        for tid, t in flow_dict["tasks"].items()
    }

    module = TaskFlowGenerationModule()
    return module.get_ready_tasks(flow)


if __name__ == "__main__":
    # 测试代码
    test_tasks = [
        {
            "task_id": "task_000001",
            "task_name": "数据获取",
            "category": "data_acquisition",
            "dependencies": []
        },
        {
            "task_id": "task_000002",
            "task_name": "特征分析",
            "category": "feature_analysis",
            "dependencies": ["task_000001"]
        },
        {
            "task_id": "task_000003",
            "task_name": "异常检测",
            "category": "anomaly_detection",
            "dependencies": ["task_000002"]
        },
        {
            "task_id": "task_000004",
            "task_name": "违规推理",
            "category": "violation_reasoning",
            "dependencies": ["task_000003"]
        }
    ]

    result = create_task_flow(test_tasks)
    print(json.dumps(result, indent=2, ensure_ascii=False))
