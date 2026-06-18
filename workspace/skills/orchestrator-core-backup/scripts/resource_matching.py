#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源匹配脚本
功能：将任务匹配到合适的子智能体，检查资源可用性

说明：此脚本由主智能体（大模型）调用，用于根据任务特征
匹配到最合适的子智能体，并检查子智能体的可用性和负载情况。
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TriggerSource(Enum):
    """触发信号来源"""
    NATURAL_LANGUAGE = "natural_language"  # 自然语言指令
    REALTIME_MONITORING = "realtime_monitoring"  # 实时监测触发


class AgentStatus(Enum):
    """子智能体状态"""
    AVAILABLE = "available"       # 可用
    BUSY = "busy"                 # 忙碌
    UNAVAILABLE = "unavailable"   # 不可用
    DEGRADED = "degraded"         # 降级服务


class MatchPriority(Enum):
    """匹配优先级"""
    REQUIRED = 0     # 必需能力
    PREFERRED = 1    # 优先能力
    OPTIONAL = 2     # 可选能力


@dataclass
class SchedulingDecision:
    """
    调度决策结果（专利：调度决策模块）

    根据专利要求的优先级计算公式确定任务执行顺序：
    P = wp × priority + wt × wait_time + wd × critical_path

    其中：
    - wp = 0.6（优先级权重）
    - wt = 0.2（等待时间权重）
    - wd = 0.2（关键路径权重）
    """
    task_id: str
    priority_score: float        # 综合优先级分数 [0, 10]
    execution_order: int         # 执行顺序
    is_realtime: bool = False    # 是否为实时监测任务

    # 分解的优先级分量
    priority_component: float = 0.0    # 任务优先级分量
    wait_time_component: float = 0.0   # 等待时间分量
    critical_path_component: float = 0.0  # 关键路径分量

    # 调度元数据
    scheduled_at: str = ""
    estimated_start: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "priority_score": round(self.priority_score, 3),
            "execution_order": self.execution_order,
            "is_realtime": self.is_realtime,
            "priority_component": round(self.priority_component, 3),
            "wait_time_component": round(self.wait_time_component, 3),
            "critical_path_component": round(self.critical_path_component, 3),
            "scheduled_at": self.scheduled_at,
            "estimated_start": self.estimated_start
        }


