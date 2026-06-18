#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务结构化脚本
功能：将主智能体的调度决策转换为标准化的任务格式

说明：此脚本由主智能体（大模型）调用，用于将自然形式的任务需求
转换为结构化的任务定义，便于后续的任务流生成和资源匹配。
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """任务类别"""
    # 数据治理相关
    DATA_ACQUISITION = "data_acquisition"       # 数据获取
    DATA_GOVERNANCE = "data_governance"         # 数据治理
    DATA_CLEANING = "data_cleaning"             # 数据清洗
    TIME_ALIGNMENT = "time_alignment"           # 时序对齐
    STANDARDIZATION = "standardization"         # 标准化

    # 特征分析相关
    FEATURE_ANALYSIS = "feature_analysis"       # 特征分析
    FEATURE_EXTRACTION = "feature_extraction"   # 特征提取
    CORRELATION_ANALYSIS = "correlation_analysis"  # 相关性分析
    TREND_ANALYSIS = "trend_analysis"           # 趋势分析

    # 异常检测相关
    ANOMALY_DETECTION = "anomaly_detection"     # 异常检测
    PATTERN_RECOGNITION = "pattern_recognition" # 模式识别
    VIOLATION_DETECTION = "violation_detection" # 违规检测

    # 规则推理相关
    VIOLATION_REASONING = "violation_reasoning" # 违规推理
    RULE_REASONING = "rule_reasoning"           # 规则推理
    REGULATION_MATCH = "regulation_match"       # 法规匹配
    EXPERT_REASONING = "expert_reasoning"       # 专家推理

    # 综合分析
    REPORT_GENERATION = "report_generation"     # 报告生成
    DUAL_STREAM_ANALYSIS = "dual_stream_analysis"  # 双数据流分析


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0   # 紧急
    HIGH = 1       # 高
    MEDIUM = 2     # 中
    LOW = 3        # 低


@dataclass
class TaskParameter:
    """任务参数"""
    name: str
    value: Any
    required: bool = True
    description: str = ""


@dataclass
class StructuredTask:
    """结构化任务"""
    task_id: str                           # 任务唯一标识
    task_name: str                         # 任务名称
    category: TaskCategory                 # 任务类别
    priority: TaskPriority                 # 任务优先级
    description: str                       # 任务描述

    # 输入输出定义
    input_params: List[TaskParameter] = field(default_factory=list)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    # 执行约束
    timeout_seconds: int = 300             # 超时时间（秒）
    retry_count: int = 3                   # 重试次数
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "category": self.category.value,
            "priority": self.priority.value,
            "description": self.description,
            "input_params": [
                {"name": p.name, "value": p.value, "required": p.required, "description": p.description}
                for p in self.input_params
            ],
            "output_schema": self.output_schema,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "dependencies": self.dependencies,
            "metadata": self.metadata
        }


class TaskStructuringError(Exception):
    """任务结构化异常"""
    pass


