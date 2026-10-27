#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则推理核心技能包

规则推理子智能体
包含四个核心模块：
1. regulation_matcher - 法规规则匹配模块
2. process_validator - 工艺机理校验模块
3. expert_reasoner - 专家经验推理模块
4. violation_generator - 违规结论生成模块
"""

from .regulation_matcher import RegulationMatcher
from .process_validator import ProcessValidator
from .expert_reasoner import ExpertReasoner
from .violation_generator import ViolationGenerator


__version__ = "1.0.0"


def run_rule_reasoning(task: dict) -> dict:
    """
    执行规则推理任务

    Args:
        task: 任务字典，包含：
            - task_id: 任务ID
            - data: 输入数据
            - anomalies: 异常列表（来自anomaly-detection-agent）
            - correlation_results: 相关性分析结果（来自anomaly-detection-agent）
            - trend_results: 趋势分析结果（来自anomaly-detection-agent）
            - config: 配置参数

    Returns:
        结果字典，包含：
            - task_id: 任务ID
            - agent: "rule-reasoning-agent"
            - status: "success" 或 "error"
            - result: 规则推理结果
    """
    try:
        # 解析任务
        task_id = task.get("task_id", "")
        data = task.get("data")
        anomalies = task.get("anomalies", [])
        correlation_results = task.get("correlation_results", {})
        trend_results = task.get("trend_results", {})
        config = task.get("config", {})

        # 1. 法规规则匹配
        regulation_matcher = RegulationMatcher()
        regulation_result = regulation_matcher.match(anomalies, data)

        # 2. 工艺机理校验
        process_validator = ProcessValidator()
        process_result = process_validator.validate(
            anomalies, correlation_results, trend_results, data
        )

        # 3. 专家经验推理
        expert_reasoner = ExpertReasoner()
        expert_result = expert_reasoner.reason(
            anomalies, regulation_result, process_result
        )

        # 4. 违规结论生成
        violation_generator = ViolationGenerator()
        violation_result = violation_generator.generate(
            anomalies, regulation_result, process_result, expert_result, data
        )

        # 组合结果
        result = {
            "regulation_check": regulation_result,
            "process_validation": process_result,
            "expert_reasoning": expert_result,
            "violation_conclusion": violation_result
        }

        return {
            "task_id": task_id,
            "agent": "rule-reasoning-agent",
            "status": "success",
            "result": result
        }

    except Exception as e:
        import logging
        logging.error(f"[RULE_REASONING] 执行失败: {e}")
        return {
            "task_id": task.get("task_id", ""),
            "agent": "rule-reasoning-agent",
            "status": "error",
            "error": str(e)
        }


__all__ = [
    "RegulationMatcher",
    "ProcessValidator",
    "ExpertReasoner",
    "ViolationGenerator",
    "run_rule_reasoning"
]