class SchedulingDecisionModule:
    """
    调度决策模块（专利：调度决策模块）

    功能：
    1. 根据优先级计算公式确定任务执行顺序
    2. 识别实时监测任务并赋予最高优先级（P=10）
    3. 生成全局调度策略
    """

    # 专利参数
    WP = 0.6  # 优先级权重
    WT = 0.2  # 等待时间权重
    WD = 0.2  # 关键路径权重

    # 实时监测任务最高优先级
    REALTIME_PRIORITY = 10.0

    def __init__(self):
        """初始化调度决策模块"""
        self.name = "调度决策模块"
        self.version = "2.1.0"
        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 专利参数: wp={self.WP}, wt={self.WT}, wd={self.WD}")

    def calculate_task_priority(
        self,
        task: Dict[str, Any],
        wait_time_seconds: float = 0.0,
        is_critical_path: bool = False,
        trigger_source: str = "natural_language"
    ) -> SchedulingDecision:
        """
        计算任务优先级（专利核心算法）

        公式：P = wp × priority + wt × wait_time + wd × critical_path

        Args:
            task: 结构化任务，包含priority字段
            wait_time_seconds: 任务已等待时间（秒）
            is_critical_path: 是否在关键路径上
            trigger_source: 触发信号来源

        Returns:
            SchedulingDecision: 调度决策结果
        """
        task_id = task.get("task_id", "")
        task_priority = task.get("priority", "MEDIUM")

        # 检查是否为实时监测任务
        is_realtime = (trigger_source == "realtime_monitoring" or
                       task.get("metadata", {}).get("trigger_source") == "realtime_monitoring")

        # 实时监测任务直接赋予最高优先级
        if is_realtime:
            logger.info(f"[SCHEDULE] Task {task_id} is realtime monitoring, P={self.REALTIME_PRIORITY}")
            return SchedulingDecision(
                task_id=task_id,
                priority_score=self.REALTIME_PRIORITY,
                execution_order=0,  # 最高优先级，最先执行
                is_realtime=True,
                priority_component=1.0,
                wait_time_component=0.0,
                critical_path_component=0.0,
                scheduled_at=datetime.now().isoformat(),
                estimated_start=datetime.now().isoformat()
            )

        # 1. 计算优先级分量 (wp × priority)
        # 将枚举优先级转换为数值：CRITICAL=0→1.0, HIGH=1→0.67, MEDIUM=2→0.33, LOW=3→0.0
        priority_map = {"CRITICAL": 1.0, "HIGH": 0.67, "MEDIUM": 0.33, "LOW": 0.0}
        priority_score = priority_map.get(str(task_priority).upper(), 0.33)
        priority_component = self.WP * priority_score

        # 2. 计算等待时间分量 (wt × wait_time)
        # 等待时间标准化：1小时为满分1.0
        wait_time_score = min(wait_time_seconds / 3600.0, 1.0)
        wait_time_component = self.WT * wait_time_score

        # 3. 计算关键路径分量 (wd × critical_path)
        critical_path_score = 1.0 if is_critical_path else 0.0
        critical_path_component = self.WD * critical_path_score

        # 综合优先级分数 [0, 1]
        total_priority = (
            priority_component +
            wait_time_component +
            critical_path_component
        )

        # 映射到 [0, 10] 范围便于展示
        priority_score_display = total_priority * 10

        now = datetime.now()
        estimated_start = now + timedelta(seconds=wait_time_seconds)

        decision = SchedulingDecision(
            task_id=task_id,
            priority_score=priority_score_display,
            execution_order=0,  # 需要全局排序后确定
            is_realtime=False,
            priority_component=priority_component,
            wait_time_component=wait_time_component,
            critical_path_component=critical_path_component,
            scheduled_at=now.isoformat(),
            estimated_start=estimated_start.isoformat()
        )

        logger.info(
            f"[SCHEDULE] Task {task_id}: P={priority_score_display:.2f} "
            f"(p={priority_component:.2f}, t={wait_time_component:.2f}, d={critical_path_component:.2f})"
        )

        return decision

    def generate_scheduling_strategy(
        self,
        tasks: List[Dict[str, Any]],
        task_waiting_times: Dict[str, float] = None,
        critical_path_tasks: List[str] = None
    ) -> Dict[str, Any]:
        """
        生成全局调度策略（专利：调度决策模块）

        根据优先级计算公式确定任务执行顺序，生成包含子任务序列、
        目标子智能体分配的结构化调度策略

        Args:
            tasks: 结构化任务列表
            task_waiting_times: 任务等待时间映射 {task_id: seconds}
            critical_path_tasks: 关键路径任务ID列表

        Returns:
            Dict: 调度策略
        """
        if task_waiting_times is None:
            task_waiting_times = {}
        if critical_path_tasks is None:
            critical_path_tasks = []

        logger.info(f"[SCHEDULE] Generating strategy for {len(tasks)} tasks")

        # 计算每个任务的优先级
        decisions = []
        for task in tasks:
            task_id = task.get("task_id")
            wait_time = task_waiting_times.get(task_id, 0.0)
            is_critical = task_id in critical_path_tasks
            trigger_source = task.get("metadata", {}).get("trigger_source", "natural_language")

            decision = self.calculate_task_priority(
                task=task,
                wait_time_seconds=wait_time,
                is_critical_path=is_critical,
                trigger_source=trigger_source
            )
            decisions.append(decision)

        # 按优先级排序（实时任务优先，然后按分数降序）
        decisions.sort(key=lambda d: (
            -1 if d.is_realtime else 0,  # 实时任务排最前
            -d.priority_score  # 分数高的排前面
        ))

        # 分配执行顺序
        for idx, decision in enumerate(decisions):
            decision.execution_order = idx

        # 生成调度策略
        strategy = {
            "strategy_id": f"strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "total_tasks": len(tasks),
            "execution_order": [
                {
                    "task_id": d.task_id,
                    "order": d.execution_order,
                    "priority_score": d.priority_score,
                    "is_realtime": d.is_realtime,
                    "estimated_start": d.estimated_start
                }
                for d in decisions
            ],
            "realtime_task_count": sum(1 for d in decisions if d.is_realtime),
            "scheduling_algorithm": "patent_formula",
            "formula": "P = wp×priority + wt×wait_time + wd×critical_path",
            "parameters": {
                "wp": self.WP,
                "wt": self.WT,
                "wd": self.WD
            },
            "generated_at": datetime.now().isoformat()
        }

        logger.info(
            f"[SCHEDULE] Strategy generated: {strategy['realtime_task_count']} realtime, "
            f"{len(tasks) - strategy['realtime_task_count']} normal tasks"
        )

        return strategy

    def compare_priorities(self, decision1: SchedulingDecision, decision2: SchedulingDecision) -> str:
        """
        比较两个任务的优先级

        Args:
            decision1: 任务1的调度决策
            decision2: 任务2的调度决策

        Returns:
            str: "task1" if task1 has higher priority, "task2" if task2 has higher priority, "equal" if same
        """
        # 实时任务优先
        if decision1.is_realtime and not decision2.is_realtime:
            return "task1"
        if decision2.is_realtime and not decision1.is_realtime:
            return "task2"

        # 比较分数
        if decision1.priority_score > decision2.priority_score:
            return "task1"
        elif decision2.priority_score > decision1.priority_score:
            return "task2"
        else:
            return "equal"


