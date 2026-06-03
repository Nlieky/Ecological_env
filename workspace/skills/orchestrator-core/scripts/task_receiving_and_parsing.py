#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务接收与解析脚本
功能：接收实时监测数据，由大模型解析任务意图并创建结构化任务

说明：此脚本由Flask中间件调用，接收实时数据流，由大模型读取主智能体身份后
解析任务意图，创建符合orchestrator-core规范的结构化任务。
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# 添加项目路径 - 尝试多种方式找到项目根目录
possible_roots = [
    Path(__file__).parent.parent.parent.parent.parent.parent,
    Path.cwd().parent,
    Path(__file__).resolve().parent.parent.parent.parent.parent,
]

for root in possible_roots:
    if (root / "workspace").exists() and (root / "subagents").exists():
        project_root = root
        break
else:
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent

sys.path.insert(0, str(project_root))

# 导入任务结构化模块
try:
    from scripts.task_structuring import StructuredTask, TaskCategory, TaskPriority, TaskParameter
except ImportError:
    # 尝试相对导入
    from task_structuring import StructuredTask, TaskCategory, TaskPriority, TaskParameter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TriggerSignal:
    """监测触发信号"""
    signal_type: str                          # 信号类型：realtime_monitoring
    timestamp: str                            # 触发时间戳
    influent_data: Dict[str, Any]            # 进水数据
    effluent_data: Dict[str, Any]            # 出水数据
    metadata: Dict[str, Any] = None          # 元数据


@dataclass
class IntentResult:
    """意图识别结果"""
    intent_type: str                          # 意图类型
    confidence: float                         # 置信度
    entities: Dict[str, Any]                  # 提取的实体
    analysis_scope: List[str]                 # 分析范围
    priority: str                             # 优先级


class MasterAgentIdentity:
    """主智能体身份信息"""

    def __init__(self, workspace_path: Path = None):
        """初始化主智能体身份"""
        if workspace_path is None:
            workspace_path = project_root / "workspace"

        self.workspace_path = workspace_path
        self.identity_files = {
            "IDENTITY": workspace_path / "IDENTITY.md",
            "AGENTS": workspace_path / "AGENTS.md",
            "MEMORY": workspace_path / "MEMORY.md",
            "HEARTBEAT": workspace_path / "HEARTBEAT.md",
            "TOOLS": workspace_path / "TOOLS.md",
            "SKILL": workspace_path / "skills" / "orchestrator-core" / "SKILL.md"
        }
        self._identity_cache = {}

    def load_identity(self) -> Dict[str, str]:
        """加载主智能体完整身份"""
        if self._identity_cache:
            return self._identity_cache

        identity = {}
        for name, path in self.identity_files.items():
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        identity[name] = f.read()
                    logger.info(f"[IDENTITY] 已加载 {name}")
                except Exception as e:
                    logger.warning(f"[IDENTITY] 无法加载 {name}: {e}")
                    identity[name] = ""
            else:
                logger.warning(f"[IDENTITY] 文件不存在: {path}")
                identity[name] = ""

        self._identity_cache = identity
        return identity

    def get_identity_summary(self) -> str:
        """获取身份摘要（用于大模型提示）"""
        identity = self.load_identity()
        summary_parts = []

        if identity.get("IDENTITY"):
            summary_parts.append("=== 主智能体身份 ===")
            summary_parts.append(identity["IDENTITY"][:500] + "..." if len(identity["IDENTITY"]) > 500 else identity["IDENTITY"])

        if identity.get("SKILL"):
            summary_parts.append("\n=== 核心技能 ===")
            summary_parts.append(identity["SKILL"][:500] + "..." if len(identity["SKILL"]) > 500 else identity["SKILL"])

        return "\n".join(summary_parts)


