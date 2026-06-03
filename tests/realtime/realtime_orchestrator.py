#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时监测编排器
功能：基于orchestrator-core实现实时监测，协调4个子智能体协同分析

架构：
数据到达 → Orchestrator任务分解 → 任务编排 → 子智能体协同执行 → 告警输出
"""

import os
import sys
import logging
import collections
from typing import Dict, Any, List, Optional, Deque
from datetime import datetime
from pathlib import Path
import copy

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Orchestrator模块路径（主智能体）
orchestrator_scripts = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(orchestrator_scripts))

# Orchestrator模块（用于任务编排，可选）
# from task_structuring import structure_task, TaskCategory
# from resource_matching import match_task_to_agent
# from task_flow_generation import create_task_flow, get_ready_tasks
from execution_control import ExecutionControlModule, ExecutionStatus

# ==================== 简化版子智能体实现 ====================
# 由于导入路径问题，使用简化版实现来保证流程可运行

class SimpleDataGovernanceAgent:
    """简化版数据治理子智能体"""
    def __init__(self):
        self.name = "数据治理子智能体"

    def process(self, request):
        data = request.get("raw_data")
        indicators = request.get("indicators", [])

        # 字段名标准化
        field_mapping = {
            "pH值": "pH", "化学需氧量浓度（毫克/升）": "COD",
            "总氮浓度（毫克/升）": "TN", "氨氮浓度（毫克/升）": "NH3-N",
            "总磷浓度（毫克/升）": "TP", "悬浮物浓度（毫克/升）": "SS"
        }

        # 处理数据
        processed = {}
        for field, norm_field in field_mapping.items():
            if field in data:
                try:
                    val = float(data[field]) if str(data[field]).strip() not in ['/', '', 'NA'] else None
                    if val is not None:
                        processed[norm_field] = val
                except (ValueError, TypeError):
                    pass

        return {
            "quality_report": {
                "total_fields": len(data),
                "processed_fields": len(processed)
            }
        }


class SimpleFeatureAnalysisAgent:
    """简化版特征分析子智能体"""
    def __init__(self):
        self.name = "特征分析子智能体"
        self.window_data = []

    def process(self, request):
        data = request.get("data")
        indicators = request.get("indicators", [])

        # 维护滑动窗口
        self.window_data.append(data)
        if len(self.window_data) > 24:
            self.window_data.pop(0)

        features = {}
        for ind in indicators:
            values = [d.get(ind) for d in self.window_data if ind in d and d.get(ind) is not None]
            if values:
                import numpy as np
                features[ind] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "count": len(values)
                }

        return {"features": features}

    def reset(self):
        self.window_data = []


class SimpleAnomalyDetectionAgent:
    """简化版异常检测子智能体"""
    def __init__(self):
        self.name = "异常检测子智能体"

        # 字段名映射
        self.field_mapping = {
            "pH值": "pH", "化学需氧量浓度（毫克/升）": "COD",
            "总氮浓度（毫克/升）": "TN", "氨氮浓度（毫克/升）": "NH3-N",
            "总磷浓度（毫克/升）": "TP", "悬浮物浓度（毫克/升）": "SS"
        }

        # 法规限值（GB18918-2002 一级A标准）
        self.limits = {
            "pH": (6.0, 9.0), "COD": (None, 50.0),
            "TN": (None, 15.0), "NH3-N": (None, 5.0),
            "TP": (None, 0.5)
        }

    def process(self, request):
        data = request.get("data")
        indicators = request.get("indicators", [])
        operators = request.get("operators", ["iqr"])

        anomalies = []

        # 标准化字段名并检测异常
        for field, norm_field in self.field_mapping.items():
            if field not in data or norm_field not in self.limits:
                continue

            try:
                val_str = str(data[field]).strip()
                if val_str in ['/', '', 'NA', 'N/A']:
                    continue

                val = float(val_str)
                min_val, max_val = self.limits[norm_field]

                if min_val is not None and val < min_val:
                    anomalies.append({
                        "indicator": norm_field,
                        "value": val,
                        "type": "below_limit",
                        "limit": min_val
                    })

                if max_val is not None and val > max_val:
                    anomalies.append({
                        "indicator": norm_field,
                        "value": val,
                        "type": "exceedance",
                        "limit": max_val
                    })
            except (ValueError, TypeError):
                pass

        return {
            "has_anomaly": len(anomalies) > 0,
            "anomalies": anomalies
        }


class SimpleRuleReasoningAgent:
    """简化版规则推理子智能体"""
    def __init__(self):
        self.name = "规则推理子智能体"

    def process(self, request):
        anomalies = request.get("anomalies", [])
        features = request.get("features", {})

        violations = []

        for anom in anomalies:
            violations.append({
                "type": anom.get("type", "unknown"),
                "level": "high" if anom.get("type") == "exceedance" else "medium",
                "message": f"{anom.get('indicator')}异常: {anom.get('value')}",
                "evidence": {"anomaly": anom}
            })

        # 恒定值检测（插瓶干扰）
        for ind, feat in features.items():
            if feat.get("std", 1) < 0.1 and feat.get("count", 0) >= 5:
                violations.append({
                    "type": "constant_value",
                    "level": "critical",
                    "message": f"{ind}恒定值异常（疑似插瓶干扰）",
                    "evidence": {"indicator": ind, "std": feat["std"]}
                })

        return {
            "has_violation": len(violations) > 0,
            "violations": violations
        }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeOrchestrator:
    """
    实时监测编排器

    功能：
    1. 维护滑动窗口（最近N条数据）
    2. 每次数据到达时触发任务分解和编排
    3. 协调4个子智能体协同执行：
       - 数据治理子智能体：数据质量检查、清洗
       - 特征分析子智能体：滑动窗口特征提取
       - 异常检测子智能体：异常识别、模式匹配
       - 规则推理子智能体：违规判定、嫌疑等级
    4. 输出告警并迭代优化
    """

    # 字段名映射
    FIELD_MAPPING = {
        "pH值": "pH",
        "化学需氧量浓度（毫克/升）": "COD",
        "总氮浓度（毫克/升）": "TN",
        "氨氮浓度（毫克/升）": "NH3-N",
        "总磷浓度（毫克/升）": "TP",
        "悬浮物浓度（毫克/升）": "SS",
        "流量（升/秒）": "flow_rate",
    }

    def __init__(self, window_size: int = 24):
        """
        初始化实时编排器

        Args:
            window_size: 滑动窗口大小（条数）
        """
        self.window_size = window_size
        self.window: Deque[Dict[str, Any]] = collections.deque(maxlen=window_size)

        # 初始化执行控制模块
        self.execution_control = ExecutionControlModule()

        # 初始化子智能体客户端（直接调用）
        self._init_agents()

        # 告警计数
        self.alert_counts: Dict[str, int] = {}

        # 统计信息
        self.total_processed = 0
        self.total_alerts = 0

        logger.info(f"[INIT] 实时监测编排器初始化")
        logger.info(f"[INIT] 窗口大小: {window_size}")

    def _init_agents(self):
        """初始化子智能体（使用简化版实现）"""
        try:
            self.data_governance_agent = SimpleDataGovernanceAgent()
            self.feature_analysis_agent = SimpleFeatureAnalysisAgent()
            self.anomaly_detection_agent = SimpleAnomalyDetectionAgent()
            self.rule_reasoning_agent = SimpleRuleReasoningAgent()

            # 注册到执行控制模块
            self.execution_control.register_agent_client("data-governance-agent", self.data_governance_agent)
            self.execution_control.register_agent_client("feature-analysis-agent", self.feature_analysis_agent)
            self.execution_control.register_agent_client("anomaly-detection-agent", self.anomaly_detection_agent)
            self.execution_control.register_agent_client("rule-reasoning-agent", self.rule_reasoning_agent)

            logger.info("[INIT] 所有子智能体已注册（简化版）")
        except Exception as e:
            logger.error(f"[ERROR] 子智能体初始化失败: {e}")
            raise

    def _normalize_field_name(self, field: str) -> Optional[str]:
        """标准化字段名"""
        return self.FIELD_MAPPING.get(field, field)

    def _extract_indicators(self, data: Dict[str, Any]) -> Dict[str, float]:
        """提取指标值"""
        indicators = {}
        for field, value in data.items():
            norm_field = self._normalize_field_name(field)
            if norm_field:
                try:
                    val = float(str(value).strip()) if str(value).strip() not in ['/', '', 'NA'] else None
                    if val is not None:
                        indicators[norm_field] = val
                except (ValueError, TypeError):
                    pass
        return indicators

    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            val_str = str(value).strip()
            if val_str in ['/', '', 'NA', 'N/A', 'null', 'None']:
                return None
            return float(val_str)
        except (ValueError, TypeError):
            return None

    async def process_realtime_data(self, influent_data: Dict[str, Any],
                                    effluent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理实时数据

        Args:
            influent_data: 进水数据
            effluent_data: 出水数据

        Returns:
            分析结果
        """
        timestamp = datetime.now().isoformat()
        self.total_processed += 1

        # 1. 更新滑动窗口
        self.window.append({
            "timestamp": timestamp,
            "influent": copy.deepcopy(influent_data),
            "effluent": copy.deepcopy(effluent_data)
        })

        # 2. 准备窗口数据
        window_data = self._prepare_window_data()

        # 3. 创建实时分析任务流
        task_flow = self._create_realtime_task_flow(timestamp, window_data)

        # 4. 执行任务流
        execution_result = await self._execute_realtime_flow(task_flow, window_data)

        # 5. 处理结果并生成告警
        alerts = self._generate_alerts(execution_result)

        return {
            "timestamp": timestamp,
            "has_anomaly": execution_result.get("has_anomaly", False),
            "has_violation": execution_result.get("has_violation", False),
            "anomalies": execution_result.get("anomalies", []),
            "alerts": alerts,
            "window_size": len(self.window),
            "total_processed": self.total_processed
        }

    def _prepare_window_data(self) -> Dict[str, Any]:
        """准备窗口数据供子智能体使用"""
        return {
            "indicators": ["pH", "COD", "TN", "NH3-N", "TP", "SS"],
            "window_size": len(self.window)
        }

    def _create_realtime_task_flow(self, timestamp: str, window_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建实时分析任务流"""
        import uuid
        flow_id = f"realtime_flow_{timestamp.replace(':', '-').replace('.', '-')}"

        # 定义任务
        tasks = [
            {
                "task_id": "task_001",
                "task_name": "实时数据清洗",
                "category": "data_cleaning",
                "priority": "high",
                "input_params": [
                    {"name": "data", "value": window_data},
                    {"name": "indicators", "value": window_data["indicators"]}
                ]
            },
            {
                "task_id": "task_002",
                "task_name": "实时特征提取",
                "category": "feature_extraction",
                "priority": "high",
                "dependencies": ["task_001"],
                "input_params": [
                    {"name": "data", "value": window_data},
                    {"name": "window", "value": window_data["window_size"]}
                ]
            },
            {
                "task_id": "task_003",
                "task_name": "实时异常检测",
                "category": "anomaly_detection",
                "priority": "high",
                "dependencies": ["task_002"],
                "input_params": [
                    {"name": "data", "value": window_data},
                    {"name": "operators", "value": ["iqr", "zscore"]}
                ]
            },
            {
                "task_id": "task_004",
                "task_name": "违规模式判定",
                "category": "rule_reasoning",
                "priority": "high",
                "dependencies": ["task_003"],
                "input_params": [
                    {"name": "anomalies", "value": []},  # 从task_003获取
                    {"name": "regulations", "value": "GB18918_2002"}
                ]
            }
        ]

        # 定义阶段
        stages = [
            {"stage_id": "stage_1", "tasks": ["task_001"], "execution_mode": "sequential"},
            {"stage_id": "stage_2", "tasks": ["task_002"], "execution_mode": "sequential"},
            {"stage_id": "stage_3", "tasks": ["task_003"], "execution_mode": "sequential"},
            {"stage_id": "stage_4", "tasks": ["task_004"], "execution_mode": "sequential"}
        ]

        return {
            "flow_id": flow_id,
            "tasks": {t["task_id"]: t for t in tasks},
            "stages": stages
        }

    async def _execute_realtime_flow(self, task_flow: Dict[str, Any],
                                     window_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行实时任务流（使用简化版子智能体）"""
        result = {
            "has_anomaly": False,
            "has_violation": False,
            "anomalies": [],
            "violations": []
        }

        try:
            # 获取最新的出水数据
            if len(self.window) == 0:
                return result

            latest_data = self.window[-1]["effluent"]

            # 阶段1: 数据治理子智能体
            logger.info("[ORCHESTRATOR] 阶段1: 数据治理...")
            gov_result = self.data_governance_agent.process({
                "raw_data": latest_data,
                "indicators": window_data["indicators"]
            })

            # 阶段2: 特征分析子智能体
            logger.info("[ORCHESTRATOR] 阶段2: 特征分析...")
            feat_result = self.feature_analysis_agent.process({
                "data": latest_data,
                "indicators": window_data["indicators"]
            })

            # 阶段3: 异常检测子智能体
            logger.info("[ORCHESTRATOR] 阶段3: 异常检测...")
            anom_result = self.anomaly_detection_agent.process({
                "data": latest_data,
                "indicators": window_data["indicators"],
                "operators": ["iqr", "zscore"]
            })

            if anom_result.get("has_anomaly"):
                result["has_anomaly"] = True
                result["anomalies"] = anom_result.get("anomalies", [])
                logger.info(f"[ANOM] 检测到 {len(result['anomalies'])} 个异常")

            # 阶段4: 规则推理子智能体
            logger.info("[ORCHESTRATOR] 阶段4: 规则推理...")
            rule_result = self.rule_reasoning_agent.process({
                "anomalies": result["anomalies"],
                "features": feat_result.get("features", {})
            })

            if rule_result.get("has_violation"):
                result["has_violation"] = True
                result["violations"] = rule_result.get("violations", [])
                logger.info(f"[RULE] 检测到 {len(result['violations'])} 个违规")

        except Exception as e:
            logger.error(f"[ERROR] 执行失败: {e}")
            import traceback
            traceback.print_exc()

        return result

    def _generate_alerts(self, execution_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成告警"""
        alerts = []

        for violation in execution_result.get("violations", []):
            alert = {
                "type": violation.get("type", "unknown"),
                "level": violation.get("level", "medium"),
                "message": violation.get("message", ""),
                "evidence": violation.get("evidence", {}),
                "timestamp": datetime.now().isoformat()
            }
            alerts.append(alert)

            # 更新计数
            alert_type = alert["type"]
            self.alert_counts[alert_type] = self.alert_counts.get(alert_type, 0) + 1
            self.total_alerts += 1

            # 记录日志
            logger.warning(f"[ALERT] {alert['type']} ({alert['level']}): {alert['message']}")

        return alerts

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "window_size": len(self.window),
            "total_processed": self.total_processed,
            "total_alerts": self.total_alerts,
            "alert_counts": self.alert_counts
        }

    def reset(self):
        """重置编排器状态"""
        self.window.clear()
        self.alert_counts.clear()
        self.total_processed = 0
        self.total_alerts = 0
        logger.info("[RESET] 编排器状态已重置")


# 便捷函数
def create_realtime_orchestrator(window_size: int = 24) -> RealtimeOrchestrator:
    """创建实时编排器"""
    return RealtimeOrchestrator(window_size=window_size)


# 同步包装函数（用于Flask中间件）
def process_realtime_data_sync(orchestrator: RealtimeOrchestrator,
                               influent_data: Dict[str, Any],
                               effluent_data: Dict[str, Any]) -> Dict[str, Any]:
    """同步处理实时数据"""
    import asyncio
    return asyncio.run(orchestrator.process_realtime_data(influent_data, effluent_data))


if __name__ == "__main__":
    # 测试
    import asyncio

    async def test():
        orchestrator = create_realtime_orchestrator(window_size=5)

        # 模拟正常数据
        print("测试正常数据...")
        for i in range(5):
            influent = {"pH值": 7.0 + i * 0.01, "化学需氧量浓度（毫克/升）": 100}
            effluent = {"pH值": 7.5 + i * 0.01, "化学需氧量浓度（毫克/升）": 45}

            result = await orchestrator.process_realtime_data(influent, effluent)
            print(f"  结果: 异常={result['has_anomaly']}, 违规={result['has_violation']}")

        # 模拟超标数据
        print("\n测试超标数据...")
        influent = {"pH值": 7.0, "化学需氧量浓度（毫克/升）": 100}
        effluent = {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 75}  # 超标

        result = await orchestrator.process_realtime_data(influent, effluent)
        print(f"  结果: 异常={result['has_anomaly']}, 违规={result['has_violation']}")
        if result['alerts']:
            for alert in result['alerts']:
                print(f"  告警: {alert['type']} - {alert['message']}")

        print(f"\n统计: {orchestrator.get_statistics()}")

    asyncio.run(test())