@dataclass
class AgentCapability:
    """子智能体能力描述"""
    agent_id: str
    agent_name: str
    capabilities: List[str]
    status: AgentStatus = AgentStatus.AVAILABLE
    current_load: float = 0.0    # 当前负载（0-1）
    max_concurrent: int = 5      # 最大并发任务数
    timeout: int = 60            # 默认超时时间（秒）

    # 性能指标
    avg_response_time: float = 0.0  # 平均响应时间（秒）
    success_rate: float = 1.0       # 成功率
    last_heartbeat: str = ""        # 最后心跳时间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "current_load": self.current_load,
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "avg_response_time": self.avg_response_time,
            "success_rate": self.success_rate,
            "last_heartbeat": self.last_heartbeat
        }


@dataclass
class ResourceAllocation:
    """资源分配结果"""
    task_id: str
    agent_id: str
    agent_name: str
    match_score: float           # 匹配分数（0-1）
    match_reasons: List[str]     # 匹配原因

    # 分配信息
    allocated_at: str = ""
    estimated_start: str = ""
    estimated_duration: int = 0

    # 替代方案
    fallback_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "match_score": self.match_score,
            "match_reasons": self.match_reasons,
            "allocated_at": self.allocated_at,
            "estimated_start": self.estimated_start,
            "estimated_duration": self.estimated_duration,
            "fallback_agents": self.fallback_agents
        }


class ResourceMatchingError(Exception):
    """资源匹配异常"""
    pass


class NoAvailableAgentError(ResourceMatchingError):
    """无可用子智能体异常"""
    pass