class TaskReceivingAndParsingModule:
    """任务接收与解析模块"""

    def __init__(self, llm_client=None):
        """
        初始化模块

        Args:
            llm_client: 大模型客户端（可选，用于意图解析）
        """
        self.master_identity = MasterAgentIdentity()
        self.llm_client = llm_client
        logger.info("[INIT] 任务接收与解析模块初始化完成")

    def receive_trigger_signal(self, data: Dict[str, Any]) -> TriggerSignal:
        """
        接收触发信号

        Args:
            data: 来自Flask的原始数据
                {
                    "influent": {...},
                    "effluent": {...},
                    "timestamp": "...",
                    "start_time": "...",  # 时间序列开始时间
                    "end_time": "...",    # 时间序列结束时间
                    "data_count": N,       # 数据条数
                    "influent_timeseries": [...],
                    "effluent_timeseries": [...]
                }

        Returns:
            触发信号
        """
        influent = data.get("influent", {})
        effluent = data.get("effluent", {})
        timestamp = data.get("timestamp", datetime.now().isoformat())

        # 提取时间序列信息
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        data_count = data.get("data_count", 1)
        influent_timeseries = data.get("influent_timeseries", [])
        effluent_timeseries = data.get("effluent_timeseries", [])

        signal = TriggerSignal(
            signal_type="realtime_monitoring",
            timestamp=timestamp,
            influent_data=influent,
            effluent_data=effluent,
            metadata={
                "source": "dual_stream_simulator",
                "start_time": start_time,
                "end_time": end_time,
                "data_count": data_count,
                "influent_timeseries": influent_timeseries,
                "effluent_timeseries": effluent_timeseries,
                "time_range": data.get("time_range", {})
            }
        )

        logger.info(f"[RECEIVE] 接收到触发信号: {timestamp}, 数据量: {data_count}条")
        if start_time and end_time:
            logger.info(f"[RECEIVE] 时间范围: {start_time} ~ {end_time}")
        return signal

    def parse_intent_with_llm(self, signal: TriggerSignal) -> IntentResult:
        """
        使用大模型解析意图

        Args:
            signal: 触发信号

        Returns:
            意图识别结果
        """
        if self.llm_client is None:
            # 如果没有大模型客户端，使用规则解析
            return self._parse_intent_by_rules(signal)

        # 加载主智能体身份
        identity_context = self.master_identity.get_identity_summary()

        # 构建提示词
        prompt = self._build_intent_prompt(signal, identity_context)

        try:
            # 调用大模型
            response = self.llm_client.chat(prompt)
            # 解析大模型响应
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"[LLM] 大模型调用失败: {e}")
            return self._parse_intent_by_rules(signal)

    def _build_intent_prompt(self, signal: TriggerSignal, identity_context: str) -> str:
        """构建大模型提示词"""
        return f"""你是废水虚假排放智能监测主智能体。

{identity_context}

当前接收到实时监测数据：
- 时间: {signal.timestamp}
- 进水数据: {list(signal.influent_data.keys())}
- 出水数据: {list(signal.effluent_data.keys())}

请分析此数据并返回任务意图（JSON格式）：
{{
    "intent_type": "violation_detection",
    "confidence": 0.95,
    "entities": {{"indicators": ["pH", "COD"]}},
    "analysis_scope": ["data_governance", "feature_analysis", "anomaly_detection", "rule_reasoning"],
    "priority": "high"
}}

只返回JSON，不要其他内容。"""

    def _parse_llm_response(self, response: str) -> IntentResult:
        """解析大模型响应"""
        import json

        try:
            # 检查响应是否为空
            if not response or not response.strip():
                logger.warning("[PARSE] 大模型返回空响应，使用规则解析")
                return self._parse_intent_by_rules(None)

            # 尝试提取JSON（处理可能的markdown代码块）
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return IntentResult(
                intent_type=data.get("intent_type", "violation_detection"),
                confidence=float(data.get("confidence", 0.8)),
                entities=data.get("entities", {}),
                analysis_scope=data.get("analysis_scope", []),
                priority=data.get("priority", "medium")
            )
        except Exception as e:
            logger.warning(f"[PARSE] 解析大模型响应失败: {e}，使用规则解析")
            logger.debug(f"[PARSE] 原始响应: {response[:200]}...")
            # 返回默认意图
            return self._parse_intent_by_rules(None)

    def _parse_intent_by_rules(self, signal: TriggerSignal = None) -> IntentResult:
        """使用规则解析意图（备用方案）"""
        # 实时监测总是需要完整的4步分析
        return IntentResult(
            intent_type="violation_detection",
            confidence=0.9,
            entities={
                "indicators": ["pH", "COD", "TN", "NH3-N", "TP"],
                "timestamp": signal.timestamp
            },
            analysis_scope=["data_governance", "feature_analysis", "anomaly_detection", "rule_reasoning"],
            priority="high"  # 实时监测总是高优先级
        )

    def create_structured_task(self, signal: TriggerSignal, intent: IntentResult) -> StructuredTask:
        """
        创建结构化任务

        Args:
            signal: 触发信号
            intent: 意图识别结果

        Returns:
            结构化任务
        """
        task_id = f"realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 映射优先级
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW
        }

        # 获取时间范围信息（但不传递大数据给LLM）
        start_time = signal.metadata.get("start_time") if signal.metadata else None
        end_time = signal.metadata.get("end_time") if signal.metadata else None
        data_count = signal.metadata.get("data_count", 1) if signal.metadata else 1
        influent_timeseries = signal.metadata.get("influent_timeseries", []) if signal.metadata else []
        effluent_timeseries = signal.metadata.get("effluent_timeseries", []) if signal.metadata else []

        # 准备输入参数（不包含大数据）
        input_params = [
            TaskParameter(
                name="has_timeseries",
                value=len(influent_timeseries) > 0,
                required=True,
                description="是否有时间序列数据"
            ),
            TaskParameter(
                name="timestamp",
                value=signal.timestamp,
                required=True,
                description="数据时间戳（最新）"
            ),
            TaskParameter(
                name="start_time",
                value=start_time,
                required=True,
                description="时间序列开始时间"
            ),
            TaskParameter(
                name="end_time",
                value=end_time,
                required=True,
                description="时间序列结束时间"
            ),
            TaskParameter(
                name="data_count",
                value=data_count,
                required=True,
                description="时间序列数据条数"
            ),
            TaskParameter(
                name="analysis_scope",
                value=intent.analysis_scope,
                required=True,
                description="分析范围"
            )
        ]

        # 构建描述
        if start_time and end_time:
            description = f"实时监测数据分析，时间范围: {start_time} ~ {end_time}，数据量: {data_count}条"
        else:
            description = f"实时监测数据分析，时间: {signal.timestamp}"

        # 创建结构化任务（大数据存在metadata中，不传给LLM）
        task = StructuredTask(
            task_id=task_id,
            task_name="实时监测数据分析",
            category=TaskCategory.DUAL_STREAM_ANALYSIS,
            priority=priority_map.get(intent.priority, TaskPriority.HIGH),
            description=description,
            input_params=input_params,
            timeout_seconds=60,
            retry_count=1,
            metadata={
                "signal_type": signal.signal_type,
                "intent_confidence": intent.confidence,
                "trigger_timestamp": signal.timestamp,
                "start_time": start_time,
                "end_time": end_time,
                "data_count": data_count,
                # 大数据存在这里，脚本执行时直接使用
                "influent_timeseries": influent_timeseries,
                "effluent_timeseries": effluent_timeseries,
                "time_range": signal.metadata.get("time_range", {}) if signal.metadata else {},
                "latest_influent": signal.influent_data,
                "latest_effluent": signal.effluent_data
            }
        )

        logger.info(f"[TASK] 创建结构化任务: {task_id}, 优先级: {task.priority.value}")
        return task

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理接收到的数据（主入口）

        Args:
            data: 来自Flask的原始数据

        Returns:
            处理结果，包含结构化任务
        """
        # 1. 接收触发信号
        signal = self.receive_trigger_signal(data)

        # 2. 解析意图
        intent = self.parse_intent_with_llm(signal)

        # 3. 创建结构化任务
        structured_task = self.create_structured_task(signal, intent)

        return {
            "status": "success",
            "signal": signal,
            "intent": intent,
            "structured_task": structured_task.to_dict()
        }


# 便捷函数
def create_task_receiving_module(llm_client=None) -> TaskReceivingAndParsingModule:
    """创建任务接收与解析模块"""
    return TaskReceivingAndParsingModule(llm_client=llm_client)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("任务接收与解析模块测试")
    print("=" * 60)

    module = create_task_receiving_module()

    # 模拟数据
    test_data = {
        "influent": {
            "pH值": 7.2,
            "化学需氧量浓度（毫克/升）": 100,
            "监测时间": "2026-05-22 10:00:00"
        },
        "effluent": {
            "pH值": 7.5,
            "化学需氧量浓度（毫克/升）": 45,
            "监测时间": "2026-05-22 12:00:00"
        },
        "timestamp": "2026-05-22T12:00:00"
    }

    result = module.process(test_data)

    print(f"状态: {result['status']}")
    print(f"意图类型: {result['intent'].intent_type}")
    print(f"任务ID: {result['structured_task']['task_id']}")
    print(f"优先级: {result['structured_task']['priority']}")

    print("\n" + "=" * 60)
    print("测试完成")