class TaskStructuringModule:
    """任务结构化模块"""

    def __init__(self):
        """初始化任务结构化模块"""
        self.name = "任务结构化模块"
        self.version = "2.0.0"
        self.task_counter = 0

        # 任务类别到子智能体的映射
        self.category_agent_mapping = {
            TaskCategory.DATA_ACQUISITION: "multi-dimensional-data-perception-agent",
            TaskCategory.FEATURE_ANALYSIS: "anomaly-detection-agent",  # 已迁移到异常检测智能体
            TaskCategory.ANOMALY_DETECTION: "anomaly-detection-agent",
            TaskCategory.VIOLATION_REASONING: "rule-reasoning-agent",
            TaskCategory.ALERT_RESPONSE: "disposition-execution-agent",  # 新增
            TaskCategory.REPORT_GENERATION: "disposition-execution-agent",  # 更新：处置执行智能体
            TaskCategory.DUAL_STREAM_ANALYSIS: "orchestrator-core"
        }

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def generate_task_id(self) -> str:
        """生成任务ID"""
        self.task_counter += 1
        return f"task_{self.task_counter:06d}"

    def structure_task(self, task_request: Dict[str, Any]) -> StructuredTask:
        """
        将任务请求结构化

        Args:
            task_request: 任务请求字典，包含：
                - task_name: 任务名称
                - category: 任务类别
                - description: 任务描述
                - input_params: 输入参数列表
                - priority: 优先级（可选）
                - timeout: 超时时间（可选）
                - dependencies: 依赖任务ID列表（可选）

        Returns:
            StructuredTask: 结构化任务
        """
        try:
            # 解析任务类别
            category_str = task_request.get("category", "data_acquisition")
            category = TaskCategory(category_str) if isinstance(category_str, str) else category

            # 解析优先级
            priority_str = task_request.get("priority", "medium")
            priority = TaskPriority[priority_str.upper()] if isinstance(priority_str, str) else TaskPriority.MEDIUM

            # 解析输入参数
            input_params = []
            for param in task_request.get("input_params", []):
                input_params.append(TaskParameter(
                    name=param["name"],
                    value=param.get("value"),
                    required=param.get("required", True),
                    description=param.get("description", "")
                ))

            # 创建结构化任务
            task = StructuredTask(
                task_id=self.generate_task_id(),
                task_name=task_request["task_name"],
                category=category,
                priority=priority,
                description=task_request.get("description", ""),
                input_params=input_params,
                output_schema=task_request.get("output_schema", {}),
                timeout_seconds=task_request.get("timeout", 300),
                retry_count=task_request.get("retry_count", 3),
                dependencies=task_request.get("dependencies", []),
                metadata=task_request.get("metadata", {})
            )

            logger.info(f"[STRUCTURE] Task structured: {task.task_id} - {task.task_name}")
            return task

        except KeyError as e:
            raise TaskStructuringError(f"Missing required field in task request: {e}")
        except ValueError as e:
            raise TaskStructuringError(f"Invalid value in task request: {e}")

    def structure_batch_tasks(self, task_requests: List[Dict[str, Any]]) -> List[StructuredTask]:
        """
        批量结构化任务

        Args:
            task_requests: 任务请求列表

        Returns:
            List[StructuredTask]: 结构化任务列表
        """
        tasks = []
        for request in task_requests:
            try:
                task = self.structure_task(request)
                tasks.append(task)
            except TaskStructuringError as e:
                logger.error(f"[ERROR] Failed to structure task {request.get('task_name', 'unknown')}: {e}")

        return tasks

    def get_target_agent(self, task: StructuredTask) -> str:
        """
        获取任务的目标子智能体

        Args:
            task: 结构化任务

        Returns:
            str: 子智能体ID
        """
        return self.category_agent_mapping.get(task.category, "orchestrator-core")

    def validate_task(self, task: StructuredTask) -> Tuple[bool, List[str]]:
        """
        验证结构化任务的有效性

        Args:
            task: 结构化任务

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 检查必需参数
        if not task.task_name:
            errors.append("Task name is required")

        # 检查输入参数的必需值
        for param in task.input_params:
            if param.required and (param.value is None or param.value == ""):
                errors.append(f"Required parameter '{param.name}' is missing")

        # 检查超时时间
        if task.timeout_seconds <= 0:
            errors.append("Timeout must be positive")

        # 检查重试次数
        if task.retry_count < 0:
            errors.append("Retry count cannot be negative")

        is_valid = len(errors) == 0
        return is_valid, errors

    def estimate_task_complexity(self, task: StructuredTask) -> str:
        """
        估算任务复杂度

        Args:
            task: 结构化任务

        Returns:
            str: 复杂度等级（simple, medium, complex）
        """
        # 基于输入参数数量和依赖关系估算
        param_count = len(task.input_params)
        dep_count = len(task.dependencies)

        if param_count <= 3 and dep_count == 0:
            return "simple"
        elif param_count <= 7 and dep_count <= 2:
            return "medium"
        else:
            return "complex"


# 便捷函数，供主智能体调用
def structure_task(task_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    结构化单个任务（便捷函数）

    Args:
        task_request: 任务请求字典

    Returns:
        Dict: 结构化任务的字典表示
    """
    module = TaskStructuringModule()
    task = module.structure_task(task_request)
    return task.to_dict()


def structure_batch_tasks(task_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量结构化任务（便捷函数）

    Args:
        task_requests: 任务请求列表

    Returns:
        List[Dict]: 结构化任务字典列表
    """
    module = TaskStructuringModule()
    tasks = module.structure_batch_tasks(task_requests)
    return [task.to_dict() for task in tasks]


if __name__ == "__main__":
    # 测试代码
    test_request = {
        "task_name": "获取出水口监测数据",
        "category": "data_acquisition",
        "description": "获取最近24小时出水口pH、COD、氨氮监测数据",
        "priority": "high",
        "input_params": [
            {"name": "monitoring_point", "value": "出水口", "required": True},
            {"name": "indicators", "value": ["pH", "COD", "NH3-N"], "required": True},
            {"name": "time_range", "value": "24h", "required": True}
        ],
        "timeout": 60
    }

    result = structure_task(test_request)
    print(json.dumps(result, indent=2, ensure_ascii=False))