class ResourceMatchingModule:
    """资源匹配模块"""

    def __init__(self):
        """初始化资源匹配模块"""
        self.name = "资源匹配模块"
        self.version = "2.0.0"

        # 注册的子智能体（基于新架构的4个子智能体）
        self.registered_agents: Dict[str, AgentCapability] = {
            "multi-dimensional-data-perception-agent": AgentCapability(
                agent_id="multi-dimensional-data-perception-agent",
                agent_name="多维数据感知子智能体",
                capabilities=[
                    "multi_source_data_acquisition",
                    "data_decomposition",
                    "time_alignment",
                    "data_cleaning",
                    "standardization"
                ],
                timeout=30
            ),
            "anomaly-detection-agent": AgentCapability(
                agent_id="anomaly-detection-agent",
                agent_name="异常检测子智能体",
                capabilities=[
                    "operator_adapter",
                    "anomaly_scorer",
                    "pattern_recognizer",
                    "violation_detector",
                    "confidence_evaluator",
                    "time_series_features",  # 从feature-analysis迁移
                    "correlation_analysis",  # 从feature-analysis迁移
                    "trend_analysis"  # 从feature-analysis迁移
                ],
                timeout=60
            ),
            "rule-reasoning-agent": AgentCapability(
                agent_id="rule-reasoning-agent",
                agent_name="规则推理子智能体",
                capabilities=[
                    "regulation_matcher",
                    "process_validator",
                    "expert_reasoning",
                    "violation_generator"
                ],
                timeout=30
            ),
            "disposition-execution-agent": AgentCapability(
                agent_id="disposition-execution-agent",
                agent_name="研判预警与处置执行子智能体",
                capabilities=[
                    "consensus_fusion",
                    "alert_classification",
                    "work_order_generation",
                    "action_execution",
                    "report_generation"
                ],
                timeout=45
            )
        }

        # 任务类别到能力的映射（扩展版）
        self.category_capability_mapping = {
            # 数据治理相关
            "data_acquisition": ["multi_source_data_acquisition", "time_alignment"],
            "data_governance": ["multi_source_data_acquisition", "time_alignment", "data_cleaning"],
            "data_cleaning": ["data_cleaning"],
            "time_alignment": ["time_alignment"],
            "standardization": ["standardization"],

            # 特征分析相关
            "feature_analysis": ["time_series_features", "correlation_analysis"],
            "feature_extraction": ["time_series_features"],
            "correlation_analysis": ["correlation_analysis"],
            "trend_analysis": ["trend_analysis"],

            # 异常检测相关
            "anomaly_detection": ["operator_adapter", "anomaly_scorer", "pattern_recognizer"],
            "pattern_recognition": ["pattern_recognizer"],
            "violation_detection": ["violation_detector"],

            # 规则推理相关
            "violation_reasoning": ["regulation_matcher", "process_validator", "expert_reasoner"],
            "rule_reasoning": ["regulation_matcher", "process_validator", "expert_reasoner"],
            "regulation_match": ["regulation_matcher"],
            "expert_reasoning": ["expert_reasoner"],

            # 综合分析
            "time_series_features": ["time_series_features", "correlation_analysis", "feature_fusion"],
            "consensus_fusion": ["consensus_fusion"],
            "alert_classification": ["alert_classification"],
            "work_order_generation": ["work_order_generation"],
            "action_execution": ["action_execution"],
            "report_generation": ["report_generation"]
        }

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] Registered {len(self.registered_agents)} agents")

    def update_agent_status(self, agent_id: str, status: AgentStatus,
                           current_load: float = 0.0, last_heartbeat: str = ""):
        """
        更新子智能体状态

        Args:
            agent_id: 子智能体ID
            status: 状态
            current_load: 当前负载
            last_heartbeat: 最后心跳时间
        """
        if agent_id in self.registered_agents:
            self.registered_agents[agent_id].status = status
            self.registered_agents[agent_id].current_load = current_load
            if last_heartbeat:
                self.registered_agents[agent_id].last_heartbeat = last_heartbeat
            logger.info(f"[UPDATE] Agent {agent_id} status: {status.value}, load: {current_load}")

    def match_task_to_agent(self, task: Dict[str, Any]) -> ResourceAllocation:
        """
        将任务匹配到最合适的子智能体

        Args:
            task: 结构化任务

        Returns:
            ResourceAllocation: 资源分配结果
        """
        task_id = task["task_id"]
        category = task.get("category", "")

        # 获取任务所需能力
        required_caps = self.category_capability_mapping.get(category, [])

        # 计算每个子智能体的匹配分数
        candidates = []
        for agent_id, agent in self.registered_agents.items():
            if agent.status == AgentStatus.UNAVAILABLE:
                continue

            score, reasons = self._calculate_match_score(task, agent, required_caps)
            if score > 0:
                candidates.append((agent_id, score, reasons))

        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates:
            raise NoAvailableAgentError(f"No available agent for task {task_id}")

        # 选择最佳匹配
        best_agent_id = candidates[0][0]
        best_agent = self.registered_agents[best_agent_id]

        # 获取备选方案
        fallback_agents = [cid for cid, _, _ in candidates[1:4]]  # 最多3个备选

        now = datetime.now().isoformat()
        allocation = ResourceAllocation(
            task_id=task_id,
            agent_id=best_agent_id,
            agent_name=best_agent.agent_name,
            match_score=candidates[0][1],
            match_reasons=candidates[0][2],
            allocated_at=now,
            estimated_start=now,
            estimated_duration=task.get("timeout_seconds", best_agent.timeout),
            fallback_agents=fallback_agents
        )

        logger.info(f"[MATCH] Task {task_id} -> {best_agent_id} (score: {candidates[0][1]:.2f})")
        return allocation

    def _calculate_match_score(self, task: Dict[str, Any],
                              agent: AgentCapability,
                              required_caps: List[str]) -> Tuple[float, List[str]]:
        """计算匹配分数"""
        score = 0.0
        reasons = []

        # 1. 能力匹配（60%权重）
        capability_score = self._calculate_capability_match(required_caps, agent.capabilities)
        score += capability_score * 0.6
        if capability_score > 0:
            reasons.append(f"能力匹配度: {capability_score:.2f}")

        # 2. 状态可用性（20%权重）
        availability_score = 0.0
        if agent.status == AgentStatus.AVAILABLE:
            availability_score = 1.0
            reasons.append("状态: 可用")
        elif agent.status == AgentStatus.DEGRADED:
            availability_score = 0.5
            reasons.append("状态: 降级服务")
        else:
            availability_score = 0.0
        score += availability_score * 0.2

        # 3. 负载情况（20%权重）
        load_score = max(0, 1.0 - agent.current_load)
        score += load_score * 0.2
        if load_score > 0.5:
            reasons.append(f"负载: {agent.current_load*100:.0f}%")

        return score, reasons

    def _calculate_capability_match(self, required: List[str], available: List[str]) -> float:
        """计算能力匹配度"""
        if not required:
            return 0.5  # 无明确需求，给予中等分数

        matched = sum(1 for cap in required if cap in available)
        return matched / len(required) if required else 0.0

    def batch_match_tasks(self, tasks: List[Dict[str, Any]]) -> List[ResourceAllocation]:
        """
        批量匹配任务

        Args:
            tasks: 任务列表

        Returns:
            List[ResourceAllocation]: 资源分配结果列表
        """
        allocations = []
        for task in tasks:
            try:
                allocation = self.match_task_to_agent(task)
                allocations.append(allocation)
            except NoAvailableAgentError as e:
                logger.error(f"[ERROR] {e}")
                # 可以创建一个失败的分配记录
                allocations.append(ResourceAllocation(
                    task_id=task["task_id"],
                    agent_id="",
                    agent_name="无可用子智能体",
                    match_score=0.0,
                    match_reasons=["所有相关子智能体均不可用"]
                ))
        return allocations

    def get_agent_info(self, agent_id: str) -> Optional[AgentCapability]:
        """
        获取子智能体信息

        Args:
            agent_id: 子智能体ID

        Returns:
            Optional[AgentCapability]: 子智能体能力信息
        """
        return self.registered_agents.get(agent_id)

    def get_all_agents(self) -> List[AgentCapability]:
        """获取所有注册的子智能体"""
        return list(self.registered_agents.values())

    def get_available_agents(self) -> List[AgentCapability]:
        """获取当前可用的子智能体"""
        return [
            agent for agent in self.registered_agents.values()
            if agent.status == AgentStatus.AVAILABLE
        ]

    def check_agent_health(self, agent_id: str) -> bool:
        """
        检查子智能体健康状态

        Args:
            agent_id: 子智能体ID

        Returns:
            bool: 是否健康
        """
        agent = self.registered_agents.get(agent_id)
        if not agent:
            return False

        # 基于状态、负载、成功率判断
        is_healthy = (
            agent.status in [AgentStatus.AVAILABLE, AgentStatus.DEGRADED] and
            agent.current_load < 0.9 and
            agent.success_rate > 0.8
        )
        return is_healthy

    def simulate_agent_failure(self, agent_id: str):
        """
        模拟子智能体故障（用于测试）

        Args:
            agent_id: 子智能体ID
        """
        self.update_agent_status(agent_id, AgentStatus.UNAVAILABLE)
        logger.warning(f"[SIMULATE] Agent {agent_id} marked as UNAVAILABLE")


# 便捷函数，供主智能体调用
def match_task_to_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    匹配任务到子智能体（便捷函数）

    Args:
        task: 结构化任务

    Returns:
        Dict: 资源分配结果的字典表示
    """
    module = ResourceMatchingModule()
    allocation = module.match_task_to_agent(task)
    return allocation.to_dict()


def batch_match_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量匹配任务（便捷函数）

    Args:
        tasks: 任务列表

    Returns:
        List[Dict]: 资源分配结果字典列表
    """
    module = ResourceMatchingModule()
    allocations = module.batch_match_tasks(tasks)
    return [a.to_dict() for a in allocations]


def get_available_agents() -> List[Dict[str, Any]]:
    """
    获取可用子智能体列表（便捷函数）

    Returns:
        List[Dict]: 子智能体信息字典列表
    """
    module = ResourceMatchingModule()
    agents = module.get_available_agents()
    return [agent.to_dict() for agent in agents]


# ========== 调度决策便捷函数（专利：调度决策模块） ==========

def calculate_task_priority(
    task: Dict[str, Any],
    wait_time_seconds: float = 0.0,
    is_critical_path: bool = False,
    trigger_source: str = "natural_language"
) -> Dict[str, Any]:
    """
    计算任务优先级（专利核心算法）

    公式：P = wp × priority + wt × wait_time + wd × critical_path
    参数：wp=0.6, wt=0.2, wd=0.2

    Args:
        task: 结构化任务，包含priority字段
        wait_time_seconds: 任务已等待时间（秒）
        is_critical_path: 是否在关键路径上
        trigger_source: 触发信号来源 ("natural_language" 或 "realtime_monitoring")

    Returns:
        Dict: 调度决策结果的字典表示

    Example:
        >>> task = {"task_id": "task_001", "priority": "HIGH"}
        >>> decision = calculate_task_priority(task)
        >>> print(f"Priority score: {decision['priority_score']}")
    """
    module = SchedulingDecisionModule()
    decision = module.calculate_task_priority(
        task=task,
        wait_time_seconds=wait_time_seconds,
        is_critical_path=is_critical_path,
        trigger_source=trigger_source
    )
    return decision.to_dict()


def generate_scheduling_strategy(
    tasks: List[Dict[str, Any]],
    task_waiting_times: Dict[str, float] = None,
    critical_path_tasks: List[str] = None
) -> Dict[str, Any]:
    """
    生成全局调度策略（专利：调度决策模块）

    根据优先级计算公式确定任务执行顺序，生成包含子任务序列、
    目标子智能体分配的结构化调度策略

    Args:
        tasks: 结构化任务列表
        task_waiting_times: 任务等待时间映射 {task_id: seconds}
        critical_path_tasks: 关键路径任务ID列表

    Returns:
        Dict: 调度策略

    Example:
        >>> tasks = [
        ...     {"task_id": "task_001", "priority": "CRITICAL"},
        ...     {"task_id": "task_002", "priority": "MEDIUM"}
        ... ]
        >>> strategy = generate_scheduling_strategy(tasks)
        >>> print(f"Execution order: {[t['task_id'] for t in strategy['execution_order']]}")
    """
    module = SchedulingDecisionModule()
    return module.generate_scheduling_strategy(
        tasks=tasks,
        task_waiting_times=task_waiting_times,
        critical_path_tasks=critical_path_tasks
    )


def compare_task_priorities(
    task1: Dict[str, Any],
    task2: Dict[str, Any],
    wait_time1: float = 0.0,
    wait_time2: float = 0.0
) -> str:
    """
    比较两个任务的优先级

    Args:
        task1: 任务1
        task2: 任务2
        wait_time1: 任务1的等待时间（秒）
        wait_time2: 任务2的等待时间（秒）

    Returns:
        str: "task1" if task1 has higher priority, "task2" if task2 has higher priority, "equal" if same
    """
    module = SchedulingDecisionModule()
    decision1 = module.calculate_task_priority(task1, wait_time1)
    decision2 = module.calculate_task_priority(task2, wait_time2)
    return module.compare_priorities(decision1, decision2)


if __name__ == "__main__":
    import json

    # 测试代码
    print("=" * 80)
    print("调度决策模块测试（专利算法）")
    print("=" * 80)

    # 测试1: 计算单个任务优先级
    print("\n[测试1] 单个任务优先级计算")
    test_task = {
        "task_id": "task_000001",
        "task_name": "数据获取与治理",
        "category": "data_acquisition",
        "priority": "HIGH",
        "timeout_seconds": 60
    }

    decision = calculate_task_priority(test_task, wait_time_seconds=1800)
    print(f"Task: {test_task['task_id']}")
    print(f"  Priority Score: {decision['priority_score']:.2f}/10")
    print(f"  Components: p={decision['priority_component']:.2f}, "
          f"t={decision['wait_time_component']:.2f}, d={decision['critical_path_component']:.2f}")

    # 测试2: 实时监测任务优先级
    print("\n[测试2] 实时监测任务优先级")
    realtime_task = {
        "task_id": "task_realtime_001",
        "task_name": "COD超限告警",
        "category": "anomaly_detection",
        "priority": "CRITICAL",
        "metadata": {"trigger_source": "realtime_monitoring"}
    }

    realtime_decision = calculate_task_priority(realtime_task)
    print(f"Task: {realtime_task['task_id']}")
    print(f"  Priority Score: {realtime_decision['priority_score']:.2f}/10")
    print(f"  Is Realtime: {realtime_decision['is_realtime']}")

    # 测试3: 多任务调度策略
    print("\n[测试3] 多任务调度策略生成")
    test_tasks = [
        {"task_id": "task_001", "priority": "HIGH", "category": "data_acquisition"},
        {"task_id": "task_002", "priority": "MEDIUM", "category": "feature_analysis"},
        {"task_id": "task_003", "priority": "CRITICAL", "category": "anomaly_detection",
         "metadata": {"trigger_source": "realtime_monitoring"}},
        {"task_id": "task_004", "priority": "LOW", "category": "violation_reasoning"}
    ]

    waiting_times = {
        "task_001": 600,   # 等待10分钟
        "task_002": 1800,  # 等待30分钟
        "task_004": 3600   # 等待1小时
    }

    critical_path = ["task_001", "task_003"]

    strategy = generate_scheduling_strategy(test_tasks, waiting_times, critical_path)
    print(f"\n调度策略: {strategy['strategy_id']}")
    print(f"算法: {strategy['scheduling_algorithm']}")
    print(f"公式: {strategy['formula']}")
    print(f"参数: wp={strategy['parameters']['wp']}, "
          f"wt={strategy['parameters']['wt']}, wd={strategy['parameters']['wd']}")
    print(f"\n执行顺序:")
    for item in strategy['execution_order']:
        prefix = "[实时]" if item['is_realtime'] else "[普通]"
        print(f"  {prefix} Order {item['order']}: {item['task_id']} "
              f"(P={item['priority_score']:.2f})")

    # 测试4: 资源匹配
    print("\n[测试4] 资源匹配测试")
    match_result = match_task_to_agent(test_task)
    print(f"Task: {test_task['task_id']}")
    print(f"  Assigned Agent: {match_result['agent_name']}")
    print(f"  Match Score: {match_result['match_score']:.2f}")
    print(f"  Reasons: {', '.join(match_result['match_reasons'])}")

    print("\n" + "=" * 80)
